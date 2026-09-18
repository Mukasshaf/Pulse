"""Thread-safe CSV event logger and session metadata manager for Pulse."""
from __future__ import annotations

import csv
import json
import threading
from dataclasses import dataclass
from pathlib import Path

from src.game.constants import DomainID, EventType, LoggerIOError


@dataclass
class GameEvent:
    """Represents a discrete behavioral or system event during a session."""

    unix_ts_ms: int
    event_type: EventType
    domain: str
    scenario_id: str
    choice_data: str
    key_pressed: int | None
    option_index: int | None
    response_time_ms: int | None
    metadata: dict[str, str | int | float | bool]


class EventLogger:
    """Thread-safe writer for structured event CSV logs and session metadata."""

    CSV_COLUMNS: list[str] = [
        "unix_ts_ms",
        "event_type",
        "domain",
        "scenario_id",
        "choice_data",
        "key_pressed",
        "option_index",
        "response_time_ms",
        "metadata",
    ]

    def __init__(self, output_dir: Path, subject_id: str) -> None:
        """Create output directory if needed and open CSV with header."""
        self.output_dir: Path = output_dir
        self.subject_id: str = subject_id
        self._lock: threading.Lock = threading.Lock()
        self._closed: bool = False

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self._csv_path: Path = self.output_dir / "events.csv"
            self._file = open(self._csv_path, mode="w", newline="", encoding="utf-8")
            self._writer = csv.writer(
                self._file,
                delimiter=",",
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL,
                lineterminator="\n",
            )
            self._writer.writerow(self.CSV_COLUMNS)
            self._file.flush()
        except OSError as exc:
            raise LoggerIOError(str(self.output_dir), str(exc)) from exc

    def log_event(self, event: GameEvent) -> None:
        """Write one CSV row and immediately flush to disk. Thread-safe."""
        with self._lock:
            if self._closed:
                return

            metadata_json = (
                json.dumps(event.metadata)
                if event.metadata
                else "{}"
            )
            choice_data = event.choice_data if event.choice_data else "{}"
            key_pressed_str = (
                str(event.key_pressed) if event.key_pressed is not None else ""
            )
            option_idx_str = (
                str(event.option_index) if event.option_index is not None else ""
            )
            rt_str = (
                str(event.response_time_ms)
                if event.response_time_ms is not None
                else ""
            )

            row = [
                str(event.unix_ts_ms),
                event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type),
                event.domain,
                event.scenario_id,
                choice_data,
                key_pressed_str,
                option_idx_str,
                rt_str,
                metadata_json,
            ]

            try:
                self._writer.writerow(row)
                self._file.flush()
            except OSError as exc:
                raise LoggerIOError(str(self._csv_path), str(exc)) from exc

    def save_domain_order(
        self, order: list[DomainID], seed: int, start_ms: int
    ) -> None:
        """Save the randomized domain sequence to domain_order.json."""
        with self._lock:
            target_path = self.output_dir / "domain_order.json"
            domain_values = [d.value if hasattr(d, "value") else str(d) for d in order]
            payload: dict[str, str | int | list[str]] = {
                "subject_id": self.subject_id,
                "session_start_unix_ts_ms": start_ms,
                "random_seed": seed,
                "domain_order": domain_values,
            }
            try:
                target_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            except OSError as exc:
                raise LoggerIOError(str(target_path), str(exc)) from exc

    def close(self) -> None:
        """Flush and close the CSV file handle. Idempotent."""
        with self._lock:
            if not self._closed:
                try:
                    self._file.flush()
                    self._file.close()
                except OSError:
                    pass
                finally:
                    self._closed = True
