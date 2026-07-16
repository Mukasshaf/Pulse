

import numpy as np
import pandas as pd
from pathlib import Path
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wesad_loader import load_subject, LABEL_NAMES
from preprocess import preprocess_subject
from features import extract_window_features, save_features


FEATURE_COLS = [
        "mean_hr", "rmssd", "sdnn", "pnn50",
        "scr_count", "scr_max_amp", "scr_energy",
        "scr_epeak", "scl_mean"]

META_COLS = [
    "sid", "window_idx", "label", "label_name",
    "win_start_s", "win_end_s", "art_frac",
]


#  Core normalization 

def normalize_subject(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    
    baseline = df[df["label"] == 1][FEATURE_COLS]

    if len(baseline) == 0:
        raise ValueError(
            f"No baseline windows (label=1) found for S{df['sid'].iloc[0]}. "
            "Cannot normalize without a baseline reference."
        )

    mu    = baseline.mean()
    sigma = baseline.std(ddof=1)

    sigma = sigma.replace(0.0, 1e-6)


    features_norm = (df[FEATURE_COLS] - mu) / sigma

    # Assemble output
    df_norm = df[META_COLS].copy()
    df_norm = pd.concat([df_norm, features_norm], axis=1)

    baseline_stats = pd.DataFrame({
        "feature": FEATURE_COLS,
        "mu":      mu.values,
        "sigma":   sigma.values,
    })

    return df_norm, baseline_stats


# Save / load

def save_normalized(df_raw: pd.DataFrame,
                    df_norm: pd.DataFrame,
                    baseline_stats: pd.DataFrame,
                    sid: int,
                    out_dir: str = "outputs/features") -> None:
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    raw_path   = Path(out_dir) / f"S{sid}_raw.csv"
    norm_path  = Path(out_dir) / f"S{sid}_norm.csv"
    stats_path = Path(out_dir) / f"S{sid}_baseline_stats.csv"

    df_raw.to_csv(raw_path,   index=False)
    df_norm.to_csv(norm_path, index=False)
    baseline_stats.to_csv(stats_path, index=False)

    print(f"  Saved raw        → {raw_path}")
    print(f"  Saved normalized → {norm_path}")
    print(f"  Saved stats      → {stats_path}")


def load_normalized(sid: int,
                    out_dir: str = "outputs/features"
                    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw_path   = Path(out_dir) / f"S{sid}_raw.csv"
    norm_path  = Path(out_dir) / f"S{sid}_norm.csv"
    stats_path = Path(out_dir) / f"S{sid}_baseline_stats.csv"

    for p in (raw_path, norm_path, stats_path):
        if not p.exists():
            raise FileNotFoundError(f"Missing: {p}")

    return (
        pd.read_csv(raw_path),
        pd.read_csv(norm_path),
        pd.read_csv(stats_path),
    )


#  Validation

def normalization_summary(df_raw: pd.DataFrame,
                          df_norm: pd.DataFrame,
                          baseline_stats: pd.DataFrame) -> None:
    """
    Prints two checks:
    1. Baseline z-scores should be ~ 0 mean, ~ 1 std
    2. Stress z-scores should differ from baseline (activation signal)
    """
    sid = df_raw["sid"].iloc[0]
    print(f"\n{'='*60}")
    print(f"  Normalization Validation — S{sid}")
    print(f"{'='*60}")

    baseline_norm = df_norm[df_norm["label"] == 1][FEATURE_COLS]
    stress_norm   = df_norm[df_norm["label"] == 2][FEATURE_COLS]

    print(f"\n  Baseline z-scores (expect mean ≈ 0, std ≈ 1):")
    print(f"  {'Feature':<16} {'mean':>8} {'std':>8}  check")
    print(f"  {'-'*44}")
    for col in FEATURE_COLS:
        m = baseline_norm[col].mean()
        s = baseline_norm[col].std()
        ok = "✓" if abs(m) < 0.1 and 0.7 < s < 1.3 else "!"
        print(f"  {col:<16} {m:>8.3f} {s:>8.3f}  {ok}")

    print(f"\n  Stress z-scores (deviation from baseline):")
    print(f"  {'Feature':<16} {'mean z':>8}  direction")
    print(f"  {'-'*38}")
    for col in FEATURE_COLS:
        m = stress_norm[col].mean()
        direction = "↑ activated" if m > 0.3 else ("↓ suppressed" if m < -0.3 else "~ neutral")
        print(f"  {col:<16} {m:>8.3f}  {direction}")

    print(f"\n  Baseline stats (mu / sigma used for normalization):")
    print(f"  {'Feature':<16} {'mu':>10} {'sigma':>10}")
    print(f"  {'-'*40}")
    for _, row in baseline_stats.iterrows():
        print(f"  {row['feature']:<16} {row['mu']:>10.4f} {row['sigma']:>10.4f}")
    print()


# CLI

if __name__ == "__main__":
    sid      = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    data_dir = sys.argv[2] if len(sys.argv) > 2 else "data/WESAD"

    subject      = load_subject(sid, data_dir)
    preprocessed = preprocess_subject(subject)
    df_raw       = extract_window_features(preprocessed)

    print("\nNormalizing features...")
    df_norm, baseline_stats = normalize_subject(df_raw)

    normalization_summary(df_raw, df_norm, baseline_stats)
    save_normalized(df_raw, df_norm, baseline_stats, sid)