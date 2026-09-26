# TEST_CRITERIA_AND_EDGE_CASES.md — Pulse Gamification Engine

> **Scope:** Governs verification and resilience logic. Every module has unit test expectations, mock dependency specifications, critical edge cases, and strict pass/fail assertions. Code generators must ensure all listed edge cases are handled in implementation.

---

## 1. Testing Infrastructure

### Framework
- **Test runner:** `pytest` (add to `[project.optional-dependencies.dev]` in pyproject.toml)
- **Assertions:** Native `assert` statements (pytest rewrites them for readable failures)
- **Mocking:** `unittest.mock.patch`, `unittest.mock.MagicMock` — no additional mocking library
- **Pygame tests:** Use `pygame.init()` / `pygame.quit()` in fixtures. All rendering tests use a headless `pygame.Surface(1280, 720)` without `set_mode()` when possible.

### Test File Location
```
tests/
├── __init__.py
├── test_constants.py
├── test_scenarios.py
├── test_event_logger.py
├── test_audio.py
├── test_bridge_interface.py
├── test_ui_effects.py
├── test_scenario_logic.py
├── test_engine.py
└── conftest.py              # Shared fixtures
```

### Shared Fixtures (`conftest.py`)

```python
import pytest
import pygame
from pathlib import Path
from src.game.constants import DomainID
from src.game.scenarios import build_domain_registry

@pytest.fixture(scope="session", autouse=True)
def init_pygame():
    pygame.init()
    yield
    pygame.quit()

@pytest.fixture
def screen():
    return pygame.Surface((1280, 720))

@pytest.fixture
def domain_registry():
    return build_domain_registry()

@pytest.fixture
def tmp_output(tmp_path):
    return tmp_path / "test_output"

@pytest.fixture
def sample_event():
    from src.game.event_logger import GameEvent
    from src.game.constants import EventType
    import time
    return GameEvent(
        unix_ts_ms=int(time.time_ns() // 1_000_000),
        event_type=EventType.BASELINE_START,
        domain="", scenario_id="", choice_data="{}",
        key_pressed=None, option_index=None,
        response_time_ms=None, metadata={}
    )
```

---

## 2. Unit Test Expectations Per Module

### 2.1 `test_constants.py`

| Test | Assertion |
|---|---|
| All enums are StrEnum | `assert issubclass(EngineState, StrEnum)` for each |
| 7 DomainID members | `assert len(DomainID) == 7` |
| 10 EngineState members | `assert len(EngineState) == 10` |
| VALID_TRANSITIONS covers all states | `assert set(VALID_TRANSITIONS.keys()) == set(EngineState)` |
| No state transitions to itself | For each `(k, v)` in VALID_TRANSITIONS: `assert k not in v` |
| DEBRIEF is terminal | `assert VALID_TRANSITIONS[EngineState.DEBRIEF] == set()` |
| Constants are correct type | `assert isinstance(SCREEN_WIDTH, int)` etc. |
| JITTER_MAX_PX ≤ 3 | `assert JITTER_MAX_PX <= 3` |
| DRONE_VOLUME ≤ 0.30 | `assert DRONE_VOLUME <= 0.30` |
| Exception hierarchy | `assert issubclass(InvalidStateTransition, PulseEngineError)` |

**Mock dependencies:** None (pure Python).

---

### 2.2 `test_scenarios.py`

| Test | Assertion |
|---|---|
| Registry has 7 domains | `assert len(registry) == 7` |
| Each domain has exactly 2 scenarios | `all(len(d.scenarios) == 2 for d in registry)` |
| All 14 scenario IDs are unique | `len(set(s.id for d in r for s in d.scenarios)) == 14` |
| `social_evaluation` scenarios have `has_deception_metric=True` | Verify for both |
| `future_uncertainty` scenarios have `has_post_wait=True` | Verify for both |
| Non-social_evaluation scenarios have `has_deception_metric=False` | Check all 10 others |
| Non-future_uncertainty scenarios have `has_post_wait=False` | Check all 10 others |
| `academic_pressure_a` has `scenario_type=MIST_ARITHMETIC` | Direct assertion |
| `academic_pressure_a` has exactly 4 MathProblems | `len(s.math_problems) == 4` |
| `risk_reward_b` has `scenario_type=BART_ESCALATION` | Direct assertion |
| `impulsivity_gratification_a` has `scenario_type=REWARD_ACCUMULATOR` | Direct assertion |
| `get_domain_by_id` returns correct domain | Verify all 7 |
| `get_domain_by_id` with invalid ID raises `DomainNotFoundError` | `pytest.raises` |
| `generate_math_problems` returns correct count | `len(generate_math_problems(4)) == 4` |
| Generated problems have exactly 4 options each | `all(len(p.options) == 4 for p in problems)` |
| Generated problems have valid `correct_index` | `all(0 <= p.correct_index < 4 for p in problems)` |
| All priming texts are non-empty strings | `all(len(s.priming_text) > 0 ...)` |
| All consequence texts are non-empty strings | `all(len(o.consequence_text) > 0 ...)` |
| Domain dataclass is frozen | `pytest.raises(FrozenInstanceError, ...)` |

