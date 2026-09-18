"""
align_signals.py -- Post-session alignment bridge.

Joins hardware sensor CSV (from serial_reader.py) and game event CSV
(from src/game/event_logger.py) on `unix_ts_ms`.

Pipeline contract columns joined:
    unix_ts_ms, event_type, domain, scenario_id, choice_data

Behavioral columns preserved:
    key_pressed, option_index, response_time_ms, metadata
"""

import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Pulse post-session signal alignment")
    parser.add_argument("--subject", required=True, help="Subject ID (e.g., HW01)")
    parser.add_argument("--sensor-csv", help="Path to hardware raw sensor CSV")
    parser.add_argument("--events-csv", help="Path to game events CSV")
    parser.add_argument("--out-dir", default="outputs/aligned", help="Output directory")
    args = parser.parse_args()

    print(f"align_signals placeholder for subject {args.subject}")


if __name__ == "__main__":
    main()
