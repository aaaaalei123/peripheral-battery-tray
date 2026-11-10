from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from battery_tray.models import (
    ConnectionKind,
    DeviceId,
    DevicePresence,
    DeviceReading,
)
from battery_tray.monitor import BatteryMonitor


@dataclass
class _FakeReader:
    device_id: DeviceId
    present: bool = True
    percent: int = 80
    probe_calls: int = 0
    read_calls: int = 0
    fail_reads: bool = False

    def probe_presence(self) -> bool:
        self.probe_calls += 1
        return self.present

    def read(self) -> Optional[DeviceReading]:
        self.read_calls += 1
        if self.fail_reads or not self.present:
            return None
        return DeviceReading(
            device_id=self.device_id,
            percent=self.percent,
            charging=False,
            connection=ConnectionKind.LIGHTSPEED
            if self.device_id == DeviceId.MOUSE
            else ConnectionKind.DONGLE_24G,
            presence=DevicePresence.ONLINE,
            raw_note="fake",
        )


def test_sleeping_stops_battery_poll_but_probes_presence():
    t = {"now": 1000.0}
    mouse = _FakeReader(DeviceId.MOUSE, present=False, fail_reads=True)
    keyboard = _FakeReader(DeviceId.KEYBOARD, percent=90)
    updates: list[dict] = []

    mon = BatteryMonitor(
        mouse,
        keyboard,
        poll_interval_sec=60,
        on_update=lambda r: updates.append(dict(r)),
        time_fn=lambda: t["now"],
        presence_probe_sec=30.0,
    )

    mon.tick_once()
    assert mouse.read_calls == 1
    assert mon.readings_snapshot()[DeviceId.MOUSE].presence == DevicePresence.SLEEPING

    mouse.read_calls = 0
    t["now"] += 10
    mon.tick_once()
    assert mouse.read_calls == 0
    assert mouse.probe_calls == 0

    t["now"] += 25
    mon.tick_once()
    assert mouse.probe_calls == 1
    assert mouse.read_calls == 0


def test_presence_probe_wake_triggers_immediate_read():
    t = {"now": 2000.0}
    mouse = _FakeReader(DeviceId.MOUSE, present=False, fail_reads=True)
    keyboard = _FakeReader(DeviceId.KEYBOARD)

    mon = BatteryMonitor(
        mouse,
        keyboard,
        poll_interval_sec=60,
        time_fn=lambda: t["now"],
        presence_probe_sec=30.0,
    )

    mon.tick_once()
    assert mon.readings_snapshot()[DeviceId.MOUSE].presence == DevicePresence.SLEEPING

    mouse.fail_reads = False
    mouse.present = True
    mouse.read_calls = 0
    t["now"] += 30
    mon.tick_once()
    assert mouse.probe_calls >= 1
    assert mouse.read_calls >= 1
    snap = mon.readings_snapshot()[DeviceId.MOUSE]
    assert snap.presence == DevicePresence.ONLINE
    assert snap.percent == 80


def test_failed_read_keeps_last_percent():
    t = {"now": 3000.0}
    mouse = _FakeReader(DeviceId.MOUSE, percent=55)
    keyboard = _FakeReader(DeviceId.KEYBOARD)

    mon = BatteryMonitor(
        mouse,
        keyboard,
        poll_interval_sec=0,
        time_fn=lambda: t["now"],
        presence_probe_sec=60.0,
    )

    mon.tick_once()
    assert mon.readings_snapshot()[DeviceId.MOUSE].percent == 55

    mouse.fail_reads = True
    t["now"] += 1
    mon.tick_once()
    snap = mon.readings_snapshot()[DeviceId.MOUSE]
    assert snap.percent == 55
    assert snap.presence == DevicePresence.SLEEPING


def test_request_refresh_force_reads():
    t = {"now": 4000.0}
    mouse = _FakeReader(DeviceId.MOUSE, fail_reads=True)
    keyboard = _FakeReader(DeviceId.KEYBOARD)

    mon = BatteryMonitor(
        mouse,
        keyboard,
        poll_interval_sec=300,
        time_fn=lambda: t["now"],
    )
    mon.tick_once()
    mouse.read_calls = 0
    keyboard.read_calls = 0

    mon.request_refresh()
    mon.tick_once()
    assert mouse.read_calls == 1
    assert keyboard.read_calls == 1


def test_online_respects_poll_interval_in_monitor():
    t = {"now": 5000.0}
    mouse = _FakeReader(DeviceId.MOUSE)
    keyboard = _FakeReader(DeviceId.KEYBOARD)

    mon = BatteryMonitor(
        mouse,
        keyboard,
        poll_interval_sec=60,
        time_fn=lambda: t["now"],
    )
    mon.tick_once()
    mouse.read_calls = 0
    t["now"] += 30
    mon.tick_once()
    assert mouse.read_calls == 0
    t["now"] += 31
    mon.tick_once()
    assert mouse.read_calls == 1
