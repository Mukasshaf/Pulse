"""
Task 1 — Peak Detection Validation
===================================
Standalone validation script — does NOT import from src/.
File: recorded_data_35s.csv
fs:   66.67 Hz  (SAMPLE_INTERVAL_MS=15 -> 1000/15)

Acceptance criteria:
  - >=95% of IBIs fall in 400-1500 ms
  - Mean BPM in 50-100 range
  - No manual parameter overrides used (nk defaults throughout)
"""

import sys
import numpy as np
import pandas as pd
import neurokit2 as nk

FS  = 1000.0 / 15.0   # 66.67 Hz -- actual hardware rate
CSV = "../data/hardware/raw/M2_tests/recorded_data_35s.csv"


def run() -> dict:
    df = pd.read_csv(CSV)
    raw = df["pulse_raw"].values.astype(float)
    duration_s = (df["timestamp_ms"].iloc[-1] - df["timestamp_ms"].iloc[0]) / 1000.0

    # Step 1: clean -- neurokit2 defaults, zero manual tuning
    clean = nk.ppg_clean(raw, sampling_rate=FS)

    # Step 2: find peaks -- neurokit2 defaults
    peaks_info = nk.ppg_findpeaks(clean, sampling_rate=FS)
    peak_idx   = peaks_info["PPG_Peaks"]

    if len(peak_idx) < 2:
        return {
            "status": "FAIL",
            "reason": "fewer than 2 peaks detected -- cannot compute IBI",
            "file":   CSV,
        }

    # Step 3: IBI series (ms)
    ibi_ms = np.diff(peak_idx) / FS * 1000.0

    # Step 4: acceptance gates
    mask_valid  = (ibi_ms >= 400) & (ibi_ms <= 1500)
    pct_valid   = mask_valid.sum() / len(ibi_ms) * 100.0
    valid_ibi   = ibi_ms[mask_valid]

    if len(valid_ibi) == 0:
        mean_bpm = float("nan")
        ibi_cv   = float("nan")
    else:
        mean_bpm = 60000.0 / float(np.mean(valid_ibi))
        ibi_cv   = float(np.std(valid_ibi) / np.mean(valid_ibi))

    gate_ibi = pct_valid >= 95.0
    gate_bpm = 50.0 <= mean_bpm <= 100.0
    passed   = gate_ibi and gate_bpm

    return {
        "status":          "PASS" if passed else "FAIL",
        "file":            CSV,
        "fs_hz":           round(FS, 4),
        "duration_s":      round(duration_s, 3),
        "total_samples":   len(raw),
        "peak_count":      int(len(peak_idx)),
        "ibi_count":       int(len(ibi_ms)),
        "ibi_min_ms":      round(float(ibi_ms.min()), 1),
        "ibi_max_ms":      round(float(ibi_ms.max()), 1),
        "ibi_mean_ms":     round(float(np.mean(ibi_ms)), 1),
        "ibi_std_ms":      round(float(np.std(ibi_ms)), 1),
        "ibi_cv":          round(ibi_cv, 4) if not np.isnan(ibi_cv) else "nan",
        "pct_valid_ibi":   round(pct_valid, 2),
        "mean_bpm":        round(mean_bpm, 2) if not np.isnan(mean_bpm) else "nan",
        "gate_ibi_pass":   gate_ibi,
        "gate_bpm_pass":   gate_bpm,
        "manual_tuning":   False,
    }


if __name__ == "__main__":
    print(f"\n{'='*55}")
    print(f"  Task 1 -- Peak Detection Validation")
    print(f"{'='*55}")
    result = run()
    for k, v in result.items():
        print(f"  {k:<22}  {v}")
    print(f"\n  STATUS: {result['status']}")
    sys.exit(0 if result["status"] == "PASS" else 1)
