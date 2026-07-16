# Batch comparison: individual subjects vs group average.
# change (stress vs baseline) per feature per subject


import argparse
import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FEATURE_COLS = [
    "mean_hr", "rmssd", "sdnn", "pnn50",
    "scr_count", "scr_max_amp", "scr_energy",
    "scr_epeak", "scl_mean", "scl_slope",
]


def pct_change(baseline_mean, stress_mean, baseline_std, eps=1e-6):
    
    denom = max(abs(baseline_mean), baseline_std, eps)
    return (stress_mean - baseline_mean) / denom * 100.0


def compute_subject_pct_change(sid, features_dir="outputs/features"):
    path = Path(features_dir) / f"S{sid}_raw.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    baseline = df[df["label"] == 1]
    stress   = df[df["label"] == 2]
    if len(baseline) == 0 or len(stress) == 0:
        return None

    row = {"sid": f"S{sid}"}
    for col in FEATURE_COLS:
        row[col] = pct_change(baseline[col].mean(), stress[col].mean())
    return row


def build_matrix(sids, features_dir="outputs/features"):
    rows, skipped = [], []
    for sid in sids:
        r = compute_subject_pct_change(sid, features_dir)
        if r is None:
            skipped.append(sid)
            continue
        rows.append(r)
    df = pd.DataFrame(rows).set_index("sid")
    df.loc["Group Avg"] = df.mean()
    return df, skipped


def plot_heatmap(df, out_path="outputs/plots/batch_comparison_heatmap.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    data = df.values
    vmax = max(np.nanpercentile(np.abs(data), 95), 10)

    fig, ax = plt.subplots(figsize=(11, max(6, 0.4 * len(df))))
    im = ax.imshow(data, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")

    ax.set_xticks(range(len(df.columns)))
    ax.set_xticklabels(df.columns, rotation=40, ha="right")
    ax.set_yticks(range(len(df.index)))
    ax.set_yticklabels(df.index)
    ax.axhline(len(df.index) - 1.5, color="black", linewidth=1.5)

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            val = data[i, j]
            color = "white" if abs(val) > vmax * 0.6 else "black"
            weight = "bold" if df.index[i] == "Group Avg" else "normal"
            ax.text(j, i, f"{val:.0f}", ha="center", va="center",
                    fontsize=7, color=color, fontweight=weight)

    ax.set_title("Batch Comparison: Individual Subjects vs Group Average\n% Change (Stress vs Baseline)",
                 fontsize=11, fontweight="bold")
    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("% change")
    plt.tight_layout()
    plt.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close()
    print(f"Heatmap saved -> {out_path}")


def feature_screening_report(df):
    subj_df = df.drop(index="Group Avg")
    print("\nFeature consistency (sign agreement across subjects):")
    print(f"{'feature':<14}{'group_avg%':>12}{'sign_agree%':>14}{'flag':>8}")
    for col in FEATURE_COLS:
        group_avg = df.loc["Group Avg", col]
        signs = np.sign(subj_df[col])
        agree = max((signs > 0).mean(), (signs < 0).mean()) * 100
        flag = "DROP?" if agree < 60 or abs(group_avg) < 5 else ""
        print(f"{col:<14}{group_avg:>12.1f}{agree:>14.1f}{flag:>8}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sids", nargs="+", type=int, required=True)
    parser.add_argument("--features_dir", type=str, default="outputs/features")
    args = parser.parse_args()

    df, skipped = build_matrix(args.sids, args.features_dir)
    if skipped:
        print(f"Skipped (missing/insufficient data): {skipped}")

    plot_heatmap(df)
    feature_screening_report(df)

    out_csv = "outputs/results/batch_comparison_pct_change.csv"
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv)
    print(f"Matrix saved -> {out_csv}")