**Mock dependencies:** None (pure Python).

---

### 2.3 `test_event_logger.py`

| Test | Assertion |
|---|---|
| CSV file created on init | `assert (tmp_output / 'events.csv').exists()` |
| Header row is correct | Verify column names match CSV schema |
| Single event writes one data row | Line count == 2 (header + data) |
| 100 events write 101 rows | Line count == 101 |
| `unix_ts_ms` is an integer | Parse CSV, verify column is int-castable |
| Empty metadata serializes as `{}` | `assert row['metadata'] == '{}'` |
| Non-empty metadata is valid JSON | `json.loads(row['metadata'])` succeeds |
| `None` fields write as empty string | `assert row['key_pressed'] == ''` |
| `domain_order.json` is valid JSON | `json.loads(path.read_text())` succeeds |
| `domain_order.json` has 7 domains | `len(data['domain_order']) == 7` |
| `close()` is idempotent | Call twice — no exception |
| Thread safety | Write from 10 threads simultaneously — no corrupted rows |

**Mock dependencies:** `tmp_path` fixture for filesystem isolation.

---

### 2.4 `test_audio.py`

| Test | Assertion |
|---|---|
| `AudioLoadError` raised for missing file | `pytest.raises(AudioLoadError)` |
| `start_drone` is idempotent | Call twice — no exception, still playing |
| `stop_drone` is idempotent | Call twice (or when not playing) — no exception |
| `is_playing()` returns correct state | False → start → True → stop → False |

**Mock dependencies:** Mock `pygame.mixer.Sound` to avoid requiring actual WAV file in unit tests.

---

### 2.5 `test_bridge_interface.py`

| Test | Assertion |
|---|---|
| `StubBridge` satisfies `BridgeInterface` protocol | `isinstance(StubBridge(), BridgeInterface)` |
| `get_latest_sample()` returns None | Direct assertion |
| `get_mpu_variance()` returns None | Direct assertion |
| `SensorSample` fields correct types | `isinstance(sample.unix_ts_ms, int)` etc. |

**Mock dependencies:** None.

---

### 2.6 `test_ui_effects.py`

| Test | Assertion |
|---|---|
| Jitter offset never exceeds ±JITTER_MAX_PX | Test 1000 frames, verify `abs(offset) <= 3` |
| Jitter frequency ≤ JITTER_MAX_HZ | Verify direction changes ≤ 2× per second |
| Timer bar green at 100% | `get_color(1.0) == COLOR_TIMER_GREEN` |
| Timer bar amber at 33% | `get_color(0.333) == COLOR_TIMER_AMBER` |
| Timer bar red at 10% | `get_color(0.10) == COLOR_TIMER_RED` |
| Timer bar red at 0% | `get_color(0.0) == COLOR_TIMER_RED` |
| Screen vibration ≤ 3px | Same as jitter constraint |
| Button flash duration is exactly 200ms | State resets after 200ms elapsed |
| Button flash state false when not triggered | Default state |

**Mock dependencies:** None (pure math).

---

### 2.7 `test_scenario_logic.py`

| Test | Assertion |
|---|---|
| **MIST: correct answer** | `handle_keypress(correct_key)` returns `(True, ...)` |
| **MIST: wrong answer** | `handle_keypress(wrong_key)` returns `(False, ...)` |
| **MIST: all 4 answered** | After 4 answers, `(_, True)` |
| **MIST: accuracy 0%** | All wrong → `get_accuracy_pct() == 0` |
| **MIST: accuracy 100%** | All correct → `get_accuracy_pct() == 100` |
| **MIST: peer average** | Always `accuracy + 15` |
| **MIST: peer progress ahead** | `get_peer_progress_fraction() > get_progress_fraction()` always |
| **BART: first pump adds value** | `val > initial_value` |
| **BART: instability increases per pump** | `frac_after > frac_before` |
| **BART: burst at max pumps** | After `max_pumps` pumps, guaranteed burst |
| **BART: secure returns current value** | `secure() == expected` |
| **BART: no pump after secure** | Attempting pump after secure raises or returns safely |
| **BART: no pump after burst** | Same |
| **Reward: value grows over time** | After update(1000), `get_current_value() > initial` |
| **Reward: collapse within range** | Run 1000 trials, all collapses within `(20s, 40s)` |
| **Reward: claim returns current value** | `claim() == get_current_value()` |
| **Reward: no update after collapse** | Value frozen |
| **Reward: no update after claim** | Value frozen |
| **Reward: max display cap** | Value never exceeds `REWARD_MAX_DISPLAY` |
| **Delay: elapsed fraction 0 at start** | `get_elapsed_fraction() == 0.0` |
| **Delay: completed after full duration** | `update(duration_ms)` returns True |
| **Delay: fraction 0.5 at midpoint** | `≈ 0.5` after half the duration |

