from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AppConfig:
    icon_device: str = "mouse"  # keyboard | mouse
    low_battery_percent: int = 15
    poll_interval_sec: int = 60
    start_with_windows: bool = False
    notify_low_battery: bool = True


def config_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / "PeripheralBattery"


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config() -> AppConfig:
    path = config_path()
    if not path.exists():
        return AppConfig()
    data = json.loads(path.read_text(encoding="utf-8"))
    return AppConfig(**{k: v for k, v in data.items() if k in AppConfig.__dataclass_fields__})


def save_config(cfg: AppConfig) -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    config_path().write_text(json.dumps(asdict(cfg), indent=2), encoding="utf-8")
