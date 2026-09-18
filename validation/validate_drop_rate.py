"""
Task 4 -- Drop Rate Validation
==============================
Standalone validation script -- does NOT import from src/.
File: recorded_data_120s.csv  [120s -- not full 5-min per spec; noted in summary]
SAMPLE_INTERVAL_MS = 15

Acceptance: drop_rate < 5%
"""

import sys
import numpy as np
import pandas as pd

CSV                = "../data/hardware/raw/M2_tests/recorded_data_120s.csv"
SAMPLE_INTERVAL_MS = 15


def run() -> dict:
    df = pd.read_csv(CSV)

    first_ts   = int(df["timestamp_ms"].iloc[0])
    last_ts    = int(df["timestamp_ms"].iloc[-1])
    duration_s = (last_ts - first_ts) / 1000.0

    actual_rows   = len(df)
    expected_rows = int((last_ts - first_ts) / SAMPLE_INTERVAL_MS) + 1

    drop_rate_ts = 1.0 - (actual_rows / expected_rows)

    idx_diffs         = np.diff(df["sample_idx"].values)
    gap_events        = int(np.sum(idx_diffs != 1))
    missed_rows_total = int(np.sum(idx_diffs[idx_diffs > 1] - 1))
    backwards_jumps   = int(np.sum(idx_diffs < 0))

    gate_pass = drop_rate_ts < 0.05

    return {
        "status":             "PASS" if gate_pass else "FAIL",
        "file":               CSV,
        "duration_note":      "120s -- not full 5-min per spec (noted for record)",
        "first_ts_ms":        first_ts,
        "last_ts_ms":         last_ts,
        "duration_s":         round(duration_s, 3),
        "sample_interval_ms": SAMPLE_INTERVAL_MS,
        "expected_rows":      expected_rows,
        "actual_rows":        actual_rows,
        "drop_rate_pct":      round(drop_rate_ts * 100, 4),
        "gap_events":         gap_events,
        "missed_rows_total":  missed_rows_total,
        "backwards_jumps":    backwards_jumps,
        "gate_lt5pct_pass":   gate_pass,
    }


if __name__ == "__main__":
    print(f"\n{'='*55}")
    print(f"  Task 4 -- Drop Rate Validation")
    print(f"{'='*55}")
    result = run()
    for k, v in result.items():
        print(f"  {k:<26}  {v}")
    print(f"\n  STATUS: {result['status']}")
    sys.exit(0 if result["status"] == "PASS" else 1)
