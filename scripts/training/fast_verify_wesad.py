import sys, glob
from pathlib import Path
import pandas as pd

sys.path.insert(0, "src")
from classifier import train_loso

feat_dir = Path("outputs/features")
files = sorted(feat_dir.glob("S*_norm.csv"))
print(f"Found {len(files)} normalized feature files.")

subject_dfs = [pd.read_csv(f) for f in files]
results = train_loso(subject_dfs, run_grid_search=False)

f1 = results["aggregate"]["f1_macro"]
print(f"\nWESAD LOSO F1-macro: {f1:.4f}")
print(f"Expected:           0.9503")
print(f"Match: {'YES' if abs(f1 - 0.9503) < 0.01 else 'NO'}")

for fold in results["fold_results"]:
    assert isinstance(fold["test_sid"], int), f"Expected int, got {type(fold['test_sid'])}"
print("test_sid type check: all int (WESAD path unaffected)")
