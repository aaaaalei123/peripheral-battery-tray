from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from battery_tray.models import (
    ConnectionKind,
    DeviceId,
    DevicePresence,
    DeviceReading,
)
from battery_tray.readers.base import HidppTransport
from battery_tray.voltage_curve import voltage_mv_to_percent

LOGITECH_VID = 0x046D
HIDPP_SHORT_REPORT_ID = 0x10
HIDPP_LONG_REPORT_ID = 0x11
DEFAULT_DEVICE_INDEX = 0x01
DEFAULT_SWID = 0x0D
ROOT_FEATURE_INDEX = 0x00

FEATURE_UNIFIED_BATTERY = 0x1004
FEATURE_BATTERY_STATUS = 0x1000
FEATURE_BATTERY_VOLTAGE = 0x1001

BATTERY_FEATURE_IDS: tuple[int, ...] = (
    FEATURE_UNIFIED_BATTERY,
    FEATURE_BATTERY_STATUS,
    FEATURE_BATTERY_VOLTAGE,
)


def _swid_byte(function: int, swid: int = DEFAULT_SWID) -> int:
    return ((function & 0x0F) << 4) | (swid & 0x0F)


def is_hidpp_error(report: bytes) -> bool:
    if len(report) < 4:
        return True
    return (report[3] & 0xF0) in (0x80, 0x90)


def build_get_feature_request(
    device_index: int,
    feature_id: int,
    *,
    swid: int = DEFAULT_SWID,
) -> bytes:
    hi = (feature_id >> 8) & 0xFF
    lo = feature_id & 0xFF
    return bytes(
        [
            HIDPP_SHORT_REPORT_ID,
            device_index,
            ROOT_FEATURE_INDEX,
            _swid_byte(0, swid),
            hi,
            lo,
            0x00,
        ]
    )


def build_battery_status_request(
    device_index: int,
    feature_index: int,
    feature_id: int,
    *,
    swid: int = DEFAULT_SWID,
) -> bytes:
    function = 1 if feature_id == FEATURE_UNIFIED_BATTERY else 0
    return bytes(
        [
            HIDPP_SHORT_REPORT_ID,
            device_index,
            feature_index,
            _swid_byte(function, swid),
            0x00,
            0x00,
            0x00,
        ]
    )


def decode_battery_report(
    feature_id: int,
    report: bytes,
) -> tuple[Optional[int], Optional[bool]]:
    """Parse a short HID++ battery response (report id 0x10, 7+ bytes)."""
    if len(report) < 7 or report[0] != HIDPP_SHORT_REPORT_ID:
        return None, None
    if is_hidpp_error(report):
        return None, None

    if feature_id == FEATURE_UNIFIED_BATTERY:
        percent = int(report[4])
        if percent > 100:
            return None, None
        charging = report[5] == 0x01 or bool(report[5] & 0x01)
        return percent, charging

    if feature_id == FEATURE_BATTERY_STATUS:
        percent = int(report[4])
        if percent > 100:
            return None, None
        status = report[5]
        charging = status == 0x01 or bool(status & 0x01)
        return percent, charging

    if feature_id == FEATURE_BATTERY_VOLTAGE:
        voltage_mv = (int(report[4]) << 8) | int(report[5])
        charging = bool(report[6] & 0x80)
        percent = voltage_mv_to_percent(voltage_mv)
        return percent, charging

    return None, None


def _exchange(
    transport: HidppTransport,
    request: bytes,
    *,
    timeout_ms: int = 500,
) -> Optional[bytes]:
    try:
        transport.write(request)
    except OSError:
        return None
    try:
        return transport.read(timeout_ms=timeout_ms)
    except OSError:
        return None


def _get_feature_index(
    transport: HidppTransport,
    device_index: int,
    feature_id: int,
    *,
    swid: int = DEFAULT_SWID,
    timeout_ms: int = 500,
) -> Optional[int]:
    request = build_get_feature_request(device_index, feature_id, swid=swid)
    response = _exchange(transport, request, timeout_ms=timeout_ms)
    if response is None or is_hidpp_error(response):
        return None
    if len(response) < 5:
        return None
    feature_index = int(response[4])
    if feature_index == 0x00 and feature_id != 0x0000:
        return None
    return feature_index


@dataclass
class _HidapiTransport:
    device: object

    def write(self, data: bytes) -> None:
        self.device.write(data)  # type: ignore[attr-defined]

    def read(self, timeout_ms: int = 500) -> Optional[bytes]:
        data = self.device.read(32, timeout_ms=timeout_ms)  # type: ignore[attr-defined]
        if not data:
            return None
        return bytes(data)


def open_logitech_hidpp_transport(
    vid: int = LOGITECH_VID,
    pid: int = 0,
) -> Optional[HidppTransport]:
    try:
        import hid
    except ImportError:
        return None

    try:
        candidates = hid.enumerate(vid, pid)
    except OSError:
        return None

    for info in candidates:
        if info.get("usage_page") == 0xFF00 and info.get("usage") == 0x0001:
            path = info.get("path")
            if not path:
                continue
            try:
                dev = hid.device()
                dev.open_path(path)
                dev.set_nonblocking(True)
                return _HidapiTransport(dev)
            except OSError:
                continue
    return None


class LogitechHidppReader:
    def __init__(
        self,
        transport: Optional[HidppTransport] = None,
        *,
        device_index: int = DEFAULT_DEVICE_INDEX,
        swid: int = DEFAULT_SWID,
        timeout_ms: int = 500,
    ) -> None:
        self._transport = transport
        self._owns_transport = transport is None
        self.device_index = device_index
        self.swid = swid
        self.timeout_ms = timeout_ms

    def _ensure_transport(self) -> Optional[HidppTransport]:
        if self._transport is not None:
            return self._transport
        self._transport = open_logitech_hidpp_transport()
        return self._transport

    def close(self) -> None:
        if not self._owns_transport or self._transport is None:
            return
        dev = getattr(self._transport, "device", None)
        if dev is not None:
            try:
                dev.close()  # type: ignore[attr-defined]
            except OSError:
                pass
        self._transport = None

    def probe_presence(self) -> bool:
        transport = self._ensure_transport()
        if transport is None:
            return False
        for feature_id in BATTERY_FEATURE_IDS:
            idx = _get_feature_index(
                transport,
                self.device_index,
                feature_id,
                swid=self.swid,
                timeout_ms=self.timeout_ms,
            )
            if idx is not None:
                return True
        return False

    def read(self) -> Optional[DeviceReading]:
        transport = self._ensure_transport()
        if transport is None:
            return None

        for feature_id in BATTERY_FEATURE_IDS:
            feature_index = _get_feature_index(
                transport,
                self.device_index,
                feature_id,
                swid=self.swid,
                timeout_ms=self.timeout_ms,
            )
            if feature_index is None:
                continue

            request = build_battery_status_request(
                self.device_index,
                feature_index,
                feature_id,
                swid=self.swid,
            )
            response = _exchange(transport, request, timeout_ms=self.timeout_ms)
            if response is None:
                continue

            percent, charging = decode_battery_report(feature_id, response)
            if percent is None:
                continue

            note = f"hid++ feature=0x{feature_id:04X}"
            return DeviceReading(
                device_id=DeviceId.MOUSE,
                percent=percent,
                charging=charging,
                connection=ConnectionKind.LIGHTSPEED,
                presence=DevicePresence.ONLINE,
                raw_note=note,
            )

        return None
