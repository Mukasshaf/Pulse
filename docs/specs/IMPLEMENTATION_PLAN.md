# IMPLEMENTATION_PLAN.md — Pulse Gamification Engine

> **Scope:** Dependency-ordered task graph. Each task is atomic (produces exactly one file), has explicit prerequisites, and a mandatory verification checkpoint. No task may begin until all its prerequisites' checkpoints have passed.
> **Integration Note:** Reflects the unified architecture (Game Engine and `serial_reader.py` run as completely decoupled processes) and the hardware pivot to the Analog Pulse Sensor. 

---

## Execution Order Overview

```
Phase 1: Foundation (no pygame dependency — pure Python)
  Task 1  → constants.py
  Task 2  → scenarios.py         (depends: Task 1)
  Task 3  → event_logger.py      (depends: Task 1)
  Task 4  → audio.py             (depends: Task 1)
  Task 5  → bridge_interface.py  (depends: Task 1)

Phase 2: Core Engine (pygame dependency required)
  Task 6  → ui.py                (depends: Tasks 1, 2)
  Task 7  → ui_effects.py        (depends: Task 1)
  Task 8  → scenario_logic.py    (depends: Tasks 1, 2)
  Task 9  → engine.py            (depends: Tasks 1–8)

Phase 3: Entry Point + Assets
  Task 10 → main.py              (depends: Task 9)
  Task 11 → tension_drone.wav    (depends: none — can parallelize)
  Task 12 → pyproject.toml       (depends: none — can parallelize)

Phase 4: Integration Verification
  Task 13 → Full flow smoke test (depends: all above)

Phase 5: Post-audit rounds (2026-10-02) — see the end of this document
  Task 14 → Audit remediation: exposure floors, baseline, composure gating, sensory limits
  Task 15 → Sensor bridge: sensor_stream.py, sensor_replay.py, sensor_bridge.py, --bridge
  Task 16 → Timing: 30s inter-domain rest (+ --extended-rest), durations bound to constants
  Task 17 → Paradigms: MIST in-run adaptation, single-balloon BART curve + pacing + logging
  Task 18 → Palette: Ferrari tokens only, neutral key badges, per-pixel audit
  Task 19 → Modularity: ui.py → ui_* + skins/, engine.py → engine_*; every file ≤500 lines
  Task 20 → Repo-wide lint and strict typing (pipeline, hardware, validation, tests)
  Task 21 → Agent context files and documentation sync
```

> **Reading this plan today.** Tasks 1–13 describe how the engine was first built, one file per task. Several of those files have since been split (Task 19), so where a task names `ui.py` or `engine.py` as its output, read "the module family behind that facade". The verification snippets below have been kept runnable against the current code.

---

## Phase 1: Foundation

### Task 1 — `src/game/constants.py`

**Dependencies:** None (leaf node)
**Output:** `src/game/constants.py`
**Specification source:** DATA_MODELS_AND_CONTRACTS.md §1 (Enumerations), §7 (Constants), §8 (Valid Transitions)

**Content:**
- All `StrEnum` definitions: `EngineState`, `EventType`, `ScenarioType`, `DomainID`
- All constant values (display, timing, audio, UI effects, colors, MIST, BART, reward, validation)
- `VALID_TRANSITIONS` adjacency dict
- Custom exception classes: `PulseEngineError`, `InvalidStateTransition`, `DomainNotFoundError`, `ScenarioConfigError`, `AudioLoadError`, `LoggerIOError`
- `SUBJECT_ID_PATTERN` regex

**Verification checkpoint:**
```bash
python -c "from src.game.constants import EngineState, EventType, ScenarioType, DomainID, VALID_TRANSITIONS, SCREEN_WIDTH; print('OK')"
```
Must print `OK` with exit code 0.

---

### Task 2 — `src/game/scenarios.py`

**Dependencies:** Task 1 (constants.py)
**Output:** `src/game/scenarios.py`
**Specification source:** DATA_MODELS_AND_CONTRACTS.md §2 (Dataclasses), Domain Implementation Strategy (all 14 scenarios)

