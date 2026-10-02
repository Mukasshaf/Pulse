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
| **Threading** | Python stdlib `threading` | One daemon reader thread per sensor bridge; lock-protected latest-sample buffer (§4.2) |
| **Serial I/O** | `pyserial>=3.5`, imported lazily | Only the sensor bridge needs it; the engine starts without it and falls back to `StubBridge` |
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

```
Pulse/                                    # Project root
├── firmware/
│   └── firmware.ino                      # ESP32 66.67 Hz ADC/IMU sampling sketch (115200 baud)
├── data/
│   ├── WESAD/S{id}/S{id}.pkl             # Phase 1 software-bridge dataset
│   └── hardware/
│       ├── raw/S{id}/recorded_data.csv, condition_log.csv
│       └── labeled/labeled_S{id}_hw.csv  # Auto-labeled hardware data
├── src/
│   ├── domains.py                        # Canonical 7 domain IDs — single source of truth for both tracks
│   ├── align_signals.py                  # Post-session Game CSV + Sensor CSV joiner (on unix_ts_ms)
│   │
│   ├── game/                             # ← Phase 4 Gamification Engine (Ayush)
│   │   ├── main.py                       # CLI entry point: `python -m src.game.main`
│   │   ├── engine.py                     # GameEngine: run loop + render dispatch (composes the mixins below)
│   │   ├── engine_state.py               # SessionConfig, EngineBase: state, transitions, exposure floors
│   │   ├── engine_input.py               # EngineInputMixin: keyboard / focus handling per scenario type
│   │   ├── engine_timer.py               # EngineTimerMixin: per-frame updates, clock monitor, composure gating
│   │   ├── scenarios.py                  # Domain/Scenario/Option dataclasses + the 14-scenario registry
│   │   ├── scenario_logic.py             # MISTRunner, BARTRunner, RewardAccumulator, DelayWaitRunner
│   │   ├── ui.py                         # UIRenderer facade (public import site; 12 lines)
│   │   ├── ui_core.py                    # Surface, fonts, text fitting/wrapping, cards, palette-safe `_mix`
│   │   ├── ui_components.py              # Key badge, compass, meters, evaluator panel, composure bar
│   │   ├── ui_screens.py                 # ID input, baseline, priming, briefing popup, feedback, rest, debrief
│   │   ├── ui_post_wait.py               # Post-decision waiting screens
│   │   ├── ui_domains.py                 # Decision dispatch to a skin + skinless fallback layouts
│   │   ├── ui_effects.py                 # Jitter, timer bar colour transition, vibration, flash, shatter
│   │   ├── skins/                        # One module per simulation skin (14): exam_hall.py … classroom_critique.py
│   │   ├── audio.py                      # Tension drone loader, fade-in/fade-out, pause/resume, volume cap
│   │   ├── event_logger.py               # 9-column CSV writer with unix_ts_ms timestamps
│   │   ├── constants.py                  # Enums, timing, safety limits, paradigm parameters, Ferrari palette tokens
│   │   ├── bridge_interface.py           # BridgeInterface protocol, SensorSample, StubBridge
│   │   ├── sensor_stream.py              # Stream row parsing (CSV/JSON) + StreamBridge buffer and motion variance
│   │   ├── sensor_replay.py              # ReplayBridge: paced replay, or live follow of a growing CSV
│   │   └── sensor_bridge.py              # SerialBridge, ESP32 port scan / baud probe, `create_bridge()` factory
│   │
│   ├── hardware/
│   │   └── serial_reader.py              # Standalone ESP32 recorder with unix_ts_ms arrival column (Mukasshaf)
│   └── pipeline/                         # ← Phase 1–3 biosignal pipeline (Mukasshaf)
│       ├── wesad_loader.py               # WESAD pickle parser
│       ├── hardware_loader.py            # Hardware CSV parser & condition-log joiner
│       ├── condition_labels.py           # Phase 3.1 protocol labels
│       ├── condition_logger.py           # Phase 3.1 session timer / protocol prompter
│       ├── preprocess.py                 # Signal cleaning, peak detection, ACC_THRESHOLD_HW=8800.0
│       ├── features.py                   # 9-feature extraction (60s window, 30s stride)
│       ├── normalize.py                  # Within-subject z-score normalization
│       ├── classifier.py                 # Random Forest LOSO-CV model
│       ├── threshold_detector.py         # Layer 1 real-time μ+2σ detector
│       ├── batch_comparison.py           # Feature screening & comparison
│       ├── run_pipeline.py               # Multi-subject batch runner
│       └── eval_zero_shot.py, train_hw_loso.py, go_nogo_check.py   # Phase 3 stubs
│
├── tests/
│   ├── conftest.py                       # Headless SDL drivers, shared fixtures
│   ├── game/                             # 12 test modules, 104 tests (see TEST_CRITERIA_AND_EDGE_CASES.md)
│   └── pipeline/                         # 3 placeholder tests
│
├── validation/                           # Standalone M2 validation suite (Mukasshaf)
│   ├── validate_*.py, run_m2_*.py
│   └── reports/M2_Validation_Summary.md, M2_Full_Validation_Report.md
│
├── assets/audio/tension_drone.wav        # 70 Hz sine wave, 30s duration, 44.1kHz mono
│
├── outputs/
│   ├── game_logs/                        # Created at runtime, never committed
│   │   └── S{subject_id}_{session_ts}/
│   │       ├── events.csv                # Master 9-column event log
│   │       ├── domain_order.json         # Shuffled domain order with seed
│   │       └── sensor_stream.csv         # Only when the engine owns the serial port (integrated topology, §4.2)
│   ├── features/                         # WESAD & Hardware feature matrices
│   ├── models/                           # rf_loso.pkl, hw_classifier.pkl
│   ├── plots/                            # Preprocessing & confusion matrices
│   └── results/                          # loso_fold_results.csv, transfer_gap.md
│
├── CLAUDE.md, GEMINI.md                  # Agent context files (identical content)
├── pyproject.toml                        # Dependencies (uv managed), mypy and pytest configuration
├── uv.lock                               # Lockfile for reproducibility
└── README.md                             # Project overview
```

