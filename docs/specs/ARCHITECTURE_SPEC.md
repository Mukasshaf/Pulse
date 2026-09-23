# ARCHITECTURE_SPEC.md — Pulse Gamification Engine

> **Scope:** This document governs the structural skeleton of the Pygame Scenario Engine (Phase 4). It is the single source of truth for directory layout, runtime constraints, component hierarchy, data flow, and state management. No code generation may contradict this document.

---

## 1. Tech Stack & Runtime

| Component | Specification | Rationale |
|---|---|---|
| **Language** | Python 3.13.x (CPython) | Owner's installed version; `match`/`case` syntax permitted |
| **Runtime OS** | Windows 10/11 (native) | COM port access for ESP32 serial; WSL2 cannot passthrough COM |
| **Package Manager** | `uv` (NOT pip, NOT conda) | Lockfile reproducibility (`uv.lock`) — project standard |
| **Game Framework** | `pygame>=2.5.0` | Sole rendering/input/audio backend |
| **Data Libraries** | `numpy>=1.26.0` | Arithmetic generation, array ops |
| **Serialization** | Python stdlib `json`, `csv`, `dataclasses` | Zero external dependencies for data layer |
| **Threading** | Python stdlib `threading`, `queue` | Producer-Consumer serial bridge pattern |
| **Audio** | `pygame.mixer` | 60–80 Hz tension drone WAV playback |
| **CLI** | Python stdlib `argparse` | Entry-point flag parsing |
| **Python Typing** | `from __future__ import annotations` in every file | Forward-ref safety; enforced by linter |

### Banned Dependencies
- `tkinter`, `PyQt`, `wxPython` — no GUI framework mixing
- `pandas` — not needed in the game engine; belongs in WSL2 ML pipeline only
- `scipy`, `scikit-learn` — WSL2 only; will not import on native Windows (AppLocker)
- `requests`, `aiohttp` — no network calls from the game engine

---

## 2. Directory Layout

