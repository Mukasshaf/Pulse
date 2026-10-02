"""Sensor stream rows for the Pulse engine: parsing, plus the shared latest-sample and motion-variance buffer.

Stream contract (firmware/firmware.ino, 115200 baud, 66.67 Hz):
    sample_idx,timestamp_ms,pulse_raw,gsr_raw,acc_x,acc_y,acc_z
"""
from __future__ import annotations

import json
import math
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from src.game.bridge_interface import SensorSample
from src.game.constants import (
    BRIDGE_MIN_WINDOW_SAMPLES,
    BRIDGE_STALE_AFTER_MS,
    BRIDGE_VARIANCE_WINDOW_MS,
)

# Same column order serial_reader.py writes, so hardware_loader.py and align_signals.py read it unchanged
RECORD_FIELDNAMES: tuple[str, ...] = (
    "sample_idx", "timestamp_ms", "unix_ts_ms", "pulse_raw", "gsr_raw", "acc_x", "acc_y", "acc_z",
)

_FIRMWARE_FIELD_COUNT: int = 7
_RECORDED_FIELD_COUNT: int = 8
POLL_IDLE_S: float = 0.005  # Idle wait of a bridge thread between polls

_JSON_ALIASES: dict[str, tuple[str, ...]] = {
    "sample_idx": ("sample_idx", "idx", "n"),
    "timestamp_ms": ("timestamp_ms", "ts", "t"),
    "pulse_raw": ("pulse_raw", "pulse", "ppg", "bvp"),
    "gsr_raw": ("gsr_raw", "gsr", "eda"),
    "acc_x": ("acc_x", "ax"),
    "acc_y": ("acc_y", "ay"),
    "acc_z": ("acc_z", "az"),
}
_JSON_OPTIONAL_DEFAULTS: dict[str, int] = {"sample_idx": -1, "timestamp_ms": 0}