**Mock dependencies:** Fixed random seeds for deterministic BART burst testing.

---

### 2.8 `test_engine.py`

| Test | Assertion |
|---|---|
| Engine initializes to INIT state | `engine._current_state == EngineState.INIT` |
| Valid transition succeeds | `_transition_to(ID_INPUT)` from INIT — no exception |
| Invalid transition raises | `_transition_to(DEBRIEF)` from INIT → `InvalidStateTransition` |
| Backward transition raises | `_transition_to(BASELINE)` from DECISION → `InvalidStateTransition` |
| Mouse events ignored | Inject `MOUSEBUTTONDOWN` → no state change, no crash |
| KEYDOWN with number key in DECISION state | Updates selected option |
| KEYDOWN with invalid key in DECISION state | No effect, no crash |
| ESC key triggers shutdown | State → cleanup path (logger.close called) |
| Domain order is shuffled | Run 100× with different seeds, verify not all identical |
| Domain order logged | `save_domain_order` called with correct data |
| Deception metric only in social_evaluation | Verify `composure_fraction` is None for non-social_evaluation scenarios |
| Timer expiry triggers TIMEOUT_NO_RESPONSE | Set timer to 0 → verify event logged |
| Consequence text matches selected option | After selecting option 1 → feedback text == option.consequence_text |
| Decision state holds full duration after keypress (C1) | When option selected at frame 1, state remains DECISION until timer reaches 0 |
| Same-frame keypress wins over timeout (M2) | Valid KEYDOWN in same frame timer reaches 0 logs OPTION_SELECTED, never TIMEOUT_NO_RESPONSE |
| Focus loss freezes timers and audio (M3) | WINDOWFOCUSLOST pauses timer and drone; WINDOWFOCUSGAINED resumes |
| Post-wait only for future_uncertainty / delay_wait | Verify STATE_POST_WAIT entered when post-wait condition active |
| Intra-rest after Scenario A | Verify 15s timer after first scenario |
| Inter-rest after Scenario B | Verify 60s timer after second scenario |
| Debrief after all domains | After 7th domain → STATE_DEBRIEF |

**Mock dependencies:** Mock `pygame.event.get()`, `pygame.display.flip()`, `AudioController`, `UIRenderer`, `EventLogger`.

---

## 3. Critical Edge Cases

### 3.1 Timing & Clock

| ID | Edge Case | Expected Behavior |
|---|---|---|
| T-01 | `time.time_ns()` returns value that overflows 32-bit int | `unix_ts_ms` is `int` (Python arbitrary precision) — no overflow possible. Verify CSV stores full value. |
| T-02 | `dt_ms` is 0 (frame rendered instantly) | Timers must NOT advance. Guard: `if dt_ms <= 0: return` in `_update()`. |
| T-03 | `dt_ms` is very large (lag spike, >1000ms) | Timer must not overshoot past 0 into negative. Clamp: `timer = max(0, timer - dt_ms)`. |
| T-04 | System clock jumps backward (NTP sync) | `unix_ts_ms` may be non-monotonic. Log warning in metadata but do NOT crash. |
| T-05 | Session runs for >60 minutes | No integer overflow, no memory leak in event list (events are written to CSV immediately, not accumulated in memory). |

### 3.2 Input

