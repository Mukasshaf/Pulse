"""Interface protocols and stub implementation for ESP32 sensor bridge."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class SensorSample:
    """Produced by the serial bridge. The game engine consumes these read-only."""

    unix_ts_ms: int
    bvp: float
    gsr: int
    acc_x: float
    acc_y: float
    acc_z: float


@runtime_checkable
class BridgeInterface(Protocol):
    """Protocol defining required data polling methods for hardware bridge."""

    def get_latest_sample(self) -> SensorSample | None:
        """Drain queue and return the most recent sample, or None if empty."""
        ...

    def get_mpu_variance(self) -> float | None:
        """Return rolling Z-axis variance over last 1s window, or None if no data."""
        ...


class StubBridge:
    """No-op bridge implementation for decoupled execution without hardware."""

    def get_latest_sample(self) -> SensorSample | None:
        """Return None unconditionally."""
        return None

    def get_mpu_variance(self) -> float | None:
        """Return None unconditionally."""
        return None
