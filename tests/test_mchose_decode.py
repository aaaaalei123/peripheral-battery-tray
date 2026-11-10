from __future__ import annotations

from battery_tray.models import ConnectionKind, DeviceId, DevicePresence
from battery_tray.readers.mchose_hid import (
    MchoseKeyboardReader,
    build_compx_battery_request,
    compx_checksum,
    decode_compx_battery_response,
    decode_feature_report_06,
    _read_path_a_on_handle,
    _read_path_b_on_handle,
    _try_read_dongle,
)
from battery_tray.readers.windows_bt import WindowsBluetoothBatteryReader


def test_compx_checksum_and_request():
    report = build_compx_battery_request()
    assert len(report) == 20
    assert report[0] == 0x13
    assert report[1] == 0x4A
    assert report[19] == 0x5D
    assert report[19] == compx_checksum(report)


def test_decode_compx_battery_response():
    charging = bytes([0x13, 0x4A, 0, 0, 0, 77, 0x10, 0])
    percent, is_charging = decode_compx_battery_response(charging)
    assert percent == 77
    assert is_charging is True

    ack = bytes([0x13, 0xCA, 0, 0, 0, 55, 0x00, 0])
    percent, is_charging = decode_compx_battery_response(ack)
    assert percent == 55
    assert is_charging is False

    assert decode_compx_battery_response(bytes([0x12, 0x4A, 0, 0, 0, 50])) == (
        None,
        None,
    )
    assert decode_compx_battery_response(bytes([0x13, 0x4B, 0, 0, 0, 50])) == (
        None,
        None,
    )


def test_decode_feature_report_06():
    assert decode_feature_report_06(bytes([0x06, 0, 0, 68])) == 68
    assert decode_feature_report_06(bytes([0x06, 0, 0, 150])) is None
    assert decode_feature_report_06(bytes([0x06, 0, 0])) is None


class _FakeMchoseHandle:
    def __init__(
        self,
        *,
        feature: bytes | None = None,
        reply: bytes | None = None,
    ) -> None:
        self.feature = feature
        self.reply = reply
        self.writes: list[bytes] = []
        self.closed = False

    def get_feature_report(self, report_id: int, length: int) -> bytes | None:
        return self.feature

    def write(self, data: bytes) -> None:
        self.writes.append(data)

    def read(self, length: int, timeout_ms: int = 500) -> bytes | None:
        return self.reply

    def close(self) -> None:
        self.closed = True


def test_path_a_and_b_handles():
    assert _read_path_a_on_handle(
        _FakeMchoseHandle(feature=bytes([0x06, 0, 0, 42]))
    ) == 42

    reply = bytes([0x13, 0x4A, 0, 0, 0, 91, 0x10])
    percent, charging = _read_path_b_on_handle(
        _FakeMchoseHandle(reply=reply),
    )
    assert percent == 91
    assert charging is True
    assert len(_FakeMchoseHandle(reply=reply).writes) == 0


def test_mchose_reader_dongle_aggregate():
    enum = lambda vid, pid: [  # noqa: E731
        {
            "path": "fake-path",
            "usage_page": 0xFF04,
            "usage": 0,
            "vendor_id": vid,
            "product_id": pid,
        }
    ]

    def open_path(path: str):
        return _FakeMchoseHandle(feature=bytes([0x06, 0, 0, 33]))

    reader = MchoseKeyboardReader(
        bt_reader=WindowsBluetoothBatteryReader(finder=lambda: []),
        enumerate_fn=enum,
        open_path_fn=open_path,
    )
    reading = reader.read()
    assert reading is not None
    assert reading.device_id == DeviceId.KEYBOARD
    assert reading.percent == 33
    assert reading.connection == ConnectionKind.DONGLE_24G
    assert reader.probe_presence() is True


def test_mchose_reader_falls_back_to_bluetooth():
    bt = WindowsBluetoothBatteryReader(
        finder=lambda: [
            {
                "name": "MCHOSE G87",
                "properties": {
                    "System.Devices.Aep.Battery.ChargePercentage": 64,
                },
            }
        ]
    )
    reader = MchoseKeyboardReader(
        bt_reader=bt,
        enumerate_fn=lambda vid, pid: [],
        open_path_fn=lambda path: None,
    )
    assert reader.read() is not None
    reading = reader.read()
    assert reading.percent == 64
    assert reading.connection == ConnectionKind.BLUETOOTH
    assert reading.presence == DevicePresence.ONLINE


def test_windows_bt_name_filter():
    reader = WindowsBluetoothBatteryReader(
        finder=lambda: [
            {"name": "Random Mouse", "properties": {}},
            {
                "name": "Machenike G87 BT",
                "properties": {"System.Devices.BatteryLife": 51},
            },
        ]
    )
    assert reader.probe_keyboard() is True
    reading = reader.read_keyboard()
    assert reading is not None
    assert reading.percent == 51


def test_probe_presence_path_b_receiver_only():
    def enum(vid, pid):
        if vid == 0x3554 and pid == 0xFA09:
            return [
                {
                    "path": "path-b-dongle",
                    "usage_page": 0xFF02,
                    "usage": 0x0002,
                }
            ]
        return []

    reader = MchoseKeyboardReader(
        bt_reader=WindowsBluetoothBatteryReader(finder=lambda: []),
        enumerate_fn=enum,
        open_path_fn=lambda path: None,
    )
    assert reader.probe_presence() is True


def test_try_read_dongle_compx_path():
    def enum(vid, pid):
        if vid == 0x3554:
            return [
                {
                    "path": "dongle",
                    "usage_page": 0xFF02,
                    "usage": 0x0002,
                }
            ]
        return []

    def open_path(path: str):
        return _FakeMchoseHandle(
            reply=bytes([0x13, 0x4A, 0, 0, 0, 48, 0x00, 0]),
        )

    result = _try_read_dongle(enum, open_path)
    assert result == (48, False, "mchose compx 0x4A")
