# TEST_CRITERIA_AND_EDGE_CASES.md — Pulse Gamification Engine

> **Scope:** Governs verification and resilience logic. Every module has unit test expectations, mock dependency specifications, critical edge cases, and strict pass/fail assertions. Code generators must ensure all listed edge cases are handled in implementation.

---

## 1. Testing Infrastructure

### Framework
- **Test runner:** `pytest` (in the `dev` dependency group of pyproject.toml, alongside `mypy` and `ruff`)
- **Assertions:** Native `assert` statements (pytest rewrites them for readable failures)
- **Mocking:** `unittest.mock.patch`, `unittest.mock.MagicMock` — no additional mocking library
- **Pygame tests:** Use `pygame.init()` / `pygame.quit()` in fixtures. All rendering tests use a headless `pygame.Surface(1280, 720)` without `set_mode()` when possible.
- **Pixel tests:** `numpy` over `pygame.surfarray` (palette and indicator tests). No image files are stored; frames are rendered and inspected in memory.
- **Serial tests:** no real port is opened. `SerialBridge` takes any object with `readline()` / `close()`; `create_bridge()` and `probe_port()` take an injected opener and port lister.
- **Warnings:** `[tool.pytest.ini_options] filterwarnings` silences one upstream deprecation (pygame 2.6 importing `pkg_resources`), so the run prints no warnings and a warning from Pulse's own code stands out.

### Test File Location
```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures (headless SDL video/audio drivers)
├── game/
│   ├── test_constants.py          #  5 tests
│   ├── test_scenarios.py          # 10   (+ locked durations, no score language)
│   ├── test_event_logger.py       #  4
│   ├── test_audio.py              #  2
│   ├── test_bridge_interface.py   # 12   (stream parser, SerialBridge, ReplayBridge, port scan / probe, create_bridge)
│   ├── test_ui_effects.py         #  5
│   ├── test_scenario_logic.py     # 12   (+ MIST adaptation / timeout, BART hazard / cooldown / counterfactual)
│   ├── test_ui.py                 # 13
│   ├── test_engine.py             # 14
│   ├── test_audit_fixes.py        # 14   (audit remediation regressions)
│   ├── test_engine_paradigms.py   #  7   (rest option, CLI, bridge lifecycle, MIST / BART logging and indicators)
│   └── test_palette.py            #  6   (Ferrari tokens, no chromatic literals, per-pixel hue audit, key badge)
└── pipeline/                      #  3   (loader / preprocess / feature placeholders)
```

**Current total: 107 tests** (104 game + 3 pipeline placeholders), about 5 s. The three commands below are the completion gate for any change, and all three must be clean:

```powershell
uv run pytest -v                      # 107 passed, no warnings
uv run mypy src/ tests/ --strict      # Success: no issues found in 76 source files
uv run ruff check .                   # All checks passed (whole repository, including validation/)
```

### Shared Fixtures (`conftest.py`)

