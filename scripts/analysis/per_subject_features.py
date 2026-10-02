"""
per_subject_features.py — Per-subject domain feature extraction.

Refactored core logic from domain_activation_map.py. This module:
  - Exposes extract_domain_features(subject_id, aligned_csv_path) → pd.DataFrame
  - Exposes plot_subject_radar(subject_id, results, out_path) for single-subject charts
  - Is called automatically by run_session.py after every session
  - Is imported by group_report.py to produce multi-subject comparisons
  - Is imported by domain_activation_map.py (thin compatibility wrapper)

All normalization guards are preserved exactly as fixed in the Phase 3.2 pilot:
  - SIGMA_MIN_FRAC = 0.01  (zero-division guard)
  - MIN_BASELINE_WINDOWS = 4  (unreliable std guard)

Usage:
    from per_subject_features import extract_domain_features, plot_subject_radar
    results = extract_domain_features("S01", Path("outputs/aligned/S01_aligned.csv"))
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Path setup ────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT / "src" / "pipeline"))
sys.path.insert(0, str(_ROOT / "src"))

from preprocess import (
    clean_bvp,
    detect_peaks,
    decompose_eda,
    flag_motion_artifacts,
    ACC_THRESHOLD_HW,
)
from domains import DOMAIN_IDS

# ── Constants ─────────────────────────────────────────────────────────────────
HW_FS: float = 1000.0 / 15.0           # 66.6667 Hz — all channels share this rate
WINDOW_S: float = 30.0                  # feature window length (seconds)
STRIDE_S: float = 15.0                  # stride between windows (seconds)
MIN_VALID_WINDOWS: int = 1              # minimum windows to include a domain value
MAX_ART_FRAC: float = 0.50             # skip window if >50% 1s-buckets are artifacts

# Normalization guards — DO NOT CHANGE without a recorded decision
MIN_BASELINE_WINDOWS: int = 4          # minimum valid baseline windows required for z-score.
                                        # With fewer, std(ddof=1) is unreliable. Subject is
                                        # flagged and raw feature values are reported instead.
SIGMA_MIN_FRAC: float = 0.01           # if per-feature sigma < 1% of |mu|, normalization is
                                        # unstable (same bug class as batch_comparison incident).
                                        # Such features are clamped to NaN for that subject.
                                        # 5% was too aggressive — flagged S01 scl_mean (sigma=49
                                        # on mu=1327, healthy variance). 1% catches true
                                        # degenerates like scr_max_amp sigma=0.

FEATURE_COLS = [
    "mean_hr", "rmssd", "sdnn", "pnn50",
    "scr_count", "scr_max_amp", "scr_energy",
    "scr_epeak", "scl_mean",
]
PRIMARY_FEATURE = "scl_mean"            # Gini rank #1 from WESAD RF (0.37 importance)
SECONDARY_FEATURE = "scr_epeak"        # Gini rank #2 from WESAD RF


# ── Feature extraction from a raw domain slice ────────────────────────────────

def extract_slice_features(
    bvp: np.ndarray,
    gsr: np.ndarray,
    acc: np.ndarray,
    fs: float = HW_FS,
) -> pd.DataFrame:
    """
    Run the full hardware preprocessing pipeline on a domain-contiguous slice,
    then extract features using rolling windows.

    Returns a DataFrame of per-window feature rows (may be empty if too short
    or all artifact-flagged).
    """
    n_samples = len(bvp)
    duration_s = n_samples / fs

    if duration_s < WINDOW_S:
        return pd.DataFrame(columns=FEATURE_COLS)

    # 1. Signal preprocessing
    bvp_clean = clean_bvp(bvp, fs=fs)
    peaks = detect_peaks(bvp_clean, fs=fs)
    eda_results = decompose_eda(gsr, fs=fs)

    # flag_motion_artifacts returns a boolean array indexed by 1-second buckets
    # (artifact_mask[i] == True means the i-th second is motion-contaminated).
    artifact_mask_1s = flag_motion_artifacts(acc, fs=fs, threshold=ACC_THRESHOLD_HW)

    ibi_ms  = peaks["ibi_ms"]
    ibi_idx = peaks["ibi_idx"]
    scr     = eda_results["scr"]
    scl     = eda_results["scl"]
    scr_peaks = eda_results["scr_peaks"]

    # 2. Rolling windows
    win_samp    = int(WINDOW_S * fs)
    stride_samp = int(STRIDE_S * fs)

    records = []
    bvp_start = 0

    while bvp_start + win_samp <= n_samples:
        bvp_end = bvp_start + win_samp

        # Artifact fraction: map sample range to 1s-bucket range
        sec_start = int(bvp_start / fs)
        sec_end   = min(int(bvp_end / fs), len(artifact_mask_1s))
        art_frac  = float(np.mean(artifact_mask_1s[sec_start:sec_end])) \
                    if sec_end > sec_start else 1.0

        if art_frac > MAX_ART_FRAC:
            bvp_start += stride_samp
            continue

        # PPG / HRV features
        mask   = (ibi_idx >= bvp_start) & (ibi_idx < bvp_end)
        ibi_w  = ibi_ms[mask]

        if len(ibi_w) >= 4:
            mean_hr = float(60_000.0 / np.mean(ibi_w))
            sdnn    = float(np.std(ibi_w, ddof=1))
            succ    = np.diff(ibi_w)
            rmssd   = float(np.sqrt(np.mean(succ ** 2)))
            pnn50   = float(np.sum(np.abs(succ) > 50) / len(succ))
        else:
            mean_hr = sdnn = rmssd = pnn50 = np.nan

        # EDA / GSR features
        eda_start = bvp_start
        eda_end   = bvp_end

        scr_w   = scr[eda_start:eda_end]
        scl_w   = scl[eda_start:eda_end]
        peaks_w = scr_peaks[(scr_peaks >= eda_start) & (scr_peaks < eda_end)]
        n_peaks = len(peaks_w)

        scr_max_amp = float(np.max(scr_w)) if n_peaks > 0 else 0.0
        scr_energy  = float(np.sum(scr_w ** 2))
        scr_epeak   = scr_energy / n_peaks if n_peaks > 0 else 0.0
        scl_mean    = float(np.mean(scl_w))

        records.append({
            "win_start_s": bvp_start / fs,
            "win_end_s":   bvp_end / fs,
            "art_frac":    art_frac,
            "mean_hr":     mean_hr,
            "rmssd":       rmssd,
            "sdnn":        sdnn,
            "pnn50":       pnn50,
            "scr_count":   float(n_peaks),
            "scr_max_amp": scr_max_amp,
            "scr_energy":  scr_energy,
            "scr_epeak":   scr_epeak,
            "scl_mean":    scl_mean,
        })

        bvp_start += stride_samp

    return pd.DataFrame(records)


# ── Per-subject domain feature extraction ────────────────────────────────────

def extract_domain_features(
    subject_id: str,
    aligned_csv_path: Path,
) -> dict:
    """
    Main entry point for single-subject domain feature extraction.

    Reads an aligned CSV (from align_signals.py), slices by active_domain,
    runs the full preprocessing + feature extraction pipeline, applies
    within-subject z-score normalization against the resting baseline, and
    applies both normalization guards (SIGMA_MIN_FRAC, MIN_BASELINE_WINDOWS).

    Returns:
        dict mapping domain_id -> {
            "mean": {feat: val},
            "std":  {feat: val},
            "n":    int,
            "normalized": bool,
            "art_frac_mean": float,   # mean artifact fraction across domain windows
        }
        or {} if baseline extraction fails entirely.

    The result dict can be saved to CSV via save_domain_features_csv().
    """
    print(f"\n[{subject_id}] Reading {aligned_csv_path.name}  ({aligned_csv_path.stat().st_size // 1024} KB)")
    df = pd.read_csv(aligned_csv_path)

    # Sanity-check unix_ts_ms
    ts_sample = df["unix_ts_ms"].dropna().iloc[min(500, len(df) - 1)]
    if ts_sample < 1e12:
        print(f"  WARNING: unix_ts_ms value {ts_sample:.0f} looks like relative time, not epoch ms.")

    all_domains = ["baseline"] + list(DOMAIN_IDS)
    raw_features: dict[str, pd.DataFrame] = {}
    domain_art_fracs: dict[str, float] = {}

    # Pass 1: extract raw features per domain
    for domain in all_domains:
        slice_df = df[df["active_domain"] == domain].copy()
        if len(slice_df) == 0:
            print(f"  [{domain:30s}] SKIP — no rows")
            continue

        dur_s = len(slice_df) / HW_FS
        print(f"  [{domain:30s}] {len(slice_df):6d} rows ({dur_s:5.0f}s)", end="  ")

        bvp = slice_df["pulse_raw"].values.astype(float)
        gsr = slice_df["gsr_raw"].values.astype(float)
        acc = slice_df[["acc_x", "acc_y", "acc_z"]].values.astype(float)

        feat_df = extract_slice_features(bvp, gsr, acc, fs=HW_FS)

        if feat_df.empty:
            print("-> SKIP (too short or fully artifact-flagged)")
            domain_art_fracs[domain] = 1.0
            continue

        valid = feat_df.dropna(subset=[PRIMARY_FEATURE, "mean_hr"])
        art_mean = feat_df["art_frac"].mean()
        print(f"-> {len(valid)}/{len(feat_df)} valid windows  (art_frac_mean={art_mean:.1%})")

        domain_art_fracs[domain] = float(art_mean)

        if len(valid) >= MIN_VALID_WINDOWS:
            raw_features[domain] = valid

    # Pass 2: baseline normalization stats
    if "baseline" not in raw_features:
        print(f"  [{subject_id}] ERROR — no valid baseline windows. Cannot normalize.")
        return {}

    n_base = len(raw_features["baseline"])
    base_df = raw_features["baseline"][FEATURE_COLS]
    baseline_mu    = base_df.mean()
    baseline_sigma = base_df.std(ddof=1)

    print(f"\n  Baseline  n_windows={n_base}  mu(scl_mean)={baseline_mu['scl_mean']:.4f}  "
          f"sigma(scl_mean)={baseline_sigma['scl_mean']:.4f}")

    # Guard 1: insufficient baseline windows
    if n_base < MIN_BASELINE_WINDOWS:
        print(f"  [{subject_id}] WARNING — only {n_base} valid baseline windows "
              f"(need >= {MIN_BASELINE_WINDOWS}). Z-score normalization SKIPPED. "
              f"Raw feature values will be reported. Do not compare directly with normalized subjects.")
        results: dict = {}
        for domain in DOMAIN_IDS:
            if domain not in raw_features:
                results[domain] = None
                continue
            feat_df = raw_features[domain][FEATURE_COLS]
            results[domain] = {
                "mean":         feat_df.mean().to_dict(),
                "std":          feat_df.std(ddof=1).to_dict() if len(feat_df) > 1
                                else {f: 0.0 for f in FEATURE_COLS},
                "n":            len(feat_df),
                "normalized":   False,
                "art_frac_mean": domain_art_fracs.get(domain, np.nan),
            }
        return results

    # Guard 2: per-feature sigma floor
    safe_sigma = baseline_sigma.copy()
    flagged_features = []
    for feat in FEATURE_COLS:
        mu_abs = abs(baseline_mu[feat])
        sig = baseline_sigma[feat]
        min_safe_sig = SIGMA_MIN_FRAC * mu_abs if mu_abs > 0 else 1e-3
        if sig < min_safe_sig or sig == 0.0:
            safe_sigma[feat] = np.nan
            flagged_features.append(f"{feat}(sigma={sig:.4f})")

    if flagged_features:
        print(f"  [{subject_id}] WARNING — near-zero sigma on: {flagged_features}. "
              f"Those feature columns will be NaN in output.")

    # Pass 3: normalize domains
    results = {}
    for domain in DOMAIN_IDS:
        if domain not in raw_features:
            results[domain] = None
            continue

        feat_df    = raw_features[domain][FEATURE_COLS]
        normalized = (feat_df - baseline_mu) / safe_sigma

        results[domain] = {
            "mean":         normalized.mean().to_dict(),
            "std":          normalized.std(ddof=1).to_dict() if len(normalized) > 1
                            else {f: 0.0 for f in FEATURE_COLS},
            "n":            len(normalized),
            "normalized":   True,
            "art_frac_mean": domain_art_fracs.get(domain, np.nan),
        }

    return results


# ── Persist to CSV ────────────────────────────────────────────────────────────

def save_domain_features_csv(
    results: dict,
    subject_id: str,
    out_path: Path,
) -> None:
    """
    Flatten the results dict to a tidy CSV with one row per domain.
    Columns: subject, domain, n_windows, normalized, art_frac_mean,
             mean_{feat}, std_{feat} for each feature in FEATURE_COLS.
    """
    records = []
    for domain in DOMAIN_IDS:
        res = results.get(domain)
        if res is None:
            row = {
                "subject": subject_id,
                "domain": domain,
                "n_windows": 0,
                "normalized": False,
                "art_frac_mean": np.nan,
            }
            for c in FEATURE_COLS:
                row[f"mean_{c}"] = np.nan
                row[f"std_{c}"]  = np.nan
        else:
            row = {
                "subject": subject_id,
                "domain": domain,
                "n_windows": res["n"],
                "normalized": res["normalized"],
                "art_frac_mean": res.get("art_frac_mean", np.nan),
            }
            for c in FEATURE_COLS:
                row[f"mean_{c}"] = res["mean"].get(c, np.nan)
                row[f"std_{c}"]  = res["std"].get(c, np.nan)
        records.append(row)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(out_path, index=False, float_format="%.4f")
    print(f"  Domain features CSV saved -> {out_path}")


# ── Single-subject radar plot ─────────────────────────────────────────────────

def plot_subject_radar(
    subject_id: str,
    results: dict,
    out_path: Path,
    color: str = "#d62728",
) -> None:
    """
    Render a single-subject radar chart of scl_mean (z-score or raw) per domain.
    Saves to out_path. Handles the normalized vs. raw-units case with distinct
    axis labels and title annotations.
    """
    domains   = list(DOMAIN_IDS)
    n_domains = len(domains)
    angles    = np.linspace(0, 2 * np.pi, n_domains, endpoint=False).tolist()
    angles   += angles[:1]

    domain_labels = [
        d.replace("_", " ").replace("impulsivity gratification", "Impulsivity /\nGratif.").title()
        for d in domains
    ]

    values = []
    errs   = []
    ns     = []
    for domain in domains:
        d_res = results.get(domain)
        if d_res:
            val = d_res["mean"].get(PRIMARY_FEATURE, np.nan)
            values.append(val if val is not None else np.nan)
            errs.append(d_res["std"].get(PRIMARY_FEATURE, 0.0) or 0.0)
            ns.append(d_res["n"])
        else:
            values.append(np.nan)
            errs.append(0.0)
            ns.append(0)

    is_normalized = any(
        v is not None and v.get("normalized", True)
        for v in results.values()
    )

    if is_normalized:
        raw_vals = [v for v in values if not np.isnan(v)]
        flat = []
        for m, s in zip(values, errs):
            if not np.isnan(m):
                flat.extend([m - s, m + s])
        y_min = (min(flat) - 0.4) if flat else -2.0
        y_max = (max(flat) + 0.4) if flat else  2.0
        y_min = min(y_min, -0.8)
        y_max = max(y_max,  1.0)
        y_label_suffix = "σ"
        baseline_ref   = 0.0
        title_suffix   = ""
    else:
        raw_vals = [v for v in values if not np.isnan(v)]
        y_min = min(raw_vals) * 0.9 if raw_vals else 0
        y_max = max(raw_vals) * 1.1 if raw_vals else 1
        y_label_suffix = " (raw)"
        baseline_ref   = None
        title_suffix   = "\n[RAW UNITS — baseline n<4]"

    fig, ax = plt.subplots(figsize=(6, 6.5), subplot_kw=dict(polar=True))
    fig.suptitle(
        f"Subject {subject_id}{title_suffix}\n"
        f"Domain Activation ({PRIMARY_FEATURE}, {'z-score' if is_normalized else 'raw units'})",
        fontsize=11, weight="bold", y=1.03,
    )

    values_plot = values + [values[0]]
    ax.plot(angles, values_plot, linewidth=2.0, color=color)

    # Matplotlib's fill behaves poorly with NaNs, bridging the gap artificially.
    # Only fill if all domains are present.
    if not np.isnan(values).any():
        ax.fill(angles, values_plot, color=color, alpha=0.18)

    if baseline_ref is not None:
        ax.plot(angles, [baseline_ref] * len(angles), "k--", linewidth=1.0, alpha=0.45)

    # Error whiskers
    for angle, val, err, n in zip(angles[:-1], values, errs, ns):
        if np.isnan(val) or n <= 1:
            continue
        ax.plot([angle, angle], [val - err, val + err],
                color=color, linewidth=1.8, alpha=0.55, solid_capstyle="round")

    # n= annotations
    span = y_max - y_min
    for angle, val, err, n in zip(angles[:-1], values, errs, ns):
        if np.isnan(val) or n == 0:
            # Explicitly label missing data so it's not just a silent gap
            ax.annotate("n=0", xy=(angle, y_min + span * 0.1),
                        ha="center", va="center", fontsize=7.5, color="#cc0000", weight="bold")
            continue
        r_label = val + err + span * 0.07
        label_color = "#aaaaaa" if n == 1 else "#444444"
        label_text  = f"n={n}*" if n == 1 else f"n={n}"
        ax.annotate(label_text, xy=(angle, r_label),
                    ha="center", va="center", fontsize=6.5, color=label_color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(domain_labels, size=8)
    ax.set_ylim(y_min, y_max)

    y_ticks = np.round(np.linspace(y_min, y_max, 5), 1)
    ax.set_yticks(y_ticks)
    ax.set_yticklabels([f"{v:.1f}{y_label_suffix}" for v in y_ticks], size=7)
    ax.grid(True, alpha=0.25)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"  Radar chart saved -> {out_path}")


# ── Multi-subject group radar (also used by group_report.py) ─────────────────

def plot_group_radar(
    all_results: dict,
    subjects: list[str],
    out_path: Path,
) -> None:
    """
    Multi-subject radar on a shared z-score y-axis (unnormalized subjects get
    their own independent axis and are annotated). Mirrors the original
    domain_activation_map.plot_radar() behaviour exactly.
    """
    domains   = list(DOMAIN_IDS)
    n_domains = len(domains)
    angles    = np.linspace(0, 2 * np.pi, n_domains, endpoint=False).tolist()
    angles   += angles[:1]

    domain_labels = [
        d.replace("_", " ").replace("impulsivity gratification", "Impulsivity /\nGratif.").title()
        for d in domains
    ]

    # Collect flat value range from normalized subjects only
    all_vals_flat = []
    normalized_sids = []
    raw_sids = []

    for sid in subjects:
        if sid not in all_results or not all_results[sid]:
            continue
        is_norm = any(
            v is not None and v.get("normalized", True)
            for v in all_results[sid].values()
        )
        if is_norm:
            normalized_sids.append(sid)
            for domain in domains:
                res = all_results[sid].get(domain)
                if res and not np.isnan(res["mean"].get(PRIMARY_FEATURE, np.nan)):
                    m = res["mean"][PRIMARY_FEATURE]
                    s = res["std"][PRIMARY_FEATURE]
                    if not np.isnan(m):
                        all_vals_flat.extend([m - s, m + s])
        else:
            raw_sids.append(sid)

    if raw_sids:
        print(f"\n  NOTE: {raw_sids} excluded from shared y-axis (insufficient baseline windows — "
              f"raw units reported, not z-score). Their subplot will use an independent axis.")

    if not all_vals_flat and not raw_sids:
        print("ERROR: No plottable data after pipeline. Check aligned CSVs.")
        return

    if all_vals_flat:
        y_min_norm = min(all_vals_flat) - 0.4
        y_max_norm = max(all_vals_flat) + 0.4
        y_min_norm = min(y_min_norm, -0.8)
        y_max_norm = max(y_max_norm, 1.0)
    else:
        y_min_norm, y_max_norm = -2.0, 2.0

    n_subs = len(subjects)
    fig, axes = plt.subplots(1, n_subs, figsize=(5.5 * n_subs, 6.5),
                             subplot_kw=dict(polar=True))
    if n_subs == 1:
        axes = [axes]

    fig.suptitle(
        f"N={n_subs} — Domain Activation (scl_mean, z-score vs. resting baseline)\n"
        "Full pipeline: Butterworth BPF · EMD tonic/phasic · ACC_THRESHOLD_HW=8800 motion gate",
        fontsize=11, weight="bold", y=1.04,
    )

    colors = ["#d62728", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd"]

    for ax_idx, sid in enumerate(subjects):
        ax = axes[ax_idx]

        if sid not in all_results or not all_results[sid]:
            ax.set_title(f"{sid}\n(Pipeline failed)", size=11)
            continue

        res = all_results[sid]
        is_normalized = any(
            v is not None and v.get("normalized", True)
            for v in res.values()
        )

        values = []
        errs   = []
        ns     = []

        for domain in domains:
            d_res = res.get(domain)
            if d_res:
                val = d_res["mean"].get(PRIMARY_FEATURE, np.nan)
                values.append(val if val is not None else np.nan)
                errs.append(d_res["std"].get(PRIMARY_FEATURE, 0.0) or 0.0)
                ns.append(d_res["n"])
            else:
                values.append(np.nan)
                errs.append(0.0)
                ns.append(0)

        if is_normalized:
            y_min, y_max = y_min_norm, y_max_norm
            y_label_suffix = "σ"
            baseline_ref   = 0.0
        else:
            raw_vals = [v for v in values if not np.isnan(v)]
            y_min = min(raw_vals) * 0.9 if raw_vals else 0
            y_max = max(raw_vals) * 1.1 if raw_vals else 1
            y_label_suffix = " (raw)"
            baseline_ref   = None

        color = colors[ax_idx % len(colors)]
        values_plot = values + [values[0]]

        ax.plot(angles, values_plot, linewidth=2.0, color=color)
        
        # Only fill if all domains are valid to avoid matplotlib NaN rendering issues
        if not np.isnan(values).any():
            ax.fill(angles, values_plot, color=color, alpha=0.18)

        if baseline_ref is not None:
            ax.plot(angles, [baseline_ref] * len(angles), "k--", linewidth=1.0, alpha=0.45)

        span = y_max - y_min
        for angle, val, err, n in zip(angles[:-1], values, errs, ns):
            if np.isnan(val) or n <= 1:
                continue
            ax.plot([angle, angle], [val - err, val + err],
                    color=color, linewidth=1.8, alpha=0.55, solid_capstyle="round")

        for angle, val, err, n in zip(angles[:-1], values, errs, ns):
            if np.isnan(val) or n == 0:
                ax.annotate("n=0", xy=(angle, y_min + span * 0.1),
                            ha="center", va="center", fontsize=6.5, color="#cc0000")
                continue
            r_label = val + err + span * 0.07
            label_color = "#aaaaaa" if n == 1 else "#444444"
            label_text  = f"n={n}*" if n == 1 else f"n={n}"
            ax.annotate(label_text, xy=(angle, r_label),
                        ha="center", va="center", fontsize=6.5, color=label_color)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(domain_labels, size=8)
        ax.set_ylim(y_min, y_max)

        y_ticks = np.round(np.linspace(y_min, y_max, 5), 1)
        ax.set_yticks(y_ticks)
        ax.set_yticklabels([f"{v:.1f}{y_label_suffix}" for v in y_ticks], size=7)

        title_suffix = "\n[RAW UNITS - baseline n<4]" if not is_normalized else ""
        ax.set_title(f"Subject {sid}{title_suffix}", size=11, weight="bold", pad=20)
        ax.grid(True, alpha=0.25)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"\n  Group radar chart saved -> {out_path}")
