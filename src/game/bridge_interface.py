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
        """Return the most recent unread sample, or None if nothing new has arrived."""
        ...

    def get_mpu_variance(self) -> float | None:
        """Return rolling 1s variance of 3-axis acceleration magnitude, or None if no live data."""
        ...

    def close(self) -> None:
        """Release the underlying port, thread, and files. Idempotent."""
        ...


class StubBridge:
    """No-op bridge implementation for decoupled execution without hardware."""

    def get_latest_sample(self) -> SensorSample | None:
        """Return None unconditionally."""
        return None

    def get_mpu_variance(self) -> float | None:
        """Return None unconditionally."""
        return None

    def close(self) -> None:
        """Nothing to release."""
