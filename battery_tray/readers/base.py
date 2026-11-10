from __future__ import annotations

from typing import Optional, Protocol


class HidppTransport(Protocol):
    """Minimal HID++ write/read surface for tests and hardware."""

    def write(self, data: bytes) -> None:
        ...

    def read(self, timeout_ms: int = 500) -> Optional[bytes]:
        ...

