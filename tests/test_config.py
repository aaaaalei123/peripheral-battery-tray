from pathlib import Path

from battery_tray.config import AppConfig, load_config, save_config


def test_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    cfg = AppConfig(icon_device="keyboard", low_battery_percent=20, poll_interval_sec=30)
    save_config(cfg)
    loaded = load_config()
    assert loaded.icon_device == "keyboard"
    assert loaded.low_battery_percent == 20
    assert loaded.poll_interval_sec == 30
