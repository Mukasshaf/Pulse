# Pulse — AI Agent Context & Rules (Dual-Track Architecture)

## Overview
Pulse is a multimodal physiological stress assessment platform uniting clinical experimental stress paradigms with digital gamification and machine learning.

### Track Division
1. **Hardware & ML Pipeline (Mukasshaf)**:
   - Microcontroller: ESP32 with Analog Pulse Sensor (GPIO35), Grove GSR (GPIO34), MPU-6050 accelerometer (I2C 21/22).
   - Sampling rate: `HW_FS = 66.67 Hz` (15 ms sample loop).
   - Preprocessing: BVP bandpass, peak detection, tonic/phasic EDA decomposition, motion artifact threshold `ACC_THRESHOLD_HW = 8800.0`.
   - Feature extraction: 9 locked features (60s sliding window, 30s stride).
   - Classification: Within-subject z-score normalization, Random Forest with Leave-One-Subject-Out (LOSO) cross-validation.
   - Execution environment: WSL2 (or native with `usbipd-win` for serial COM).

2. **Gamification Engine (Ayush)**:
   - Engine: Pygame @ 60 FPS running natively on Windows.
   - Paradigms: 7 behavioral domains, 14 scenarios (MIST arithmetic, BART balloon pumps, reward accumulator, delay discounting, moral dilemmas, social evaluative threat).
   - Target demographic: 15–25 years old (age-universal school, social, and digital contexts).
   - Strict constraints: Keyboard-only input (keys 1–4), score-free consequence design, capped UI deterioration (jitter <= 3px, <= 2Hz, no strobing > 3Hz).
   - Deception metric: Active ONLY in `social_evaluation` domain (calibrated to subject resting tremor mu + 1.5 sigma).

## Inter-Track Integration Contracts
- **Clock Synchronization**: Both tracks log host-PC Unix epoch time in milliseconds (`unix_ts_ms` = `int(time.time_ns() // 1_000_000)`).
- **Domains Single Source of Truth**: `src/domains.py` defines the canonical 7 domain IDs. Never hardcode domain strings.
- **Event Log Schema**: First 5 columns are `unix_ts_ms, event_type, domain, scenario_id, choice_data`.
- **Signal Alignment**: `src/align_signals.py` joins hardware CSV and game CSV natively on `unix_ts_ms`.
- **Decoupled Architecture**: Hardware capture (`serial_reader.py`) and Pygame engine (`src.game.main`) run as separate independent processes without live socket IPC.

## Development Commands
- Run all tests: `uv run pytest`
- Run gamification engine: `uv run python -m src.game.main --subject S01 --fast-baseline`
- Check type annotations: `uv run mypy src/ tests/`
