from __future__ import annotations

from typing import Callable, Iterator, Optional, Protocol

from battery_tray.models import (
    ConnectionKind,
    DeviceId,
    DevicePresence,
    DeviceReading,
)

COMPX_REPORT_ID = 0x13
COMPX_CMD_BATTERY = 0x4A
COMPX_REPORT_LEN = 20

PATH_A_VID = 0x41E4
PATH_A_PID = 0x2001
PATH_A_USAGE_PAGE = 0xFF04
PATH_A_FEATURE_REPORT_ID = 0x06
PATH_A_FEATURE_LEN = 8

PATH_B_TARGETS: tuple[tuple[int, int], ...] = (
    (0x3554, 0xFA09),
    (PATH_A_VID, PATH_A_PID),
)
PATH_B_USAGE_PAGE = 0xFF02
PATH_B_USAGE = 0x0002

PATH_C_VID = 0x3837
PATH_C_PID = 0x3033

HidEnumerateFn = Callable[[int, int], list[dict]]


class MchoseHidHandle(Protocol):
    def get_feature_report(self, report_id: int, length: int) -> Optional[bytes]:
        ...

    def write(self, data: bytes) -> None:
        ...

    def read(self, length: int, timeout_ms: int = 500) -> Optional[bytes]:
        ...

    def close(self) -> None:
        ...


HidOpenPathFn = Callable[[str], Optional[MchoseHidHandle]]


def compx_checksum(report: bytes | bytearray) -> int:
    """Checksum for 20-byte Compx report: sum of first 19 bytes mod 256."""
    if len(report) < 19:
        return sum(report) % 256
    return sum(report[:19]) % 256


def build_compx_battery_request() -> bytes:
    report = bytearray(COMPX_REPORT_LEN)
    report[0] = COMPX_REPORT_ID
    report[1] = COMPX_CMD_BATTERY
    report[19] = compx_checksum(report)
    return bytes(report)


def decode_compx_battery_response(data: bytes) -> tuple[Optional[int], Optional[bool]]:
    if len(data) < 7 or data[0] != COMPX_REPORT_ID:
        return None, None
    if (data[1] & 0x7F) != COMPX_CMD_BATTERY:
        return None, None
    percent = int(data[5])
    if percent > 100:
        return None, None
    charging: Optional[bool] = None
    if len(data) > 6:
        charging = data[6] == 0x10
    return percent, charging


def decode_feature_report_06(resp: bytes) -> Optional[int]:
    if not resp or len(resp) < 4:
        return None
    percent = int(resp[3])
    if 0 <= percent <= 100:
        return percent
    return None


def _default_hid_enumerate(vid: int, pid: int) -> list[dict]:
    try:
        import hid
    except ImportError:
        return []
    try:
        return list(hid.enumerate(vid, pid))
    except Exception:
        return []


class _HidapiMchoseHandle:
    def __init__(self, device: object) -> None:
        self._dev = device

    def get_feature_report(self, report_id: int, length: int) -> Optional[bytes]:
        try:
            data = self._dev.get_feature_report(report_id, length)  # type: ignore[attr-defined]
        except Exception:
            return None
        if not data:
            return None
        return bytes(data)

    def write(self, data: bytes) -> None:
        self._dev.write(data)  # type: ignore[attr-defined]

    def read(self, length: int, timeout_ms: int = 500) -> Optional[bytes]:
        try:
            data = self._dev.read(length, timeout_ms=timeout_ms)  # type: ignore[attr-defined]
        except Exception:
            return None
        if not data:
            return None
        return bytes(data)

    def close(self) -> None:
        try:
            self._dev.close()  # type: ignore[attr-defined]
        except Exception:
            pass


def default_hid_open_path(path: str) -> Optional[MchoseHidHandle]:
    try:
        import hid
    except ImportError:
        return None
    try:
        dev = hid.device()
        dev.open_path(path)
        dev.set_nonblocking(True)
        return _HidapiMchoseHandle(dev)
    except Exception:
        return None


def _paths_from_info(info: dict) -> list[str]:
    path = info.get("path")
    if path:
        return [path]
    return []


def _enumerate_targets(
    targets: tuple[tuple[int, int], ...],
    enumerate_fn: HidEnumerateFn,
) -> Iterator[dict]:
    seen_paths: set[str] = set()
    for vid, pid in targets:
        for info in enumerate_fn(vid, pid):
            for path in _paths_from_info(info):
                if path in seen_paths:
                    continue
                seen_paths.add(path)
                yield info


def _matches_path_a(info: dict) -> bool:
    return int(info.get("usage_page") or 0) == PATH_A_USAGE_PAGE


def _matches_path_b(info: dict) -> bool:
    return (
        int(info.get("usage_page") or 0) == PATH_B_USAGE_PAGE
        and int(info.get("usage") or 0) == PATH_B_USAGE
    )


