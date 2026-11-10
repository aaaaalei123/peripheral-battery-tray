from __future__ import annotations

# Solaar-style piecewise-linear Li-ion discharge curve (mV -> %).
_VOLTAGE_TABLE: list[tuple[int, int]] = [
    (3500, 0),
    (3600, 10),
    (3700, 25),
    (3800, 45),
    (3900, 65),
    (4000, 80),
    (4100, 92),
    (4200, 100),
]


def _clamp_percent(value: float) -> int:
    return max(0, min(100, int(round(value))))


def voltage_mv_to_percent(mv: int) -> int:
    """Map battery voltage (mV) to state-of-charge percent (0–100)."""
    if mv <= _VOLTAGE_TABLE[0][0]:
        return 0
    if mv >= _VOLTAGE_TABLE[-1][0]:
        return 100

    for (mv0, pct0), (mv1, pct1) in zip(_VOLTAGE_TABLE, _VOLTAGE_TABLE[1:]):
        if mv <= mv1:
            if mv1 == mv0:
                return _clamp_percent(pct1)
            span = (mv - mv0) / (mv1 - mv0)
            return _clamp_percent(pct0 + span * (pct1 - pct0))

    return 100