### Directory Rules
1. **The gamification engine lives in `src/game/` and `tests/game/`.** Outside those it may touch only `pyproject.toml`, `assets/audio/`, and the documentation. Lint- and type-only maintenance of `src/pipeline/`, `src/hardware/` and `validation/` is allowed when it is proven behaviour-preserving (ADR-B7).
2. **No circular imports.** Dependency direction is strictly downward:
   `main → engine → {engine_input, engine_timer} → engine_state → {scenarios, scenario_logic, ui, audio, event_logger, bridge_interface} → constants`,
   `ui → {ui_domains, ui_screens, ui_post_wait} → skins/* → ui_components → ui_core → {ui_effects, constants}`, and
   `sensor_bridge → {sensor_replay, sensor_stream} → {bridge_interface, constants}`.
   No module may import from `engine.py` except `main.py`; no skin may import another skin.
3. **Every Python file is at most 500 lines** (CODING_STANDARDS §8.2). The largest module in `src/game/` is `scenarios.py` at 428 lines. New skins go in their own `skins/<name>.py` module and are composed in `ui_domains.py`.
4. **`outputs/game_logs/`** is created at runtime by `event_logger.py` if it does not exist. Never committed to version control.

---

## 3. Component Hierarchy

```
main.py
  │
  ├── parse_cli() → (SessionConfig, BridgeOptions)
  │     --subject (must match SUBJECT_ID_PATTERN), --fast-baseline, --fullscreen/--no-fullscreen,
  │     --window-size, --domain, --no-exposure-floor [developer testing only],
  │     --extended-rest [60 s inter-domain wash-out instead of 30 s],
  │     --bridge {auto,serial,stub,replay} [default auto], --bridge-port, --bridge-source, --bridge-follow
  ├── Builds SessionConfig with the exposure guarantees ON (hold_full_decision,
  │   min_priming_s, min_active_epoch_s) unless --no-exposure-floor is given
  ├── create_bridge() BEFORE the window opens (a port scan must never show a frozen screen);
  │   prints "Sensor bridge [mode]: detail" and warns when the session runs on StubBridge
  ├── Initializes pygame.display, pygame.mixer
  ├── Instantiates GameEngine(config, screen, bridge=...) → calls engine.run()
  └── Always closes the bridge and quits pygame in `finally`

engine.py — GameEngine(EngineInputMixin, EngineTimerMixin)
  │
  ├── run(): the Pygame event loop (single-threaded, 60 FPS cap); blocks mouse events, grabs input,
  │          monitors the clock, logs an aborted SESSION_END on ESC/QUIT
  └── _render(): dispatches the current state to UIRenderer

engine_state.py — SessionConfig, session_output_dir(), EngineBase
  │
  ├── Owns the state machine (current_state: EngineState enum) and every piece of session state
  ├── Holds references to:
  │   ├── domain registry        (from scenarios.py, shuffled with the logged seed)
  │   ├── EventLogger            (from event_logger.py)
  │   ├── UIRenderer             (from ui.py)
  │   ├── TextJitter / ScreenVibration / ButtonFlash / TimerBarColorTransition (from ui_effects.py)
  │   ├── AudioController        (from audio.py — None when the drone asset is missing)
  │   ├── BridgeInterface        (from bridge_interface.py — StubBridge when no hardware)
  │   └── MISTRunner / BARTRunner / RewardAccumulator / DelayWaitRunner (from scenario_logic.py)
  ├── _transition_to(): validates against VALID_TRANSITIONS, emits lifecycle events, sets the state timer
  │                     (INTER_REST uses config.inter_domain_rest_s; INTRA_REST uses INTRA_DOMAIN_REST_S)
  ├── _enter_decision(): builds the runner for the scenario type (MIST gets 60 generated problems;
  │                      BART gets the 1.5 s pump cooldown)
  ├── _exit_decision(), _decision_floor_ms(), _priming_floor_ms(): commit-and-hold + exposure floors (§5 Rules 1, 3)
  └── _shutdown(): closes the logger, the audio and the bridge

engine_input.py — EngineInputMixin(EngineBase)
  │
  ├── _handle_input(): focus loss/gain (pause + log), TAB/Q/H briefing popup, per-state key routing
  ├── _handle_standard_input / _handle_mist_input / _handle_bart_input / _handle_reward_input
  │     each returns True only when the key was acted on; the per-item latency clock restarts
  │     only from an accepted response (an ignored key never resets it)
  └── Number keys are ignored once a choice is committed or while the briefing popup hides the options

engine_timer.py — EngineTimerMixin(EngineBase)
  │
  ├── _monitor_clock(): CLOCK_ANOMALY on a frame stall or wall-clock step
  ├── _update(): returns early while the window is unfocused; drives the per-state update
  ├── _update_baseline(): collects μ_acc / σ_acc from the bridge; marks telemetry live or lost
  ├── _update_composure(): 4 Hz gating, ≥3 consecutive supra-threshold samples, 5 s cooldown
  ├── _tick_mist(): advances the per-item countdown; a timed-out item is logged as an incorrect MATH_ANSWER
  └── _update_decision(): timer → drone / colour / jitter → composure → pending-hold exit → runners → timeout

scenarios.py
  │
  ├── @dataclass: Option (key, text, consequence_text, is_conforming?)
  ├── @dataclass: Scenario (id, domain_id, title, paradigm, priming_text,
  │                          priming_duration_s, decision_duration_s,
  │                          consequence_duration_s, options: list[Option],
  │                          scenario_type: ScenarioType, skin: str,
  │                          has_deception_metric: bool, has_post_wait: bool,
  │                          post_wait_duration_s: int, post_wait_text: str,
  │                          math_problems: list[MathProblem] | None,
  │                          bart_config: BARTConfig | None,
  │                          reward_config: RewardAccumulatorConfig | None,
  │                          delay_wait_outcomes, timeout_consequence,
  │                          jitter_trigger_s, drone_trigger_fraction)
  ├── @dataclass: Domain (id, name, scenarios: tuple[Scenario, Scenario])
  ├── Durations come from constants only: DEFAULT_PRIMING_DURATION_S (20), DEFAULT_DECISION_DURATION_S (45),
  │   MIST_DECISION_DURATION_S (40), DEFAULT_CONSEQUENCE_DURATION_S (4) — no duration literal in the registry
  └── build_domain_registry() → list[Domain] — all 7 domains, 14 scenarios, fully populated

scenario_logic.py
  │
  ├── class MISTRunner — rapid-fire arithmetic with an adaptive per-item countdown (Domain 1, Scenario A):
  │                      update(dt_ms) times an item out; two correct in a row tighten the limit 10 %,
  │                      two incorrect (or timed-out) in a row ease it 10 %, bounded to 3–12 s
  ├── class BARTRunner — single-balloon pump mechanic (Domain 4, Scenario B): linear hazard
  │                      burst_probability(k) = 0.02 + 0.03·(k−1), certain burst at pump 15,
  │                      1.5 s pacing cooldown (can_pump / get_cooldown_fraction),
  │                      get_pumps_remaining_after_burst() replays the true counterfactual from a copy of the RNG
  ├── class RewardAccumulator — growing reward + collapse (Domain 3, Scenario A)
  └── class DelayWaitRunner — post-decision wait screen (Domain 6, and impulsivity_gratification_b)

ui.py — class UIRenderer(UIDomainSkins, UIScreens, UIPostWait)   (facade; the only UI import site)
  │
  ├── ui_core.py        UIRendererCore: fonts (exact Segoe UI / Consolas files), _draw_text(max_width=),
  │                     _draw_wrapped_text (same-family downscale, ellipsis), _draw_card, _ink_for,
  │                     _mix(color, toward, amount) — blends a palette token toward a neutral, hue unchanged
  ├── ui_components.py  UIComponents: _draw_key_badge (neutral key prompt, inverted once chosen),
  │                     _draw_compass, draw_peer_average_bar, draw_instability_gauge, draw_team_chat,
  │                     draw_evaluator_panel, draw_composure_bar (fraction=None → honest STANDBY state)
  ├── ui_screens.py     UIScreens: draw_id_input, draw_baseline (static fixation cross, no paced breathing),
  │                     draw_priming, draw_question_popup, draw_feedback, draw_rest, draw_debrief
  ├── ui_post_wait.py   UIPostWait: draw_post_wait
  ├── ui_domains.py     UIDomainSkins: draw_decision → _render_skin(scenario.skin) or a skinless fallback
  │                     (_draw_standard_decision, _draw_mist_decision, _draw_bart_decision, _draw_reward_decision)
  └── skins/*.py        14 classes, one `_draw_skin_<name>` method each; composed by UIDomainSkins

ui_effects.py
  │
  ├── TextJitter — ≤3px displacement (vector magnitude), ≤2Hz on BOTH axes, activates on trigger
  ├── TimerBarColorTransition — green(100%) → amber(33%) → red(10%)
  ├── ScreenVibration — ≤2px displacement, ≤2Hz, for reward accumulator instability
  ├── ButtonFlash — 200ms red flash on a wrong or timed-out answer (MIST only)
  └── RadialShatterEffect — 12-particle dispersal on chest collapse (palette tokens only)

audio.py
  │
  ├── AudioController(drone_path) — loads the WAV once
  ├── start_drone(fade_in_ms) — fade-in during final 1/3 of timer
  ├── stop_drone(fade_out_ms) — fade-out on phase transition
  ├── pause() / resume() — suspend and resume the drone on window focus loss / gain
  └── Volume capped at 0.30 (30%)

event_logger.py
  │
  ├── Opens CSV file on session start
  ├── log_event(GameEvent) — writes one 9-column row with unix_ts_ms timestamp
  ├── flush after every event (no buffering)
  ├── save_domain_order() — domain_order.json with the shuffle seed
  └── close() — on session end

bridge_interface.py
  │
  ├── @dataclass SensorSample (unix_ts_ms, bvp, gsr, acc_x, acc_y, acc_z)
  ├── class BridgeInterface(Protocol)
  │   ├── get_latest_sample() → SensorSample | None
  │   ├── get_mpu_variance() → float | None
  │   └── close() → None
  └── class StubBridge — returns None for all calls (used when no hardware)

sensor_stream.py / sensor_replay.py / sensor_bridge.py   (see §4.2)
  │
  ├── parse_sensor_line() — firmware CSV (7 ints), serial_reader CSV (8 ints), or a JSON object
  ├── class StreamBridge — thread-safe latest sample + 1 s rolling variance of acceleration magnitude
  ├── class SerialBridge(StreamBridge) — owns the ESP32 port, reads on a daemon thread, records every valid row
  ├── class ReplayBridge(StreamBridge) — paced replay of a recording, or live follow of a growing CSV
  ├── list_candidate_ports() / probe_port() — USB-VID filtered scan and baud negotiation (115200)
  └── create_bridge(mode, …) → BridgeSetup(bridge, mode, detail)

constants.py
  │
  ├── SCREEN_WIDTH, SCREEN_HEIGHT, FPS
  ├── Timing: BASELINE_DURATION_S, FAST_BASELINE_DURATION_S, INTRA_DOMAIN_REST_S (15),
  │           INTER_DOMAIN_REST_S (30), INTER_DOMAIN_REST_EXTENDED_S (60),
  │           DEFAULT_PRIMING_DURATION_S (20), DEFAULT_DECISION_DURATION_S (45), MIST_DECISION_DURATION_S (40),
  │           DEFAULT_CONSEQUENCE_DURATION_S (4), MIN_PRIMING_DURATION_S (8), MIN_ACTIVE_EPOCH_S (60)
  ├── Safety: DRONE_VOLUME, JITTER_MAX_PX/HZ, VIBRATION_MAX_PX/HZ, COMPASS_SPIN_MAX_RPM
  ├── Paradigms: MIST_* (adaptive item limit), BART_* (hazard curve, pump cooldown), REWARD_*
  ├── Bridge: BRIDGE_BAUD_CANDIDATES, BRIDGE_PROBE_*, BRIDGE_VARIANCE_WINDOW_MS, BRIDGE_STALE_AFTER_MS
  ├── DECEPTION_THRESHOLD_SIGMA, composure gating constants
  ├── EngineState, EventType (22), ScenarioType, VALID_TRANSITIONS, exception classes
  └── Ferrari palette tokens (§6.1) — the only place a chromatic colour is defined
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

### 4.2 Hardware Integration Pipeline (Sensor Bridge)

A serial port can be opened by one process only, and `src/hardware/serial_reader.py` is the pipeline's recorder. The engine therefore supports two topologies, selected with `--bridge` (ADR-B1):

```
A. DECOUPLED (primary data path)                    B. INTEGRATED (engine owns the port)