**Content:**
- Dataclass definitions: `Option`, `MathProblem`, `BARTConfig`, `RewardAccumulatorConfig`, `Scenario`, `Domain`
- `build_domain_registry()` → returns `list[Domain]` with all 7 domains, 14 scenarios fully populated
- `get_domain_by_id()` lookup function
- `generate_math_problems()` for MIST scenario
- Every priming_text, option text, and consequence_text must be copied **verbatim** from Domain Implementation Strategy

**Verification checkpoint:**
```bash
python -c "
from src.game.scenarios import build_domain_registry, get_domain_by_id
from src.game.constants import DomainID
r = build_domain_registry()
assert len(r) == 7, f'Expected 7 domains, got {len(r)}'
for d in r:
    assert len(d.scenarios) == 2, f'{d.id} has {len(d.scenarios)} scenarios'
d = get_domain_by_id(r, DomainID.SOCIAL_EVALUATION)
assert d.scenarios[0].has_deception_metric is True
assert d.scenarios[1].has_deception_metric is True
fu = get_domain_by_id(r, DomainID.FUTURE_UNCERTAINTY)
assert fu.scenarios[0].has_post_wait is True
assert fu.scenarios[1].has_post_wait is True
print('OK')
"
```

---

### Task 3 — `src/game/event_logger.py`

**Dependencies:** Task 1 (constants.py)
**Output:** `src/game/event_logger.py`
**Specification source:** DATA_MODELS_AND_CONTRACTS.md §3 (CSV Schema), §5 (`EventLogger` signatures)

**Content:**
- `GameEvent` dataclass (defined here in `event_logger.py` — not in `constants.py`)
- `EventLogger` class with `__init__`, `log_event`, `save_domain_order`, `close`
- CSV writer configuration: `QUOTE_MINIMAL`, `\n` line terminator, flush after every row
- Thread-safe via `threading.Lock` on writes

**Verification checkpoint:**
```bash
python -c "
from pathlib import Path
from src.game.event_logger import EventLogger, GameEvent
from src.game.constants import EventType
import time, json, tempfile, os

with tempfile.TemporaryDirectory() as d:
    logger = EventLogger(Path(d), 'S01')
    evt = GameEvent(
        unix_ts_ms=int(time.time_ns() // 1_000_000),
        event_type=EventType.BASELINE_START,
        domain="", scenario_id="", choice_data="{}",
        key_pressed=None, option_index=None,
        response_time_ms=None, metadata={}
    )
    logger.log_event(evt)
    logger.close()
    csv_path = Path(d) / 'events.csv'
    assert csv_path.exists()
    lines = csv_path.read_text().strip().split('\n')
    assert len(lines) == 2  # header + 1 event
    assert 'BASELINE_START' in lines[1]
print('OK')
"
```

---

### Task 4 — `src/game/audio.py`

**Dependencies:** Task 1 (constants.py)
**Output:** `src/game/audio.py`
**Specification source:** DATA_MODELS_AND_CONTRACTS.md §5 (`AudioController` signatures)

**Content:**
- `AudioController` class with `__init__`, `start_drone`, `stop_drone`, `is_playing`
- Loads WAV from provided `Path`
- Raises `AudioLoadError` if file missing
- Idempotent start/stop

**Verification checkpoint:**
```bash
python -c "from src.game.audio import AudioController; print('OK')"
```
(Full audio test requires pygame.mixer.init() and a WAV file — deferred to Task 13.)

---

### Task 5 — `src/game/bridge_interface.py`

**Dependencies:** Task 1 (constants.py)
**Output:** `src/game/bridge_interface.py`
**Specification source:** DATA_MODELS_AND_CONTRACTS.md §2 (`SensorSample`), §5 (`BridgeInterface`, `StubBridge`)

**Content:**
- `SensorSample` dataclass
- `BridgeInterface` Protocol with `get_latest_sample()` and `get_mpu_variance()` (3-axis magnitude variance)
- `StubBridge` class returning `None` for all methods (default fallback mode)
- The real bridge is not in this file: `SerialBridge` and `ReplayBridge` were added in Task 15 (`sensor_bridge.py`, `sensor_replay.py`, `sensor_stream.py`). The protocol also has `close()`

