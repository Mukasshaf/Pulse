"""
condition_logger.py -- logs condition-transition timestamps for the Phase 3.1
protocol, using the same unix_ts_ms clock reference that serial_reader.py
already writes.

Durations are fixed per workplan 3.1:
    3 min baseline -> 3 min mental arithmetic -> 2 min Stroop
No per-transition manual timing needed. The print() at each transition is
the operator cue to verbally instruct the participant.

Usage:
    # Terminal 1 -- start sensor recording
    python src/serial_reader.py --port /dev/ttyUSB0 --subject HW01

    # Terminal 2 -- start condition logger at the same moment
    python src/condition_logger.py HW01

    Both write unix_ts_ms-aligned timestamps. hardware_loader.py joins
    them on that shared clock to assign per-row condition labels.

Output CSV schema:
    condition, start_unix_ms, end_unix_ms
"""

import time
import csv
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from condition_labels import CONDITION_DURATION_S, CONDITION_LABELS


def run_session(subject_id: str, output_path: str) -> None:
    """
    Run the fixed 3.1 protocol schedule, printing operator cues at each
    transition and writing a condition log CSV on completion.

    Args:
        subject_id:   Subject identifier string, e.g. "HW01".
        output_path:  Path where the condition log CSV will be written.
    """
    rows: list[tuple[str, str | int, str | int]] = [("condition", "start_unix_ms", "end_unix_ms")]
    t_ms = int(time.time() * 1000)

    print(f"\n[condition_logger] Subject: {subject_id}")
    print(f"[condition_logger] Total session: "
          f"{sum(CONDITION_DURATION_S.values())}s "
          f"({sum(CONDITION_DURATION_S.values())//60} min)\n")

    for condition in CONDITION_LABELS:
        duration_s = CONDITION_DURATION_S[condition]
        end_ms = t_ms + duration_s * 1000

        print(f">>> [{condition.upper()}] — starts NOW. "
              f"Duration: {duration_s}s ({duration_s//60}m {duration_s%60}s). "
              f"Cue the participant.")

        rows.append((condition, t_ms, end_ms))

        # Block until this condition's window closes
        target = time.time() + duration_s
        while time.time() < target:
            remaining = target - time.time()
            # Print countdown every 30s without blocking the sleep loop
            if remaining % 30 < 0.1 and remaining > 5:
                print(f"    [{condition}] {int(remaining)}s remaining ...")
            time.sleep(0.05)

        t_ms = end_ms
        print(f"    [{condition}] DONE.\n")

    # Write output
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", newline="") as f:
        csv.writer(f).writerows(rows)

    print(f"[condition_logger] Session complete.")
    print(f"[condition_logger] Condition log written -> {output_path}")


if __name__ == "__main__":
    subject_id  = sys.argv[1] if len(sys.argv) > 1 else "HW01"
    out_dir     = sys.argv[2] if len(sys.argv) > 2 else "outputs/condition_logs"
    output_path = os.path.join(out_dir, f"condition_log_{subject_id}.csv")
    run_session(subject_id, output_path)
