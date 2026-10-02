"""Replay bridge for the Pulse engine: paced playback of a recorded sensor CSV, or live follow of a growing one."""
from __future__ import annotations

import contextlib
import threading
from collections.abc import Callable
from pathlib import Path
from typing import IO

from src.game.constants import BridgeUnavailableError
from src.game.sensor_stream import (
    POLL_IDLE_S,
    SensorRow,
    StreamBridge,
    parse_sensor_line,
)


def load_recorded_rows(source: Path) -> list[SensorRow]:
    """Load every valid row from a firmware-format or serial_reader-format CSV."""
    rows: list[SensorRow] = []
    with open(source, encoding="utf-8") as handle:
        for line in handle:
            row = parse_sensor_line(line, 0)
            if row is not None:
                rows.append(row)
    return rows


def _row_time_ms(row: SensorRow) -> int:
    """Return the timeline position of a recorded row (host clock if present, else device clock)."""
    return row.unix_ts_ms if row.unix_ts_ms > 0 else row.timestamp_ms


class ReplayBridge(StreamBridge):
    """Feeds the engine from a sensor CSV: paced replay of a recording, or live follow of a growing file."""

    def __init__(self, source: Path, follow: bool = False, clock_ms: Callable[[], int] | None = None) -> None:
        """Open the source. follow=True tails rows that serial_reader.py appends from now on."""
        super().__init__(clock_ms)
        self.source: Path = source
        self.follow: bool = follow
        self._rows: list[SensorRow] = [] if follow else load_recorded_rows(source)
        self._cursor: int = 0
        self._origin_ms: int | None = None
        self._stop: threading.Event = threading.Event()
        self._thread: threading.Thread | None = None
        self._closed: bool = False
        self._follow_file: IO[str] | None = None
        self._follow_stack: contextlib.ExitStack[bool | None] = contextlib.ExitStack()
        if follow:
            with contextlib.ExitStack() as stack:
                handle = stack.enter_context(open(source, encoding="utf-8"))
                handle.seek(0, 2)  # only rows written after the game starts are live
                self._follow_file = handle
                self._follow_stack = stack.pop_all()

    def advance(self) -> int:
        """Replay mode: ingest every recorded row that is due by now. Return how many were ingested."""
        if self.follow or not self._rows:
            return 0
        now_ms = self._clock_ms()
        if self._origin_ms is None:
            self._origin_ms = now_ms
        start_time_ms = _row_time_ms(self._rows[0])
        ingested = 0
        while self._cursor < len(self._rows):
            row = self._rows[self._cursor]
            due_ms = self._origin_ms + (_row_time_ms(row) - start_time_ms)
            if due_ms > now_ms:
                break
            self._ingest(row, due_ms)
            self._cursor += 1
            ingested += 1
        return ingested

    def poll_follow(self) -> int:
        """Follow mode: ingest every complete line appended since the last poll. Return how many."""
        if self._follow_file is None:
            return 0
        ingested = 0
        while True:
            position = self._follow_file.tell()
            line = self._follow_file.readline()
            if not line:
                break
            if not line.endswith("\n"):
                self._follow_file.seek(position)  # partial row: wait for the writer to finish it
                break
            row = parse_sensor_line(line, self._clock_ms())
            if row is None:
                self.rows_rejected += 1
                continue
            self._ingest(row, self._clock_ms())
            ingested += 1
        return ingested

    def is_finished(self) -> bool:
        """Return True once a non-follow replay has emitted every row."""
        return not self.follow and self._cursor >= len(self._rows)

    def _run(self) -> None:
        """Background loop: pace the replay or tail the file until stopped."""
        while not self._stop.is_set() and not self.is_finished():
            if self.follow:
                self.poll_follow()
            else:
                self.advance()
            self._stop.wait(POLL_IDLE_S)

    def start(self) -> None:
        """Start the background feeder thread. Idempotent."""
        if self._thread is None and not self._closed:
            self._thread = threading.Thread(target=self._run, name="pulse-replay-bridge", daemon=True)
            self._thread.start()

    def close(self) -> None:
        """Stop the feeder and release the file. Idempotent."""
        if self._closed:
            return
        self._closed = True
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._follow_stack.close()


def resolve_replay_source(source: Path) -> Path:
    """Return the CSV to replay. A directory resolves to its newest recording."""
    if source.is_file():
        return source
    if source.is_dir():
        candidates = sorted(source.glob("recorded_*.csv")) or sorted(source.glob("*.csv"))
        if candidates:
            return max(candidates, key=lambda path: path.stat().st_mtime)
        raise BridgeUnavailableError(f"no sensor CSV found in {source}")
    raise BridgeUnavailableError(f"replay source does not exist: {source}")