Pulse/                                    # Project root
├── firmware/
│   └── firmware.ino                      # ESP32 66.67 Hz ADC/IMU sampling sketch
├── data/
│   ├── WESAD/S{id}/S{id}.pkl             # Phase 1 software-bridge dataset
│   └── hardware/
│       ├── raw/S{id}/recorded_data.csv, condition_log.csv
│       └── labeled/labeled_S{id}_hw.csv  # Auto-labeled hardware data
├── src/
│   ├── game/                             # ← Phase 4 Gamification Engine (Ayush)
│   │   ├── __init__.py                   # Package marker (empty)
│   │   ├── main.py                       # CLI entry point: `python -m src.game.main`
│   │   ├── engine.py                     # Master state machine + Pygame loop
│   │   ├── scenarios.py                  # Domain/Scenario/Option dataclasses + registry
│   │   ├── scenario_logic.py             # Interactive logic (BART pumps, MIST arithmetic, reward accumulator)
│   │   ├── ui.py                         # Rendering primitives: colors, fonts, widgets
│   │   ├── ui_effects.py                 # Jitter, timer bar color transitions, screen vibration
│   │   ├── audio.py                      # Tension drone loader, fade-in/fade-out, volume control
│   │   ├── event_logger.py               # CSV writer with unix_ts_ms timestamps
│   │   ├── constants.py                  # Magic numbers, enums, canonical DomainIDs, timing defaults
│   │   └── bridge_interface.py           # Interface for serial bridge (stub for decoupled mode)
│   │
│   ├── wesad_loader.py                   # WESAD pickle parser (Phase 1, unchanged)
│   ├── hardware_loader.py                # Hardware CSV parser & joiner (Mukasshaf)
│   ├── domains.py                        # Canonical 7 domain IDs single source of truth (Mukasshaf)
│   ├── condition_labels.py               # Phase 3.1 protocol labels (Mukasshaf)
│   ├── condition_logger.py               # Phase 3.1 session timer / protocol prompter (Mukasshaf)
│   ├── serial_reader.py                  # ESP32 serial reader with unix_ts_ms arrival column (Mukasshaf)
│   ├── preprocess.py                     # Signal cleaning, peak detection, ACC_THRESHOLD_HW=8800.0
│   ├── features.py                       # 9-feature extraction (60s window, 30s stride)
│   ├── normalize.py                      # Within-subject z-score normalization
│   ├── classifier.py                     # Random Forest LOSO-CV model
│   ├── threshold_detector.py             # Layer 1 real-time μ+2σ detector
│   ├── batch_comparison.py               # Feature screening & comparison
│   ├── run_pipeline.py                   # Multi-subject batch runner
│   ├── eval_zero_shot.py                 # WESAD→Hardware transfer test (Mukasshaf)
│   ├── train_hw_loso.py                  # Hardware-trained classifier (Mukasshaf)
│   ├── go_nogo_check.py                  # M3 gate verification (Mukasshaf)
│   └── align_signals.py                  # Post-session Game CSV + Sensor CSV joiner (Mukasshaf)
│
├── validation/                           # Standalone M2 validation suite (Mukasshaf)
│   ├── validate_peak_detection.py
│   ├── validate_gsr_stability.py
│   ├── validate_motion_flag.py
│   ├── validate_drop_rate.py
│   ├── run_m2_validation.py
│   └── reports/M2_Validation_Summary.md
│
├── assets/
│   └── audio/
│       └── tension_drone.wav             # 70 Hz sine wave, 30s duration, 44.1kHz mono
│
├── outputs/
│   ├── game_logs/                        # Game event CSVs & domain_order.json
│   │   └── S{subject_id}_{session_ts}/
│   │       ├── events.csv                # Master 9-column event log
│   │       └── domain_order.json         # Shuffled domain order with seed
│   ├── features/                         # WESAD & Hardware feature matrices
│   ├── models/                           # rf_loso.pkl, hw_classifier.pkl
│   ├── plots/                            # Preprocessing & confusion matrices
│   └── results/                          # loso_fold_results.csv, transfer_gap.md
│
├── pyproject.toml                        # Project dependencies (uv managed)
├── uv.lock                              # Lockfile for reproducibility
└── README.md                             # Project overview
```

### Directory Rules
1. **No file outside `src/game/`** may be created or modified by the gamification engine implementation, except `pyproject.toml` (to add `pygame` dependency) and `assets/audio/`.
2. **No circular imports.** Dependency direction is strictly: `main → engine → {scenarios, scenario_logic, ui, ui_effects, audio, event_logger, bridge_interface} → constants`. No file may import from `engine.py` except `main.py`.
3. **`outputs/game_logs/`** directory is created at runtime by `event_logger.py` if it does not exist. Never committed to version control.

---

## 3. Component Hierarchy

```
main.py
  │
  ├── Parses CLI args (--subject, --fast-baseline, --fullscreen, --domain)
  ├── Initializes pygame.display, pygame.mixer
  └── Instantiates GameEngine → calls engine.run()

engine.py (GameEngine)
  │
  ├── Owns the Pygame event loop (single-threaded, 60 FPS cap)
  ├── Owns the state machine (current_state: EngineState enum)
  ├── Holds references to:
  │   ├── ScenarioRegistry       (from scenarios.py)
  │   ├── EventLogger            (from event_logger.py)
  │   ├── UIRenderer             (from ui.py)
  │   ├── UIEffects              (from ui_effects.py)
  │   ├── AudioController        (from audio.py)
  │   ├── BridgeInterface        (from bridge_interface.py — nullable/stub)
  │   └── ScenarioRunner         (from scenario_logic.py)
  │
  └── State machine drives all transitions (see §5)

scenarios.py
  │
  ├── @dataclass: Option (key, text, consequence_text, is_conforming?)
  ├── @dataclass: Scenario (id, domain_id, title, paradigm, priming_text,
  │                          priming_duration_s, decision_duration_s,
  │                          consequence_duration_s, options: list[Option],
  │                          has_deception_metric: bool, has_post_wait: bool,
  │                          post_wait_duration_s: int, scenario_type: ScenarioType,
  │                          math_problems: list[MathProblem] | None,
  │                          bart_config: BARTConfig | None,
  │                          reward_config: RewardAccumulatorConfig | None)
  ├── @dataclass: Domain (id, name, scenarios: list[Scenario])
  ├── enum: ScenarioType (STANDARD_MCQ, MIST_ARITHMETIC, BART_ESCALATION, REWARD_ACCUMULATOR, DELAY_WAIT)
  └── DOMAIN_REGISTRY: list[Domain] — all 7 domains, 14 scenarios, fully populated

