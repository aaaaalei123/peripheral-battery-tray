from battery_tray.models import DeviceId, DevicePresence
from battery_tray.state import DeviceScheduler


def test_sleep_stops_battery_poll():
    s = DeviceScheduler(poll_interval_sec=60)
    s.on_read_result(DeviceId.MOUSE, success=False)
    assert s.presence(DeviceId.MOUSE) == DevicePresence.SLEEPING
    assert s.should_poll_battery(DeviceId.MOUSE) is False


def test_wake_triggers_immediate_poll():
    s = DeviceScheduler(poll_interval_sec=60)
    s.on_read_result(DeviceId.MOUSE, success=False)
    s.on_presence_probe(DeviceId.MOUSE, present=True)
    assert DeviceId.MOUSE in s.consume_wake_events()
    assert s.should_poll_battery(DeviceId.MOUSE) is True


def test_online_respects_poll_interval():
    t = {"now": 1000.0}

    def time_fn() -> float:
        return t["now"]

    s = DeviceScheduler(poll_interval_sec=60, time_fn=time_fn)
    s.on_read_result(DeviceId.KEYBOARD, success=True)
    assert s.should_poll_battery(DeviceId.KEYBOARD) is False
    t["now"] += 59
    assert s.should_poll_battery(DeviceId.KEYBOARD) is False
    t["now"] += 1
    assert s.should_poll_battery(DeviceId.KEYBOARD) is True


def test_force_poll_while_sleeping():
    s = DeviceScheduler(poll_interval_sec=60)
    s.on_read_result(DeviceId.MOUSE, success=False)
    assert s.should_poll_battery(DeviceId.MOUSE) is False
    s.force_poll(DeviceId.MOUSE)
    assert s.should_poll_battery(DeviceId.MOUSE) is True


def test_read_success_from_sleeping_emits_wake():
    s = DeviceScheduler(poll_interval_sec=60)
    s.on_read_result(DeviceId.KEYBOARD, success=False)
    s.on_read_result(DeviceId.KEYBOARD, success=True)
    assert s.consume_wake_events() == [DeviceId.KEYBOARD]


def test_force_poll_while_sleeping_consumed_on_failed_read():
    s = DeviceScheduler(poll_interval_sec=60)
    s.on_read_result(DeviceId.MOUSE, success=False)
    s.force_poll(DeviceId.MOUSE)
    assert s.should_poll_battery(DeviceId.MOUSE) is True
    s.on_read_result(DeviceId.MOUSE, success=False)
    assert s.should_poll_battery(DeviceId.MOUSE) is False
