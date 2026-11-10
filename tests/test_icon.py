from battery_tray.icon import _ring_colors, render_tray_icon


def test_icon_size():
    img = render_tray_icon(72, charging=False, sleeping=False, light_theme=False)
    assert img.size == (64, 64)
    assert img.mode == "RGBA"


def test_low_battery_threshold_controls_red_ring():
    _, red_at_custom = _ring_colors(
        20, False, False, low_battery_percent=25, warn_battery_percent=30
    )
    _, warn_at_default = _ring_colors(
        20, False, False, low_battery_percent=15, warn_battery_percent=30
    )
    assert red_at_custom[0] > 180 and red_at_custom[1] < 100
    assert warn_at_default[1] > 150


def test_render_tray_icon_passes_low_threshold():
    img = render_tray_icon(
        18,
        charging=False,
        sleeping=False,
        light_theme=False,
        low_battery_percent=20,
    )
    assert img.getpixel((32, 8))[0] > 100