def wall_ms() -> int:
    """Return current epoch timestamp in milliseconds (the project-wide join clock)."""
    return int(time.time_ns() // 1_000_000)


@dataclass(frozen=True)
class SensorRow:
    """One validated stream row plus the host-side arrival time."""

    sample_idx: int
    timestamp_ms: int
    unix_ts_ms: int
    pulse_raw: int
    gsr_raw: int
    acc_x: int
    acc_y: int
    acc_z: int

    def to_sample(self) -> SensorSample:
        """Convert to the engine-facing SensorSample contract."""
        return SensorSample(
            unix_ts_ms=self.unix_ts_ms,
            bvp=float(self.pulse_raw),
            gsr=self.gsr_raw,
            acc_x=float(self.acc_x),
            acc_y=float(self.acc_y),
            acc_z=float(self.acc_z),
        )


def _parse_csv_row(text: str, arrival_unix_ms: int) -> SensorRow | None:
    """Parse a firmware row (7 ints) or a serial_reader row (8 ints, with recorded unix_ts_ms)."""
    try:
        values = [int(part) for part in text.split(",")]
    except ValueError:
        return None
    if len(values) == _FIRMWARE_FIELD_COUNT:
        idx, ts_ms, pulse, gsr, acc_x, acc_y, acc_z = values
        return SensorRow(idx, ts_ms, arrival_unix_ms, pulse, gsr, acc_x, acc_y, acc_z)
    if len(values) == _RECORDED_FIELD_COUNT:
        idx, ts_ms, unix_ts, pulse, gsr, acc_x, acc_y, acc_z = values
        return SensorRow(idx, ts_ms, unix_ts, pulse, gsr, acc_x, acc_y, acc_z)
    return None


def _json_int(value: object) -> int | None:
    """Return a finite JSON number as an int, or None for anything else (including booleans)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    return round(value)


def _parse_json_row(text: str, arrival_unix_ms: int) -> SensorRow | None:
    """Parse a JSON object row. Unknown keys (for example a firmware-side heart rate) are ignored."""
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    fields: dict[str, int] = {}
    for name, aliases in _JSON_ALIASES.items():
        parsed = next((_json_int(obj[alias]) for alias in aliases if alias in obj), None)
        if parsed is None:
            if name not in _JSON_OPTIONAL_DEFAULTS:
                return None
            parsed = _JSON_OPTIONAL_DEFAULTS[name]
        fields[name] = parsed
    recorded_unix = _json_int(obj.get("unix_ts_ms"))
    return SensorRow(
        sample_idx=fields["sample_idx"],
        timestamp_ms=fields["timestamp_ms"],
        unix_ts_ms=recorded_unix if recorded_unix is not None else arrival_unix_ms,
        pulse_raw=fields["pulse_raw"],
        gsr_raw=fields["gsr_raw"],
        acc_x=fields["acc_x"],
        acc_y=fields["acc_y"],
        acc_z=fields["acc_z"],
    )


def parse_sensor_line(line: str, arrival_unix_ms: int) -> SensorRow | None:
    """Parse one stream line (firmware CSV, recorded CSV, or JSON object). Return None if malformed."""
    text = line.strip()
    if not text or text.startswith("#"):
        return None
    if text.startswith("{"):
        return _parse_json_row(text, arrival_unix_ms)
    return _parse_csv_row(text, arrival_unix_ms)


class StreamBridge:
    """Thread-safe latest-sample buffer and rolling accelerometer window shared by the stream bridges."""

    def __init__(self, clock_ms: Callable[[], int] | None = None) -> None:
        """Initialize the buffer. clock_ms is injectable so tests control time."""
        self._clock_ms: Callable[[], int] = clock_ms if clock_ms is not None else wall_ms
        self._lock: threading.Lock = threading.Lock()
        self._latest: SensorSample | None = None
        self._has_unread: bool = False
        self._window: deque[tuple[int, float]] = deque()
        self._last_arrival_ms: int | None = None
        self._last_sample_idx: int | None = None
        self.rows_ingested: int = 0
        self.rows_rejected: int = 0
        self.gap_events: int = 0

    def _prune(self, now_ms: int) -> None:
        """Drop window entries older than the variance window. Caller holds the lock."""
        cutoff = now_ms - BRIDGE_VARIANCE_WINDOW_MS
        while self._window and self._window[0][0] < cutoff:
            self._window.popleft()

    def _ingest(self, row: SensorRow, arrival_ms: int) -> None:
        """Store a validated row as the latest sample and add its magnitude to the rolling window."""
        magnitude = math.sqrt(row.acc_x**2 + row.acc_y**2 + row.acc_z**2)
        with self._lock:
            if self._last_sample_idx is not None and row.sample_idx >= 0 and row.sample_idx - self._last_sample_idx != 1:
                self.gap_events += 1
            self._last_sample_idx = row.sample_idx
            self._latest = row.to_sample()
            self._has_unread = True
            self._last_arrival_ms = arrival_ms
            self._window.append((arrival_ms, magnitude))
            self._prune(arrival_ms)
            self.rows_ingested += 1

    def get_latest_sample(self) -> SensorSample | None:
        """Return the most recent unread sample, or None if nothing new has arrived."""
        with self._lock:
            if not self._has_unread:
                return None
            self._has_unread = False
            return self._latest

    def get_mpu_variance(self) -> float | None:
        """Return the 1 s rolling variance of acceleration magnitude, or None when telemetry is absent or stale."""
        now_ms = self._clock_ms()
        with self._lock:
            if self._last_arrival_ms is None or now_ms - self._last_arrival_ms > BRIDGE_STALE_AFTER_MS:
                return None
            self._prune(now_ms)
            magnitudes = [magnitude for _, magnitude in self._window]
        if len(magnitudes) < BRIDGE_MIN_WINDOW_SAMPLES:
            return None
        mean = sum(magnitudes) / len(magnitudes)
        return sum((magnitude - mean) ** 2 for magnitude in magnitudes) / len(magnitudes)

    def close(self) -> None:
        """Release resources. Subclasses extend this."""
