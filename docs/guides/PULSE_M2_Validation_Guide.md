# PULSE M2 Hardware Validation Guide

## Overview
Milestone 2 (M2) verifies sensor signal fidelity and timing stability from the ESP32 hardware capture rig before running full multi-subject protocols.

## Verification Criteria
1. **Drop Rate**: Sample drop rate < 0.1% over 20,000 samples (<20 dropped frames).
   - Validation script: `validation/validate_drop_rate.py`
2. **Pulse & IBI Validity**: Clean physiological peak detection with valid inter-beat intervals (IBI) at resting heart rates (60–90 BPM).
   - Validation script: `validation/validate_peak_detection.py`
3. **GSR Baseline Stability**: Stable tonic conductance across resting windows without drift > 15%.
   - Validation script: `validation/validate_gsr_stability.py`
4. **Motion Artifact Sensitivity & Specificity**:
   - `ACC_THRESHOLD_HW = 8800.0`
   - Specificity: 0% false positives when sensor hand rests stationary on table.
   - Sensitivity: >90% true positive flagging during bilateral typing / intentional movement.
   - Validation script: `validation/validate_motion_flag.py`

## Running M2 Suite
```bash
python validation/run_m2_validation.py --raw-csv data/hardware/raw/HW01/recorded_data.csv
```
