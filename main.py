"""Entry point for the peripheral battery tray app."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

def _print_hid_enumerate() -> None:
    try:
        import hid
    except ImportError:
        print("hidapi: 未安装 (pip install hidapi)")
        return

    targets = [
        (0x046D, 0, "Logitech (VID 046D)"),
        (0x3554, 0xFA09, "Mchose receiver 3554:FA09"),
        (0x41E4, 0x2001, "Mchose 41E4:2001"),
        (0x3837, 0x3033, "Mchose wired 3837:3033"),
    ]
    for vid, pid, label in targets:
        print(f"\n--- HID {label} ---")
        try:
            devices = hid.enumerate(vid, pid)
        except Exception as exc:
            print(f"enumerate failed: {exc}")
            continue
        if not devices:
            print("(无设备)")
            continue
        for info in devices:
            slim = {
                k: info.get(k)
                for k in (
                    "vendor_id",
                    "product_id",
                    "path",
                    "serial_number",
                    "interface_number",
                    "usage_page",
                    "usage",
                )
            }
            print(json.dumps(slim, ensure_ascii=False))


def run_probe() -> None:
    from battery_tray.readers import LogitechHidppReader, MchoseKeyboardReader

    print("=== 外设电量探测模式 ===")
    if sys.platform != "win32":
        print(f"平台: {sys.platform}（蓝牙 WinRT 仅在 Windows 可用）\n")

    _print_hid_enumerate()

    print("\n--- 罗技 GPW (HID++) ---")
    mouse = LogitechHidppReader()
    try:
        print("probe_presence:", mouse.probe_presence())
        reading = mouse.read()
        if reading is None:
            print("read: None")
        else:
            print("read:", asdict(reading))
    finally:
        mouse.close()

    print("\n--- 迈从 G87 ---")
    keyboard = MchoseKeyboardReader()
    print("probe_presence:", keyboard.probe_presence())
    kb_reading = keyboard.read()
    if kb_reading is None:
        print("read: None")
    else:
        print("read:", asdict(kb_reading))

    print("\n完成。")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="外设电量托盘")
    parser.add_argument(
        "--probe",
        action="store_true",
        help="枚举 HID 并打印两台 reader 探测结果后退出",
    )
    args = parser.parse_args(argv)

    if args.probe:
        run_probe()
        return

    from battery_tray.tray_app import TrayApp

    TrayApp().run()


if __name__ == "__main__":
    main()
