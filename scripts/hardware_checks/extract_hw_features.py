import sys
import os
from pathlib import Path
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "pipeline"))

from hardware_loader import load_labeled_hardware_csv
from preprocess import clean_bvp, detect_peaks, decompose_eda, flag_motion_artifacts, ACC_THRESHOLD_HW
from features import extract_window_features
from normalize import normalize_subject

def preprocess_hardware_labeled(data: dict) -> dict:
    sid    = data["sid"]
    fs_bvp = data["fs"]["bvp"]
    fs_eda = data["fs"]["eda"]
    fs_acc = data["fs"]["acc"]

    print(f"  Preprocessing labeled hardware file: {sid}  (fs={fs_bvp:.4f} Hz)")

    bvp_clean = clean_bvp(data["bvp"], fs=fs_bvp)
    peaks     = detect_peaks(bvp_clean, fs=fs_bvp)
    print(f"    BVP  -> {len(peaks['peaks'])} peaks  mean HR = {peaks['mean_hr']:.1f} BPM")

    eda_results = decompose_eda(data["eda"], fs=fs_eda)
    print(f"    EDA  -> {len(eda_results['scr_peaks'])} SCR peaks")

    artifact_mask = flag_motion_artifacts(data["acc"], fs=fs_acc, threshold=ACC_THRESHOLD_HW)
    print(f"    ACC  -> {artifact_mask.mean() * 100:.1f}% windows flagged as artifacts (thresh={ACC_THRESHOLD_HW:.0f})")

    return {
        "sid":           sid,
        "bvp_clean":     bvp_clean,
        "peaks":         peaks,
        "eda":           eda_results,
        "artifact_mask": artifact_mask,
        "labels":        data["labels"],
        "fs":            data["fs"],
    }

def main():
    raw_dir = Path("data/hardware/raw")
    out_dir = Path("outputs/features/hw")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each subject directory inside data/hardware/raw
    for subject_dir in sorted(raw_dir.iterdir()):
        if not subject_dir.is_dir():
            continue
            
        # Find the recorded_*.csv and condition_log_*.csv dynamically
        try:
            csv_path = next(subject_dir.glob("recorded*.csv"))
            log_path = next(subject_dir.glob("condition_log*.csv"))
        except StopIteration:
            print(f"  SKIP {subject_dir.name} — missing a recorded_*.csv or condition_log*.csv")
            continue
            
        sid = subject_dir.name
        print(f"\n[{sid}] Starting feature extraction...")
        
        try:
            # 1. Load raw data and align with condition log
            data = load_labeled_hardware_csv(csv_path, log_path, subject_id=sid)
            
            # 2. Preprocess (filtering, peak detection, artifacts)
            preprocessed = preprocess_hardware_labeled(data)
            
            # 3. Extract 60s rolling window features (adaptive artifact threshold)
            thresholds_to_try = [0.20, 0.50, 0.80, 1.0]
            df_raw = None
            for thresh in thresholds_to_try:
                df_temp = extract_window_features(preprocessed, artifact_threshold=thresh)
                if not df_temp.empty and len(df_temp[df_temp["label"] == 1]) > 0:
                    df_raw = df_temp
                    if thresh > 0.20:
                        print(f"  [Artifact Rescue] Relaxed artifact_threshold to {thresh} for {sid} to preserve baseline windows.")
                    break
            
            if df_raw is None or df_raw.empty:
                print(f"  SKIP {sid} — no valid baseline windows after feature extraction (too many artifacts).")
                continue
                
            # 4. Normalize (within-subject z-score based on baseline)
            df_norm, _ = normalize_subject(df_raw)
            
            # 5. Save the final features (expected format by training scripts)
            out_file = out_dir / f"labeled_{sid}_hw.csv"
            df_norm.to_csv(out_file, index=False)
            print(f"  SUCCESS: Saved normalized features to {out_file}")
            
        except Exception as e:
            print(f"  ERROR processing {sid}: {e}")

if __name__ == "__main__":
    main()
