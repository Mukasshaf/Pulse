"""
group_report.py — Multi-subject domain activation group comparison.

Reads every outputs/features/domain/*_domain_features.csv present at run time
(any N), reconstructs the results dict, and produces the multi-subject
comparison radar chart + summary CSV.

Run this manually at any N (e.g., N=3 pilot, N=15 Phase 6):
    uv run python group_report.py
    uv run python group_report.py --features-dir outputs/features/domain --out-dir outputs/group
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ── Path setup ────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT / "src" / "pipeline"))
sys.path.insert(0, str(_ROOT / "src"))

from per_subject_features import (
    FEATURE_COLS,
    DOMAIN_IDS,
    plot_group_radar,
)


def load_domain_features_csv(csv_path: Path) -> tuple[str, dict]:
    """
    Read a per-subject domain features CSV (produced by save_domain_features_csv)
    and reconstruct the results dict that plot_group_radar() expects.

    Returns: (subject_id, results_dict)
    """
    df = pd.read_csv(csv_path)
    if df.empty or "subject" not in df.columns:
        raise ValueError(f"Invalid domain features CSV: {csv_path}")

    subject_id = df["subject"].iloc[0]
    results: dict = {}

    for _, row in df.iterrows():
        domain = row["domain"]
        n = int(row["n_windows"])
        normalized = bool(row.get("normalized", True))
        art_frac_mean = float(row.get("art_frac_mean", np.nan))

        if n == 0:
            results[domain] = None
            continue

        mean_d = {c: row.get(f"mean_{c}", np.nan) for c in FEATURE_COLS}
        std_d  = {c: row.get(f"std_{c}",  np.nan) for c in FEATURE_COLS}

        results[domain] = {
            "mean":         mean_d,
            "std":          std_d,
            "n":            n,
            "normalized":   normalized,
            "art_frac_mean": art_frac_mean,
        }

    return subject_id, results


def save_group_summary_csv(
    all_results: dict,
    subjects: list[str],
    out_path: Path,
) -> None:
    """Write a consolidated group-level summary CSV."""
    from per_subject_features import DOMAIN_IDS, FEATURE_COLS
    records = []
    for sid in subjects:
        if sid not in all_results:
            continue
        for domain in DOMAIN_IDS:
            res = all_results[sid].get(domain)
            if res is None:
                row = {"subject": sid, "domain": domain, "n_windows": 0}
                for c in FEATURE_COLS:
                    row[f"mean_{c}"] = np.nan
                    row[f"std_{c}"]  = np.nan
            else:
                row = {
                    "subject": sid,
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
    print(f"  Group summary CSV saved -> {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pulse group domain activation report — run at any N"
    )
    parser.add_argument(
        "--features-dir", type=Path,
        default=Path("outputs/features/domain"),
        help="Directory containing *_domain_features.csv files",
    )
    parser.add_argument(
        "--out-dir", type=Path,
        default=Path("outputs/group"),
        help="Output directory for group radar and summary CSV",
    )
    args = parser.parse_args()

    feature_csvs = sorted(args.features_dir.glob("*_domain_features.csv"))
    if not feature_csvs:
        print(f"ERROR: No *_domain_features.csv files found in {args.features_dir}")
        print("       Run at least one subject through run_session.py first.")
        sys.exit(1)

    print(f"Pulse — Group Domain Activation Report")
    print("=" * 60)
    print(f"  Found {len(feature_csvs)} subject file(s) in {args.features_dir}")

    all_results: dict = {}
    subjects: list[str] = []

    for csv_path in feature_csvs:
        try:
            sid, res = load_domain_features_csv(csv_path)
            all_results[sid] = res
            subjects.append(sid)
            valid_domains = sum(1 for v in res.values() if v is not None)
            print(f"  Loaded {sid}: {valid_domains}/7 valid domains")
        except Exception as exc:
            print(f"  WARNING: Could not load {csv_path.name}: {exc}")

    if not subjects:
        print("ERROR: No subjects successfully loaded.")
        sys.exit(1)

    print(f"\n  Subjects: {subjects}")

    radar_out = args.out_dir / "domain_map.png"
    plot_group_radar(all_results, subjects, radar_out)

    csv_out = args.out_dir / "domain_map_feature_summary.csv"
    save_group_summary_csv(all_results, subjects, csv_out)

    print(f"\nDone. N={len(subjects)} subjects.")
    print(f"  Radar   -> {radar_out}")
    print(f"  Summary -> {csv_out}")


if __name__ == "__main__":
    main()