ESP32 ──USB serial 115200──► serial_reader.py       ESP32 ──USB serial 115200──► SerialBridge (daemon thread)
                                │ owns the port                                    │ parse_sensor_line()
                                ▼                                                  │ stamp unix_ts_ms on arrival
                 data/hardware/raw/…/recorded_*.csv                                ├──► outputs/game_logs/S…/sensor_stream.csv
                                │ (growing file)                                   │     (same 8-column schema as serial_reader)
                                ▼                                                  ▼
        ReplayBridge(follow=True) tails new rows                       StreamBridge buffer (lock-protected)
        --bridge replay --bridge-follow --bridge-source <csv|dir>      --bridge auto (default) or --bridge serial
                                │                                                  │
                                └──────────────► GameEngine (main thread, once per frame) ◄──────────┘
                                                   bridge.get_latest_sample() → most recent unread sample
                                                   bridge.get_mpu_variance()  → 1 s rolling variance of √(x²+y²+z²)
```

- **Stream contract** (`firmware/firmware.ino`): `sample_idx,timestamp_ms,pulse_raw,gsr_raw,acc_x,acc_y,acc_z` at 66.67 Hz. The firmware sends raw PPG, GSR and acceleration only — no heart rate and no JSON. `parse_sensor_line()` also accepts the 8-column recorded format and a JSON object (aliases such as `ppg`, `eda`, `ax`; unknown keys such as a firmware-side `hr` are ignored) so a later firmware revision does not break the bridge. Headers, `#` comments, non-numeric and non-finite values are rejected and counted.
- **Auto-detection** opens only ports whose USB vendor ID is a known ESP32 serial bridge (CP210x `10C4`, CH340/CH9102 `1A86`, FTDI `0403`, Espressif `303A`), then requires 3 valid rows within 3 s at 115200 baud. A Bluetooth COM port or another instrument is never opened. `--bridge-port COM3` skips the scan.
- **`--bridge auto`** (default): use the ESP32 if it answers, otherwise fall back to `StubBridge` and print a warning. **`--bridge serial`**: the ESP32 is required; the session refuses to start without it (`BridgeUnavailableError`, exit code 2). **`--bridge replay`**: feed from a recording (paced by its own timestamps) or follow a live one. **`--bridge stub`**: no telemetry.
- **No lost recording:** whenever the engine owns the port it writes every valid row to `sensor_stream.csv` in the session folder, in `serial_reader.py`'s column order, so `hardware_loader.py` and `align_signals.py` read it unchanged. A write failure stops the recording but not the telemetry (`SerialBridge.error`).
- **Stale telemetry is not live telemetry:** `get_mpu_variance()` returns `None` with fewer than 20 samples in the window or when the last sample is older than 1.5 s. The engine then shows the composure display in STANDBY rather than a frozen reading.
- **Composure gating** (`social_evaluation` only): threshold `μ_acc + 1.5·σ_acc` from the resting baseline, sampled at 4 Hz; a drop needs ≥3 consecutive supra-threshold samples and respects a 5 s cooldown.
- **Thread model:** one daemon reader thread per bridge; the only shared state is the lock-protected buffer inside `StreamBridge`. The engine never blocks on I/O.

