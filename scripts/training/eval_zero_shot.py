"""
eval_zero_shot.py -- Phase 3, §3.2 Task 4.

Zero-shot evaluation: run the WESAD-trained RF classifier directly on
hardware-derived features. No retraining — the model's weights are frozen
as trained on WESAD. Reports accuracy and F1-macro to quantify the
domain-adaptation gap before hardware-only retraining.

Usage:
    python eval_zero_shot.py \
        --model  outputs/models/classifier.pkl \
        --features outputs/features/hw/  \
        [--out outputs/results/zero_shot_result.json]

    The --features directory must contain one CSV per subject following the
    workplan convention: labeled_S{id}_hw.csv (produced by features.py on
    hardware data via hardware_loader.load_labeled_hardware_csv + preprocess_hardware
    + extract_window_features).
"""

import argparse
import json
import pickle
import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    confusion_matrix, classification_report,
)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "pipeline"))
from classifier import FEATURE_COLS


def load_hw_features(features_dir: str) -> pd.DataFrame:
    """Load all labeled_S*_hw.csv files from features_dir into one DataFrame."""
    feat_dir = Path(features_dir)
    files = sorted(feat_dir.glob("labeled_*_hw.csv"))
    if not files:
        raise FileNotFoundError(
            f"No labeled_*_hw.csv files found in {features_dir}.\n"
            f"Run the feature extraction pipeline on hardware data first."
        )
    dfs = [pd.read_csv(f) for f in files]
    df  = pd.concat(dfs, ignore_index=True)
    print(f"  Loaded {len(files)} subject file(s): {[f.name for f in files]}")
    return df


def run_zero_shot(model_path: str, features_dir: str, out_path: str | None) -> dict:
    # Load model
    with open(model_path, "rb") as f:
        clf = pickle.load(f)
    print(f"  WESAD model loaded: {Path(model_path).name}")
    print(f"  Model type: {type(clf).__name__}")

    # Load hardware features
    df = load_hw_features(features_dir)
    df = df[df["label"].isin([1, 2])].dropna(subset=FEATURE_COLS).reset_index(drop=True)

    if df.empty:
        raise ValueError("No valid labeled windows (label 1 or 2) found in hardware features.")

    X      = df[FEATURE_COLS].values
    y_true = df["label"].values
    sids   = df["sid"].values if "sid" in df.columns else ["unknown"] * len(df)

    n_base   = int(np.sum(y_true == 1))
    n_stress = int(np.sum(y_true == 2))
    print(f"\n  Hardware windows: {len(df)} total  ({n_base} baseline, {n_stress} stress)")
    print(f"  Subjects: {sorted(set(sids))}")

    # Zero-shot predict
    y_pred = clf.predict(X)

    acc   = float(accuracy_score(y_true, y_pred))
    f1    = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    prec  = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    rec   = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    cm    = confusion_matrix(y_true, y_pred, labels=[1, 2]).tolist()

    print(f"\n  === Zero-shot result ===")
    print(f"  Accuracy   : {acc:.4f}")
    print(f"  F1-macro   : {f1:.4f}")
    print(f"  Precision  : {prec:.4f}")
    print(f"  Recall     : {rec:.4f}")
    print(f"\n{classification_report(y_true, y_pred, target_names=['baseline','stress'], zero_division=0)}")

    result = dict(
        mode="zero_shot",
        wesad_model=str(model_path),
        hw_features_dir=str(features_dir),
        n_subjects=len(set(sids)),
        n_windows=len(df),
        n_baseline=n_base,
        n_stress=n_stress,
        accuracy=acc,
        f1_macro=f1,
        precision=prec,
        recall=rec,
        confusion_matrix=cm,
    )

    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n  Result saved -> {out_path}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zero-shot WESAD model on hardware data")
    parser.add_argument("--model",    required=True, help="Path to WESAD classifier .pkl")
    parser.add_argument("--features", required=True, help="Dir with labeled_S*_hw.csv files")
    parser.add_argument("--out",      default=None,  help="Output JSON path (optional)")
    args = parser.parse_args()

    run_zero_shot(args.model, args.features, args.out)
