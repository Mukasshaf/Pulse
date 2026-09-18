"""Unit tests for CSV event logging, thread safety, and session metadata."""
from __future__ import annotations

import csv
import json
import threading
import time
from pathlib import Path

from src.game.constants import DomainID, EventType
from src.game.event_logger import EventLogger, GameEvent


def test_logger_initialization_and_header(tmp_output: Path) -> None:
    """Verify CSV creation and 9-column schema compliance."""
    logger = EventLogger(tmp_output, "S01")
    logger.close()

    csv_path = tmp_output / "events.csv"
    assert csv_path.is_file()

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == [
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


def test_single_and_multi_event_logging(tmp_output: Path) -> None:
    """Verify row formatting, empty numerics, and metadata JSON serialization."""
    logger = EventLogger(tmp_output, "S02")
    now = int(time.time_ns() // 1_000_000)

    # Event with None fields
    evt1 = GameEvent(
        unix_ts_ms=now,
        event_type=EventType.BASELINE_START,
        domain="",
        scenario_id="",
        choice_data="{}",
        key_pressed=None,
        option_index=None,
        response_time_ms=None,
        metadata={},
    )
    logger.log_event(evt1)

    # Event with full fields
    evt2 = GameEvent(
        unix_ts_ms=now + 500,
        event_type=EventType.OPTION_SELECTED,
        domain="academic_pressure",
        scenario_id="academic_pressure_b",
        choice_data='{"key": 1}',
        key_pressed=1,
        option_index=0,
        response_time_ms=452,
        metadata={"tested": True, "value": 12.5},
    )
    logger.log_event(evt2)
    logger.close()

    lines = (tmp_output / "events.csv").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3

    with open(tmp_output / "events.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert rows[0]["event_type"] == "BASELINE_START"
    assert rows[0]["key_pressed"] == ""
    assert rows[0]["metadata"] == "{}"

    assert rows[1]["event_type"] == "OPTION_SELECTED"
    assert rows[1]["key_pressed"] == "1"
    meta = json.loads(rows[1]["metadata"])
    assert meta["tested"] is True
    assert meta["value"] == 12.5


def test_domain_order_json(tmp_output: Path) -> None:
    """Verify domain_order.json structure and contents."""
    logger = EventLogger(tmp_output, "S03")
    order = list(DomainID)
    logger.save_domain_order(order, seed=12345, start_ms=1700000000000)
    logger.close()

    order_file = tmp_output / "domain_order.json"
    assert order_file.is_file()

    data = json.loads(order_file.read_text(encoding="utf-8"))
    assert data["subject_id"] == "S03"
    assert data["random_seed"] == 12345
    assert len(data["domain_order"]) == 7


def test_thread_safety(tmp_output: Path) -> None:
    """Verify concurrent writes from 10 threads do not corrupt CSV integrity."""
    logger = EventLogger(tmp_output, "S04")
    threads: list[threading.Thread] = []

    def writer_task(thread_id: int) -> None:
        for i in range(10):
            logger.log_event(
                GameEvent(
                    unix_ts_ms=int(time.time_ns() // 1_000_000),
                    event_type=EventType.MATH_ANSWER,
                    domain="test",
                    scenario_id="test",
                    choice_data="{}",
                    key_pressed=thread_id,
                    option_index=i,
                    response_time_ms=100,
                    metadata={"thread": thread_id},
                )
            )

    for tid in range(10):
        t = threading.Thread(target=writer_task, args=(tid,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    logger.close()

    lines = (tmp_output / "events.csv").read_text(encoding="utf-8").strip().split("\n")
    # 1 header + 100 rows
    assert len(lines) == 101
