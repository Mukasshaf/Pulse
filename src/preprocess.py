"""
preprocess.py
-------------
Signal preprocessing for PPG (BVP) and EDA (GSR) signals.
All functions are parameterized by sampling rate — same code runs on
WESAD data and live hardware output.

Pipeline per signal:
    BVP  → Butterworth BPF (0.5–5 Hz) → peak detection → IBI series
    EDA  → low-pass filter (1 Hz) → EMD decomposition → SCL + SCR
    ACC  → variance per window → motion artifact flag

Public API:
    clean_bvp(bvp, fs)              → cleaned BVP array
    detect_peaks(bvp_clean, fs)     → peak indices + IBI array (ms)
    decompose_eda(eda, fs)          → dict with scl, scr, eda_clean
    flag_motion_artifacts(acc, fs, window_s, threshold) → bool mask (True = artifact)
    preprocess_subject(subject)     → all of the above in one call
"""

import numpy as np
from scipy.signal import butter, sosfiltfilt
import neurokit2 as nk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wesad_loader import load_subject


# ── BVP / PPG ───────────────────────────────────────────────────────────────

def clean_bvp(bvp: np.ndarray, fs: int = 64) -> np.ndarray:
    """
    4th order Butterworth BPF: 0.5 – 5 Hz
    Covers physiological HR range (30–300 BPM).
    Upper cutoff can be tightened to 3.5 Hz if hardware has motion noise.
    """
    low  = 0.5 / (fs / 2)
    high = min(5.0 / (fs / 2), 0.99)
    sos  = butter(4, [low, high], btype="band", output="sos")
    return sosfiltfilt(sos, bvp).astype(np.float32)


def detect_peaks(bvp_clean: np.ndarray, fs: int = 64) -> dict:
    """
    Detect systolic peaks in cleaned BVP and compute IBI series.

    Applies two-stage cleaning:
      1. Physiological plausibility: 300-2000 ms (30-200 BPM)
      2. Local median filter: remove IBIs deviating > 30% from
         rolling 5-beat median — catches missed/double peaks that
         slip through the plausibility gate.
    """
    from scipy.ndimage import median_filter

    ppg_signals, info = nk.ppg_process(bvp_clean, sampling_rate=fs)
    peaks = info["PPG_Peaks"]

    if len(peaks) < 2:
        return {"peaks": peaks, "ibi_ms": np.array([]),
                "ibi_idx": np.array([]), "mean_hr": np.nan}

    ibi_samples = np.diff(peaks)
    ibi_ms      = (ibi_samples / fs) * 1000.0
    ibi_idx     = peaks[1:]

    # Stage 1: physiological plausibility (30-200 BPM)
    valid   = (ibi_ms >= 300) & (ibi_ms <= 2000)
    ibi_ms  = ibi_ms[valid]
    ibi_idx = ibi_idx[valid]

    # Stage 2: local median filter — remove outliers > 30% from 5-beat median
    if len(ibi_ms) >= 5:
        ibi_median = median_filter(ibi_ms, size=5, mode="nearest")
        ratio      = np.abs(ibi_ms - ibi_median) / (ibi_median + 1e-6)
        clean      = ratio < 0.30
        ibi_ms     = ibi_ms[clean]
        ibi_idx    = ibi_idx[clean]

    mean_hr = 60000.0 / np.mean(ibi_ms) if len(ibi_ms) > 0 else np.nan

    return {
        "peaks":   peaks,
        "ibi_ms":  ibi_ms.astype(np.float32),
        "ibi_idx": ibi_idx,
        "mean_hr": float(mean_hr),
    }

# ── EDA / GSR ────────────────────────────────────────────────────────────────

def decompose_eda(eda: np.ndarray, fs: int = 4) -> dict:
    """
    Decompose raw EDA into tonic (SCL) and phasic (SCR) components
    using neurokit2's eda_process.

    Returns
    -------
    dict:
        eda_clean : filtered EDA array
        scl       : tonic component (slow baseline)
        scr       : phasic component (event-driven spikes)
        scr_peaks : indices of detected SCR peaks
        raw       : original input
    """
    eda_signals, info = nk.eda_process(eda, sampling_rate=fs)

    eda_clean = eda_signals["EDA_Clean"].values.astype(np.float32)
    scl       = eda_signals["EDA_Tonic"].values.astype(np.float32)
    scr       = eda_signals["EDA_Phasic"].values.astype(np.float32)

    scr_peaks = info.get("SCR_Peaks", np.array([], dtype=int))
    if hasattr(scr_peaks, "values"):
        scr_peaks = scr_peaks.values
    scr_peaks = np.asarray(scr_peaks, dtype=int)

    return {
        "eda_clean": eda_clean,
        "scl":       scl,
        "scr":       scr,
        "scr_peaks": scr_peaks,
        "raw":       eda.astype(np.float32),
    }


