from __future__ import annotations

import sys
from typing import Any, Callable, Optional

from battery_tray.models import (
    ConnectionKind,
    DeviceId,
    DevicePresence,
    DeviceReading,
)

KEYBOARD_NAME_MARKERS: tuple[str, ...] = ("g87", "mchose", "machenike")

BATTERY_PROPERTY_CANDIDATES: tuple[str, ...] = (
    "System.Devices.Aep.Battery.ChargePercentage",
    "System.Devices.Aep.BatteryLife",
    "System.Devices.BatteryLife",
)

BtDeviceFinder = Callable[[], list[dict[str, Any]]]


def _name_matches_keyboard(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in KEYBOARD_NAME_MARKERS)


def _percent_from_properties(props: dict[str, Any]) -> Optional[int]:
    for key in BATTERY_PROPERTY_CANDIDATES:
        if key not in props:
            continue
        raw = props[key]
        if raw is None:
            continue
        try:
            value = int(raw)
        except (TypeError, ValueError):
            continue
        if 0 <= value <= 100:
            return value
    return None


def _default_find_bluetooth_devices() -> list[dict[str, Any]]:
    if sys.platform != "win32":
        return []
    try:
        from winsdk.windows.devices.enumeration import (  # type: ignore[import-untyped]
            DeviceInformation,
            DeviceInformationKind,
        )
    except ImportError:
        return []

    try:
        import asyncio

        selector = (
            'System.Devices.Aep.ProtocolId:="{70827BBE-4FFB-4A09-A0CA-A44C4436DAA0}"'
        )
        properties = list(BATTERY_PROPERTY_CANDIDATES) + [
            "System.ItemNameDisplay",
            "System.Devices.FriendlyName",
            "System.Devices.Aep.IsConnected",
        ]

        async def _query() -> object:
            return await DeviceInformation.FindAllAsync(
                selector,
                properties,
                DeviceInformationKind.ASSOCIATION_ENDPOINT,
            )

        devices = asyncio.run(_query())
    except Exception:
        return []

    results: list[dict[str, Any]] = []
    try:
        for dev in devices:  # type: ignore[attr-defined]
            name = ""
            props: dict[str, Any] = {}
            try:
                name = str(getattr(dev, "name", "") or "")
                for key in properties:
                    try:
                        props[key] = dev.properties.try_lookup(key)  # type: ignore[attr-defined]
                    except Exception:
                        props[key] = None
            except Exception:
                continue
            if not name:
                for key in ("System.ItemNameDisplay", "System.Devices.FriendlyName"):
                    alt = props.get(key)
                    if alt:
                        name = str(alt)
                        break
            results.append({"name": name, "properties": props})
    except Exception:
        return []
    return results


class WindowsBluetoothBatteryReader:
    def __init__(
        self,
        *,
        finder: Optional[BtDeviceFinder] = None,
    ) -> None:
        self._finder = finder or _default_find_bluetooth_devices

    def probe_keyboard(self) -> bool:
        try:
            for entry in self._finder():
                name = str(entry.get("name") or "")
                if _name_matches_keyboard(name):
                    return True
            return False
        except Exception:
            return False

    def read_keyboard(self) -> Optional[DeviceReading]:
        try:
            best: Optional[tuple[int, str]] = None
            for entry in self._finder():
                name = str(entry.get("name") or "")
                if not _name_matches_keyboard(name):
                    continue
                props = entry.get("properties") or {}
                percent = _percent_from_properties(props)
                if percent is None:
                    continue
                note = f"winrt bt name={name!r}"
                if best is None or percent > best[0]:
                    best = (percent, note)

            if best is None:
                return None

            percent, note = best
            return DeviceReading(
                device_id=DeviceId.KEYBOARD,
                percent=percent,
                charging=None,
                connection=ConnectionKind.BLUETOOTH,
                presence=DevicePresence.ONLINE,
                raw_note=note,
            )
        except Exception:
            return None
