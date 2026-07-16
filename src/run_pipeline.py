

import argparse
import sys
import os
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wesad_loader import load_subject
from preprocess import preprocess_subject
from features import extract_window_features, save_features
from normalize import normalize_subject, save_normalized
from classifier import train_loso, compare_models, plot_results, save_model

import json


def run_subject(sid: int, data_dir: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    print(f"\n{'─'*50}")
    print(f"  Processing S{sid}")
    print(f"{'─'*50}")

    subject      = load_subject(sid, data_dir)
    preprocessed = preprocess_subject(subject)
    df_raw       = extract_window_features(preprocessed)

    if df_raw.empty:
        print(f"  SKIP S{sid} — no valid windows")
        return None, None

    df_norm, baseline_stats = normalize_subject(df_raw)
    save_normalized(df_raw, df_norm, baseline_stats, sid)

    print(f"  S{sid} → {len(df_norm)} windows  "
          f"(baseline={len(df_norm[df_norm.label==1])}, "
          f"stress={len(df_norm[df_norm.label==2])})")
    return df_raw, df_norm


def main():
    # parser = argparse.ArgumentParser()
    # parser.add_argument("--sids", nargs="+", type=int,
    #                     default=[2, 3, 4, 5, 6],
    #                     help="Subject IDs to process")
    # parser.add_argument("--data_dir", type=str, default="data/WESAD")
    # parser.add_argument("--no_grid_search", action="store_true",
    #                     help="Skip GridSearchCV (faster, uses base RF params)")
    # args = parser.parse_args()

    # print(f"\nGPAMS Pipeline — subjects: {args.sids}")

    # #  Run per-subject pipeline 
    # norm_dfs = []
    # failed   = []

    # for sid in args.sids:
    #     try:
    #         _, df_norm = run_subject(sid, args.data_dir)
    #         if df_norm is not None:
    #             norm_dfs.append(df_norm)
    #     except Exception as e:
    #         print(f"  ERROR S{sid}: {e}")
    #         failed.append(sid)

    # if failed:
    #     print(f"\n  Failed subjects: {failed}")


    #parallel processing
    from concurrent.futures import ProcessPoolExecutor, as_completed
    import multiprocessing as mp
    parser = argparse.ArgumentParser()
    parser.add_argument("--sids", nargs="+", type=int, default=[2, 3, 4, 5, 6])
    parser.add_argument("--data_dir", type=str, default="data/WESAD")
    parser.add_argument("--no_grid_search", action="store_true")
    parser.add_argument("--workers", type=int, default=max(1, mp.cpu_count() - 1))
    args = parser.parse_args()

    print(f"\nGPAMS Pipeline — subjects: {args.sids}  (workers={args.workers})")

    norm_dfs = []
    failed   = []

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_subject, sid, args.data_dir): sid
                   for sid in args.sids}
        for future in as_completed(futures):
            sid = futures[future]
            try:
                _, df_norm = future.result()
                if df_norm is not None:
                    norm_dfs.append(df_norm)
            except Exception as e:
                print(f"  ERROR S{sid}: {e}")
                failed.append(sid)

    if failed:
        print(f"\n  Failed subjects: {failed}")



    if len(norm_dfs) < 2:
        print("\n  Need at least 2 subjects for LOSO. Exiting.")
        return

    #  LOSO cross-validation 
    print(f"\n{'='*50}")
    print(f"  LOSO Cross-Validation ({len(norm_dfs)} subjects)")
    print(f"{'='*50}")

    run_gs = not args.no_grid_search
    results = train_loso(norm_dfs, run_grid_search=run_gs)

    #  Print aggregate summary 
    agg = results["aggregate"]
    print(f"\n{'='*50}")
    print(f"  Final Results")
    print(f"{'='*50}")
    print(f"  Accuracy    : {agg['accuracy']:.4f}")
    print(f"  F1-macro    : {agg['f1_macro']:.4f}")
    print(f"  Specificity : {agg['specificity']:.4f}")
    print(f"  Sensitivity : {agg['sensitivity']:.4f}")

    print(f"\n  Feature Importance (ranked):")
    importance = results["importance"]
    for feat, val in sorted(importance.items(), key=lambda x: -x[1]):
        bar = "█" * int(val * 40)
        print(f"    {feat:<16} {val:.4f}  {bar}")

    #  Save outputs 
    Path("outputs/results").mkdir(parents=True, exist_ok=True)
    Path("outputs/models").mkdir(parents=True, exist_ok=True)

    plot_results(results, out_dir="outputs/plots")
    save_model(results["best_clf"], "outputs/models/rf_loso.pkl")

    # Save fold-level results
    fold_df = pd.DataFrame([
        {k: v for k, v in f.items() if k != "confusion_matrix"}
        for f in results["fold_results"]
    ])
    fold_df.to_csv("outputs/results/loso_fold_results.csv", index=False)
    print(f"\n  Fold results → outputs/results/loso_fold_results.csv")

    # Save best params
    params = {k: v for k, v in results["best_params"].items()
              if isinstance(v, (int, float, str, bool, type(None)))}
    with open("outputs/models/best_params_loso.json", "w") as f:
        json.dump(params, f, indent=2)

    #  Model comparison on pooled data 
    print(f"\n  Running model comparison on pooled data...")
    df_all = pd.concat(norm_dfs, ignore_index=True)
    comparison_df = compare_models(df_all)
    comparison_df.to_csv("outputs/results/model_comparison_loso.csv", index=False)
    print(f"  Model comparison → outputs/results/model_comparison_loso.csv")


if __name__ == "__main__":
    main()