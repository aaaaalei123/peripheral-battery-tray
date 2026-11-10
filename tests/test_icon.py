from battery_tray.icon import render_tray_icon


def test_icon_size():
    img = render_tray_icon(72, charging=False, sleeping=False, light_theme=False)
    assert img.size == (64, 64)
    assert img.mode == "RGBA"
