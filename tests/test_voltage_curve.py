from battery_tray.voltage_curve import voltage_mv_to_percent


def test_empty_and_full():
    assert voltage_mv_to_percent(3500) <= 5
    assert voltage_mv_to_percent(4200) >= 95


def test_mid_monotonic():
    assert voltage_mv_to_percent(3800) < voltage_mv_to_percent(4000)