### 4.3 Synchronization Contract

- **Clock:** `int(time.time_ns() // 1_000_000)` — Unix epoch milliseconds (`unix_ts_ms`). Used by both game events and serial bridge.
- **SYNC_PULSE:** At `BASELINE_START`, the engine emits a `SYNC_PULSE` event with the unix_ts_ms timestamp. Its metadata records the bridge class, the audio state and `inter_domain_rest_s`, so a log states which configuration produced it.
- **No shared mutable state** between the game thread and a bridge thread except the lock-protected buffer inside `StreamBridge`.
- **Sensor rows carry the same clock:** `SerialBridge` stamps `unix_ts_ms` on arrival exactly as `serial_reader.py` does, so `align_signals.py` joins either recording to `events.csv`.

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
│                │  Static fixation cross (no paced breathing), countdown timer
│                │  Emits: BASELINE_START, BASELINE_END
│                │  Computes: μ_acc, σ_acc from bridge (if connected)
└──────┬─────────┘
       │ [timer expires]
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DOMAIN LOOP (×7, randomized)                │
│                                                                 │
│  ┌────────────────┐                                             │
│  │ STATE_PRIMING  │  Show scenario context text (20s, locked)   │
│  │                │  Emits: DOMAIN_START (first scenario only), │
│  │                │         SCENARIO_PRIMING                    │
│  └──────┬─────────┘                                             │
│         │ [timer expires, or SPACE after the priming floor]     │
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
│  │ STATE_FEEDBACK   │  Show consequence text (4s)               │
│  │                  │  Emits: SCENARIO_END                      │
│  └──────┬───────────┘                                           │
│         │ [timer expires]                                       │
│         ▼                                                       │
│  ┌─────────────────────────┐                                    │
│  │ STATE_INTRA_REST (15s)  │  Between Scenario A and B          │
│  │ or STATE_INTER_REST     │  Between domains (30s default,     │
│  │  (30s / 60s extended)   │  60s with --extended-rest)         │
│  │                         │  Emits: REST_START, REST_END       │
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
1. **No state may be skipped** — every session passes through every state in order. `STATE_PRIMING` runs 20s for all 14 scenarios (`DEFAULT_PRIMING_DURATION_S`, ADR-B3) and may be *shortened* with SPACE/ENTER, but only after the **priming floor**: `max(min_priming_s, min_active_epoch_s − decision_duration_s − DEFAULT_CONSEQUENCE_DURATION_S)`. With the production values (8s read floor, 60s active epoch) that is 11s for 45s scenarios and 16s for the 40s MIST scenario, so PRIMING + DECISION + FEEDBACK never falls below 60s. Until the floor passes the card shows "Read carefully • Starting in Ns" instead of the skip prompt.
2. **No backward transitions** — the state machine is strictly forward-only. There is no "retry" or "go back."
3. **Fixed DECISION duration (C1)** — `STATE_DECISION` always holds for the full `decision_duration_s`. A valid keypress immediately locks in the selection and logs `OPTION_SELECTED` (recording the precise `response_time_ms`), but does NOT cause an early exit. The UI displays the locked-in choice (selected card highlighted, others dimmed) for the remainder of the timer. Transition to `STATE_POST_WAIT` or `STATE_FEEDBACK` occurs exclusively when the timer reaches 0. This guarantees a continuous active window (≥60s total active epoch) to satisfy the Random Forest classifier's HRV/EDA windowing requirement.
   - **Implementation (2026-10-02):** `SessionConfig.hold_full_decision`. `main.py` turns it on for every real session; it defaults to `False` only so unit tests can drive the machine without waiting, and `--no-exposure-floor` exposes that for development. The hold covers every scenario type: BART secure/burst, reward claim/collapse and MCQ selections all commit immediately (`_exit_decision()` stores `_pending_exit`) and leave on timer expiry. Further number keys are ignored once a choice is committed.
   - **Stimulus invariance:** the drone, timer colour and jitter follow the clock only, so they run identically whether or not a choice has been committed. The drone stops at the actual state exit, not at the keypress.
   - **MIST:** the arithmetic task runs on the clock (60 generated problems, randomised answer positions), so it cannot end early by answering. Expiry after at least one answer is completion, not `TIMEOUT_NO_RESPONSE`.
   - **MIST adaptive difficulty (ADR-B3):** every item has its own countdown, starting at 8 s. Two consecutive correct answers tighten it by 10 %; two consecutive incorrect or timed-out answers ease it by 10 %; it stays within 3–12 s. An item that runs out is scored incorrect, logged as `MATH_ANSWER` with `timed_out: true`, and replaced. This replaces the separate pretest calibration block, which is not implemented and is no longer planned.
   - **BART pacing (ADR-B4):** each pump starts a 1.5 s cooldown during which further pump keys are ignored (the card reads "PUBLISHING POST..."). Securing is never blocked. Every accepted pump logs the hazard it faced.