**Verification checkpoint:**
```bash
python -c "
from src.game.bridge_interface import StubBridge, BridgeInterface
b = StubBridge()
assert isinstance(b, BridgeInterface)
assert b.get_latest_sample() is None
assert b.get_mpu_variance() is None
b.close()
print('OK')
"
```

---

## Phase 2: Core Engine

### Task 6 — `src/game/ui.py`

**Dependencies:** Tasks 1, 2
**Output:** `src/game/ui.py`
**Specification source:** ARCHITECTURE_SPEC.md §3 (`UIRenderer` component tree), DATA_MODELS_AND_CONTRACTS.md §5 (`UIRenderer` signatures)

**Content:**
- `UIRenderer` class with all `draw_*` methods
- Font loader with fallback chain
- Color palette from constants
- Layout calculation (card rects, button rects, timer bar rect)
- `UIEffectState` dataclass to pass jitter/vibration state into draw methods
- Specialized draw methods: `draw_peer_average_bar`, `draw_team_chat`, `draw_evaluator_panel`, `draw_composure_bar`, `draw_instability_gauge`
- *Since Task 19:* `ui.py` is a 12-line facade. The class is assembled from `ui_core.py`, `ui_components.py`, `ui_screens.py`, `ui_post_wait.py`, `ui_domains.py` and the 14 modules in `skins/`. The import below is unchanged

**Verification checkpoint:**
```bash
python -c "
import pygame
pygame.init()
screen = pygame.display.set_mode((1280, 720))
from src.game.ui import UIRenderer
r = UIRenderer(screen)
print('OK')
pygame.quit()
"
```

---

### Task 7 — `src/game/ui_effects.py`

**Dependencies:** Task 1
**Output:** `src/game/ui_effects.py`
**Specification source:** ARCHITECTURE_SPEC.md §3 (`ui_effects.py` component list), DATA_MODELS_AND_CONTRACTS.md §7 (effect constants)

**Content:**
- `TextJitter` class — computes x,y offset based on elapsed time, capped at JITTER_MAX_PX/HZ
- `TimerBarColorTransition` — returns RGB tuple based on fraction remaining
- `ScreenVibration` — computes x,y offset for reward accumulator
- `ButtonFlash` — manages 200ms red flash state
- `UIEffectState` — aggregate state holder (jitter_offset, is_flashing, vibration_offset)

**Verification checkpoint:**
```bash
python -c "
from src.game.ui_effects import TextJitter, TimerBarColorTransition
j = TextJitter()
offset = j.get_offset(elapsed_ms=500)
assert abs(offset[0]) <= 3 and abs(offset[1]) <= 3
c = TimerBarColorTransition()
from src.game.constants import COLOR_TIMER_GREEN, COLOR_TIMER_RED
assert c.get_color(1.0) == COLOR_TIMER_GREEN   # green at 100%
assert c.get_color(0.05) == COLOR_TIMER_RED    # Rosso Corsa at 5%
print('OK')
"
```

---

### Task 8 — `src/game/scenario_logic.py`

**Dependencies:** Tasks 1, 2
**Output:** `src/game/scenario_logic.py`
**Specification source:** DATA_MODELS_AND_CONTRACTS.md §5 (Runner signatures)

**Content:**
- `MISTRunner` — rapid-fire arithmetic with fake peer progress; since Task 17 an adaptive per-item countdown (`update()`, `get_item_time_fraction()`)
- `BARTRunner` — escalating pump with probabilistic burst; since Task 17 a linear hazard curve, pump pacing (`can_pump()`, `update()`), and an honest counterfactual
- `RewardAccumulator` — growing value with random collapse
- `DelayWaitRunner` — simple timed wait screen

