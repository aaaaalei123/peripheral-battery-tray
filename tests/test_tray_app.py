import sys

from battery_tray.tray_app import _autostart_command


def test_autostart_command_when_frozen(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Apps\PeripheralBattery.exe", raising=False)
    assert _autostart_command() == r'"C:\Apps\PeripheralBattery.exe"'


def test_autostart_command_when_not_frozen(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    cmd = _autostart_command()
    assert "main.py" in cmd
