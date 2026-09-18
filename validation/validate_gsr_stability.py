"""
Task 2 -- GSR Stability Validation (>=60s)
==========================================
Standalone validation script -- does NOT import from src/.
File: recorded_data_60s.csv

Acceptance criteria:
  - No sustained drop >50% of baseline mean lasting >30s
  - No saturation at ADC limits: 0 or 4095
"""

import sys
import numpy as np
import pandas as pd

FS  = 1000.0 / 15.0   # 66.67 Hz
CSV = "../data/hardware/raw/M2_tests/recorded_data_60s.csv"


def _longest_run(mask) -> int:
    max_run = cur = 0
    for b in mask:
        if b:
            cur += 1
            max_run = max(max_run, cur)
        else:
            cur = 0
    return max_run


def run() -> dict:
    df  = pd.read_csv(CSV)
    gsr = df["gsr_raw"].values.astype(float)
    duration_s = (df["timestamp_ms"].iloc[-1] - df["timestamp_ms"].iloc[0]) / 1000.0

    overall_std  = float(np.std(gsr))
    overall_mean = float(np.mean(gsr))
    gsr_range    = float(gsr.max() - gsr.min())
    gsr_min      = float(gsr.min())
    gsr_max      = float(gsr.max())

    # Baseline = first 10s
    baseline_n    = int(FS * 10)
    baseline_mean = float(np.mean(gsr[:baseline_n]))

    # Rolling 1s std
    win_n        = int(FS)
    windows      = [gsr[i : i + win_n] for i in range(0, len(gsr) - win_n, win_n)]
    rolling_std  = [float(np.std(w)) for w in windows]
    max_roll_std = float(max(rolling_std))
    mean_roll_std= float(np.mean(rolling_std))

    # Single-sample jump >20% of full range
    diffs        = np.abs(np.diff(gsr))
    jump_thresh  = 0.20 * gsr_range
    big_jumps    = int(np.sum(diffs > jump_thresh))
    max_jump     = float(diffs.max())

    # Saturation
    sat_0    = int(np.sum(gsr == 0))
    sat_4095 = int(np.sum(gsr == 4095))
    saturation = (sat_0 > 0) or (sat_4095 > 0)

    # Sustained dropout
    dropout_thresh  = 0.50 * baseline_mean
    below_thresh    = gsr < dropout_thresh
    longest_run_smp = _longest_run(below_thresh)
    max_dropout_s   = longest_run_smp / FS
    sustained_dropout = max_dropout_s > 30.0

    gate_dropout = not sustained_dropout
    gate_sat     = not saturation
    passed       = gate_dropout and gate_sat

    return {
        "status":              "PASS" if passed else "FAIL",
        "file":                CSV,
        "fs_hz":               round(FS, 4),
        "duration_s":          round(duration_s, 3),
        "total_samples":       len(gsr),
        "overall_mean":        round(overall_mean, 2),
        "overall_std":         round(overall_std, 2),
        "gsr_range":           round(gsr_range, 1),
        "gsr_min":             round(gsr_min, 1),
        "gsr_max":             round(gsr_max, 1),
        "baseline_mean_10s":   round(baseline_mean, 2),
        "max_rolling_1s_std":  round(max_roll_std, 2),
        "mean_rolling_1s_std": round(mean_roll_std, 2),
        "big_jumps_gt20pct":   big_jumps,
        "max_single_jump":     round(max_jump, 2),
        "sat_at_0":            sat_0,
        "sat_at_4095":         sat_4095,
        "dropout_50pct_thresh":round(dropout_thresh, 2),
        "max_dropout_run_s":   round(max_dropout_s, 3),
        "gate_dropout_pass":   gate_dropout,
        "gate_sat_pass":       gate_sat,
    }


if __name__ == "__main__":
    print(f"\n{'='*55}")
    print(f"  Task 2 -- GSR Stability Validation")
    print(f"{'='*55}")
    result = run()
    for k, v in result.items():
        print(f"  {k:<26}  {v}")
    print(f"\n  STATUS: {result['status']}")
    sys.exit(0 if result["status"] == "PASS" else 1)
