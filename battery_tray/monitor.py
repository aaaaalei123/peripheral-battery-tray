from __future__ import annotations

import threading
import time
from dataclasses import replace
from typing import Callable, Optional, Protocol

from battery_tray.models import (
    ConnectionKind,
    DeviceId,
    DevicePresence,
    DeviceReading,
)
from battery_tray.state import DeviceScheduler


class BatteryReader(Protocol):
    def probe_presence(self) -> bool:
        ...

    def read(self) -> Optional[DeviceReading]:
        ...


def _empty_reading(device_id: DeviceId, presence: DevicePresence) -> DeviceReading:
    return DeviceReading(
        device_id=device_id,
        percent=None,
        charging=None,
        connection=ConnectionKind.UNKNOWN,
        presence=presence,
        raw_note="",
    )


def _merge_cached(
    cached: Optional[DeviceReading],
    device_id: DeviceId,
    presence: DevicePresence,
) -> DeviceReading:
    if cached is None:
        return _empty_reading(device_id, presence)
    return replace(cached, presence=presence)


class BatteryMonitor:
    def __init__(
        self,
        mouse_reader: BatteryReader,
        keyboard_reader: BatteryReader,
        *,
        poll_interval_sec: float = 60,
        on_update: Optional[Callable[[dict[DeviceId, DeviceReading]], None]] = None,
        time_fn: Callable[[], float] = time.monotonic,
        tick_sec: float = 1.0,
        presence_probe_sec: float = 45.0,
    ) -> None:
        self._mouse = mouse_reader
        self._keyboard = keyboard_reader
        self._scheduler = DeviceScheduler(poll_interval_sec, time_fn=time_fn)
        self._on_update = on_update
        self._time_fn = time_fn
        self._tick_sec = tick_sec
        self._presence_probe_sec = presence_probe_sec

        self._lock = threading.Lock()
        self._cache: dict[DeviceId, Optional[DeviceReading]] = {
            DeviceId.MOUSE: None,
            DeviceId.KEYBOARD: None,
        }
        self._last_presence_probe: dict[DeviceId, float] = {
            did: time_fn() for did in DeviceId
        }

        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _reader(self, device: DeviceId) -> BatteryReader:
        return self._mouse if device == DeviceId.MOUSE else self._keyboard

    def set_poll_interval(self, poll_interval_sec: float) -> None:
        with self._lock:
            self._scheduler.set_poll_interval(poll_interval_sec)

    def readings_snapshot(self) -> dict[DeviceId, DeviceReading]:
        with self._lock:
            return {
                did: _merge_cached(
                    self._cache[did],
                    did,
                    self._scheduler.presence(did),
                )
                for did in DeviceId
            }

    def request_refresh(self) -> None:
        with self._lock:
            for did in DeviceId:
                self._scheduler.force_poll(did)
        self._wake.set()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="BatteryMonitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._tick()
            self._wake.clear()
            if self._wake.wait(timeout=self._tick_sec):
                continue

    def _tick(self) -> None:
        with self._lock:
            for did in self._scheduler.consume_wake_events():
                self._scheduler.force_poll(did)

            now = self._time_fn()
            for did in DeviceId:
                presence = self._scheduler.presence(did)
                if presence in (DevicePresence.SLEEPING, DevicePresence.OFFLINE):
                    last = self._last_presence_probe[did]
                    if (now - last) >= self._presence_probe_sec:
                        self._last_presence_probe[did] = now
                        present = self._reader(did).probe_presence()
                        self._scheduler.on_presence_probe(did, present=present)

            for did in DeviceId:
                if not self._scheduler.should_poll_battery(did):
                    continue
                reading = self._reader(did).read()
                success = reading is not None
                self._scheduler.on_read_result(did, success=success)
                if success and reading is not None:
                    self._cache[did] = reading
                else:
                    pres = self._scheduler.presence(did)
                    cached = self._cache[did]
                    if cached is not None:
                        self._cache[did] = replace(cached, presence=pres)
                    else:
                        self._cache[did] = _empty_reading(did, pres)

            snapshot = {
                did: _merge_cached(
                    self._cache[did],
                    did,
                    self._scheduler.presence(did),
                )
                for did in DeviceId
            }

        if self._on_update is not None:
            self._on_update(snapshot)

    def tick_once(self) -> dict[DeviceId, DeviceReading]:
        """Run one monitor tick (for tests)."""
        self._tick()
        return self.readings_snapshot()