4. **Timeout always advances** — if the decision timer expires without a choice, the engine logs `TIMEOUT_NO_RESPONSE`, displays the timeout consequence text ("The system has made a decision for you"), and advances to `STATE_FEEDBACK`.
5. **`STATE_POST_WAIT` is entered when post-wait condition is met** — applies to `future_uncertainty` scenarios (`has_post_wait=True`, 10–12s) and conditionally to `impulsivity_gratification_b` (15s if Key 2 "Request more time" was selected).
6. **`STATE_INTRA_REST` vs `STATE_INTER_REST`** — the engine tracks whether it just completed Scenario A (→ intra, 15s) or Scenario B (→ inter, `SessionConfig.inter_domain_rest_s`: 30s by default, 60s with `--extended-rest`; or → debrief if last domain). `REST_START` metadata records `is_inter` and the actual `duration_s` (ADR-B2).
7. **Same-Frame Event Precedence (M2)** — In every frame, `_handle_input()` processes all pending OS and keyboard events before `_update()` decrements timers. A valid keypress in the same frame as timer expiry is logged as `OPTION_SELECTED`, never `TIMEOUT_NO_RESPONSE`.
8. **Window Focus Loss Handling (M3)** — If the Pygame window loses OS focus (`pygame.WINDOWFOCUSLOST`), timers and audio drones freeze immediately, and `FOCUS_LOST` is logged. Upon focus restoration (`pygame.WINDOWFOCUSGAINED`), `FOCUS_GAINED` is logged, and timers resume. *(Implemented 2026-10-02: `_focus_paused` gates `_update()`; `AudioController.pause()/resume()`.)*
9. **Briefing popup gates input** — while the TAB/Q briefing modal is on screen the options are hidden, so number keys are ignored. No choice can be committed blind.
10. **Clock monitoring** — every frame `_monitor_clock()` compares the wall-clock delta with the frame delta. A frame stall (> one frame + `CLOCK_JUMP_WARNING_THRESHOLD_MS`) or a wall-clock step (> threshold) logs `CLOCK_ANOMALY` with `wall_delta_ms`, `frame_dt_ms` and `state`.
11. **Abort is logged** — ESC/QUIT before `STATE_DEBRIEF` writes `SESSION_END` with `{"aborted": true, "state": ...}`, so a truncated session is distinguishable from a completed one.