scenario_logic.py
  │
  ├── class MISTRunner — handles rapid-fire arithmetic (Domain 1, Scenario A)
  ├── class BARTRunner — handles escalating pump mechanic (Domain 4, Scenario B)
  ├── class RewardAccumulator — handles growing reward + collapse (Domain 3, Scenario A)
  └── class DelayWaitRunner — handles post-decision wait screen (Domain 6, and impulsivity_gratification_b)

ui.py
  │
  ├── Color palette constants (HSL-based dark theme)
  ├── Font loader (system fallback chain)
  ├── draw_card(), draw_button(), draw_timer_bar(), draw_progress_bar()
  ├── draw_priming_screen(), draw_decision_screen(), draw_consequence_screen()
  ├── draw_baseline_screen() — breathing circle animation
  ├── draw_rest_screen() — soothing gradient
  ├── draw_debrief_screen()
  ├── draw_id_input_screen()
  ├── draw_peer_average_bar() — MIST fake comparison (Domain 1A)
  ├── draw_team_chat() — Asch conformity group display (Domain 2)
  ├── draw_evaluator_panel() — TSST neutral faces (Domain 7)
  ├── draw_composure_bar() — MPU6050 deception metric bar (Domain 7)
  └── draw_instability_gauge() — BART system instability (Domain 4B)

ui_effects.py
  │
  ├── TextJitter — ≤3px amplitude, ≤2Hz frequency, activates on trigger
  ├── TimerBarColorTransition — green(100%) → amber(33%) → red(10%)
  ├── ScreenVibration — ≤3px, for reward accumulator instability
  └── ButtonFlash — 200ms red flash on wrong answer (MIST only)

audio.py
  │
  ├── load_tension_drone() — loads WAV once
  ├── start_drone(fade_in_ms) — fade-in during final 1/3 of timer
  ├── stop_drone(fade_out_ms) — fade-out on phase transition
  └── Volume capped at 0.30 (30%)

event_logger.py
  │
  ├── Opens CSV file on session start
  ├── log_event(event_type, metadata_dict) — writes row with unix_ts_ms timestamp
  ├── flush() — after every event (no buffering)
  └── close() — on session end

bridge_interface.py
  │
  ├── class BridgeInterface(Protocol) — abstract interface
  │   ├── get_latest_sample() → SensorSample | None
  │   └── get_mpu_variance() → float | None
  ├── class StubBridge — returns None for all calls (used when no hardware)
  └── (Mukasshaf implements the real bridge in a separate module later)

constants.py
  │
  ├── SCREEN_WIDTH, SCREEN_HEIGHT, FPS
  ├── BASELINE_DURATION_S, FAST_BASELINE_DURATION_S
  ├── INTRA_DOMAIN_REST_S, INTER_DOMAIN_REST_S
  ├── DRONE_VOLUME, DRONE_FADE_IN_MS, DRONE_FADE_OUT_MS
  ├── JITTER_MAX_PX, JITTER_MAX_HZ
  ├── DECEPTION_THRESHOLD_SIGMA
  ├── TIMEOUT_EVENT_TYPE
  ├── All domain/scenario string IDs
  └── Color palette hex values
```

---

## 4. Data Flow Pipelines

### 4.1 Game Event Pipeline (Standalone — No Hardware)

```
User Input (keyboard)
    │
    ▼
GameEngine.handle_input()
    │
    ├── Updates internal state (selected_option, timer, etc.)
    ├── Calls EventLogger.log_event(event_type, metadata)
    │       │
    │       ▼
    │   CSV row written to: outputs/game_logs/S{id}_{ts}/events.csv
    │   Format: unix_ts_ms, event_type, domain, scenario_id, choice_data,
    │           key_pressed, option_index, response_time_ms, metadata
    │
    └── Triggers state transition if applicable
