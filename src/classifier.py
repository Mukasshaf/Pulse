

import numpy as np
import pandas as pd
import json
import pickle
import sys
import os
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import (
    LeaveOneGroupOut, StratifiedKFold, GridSearchCV, cross_val_predict
)
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)
from sklearn.preprocessing import LabelEncoder

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wesad_loader import load_subject, LABEL_NAMES
from preprocess import preprocess_subject
from features import extract_window_features
from normalize import normalize_subject


FEATURE_COLS = [
        "mean_hr", "rmssd", "sdnn", "pnn50",
        "scr_count", "scr_max_amp", "scr_energy",
        "scr_epeak", "scl_mean"]

# RF starting config from Barik et al. paper
RF_BASE_PARAMS = {
    "n_estimators":     75,
    "max_leaf_nodes":   9,
    "min_samples_split": 5,
    "random_state":     42,
    "n_jobs":           -1,
}

RF_GRID = {
    "n_estimators":      [50, 75, 100],
    "max_leaf_nodes":    [9, 15, None],
    "min_samples_split": [5, 10],
}


# Metrics

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray,
                    labels: list = [1, 2]) -> dict:
   
    acc  = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, average="macro", zero_division=0)
    rec  = recall_score(y_true, y_pred, average="macro", zero_division=0)
    f1   = f1_score(y_true, y_pred, average="macro", zero_division=0)

    cm = confusion_matrix(y_true, y_pred, labels=labels)
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    else:
        specificity = float("nan")
        sensitivity = float("nan")

    return {
        "accuracy":    float(acc),
        "precision":   float(prec),
        "recall":      float(rec),
        "f1_macro":    float(f1),
        "specificity": float(specificity),
        "sensitivity": float(sensitivity),
        "confusion_matrix": cm.tolist(),
    }


#  Grid search 

def grid_search(X: np.ndarray, y: np.ndarray,
                groups: np.ndarray = None) -> RandomForestClassifier:
   
    cv = LeaveOneGroupOut() if groups is not None else StratifiedKFold(n_splits=5)
    cv_kwargs = {"groups": groups} if groups is not None else {}

    rf   = RandomForestClassifier(random_state=42, n_jobs=-1)
    grid = GridSearchCV(rf, RF_GRID, cv=cv, scoring="f1_macro",
                        n_jobs=-1, verbose=0, refit=True)
    grid.fit(X, y, **cv_kwargs)

    print(f"  Best params : {grid.best_params_}")
    print(f"  Best F1     : {grid.best_score_:.4f}")
    return grid.best_estimator_


# LOSO training

def train_loso(subject_dfs: list[pd.DataFrame],
               run_grid_search: bool = True) -> dict:
  
    df_all = pd.concat(subject_dfs, ignore_index=True)
    df_all = df_all[df_all["label"].isin([1, 2])].copy()

    X      = df_all[FEATURE_COLS].values
    y      = df_all["label"].values
    groups = df_all["sid"].values

    n_subjects = len(df_all["sid"].unique())
    print(f"\n  LOSO CV — {n_subjects} subjects, "
          f"{len(df_all)} windows ({np.sum(y==1)} baseline, {np.sum(y==2)} stress)")

    if run_grid_search:
        print("\n  Running GridSearchCV...")
        best_clf = grid_search(X, y, groups=groups)
    else:
        best_clf = RandomForestClassifier(**RF_BASE_PARAMS)

    # LOSO evaluation
    logo     = LeaveOneGroupOut()
    fold_results = []
    y_pred_all   = np.zeros_like(y)

    for fold, (train_idx, test_idx) in enumerate(logo.split(X, y, groups)):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        test_sid        = groups[test_idx][0]

        clf = RandomForestClassifier(**best_clf.get_params())
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)
        y_pred_all[test_idx] = y_pred

        metrics = compute_metrics(y_test, y_pred)
        metrics["test_sid"] = int(test_sid)
        metrics["n_test"]   = len(y_test)
        fold_results.append(metrics)

        print(f"  Fold S{test_sid:02d} | "
              f"acc={metrics['accuracy']:.3f}  "
              f"f1={metrics['f1_macro']:.3f}  "
              f"spec={metrics['specificity']:.3f}")

    # Aggregate metrics
    agg = compute_metrics(y, y_pred_all)
    agg_f1s = [f["f1_macro"] for f in fold_results]
    print(f"\n  Aggregate | acc={agg['accuracy']:.3f}  "
          f"f1={agg['f1_macro']:.3f} (±{np.std(agg_f1s):.3f})  "
          f"spec={agg['specificity']:.3f}")

    # Feature importance from best clf
    best_clf.fit(X, y)
    importance = dict(zip(FEATURE_COLS, best_clf.feature_importances_.tolist()))

    return {
        "mode":         "loso",
        "n_subjects":   n_subjects,
        "fold_results": fold_results,
        "aggregate":    agg,
        "importance":   importance,
        "best_clf":     best_clf,
        "best_params":  best_clf.get_params(),
        "y_true":       y.tolist(),
        "y_pred":       y_pred_all.tolist(),
        "groups":       groups.tolist(),
    }


#  Single-subject fallback