| ID | Edge Case | Expected Behavior |
|---|---|---|
| I-01 | Key pressed during PRIMING (not DECISION) | Ignored. No state change, no event logged. |
| I-02 | Key pressed during REST | Ignored. |
| I-03 | Key pressed during FEEDBACK | Ignored. |
| I-04 | Multiple keys pressed in same frame | Process only the first `KEYDOWN` event. Ignore subsequent in same frame. |
| I-05 | Key `5` pressed during 3-option MCQ | Ignored (only keys 1–3 valid for 3 options, 1–4 for 4 options). |
| I-06 | Key `0` pressed | Ignored everywhere. |
| I-07 | Non-number key pressed during DECISION | Ignored (except ESC for quit). |
| I-08 | Rapid key spam (>10 presses per second) | Only the first valid keypress in DECISION state is accepted. Subsequent presses ignored after selection is locked. |
| I-09 | Subject ID input: empty string + Enter | Show error message "Enter a valid Subject ID (e.g., S01)". Do not advance. |
| I-10 | Subject ID input: "ABC" (invalid format) | Show error message. Do not advance. |
| I-11 | Subject ID input: "S01" (valid) | Accept and advance to BASELINE. |
| I-12 | Subject ID input: "S999" (valid edge) | Accept — pattern allows S\d{2,3}. |
| I-13 | Mouse click during any state | Completely ignored (cursor is hidden, MOUSEBUTTONDOWN events are not handled). |

### 3.3 State Machine

| ID | Edge Case | Expected Behavior |
|---|---|---|
| S-01 | `_transition_to()` called with same state | Raise `InvalidStateTransition` (self-transitions are not in VALID_TRANSITIONS). |
| S-02 | Engine shutdown during BASELINE | `logger.close()` called, CSV is well-formed (header + partial events). |
| S-03 | Engine shutdown during DECISION | Same as S-02. The in-progress scenario is logged as incomplete (no `SCENARIO_END`). |
| S-04 | `--domain academic_pressure` flag | Only 1 domain presented (2 scenarios), then → DEBRIEF. |
| S-05 | `--fast-baseline` | Baseline duration is 10s, not 180s. |
| S-06 | All 14 scenarios completed | State reaches DEBRIEF. Session ends cleanly. |

### 3.4 MIST Arithmetic (Domain 1A)

| ID | Edge Case | Expected Behavior |
|---|---|---|
| M-01 | All 4 answers correct | Accuracy 100%, peer average 115%. |
| M-02 | All 4 answers wrong | Accuracy 0%, peer average 15%. |
| M-03 | Timer expires mid-problem | Unanswered problems count as wrong. Log `TIMEOUT_NO_RESPONSE`. |
| M-04 | Answer key pressed after all 4 answered | Ignored — `all_problems_done` flag prevents further input. |
| M-05 | Peer progress always ahead | Verify `get_peer_progress_fraction() > get_progress_fraction()` at every point. |

### 3.5 BART Escalation (Domain 4B)

| ID | Edge Case | Expected Behavior |
|---|---|---|
| B-01 | First pump (probability ~5%) | Very unlikely burst. Value increases. |
| B-02 | Pump at max_pumps (15th pump) | Guaranteed burst (probability = 1.0 or deterministic cap). |
| B-03 | Secure after 0 pumps | Returns initial value. Scenario ends. |
| B-04 | Timer expires with no action | Log `TIMEOUT_NO_RESPONSE`. All accumulated value lost (treated as burst). |
| B-05 | Instability gauge at max | Visual gauge at 1.0 before burst. |

### 3.6 Reward Accumulator (Domain 3A)

| ID | Edge Case | Expected Behavior |
|---|---|---|
| R-01 | Claim at t=0 | Returns initial value (10). |
| R-02 | Collapse at earliest point (t=20s) | Value lost. Consequence text shown. |
| R-03 | Claim just before collapse | Value secured. Consequence shows how close they cut it. |
| R-04 | Value exceeds REWARD_MAX_DISPLAY | Clamped to 9999 on display. Internal value may be higher. |
| R-05 | Timer expires without claim or collapse | Treat as claim at current value (not loss). |

### 3.7 Deception Metric (Domain 7)

| ID | Edge Case | Expected Behavior |
|---|---|---|
| D-01 | No bridge connected (StubBridge) | Composure bar hidden or at 100%. No `DECEPTION_TRIGGER` events. |
| D-02 | MPU variance exactly at threshold (μ + 1.5σ) | Bar does NOT drop (threshold is strictly greater-than). |
| D-03 | MPU variance above threshold | Bar drops. `DECEPTION_TRIGGER` event logged. |
| D-04 | Baseline has zero variance (participant perfectly still) | σ = 0 → threshold = μ + 0 = μ. Any movement triggers. Handle gracefully (add minimum σ floor = 0.01). |
| D-05 | Deception metric in non-social_evaluation domain | Never active. `has_deception_metric=False` prevents composure bar rendering and MPU polling. |

### 3.8 Audio

