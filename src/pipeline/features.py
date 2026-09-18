

import numpy as np
import pandas as pd
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wesad_loader import load_subject, LABEL_NAMES
from preprocess import preprocess_subject

FEATURE_COLS = [
    "mean_hr", "rmssd", "sdnn", "pnn50",
    "scr_count", "scr_max_amp", "scr_energy",
    "scr_epeak", "scl_mean",
]


def _ppg_features(ibi_ms, ibi_idx, win_start, win_end, fs_bvp):
    mask  = (ibi_idx >= win_start) & (ibi_idx < win_end)
    ibi_w = ibi_ms[mask]

    if len(ibi_w) < 4:
        return {"mean_hr": np.nan, "rmssd": np.nan,
                "sdnn": np.nan, "pnn50": np.nan}

    mean_hr = 60000.0 / np.mean(ibi_w)
    sdnn    = float(np.std(ibi_w, ddof=1))
    successive_diff = np.diff(ibi_w)
    rmssd = float(np.sqrt(np.mean(successive_diff ** 2)))
    pnn50 = float(np.sum(np.abs(successive_diff) > 50) / len(successive_diff))

    return {"mean_hr": float(mean_hr), "rmssd": rmssd,
            "sdnn": sdnn, "pnn50": pnn50}


def _gsr_features(scr, scl, scr_peaks, win_start, win_end, fs_eda):
    scr_w = scr[win_start:win_end]
    scl_w = scl[win_start:win_end]

    peaks_w = scr_peaks[(scr_peaks >= win_start) & (scr_peaks < win_end)]
    n_peaks = len(peaks_w)

    scr_max_amp = float(np.max(scr_w)) if n_peaks > 0 else 0.0
    scr_energy  = float(np.sum(scr_w ** 2))
    scr_epeak   = scr_energy / n_peaks if n_peaks > 0 else 0.0
    scl_mean    = float(np.mean(scl_w))

    return {"scr_count": float(n_peaks), "scr_max_amp": scr_max_amp,
            "scr_energy": scr_energy, "scr_epeak": scr_epeak,
            "scl_mean": scl_mean}


def _window_label(labels_bvp, win_start, win_end):
    seg   = labels_bvp[win_start:win_end]
    valid = seg[seg != 0]
    if len(valid) == 0:
        return 0
    values, counts = np.unique(valid, return_counts=True)
    majority      = values[np.argmax(counts)]
    majority_frac = counts.max() / len(seg)
    if majority_frac < 0.80:
        return 0
    return int(majority)


def _artifact_fraction(artifact_mask, win_start_s, win_end_s):
    i_start = int(win_start_s)
    i_end   = min(int(win_end_s), len(artifact_mask))
    if i_end <= i_start:
        return 0.0
    return float(np.mean(artifact_mask[i_start:i_end]))


