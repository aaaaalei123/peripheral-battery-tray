from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from battery_tray.models import DeviceId, DevicePresence


@dataclass
class _DeviceState:
    presence: DevicePresence = DevicePresence.ONLINE
    last_battery_poll_at: float | None = None
    force_battery_poll: bool = False
    wake_immediate_poll: bool = False


class DeviceScheduler:
    def __init__(
        self,
        poll_interval_sec: float = 60,
        *,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self._poll_interval_sec = poll_interval_sec
        self._time_fn = time_fn
        self._devices: dict[DeviceId, _DeviceState] = {
            did: _DeviceState() for did in DeviceId
        }
        self._wake_events: list[DeviceId] = []

    def presence(self, device: DeviceId) -> DevicePresence:
        return self._devices[device].presence

    def on_read_result(self, device: DeviceId, *, success: bool) -> None:
        st = self._devices[device]
        prev = st.presence
        if success:
            self._maybe_wake(device, prev)
            st.presence = DevicePresence.ONLINE
            st.last_battery_poll_at = self._time_fn()
            st.force_battery_poll = False
            st.wake_immediate_poll = False
        else:
            st.presence = DevicePresence.SLEEPING
            st.force_battery_poll = False
            st.wake_immediate_poll = False

    def on_presence_probe(self, device: DeviceId, *, present: bool) -> None:
        st = self._devices[device]
        prev = st.presence
        if present:
            st.presence = DevicePresence.ONLINE
            self._maybe_wake(device, prev)
        else:
            st.presence = DevicePresence.OFFLINE

    def should_poll_battery(self, device: DeviceId) -> bool:
        st = self._devices[device]
        if st.force_battery_poll:
            return True
        if st.presence == DevicePresence.SLEEPING:
            return False
        if st.presence == DevicePresence.OFFLINE:
            return False
        if st.wake_immediate_poll:
            return True
        if st.last_battery_poll_at is None:
            return True
        return (self._time_fn() - st.last_battery_poll_at) >= self._poll_interval_sec

    def force_poll(self, device: DeviceId) -> None:
        self._devices[device].force_battery_poll = True

    def consume_wake_events(self) -> list[DeviceId]:
        events = list(self._wake_events)
        self._wake_events.clear()
        return events

    def _maybe_wake(self, device: DeviceId, prev: DevicePresence) -> None:
        if prev in (DevicePresence.SLEEPING, DevicePresence.OFFLINE):
            self._wake_events.append(device)
            self._devices[device].wake_immediate_poll = True
