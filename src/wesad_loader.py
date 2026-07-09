"""
wesad_loader.py
---------------
Loads WESAD subject .pkl files and extracts wrist signals with
label alignment. All downstream modules consume the output of load_subject().

WESAD signal layout (wrist):
    BVP  — 64 Hz  (Blood Volume Pulse / PPG proxy)
    EDA  —  4 Hz  (Electrodermal Activity / GSR proxy)
    ACC  — 32 Hz  (Accelerometer — 3-axis)
    TEMP —  4 Hz  (Skin temperature — not used in pipeline)

Labels are stored at chest rate (700 Hz) and are resampled here to
match each wrist signal's native sampling rate.

Label values:
    0 = not defined / transient
    1 = baseline
    2 = stress
    3 = amusement
    4 = meditation
"""

import pickle
import numpy as np
from pathlib import Path


# ── Sampling rates ──────────────────────────────────────────────────────────
FS = {
    "bvp":   64,
    "eda":    4,
    "acc":   32,
    "temp":   4,
    "label": 700,   # chest sensor rate — source of ground-truth labels
}

LABEL_NAMES = {
    0: "undefined",
    1: "baseline",
    2: "stress",
    3: "amusement",
    4: "meditation",
}


# ── Core loader ─────────────────────────────────────────────────────────────
def load_subject(subject_id: int, data_dir: str | Path = "data/WESAD") -> dict:
    """
    Load one WESAD subject and return aligned wrist signals + labels.

    Parameters
    ----------
    subject_id : int
        Subject number, e.g. 2 for S2.pkl
    data_dir : str or Path
        Root WESAD directory. Expects data_dir/S{id}/S{id}.pkl

    Returns
    -------
    dict with keys:
        bvp    : np.ndarray  shape (N,)       — 64 Hz
        eda    : np.ndarray  shape (M,)       —  4 Hz
        acc    : np.ndarray  shape (K, 3)     — 32 Hz, columns = x, y, z
        labels : dict of np.ndarray — keys: 'bvp', 'eda', 'acc'
                 each array has same length as its signal, values 0-4
        fs     : dict — sampling rates for each signal
        sid    : int  — subject id
        pkl_path : Path — resolved path to source file
    """
    pkl_path = Path(data_dir) / f"S{subject_id}" / f"S{subject_id}.pkl"

    if not pkl_path.exists():
        raise FileNotFoundError(
            f"WESAD file not found: {pkl_path}\n"
            f"Expected structure: {data_dir}/S{{id}}/S{{id}}.pkl"
        )

    with open(pkl_path, "rb") as f:
        raw = pickle.load(f, encoding="latin1")

    wrist = raw["signal"]["wrist"]

    bvp  = wrist["BVP"].flatten().astype(np.float32)
    eda  = wrist["EDA"].flatten().astype(np.float32)
    acc  = wrist["ACC"].astype(np.float32)          # shape (K, 3)
    label_700hz = raw["label"].flatten().astype(np.int8)

    # Resample labels from 700 Hz to each signal's native rate
    labels = {
        "bvp": _resample_labels(label_700hz, FS["label"], FS["bvp"],  len(bvp)),
        "eda": _resample_labels(label_700hz, FS["label"], FS["eda"],  len(eda)),
        "acc": _resample_labels(label_700hz, FS["label"], FS["acc"],  len(acc)),
    }

    return {
        "sid":      subject_id,
        "bvp":      bvp,
        "eda":      eda,
        "acc":      acc,
        "labels":   labels,
        "fs":       {"bvp": FS["bvp"], "eda": FS["eda"], "acc": FS["acc"]},
        "pkl_path": pkl_path,
    }


def _resample_labels(labels_src: np.ndarray, fs_src: int,
                     fs_dst: int, target_len: int) -> np.ndarray:
    """
    Nearest-neighbour resample of a label array from fs_src to fs_dst.
    Clips to target_len to handle rounding at boundaries.
    """
    n_src = len(labels_src)
    # Map each destination sample index to a source sample index
    dst_indices = np.arange(target_len)
    src_indices = np.round(dst_indices * (fs_src / fs_dst)).astype(int)
    src_indices = np.clip(src_indices, 0, n_src - 1)
    return labels_src[src_indices]