# ── Motion artifact detection ────────────────────────────────────────────────

def flag_motion_artifacts(acc: np.ndarray, fs: int = 32,
                          window_s: float = 1.0,
                          threshold: float = 50.0) -> np.ndarray:
    """
    Flag windows with high ACC variance as motion artifacts.

    Returns
    -------
    artifact_mask : bool array, length = number of 1s windows
                    True = artifact present
    """
    magnitude = np.sqrt(np.sum(acc.astype(np.float32) ** 2, axis=1))
    magnitude -= np.mean(magnitude)

    window_samples = int(window_s * fs)
    n_windows      = len(magnitude) // window_samples

    artifact_mask = np.zeros(n_windows, dtype=bool)
    for i in range(n_windows):
        seg = magnitude[i * window_samples: (i + 1) * window_samples]
        artifact_mask[i] = np.var(seg) > threshold

    return artifact_mask


# ── Combined per-subject preprocessing ──────────────────────────────────────

def preprocess_subject(subject: dict) -> dict:
    """
    Run full preprocessing pipeline on a loaded subject dict.
    Input: output of wesad_loader.load_subject()
    """
    sid    = subject["sid"]
    fs_bvp = subject["fs"]["bvp"]
    fs_eda = subject["fs"]["eda"]
    fs_acc = subject["fs"]["acc"]

    print(f"  Preprocessing S{sid}...")

    bvp_clean = clean_bvp(subject["bvp"], fs=fs_bvp)
    peaks     = detect_peaks(bvp_clean, fs=fs_bvp)
    print(f"    BVP  → {len(peaks['peaks'])} peaks  mean HR = {peaks['mean_hr']:.1f} BPM")

    eda_results = decompose_eda(subject["eda"], fs=fs_eda)
    print(f"    EDA  → {len(eda_results['scr_peaks'])} SCR peaks  "
          f"SCL range = [{eda_results['scl'].min():.4f}, {eda_results['scl'].max():.4f}]")

    artifact_mask = flag_motion_artifacts(subject["acc"], fs=fs_acc)
    print(f"    ACC  → {artifact_mask.mean() * 100:.1f}% windows flagged as artifacts")

    return {
        "sid":           sid,
        "bvp_clean":     bvp_clean,
        "peaks":         peaks,
        "eda":           eda_results,
        "artifact_mask": artifact_mask,
        "labels":        subject["labels"],
        "fs":            subject["fs"],
    }


# ── Validation plot ──────────────────────────────────────────────────────────