def _matches_path_c_private(info: dict) -> bool:
    usage_page = int(info.get("usage_page") or 0)
    return usage_page >= 0xFF00


def _read_path_a_on_handle(handle: MchoseHidHandle) -> Optional[int]:
    resp = handle.get_feature_report(PATH_A_FEATURE_REPORT_ID, PATH_A_FEATURE_LEN)
    return decode_feature_report_06(resp) if resp else None


def _read_path_b_on_handle(
    handle: MchoseHidHandle,
    *,
    timeout_ms: int = 500,
) -> tuple[Optional[int], Optional[bool]]:
    request = build_compx_battery_request()
    try:
        handle.write(request)
        response = handle.read(COMPX_REPORT_LEN, timeout_ms=timeout_ms)
    except Exception:
        return None, None
    if response is None:
        return None, None
    return decode_compx_battery_response(response)


def _try_read_dongle(
    enumerate_fn: HidEnumerateFn,
    open_path_fn: HidOpenPathFn,
    *,
    timeout_ms: int = 500,
) -> Optional[tuple[int, Optional[bool], str]]:
    for info in _enumerate_targets(((PATH_A_VID, PATH_A_PID),), enumerate_fn):
        if not _matches_path_a(info):
            continue
        path = info.get("path")
        if not path:
            continue
        handle = open_path_fn(path)
        if handle is None:
            continue
        try:
            percent = _read_path_a_on_handle(handle)
            if percent is not None:
                return percent, None, "mchose feature_report=0x06"
        finally:
            handle.close()

    for info in _enumerate_targets(PATH_B_TARGETS, enumerate_fn):
        if not _matches_path_b(info):
            continue
        path = info.get("path")
        if not path:
            continue
        handle = open_path_fn(path)
        if handle is None:
            continue
        try:
            percent, charging = _read_path_b_on_handle(handle, timeout_ms=timeout_ms)
            if percent is not None:
                return percent, charging, "mchose compx 0x4A"
        finally:
            handle.close()

    for info in _enumerate_targets(((PATH_C_VID, PATH_C_PID),), enumerate_fn):
        if not _matches_path_c_private(info):
            continue
        path = info.get("path")
        if not path:
            continue
        handle = open_path_fn(path)
        if handle is None:
            continue
        try:
            percent = _read_path_a_on_handle(handle)
            if percent is not None:
                return percent, None, "mchose wired feature_report=0x06"
            percent, charging = _read_path_b_on_handle(handle, timeout_ms=timeout_ms)
            if percent is not None:
                return percent, charging, "mchose wired compx 0x4A"
        except Exception:
            pass
        finally:
            handle.close()

    return None


def _dongle_interface_present(enumerate_fn: HidEnumerateFn) -> bool:
    for info in _enumerate_targets(((PATH_A_VID, PATH_A_PID),), enumerate_fn):
        if _matches_path_a(info):
            return True
    for info in _enumerate_targets(PATH_B_TARGETS, enumerate_fn):
        if _matches_path_b(info):
            return True
    for info in _enumerate_targets(((PATH_C_VID, PATH_C_PID),), enumerate_fn):
        if _matches_path_c_private(info):
            return True
    return False


class MchoseKeyboardReader:
    def __init__(
        self,
        *,
        bt_reader: Optional[object] = None,
        enumerate_fn: Optional[HidEnumerateFn] = None,
        open_path_fn: Optional[HidOpenPathFn] = None,
        timeout_ms: int = 500,
    ) -> None:
        from battery_tray.readers.windows_bt import WindowsBluetoothBatteryReader

        self._bt = bt_reader if bt_reader is not None else WindowsBluetoothBatteryReader()
        self._enumerate_fn = enumerate_fn or _default_hid_enumerate
        self._open_path_fn = open_path_fn or default_hid_open_path
        self.timeout_ms = timeout_ms

    def probe_presence(self) -> bool:
        try:
            if _dongle_interface_present(self._enumerate_fn):
                return True
            probe = getattr(self._bt, "probe_keyboard", None)
            if callable(probe) and probe():
                return True
            return False
        except Exception:
            return False

    def read(self) -> Optional[DeviceReading]:
        try:
            dongle = _try_read_dongle(
                self._enumerate_fn,
                self._open_path_fn,
                timeout_ms=self.timeout_ms,
            )
            if dongle is not None:
                percent, charging, note = dongle
                return DeviceReading(
                    device_id=DeviceId.KEYBOARD,
                    percent=percent,
                    charging=charging,
                    connection=ConnectionKind.DONGLE_24G,
                    presence=DevicePresence.ONLINE,
                    raw_note=note,
                )

            bt_reading = getattr(self._bt, "read_keyboard", lambda: None)()
            if bt_reading is not None:
                return bt_reading
            return None
        except Exception:
            return None