# ── Condition extraction ─────────────────────────────────────────────────────
def get_condition_segments(subject: dict, signal: str = "bvp",
                           condition: int = 2) -> list[dict]:
    """
    Extract contiguous segments of a given condition from a signal.

    Parameters
    ----------
    subject   : output of load_subject()
    signal    : 'bvp' | 'eda' | 'acc'
    condition : label value (1=baseline, 2=stress, 3=amusement, 4=meditation)

    Returns
    -------
    List of dicts, each with:
        'data'       : np.ndarray — signal values for that segment
        'start_idx'  : int — start index in full signal array
        'end_idx'    : int — end index (exclusive)
        'duration_s' : float — segment duration in seconds
    """
    sig_data = subject[signal]
    sig_labels = subject["labels"][signal]
    fs = subject["fs"][signal]

    mask = (sig_labels == condition).astype(int)
    # Find contiguous runs
    edges = np.diff(np.concatenate([[0], mask, [0]]))
    starts = np.where(edges == 1)[0]
    ends   = np.where(edges == -1)[0]

    segments = []
    for s, e in zip(starts, ends):
        seg = sig_data[s:e] if sig_data.ndim == 1 else sig_data[s:e, :]
        segments.append({
            "data":       seg,
            "start_idx":  s,
            "end_idx":    e,
            "duration_s": (e - s) / fs,
        })

    return segments


def get_baseline(subject: dict, signal: str = "bvp") -> np.ndarray:
    """Convenience wrapper — returns the baseline segment data for a signal."""
    segs = get_condition_segments(subject, signal=signal, condition=1)
    if not segs:
        raise ValueError(f"No baseline (label=1) found for S{subject['sid']} / {signal}")
    # WESAD has one baseline block — return it directly
    return segs[0]["data"]


def get_stress(subject: dict, signal: str = "bvp") -> np.ndarray:
    """Convenience wrapper — returns the stress segment data for a signal."""
    segs = get_condition_segments(subject, signal=signal, condition=2)
    if not segs:
        raise ValueError(f"No stress (label=2) found for S{subject['sid']} / {signal}")
    return segs[0]["data"]


# ── Summary ──────────────────────────────────────────────────────────────────
def summary(subject: dict) -> None:
    """Print a sanity-check summary for a loaded subject."""
    sid = subject["sid"]
    fs  = subject["fs"]

    print(f"\n{'='*50}")
    print(f"  WESAD Subject S{sid}")
    print(f"{'='*50}")

    for sig in ("bvp", "eda", "acc"):
        data = subject[sig]
        labs = subject["labels"][sig]
        n    = len(data)
        dur  = n / fs[sig]

        # Condition breakdown
        cond_str = "  ".join(
            f"{LABEL_NAMES[c]}={np.sum(labs == c) / fs[sig]:.0f}s"
            for c in sorted(LABEL_NAMES)
            if np.sum(labs == c) > 0
        )

        shape_str = str(data.shape)
        print(f"\n  {sig.upper():4s}  {fs[sig]:>3d} Hz  shape={shape_str:>12s}"
              f"  total={dur:.1f}s")
        print(f"        {cond_str}")
        print(f"        range=[{data.min():.4f}, {data.max():.4f}]"
              f"  mean={data.mean():.4f}")

    print(f"\n  Source: {subject['pkl_path']}")
    print(f"{'='*50}\n")


# ── CLI quick-check ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    sid = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    data_dir = sys.argv[2] if len(sys.argv) > 2 else "data/WESAD"

    print(f"Loading S{sid} from {data_dir} ...")
    subject = load_subject(sid, data_dir)
    summary(subject)

    # Quick label alignment check
    bvp_len = len(subject["bvp"])
    lab_len = len(subject["labels"]["bvp"])
    print(f"  Label alignment check: BVP samples={bvp_len}, label array={lab_len}",
          "✓ MATCH" if bvp_len == lab_len else "✗ MISMATCH")
    print()