def plot_validation(subject_raw: dict, preprocessed: dict,
                    save_path: str = "outputs/plots/preprocess_validation.png",
                    n_seconds: int = 30) -> None:
    """
    4-panel validation plot:
        1. Raw BVP vs cleaned BVP
        2. Detected peaks on cleaned BVP
        3. EDA SCL/SCR decomposition
        4. ACC magnitude with artifact flags
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from pathlib import Path

    Path(save_path).parent.mkdir(parents=True, exist_ok=True)

    fs_bvp = subject_raw["fs"]["bvp"]
    fs_eda = subject_raw["fs"]["eda"]
    fs_acc = subject_raw["fs"]["acc"]
    sid    = subject_raw["sid"]

    n_bvp = n_seconds * fs_bvp
    n_eda = n_seconds * fs_eda
    n_acc = n_seconds * fs_acc

    t_bvp = np.arange(n_bvp) / fs_bvp
    t_eda = np.arange(n_eda) / fs_eda
    t_acc = np.arange(n_acc) / fs_acc

    fig, axes = plt.subplots(4, 1, figsize=(14, 12))
    fig.suptitle(f"GPAMS — Preprocessing Validation  (S{sid}, first {n_seconds}s)",
                 fontsize=13, fontweight="bold")

    # Panel 1: Raw vs clean BVP
    ax = axes[0]
    ax.plot(t_bvp, subject_raw["bvp"][:n_bvp],
            color="#888888", alpha=0.6, linewidth=0.8, label="Raw BVP")
    ax.plot(t_bvp, preprocessed["bvp_clean"][:n_bvp],
            color="#2563EB", linewidth=1.0, label="Cleaned BVP (0.5–5 Hz BPF)")
    ax.set_ylabel("Amplitude (ADC)")
    ax.set_title("BVP — Raw vs Filtered")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Panel 2: Peaks on cleaned BVP
    ax = axes[1]
    ax.plot(t_bvp, preprocessed["bvp_clean"][:n_bvp],
            color="#2563EB", linewidth=0.9, label="Cleaned BVP")
    peaks_in_range = preprocessed["peaks"]["peaks"]
    peaks_in_range = peaks_in_range[peaks_in_range < n_bvp]
    ax.scatter(peaks_in_range / fs_bvp,
               preprocessed["bvp_clean"][peaks_in_range],
               color="#DC2626", s=20, zorder=5,
               label=f"Peaks (n={len(peaks_in_range)})")
    ax.set_ylabel("Amplitude")
    ax.set_title(f"BVP — Peak Detection  (mean HR = {preprocessed['peaks']['mean_hr']:.1f} BPM)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Panel 3: EDA decomposition
    ax = axes[2]
    ax.plot(t_eda, subject_raw["eda"][:n_eda],
            color="#888888", alpha=0.6, linewidth=0.8, label="Raw EDA")
    ax.plot(t_eda, preprocessed["eda"]["scl"][:n_eda],
            color="#059669", linewidth=1.2, label="SCL (tonic)")
    ax.plot(t_eda,
            preprocessed["eda"]["scr"][:n_eda] + preprocessed["eda"]["scl"][:n_eda],
            color="#D97706", linewidth=0.9, alpha=0.8, label="SCR offset (phasic)")
    scr_peaks_range = preprocessed["eda"]["scr_peaks"]
    scr_peaks_range = scr_peaks_range[scr_peaks_range < n_eda]
    if len(scr_peaks_range) > 0:
        ax.scatter(scr_peaks_range / fs_eda,
                   preprocessed["eda"]["eda_clean"][scr_peaks_range],
                   color="#7C3AED", s=30, zorder=5,
                   label=f"SCR peaks (n={len(scr_peaks_range)})")
    ax.set_ylabel("EDA (µS)")
    ax.set_title("EDA — SCL/SCR Decomposition")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Panel 4: ACC + artifact flags
    acc_seg   = subject_raw["acc"][:n_acc].astype(np.float32)
    magnitude = np.sqrt(np.sum(acc_seg ** 2, axis=1))
    magnitude -= np.mean(magnitude)
    ax = axes[3]
    ax.plot(t_acc, magnitude, color="#6B7280",
            linewidth=0.7, label="ACC magnitude (de-meaned)")
    win_s = 1.0
    for i, flag in enumerate(preprocessed["artifact_mask"]):
        if flag:
            x0 = i * win_s
            x1 = x0 + win_s
            if x0 < n_seconds:
                ax.axvspan(x0, min(x1, n_seconds), color="#FCA5A5", alpha=0.4)
    ax.set_ylabel("Magnitude")
    ax.set_xlabel("Time (s)")
    ax.set_title("ACC — Motion Artifact Windows (red = flagged)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close()
    print(f"\n  Validation plot saved → {save_path}")


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sid      = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    data_dir = sys.argv[2] if len(sys.argv) > 2 else "data/WESAD"

    subject      = load_subject(sid, data_dir)
    preprocessed = preprocess_subject(subject)

    print("\nGenerating validation plot...")
    plot_validation(subject, preprocessed,
                    save_path=f"outputs/plots/preprocess_validation_S{sid}.png")

    ibi = preprocessed["peaks"]["ibi_ms"]
    if len(ibi) > 0:
        print(f"\n  IBI stats: n={len(ibi)}  mean={np.mean(ibi):.1f}ms  "
              f"std={np.std(ibi):.1f}ms  range=[{ibi.min():.0f}, {ibi.max():.0f}]ms")