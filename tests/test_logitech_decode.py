from __future__ import annotations

from battery_tray.models import ConnectionKind, DeviceId, DevicePresence
from battery_tray.readers.logitech_hidpp import (
    FEATURE_BATTERY_STATUS,
    FEATURE_BATTERY_VOLTAGE,
    FEATURE_UNIFIED_BATTERY,
    LogitechHidppReader,
    build_battery_status_request,
    build_get_feature_request,
    decode_battery_report,
    is_hidpp_error,
)


def test_is_hidpp_error():
    assert is_hidpp_error(bytes([0x10, 0x01, 0x00, 0x80, 0x00, 0x00, 0x00]))
    assert not is_hidpp_error(bytes([0x10, 0x01, 0x05, 0x1D, 0x4B, 0x01, 0x00]))


def test_decode_unified_battery():
    report = bytes([0x10, 0x01, 0x05, 0x1D, 75, 0x01, 0x00])
    percent, charging = decode_battery_report(FEATURE_UNIFIED_BATTERY, report)
    assert percent == 75
    assert charging is True

    discharging = bytes([0x10, 0x01, 0x05, 0x1D, 50, 0x00, 0x00])
    percent, charging = decode_battery_report(FEATURE_UNIFIED_BATTERY, discharging)
    assert percent == 50
    assert charging is False


def test_decode_battery_status():
    report = bytes([0x10, 0x01, 0x03, 0x0D, 88, 0x01, 0x00])
    percent, charging = decode_battery_report(FEATURE_BATTERY_STATUS, report)
    assert percent == 88
    assert charging is True


def test_decode_battery_voltage():
    # 3900 mV -> mid curve; charging flag in byte 6 bit 7
    report = bytes([0x10, 0x01, 0x04, 0x0D, 0x0F, 0x3C, 0x80])
    percent, charging = decode_battery_report(FEATURE_BATTERY_VOLTAGE, report)
    assert percent == 65
    assert charging is True

    report_off = bytes([0x10, 0x01, 0x04, 0x0D, 0x0F, 0x3C, 0x00])
    _, charging = decode_battery_report(FEATURE_BATTERY_VOLTAGE, report_off)
    assert charging is False


def test_decode_error_and_short():
    err = bytes([0x10, 0x01, 0x05, 0x8F, 0x05, 0x00, 0x00])
    assert decode_battery_report(FEATURE_UNIFIED_BATTERY, err) == (None, None)
    assert decode_battery_report(FEATURE_UNIFIED_BATTERY, bytes([0x10, 0x01])) == (
        None,
        None,
    )


def test_build_requests():
    gf = build_get_feature_request(0x01, 0x1004)
    assert gf == bytes([0x10, 0x01, 0x00, 0x0D, 0x10, 0x04, 0x00])

    unified = build_battery_status_request(0x01, 5, FEATURE_UNIFIED_BATTERY)
    assert unified[3] == 0x1D

    voltage = build_battery_status_request(0x01, 4, FEATURE_BATTERY_VOLTAGE)
    assert voltage[3] == 0x0D


class _FakeTransport:
    def __init__(self, responses: list[bytes]) -> None:
        self._responses = list(responses)
        self.writes: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.writes.append(data)

    def read(self, timeout_ms: int = 500) -> bytes | None:
        if not self._responses:
            return None
        return self._responses.pop(0)


def test_reader_read_via_fake_transport():
    feature_idx = 5
    get_feat_resp = bytes([0x10, 0x01, 0x00, 0x00, feature_idx, 0x00, 0x00])
    batt_resp = bytes([0x10, 0x01, feature_idx, 0x1D, 62, 0x00, 0x00])
    transport = _FakeTransport([get_feat_resp, batt_resp])
    reader = LogitechHidppReader(transport)
    reading = reader.read()
    assert reading is not None
    assert reading.device_id == DeviceId.MOUSE
    assert reading.percent == 62
    assert reading.charging is False
    assert reading.connection == ConnectionKind.LIGHTSPEED
    assert reading.presence == DevicePresence.ONLINE

    empty = LogitechHidppReader(_FakeTransport([]))
    assert empty.read() is None


def test_probe_presence():
    transport = _FakeTransport(
        [bytes([0x10, 0x01, 0x00, 0x00, 0x05, 0x00, 0x00])]
    )
    assert LogitechHidppReader(transport).probe_presence() is True
    assert LogitechHidppReader(_FakeTransport([bytes([0x10, 0x01, 0x00, 0x8F, 0x00, 0x00, 0x00])])).probe_presence() is False


class _WriteRaisesTransport:
    def write(self, data: bytes) -> None:
        raise RuntimeError("transport write failed")

    def read(self, timeout_ms: int = 500) -> bytes | None:
        return None


def test_read_returns_none_when_write_raises():
    assert LogitechHidppReader(_WriteRaisesTransport()).read() is None