**Verification checkpoint:**
```bash
python -c "
from src.game.scenario_logic import MISTRunner, BARTRunner, RewardAccumulator, DelayWaitRunner
from src.game.scenarios import generate_math_problems
from src.game.constants import BART_INITIAL_VALUE, BART_INCREMENT, BART_BURST_PROB_BASE, BART_BURST_PROB_INCREMENT, BART_MAX_PUMPS

# MIST
problems = generate_math_problems(4)
m = MISTRunner(problems, 40)
assert m.get_accuracy_pct() == 0
assert m.get_peer_average_pct() == 15

# BART
from src.game.scenarios import BARTConfig
cfg = BARTConfig(BART_INITIAL_VALUE, BART_INCREMENT, BART_BURST_PROB_BASE, BART_BURST_PROB_INCREMENT, BART_MAX_PUMPS)
b = BARTRunner(cfg)
val, burst = b.pump()
assert val >= BART_INITIAL_VALUE

# Reward
from src.game.scenarios import RewardAccumulatorConfig
rcfg = RewardAccumulatorConfig(10, 1.15, (20, 40), 9999)
r = RewardAccumulator(rcfg)
assert r.get_current_value() == 10

# Delay
d = DelayWaitRunner(12, 'Processing...')
assert d.get_elapsed_fraction() == 0.0

print('OK')
"
```

---

### Task 9 — `src/game/engine.py`

**Dependencies:** Tasks 1–8 (all foundation + UI + logic)
**Output:** `src/game/engine.py`
**Specification source:** ARCHITECTURE_SPEC.md §3 (`GameEngine`), §5 (State Machine), DATA_MODELS_AND_CONTRACTS.md §2 (`SessionConfig`), §5 (`GameEngine` signatures)

**Content:**
- `GameEngine` class implementing the full state machine
- `run()` — main Pygame loop with `clock.tick(60)`, event dispatch, `_update()`, `_render()`
- `_transition_to()` — validated against `VALID_TRANSITIONS`, logs transition event
- `_handle_input()` — routes KEYDOWN to current state handler:
  - In `STATE_DECISION`, a keypress locks in `_selected_option` and logs `OPTION_SELECTED` with `response_time_ms` immediately, but does NOT transition early (C1).
  - Processes all pending events in the queue before `_update()` decrements timers, ensuring same-frame keypresses win over timeouts (M2).
  - Handles `pygame.WINDOWFOCUSLOST` (logs `FOCUS_LOST`, pauses timers/audio) and `pygame.WINDOWFOCUSGAINED` (logs `FOCUS_GAINED`, resumes) (M3).
- `_update()` — decrements timers only when window has focus; triggers state transition from `STATE_DECISION` to `FEEDBACK` or `POST_WAIT` only when decision timer reaches 0.
- `_render()` — delegates to `UIRenderer` based on `_current_state`; displays locked-in selection highlight during remainder of decision timer.
- Domain randomization with seed logging
- Scenario progression tracking (current domain index, scenario A/B flag)
- Deception metric integration (social_evaluation only, reads `bridge.get_mpu_variance()` with 3-sample consecutive elevation + 5s cooldown gating)
- *Since Task 19:* `engine.py` holds `run()` and `_render()`; state and transitions are in `engine_state.py`, input handlers in `engine_input.py`, per-frame updates in `engine_timer.py`

**Verification checkpoint:**
```bash
python -c "
import pygame
pygame.init()
screen = pygame.display.set_mode((1280, 720))
from src.game.engine import GameEngine
from src.game.constants import EngineState
from src.game.event_logger import GameEvent
# Verify construction succeeds
from src.game.engine import SessionConfig
import time

cfg = SessionConfig(subject_id='S99', fast_baseline=True, fullscreen=False, window_size=(1280, 720),
                    domain_filter=None, session_start_unix_ts_ms=int(time.time_ns()//1_000_000), random_seed=42)
engine = GameEngine(cfg, screen)
assert engine._current_state == EngineState.INIT
engine._shutdown()
print('OK')
pygame.quit()
"
```

---

## Phase 3: Entry Point + Assets

### Task 10 — `src/game/main.py`

**Dependencies:** Task 9
**Output:** `src/game/main.py`
**Specification source:** DATA_MODELS_AND_CONTRACTS.md §5 (`main.py` signatures)

**Content:**
- `parse_cli()` → `(SessionConfig, BridgeOptions)` via `argparse`; `parse_args()` is kept as `parse_cli()[0]`
- `main()` → create the sensor bridge, init pygame, create screen, create `GameEngine`, call `run()`, close the bridge
- Top-level `try/except` for `PulseEngineError` and `KeyboardInterrupt`
- `if __name__ == "__main__": main()` guard

