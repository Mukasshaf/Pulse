"""
plot_roc_curves.py — Generate publication-grade ROC curves for GPAMS.

Generates:
  1. outputs/plots/roc_wesad_benchmark.png:
     Model comparison ROC curves (Random Forest vs KNN vs SVM) on WESAD (N=15 subjects, LOSO CV).
  2. outputs/plots/roc_hardware_loso.png:
     Hardware LOSO CV ROC curves across live subjects (HW01–HW04), showing individual folds and Mean ROC.
  3. outputs/plots/roc_combined.png:
     Side-by-side 2-panel presentation slide figure.

Usage:
    uv run python plot_roc_curves.py
"""
import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import roc_curve, auc

FEATURE_COLS = [
    "mean_hr", "rmssd", "sdnn", "pnn50",
    "scr_count", "scr_max_amp", "scr_energy",
    "scr_epeak", "scl_mean"
]

def generate_roc_curves():
    out_dir = Path("outputs/plots")
    out_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------
    # 1. WESAD Dataset (N=15) - LOSO Cross-Validation
    # -------------------------------------------------------------
    print("Loading WESAD normalized feature datasets...")
    wesad_files = sorted(Path("outputs/features").glob("S*_norm.csv"))
    if not wesad_files:
        raise FileNotFoundError("No WESAD feature files found in outputs/features/")
    
    df_wesad = pd.concat([pd.read_csv(f) for f in wesad_files], ignore_index=True)
    df_wesad = df_wesad[df_wesad["label"].isin([1, 2])].copy()
    X_w = df_wesad[FEATURE_COLS].values
    y_w = (df_wesad["label"].values == 2).astype(int)  # 0: Baseline, 1: Stress
    groups_w = df_wesad["sid"].values

    logo = LeaveOneGroupOut()

    # Models to compare
    models = {
        "Random Forest (Production)": RandomForestClassifier(
            n_estimators=75, max_leaf_nodes=9, min_samples_split=5, random_state=42
        ),
        "KNN (k=5)": KNeighborsClassifier(n_neighbors=5),
        "SVM (RBF Kernel)": SVC(kernel="rbf", C=1.0, probability=True, random_state=42)
    }

    wesad_roc_data = {}
    print("Evaluating WESAD models via Leave-One-Subject-Out CV...")
    for name, clf in models.items():
        y_prob = np.zeros(len(y_w))
        for train_idx, test_idx in logo.split(X_w, y_w, groups_w):
            clf.fit(X_w[train_idx], y_w[train_idx])
            y_prob[test_idx] = clf.predict_proba(X_w[test_idx])[:, 1]
        
        fpr, tpr, _ = roc_curve(y_w, y_prob)
        roc_auc = auc(fpr, tpr)
        wesad_roc_data[name] = {"fpr": fpr, "tpr": tpr, "auc": roc_auc}
        print(f"  {name:30s} -> AUC = {roc_auc:.4f}")

    # -------------------------------------------------------------
    # 2. Hardware Dataset (N=4) - LOSO Cross-Validation
    # -------------------------------------------------------------
    print("\nLoading Hardware Phase 3.1 feature datasets...")
    hw_files = sorted(Path("outputs/features/hw").glob("labeled_*_hw.csv"))
    if not hw_files:
        raise FileNotFoundError("No HW feature files found in outputs/features/hw/")

    df_hw = pd.concat([pd.read_csv(f) for f in hw_files], ignore_index=True)
    df_hw = df_hw[df_hw["label"].isin([1, 2])].copy()
    X_hw = df_hw[FEATURE_COLS].values
    y_hw = (df_hw["label"].values == 2).astype(int)
    groups_hw = df_hw["sid"].values

    rf_hw = RandomForestClassifier(
        n_estimators=50, max_leaf_nodes=9, min_samples_split=10, random_state=42
    )

    y_prob_hw = np.zeros(len(y_hw))
    hw_fold_roc = {}

    print("Evaluating Hardware via Leave-One-Subject-Out CV...")
    for train_idx, test_idx in logo.split(X_hw, y_hw, groups_hw):
        test_sid = groups_hw[test_idx][0]
        rf_hw.fit(X_hw[train_idx], y_hw[train_idx])
        probs = rf_hw.predict_proba(X_hw[test_idx])[:, 1]
        y_prob_hw[test_idx] = probs

        # Per-fold ROC (if both classes present in fold)
        if len(np.unique(y_hw[test_idx])) > 1:
            f_fpr, f_tpr, _ = roc_curve(y_hw[test_idx], probs)
            f_auc = auc(f_fpr, f_tpr)
            hw_fold_roc[test_sid] = {"fpr": f_fpr, "tpr": f_tpr, "auc": f_auc}
            print(f"  Fold {test_sid} -> AUC = {f_auc:.4f}")
        else:
            print(f"  Fold {test_sid} -> Only 1 class present in test set, skipping individual fold curve")

    fpr_hw_agg, tpr_hw_agg, _ = roc_curve(y_hw, y_prob_hw)
    auc_hw_agg = auc(fpr_hw_agg, tpr_hw_agg)
    print(f"  Aggregate Hardware LOSO -> AUC = {auc_hw_agg:.4f}")

    # -------------------------------------------------------------
    # Plot 1: WESAD Benchmark Standalone
    # -------------------------------------------------------------
    plt.figure(figsize=(7, 6))
    colors = {"Random Forest (Production)": "#1f77b4", "KNN (k=5)": "#2ca02c", "SVM (RBF Kernel)": "#d62728"}
    for name, data in wesad_roc_data.items():
        lw = 2.5 if "Random Forest" in name else 1.8
        ls = "-" if "Random Forest" in name else "--"
        plt.plot(data["fpr"], data["tpr"], label=f"{name} (AUC = {data['auc']:.3f})",
                 color=colors.get(name, "#333333"), linewidth=lw, linestyle=ls)
    plt.plot([0, 1], [0, 1], "k:", alpha=0.6, label="Chance Level (AUC = 0.500)")
    plt.xlim([-0.02, 1.02])
    plt.ylim([-0.02, 1.05])
    plt.xlabel("False Positive Rate (1 - Specificity)", fontsize=11, fontweight="bold")
    plt.ylabel("True Positive Rate (Sensitivity / Recall)", fontsize=11, fontweight="bold")
    plt.title("WESAD Benchmark — Model Comparison\nLeave-One-Subject-Out CV (N=15 Subjects)", fontsize=12, fontweight="bold")
    plt.legend(loc="lower right", fontsize=9.5, framealpha=0.9)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / "roc_wesad_benchmark.png", dpi=300)
    plt.close()
    print("  Saved: outputs/plots/roc_wesad_benchmark.png")

    # -------------------------------------------------------------
    # Plot 2: Hardware LOSO Standalone
    # -------------------------------------------------------------
    plt.figure(figsize=(7, 6))
    fold_colors = ["#9467bd", "#8c564b", "#e377c2", "#17becf"]
    for idx, (sid, data) in enumerate(hw_fold_roc.items()):
        plt.plot(data["fpr"], data["tpr"], linestyle="--", alpha=0.7,
                 color=fold_colors[idx % len(fold_colors)],
                 label=f"Fold {sid} (AUC = {data['auc']:.3f})")
    
    plt.plot(fpr_hw_agg, tpr_hw_agg, color="#d62728", linewidth=2.8,
             label=f"Aggregate HW LOSO (AUC = {auc_hw_agg:.3f})")
    plt.plot([0, 1], [0, 1], "k:", alpha=0.6, label="Chance Level (AUC = 0.500)")
    plt.xlim([-0.02, 1.02])
    plt.ylim([-0.02, 1.05])
    plt.xlabel("False Positive Rate (1 - Specificity)", fontsize=11, fontweight="bold")
    plt.ylabel("True Positive Rate (Sensitivity / Recall)", fontsize=11, fontweight="bold")
    plt.title("Custom Hardware Validation (Phase 3.1)\nLeave-One-Subject-Out CV (N=4 Subjects)", fontsize=12, fontweight="bold")
    plt.legend(loc="lower right", fontsize=9.5, framealpha=0.9)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / "roc_hardware_loso.png", dpi=300)
    plt.close()
    print("  Saved: outputs/plots/roc_hardware_loso.png")

    # -------------------------------------------------------------
    # Plot 3: Combined 2-Panel Slide Figure
    # -------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Panel A: WESAD
    ax = axes[0]
    for name, data in wesad_roc_data.items():
        lw = 2.5 if "Random Forest" in name else 1.8
        ls = "-" if "Random Forest" in name else "--"
        ax.plot(data["fpr"], data["tpr"], label=f"{name} (AUC = {data['auc']:.3f})",
                color=colors.get(name, "#333333"), linewidth=lw, linestyle=ls)
    ax.plot([0, 1], [0, 1], "k:", alpha=0.6, label="Chance (AUC = 0.50)")
    ax.set_xlim([-0.02, 1.02])
    ax.set_ylim([-0.02, 1.05])
    ax.set_xlabel("False Positive Rate (1 - Specificity)", fontsize=10.5, fontweight="bold")
    ax.set_ylabel("True Positive Rate (Sensitivity / Recall)", fontsize=10.5, fontweight="bold")
    ax.set_title("A. Benchmark Validation (WESAD, N=15)\nLeave-One-Subject-Out Cross-Validation", fontsize=11.5, fontweight="bold")
    ax.legend(loc="lower right", fontsize=8.5, framealpha=0.9)
    ax.grid(True, alpha=0.3)

    # Panel B: Hardware
    ax = axes[1]
    for idx, (sid, data) in enumerate(hw_fold_roc.items()):
        ax.plot(data["fpr"], data["tpr"], linestyle="--", alpha=0.7,
                color=fold_colors[idx % len(fold_colors)],
                label=f"Fold {sid} (AUC = {data['auc']:.3f})")
    ax.plot(fpr_hw_agg, tpr_hw_agg, color="#d62728", linewidth=2.8,
            label=f"Aggregate HW LOSO (AUC = {auc_hw_agg:.3f})")
    ax.plot([0, 1], [0, 1], "k:", alpha=0.6, label="Chance (AUC = 0.50)")
    ax.set_xlim([-0.02, 1.02])
    ax.set_ylim([-0.02, 1.05])
    ax.set_xlabel("False Positive Rate (1 - Specificity)", fontsize=10.5, fontweight="bold")
    ax.set_ylabel("True Positive Rate (Sensitivity / Recall)", fontsize=10.5, fontweight="bold")
    ax.set_title("B. Live Hardware Validation (Phase 3.1, N=4)\nLeave-One-Subject-Out Cross-Validation", fontsize=11.5, fontweight="bold")
    ax.legend(loc="lower right", fontsize=8.5, framealpha=0.9)
    ax.grid(True, alpha=0.3)

    fig.suptitle("GPAMS Classifier Discrimination Performance (ROC & AUC)", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(out_dir / "roc_combined.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  Saved: outputs/plots/roc_combined.png")
    print("\nAll ROC curves successfully generated!")

if __name__ == "__main__":
    generate_roc_curves()
