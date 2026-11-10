from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Callable, Optional

from battery_tray.config import AppConfig, load_config, save_config
from battery_tray.icon import render_tray_icon
from battery_tray.models import ConnectionKind, DeviceId, DevicePresence, DeviceReading
from battery_tray.monitor import BatteryMonitor
from battery_tray.readers import LogitechHidppReader, MchoseKeyboardReader

AUTOSTART_VALUE_NAME = "PeripheralBatteryTray"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
THEME_KEY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"

_DEVICE_LABEL = {
    DeviceId.KEYBOARD: "键盘",
    DeviceId.MOUSE: "鼠标",
}

_CONN_LABEL = {
    ConnectionKind.LIGHTSPEED: "Lightspeed",
    ConnectionKind.DONGLE_24G: "2.4G",
    ConnectionKind.BLUETOOTH: "蓝牙",
    ConnectionKind.UNKNOWN: "—",
}

_PRESENCE_LABEL = {
    DevicePresence.ONLINE: "在线",
    DevicePresence.SLEEPING: "休眠",
    DevicePresence.OFFLINE: "离线",
}


def detect_light_theme() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, THEME_KEY) as key:
            value, _ = winreg.QueryValueEx(key, "SystemUsesLightTheme")
            return bool(value)
    except OSError:
        return False


def _autostart_command() -> str:
    exe = Path(sys.executable)
    if exe.name.lower().endswith("python.exe"):
        launcher = exe.with_name("pythonw.exe")
        if launcher.exists():
            exe = launcher
    main_py = Path(__file__).resolve().parent.parent / "main.py"
    return f'"{exe}" "{main_py}"'


def is_autostart_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, AUTOSTART_VALUE_NAME)
            return True
    except OSError:
        return False


def set_autostart(enabled: bool) -> None:
    if sys.platform != "win32":
        return
    import winreg

    if enabled:
        cmd = _autostart_command()
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, AUTOSTART_VALUE_NAME, 0, winreg.REG_SZ, cmd)
    else:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                RUN_KEY,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.DeleteValue(key, AUTOSTART_VALUE_NAME)
        except OSError:
            pass


def _percent_display(reading: DeviceReading) -> str:
    if reading.percent is None:
        return "—"
    return f"{reading.percent}%"


def _tooltip_line(readings: dict[DeviceId, DeviceReading]) -> str:
    kb = readings.get(DeviceId.KEYBOARD)
    ms = readings.get(DeviceId.MOUSE)
    kb_pct = _percent_display(kb) if kb else "—"
    ms_pct = _percent_display(ms) if ms else "—"
    return f"键盘 {kb_pct} · 鼠标 {ms_pct}"


def _icon_reading(readings: dict[DeviceId, DeviceReading], icon_device: str) -> DeviceReading:
    did = DeviceId.MOUSE if icon_device == "mouse" else DeviceId.KEYBOARD
    if did in readings:
        return readings[did]
    return DeviceReading(
        device_id=did,
        percent=None,
        charging=None,
        connection=ConnectionKind.UNKNOWN,
        presence=DevicePresence.OFFLINE,
    )