| ID | Edge Case | Expected Behavior |
|---|---|---|
| A-01 | `tension_drone.wav` missing | `AudioLoadError` raised at `AudioController.__init__()`. Engine fails fast. |
| A-02 | `pygame.mixer` fails to initialize | Catch mixer error in `main.py`. Log warning, continue without audio. |
| A-03 | Drone start called when already playing | Idempotent — no effect, no crash, no restart. |
| A-04 | Drone stop called when not playing | Idempotent — no effect. |
| A-05 | Rapid start/stop cycling | No crash. Each call is idempotent. |

### 3.9 File System

| ID | Edge Case | Expected Behavior |
|---|---|---|
| F-01 | `outputs/game_logs/` doesn't exist | Created automatically by `EventLogger.__init__()`. |
| F-02 | Subject ID contains special characters | Rejected by `SUBJECT_ID_PATTERN` regex at ID input. |
| F-03 | Disk full during CSV write | `LoggerIOError` raised. Engine catches in `main.py`, attempts clean shutdown. |
| F-04 | CSV file path >260 chars (Windows MAX_PATH) | Use `Path` objects with long-path prefix if needed. Subject IDs are short (S01–S999), so this is unlikely. |
| F-05 | Two sessions with same subject ID | Each session gets a unique timestamp directory: `S01_1724688000000/`. No collision. |

### 3.10 Concurrency (Bridge Integration)

| ID | Edge Case | Expected Behavior |
|---|---|---|
| C-01 | Bridge thread writes faster than main thread reads | `queue.Queue(maxsize=256)` — oldest samples dropped via `queue.Full` handling in producer. Game always gets latest sample. |
| C-02 | Bridge thread crashes | `get_latest_sample()` returns `None`. Game continues without hardware data. |
| C-03 | Queue empty | `get_latest_sample()` returns `None`. No blocking. |
| C-04 | Main thread calls `get_latest_sample()` 60× per second | Queue drain is O(n) where n ≤ 256. At 66.67 Hz producer / 60 Hz consumer, queue depth is ~1 sample per frame. No performance issue. |

---

## 4. Strict Validation Assertions (Self-Correction Gates)

These assertions MUST pass for any implementation to be considered complete. They serve as the self-correction criteria for iterative code generation.

### Gate 1: Structural Integrity
```
□ All 11 files exist in src/game/: __init__.py, main.py, engine.py, scenarios.py, scenario_logic.py, ui.py, ui_effects.py, audio.py, event_logger.py, constants.py, bridge_interface.py
□ All files begin with docstring + `from __future__ import annotations`
□ No circular imports (verified by importing all modules in isolation)
□ No file exceeds 500 lines
□ No function exceeds 60 lines (excluding docstring)
```

### Gate 2: Type Safety
```
□ `mypy --strict src/game/` produces 0 errors (if mypy is available)
□ All function signatures have complete type annotations
□ No `Any` type used anywhere
□ No `# type: ignore` comments
```

### Gate 3: Behavioral Correctness
```
□ 7 domains × 2 scenarios = 14 scenarios in registry
□ All 14 scenario IDs are unique
□ social_evaluation is the ONLY domain with has_deception_metric=True
□ future_uncertainty scenarios have has_post_wait=True; impulsivity_gratification_b conditionally activates DELAY_WAIT
□ STATE_DECISION holds for full duration even when option selected early (C1)
□ MIST peer average is ALWAYS accuracy + 15
□ MIST starting difficulty is calibrated via pretest (C4)
□ BART burst probability increases monotonically with pumps
□ Reward accumulator collapse point is within (20, 40) seconds
□ Timer bar color transitions at correct fractions
□ Jitter never exceeds ±3px
```

### Gate 4: Data Integrity
```
□ CSV header matches the 9-column schema exactly
□ All unix_ts_ms values are valid Unix timestamps (>1700000000000)
□ Empty numeric fields are "" not "None" or "null"
□ metadata column is always valid JSON
□ domain_order.json contains exactly 7 domain IDs
□ domain_order.json random_seed matches the seed used for shuffling
```

### Gate 5: Safety Constraints
```
□ Mouse cursor is hidden
□ No mouse event handling code exists in any file
□ No numerical score displayed in any UI text
□ No strobing effect >3 Hz exists in any effect code
□ No skin-specific visual effect (brightness flicker, pulse, spin, swing) exceeds 3 Hz safety limit
□ No full-screen color inversion exists in any rendering code
□ Drone volume ≤ 0.30
□ Jitter amplitude constant ≤ 3
□ Deception metric only activates when has_deception_metric=True
```
