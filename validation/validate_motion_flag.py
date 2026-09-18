"""
Task 3 -- Motion Artifact Flagging Validation
=============================================
Standalone validation script -- does NOT import from src/.

STATUS: NOT RUN
  All available recordings (20s/35s/60s/90s/120s) captured while
  stationary -- no keyboard/mouse/movement. No motion segment exists.

TO ACTIVATE when a motion capture is available:
  1. Set NOT_RUN = False
  2. Set CSV to the new motion-capture file
  3. Set TAP_START_S and TAP_END_S to tap window boundaries
  4. Re-run

Detection logic (mu+2sigma pattern -- project standard):
  - ACC magnitude sqrt(x2+y2+z2), de-meaned
  - Rolling 1s std
  - Baseline mu, sigma from first 20s
  - Threshold = mu_rest + 2*sigma_rest
  - PASS: >=1 tap window flagged AND 0 false positives in rest segments
"""

import sys
import numpy as np
import pandas as pd

# --- Configuration ---
NOT_RUN     = True
CSV         = "../data/hardware/raw/M2_tests/recorded_data_90s.csv"
TAP_START_S = 35.0
TAP_END_S   = 45.0
FS          = 1000.0 / 15.0   # 66.67 Hz


def _detect(csv, tap_start_s, tap_end_s) -> dict:
    df  = pd.read_csv(csv)
    acc = df[["acc_x", "acc_y", "acc_z"]].values.astype(float)
    duration_s = (df["timestamp_ms"].iloc[-1] - df["timestamp_ms"].iloc[0]) / 1000.0

    mag  = np.sqrt(np.sum(acc ** 2, axis=1))
    mag -= np.mean(mag)

    win_n     = int(FS)
    n_windows = len(mag) // win_n
    roll_std  = np.array([np.std(mag[i * win_n : (i + 1) * win_n])
                          for i in range(n_windows)])
    win_times = np.arange(n_windows) * 1.0

    rest_n    = min(20, n_windows)
    rest_stds = roll_std[:rest_n]
    rest_mu   = float(np.mean(rest_stds))
    rest_sig  = float(np.std(rest_stds))
    threshold = rest_mu + 2.0 * rest_sig

    flags = roll_std > threshold

    tap_idx   = np.where((win_times >= tap_start_s) & (win_times < tap_end_s))[0]
    rest_idx  = np.where(
        (win_times < tap_start_s - 5.0) | (win_times >= tap_end_s + 5.0)
    )[0]

    tap_flags  = int(np.sum(flags[tap_idx]))  if len(tap_idx)  > 0 else 0
    rest_flags = int(np.sum(flags[rest_idx])) if len(rest_idx) > 0 else 0

    gate_tap  = tap_flags  >= 1
    gate_rest = rest_flags == 0
    passed    = gate_tap and gate_rest

    return {
        "status":              "PASS" if passed else "FAIL",
        "file":                csv,
        "duration_s":          round(duration_s, 3),
        "n_windows_1s":        n_windows,
        "rest_baseline_mu":    round(rest_mu, 4),
        "rest_baseline_sig":   round(rest_sig, 4),
        "threshold_mu2sig":    round(threshold, 4),
        "tap_window_s":        f"{tap_start_s}-{tap_end_s}",
        "tap_windows_n":       len(tap_idx),
        "tap_windows_flagged": tap_flags,
        "rest_windows_n":      len(rest_idx),
        "rest_false_positives":rest_flags,
        "gate_tap_detected":   gate_tap,
        "gate_no_fp":          gate_rest,
    }


def run() -> dict:
    if NOT_RUN:
        return {
            "status":           "NOT RUN",
            "reason":           "All captures resting-only -- no motion segment in available data",
            "required_capture": "~20s rest -> ~10s tap/keyboard -> ~20s rest",
            "how_to_activate":  "Set NOT_RUN=False, set CSV, TAP_START_S, TAP_END_S",
            "script_ready":     True,
        }
    return _detect(CSV, TAP_START_S, TAP_END_S)


if __name__ == "__main__":
    print(f"\n{'='*55}")
    print(f"  Task 3 -- Motion Artifact Flagging")
    print(f"{'='*55}")
    result = run()
    for k, v in result.items():
        print(f"  {k:<28}  {v}")
    print(f"\n  STATUS: {result['status']}")
    sys.exit(0)