def train_single_subject(df_norm: pd.DataFrame,
                         run_grid_search: bool = True) -> dict:
    
    sid = df_norm["sid"].iloc[0]
    df  = df_norm[df_norm["label"].isin([1, 2])].copy()
    X   = df[FEATURE_COLS].values
    y   = df["label"].values

    print(f"\n  Single-subject 5-fold CV — S{sid} "
          f"({np.sum(y==1)} baseline, {np.sum(y==2)} stress)")
    print("  NOTE: switch to LOSO when multiple subjects available\n")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    if run_grid_search:
        best_clf = grid_search(X, y)
    else:
        best_clf = RandomForestClassifier(**RF_BASE_PARAMS)
        best_clf.fit(X, y)

    y_pred = cross_val_predict(best_clf, X, y, cv=cv)
    metrics = compute_metrics(y, y_pred)

    print(f"\n  5-fold CV | acc={metrics['accuracy']:.3f}  "
          f"f1={metrics['f1_macro']:.3f}  "
          f"spec={metrics['specificity']:.3f}")

    best_clf.fit(X, y)
    importance = dict(zip(FEATURE_COLS, best_clf.feature_importances_.tolist()))

    return {
        "mode":       "single_subject_5fold",
        "sid":        int(sid),
        "metrics":    metrics,
        "importance": importance,
        "best_clf":   best_clf,
        "best_params": best_clf.get_params(),
        "y_true":     y.tolist(),
        "y_pred":     y_pred.tolist(),
    }


# Model comparison (RF vs SVM vs KNN)

def compare_models(df_norm: pd.DataFrame) -> pd.DataFrame:
   
    sid = df_norm["sid"].iloc[0]
    df  = df_norm[df_norm["label"].isin([1, 2])].copy()
    X   = df[FEATURE_COLS].values
    y   = df["label"].values
    cv  = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    models = {
        "Random Forest": RandomForestClassifier(**RF_BASE_PARAMS),
        "SVM (RBF)":     SVC(kernel="rbf", C=1.0, gamma="scale", random_state=42),
        "KNN (k=5)":     KNeighborsClassifier(n_neighbors=5),
    }

    rows = []
    print(f"\n  Model comparison — pooled {len(df['sid'].unique())} subjects (5-fold CV)")
    print(f"  {'Model':<18} {'acc':>6} {'f1':>6} {'spec':>6} {'sens':>6}")
    print(f"  {'-'*46}")

    for name, clf in models.items():
        y_pred = cross_val_predict(clf, X, y, cv=cv)
        m = compute_metrics(y, y_pred)
        print(f"  {name:<18} "
              f"{m['accuracy']:>6.3f} "
              f"{m['f1_macro']:>6.3f} "
              f"{m['specificity']:>6.3f} "
              f"{m['sensitivity']:>6.3f}")
        rows.append({"model": name, **{k: v for k, v in m.items()
                                        if k != "confusion_matrix"}})

    return pd.DataFrame(rows)


# Plots

def plot_results(results: dict,
                 out_dir: str = "outputs/plots") -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    sid_tag = f"S{results.get('sid', 'multi')}"

    #Feature importance bar chart
    importance = results["importance"]
    features   = list(importance.keys())
    values     = list(importance.values())
    sorted_idx = np.argsort(values)[::-1]

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#2563EB" if i == 0 else "#93C5FD" for i in range(len(features))]
    bars   = ax.bar(range(len(features)),
                    [values[i] for i in sorted_idx],
                    color=colors)
    ax.set_xticks(range(len(features)))
    ax.set_xticklabels([features[i] for i in sorted_idx], rotation=35, ha="right")
    ax.set_ylabel("Gini Importance")
    ax.set_title(f"GPAMS — RF Feature Importance ({sid_tag})")
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{out_dir}/feature_importance_{sid_tag}.png", dpi=120)
    plt.close()
    print(f"  Feature importance → {out_dir}/feature_importance_{sid_tag}.png")

    #Confusion matrix
    cm = np.array(results.get("aggregate", results.get("metrics", {}))
                  .get("confusion_matrix", [[0, 0], [0, 0]]))
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xticklabels(["Pred Baseline", "Pred Stress"])
    ax.set_yticklabels(["True Baseline", "True Stress"])
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    fontsize=14, color="white" if cm[i, j] > cm.max()/2 else "black")
    ax.set_title(f"Confusion Matrix ({sid_tag})")
    plt.colorbar(im, ax=ax)
    plt.tight_layout()
    plt.savefig(f"{out_dir}/confusion_matrix_{sid_tag}.png", dpi=120)
    plt.close()
    print(f"  Confusion matrix  → {out_dir}/confusion_matrix_{sid_tag}.png")


#  Save / load model

def save_model(clf, path: str = "outputs/models/classifier.pkl") -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(clf, f)
    print(f"  Model saved → {path}")


def load_model(path: str = "outputs/models/classifier.pkl"):
    with open(path, "rb") as f:
        return pickle.load(f)


# CLI

if __name__ == "__main__":
    sid      = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    data_dir = sys.argv[2] if len(sys.argv) > 2 else "data/WESAD"

    subject      = load_subject(sid, data_dir)
    preprocessed = preprocess_subject(subject)
    df_raw       = extract_window_features(preprocessed)
    df_norm, _   = normalize_subject(df_raw)

    # Single-subject mode
    results = train_single_subject(df_norm, run_grid_search=True)
    plot_results(results)

    # Model comparison 
    print("\nRunning model comparison...")
    comparison_df = compare_models(df_norm)
    Path("outputs/results").mkdir(parents=True, exist_ok=True)
    comparison_df.to_csv(f"outputs/results/model_comparison_S{sid}.csv", index=False)
    print(f"\n  Comparison saved → outputs/results/model_comparison_S{sid}.csv")

    # Save best model
    save_model(results["best_clf"],
               f"outputs/models/rf_S{sid}.pkl")

    # Save best params
    params_path = f"outputs/models/best_params_S{sid}.json"
    with open(params_path, "w") as f:
        params = {k: v for k, v in results["best_params"].items()
                  if isinstance(v, (int, float, str, bool, type(None)))}
        json.dump(params, f, indent=2)
    print(f"  Best params → {params_path}")