---

## 6. Hard System Constraints (from Locked Decisions)

| Constraint | Value | Source |
|---|---|---|
| Input method | Keyboard ONLY (keys 1,2,3,4, SPACE/Enter, TAB/Q hold for the briefing, Escape) | Decisions.md — protect PPG/GSR |
| Mouse cursor | Hidden via `pygame.mouse.set_visible(False)`; mouse events blocked at the queue (`pygame.event.set_blocked`) and input grabbed | Prevent accidental mouse use |
| Scoring | BANNED — no numerical scores anywhere in UI | Decisions.md |
| Domain order | Randomized per session via `random.shuffle()` with seed logged | Decisions.md — unconditional, all domains |
| Deception metric | `social_evaluation` domain ONLY | Decisions.md |
| MPU6050 threshold | Per-subject: μ_acc + 1.5 × σ_acc (from baseline) | Decisions.md |
| Audio during scenarios | 60–80 Hz tension drone ONLY, final 1/3 of timer, ≤30% volume | Decisions.md |
| Jitter | ≤3px displacement measured as vector magnitude, ≤2Hz on both axes, one jitter source per element | Decisions.md |
| Screen vibration | ≤2px displacement, ≤2Hz | Decisions.md (2026-10-02) |
| Compass rotation | ≤4 RPM (`COMPASS_SPIN_MAX_RPM`), decision and post-wait | Decisions.md (2026-10-02) |
| Strobing | BANNED (nothing >3 Hz) | Decisions.md — WCAG |
| Full-screen color inversion | BANNED | Decisions.md |
| Participant-facing text | No paradigm names, citations or construct labels (TSST, MIST, Asch, "conform", "dissent", "diegetic") | Decisions.md (2026-10-02) — demand characteristics |
| Baseline duration | 180s (3 min) standard; 10s with `--fast-baseline` | HRV statistical validity |
| Baseline stimulus | Static fixation cross, spontaneous breathing. No paced-breathing visual | Decisions.md (2026-10-02) — paced slow breathing inflates resting RMSSD/SDNN |
| Active epoch | PRIMING + DECISION + FEEDBACK ≥ 60s per scenario, enforced by the engine | Decisions.md (2026-10-02) |
| Intra-domain rest | 15s | Decisions.md |
| Inter-domain rest | 30s default; 60s with `--extended-rest` | Decisions.md ADR-B2 |
| Scenario durations | Priming 20s (all 14); decision 45s (40s for the MIST run); consequence 4s — defined once in `constants.py` | Decisions.md ADR-B3 |
| Paradigm wrapper | One ≥60s acute-stress epoch per scenario takes precedence over multi-trial paradigm fidelity | Decisions.md ADR-B4 |
| Colour | Six chromatic tokens only (§6.1); every other colour is a neutral grey | Decisions.md ADR-B5 — `DESIGN-ferrari.md` |
| Rosso Corsa | Stress triggers, danger states and timer expiry only; never a key prompt or the participant's own selection | Decisions.md ADR-B5 |
| File length | ≤500 lines per Python file | CODING_STANDARDS §8.2, ADR-B6 |
| FPS cap | 60 FPS (`clock.tick(60)`) | Pygame standard; sufficient for UI |
| Screen resolution | 1280×720 default; `--fullscreen` uses native | Balances readability and universality |

