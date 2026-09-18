

import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wesad_loader import load_subject
from preprocess import preprocess_subject


#  GSR threshold 

def gsr_baseline_stats(preprocessed: dict) -> dict:
    scr    = preprocessed["eda"]["scr"]
    labels = preprocessed["labels"]["eda"]
    baseline_scr = scr[labels == 1]

    if len(baseline_scr) == 0:
        raise ValueError("No baseline EDA samples found for this subject.")

    return {"mu": float(np.mean(baseline_scr)), "sigma": float(np.std(baseline_scr, ddof=1))}


def flag_gsr_events(preprocessed: dict, k: float = 2.0) -> dict:
  
    stats = gsr_baseline_stats(preprocessed)
    threshold = stats["mu"] + k * stats["sigma"]

    scr = preprocessed["eda"]["scr"]
    flags = scr > threshold
    flag_indices = np.where(flags)[0]

    return {"threshold": threshold, "mu": stats["mu"], "sigma": stats["sigma"],
            "flags": flags, "flag_indices": flag_indices}


#  HR threshold 

def hr_baseline_mean(preprocessed: dict) -> float:
    ibi_ms  = preprocessed["peaks"]["ibi_ms"]
    ibi_idx = preprocessed["peaks"]["ibi_idx"]
    labels  = preprocessed["labels"]["bvp"]

    baseline_mask = labels[ibi_idx] == 1
    baseline_ibi  = ibi_ms[baseline_mask]

    if len(baseline_ibi) == 0:
        raise ValueError("No baseline IBI found for this subject.")

    return float(60000.0 / np.mean(baseline_ibi))


def flag_hr_events(preprocessed: dict, pct: float = 0.10,
                   window_s: float = 10.0) -> dict:

    baseline_hr = hr_baseline_mean(preprocessed)
    threshold_hi = baseline_hr * (1 + pct)
    threshold_lo = baseline_hr * (1 - pct)

    fs_bvp  = preprocessed["fs"]["bvp"]
    ibi_ms  = preprocessed["peaks"]["ibi_ms"]
    ibi_idx = preprocessed["peaks"]["ibi_idx"]

    total_s   = len(preprocessed["bvp_clean"]) / fs_bvp
    step_s    = 1.0
    n_windows = int(total_s - window_s)

    window_times = []
    window_hr    = []
    flags        = []

    ibi_time = ibi_idx / fs_bvp   # seconds

    for i in range(max(n_windows, 0)):
        t0, t1 = i * step_s, i * step_s + window_s
        mask = (ibi_time >= t0) & (ibi_time < t1)
        ibi_w = ibi_ms[mask]

        if len(ibi_w) < 3:
            window_times.append(t0)
            window_hr.append(np.nan)
            flags.append(False)
            continue

        hr = 60000.0 / np.mean(ibi_w)
        window_times.append(t0)
        window_hr.append(hr)
        flags.append(hr > threshold_hi or hr < threshold_lo)

    return {
        "baseline_hr":  baseline_hr,
        "threshold_hi": threshold_hi,
        "threshold_lo": threshold_lo,
        "window_times": np.array(window_times),
        "window_hr":    np.array(window_hr),
        "flags":        np.array(flags, dtype=bool),
    }


# Onset latency validation 

def find_condition_onset(preprocessed: dict, signal: str = "eda",
                         condition: int = 2) -> float:
    labels = preprocessed["labels"][signal]
    fs = preprocessed["fs"][signal]
    idx = np.where(labels == condition)[0]
    if len(idx) == 0:
        raise ValueError(f"Condition {condition} not found in {signal} labels.")
    return idx[0] / fs


def measure_gsr_latency(preprocessed: dict, k: float = 2.0,
                        search_window_s: float = 30.0) -> dict:
   
    onset_s = find_condition_onset(preprocessed, signal="eda", condition=2)
    fs_eda  = preprocessed["fs"]["eda"]

    gsr = flag_gsr_events(preprocessed, k=k)
    onset_idx = int(onset_s * fs_eda)
    search_end_idx = onset_idx + int(search_window_s * fs_eda)

    window_flags = gsr["flags"][onset_idx:search_end_idx]
    flagged = np.where(window_flags)[0]

    if len(flagged) == 0:
        return {"onset_s": onset_s, "latency_s": None, "detected": False}

    latency_s = flagged[0] / fs_eda
    return {"onset_s": onset_s, "latency_s": float(latency_s), "detected": True}


