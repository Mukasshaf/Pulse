"""align_signals.py -- Post-session alignment bridge.

Joins hardware sensor CSV (from serial_reader.py) and game event CSV
(from src/game/event_logger.py) on `unix_ts_ms`.

Pipeline contract columns joined:
    unix_ts_ms, event_type, domain, scenario_id, choice_data

Behavioral columns preserved:
    key_pressed, option_index, response_time_ms, metadata
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any


def align_sensor_and_events(
    sensor_csv_path: Path,
    events_csv_path: Path,
    output_csv_path: Path,
) -> int:
    """Join sensor data rows with concurrent game session events based on unix_ts_ms.

    Args:
        sensor_csv_path: Path to raw hardware CSV from serial_reader.py
        events_csv_path: Path to session event log CSV from event_logger.py
        output_csv_path: Destination path for aligned labeled dataset

    Returns:
        Number of aligned sensor rows written.
    """
    if not sensor_csv_path.exists():
        raise FileNotFoundError(f"Sensor CSV not found: {sensor_csv_path}")
    if not events_csv_path.exists():
        raise FileNotFoundError(f"Events CSV not found: {events_csv_path}")

    # Read all events sorted by timestamp
    events: list[dict[str, Any]] = []
    with open(events_csv_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            events.append({
                "unix_ts_ms": int(row["unix_ts_ms"]),
                "event_type": row.get("event_type", ""),
                "domain": row.get("domain", ""),
                "scenario_id": row.get("scenario_id", ""),
                "choice_data": row.get("choice_data", ""),
            })

    events.sort(key=lambda x: x["unix_ts_ms"])

    # Read sensor rows and tag with active scenario/domain state
    rows_written = 0
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(sensor_csv_path, mode="r", encoding="utf-8", newline="") as sf, \
         open(output_csv_path, mode="w", encoding="utf-8", newline="") as out_f:
        sensor_reader = csv.DictReader(sf)
        if not sensor_reader.fieldnames:
            return 0

        fieldnames = list(sensor_reader.fieldnames) + [
            "active_domain",
            "active_scenario",
            "last_event_type",
        ]
        writer = csv.DictWriter(out_f, fieldnames=fieldnames)
        writer.writeheader()

        current_domain = ""
        current_scenario = ""
        last_event = ""
        event_idx = 0
        num_events = len(events)

        for s_row in sensor_reader:
            s_ts = int(s_row["unix_ts_ms"])

            # Advance events that occurred before or at this sensor timestamp
            while event_idx < num_events and events[event_idx]["unix_ts_ms"] <= s_ts:
                ev = events[event_idx]
                last_event = ev["event_type"]
                if ev["domain"]:
                    current_domain = ev["domain"]
                if ev["scenario_id"]:
                    current_scenario = ev["scenario_id"]
                if ev["event_type"] in ("REST_START", "REST_END", "BASELINE_START", "BASELINE_END"):
                    if "REST" in ev["event_type"]:
                        current_domain = "rest"
                        current_scenario = ""
                    elif "BASELINE" in ev["event_type"]:
                        current_domain = "baseline"
                        current_scenario = ""
                event_idx += 1

            s_row["active_domain"] = current_domain
            s_row["active_scenario"] = current_scenario
            s_row["last_event_type"] = last_event
            writer.writerow(s_row)
            rows_written += 1

    return rows_written


def main() -> None:
    """CLI entry point for signal alignment."""
    parser = argparse.ArgumentParser(description="Pulse post-session signal alignment")
    parser.add_argument("--subject", help="Subject ID (e.g., HW01)")
    parser.add_argument("--sensor-csv", type=Path, help="Path to hardware raw sensor CSV")
    parser.add_argument("--events-csv", type=Path, help="Path to game events CSV")
    parser.add_argument("--output-csv", type=Path, help="Explicit path for aligned output CSV")
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/aligned"), help="Output directory")

    args = parser.parse_args()

    sensor_path = args.sensor_csv
    events_path = args.events_csv
    out_path = args.output_csv

    if args.subject and not sensor_path:
        sensor_path = Path(f"data/hardware/raw/{args.subject}/recorded_data.csv")
    if args.subject and not events_path:
        events_path = Path(f"data/game_logs/{args.subject}/events.csv")
    if not out_path:
        subj = args.subject or "aligned"
        out_path = args.out_dir / f"{subj}_aligned.csv"

    if not sensor_path or not events_path:
        print("Error: Must specify either --subject or both --sensor-csv and --events-csv", file=sys.stderr)
        sys.exit(1)

    written = align_sensor_and_events(sensor_path, events_path, out_path)
    print(f"Successfully aligned and wrote {written} rows to {out_path}")


if __name__ == "__main__":
    main()