def extract_window_features(preprocessed, window_s=60.0, stride_s=30.0,
                            artifact_threshold=0.20):
    sid    = preprocessed["sid"]
    fs_bvp = preprocessed["fs"]["bvp"]
    fs_eda = preprocessed["fs"]["eda"]

    ibi_ms  = preprocessed["peaks"]["ibi_ms"]
    ibi_idx = preprocessed["peaks"]["ibi_idx"]

    scr           = preprocessed["eda"]["scr"]
    scl           = preprocessed["eda"]["scl"]
    scr_peaks     = preprocessed["eda"]["scr_peaks"]
    labels_bvp    = preprocessed["labels"]["bvp"]
    artifact_mask = preprocessed["artifact_mask"]

    win_samples    = int(window_s * fs_bvp)
    stride_samples = int(stride_s * fs_bvp)
    win_eda        = int(window_s * fs_eda)
    stride_eda     = int(stride_s * fs_eda)

    total_samples = len(preprocessed["bvp_clean"])
    records = []

    win_idx   = 0
    bvp_start = 0
    eda_start = 0

    while bvp_start + win_samples <= total_samples:
        bvp_end = bvp_start + win_samples
        eda_end = eda_start + win_eda

        win_start_s = bvp_start / fs_bvp
        win_end_s   = bvp_end   / fs_bvp

        label = _window_label(labels_bvp, bvp_start, bvp_end)

        if label not in (1, 2):
            bvp_start += stride_samples
            eda_start += stride_eda
            win_idx   += 1
            continue

        art_frac = _artifact_fraction(artifact_mask, win_start_s, win_end_s)
        if art_frac > artifact_threshold:
            bvp_start += stride_samples
            eda_start += stride_eda
            win_idx   += 1
            continue

        ppg_feat = _ppg_features(ibi_ms, ibi_idx, bvp_start, bvp_end, fs_bvp)

        if np.isnan(ppg_feat["rmssd"]):
            bvp_start += stride_samples
            eda_start += stride_eda
            win_idx   += 1
            continue

        eda_end_clipped = min(eda_end, len(scr))
        gsr_feat = _gsr_features(scr, scl, scr_peaks,
                                  eda_start, eda_end_clipped, fs_eda)

        records.append({
            "sid": sid, "window_idx": win_idx, "label": label,
            "label_name": LABEL_NAMES[label],
            "win_start_s": win_start_s, "win_end_s": win_end_s,
            "art_frac": art_frac, **ppg_feat, **gsr_feat,
        })

        bvp_start += stride_samples
        eda_start += stride_eda
        win_idx   += 1

    df = pd.DataFrame(records)

    if df.empty:
        print(f"  WARNING: No valid windows found for S{sid}")
        return df

    df = df.dropna(subset=FEATURE_COLS).reset_index(drop=True)
    return df


def save_features(df, sid, out_dir="outputs/features"):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    path = Path(out_dir) / f"S{sid}_features.csv"
    df.to_csv(path, index=False)
    print(f"  Features saved → {path}  ({len(df)} windows)")


def load_features(sid, out_dir="outputs/features"):
    path = Path(out_dir) / f"S{sid}_features.csv"
    if not path.exists():
        raise FileNotFoundError(f"Features not found: {path}")
    return pd.read_csv(path)


def feature_summary(df):
    sid = df["sid"].iloc[0]
    print(f"\n{'='*55}")
    print(f"  Feature Summary — S{sid}")
    print(f"{'='*55}")
    print(f"  Total windows : {len(df)}")
    for label in sorted(df["label"].unique()):
        name = LABEL_NAMES[label]
        n    = (df["label"] == label).sum()
        print(f"    {name:12s} (label={label}) : {n} windows")

    print(f"\n  {'Feature':<16} {'mean':>8} {'std':>8} {'min':>8} {'max':>8}")
    print(f"  {'-'*52}")
    for col in FEATURE_COLS:
        print(f"  {col:<16} {df[col].mean():>8.3f} {df[col].std():>8.3f} "
              f"{df[col].min():>8.3f} {df[col].max():>8.3f}")
    print()

    print(f"  {'Feature':<16} {'baseline':>10} {'stress':>10}  diff")
    print(f"  {'-'*46}")
    for col in ["mean_hr", "rmssd", "sdnn", "scr_count", "scl_mean"]:
        base   = df[df["label"] == 1][col].mean()
        stress = df[df["label"] == 2][col].mean()
        diff   = stress - base
        direction = "↑" if diff > 0 else "↓"
        print(f"  {col:<16} {base:>10.3f} {stress:>10.3f}  {direction}{abs(diff):.3f}")
    print()


if __name__ == "__main__":
    sid      = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    data_dir = sys.argv[2] if len(sys.argv) > 2 else "data/WESAD"

    subject      = load_subject(sid, data_dir)
    preprocessed = preprocess_subject(subject)
    df = extract_window_features(preprocessed)
    feature_summary(df)
    save_features(df, sid)