# Architecture — Technical Reference

Technical reference for the pipeline layers, feature set, ML model configuration, hardware wiring, and repository layout.

---

## Signal Processing Pipeline

```
Raw PPG + EDA + ACC (66.67 Hz via ESP32)
        │
        ▼
Preprocessing
  PPG → Butterworth BPF (0.5–5 Hz) → peak detection
        → 5-beat median-filter IBI outlier correction → IBI series
  EDA → tonic/phasic decomposition → SCL (tonic) + SCR (phasic)
  ACC → per-second magnitude variance → motion artifact flag
        │
        ▼
Feature Extraction (60s window, 30s stride, ≥4 valid beats required)
        │
        ▼
Within-subject z-score normalization (vs subject's own 3-minute resting baseline)
        │
        ├──▶ Layer 1 — Adaptive Threshold Detector (real-time flagging)
        │     GSR: flag if SCR sample > μ+2σ of subject's baseline
        │     HR : flag if 10s-rolling HR deviates >10% from baseline
        │
        └──▶ Layer 2 — Random Forest Classifier (LOSO-CV)
                     │
                     ▼
              Layer 3 — Per-subject z-score domain activation map (radar chart)
```

---

## Feature Set (9 Features)

| Feature | Sensor | Notes |
|---|---|---|
| `mean_hr` | PPG | Mean heart rate over window |
| `rmssd` | PPG / HRV | Root mean square of successive IBI differences |
| `sdnn` | PPG / HRV | Standard deviation of normal-to-normal intervals |
| `pnn50` | PPG / HRV | Proportion of successive IBIs differing by >50ms |
| `scr_count` | GSR phasic | Number of skin conductance response peaks |
| `scr_max_amp` | GSR phasic | Maximum SCR amplitude |
| `scr_energy` | GSR phasic | Total SCR signal energy |
| `scr_epeak` | GSR phasic | Mean energy per SCR peak |
| `scl_mean` | GSR tonic | **Dominant feature** — highest Gini importance (~0.33) |

---

## ML Model Configuration

**Random Forest** (binary classification: baseline vs. stress)

```python
RandomForestClassifier(
    n_estimators=50,
    max_leaf_nodes=None,
    min_samples_split=10
)
```
Hyperparameters tuned via `GridSearchCV`. Evaluation uses **Leave-One-Subject-Out (LOSO) cross-validation** to ensure subject-independent generalization.

---

## Results

### WESAD Benchmark (N=15 subjects, 807 windows, LOSO-CV)

| Metric | Value |
|---|---|
| Accuracy | 0.9591 |
| F1-macro | 0.9503 |
| Specificity | 0.9841 |
| Sensitivity | 0.9004 |

### Model Comparison

| Model | Accuracy | F1-macro | Sensitivity |
|---|---|---|---|
| **Random Forest** | **0.978** | **0.973** | **0.963** |
| KNN (k=5) | 0.983 | 0.979 | 0.946 |
| SVM (RBF) | 0.726 | 0.495 | 0.083 |

SVM (RBF) collapses under cross-subject shift - ruled out for this use case.

### Live Hardware Pilot (N=7 subjects, LOSO-CV)

| Metric | Value |
|---|---|
| Accuracy | 0.86 |
| AUC | 0.902 |

### Threshold Detector (Layer 1) — Onset Latency (target ≤ 10s)

| Sensor | Pass Rate |
|---|---|
| HR | 14/15 |
| GSR | 11/15 |

GSR misses trace to low-sympathetic responders (S2, S14) — confirmed not a detector defect.

---

## Hardware Wiring

### Analog Pulse Sensor → ESP32

| Pulse Sensor | ESP32 | Notes |
|---|---|---|
| VCC | 3V3 | |
| GND | GND | |
| SIG | GPIO35 | ADC1_CH7 |

### Grove GSR → ESP32

| GSR Wire | ESP32 | Notes |
|---|---|---|
| VCC (red) | 3V3 | **Not 5V** — GPIO34 is 3.3V-only. 5V risks ADC damage. |
| GND (black) | GND | |
| SIG (white) | GPIO34 | ADC1_CH6 — input-only, WiFi-safe |

Sensor placement: GSR electrodes on **middle and ring fingertips** of the non-dominant hand, consistent across all subjects.

### MPU6050 → ESP32

| MPU6050 | ESP32 | Notes |
|---|---|---|
| VCC | 3V3 | |
| GND | GND | |
| SCL | GPIO22 | Shared I2C bus |
| SDA | GPIO21 | Shared I2C bus |
| AD0 | GND | Forces I2C address 0x68 |
| INT, XDA, XCL | Not connected | |

Expected I2C address on scan: `0x68` (MPU6050).

### Firmware Output Schema

```
sample_idx, timestamp_ms, pulse_raw, gsr_raw, acc_x, acc_y, acc_z
```
Sampling rate: **66.67 Hz** (`SAMPLE_INTERVAL_MS = 15`).

---

## Repository Structure

```text
Pulse/
├── assets/                 # Static media assets (audio/visuals)
├── docs/                   # Centralized documentation
│   ├── reports/            # Pilot results and research reports
│   ├── specs/              # Architecture, interface, and system reference docs
│   └── CHANGELOG.md        # Detailed progress and update tracker
│
├── firmware/
│   └── firmware.ino        # ESP32 sampling sketch (66.67 Hz, GSR + PPG + IMU)
│
├── scripts/
│   ├── analysis/           # Radar chart generation, feature extraction, ROC curves
│   ├── hardware_checks/    # Pre-session hardware go/no-go verification
│   └── training/           # ML training and zero-shot evaluation
│
├── src/
│   ├── domains.py          # Canonical source of truth for 7 domain IDs
│   ├── align_signals.py    # Post-session join: hardware CSV ↔ game events.csv
│   ├── pipeline/           # Preprocessing, feature extraction, ML classifier
│   ├── hardware/           # Serial acquisition (serial_reader.py)
│   └── game/              # Gamification engine (Pygame state machine)
│
├── tests/                  # Pytest automated test suite
├── validation/             # Hardware bring-up validation scripts and reports
├── pyproject.toml
└── run_session.py          # Primary CLI orchestrator for live subject sessions
```
