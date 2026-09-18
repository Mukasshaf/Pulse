# PULSE Phase 3 Pipeline Additions

## Overview
Phase 3 integrates live hardware captures (ESP32 via `serial_reader.py`) with the offline ML pipeline (WESAD-trained classifier and HW-trained LOSO classifier).

## Module Manifest (`src/pipeline/`)
1. `hardware_loader.py`: Raw CSV parser converting ESP32 columns to canonical dataframe with `HW_FS = 66.67`.
2. `condition_labels.py`: Phase 3.1 protocol condition markers (`baseline`, `mental_arithmetic`, `stroop`).
3. `condition_logger.py`: Interactive CLI timer prompting the subject through Phase 3.1 calibration.
4. `eval_zero_shot.py`: Evaluates zero-shot transfer performance of WESAD-trained Random Forest model on hardware data.
5. `train_hw_loso.py`: Trains and evaluates Leave-One-Subject-Out (LOSO) cross-validation directly on hardware-collected subjects.
6. `go_nogo_check.py`: M3 milestone verification script ensuring F1-macro >= 0.65.
