# Pulse — Multimodal Biosignal Stress Assessment & Gamification Protocol

Pulse is an end-to-end research platform that investigates domain-specific physiological stress activation in healthy individuals aged 15–25. It bridges clinical laboratory stress paradigms (MIST, TSST, Stroop, BART, Iowa Gambling Task) with a deterministic, score-free digital gamification engine and an ESP32 wearable biosignal sensor pipeline.

---

## Repository Structure

```
Pulse/
├── .gitignore                            # Unified ignore rules (caches, data/, outputs/, venvs)
├── .python-version                       # Python runtime specification (3.13)
├── pyproject.toml                        # Merged dependencies (numpy, scipy, scikit-learn, neurokit2, pygame, etc.)
├── uv.lock                               # Deterministic dependency lockfile
├── README.md                             # Project overview (both tracks documented)
├── CLAUDE.md / GEMINI.md                 # AI agent rules & architecture contracts
│
├── assets/                               # [Ayush] Static media assets
│   └── audio/
│       └── tension_drone.wav             # 60–80 Hz low-frequency loop drone
│
├── data/                                 # Shared data root (gitignored)
│   ├── WESAD/                            # [Mukasshaf] Benchmark dataset (S2–S17)
│   ├── hardware/                         # [Mukasshaf] ESP32 sensor captures
│   │   ├── raw/                          # Raw CSVs from serial_reader.py
│   │   └── labeled/                      # Protocol labeled CSVs
│   └── game_logs/                        # [Ayush] Session event logs
│
├── docs/                                 # Unified documentation
│   ├── specs/                            # [Ayush] Gamification technical specifications
│   │   ├── ARCHITECTURE_SPEC.md
│   │   ├── CODING_STANDARDS_AND_RULES.md
│   │   ├── DATA_MODELS_AND_CONTRACTS.md
│   │   ├── domain_implementation_strategy.md
│   │   ├── IMPLEMENTATION_PLAN.md
│   │   └── TEST_CRITERIA_AND_EDGE_CASES.md
│   ├── guides/                           # [Mukasshaf] Hardware & validation guides
│   │   ├── PULSE_Hardware_Setup.md
│   │   ├── PULSE_M2_Validation_Guide.md
│   │   ├── PULSE_Phase3_Pipeline_Additions.md
│   │   └── PULSE_Pipeline_Change_Plan.md
│   └── interface/
│       └── PULSE_Gamification_Interface_Spec.md  # Inter-track contract
│
├── firmware/                             # [Mukasshaf] Microcontroller firmware
│   └── firmware.ino                      # ESP32 66.67 Hz sampling sketch
│
├── notebooks/                            # Exploratory Jupyter notebooks
│
├── outputs/                              # Generated run artifacts (gitignored)
│   ├── features/                         # Extracted 9-feature CSVs
│   ├── models/                           # Trained estimators (rf_loso.pkl, hw_classifier.pkl)
│   ├── plots/                            # Preprocessing & confusion matrix plots
│   └── results/                          # Fold results, transfer gap, activation maps
│
├── src/                                  # Core application source
│   ├── __init__.py
│   ├── domains.py                        # [SHARED] Single source of truth for 7 canonical domain IDs
│   ├── align_signals.py                  # [SHARED] Join script: hardware sensor CSV ↔ game events.csv
│   │
│   ├── pipeline/                         # [Mukasshaf] ML & Signal Processing Pipeline
│   │   ├── __init__.py
│   │   ├── wesad_loader.py               # WESAD pickle parser (Phase 1)
│   │   ├── hardware_loader.py            # Hardware CSV parser (HW_FS = 66.67 Hz)
│   │   ├── preprocess.py                 # BVP BPF, peak detect, EMD/SCL, motion flag (8800.0)
│   │   ├── features.py                   # 9 locked features (60s window, 30s stride)
│   │   ├── normalize.py                  # Within-subject z-score normalization
│   │   ├── classifier.py                 # Tuned Random Forest (LOSO-CV)
│   │   ├── threshold_detector.py         # Layer 1 deterministic μ+2σ rule
│   │   ├── condition_labels.py           # Protocol labels (baseline/arithmetic/stroop)
│   │   ├── condition_logger.py           # Session timer cue tool
│   │   ├── eval_zero_shot.py             # Zero-shot WESAD-to-HW evaluator
│   │   ├── train_hw_loso.py              # HW-trained LOSO classifier
│   │   ├── go_nogo_check.py              # M3 gate verification (F1-macro ≥ 0.65)
│   │   ├── batch_comparison.py           # Feature importance & comparison utility
│   │   └── run_pipeline.py               # Multi-subject batch pipeline runner
│   │
│   ├── hardware/                         # [Mukasshaf] Serial acquisition tools
│   │   ├── __init__.py
│   │   └── serial_reader.py              # Live COM reader, validates rows, injects unix_ts_ms
│   │
│   └── game/                             # [Ayush] Gamification Engine (Pygame)
│       ├── __init__.py
│       ├── main.py                       # Game CLI entry point (--subject, etc.)
│       ├── engine.py                     # Master GameEngine state machine & 60 FPS loop
│       ├── constants.py                  # Enums (EngineState, EventType), colors, timers
│       ├── event_logger.py               # 9-column CSV logger (with host unix_ts_ms)
│       ├── scenarios.py                  # 14 scenarios registry (2 per domain)
│       ├── scenario_logic.py             # Arithmetic, BART pumps, reward accumulators
│       ├── ui.py                         # Pygame rendering (text, prompt boxes, timer bars)
│       ├── ui_effects.py                 # Visual jitter (≤3px), screen vibration, color lerp
│       ├── audio.py                      # Audio player for recovery & tension drones
│       └── bridge_interface.py           # BridgeInterface & StubBridge abstraction
│
├── tests/                                # Automated test suite
│   ├── __init__.py
│   ├── conftest.py                       # Shared test fixtures (mock screen, session configs)
│   │
│   ├── game/                             # [Ayush] 41 Gamification engine tests
│   │   ├── test_audio.py
│   │   ├── test_bridge_interface.py
│   │   ├── test_constants.py
│   │   ├── test_engine.py
│   │   ├── test_event_logger.py
│   │   ├── test_scenario_logic.py
│   │   ├── test_scenarios.py
│   │   └── test_ui_effects.py
│   │
│   └── pipeline/                         # [Mukasshaf] ML & Signal tests
│       ├── test_loaders.py
│       ├── test_preprocess.py
│       └── test_features.py
│
└── validation/                           # [Mukasshaf] Hardware bring-up validation
    ├── run_m2_validation.py
    ├── validate_peak_detection.py
    ├── validate_gsr_stability.py
    ├── validate_motion_flag.py
    ├── validate_drop_rate.py
    └── reports/
        ├── M2_Full_Validation_Report.md
        └── M2_Validation_Summary.md
```

---

## Quickstart

### Prerequisites
- Python 3.11+ (Python 3.13 recommended)
- Package manager: [`uv`](https://docs.astral.sh/uv/)

### Installation
```bash
uv sync
```

### Running Tests
```bash
uv run pytest
```

### Running the Gamification Engine
```bash
uv run python -m src.game.main --subject S01 --fast-baseline
```
