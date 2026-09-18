# PULSE Pipeline Change Plan

## Summary of Pipeline Modifications for Hardware Integration
1. **Analog Pulse Sensor Pivot**: Sampling rate fixed at 66.67 Hz (15 ms timer loop) replacing 64 Hz WESAD default.
2. **Motion Threshold Calibration**: `ACC_THRESHOLD_HW = 8800.0` (int16 variance on resting hand) replacing normalized float threshold.
3. **Timestamp Standardization**: `unix_ts_ms` (integer Unix epoch ms) used as universal join key across hardware sensor logs and game event logs.
4. **Feature Set**: 9 locked features (scl_slope dropped per Phase 1 Gini importance analysis).