---

### 6.1 Colour Palette (ADR-B5)

Values come from `DESIGN-ferrari.md` and are defined once, in `constants.py`. The task brief that requested this alignment quoted different hex values (`#0A0A0A`, `#D40000`, `#FFF200`, `#8C8C8C`); they contradict the design file ("never pure black", Rosso Corsa `#da291c`), so the design file is the authority.

| Token | Hex | Use |
|---|---|---|
| `COLOR_BG` | `#181818` | Canvas (near-black, never pure black) |
| `COLOR_CARD_BG` / `COLOR_HAIRLINE` | `#303030` | Elevated surface / hairline divider |
| `COLOR_TEXT_PRIMARY` | `#ffffff` | Ink, and the mark of the participant's own selection |
| `COLOR_TEXT_SECONDARY` | `#969696` | Body text; Grigio border of a key badge |
| `COLOR_TEXT_MUTED` | `#666666` | Captions, avatar plates |
| `COLOR_PRIMARY_ROSSO` (= `COLOR_TIMER_RED`) | `#da291c` | Stress triggers, danger states, timer expiry |
| `COLOR_PRIMARY_ACTIVE` | `#b01e0a` | Dimmed alert strokes (the "off" phase of a blink) |
| `COLOR_SEMANTIC_WARNING` | `#f13a2c` | Small alert text on dark surfaces (better contrast than Rosso) |
| `COLOR_ACCENT_CYAN` | `#4c98b9` | Semantic info / telemetry |
| `COLOR_ACCENT_YELLOW` (= `COLOR_TIMER_AMBER`) | `#f6e500` | Caution; telemetry standby |
| `COLOR_TIMER_GREEN` | `#03904a` | Success / safe state |

Rules, each enforced by `tests/game/test_palette.py`:

1. **No chromatic colour literal** in `ui*.py` or `skins/*.py`. A literal RGB tuple must be a neutral grey (`r == g == b`); chromatic colour is referenced by token name.
2. **Derived shades keep the token's hue.** `_mix(token, neutral, amount)` blends toward the canvas or toward white; blending with a grey cannot change hue, so the result is still on-palette.
3. **Semantic gradients are the one sanctioned blend between tokens:** the timer bar and the composure bar (green → yellow → Rosso) and the reward-chest glow (cyan → yellow → Rosso).
4. **Key prompts are neutral:** `_draw_key_badge()` draws a canvas plate with white ink and a Grigio border. A chosen key inverts to a white plate with canvas ink. A key that is temporarily inert (BART cooldown) is drawn muted.
5. **Selection is never Rosso.** On plain multiple-choice skins the chosen card gets a white border; risk-coded skins keep the option's own semantic accent.
6. **A rendered frame contains no foreign hue.** Every chromatic pixel of all 14 skins and every non-decision screen must carry a token hue or lie on a sanctioned gradient.

---

## 7. Remediation Record (2026-10-02)

An independent audit of `src/game/` raised 7 blockers (B1–B7) and 14 cautions (C1–C14). §7.1 records the audit fixes, §7.2 the eight issues that the audit left open and that were resolved afterwards, §7.3 what is still open. Decision rationale lives in `Decisions.md` (ADR-A1…A10 for the audit, ADR-B1…B8 for the open issues).

### 7.1 Audit fixes

| Finding | Resolution | Where |
|---|---|---|
| B1 No exposure floor | Full-window committed-choice hold (Rule 3) and priming floor (Rule 1) | `engine_state.py` `_exit_decision()`, `_decision_floor_ms()`, `_priming_floor_ms()` |
| B2 Paced-breathing baseline | Static fixation cross, "breathe normally" | `ui_screens.py` `draw_baseline()` |
| B3 Inert composure display | No fabricated readings; `None` composure renders a STANDBY state; `main.py` warns on `StubBridge`; bridge name logged in `SYNC_PULSE` metadata | `ui_components.py` `draw_composure_bar()`, `engine.py` `_render()` |
| B4 Composure gating artifacts | ≥3 consecutive supra-threshold samples and a 5s cooldown before a drop; composure resets per scenario | `engine_timer.py` `_update_composure()` |
| B5 Construct leaks | Paradigm line removed from priming card and popup; leak strings replaced | `ui_screens.py`, `skins/` |
| B6 Sensory limits | Vector-magnitude clamp, both axes ≤2Hz, vibration ≤2px, single jitter source in `portal_log`, compass ≤4 RPM | `ui_effects.py`, `skins/`, `constants.py` |
| B7 Missing paradigm mechanics | `document_workspace` Key 2 enters the 15s `POST_WAIT`; MIST runs on the clock with randomised answer positions and a peer figure capped at 100% | `engine_input.py`, `engine_state.py`, `scenarios.py` |
| C1 Selection wiped | Selection persists through the hold; `set_last_choice()` feeds the fork-map post-wait | `engine_state.py`, `ui_core.py` |
| C2 Wrong suspension badge | Badge matches "account suspended" / "system failure" only | `ui_screens.py` `draw_feedback()` |
| C3 Missing lifecycle events | `CLOCK_ANOMALY`, `FOCUS_LOST`, `FOCUS_GAINED`, aborted `SESSION_END` | `engine_timer.py`, `engine_input.py`, `engine_state.py` |
| C4 Reaction time | Intervals from `time.perf_counter_ns()`; per-item `item_rt_ms` in metadata. Still quantised to the 60 FPS event poll (≤16.7ms) | `engine_input.py` |
| C5 Popup input | Rule 9 | `engine_input.py` |
| C6 Session metadata | Edited subject ID rewrites `domain_order.json`; `--subject` validated; audio/bridge state logged | `engine_input.py`, `main.py` |
| C7 Text overflow | `max_width` guard, same-family downscale, ellipsis on truncation | `ui_core.py` |
| C8 Fonts | Exact font files (Segoe UI Regular / Semibold, Consolas) instead of `SysFont` name matching | `ui_core.py` `_init_fonts()` |
| C9 Ferrari alignment | 0px corners everywhere, neutral window controls, contrast-aware badge ink | `skins/` (completed by §7.2 issue 5) |
| C10 Score language | "Final Score" removed. A second pass found four more strings using the word ("average score improvement", "unhedged score drop", "Composure score: evaluated", "Guaranteed score gain"); they were reworded and a test now scans every participant-facing string | `skins/`, `scenarios.py`, `test_scenarios.py` |
| C13 Zero warnings | `mypy --strict` and `ruff check` clean (extended repo-wide by §7.2 issue 7) | — |

