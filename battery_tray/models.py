from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DeviceId(str, Enum):
    KEYBOARD = "keyboard"
    MOUSE = "mouse"


class ConnectionKind(str, Enum):
    LIGHTSPEED = "lightspeed"
    DONGLE_24G = "2.4g"
    BLUETOOTH = "bluetooth"
    UNKNOWN = "unknown"


class DevicePresence(str, Enum):
    ONLINE = "online"
    SLEEPING = "sleeping"
    OFFLINE = "offline"


@dataclass
class DeviceReading:
    device_id: DeviceId
    percent: Optional[int]
    charging: Optional[bool]
    connection: ConnectionKind
    presence: DevicePresence
    raw_note: str = ""