**Verification checkpoint:**
```bash
python -m src.game.main --subject S01 --fast-baseline --help
```
Must print help text with exit code 0. (Actual game launch tested in Task 13.)

---

### Task 11 — `assets/audio/tension_drone.wav`

**Dependencies:** None (parallelizable)
**Output:** `assets/audio/tension_drone.wav`

**Content:**
- Generate a 30-second WAV file containing a 70 Hz sine wave (center of 60–80 Hz spec).
- 44100 Hz sample rate, 16-bit, mono.
- Can be generated with a Python script using `numpy` + `wave` stdlib:

```python
import numpy as np
import wave

sr = 44100
duration = 30
freq = 70
t = np.linspace(0, duration, sr * duration, endpoint=False)
samples = (np.sin(2 * np.pi * freq * t) * 16000).astype(np.int16)

with wave.open("assets/audio/tension_drone.wav", "w") as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(sr)
    f.writeframes(samples.tobytes())
```

**Verification checkpoint:**
```bash
python -c "
import wave
with wave.open('assets/audio/tension_drone.wav', 'r') as f:
    assert f.getnchannels() == 1
    assert f.getsampwidth() == 2
    assert f.getframerate() == 44100
    assert f.getnframes() >= 44100 * 29  # At least 29s
print('OK')
"
```

---

### Task 12 — `pyproject.toml` update

**Dependencies:** None (parallelizable)
**Output:** `pyproject.toml` (modify existing)

**Content:**
- Add `pygame>=2.5.0` and `numpy>=1.26.0` to `[project.dependencies]`
- Run `uv lock` to regenerate `uv.lock`
- Run `uv sync` to install

**Verification checkpoint:**
```bash
uv run python -c "import pygame; import numpy; print('OK')"
```

---

## Phase 4: Integration Verification

### Task 13 — Full Flow Smoke Test

**Dependencies:** All Tasks 1–12
**Output:** No new files — validation only

**Procedure:**
1. Launch: `uv run python -m src.game.main --subject S99 --fast-baseline`. The console first prints the bridge status, e.g. `Sensor bridge [stub]: no ESP32-like serial port found`, and a warning that the Domain 7 composure display will stay on STANDBY. Add `--bridge stub` to skip the port scan on a machine without the hardware.
2. Verify: ID input screen appears → type `S99` → press Enter
3. Verify: Baseline screen appears with a static fixation cross (no breathing animation) and 10s countdown
4. Verify: First domain's Scenario A priming text appears; SPACE is refused until the priming floor passes
5. Verify: Decision screen with options and timer bar
6. Press a number key → verify the choice locks in and stays highlighted until the timer expires, then the consequence screen appears (add `--no-exposure-floor` for a fast developer walkthrough)
7. Verify: 15s intra-domain rest screen
8. Verify: Scenario B priming → decision → consequence
9. Verify: 30s inter-domain rest screen (60s when launched with `--extended-rest`)
10. Continue through all 7 domains (or press Escape to exit early)
11. Verify: `outputs/game_logs/S99_{timestamp}/events.csv` exists and contains:
    - Header row
    - `SYNC_PULSE` event
    - `BASELINE_START` and `BASELINE_END` events
    - At least one `DOMAIN_START`, `SCENARIO_PRIMING`, `DECISION_PRESENTED`, `OPTION_SELECTED`, `SCENARIO_END`
    - All `unix_ts_ms` values are monotonically increasing (Critical for offline post-session dataset join with `serial_reader.py`)
12. Verify: `outputs/game_logs/S99_{timestamp}/domain_order.json` exists with 7 domain IDs

**Pass criteria:**
- No Python exceptions during the full flow
- CSV file is well-formed and parseable
- Mouse cursor is hidden throughout
- No numerical scores displayed anywhere
- Tension drone plays during final 1/3 of at least one timer (verify audibly)
- No colour on screen other than neutral greys, Rosso Corsa, yellow, cyan and green
- Key prompts are dark plates with a grey border; the chosen one turns white

---

## Phase 5: Post-audit rounds (2026-10-02)