```

### 4.2 Hardware Integration Pipeline (Future — Mukasshaf's Bridge)

```
ESP32 (Analog Pulse Sensor + GSR + MPU6050)
    │ USB Serial @ 66.67 Hz
    ▼
pulse_serial_bridge.py (Mukasshaf's module — NOT in src/game/)
    │ Background thread: serial.readline() → parse → SensorSample
    │ Stamps each sample with int(time.time_ns() // 1_000_000) (unix_ts_ms)
    ▼
queue.Queue(maxsize=256)
    │
    ▼
GameEngine (main thread, once per frame):
    │ bridge.get_latest_sample() → drains queue, returns latest
    │ bridge.get_mpu_variance()  → returns rolling 1s variance of 3-axis magnitude sqrt(x^2+y^2+z^2)
    │
    ├── Appends sensor data to event CSV row (if sample available)
    └── Updates composure bar (social_evaluation domain only, if MPU variance > threshold
        sustained for >=3 consecutive samples with 5s cooldown)
```

### 4.3 Synchronization Contract

- **Clock:** `int(time.time_ns() // 1_000_000)` — Unix epoch milliseconds (`unix_ts_ms`). Used by both game events and serial bridge.
- **SYNC_PULSE:** At `BASELINE_START`, the engine emits a `SYNC_PULSE` event with the unix_ts_ms timestamp. The serial bridge must log the same timestamp in its own CSV. This allows post-hoc alignment even if thread clocks drift.
- **No shared mutable state** between game thread and bridge thread — only `queue.Queue`.

---

## 5. State Machine Lifecycle

```
┌──────────────┐
│  STATE_INIT  │  pygame.init(), load assets, parse CLI
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│  STATE_ID_INPUT  │  Participant enters Subject ID via keyboard
└──────┬───────────┘
       │ [ENTER pressed with valid ID]
       ▼
┌────────────────┐
│ STATE_BASELINE │  3 min (or --fast-baseline: 10s) resting screen
│                │  Breathing circle animation, countdown timer
│                │  Emits: BASELINE_START, BASELINE_END
│                │  Computes: μ_acc, σ_acc from bridge (if connected)
└──────┬─────────┘
       │ [timer expires]
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DOMAIN LOOP (×7, randomized)                │
│                                                                 │
│  ┌────────────────┐                                             │
│  │ STATE_PRIMING  │  Show scenario context text (5–10s)         │
│  │                │  Emits: DOMAIN_START (first scenario only), │
│  │                │         SCENARIO_PRIMING                    │
│  └──────┬─────────┘                                             │
│         │ [timer expires]                                       │
│         ▼                                                       │
│  ┌─────────────────┐                                            │
│  │ STATE_DECISION  │  MCQ / MIST / BART / Accumulator / Wait   │
│  │                 │  Countdown timer bar (green→amber→red)     │
│  │                 │  UI effects active (jitter, drone)         │
│  │                 │  Deception metric (social_evaluation only)  │
│  │                 │  Emits: DECISION_PRESENTED, OPTION_SELECTED│
│  │                 │         or TIMEOUT_NO_RESPONSE             │
│  └──────┬──────────┘                                            │
│         │ [timer expires — selection held for full duration]     │
│         ▼                                                       │
│  ┌─────────────────────┐                                        │
│  │ STATE_POST_WAIT     │  future_uncertainty (10-12s) or        │
│  │ (conditional)       │  impulsivity_gratification_b (15s)     │
│  │                     │  "Processing..." spinner, no info      │
│  └──────┬──────────────┘                                        │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────────┐                                           │
│  │ STATE_FEEDBACK   │  Show consequence text (3–5s)             │
│  │                  │  Emits: SCENARIO_END                      │
│  └──────┬───────────┘                                           │
│         │ [timer expires]                                       │
│         ▼                                                       │
│  ┌─────────────────────────┐                                    │
│  │ STATE_INTRA_REST (15s)  │  Between Scenario A and B          │
│  │ or STATE_INTER_REST     │  Between domains (60s)             │
│  │  (60s)                  │  Emits: REST_START, REST_END       │
│  └──────┬──────────────────┘                                    │
│         │ [timer expires → next scenario or next domain]        │
│         ▼                                                       │
│     (loop back to STATE_PRIMING for next scenario/domain)       │
└─────────────────────────────────────────────────────────────────┘
       │ [all 7 domains complete]
       ▼
┌────────────────┐
│ STATE_DEBRIEF  │  "Session complete" message
│                │  Display session duration, scenarios completed
│                │  Emits: SESSION_END
│                │  Close CSV, quit pygame
└────────────────┘
```

### State Transition Rules
1. **No state may be skipped** — every session passes through every state in order.
2. **No backward transitions** — the state machine is strictly forward-only. There is no "retry" or "go back."
3. **Fixed DECISION duration (C1)** — `STATE_DECISION` always holds for the full `decision_duration_s`. A valid keypress immediately locks in the selection and logs `OPTION_SELECTED` (recording the precise `response_time_ms`), but does NOT cause an early exit. The UI displays the locked-in choice (selected card highlighted, others dimmed) for the remainder of the timer. Transition to `STATE_POST_WAIT` or `STATE_FEEDBACK` occurs exclusively when the timer reaches 0. This guarantees a continuous active window (≥60s total active epoch) to satisfy the Random Forest classifier's HRV/EDA windowing requirement.
4. **Timeout always advances** — if the decision timer expires without a choice, the engine logs `TIMEOUT_NO_RESPONSE`, displays the timeout consequence text ("The system has made a decision for you"), and advances to `STATE_FEEDBACK`.
5. **`STATE_POST_WAIT` is entered when post-wait condition is met** — applies to `future_uncertainty` scenarios (`has_post_wait=True`, 10–12s) and conditionally to `impulsivity_gratification_b` (15s if Key 2 "Request more time" was selected).
6. **`STATE_INTRA_REST` vs `STATE_INTER_REST`** — the engine tracks whether it just completed Scenario A (→ intra, 15s) or Scenario B (→ inter, 60s, or → debrief if last domain).
7. **Same-Frame Event Precedence (M2)** — In every frame, `_handle_input()` processes all pending OS and keyboard events before `_update()` decrements timers. A valid keypress in the same frame as timer expiry is logged as `OPTION_SELECTED`, never `TIMEOUT_NO_RESPONSE`.
8. **Window Focus Loss Handling (M3)** — If the Pygame window loses OS focus (`pygame.WINDOWFOCUSLOST`), timers and audio drones freeze immediately, and `FOCUS_LOST` is logged. Upon focus restoration (`pygame.WINDOWFOCUSGAINED`), `FOCUS_GAINED` is logged, and timers resume.

---

## 6. Hard System Constraints (from Locked Decisions)

| Constraint | Value | Source |
|---|---|---|
| Input method | Keyboard ONLY (keys 1,2,3,4 + Enter + Escape) | Decisions.md — protect PPG/GSR |
| Mouse cursor | Hidden via `pygame.mouse.set_visible(False)` | Prevent accidental mouse use |
| Scoring | BANNED — no numerical scores anywhere in UI | Decisions.md |
| Domain order | Randomized per session via `random.shuffle()` with seed logged | Decisions.md — unconditional, all domains |
| Deception metric | `social_evaluation` domain ONLY | Decisions.md |
| MPU6050 threshold | Per-subject: μ_acc + 1.5 × σ_acc (from baseline) | Decisions.md |
| Audio during scenarios | 60–80 Hz tension drone ONLY, final 1/3 of timer, ≤30% volume | Decisions.md |
| Jitter | ≤3px amplitude, ≤2Hz frequency | Decisions.md |
| Strobing | BANNED (nothing >3 Hz) | Decisions.md — WCAG |
| Full-screen color inversion | BANNED | Decisions.md |
| Baseline duration | 180s (3 min) standard; 10s with `--fast-baseline` | HRV statistical validity |
| Intra-domain rest | 15s | Decisions.md |
| Inter-domain rest | 60s | Decisions.md |
| FPS cap | 60 FPS (`clock.tick(60)`) | Pygame standard; sufficient for UI |
| Screen resolution | 1280×720 default; `--fullscreen` uses native | Balances readability and universality |
