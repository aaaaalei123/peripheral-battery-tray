import sys

import pytest

from battery_tray.config import AppConfig
from battery_tray.tray_app import TrayApp, _autostart_command


def test_autostart_command_when_frozen(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Apps\PeripheralBattery.exe", raising=False)
    assert _autostart_command() == r'"C:\Apps\PeripheralBattery.exe"'


def test_autostart_command_when_not_frozen(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    cmd = _autostart_command()
    assert "main.py" in cmd


def test_build_menu_accepts_pystray_actions(monkeypatch, tmp_path):
    pytest.importorskip("pystray")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = TrayApp(cfg=AppConfig())
    menu = app._build_menu()
    assert menu is not None