Each task below was verified with the same three commands, all clean at the end of the round:

```powershell
uv run pytest -v                      # 107 passed
uv run mypy src/ tests/ --strict      # no issues in 76 source files
uv run ruff check .                   # all checks passed
```

### Task 14 — Audit remediation
Exposure floors (commit-and-hold, priming floor), static baseline, honest composure display and gating, sensory limits as vector bounds, lifecycle events, text-fit guards. Record: ARCHITECTURE_SPEC §7.1, ADR-A1…A10, `tests/game/test_audit_fixes.py`.

### Task 15 — Sensor bridge (ADR-B1)
**Output:** `src/game/sensor_stream.py`, `sensor_replay.py`, `sensor_bridge.py`; `BridgeInterface.close()`; `--bridge {auto,serial,stub,replay}`, `--bridge-port`, `--bridge-source`, `--bridge-follow`.
**Checkpoint:** `tests/game/test_bridge_interface.py` (12 tests, simulated ports only).
**Not done:** a run against the physical ESP32.

### Task 16 — Timing (ADR-B2, ADR-B3)
**Output:** `INTER_DOMAIN_REST_S = 30`, `INTER_DOMAIN_REST_EXTENDED_S = 60`, `SessionConfig.inter_domain_rest_s`, `--extended-rest`; `DEFAULT_PRIMING_DURATION_S = 20`, `DEFAULT_DECISION_DURATION_S = 45`, `MIST_DECISION_DURATION_S = 40` used by every scenario in the registry.
**Checkpoint:** `test_inter_domain_rest_default_and_extended`, `test_scenario_durations_are_locked`.

### Task 17 — Paradigms (ADR-B3, ADR-B4)
**Output:** MIST per-item countdown that adapts in-run and logs time-outs; BART hazard `0.02 + 0.03·(k−1)` with a certain burst at pump 15, a 1.5s pump cooldown, per-pump hazard / latency logging, and a counterfactual replayed from the session RNG; item bar in the exam skin; "PUBLISHING POST..." state in the analytics skin; `risk_reward_a` relabelled as a one-shot risky choice.
**Checkpoint:** `test_scenario_logic.py` (5 new tests), `test_engine_paradigms.py`.

### Task 18 — Palette (ADR-B5)
**Output:** `COLOR_SEMANTIC_WARNING`, `_mix()`, `_draw_key_badge()`; 248 tinted literals neutralised at equal luminance, every saturated off-token colour mapped to a token; neutral avatars; selection in white; `COLOR_ACCENT_INDIGO` removed; four participant-facing strings reworded to drop the word "score".
**Checkpoint:** `tests/game/test_palette.py` (6 tests, including a per-pixel hue audit of every screen), `test_participant_facing_text_has_no_score_language`.

### Task 19 — Modularity (ADR-B6)
**Output:** `ui.py` → `ui_core`, `ui_components`, `ui_screens`, `ui_post_wait`, `ui_domains` + `skins/` (14 modules); `engine.py` → `engine`, `engine_state`, `engine_input`, `engine_timer`. Largest file in `src/game/` is 428 lines.
**Checkpoint:** 248 rendered frames hashed before and after the UI move: identical.
**Not done:** the 60-line function rule (15 skin methods are 134–304 lines).

### Task 20 — Repo-wide lint and typing (ADR-B7)
**Output:** `ruff check .` and `mypy src/ tests/ --strict` clean. 185 ruff findings and 65 mypy errors cleared in `src/pipeline/`, `src/hardware/`, `validation/` and the shared tests.
**Checkpoint:** 106 behavioural checkpoints of the pipeline on synthetic data, before and after: 104 identical, 2 changed by design (`batch_comparison.pct_change` was called with a missing argument). A structural comparison against git HEAD shows only the intentionally edited functions differ.
**Left for the pipeline owner:** `batch_comparison.FEATURE_COLS` lists `scl_slope`, which `features.py` does not produce.

### Task 21 — Agent files and documentation (ADR-B8)
**Output:** `CLAUDE.md` rewritten, `GEMINI.md` created (identical content); all specs in `docs/` updated and mirrored to the Obsidian vault; ADR-B1…B8 in `Decisions.md`.
