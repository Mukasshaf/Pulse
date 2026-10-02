"""
train_hw_loso.py -- Phase 3, §3.3 Task 1.

Train Random Forest from scratch on the 5-subject hardware dataset using
Leave-One-Subject-Out (LOSO) cross-validation. Reports per-fold and aggregate
metrics. Saves the model trained on all data after CV for Phase 4 use.

Usage:
    python train_hw_loso.py \
        --features outputs/features/hw/ \
        [--no-grid]                        (skip GridSearchCV, use RF_BASE_PARAMS) \
        [--out-model outputs/models/hw_classifier.pkl] \
        [--out-results outputs/results/hw_loso_results.json]

    The --features directory must contain labeled_S*_hw.csv files
    (naming convention: labeled_S{id}_hw.csv, e.g. labeled_SHW01_hw.csv).

NOTE: With only 5 subjects, LOSO gives 5 folds. Per-fold variance will be
higher than the WESAD 15-subject run — that is expected, not a red flag.
The M3 gate is aggregate F1-macro >= 0.65. See §3.3 Task 3 / go_nogo_check.py.
"""

import argparse
import json
import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "pipeline"))
from classifier import FEATURE_COLS, train_loso, save_model


def load_hw_features(features_dir: str) -> list[pd.DataFrame]:
    """
    Load all labeled_S*_hw.csv files from features_dir.
    Returns a list of per-subject DataFrames, one per file — matching the
    shape train_loso() expects (list of subject DataFrames).
    """
    feat_dir = Path(features_dir)
    files = sorted(feat_dir.glob("labeled_*_hw.csv"))
    if not files:
        raise FileNotFoundError(
            f"No labeled_*_hw.csv files found in {features_dir}.\n"
            f"Run the feature extraction pipeline on hardware data first."
        )
    dfs = [pd.read_csv(f) for f in files]
    print(f"  Loaded {len(files)} subject file(s): {[f.name for f in files]}")
    return dfs


def run_hw_loso(features_dir: str,
                run_grid_search: bool,
                out_model: str | None,
                out_results: str | None) -> dict:

    subject_dfs = load_hw_features(features_dir)

    # Validate subject count before handing off to train_loso
    all_sids = pd.concat(subject_dfs)["sid"].unique()
    n_subjects = len(all_sids)
    if n_subjects < 2:
        raise ValueError(
            f"LOSO requires >=2 subjects. Found {n_subjects}. "
            f"Collect more hardware data before running this script."
        )
    print(f"\n  Subject IDs: {sorted(all_sids)}")

    # Delegate to classifier.train_loso() — same function used for WESAD.
    # The int(test_sid) cast is now permissive (try/except) so string SIDs
    # like 'HW01' pass through without conversion.
    result = train_loso(subject_dfs, run_grid_search=run_grid_search)

    # Annotate with hardware-specific metadata for the results JSON
    result["mode"]       = "hw_loso"
    result["subject_ids"] = sorted(str(s) for s in all_sids)
    result["f1_std"]     = float(np.std([f["f1_macro"] for f in result["fold_results"]]))

    if out_model:
        save_model(result["best_clf"], out_model)

    if out_results:
        Path(out_results).parent.mkdir(parents=True, exist_ok=True)
        to_save = {k: v for k, v in result.items()
                   if k not in ("best_clf",) and isinstance(v, (str, int, float, list, dict, type(None)))}
        with open(out_results, "w") as f:
            json.dump(to_save, f, indent=2, default=str)
        print(f"  Results saved -> {out_results}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HW-only LOSO RF training (Phase 3)")
    parser.add_argument("--features",    required=True,
                        help="Dir with labeled_S*_hw.csv feature files")
    parser.add_argument("--no-grid",     action="store_true",
                        help="Skip GridSearchCV, use RF base params")
    parser.add_argument("--out-model",   default="outputs/models/hw_classifier.pkl",
                        help="Path to save trained model .pkl")
    parser.add_argument("--out-results", default="outputs/results/hw_loso_results.json",
                        help="Path to save per-fold JSON results")
    args = parser.parse_args()

    run_hw_loso(
        features_dir    = args.features,
        run_grid_search = not args.no_grid,
        out_model       = args.out_model,
        out_results     = args.out_results,
    )