class TrayApp:
    def __init__(
        self,
        cfg: Optional[AppConfig] = None,
        *,
        monitor_factory: Optional[Callable[[AppConfig], BatteryMonitor]] = None,
    ) -> None:
        self.cfg = cfg if cfg is not None else load_config()
        self._light_theme = detect_light_theme()
        self._readings: dict[DeviceId, DeviceReading] = {}
        self._low_notified: set[DeviceId] = set()
        self._ui_lock = threading.Lock()
        self._icon: Optional[object] = None

        if monitor_factory is not None:
            self._monitor = monitor_factory(self.cfg)
        else:
            self._monitor = BatteryMonitor(
                LogitechHidppReader(),
                MchoseKeyboardReader(),
                poll_interval_sec=float(self.cfg.poll_interval_sec),
                on_update=self._on_monitor_update,
            )

    def _on_monitor_update(self, readings: dict[DeviceId, DeviceReading]) -> None:
        with self._ui_lock:
            self._readings = readings
        self._refresh_icon()
        self._check_low_battery(readings)

    def _check_low_battery(self, readings: dict[DeviceId, DeviceReading]) -> None:
        if not self.cfg.notify_low_battery:
            return
        threshold = self.cfg.low_battery_percent
        icon = self._icon
        for did, reading in readings.items():
            pct = reading.percent
            if pct is None:
                continue
            if pct > threshold:
                self._low_notified.discard(did)
                continue
            if did in self._low_notified:
                continue
            if icon is None:
                continue
            label = _DEVICE_LABEL[did]
            try:
                icon.notify(  # type: ignore[attr-defined]
                    f"{label}电量低",
                    f"{label}剩余 {pct}%（阈值 {threshold}%）",
                )
            except Exception:
                pass
            self._low_notified.add(did)

    def _refresh_icon(self) -> None:
        icon = self._icon
        if icon is None:
            return
        with self._ui_lock:
            readings = dict(self._readings)
        ir = _icon_reading(readings, self.cfg.icon_device)
        pct = ir.percent if ir.percent is not None else 0
        sleeping = ir.presence != DevicePresence.ONLINE
        charging = bool(ir.charging) if ir.charging is not None else False
        image = render_tray_icon(
            pct,
            charging=charging,
            sleeping=sleeping,
            light_theme=self._light_theme,
        )
        icon.icon = image  # type: ignore[attr-defined]
        icon.title = _tooltip_line(readings)  # type: ignore[attr-defined]

    def _set_icon_device(self, device: str) -> None:
        self.cfg.icon_device = device
        save_config(self.cfg)
        self._refresh_icon()

    def _set_poll_interval(self, sec: int) -> None:
        self.cfg.poll_interval_sec = sec
        save_config(self.cfg)
        self._monitor.set_poll_interval(float(sec))

    def _set_low_threshold(self, pct: int) -> None:
        self.cfg.low_battery_percent = pct
        save_config(self.cfg)
        self._low_notified.clear()

    def _toggle_notify(self) -> None:
        self.cfg.notify_low_battery = not self.cfg.notify_low_battery
        save_config(self.cfg)
        if not self.cfg.notify_low_battery:
            self._low_notified.clear()

    def _toggle_autostart(self) -> None:
        self.cfg.start_with_windows = not self.cfg.start_with_windows
        save_config(self.cfg)
        set_autostart(self.cfg.start_with_windows)

    def _status_text(self, device: DeviceId) -> str:
        with self._ui_lock:
            reading = self._readings.get(device)
        if reading is None:
            return f"{_DEVICE_LABEL[device]}：无数据"
        pct = _percent_display(reading)
        conn = _CONN_LABEL.get(reading.connection, "—")
        state = _PRESENCE_LABEL.get(reading.presence, reading.presence.value)
        charge = ""
        if reading.charging:
            charge = " · 充电中"
        return f"{_DEVICE_LABEL[device]} {pct} · {conn} · {state}{charge}"

    def _build_menu(self) -> object:
        import pystray

        def checked_icon_device(device: str):
            return lambda item: self.cfg.icon_device == device

        def checked_poll(sec: int):
            return lambda item: self.cfg.poll_interval_sec == sec

        def checked_threshold(pct: int):
            return lambda item: self.cfg.low_battery_percent == pct

        return pystray.Menu(
            pystray.MenuItem(
                lambda item: self._status_text(DeviceId.KEYBOARD),
                None,
                enabled=False,
            ),
            pystray.MenuItem(
                lambda item: self._status_text(DeviceId.MOUSE),
                None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "图标显示设备",
                pystray.Menu(
                    pystray.MenuItem(
                        "键盘",
                        lambda icon, item: self._set_icon_device("keyboard"),
                        checked=checked_icon_device("keyboard"),
                        radio=True,
                    ),
                    pystray.MenuItem(
                        "鼠标",
                        lambda icon, item: self._set_icon_device("mouse"),
                        checked=checked_icon_device("mouse"),
                        radio=True,
                    ),
                ),
            ),
            pystray.MenuItem(
                "低电量阈值",
                pystray.Menu(
                    *[
                        pystray.MenuItem(
                            f"{p}%",
                            lambda icon, item, p=p: self._set_low_threshold(p),
                            checked=checked_threshold(p),
                            radio=True,
                        )
                        for p in (10, 15, 20, 25)
                    ]
                ),
            ),
            pystray.MenuItem(
                "低电量通知",
                lambda icon, item: self._toggle_notify(),
                checked=lambda item: self.cfg.notify_low_battery,
            ),
            pystray.MenuItem(
                "轮询间隔",
                pystray.Menu(
                    *[
                        pystray.MenuItem(
                            f"{sec} 秒",
                            lambda icon, item, sec=sec: self._set_poll_interval(sec),
                            checked=checked_poll(sec),
                            radio=True,
                        )
                        for sec in (30, 60, 120)
                    ]
                ),
            ),
            pystray.MenuItem(
                "开机自启",
                lambda icon, item: self._toggle_autostart(),
                checked=lambda item: self.cfg.start_with_windows,
                enabled=sys.platform == "win32",
            ),
            pystray.MenuItem(
                "立即刷新",
                lambda icon, item: self._monitor.request_refresh(),
            ),
            pystray.MenuItem(
                "退出",
                lambda icon, item: self._shutdown(icon),
            ),
        )

    def _shutdown(self, icon: object) -> None:
        self._monitor.stop()
        try:
            icon.stop()  # type: ignore[attr-defined]
        except Exception:
            pass

    def run(self) -> None:
        try:
            import pystray
        except ImportError as exc:
            raise SystemExit("需要安装 pystray 才能运行托盘程序：pip install pystray") from exc

        if self.cfg.start_with_windows:
            set_autostart(True)

        self._monitor.start()
        image = render_tray_icon(
            0,
            charging=False,
            sleeping=True,
            light_theme=self._light_theme,
        )
        self._icon = pystray.Icon(
            "peripheral-battery",
            image,
            _tooltip_line({}),
            menu=self._build_menu(),
        )
        self._refresh_icon()
        try:
            self._icon.run()  # type: ignore[attr-defined]
        finally:
            self._monitor.stop()