### 7.2 Open issues resolved

| # | Issue | Resolution | ADR |
|---|---|---|---|
| 1 | Real sensor bridge | `SerialBridge` (live ESP32, records `sensor_stream.csv`), `ReplayBridge` (recording or live follow), auto-detection with graceful `StubBridge` fallback; `--bridge {auto,serial,stub,replay}` (§4.2) | B1 |
| 2 | Inter-domain rest 30s vs 60s | 30s default in `constants.py` and `SessionConfig.inter_domain_rest_s`; `--extended-rest` selects 60s; the duration used is logged | B2 |
| 3 | Spec-versus-code durations, MIST calibration | Priming locked at 20s and `social_evaluation_b` at 45s, durations bound to constants; MIST adapts in-run instead of a pretest (Rule 3) | B3 |
| 4 | Paradigm design | The ≥60s acute-stress wrapper takes precedence over multi-trial paradigms. BART is a single balloon with a linear hazard (2 % → 41 %, certain at pump 15, about 6 expected safe pumps), paced pumps, and per-pump latency + pressure-curve logging. `risk_reward_a` is labelled as what it is: a one-shot described-risk choice, not the Iowa Gambling Task | B4 |
| 5 | Palette | §6.1: six chromatic tokens, neutral greys, neutral key badges, selection never Rosso; verified per pixel | B5 |
| 6 | File length | `ui.py` (3,280 lines) → `ui_core`, `ui_components`, `ui_screens`, `ui_post_wait`, `ui_domains` + `skins/` (14 modules); `engine.py` (600) → `engine`, `engine_state`, `engine_input`, `engine_timer`; the bridge is three modules. Every file ≤500 lines; the moves were verified pixel-identical on 248 frames | B6 |
| 7 | Repo-wide lint and typing | `ruff check .` and `mypy src/ tests/ --strict` are clean. Pipeline edits are annotation- and lint-only, proven on 106 behavioural checkpoints (104 identical; the 2 that differ are the fixed `batch_comparison` call) | B7 |
| 8 | Agent context files | `CLAUDE.md` rewritten and `GEMINI.md` created with the same content | B8 |

### 7.3 Still open

| Item | State |
|---|---|
| Hardware-in-the-loop run | `SerialBridge` is verified against simulated ports and recorded rows only. It has not been run against a physical ESP32, and fullscreen and audio output have not been exercised on the study machine. |
| Composure false-trigger rate | A headless full-protocol session driven through `main.py` with a replayed recording produced the expected `DECEPTION_TRIGGER` events during simulated tremor (one per 5 s cooldown). It also produced about one brief drop per 45 s window on *stationary* resting motion: the μ + 1.5σ threshold sits near the 93rd percentile of resting variance, and consecutive 4 Hz polls of a 1 s window overlap by 75 %, so three in a row above threshold is not rare. The parameters are a locked decision; measure the rate on real resting recordings before reading `DECEPTION_TRIGGER` counts as tremor events. |
| Function length (CODING_STANDARDS §8.1) | 19 functions exceed 60 lines; 15 are the `_draw_skin_*` methods (134–304 lines). Decomposing them needs per-skin layout objects and is a separate piece of work. |
| Resolution scaling (audit C12) | Layout assumes 1280×720. Fullscreen uses `pygame.SCALED`, so it is scaled as a whole rather than re-laid-out. |
| Reaction-time resolution (audit C4) | Latencies are quantised to the 60 FPS event poll (≤16.7 ms). |
| `batch_comparison.py` feature list | `FEATURE_COLS` lists `scl_slope`, which `features.py` does not produce, so the script raises `KeyError` on current feature files. Left for the pipeline owner: drop the column or add the feature. |
| `validation/run_m2_validation_v2.py` | 542 lines (archived M2 evidence script, outside `src/`). |
| Option colour coding | Risk-coded skins still mark options green / yellow / red. That is on-palette, but it is a valence cue; whether it biases choice is an experimental-design question, not a palette one. |
