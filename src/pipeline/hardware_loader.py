"""
hardware_loader.py -- single mapping point between raw ESP32 CSV output
and the internal column names / sampling rate the rest of the pipeline
(preprocess.py, features.py, normalize.py) expects.

Raw hardware CSV schema (current firmware, confirmed from captures):
    sample_idx, timestamp_ms, pulse_raw, gsr_raw, acc_x, acc_y, acc_z

Internal pipeline column names (matching wesad_loader.py output keys):
    bvp  -- PPG/BVP signal  (was: pulse_raw)
    eda  -- EDA/GSR signal  (was: gsr_raw)
    acc_x, acc_y, acc_z unchanged

True sampling rate: 66.67 Hz (1000 / SAMPLE_INTERVAL_MS=15)
Do NOT hardcode 64 anywhere downstream of this file -- always use HW_FS
or read df.attrs["fs"] from the returned DataFrame.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# True hardware fs -- confirmed from real timestamp deltas across captures
# (SAMPLE_INTERVAL_MS = 15 in firmware -> 1000/15 = 66.6667 Hz)
HW_FS: float = 1000.0 / 15.0   # 66.6667 Hz

# Maps raw ESP32 CSV column names -> internal pipeline names
# Must match what wesad_loader.py returns (keys: "bvp", "eda", "acc")
COLUMN_MAP = {
    "pulse_raw": "bvp",
    "gsr_raw":   "eda",
    # acc_x, acc_y, acc_z are kept as-is (pipeline reads them by name)
}

REQUIRED_COLUMNS = {
    "sample_idx", "timestamp_ms", "pulse_raw", "gsr_raw",
    "acc_x", "acc_y", "acc_z",
}


def load_hardware_csv(path: str | Path) -> dict:
    """
    Load one hardware CSV and return a dict matching the shape that
    preprocess.preprocess_subject() expects:

        {
            "sid":    path stem (e.g. "recorded_data_120s"),
            "bvp":    np.ndarray float32, shape (N,)
            "eda":    np.ndarray float32, shape (N,)
            "acc":    np.ndarray float32, shape (N, 3)
            "labels": {"bvp": None, "eda": None, "acc": None}  -- no labels on hardware
            "fs":     {"bvp": 66.67, "eda": 66.67, "acc": 66.67}
            "timestamp_ms":  np.ndarray int64, shape (N,)
            "sample_idx":    np.ndarray int64, shape (N,)
        }

    Raises ValueError on missing columns or non-monotonic timestamps.
    """
    path = Path(path)
    df   = pd.read_csv(path)

    # --- Column validation ---
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"hardware CSV missing expected columns: {missing}\n"
            f"  Found: {list(df.columns)}\n"
            f"  File:  {path}"
        )

    # --- Timestamp monotonicity check ---
    ts = df["timestamp_ms"].values.astype(np.int64)
    if np.any(np.diff(ts) < 0):
        n_backwards = int(np.sum(np.diff(ts) < 0))
        raise ValueError(
            f"timestamp_ms is not monotonically increasing in {path.name} "
            f"({n_backwards} backwards steps detected)"
        )

    # --- sample_idx gap report (warn, don't raise) ---
    idx_diffs = np.diff(df["sample_idx"].values)
    gap_events = int(np.sum(idx_diffs != 1))
    if gap_events > 0:
        missed = int(np.sum(idx_diffs[idx_diffs > 1] - 1))
        print(
            f"  [hardware_loader] WARNING: {gap_events} gap event(s) in {path.name} "
            f"({missed} missed sample(s))"
        )

    # --- Extract arrays ---
    bvp = df["pulse_raw"].values.astype(np.float32)
    eda = df["gsr_raw"].values.astype(np.float32)
    acc = df[["acc_x", "acc_y", "acc_z"]].values.astype(np.float32)

    fs_dict = {"bvp": HW_FS, "eda": HW_FS, "acc": HW_FS}

    return {
        "sid":          path.stem,
        "bvp":          bvp,
        "eda":          eda,
        "acc":          acc,
        "labels":       {"bvp": None, "eda": None, "acc": None},
        "fs":           fs_dict,
        "timestamp_ms": ts,
        "sample_idx":   df["sample_idx"].values.astype(np.int64),
    }




def load_condition_log(path: str | Path) -> pd.DataFrame:
    """
    Load a condition log CSV written by condition_logger.py.

    Expected schema (exactly as condition_logger.py writes it):
        condition, start_unix_ms, end_unix_ms

    Returns a DataFrame with those three columns, dtypes verified.
    Raises ValueError on missing columns.
    """
    path = Path(path)
    df   = pd.read_csv(path)

    required = {"condition", "start_unix_ms", "end_unix_ms"}
    missing  = required - set(df.columns)
    if missing:
        raise ValueError(
            f"condition log CSV missing columns: {missing}\n"
            f"  Expected: condition, start_unix_ms, end_unix_ms\n"
            f"  Found:    {list(df.columns)}\n"
            f"  File:     {path}\n"
            f"  Produced by src/condition_logger.py — check it wrote correctly."
        )

    df["start_unix_ms"] = df["start_unix_ms"].astype(np.int64)
    df["end_unix_ms"]   = df["end_unix_ms"].astype(np.int64)
    return df


def load_labeled_hardware_csv(csv_path: str | Path,
                               log_path:  str | Path,
                               subject_id: str | None = None) -> dict:
    """
    Load a hardware CSV and assign per-sample condition labels by joining
    it against a condition log (from condition_logger.py) on unix_ts_ms.

    The join key is unix_ts_ms injected by serial_reader.py into the sensor
    stream — this is a Unix-clock timestamp, not the ESP32's millis()-based
    timestamp_ms, which is why the clock-domain fix in serial_reader.py matters.

    Label mapping (from condition_labels.CONDITION_TO_LABEL):
        baseline           -> 1
        mental_arithmetic  -> 2   (stress class)
        stroop             -> 2   (stress class, collapsed with mental_arithmetic)
        unlabeled samples  -> 0   (excluded by features.extract_window_features)

    Naming convention (workplan §3.1.3):
        Subject feature CSVs produced from this loader's output should be saved as
        labeled_S{id}_hw.csv  (e.g. labeled_SHW01_hw.csv).
        Do not invent a different scheme — this matches the pattern eval_zero_shot.py
        and train_hw_loso.py glob for (labeled_S*_hw.csv).

    Args:
        csv_path:    Path to the hardware sensor CSV.
        log_path:    Path to the condition log CSV from condition_logger.py.
        subject_id:  Optional override for the 'sid' field.
                     Defaults to stem of csv_path. Pass e.g. "HW01" to use
                     the workplan naming scheme (recommended for Phase 3.1).

    Returns:
        Same dict shape as load_hardware_csv(), with labels dict populated.
    """
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from condition_labels import CONDITION_TO_LABEL

    data   = load_hardware_csv(csv_path)
    log_df = load_condition_log(log_path)

    # Use caller-supplied subject_id if given; else stem of csv_path
    if subject_id is not None:
        data["sid"] = subject_id

    # unix_ts_ms is injected by serial_reader.py as the host-side Unix clock.
    # If the key is missing, warn and fall back to timestamp_ms (less accurate).
    if "unix_ts_ms" in data:
        ts = data["unix_ts_ms"]
    else:
        print(
            "  [hardware_loader] WARNING: unix_ts_ms not found in data dict — "
            "falling back to timestamp_ms for condition join. "
            "This is less accurate; ensure serial_reader.py wrote unix_ts_ms."
        )
        ts = data["timestamp_ms"]

    n = len(ts)
    labels_arr = np.zeros(n, dtype=np.int32)   # 0 = unlabeled / undefined

    for _, row in log_df.iterrows():
        cond_name = str(row["condition"]).strip().lower()
        label_id  = CONDITION_TO_LABEL.get(cond_name, 0)
        if label_id == 0:
            print(
                f"  [hardware_loader] WARNING: unknown condition '{cond_name}' "
                f"in log — samples in this interval will be labeled 0 (excluded)."
            )
        mask = (ts >= row["start_unix_ms"]) & (ts < row["end_unix_ms"])
        labels_arr[mask] = label_id

    labeled_n = int(np.sum(labels_arr > 0))
    print(
        f"  [hardware_loader] Label join: {labeled_n}/{n} samples labeled "
        f"({100*labeled_n/n:.1f}%), {n - labeled_n} unlabeled (label=0, will be excluded)"
    )

    data["labels"] = {
        "bvp": labels_arr,
        "eda": labels_arr,
        "acc": labels_arr,
    }
    return data


# --- CLI quick-check ---
if __name__ == "__main__":
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "recorded_data_120s.csv"
    log_path = sys.argv[2] if len(sys.argv) > 2 else None

    if log_path:
        data = load_labeled_hardware_csv(csv_path, log_path)
        label_counts = {int(k): int(v) for k, v in
                        zip(*np.unique(data["labels"]["bvp"], return_counts=True))}
        print(f"  label distribution: {label_counts}")
    else:
        data = load_hardware_csv(csv_path)

    print(f"\n  hardware_loader -- {data['sid']}")
    print(f"  BVP  shape={data['bvp'].shape}  range=[{data['bvp'].min():.1f}, {data['bvp'].max():.1f}]")
    print(f"  EDA  shape={data['eda'].shape}  range=[{data['eda'].min():.1f}, {data['eda'].max():.1f}]")
    print(f"  ACC  shape={data['acc'].shape}")
    print(f"  fs   = {data['fs']}")
    print(f"  duration = {(data['timestamp_ms'][-1] - data['timestamp_ms'][0]) / 1000:.3f}s")