def measure_hr_latency(preprocessed: dict, pct: float = 0.10,
                       search_window_s: float = 30.0) -> dict:
   
    onset_s = find_condition_onset(preprocessed, signal="bvp", condition=2)
    hr = flag_hr_events(preprocessed, pct=pct)

    mask = (hr["window_times"] >= onset_s) & (hr["window_times"] < onset_s + search_window_s)
    flags_in_range = hr["flags"][mask]
    times_in_range = hr["window_times"][mask]

    flagged = np.where(flags_in_range)[0]
    if len(flagged) == 0:
        return {"onset_s": onset_s, "latency_s": None, "detected": False}

    latency_s = times_in_range[flagged[0]] - onset_s
    return {"onset_s": onset_s, "latency_s": float(latency_s), "detected": True}


#  Summary / CLI 

def summary(preprocessed: dict) -> dict:
    sid = preprocessed["sid"]

    gsr = flag_gsr_events(preprocessed)
    hr  = flag_hr_events(preprocessed)
    gsr_lat = measure_gsr_latency(preprocessed)
    hr_lat  = measure_hr_latency(preprocessed)

    print(f"\n{'='*55}")
    print(f"  Threshold Detector — S{sid}")
    print(f"{'='*55}")
    print(f"  GSR  mu={gsr['mu']:.4f}  sigma={gsr['sigma']:.4f}  "
          f"threshold={gsr['threshold']:.4f}")
    print(f"       flagged samples: {gsr['flags'].sum()} / {len(gsr['flags'])} "
          f"({gsr['flags'].mean()*100:.2f}%)")
    print(f"  HR   baseline={hr['baseline_hr']:.1f} BPM  "
          f"range=[{hr['threshold_lo']:.1f}, {hr['threshold_hi']:.1f}] BPM")
    print(f"       flagged windows: {hr['flags'].sum()} / {len(hr['flags'])} "
          f"({hr['flags'].mean()*100:.2f}%)")

    print(f"\n  Onset latency (stress condition transition):")
    if gsr_lat["detected"]:
        print(f"    GSR: onset={gsr_lat['onset_s']:.1f}s  "
              f"latency={gsr_lat['latency_s']:.1f}s  "
              f"{'PASS' if gsr_lat['latency_s'] <= 10 else 'SLOW'} (target <=10s)")
    else:
        print(f"    GSR: onset={gsr_lat['onset_s']:.1f}s  no flag within 30s  FAIL")

    if hr_lat["detected"]:
        print(f"    HR : onset={hr_lat['onset_s']:.1f}s  "
              f"latency={hr_lat['latency_s']:.1f}s  "
              f"{'PASS' if hr_lat['latency_s'] <= 10 else 'SLOW'} (target <=10s)")
    else:
        print(f"    HR : onset={hr_lat['onset_s']:.1f}s  no flag within 30s  FAIL")
    print()

    return {
        "sid": sid, "gsr": gsr, "hr": hr,
        "gsr_latency": gsr_lat, "hr_latency": hr_lat,
    }


if __name__ == "__main__":
    sid      = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    data_dir = sys.argv[2] if len(sys.argv) > 2 else "data/WESAD"

    subject      = load_subject(sid, data_dir)
    preprocessed = preprocess_subject(subject)
    results      = summary(preprocessed)

    Path("outputs/results").mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "sid": sid,
        "gsr_onset_s": results["gsr_latency"]["onset_s"],
        "gsr_latency_s": results["gsr_latency"]["latency_s"],
        "gsr_detected": results["gsr_latency"]["detected"],
        "hr_onset_s": results["hr_latency"]["onset_s"],
        "hr_latency_s": results["hr_latency"]["latency_s"],
        "hr_detected": results["hr_latency"]["detected"],
    }]).to_csv(f"outputs/results/threshold_test_S{sid}.csv", index=False)