```python
import pytest
import pygame
from pathlib import Path
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
| **Durations are locked** (`test_scenario_durations_are_locked`) | Priming == `DEFAULT_PRIMING_DURATION_S` == 20 for all 14; decision == 45 except `academic_pressure_a` == 40; consequence == 4; `social_evaluation_b` decision == 45; priming + decision + consequence ≥ `MIN_ACTIVE_EPOCH_S` for every scenario; the MIST priming text quotes the real duration |
| **No score language** (`test_participant_facing_text_has_no_score_language`) | No scenario title, briefing, option, consequence or wait text, and no string literal drawn by `ui*.py`, `skins/*.py` or the engine, contains "score", "points" or "leaderboard" |
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
| `test_stub_bridge_protocol_compliance` | `isinstance(StubBridge(), BridgeInterface)`; both getters return None; `close()` is a no-op |
| `test_sensor_sample_fields` | `SensorSample` field types |
| `test_parse_firmware_recorded_and_json_rows` | A 7-field firmware row, an 8-field recorded row and a JSON object (with aliases and an ignored `hr` key) map onto the same `SensorRow`; the recorded `unix_ts_ms` is kept, otherwise the arrival time is used |
| `test_parse_rejects_malformed_rows` | Header, `#` comment, blank, short row, text, float text, `NaN`, JSON array, JSON boolean → `None` |
| `test_serial_bridge_reports_latest_sample_and_variance` | Rolling variance equals the population variance of `√(x²+y²+z²)`; a sample is returned once (unread semantics); fewer than 20 samples or a 1.5 s silence → `None` |
| `test_serial_bridge_counts_gaps_and_records_serial_reader_schema` | A dropped `sample_idx` increments `gap_events`; malformed lines increment `rows_rejected`; the recording's header and rows equal `serial_reader.py`'s schema |
| `test_serial_bridge_background_thread_and_port_failure` | The daemon thread ingests rows; a port that raises `OSError` stops the thread, sets `error`, and never propagates; `close()` is idempotent and closes the port |
| `test_port_scan_keeps_only_known_usb_serial_bridges` | Bluetooth ports, ports without a VID and unknown vendors are excluded |
| `test_probe_negotiates_baud_and_skips_busy_or_foreign_ports` | First baud that yields 3 valid rows wins and the port is returned open; a busy port (`OSError`) and a port speaking another protocol return `None` and are closed |
| `test_create_bridge_modes_and_fallback` | `stub` → `StubBridge`; `auto` with no hardware → `StubBridge` with a reason; `serial` with no hardware → `BridgeUnavailableError`; `auto` with a responding port → started `SerialBridge`; `replay` without a source and an unknown mode raise |
| `test_replay_bridge_paces_a_recording` | Rows are released on the recording's own timeline as the injected clock advances, not all at once; `is_finished()` only after the last row |
| `test_replay_bridge_follows_a_file_being_written` | Follow mode ignores rows already in the file, ingests complete appended rows, and leaves a partial row for the next poll |

**Mock dependencies:** `_FakePort` (prepared lines, then timeouts), injected `opener`, `comports` and clock. No real serial port, no sleeping.

---

### 2.6 `test_ui_effects.py`

| Test | Assertion |
|---|---|
| Jitter offset never exceeds ±JITTER_MAX_PX | Test 1000 frames, verify `abs(offset) <= 3` |
| Jitter displacement is vector-bounded | `max(hypot(dx, dy)) <= JITTER_MAX_PX` over 10s (per-axis bounds alone allow 4.24px) |
| Jitter frequency ≤ JITTER_MAX_HZ on BOTH axes | Zero-crossing rate of dx and of dy each ≤ 2 Hz |
| Timer bar green at 100% | `get_color(1.0) == COLOR_TIMER_GREEN` |
| Timer bar amber at 33% | `get_color(0.333) == COLOR_TIMER_AMBER` |
| Timer bar red at 10% | `get_color(0.10) == COLOR_TIMER_RED` |
| Timer bar red at 0% | `get_color(0.0) == COLOR_TIMER_RED` |
| Screen vibration ≤ 2px, ≤ 2Hz | `VIBRATION_MAX_PX <= 2`; vector magnitude and both axis frequencies bounded |
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
| **MIST: adaptive countdown** (`test_mist_item_limit_tightens_…`) | One correct answer changes nothing; the second tightens the limit to `round(8000 × 0.9)`; one wrong answer changes nothing; the second eases it by 10 %; 40 correct pin it at `MIST_ITEM_LIMIT_MIN_MS`, 40 wrong at `MIST_ITEM_LIMIT_MAX_MS` |
| **MIST: item timeout** (`test_mist_item_timeout_scores_incorrect_and_advances`) | `update()` returns True exactly when the limit is reached; the item counts as answered-incorrect; the next problem is presented with a full countdown; two timeouts ease the limit |
| **BART: hazard curve** (`test_bart_hazard_escalates_…`) | Production curve is strictly increasing, ≤5 % on the first pump, <50 % on the 14th, 1.0 on the 15th; expected safe pumps between 5 and 8 |
| **BART: pacing** (`test_bart_cooldown_paces_pumps`) | After a pump `can_pump()` is False until `cooldown_ms` has elapsed; `get_cooldown_fraction()` runs 1.0 → 0.0; an unpaced runner is always ready |
| **BART: honest counterfactual** (`test_bart_counterfactual_matches_…`) | For 25 seeds, `get_pumps_remaining_after_burst()` equals the number of pumps that actually survive when pumping continues, and asking does not consume the RNG |
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
| Inter-rest after Scenario B | Verify the 30s default timer after the second scenario (60s with `--extended-rest`: `test_engine_paradigms.py`) |
| Debrief after all domains | After 7th domain → STATE_DEBRIEF |

**Mock dependencies:** Mock `pygame.event.get()`, `pygame.display.flip()`, `AudioController`, `UIRenderer`, `EventLogger`.

> **Note on `test_engine.py`:** its helper builds `SessionConfig` with the exposure guarantees at their default (off), so those 14 tests step the state machine instantly. The guaranteed behaviour (C1 hold, priming floor, M3 focus freeze) is asserted in `test_audit_fixes.py` with the guarantees switched on, exactly as `main.py` configures a real session. The inter-rest test asserts the 30s default (ADR-B2).

---

### 2.9 `test_audit_fixes.py` (audit remediation regressions)

| Test | Assertion |
|---|---|
| `test_decision_floor_holds_reflex_choice` | Keypress at 0ms logs one `OPTION_SELECTED`, state stays DECISION until the timer expires, a second key cannot change the choice, no `TIMEOUT_NO_RESPONSE` |
| `test_floor_applies_to_every_scenario` | All 14 scenarios: 8 keypresses, still DECISION at `duration − 1s`, advanced at `duration` |
| `test_priming_floor_blocks_early_skip` | SPACE ignored before the 8s read floor; with a 60s epoch the MIST scenario refuses SPACE at 15s and accepts at 16s |
| `test_delay_wait_branch_enters_post_wait` | `impulsivity_gratification_b`: Key 2 → POST_WAIT, Key 1 → FEEDBACK |
| `test_post_wait_reflects_chosen_fork` | Choosing Path B sets `renderer._last_fork_choice == 1` |
| `test_mist_runs_on_the_clock_and_caps_peer_figure` | Six correct answers do not end MIST; expiry gives "Peer average: 100%", no timeout event, `item_rt_ms` on every `MATH_ANSWER` |
| `test_mist_answer_position_is_not_a_fixed_cycle` | Correct positions are not `[0,1,2,3,…]` |
| `test_popup_blocks_decision_keys` | TAB held + number key commits nothing |
| `test_composure_requires_sustained_motion_and_cooldown` | One spike leaves 100%; sustained motion gives exactly one 15% drop and one `DECEPTION_TRIGGER` inside the cooldown |
| `test_composure_is_none_without_telemetry` | `StubBridge` never yields a live reading; render succeeds in STANDBY |
| `test_clock_anomaly_and_focus_are_logged` | 400ms frame logs one `CLOCK_ANOMALY`; timers freeze between `FOCUS_LOST` and `FOCUS_GAINED`; aborted `SESSION_END` |
| `test_edited_subject_id_reaches_session_metadata` | ID typed on the entry screen is written to `domain_order.json` |
| `test_effect_limits_are_vector_and_frequency_bounded` | Jitter ≤3px / ≤2Hz and vibration ≤2px / ≤2Hz by vector magnitude on both axes |
| `test_text_width_guard_and_feedback_badge` | `_draw_text(max_width=)` never exceeds the width; the suspension badge appears only for its own consequences |

---

### 2.10 `test_engine_paradigms.py` (session options, bridge lifecycle, MIST / BART at engine level)

| Test | Assertion |
|---|---|
| `test_inter_domain_rest_default_and_extended` | `INTER_REST` timer is 30 000 ms by default and 60 000 ms when `inter_domain_rest_s = 60`; `REST_START` metadata is `{is_inter: true, duration_s}`; `SYNC_PULSE` records `inter_domain_rest_s` |
| `test_cli_defaults_enable_every_guarantee_and_flags_override` | `parse_cli(["--subject", "S01"])` → hold on, 8 s read floor, 60 s epoch, 30 s rest, bridge `auto`; `--extended-rest`, `--no-exposure-floor`, `--bridge replay --bridge-source … --bridge-follow --bridge-port` map to their fields; a bad subject and `--bridge replay` without a source exit |
| `test_engine_closes_bridge_and_reports_lost_telemetry` | A bridge that goes silent flips `_telemetry_live` to False (display returns to STANDBY); `_shutdown()` closes the bridge |
| `test_mist_item_timeout_is_logged_as_an_incorrect_answer` | An unanswered item produces one `MATH_ANSWER` row with empty `key_pressed` / `option_index`, `correct: false`, `timed_out: true`, the `item_limit_ms` in force and the problem text; the flash follows on the next frame; the state stays DECISION |
| `test_bart_pumps_are_paced_and_log_the_pressure_curve` | A second pump inside the cooldown is ignored; accepted pumps log `pump` 1, 2 with `burst_prob` 0.02, 0.05 and rising `instability`; `BART_SECURE` logs `pumps: 2` and `next_burst_prob: 0.08` |
| `test_mist_item_countdown_bar_drains_and_turns_rosso_near_expiry` | With half the item time left the bar adds no Rosso pixels; below 25 % it is Rosso and its pixel count halves from 20 % to 10 % remaining |
| `test_bart_pacing_cooldown_is_shown_on_the_pump_card` | The pump card reads "POST ANOTHER (Escalate Reach)" when live, "PUBLISHING POST..." inside the cooldown, and live again after it |

### 2.11 `test_palette.py` (ADR-B5)

| Test | Assertion |
|---|---|
| `test_palette_tokens_match_the_ferrari_design_system` | Every colour token equals its `DESIGN-ferrari.md` hex; amber == yellow, timer red == Rosso; the canvas is not pure black; `COLOR_ACCENT_INDIGO` no longer exists |
| `test_ui_code_has_no_chromatic_colour_literals` | AST scan of `ui*.py` and `skins/*.py`: every literal RGB / RGBA tuple is a neutral grey |
| `test_off_palette_detector_flags_foreign_hues` | The detector accepts all six tokens and their blends toward canvas and white, and counts exactly the pixels of a purple and a navy patch |
| `test_every_screen_renders_inside_the_palette` | 14 skins × (idle, selected + flashing, final seconds), BART burst, chest collapse, briefing popup, priming, feedback, post-wait, ID input, baseline, rest, debrief: zero pixels with a foreign hue |
| `test_key_badge_is_neutral_and_inverts_when_selected` | Badge border is `COLOR_TEXT_SECONDARY`, plate `COLOR_BG`; selected plate is white; disabled border is `COLOR_HAIRLINE_SUBTLE`; no Rosso pixel in any state |
| `test_selecting_an_option_never_adds_rosso` | On the five plain multiple-choice skins, selecting any option never increases the number of Rosso pixels |

---

## 3. Critical Edge Cases

### 3.1 Timing & Clock

| ID | Edge Case | Expected Behavior |
|---|---|---|
| T-01 | `time.time_ns()` returns value that overflows 32-bit int | `unix_ts_ms` is `int` (Python arbitrary precision) — no overflow possible. Verify CSV stores full value. |
| T-02 | `dt_ms` is 0 (frame rendered instantly) | Timers must NOT advance. Guard: `if dt_ms <= 0: return` in `_update()`. |
| T-03 | `dt_ms` is very large (lag spike, >1000ms) | Timer must not overshoot past 0 into negative. Clamp: `timer = max(0, timer - dt_ms)`. |
| T-04 | System clock jumps backward (NTP sync) | `unix_ts_ms` may be non-monotonic. `CLOCK_ANOMALY` is logged when the wall-clock delta and the frame delta differ by more than 50ms; reaction times are unaffected because they use the monotonic clock. Never crash. |
| T-06 | Frame stall (window drag, OS hitch) | `CLOCK_ANOMALY` logged when `dt_ms` > one frame + 50ms, with `wall_delta_ms`, `frame_dt_ms`, `state`. |
| T-05 | Session runs for >60 minutes | No integer overflow, no memory leak in event list (events are written to CSV immediately, not accumulated in memory). |

### 3.2 Input

| ID | Edge Case | Expected Behavior |
|---|---|---|
| I-01 | Key pressed during PRIMING (not DECISION) | Number keys ignored. SPACE/ENTER shorten priming only after the priming floor (ARCHITECTURE_SPEC §5 Rule 1); before it they are ignored. |
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
| I-13 | Mouse click during any state | Completely ignored (cursor is hidden, mouse events are blocked at the event queue and never handled). |
| I-14 | Number key while the TAB/Q briefing popup is held | Ignored. No choice can be committed while the options are hidden. |
| I-15 | Number key after a choice is committed (during the hold) | Ignored. The first commit is final. |

### 3.3 State Machine

| ID | Edge Case | Expected Behavior |
|---|---|---|
| S-01 | `_transition_to()` called with same state | Raise `InvalidStateTransition` (self-transitions are not in VALID_TRANSITIONS). |
| S-02 | Engine shutdown during BASELINE | `logger.close()` called, CSV is well-formed (header + partial events). |
| S-03 | Engine shutdown during DECISION | Same as S-02. The in-progress scenario is logged as incomplete (no `SCENARIO_END`), and `SESSION_END` carries `aborted: true` with the state at exit. |
| S-07 | Window loses focus mid-scenario | `FOCUS_LOST` logged, timers and drone frozen; `FOCUS_GAINED` resumes both. No timeout can occur while unfocused. |
| S-04 | `--domain academic_pressure` flag | Only 1 domain presented (2 scenarios), then → DEBRIEF. |
| S-05 | `--fast-baseline` | Baseline duration is 10s, not 180s. |
| S-06 | All 14 scenarios completed | State reaches DEBRIEF. Session ends cleanly. |

### 3.4 MIST Arithmetic (Domain 1A)

| ID | Edge Case | Expected Behavior |
|---|---|---|
| M-01 | All answers correct | `MISTRunner` reports accuracy 100% and peer average 115%; the engine caps the displayed peer figure at 100%. |
| M-02 | All answers wrong | Accuracy 0%, peer average 15%. |
| M-03 | Timer expires | The engine feeds the runner 60 problems, so the task always ends on the clock. Expiry after ≥1 answer shows the accuracy summary and logs no timeout; expiry with zero answers logs `TIMEOUT_NO_RESPONSE`. |
| M-04 | Answer key pressed after every problem is answered | Ignored — `all_problems_done` flag prevents further input (unreachable in practice with 60 problems in 40s). |
| M-06 | Answer-key pattern | The correct option position is drawn from the seeded RNG, not cycled 1-2-3-4. |
| M-05 | Peer progress always ahead | Verify `get_peer_progress_fraction() > get_progress_fraction()` at every point. |
| M-07 | Item left unanswered | The per-item countdown (8 s at the start) expires: the item is scored incorrect, logged as `MATH_ANSWER` with `timed_out: true` and no key, the wrong-answer flash fires, and the next problem appears with a full countdown. |
| M-08 | Long correct streak | The countdown tightens 10 % per two consecutive correct answers and never goes below 3 s. |
| M-09 | Long error streak (including timeouts) | The countdown eases 10 % per two consecutive failures and never exceeds 12 s. |
| M-10 | Alternating correct / wrong | No adaptation: a streak needs two consecutive outcomes of the same kind. |
| M-11 | Participant never presses a key | Items time out one after another (8 s, 8 s, then eased), each logged; the MIST run still ends on the 40 s clock. Because ≥1 item was scored, expiry is completion, not `TIMEOUT_NO_RESPONSE`. |

### 3.5 BART Escalation (Domain 4B)

| ID | Edge Case | Expected Behavior |
|---|---|---|
| B-01 | First pump (hazard 2%) | Very unlikely burst. Value increases. Hazard then rises 3 points per pump (5%, 8%, … 41% on the 14th). |
| B-02 | Pump at max_pumps (15th pump) | Guaranteed burst (probability = 1.0 or deterministic cap). |
| B-03 | Secure after 0 pumps | Returns initial value. The choice is committed; the state exits when the decision timer expires (C1). |
| B-06 | Burst before the timer expires | `BART_BURST` logged at once; the suspension splash stays on screen until the timer expires. |
| B-04 | Timer expires with no action | Log `TIMEOUT_NO_RESPONSE`. All accumulated value lost (treated as burst). |
| B-05 | Instability gauge at max | Visual gauge at 1.0 before burst. |
| B-07 | Pump key pressed inside the 1.5 s cooldown | Ignored and not logged; the latency clock is not reset; the pump card reads "PUBLISHING POST..." with a progress line and a muted key badge. |
| B-08 | Secure key pressed inside the cooldown | Accepted. Pacing never blocks the safe option. |
| B-09 | Key mashing | At most one pump per 1.5 s, so a 45 s window allows at most 30 attempts — more than the 15-pump cap, so pacing never prevents reaching the cap deliberately. |
| B-10 | "Would have survived N more" after securing | N is replayed from a copy of the session's RNG state and equals what would really have happened. |

### 3.6 Reward Accumulator (Domain 3A)

| ID | Edge Case | Expected Behavior |
|---|---|---|
| R-01 | Claim at t=0 | Returns initial value (10). |
| R-02 | Collapse at earliest point (t=20s) | Value lost. `REWARD_COLLAPSE` logged at once; the collapsed chest stays on screen until the timer expires, then the consequence text is shown. |
| R-03 | Claim just before collapse | Value secured. Consequence shows how close they cut it. |
| R-04 | Value exceeds REWARD_MAX_DISPLAY | Clamped to 9999 on display. Internal value may be higher. |
| R-05 | Timer expires without claim or collapse | Treat as claim at current value (not loss). |

### 3.7 Deception Metric (Domain 7)

| ID | Edge Case | Expected Behavior |
|---|---|---|
| D-01 | No bridge connected (StubBridge) | Composure bar renders "TELEMETRY LINK: STANDBY" with an empty track — never a reading. No `DECEPTION_TRIGGER` events. `SYNC_PULSE` metadata records `bridge: StubBridge`. |
| D-02 | MPU variance exactly at threshold (μ + 1.5σ) | Bar does NOT drop (threshold is strictly greater-than). |
| D-03 | MPU variance above threshold | Bar drops 15% only after 3 consecutive supra-threshold samples (~0.75s at 4Hz) and outside the 5s cooldown. One `DECEPTION_TRIGGER` per drop, with `mpu_var` and `threshold`. A single spike changes nothing. |
| D-06 | Composure carry-over | Composure, poll timer, streak and cooldown reset at every DECISION entry. |
| D-04 | Baseline has zero variance (participant perfectly still) | σ = 0 → threshold = μ + 0 = μ. Any movement triggers. Handle gracefully (add minimum σ floor = 0.01). |
| D-05 | Deception metric in non-social_evaluation domain | Never active. `has_deception_metric=False` prevents composure bar rendering and MPU polling. |
| D-07 | Sensor unplugged mid-session | `get_mpu_variance()` returns `None` once the newest sample is older than 1.5 s; the composure display returns to STANDBY instead of freezing on the last reading. |

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

### 3.10 Concurrency and Hardware (Sensor Bridge)

| ID | Edge Case | Expected Behavior |
|---|---|---|
| C-01 | Bridge thread reads faster than the main thread polls | The buffer keeps only the latest sample and a 1 s window of magnitudes; nothing queues up. The game always gets the newest sample. |
| C-02 | Serial port fails (`OSError` / `ValueError` from `readline`) | The reader thread stops, `SerialBridge.error` records why, nothing propagates. Telemetry goes stale and the display returns to STANDBY. |
| C-03 | No new sample since the last poll | `get_latest_sample()` returns `None`. No blocking. |
| C-04 | Main thread polls 60× per second | One lock acquisition per call; the variance is computed over ≤ ~70 samples. No performance issue. |
| C-05 | `serial_reader.py` already owns the port | The probe's open raises `OSError`; `auto` falls back to `StubBridge` with a message naming `--bridge replay --bridge-follow`; `serial` raises `BridgeUnavailableError`. The recorder is never disturbed. |
| C-06 | pyserial not installed | `auto` → `StubBridge` with the reason; `serial` → `BridgeUnavailableError`. The engine itself never imports `serial` at module load. |
| C-07 | A Bluetooth COM port or another instrument is present | Never opened: auto-detection only considers ports whose USB vendor ID is a known ESP32 serial bridge. |
| C-08 | A port answers but speaks another protocol | Fewer than 3 valid rows within 3 s → the port is closed and skipped. |
| C-09 | Recording file cannot be written (disk full) | Recording stops, `error` is set, telemetry continues. |
| C-10 | Follow mode reads a row that is still being written | A line without a trailing newline is not consumed; the file position is rewound and the row is read whole on the next poll. |
| C-11 | Replay of a recording | Rows are released on the recording's own timestamps relative to the first poll, so a 60 s file replays in 60 s. |
| C-12 | Boot banner, header row or garbage on the stream | Rejected by `parse_sensor_line()` and counted; never reaches the buffer or the recording. |
| C-13 | Engine exit (normal, ESC, exception) | `main.py` closes the bridge in `finally`; `GameEngine._shutdown()` closes it too. `close()` is idempotent. |

---

## 4. Strict Validation Assertions (Self-Correction Gates)

These assertions MUST pass for any implementation to be considered complete. They serve as the self-correction criteria for iterative code generation.

### Gate 1: Structural Integrity
```
□ src/game/ contains: __init__.py, main.py, engine.py, engine_state.py, engine_input.py, engine_timer.py,
  scenarios.py, scenario_logic.py, ui.py, ui_core.py, ui_components.py, ui_screens.py, ui_post_wait.py,
  ui_domains.py, ui_effects.py, audio.py, event_logger.py, constants.py, bridge_interface.py,
  sensor_stream.py, sensor_replay.py, sensor_bridge.py, and skins/ with one module per skin (14)
□ All files begin with docstring + `from __future__ import annotations`
□ No circular imports (verified by importing all modules in isolation)
□ No file exceeds 500 lines (largest in src/game/: scenarios.py, 428; largest test: test_ui.py, 495)
□ No function exceeds 60 lines (excluding docstring) — NOT MET, see below
```
> **Status (2026-10-02):** the file-length rule is met across `src/` and `tests/`. The function-length rule is not: 19 functions in `src/game/` exceed 60 lines, 15 of them the `_draw_skin_*` methods (134–304 lines). Tracked in ARCHITECTURE_SPEC §7.3.

### Gate 2: Type Safety
```
□ `mypy src/ tests/ --strict` produces 0 errors (76 source files, verified clean 2026-10-02)
□ `ruff check .` produces 0 findings across the whole repository (verified clean 2026-10-02)
□ All function signatures have complete type annotations
□ No `Any` in src/game/ (the pipeline uses `dict[str, Any]` for its signal dictionaries)
□ No `# type: ignore` in src/ (tests use it only where they deliberately pass a wrong type or patch a method)
```

### Gate 3: Behavioral Correctness
```
□ 7 domains × 2 scenarios = 14 scenarios in registry
□ All 14 scenario IDs are unique
□ social_evaluation is the ONLY domain with has_deception_metric=True
□ future_uncertainty scenarios have has_post_wait=True; impulsivity_gratification_b conditionally activates DELAY_WAIT
□ STATE_DECISION holds for full duration even when option selected early (C1) — all 14 scenarios
□ PRIMING + DECISION + FEEDBACK ≥ 60s: SPACE cannot shorten priming below the priming floor
□ MIST peer average is ALWAYS accuracy + 15 in the runner; the displayed figure is capped at 100%
□ MIST runs on the clock and its correct-answer position is not a fixed cycle
□ MIST difficulty adapts in-run: the per-item countdown tightens 10% after 2 correct and eases 10% after 2 incorrect, within 3–12s (replaces the pretest)
□ An unanswered MIST item times out, is scored incorrect and is logged
□ Priming is 20s in all 14 scenarios; decisions are 45s (MIST 40s); durations come from constants.py only
□ Inter-domain rest is 30s by default and 60s with --extended-rest; the duration used is logged
□ Composure drops require 3 consecutive supra-threshold samples and respect the 5s cooldown
□ BART burst probability increases monotonically with pumps (2% → 41%, certain on the 15th)
□ BART pumps are paced (1.5s cooldown) and each accepted pump logs its hazard, value and latency
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
□ No numerical score displayed in any UI text, and the words "score" / "points" appear in no participant-facing string
□ No strobing effect >3 Hz exists in any effect code
□ No skin-specific visual effect (brightness flicker, pulse, spin, swing) exceeds 3 Hz safety limit
□ No full-screen color inversion exists in any rendering code
□ Drone volume ≤ 0.30
□ Jitter amplitude constant ≤ 3, enforced as vector magnitude, both axes ≤ 2 Hz
□ Screen vibration ≤ 2px and ≤ 2 Hz
□ Compass rotation ≤ COMPASS_SPIN_MAX_RPM (4) in decision and post-wait
□ Baseline screen has no paced-breathing stimulus
□ No participant-facing string names a paradigm, citation or construct
□ Composure bar never shows a reading without live telemetry
□ Deception metric only activates when has_deception_metric=True
□ No chromatic colour outside the six Ferrari tokens (literal scan + per-pixel hue audit)
□ Key prompts are neutral plates; Rosso Corsa never marks the participant's own selection
□ Stale telemetry (no sample for 1.5s) is shown as STANDBY, not as a frozen reading
□ Auto-detection never opens a serial port that is not a known ESP32 USB bridge
```
