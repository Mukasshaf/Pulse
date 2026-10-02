# DATA_MODELS_AND_CONTRACTS.md — Pulse Gamification Engine

> **Scope:** Eliminates structural ambiguity. Every dataclass, enum, constant, CSV column, function signature, and exception is defined here. Code generators must implement these exactly — no field additions, no renamed parameters, no type changes.

---

## 1. Enumerations

```python
# All enums use StrEnum for JSON-serializable .value

from enum import StrEnum

class EngineState(StrEnum):
    INIT         = "INIT"
    ID_INPUT     = "ID_INPUT"
    BASELINE     = "BASELINE"
    PRIMING      = "PRIMING"
    DECISION     = "DECISION"
    POST_WAIT    = "POST_WAIT"
    FEEDBACK     = "FEEDBACK"
    INTRA_REST   = "INTRA_REST"
    INTER_REST   = "INTER_REST"
    DEBRIEF      = "DEBRIEF"

class EventType(StrEnum):
    SYNC_PULSE         = "SYNC_PULSE"
    BASELINE_START     = "BASELINE_START"
    BASELINE_END       = "BASELINE_END"
    DOMAIN_START       = "DOMAIN_START"
    SCENARIO_PRIMING   = "SCENARIO_PRIMING"
    DECISION_PRESENTED = "DECISION_PRESENTED"
    OPTION_SELECTED    = "OPTION_SELECTED"
    TIMEOUT_NO_RESPONSE = "TIMEOUT_NO_RESPONSE"
    MATH_ANSWER        = "MATH_ANSWER"
    BART_PUMP          = "BART_PUMP"
    BART_SECURE        = "BART_SECURE"
    BART_BURST         = "BART_BURST"
    REWARD_CLAIM       = "REWARD_CLAIM"
    REWARD_COLLAPSE    = "REWARD_COLLAPSE"
    SCENARIO_END       = "SCENARIO_END"
    REST_START         = "REST_START"
    REST_END           = "REST_END"
    SESSION_END        = "SESSION_END"
    DECEPTION_TRIGGER  = "DECEPTION_TRIGGER"
    FOCUS_LOST         = "FOCUS_LOST"
    FOCUS_GAINED       = "FOCUS_GAINED"
    CLOCK_ANOMALY      = "CLOCK_ANOMALY"

class ScenarioType(StrEnum):
    STANDARD_MCQ       = "STANDARD_MCQ"
    MIST_ARITHMETIC    = "MIST_ARITHMETIC"
    BART_ESCALATION    = "BART_ESCALATION"
    REWARD_ACCUMULATOR = "REWARD_ACCUMULATOR"
    DELAY_WAIT         = "DELAY_WAIT"

class DomainID(StrEnum):
    ACADEMIC_PRESSURE          = "academic_pressure"
    PEER_INFLUENCE             = "peer_influence"
    IMPULSIVITY_GRATIFICATION  = "impulsivity_gratification"
    RISK_REWARD                = "risk_reward"
    RULE_AMBIGUITY             = "rule_ambiguity"
    FUTURE_UNCERTAINTY         = "future_uncertainty"
    SOCIAL_EVALUATION          = "social_evaluation"
```

---

## 2. Dataclasses

```python
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Option:
    key: int                          # 1, 2, 3, or 4
    text: str                         # Display text for this option
    consequence_text: str             # Shown during STATE_FEEDBACK
    is_conforming: bool | None = None # Only used in peer_influence domain (Asch)

@dataclass(frozen=True)
class MathProblem:
    question_text: str                # e.g. "247 + 386 = ?"
    options: list[int]                # 4 answer options [633, 621, 647, 612]
    correct_index: int                # 0-based index of correct answer

@dataclass(frozen=True)
class BARTConfig:
    initial_value: int                # Starting accumulated value
    increment_per_pump: int           # Value added per Key 2 press
    burst_probability_base: float     # Burst hazard of the first pump (production: 0.02)
    burst_probability_increment: float # Added to the hazard for each further pump (production: 0.03)
    max_pumps: int                    # Hard cap: the pump with this number always bursts (production: 15)

@dataclass(frozen=True)
class RewardAccumulatorConfig:
    initial_value: int                # Starting reward value
    growth_rate: float                # Multiplier per second (e.g. 1.15)
    collapse_time_range: tuple[int, int]  # (min_s, max_s) — random collapse within
    max_display_value: int            # Cap for display (e.g. 9999)

@dataclass(frozen=True)
class Scenario:
    id: str                           # e.g. "academic_pressure_a"
    domain_id: DomainID
    title: str                        # e.g. "Exam Countdown Rush"
    paradigm: str                     # Registry documentation only: never rendered, never logged
    priming_text: str                 # Full priming message
    priming_duration_s: int           # DEFAULT_PRIMING_DURATION_S (20) in all 14 scenarios — locked, ADR-B3
    decision_duration_s: int          # MIST_DECISION_DURATION_S (40) for academic_pressure_a, else DEFAULT_DECISION_DURATION_S (45)
    consequence_duration_s: int       # DEFAULT_CONSEQUENCE_DURATION_S (4)
    options: list[Option]             # 2–4 options
    scenario_type: ScenarioType       # Determines which runner to use
    skin: str = ""                    # Simulation skin key, dispatched to UIRenderer._draw_skin_<skin>() (src/game/skins/<skin>.py)
    has_deception_metric: bool = False # True only for social_evaluation scenarios
    has_post_wait: bool = False       # True only for future_uncertainty scenarios
    post_wait_duration_s: int = 0     # 10 or 12 for future_uncertainty; 15 for the DELAY_WAIT scenario, where
                                      # only Key 2 ("request more time") enters POST_WAIT; 0 otherwise
    post_wait_text: str = ""          # "Processing your selection..."
    math_problems: list[MathProblem] | None = None     # MIST only
    bart_config: BARTConfig | None = None              # BART only
    reward_config: RewardAccumulatorConfig | None = None # Accumulator only
    delay_wait_outcomes: list[str] | None = None       # DELAY_WAIT only
    timeout_consequence: str = "The system has made a decision for you."
    jitter_trigger_s: int | None = None  # Seconds remaining when jitter activates (e.g. 10)
    drone_trigger_fraction: float = 0.333  # Fraction of timer remaining when drone starts

@dataclass(frozen=True)
class Domain:
    id: DomainID
    name: str                         # e.g. "Academic Performance Pressure"
    scenarios: tuple[Scenario, Scenario]  # Exactly 2 per domain — enforced

@dataclass
class GameEvent:
    unix_ts_ms: int                   # int(time.time_ns() // 1_000_000) — join key with serial_reader.py
    event_type: EventType
    domain: str                       # DomainID.value or "" for session-level events
    scenario_id: str                  # Scenario.id or "" for non-scenario events
    choice_data: str                  # JSON-encoded selection data (key, option text) or "{}"
    key_pressed: int | None           # The key number pressed (1–4) or None
    option_index: int | None          # 0-based index of selected option, or None
    response_time_ms: int | None      # ms from DECISION_PRESENTED to keypress (monotonic clock), or None
    metadata: dict[str, str | int | float | bool]  # Arbitrary k/v (scenario-specific data)

@dataclass
class SensorSample:
    """Produced by a sensor bridge (SerialBridge / ReplayBridge). The game engine consumes these read-only."""
    unix_ts_ms: int
    bvp: float                        # Analog Pulse Sensor raw PPG value (GPIO35)
    gsr: int                          # Grove-GSR raw ADC value (0–4095)
    acc_x: float                      # MPU6050 X-axis
    acc_y: float                      # MPU6050 Y-axis
    acc_z: float                      # MPU6050 Z-axis

@dataclass
class SessionConfig:
    subject_id: str                   # e.g. "S01"
    fast_baseline: bool               # --fast-baseline flag
    fullscreen: bool                  # --fullscreen flag
    window_size: tuple[int, int]      # (width, height)
    domain_filter: DomainID | None    # --domain flag (test single domain)
    session_start_unix_ts_ms: int       # Set once at session start
    random_seed: int                  # Logged for reproducibility
    hold_full_decision: bool = False  # True in main.py: a committed choice is held until the DECISION timer expires (C1)
    min_priming_s: int = 0            # Read floor before SPACE may skip priming (main.py: MIN_PRIMING_DURATION_S)
    min_active_epoch_s: int = 0       # PRIMING + DECISION + FEEDBACK lower bound (main.py: MIN_ACTIVE_EPOCH_S)
    inter_domain_rest_s: float = 30.0 # Wash-out between domains; main.py sets 60.0 for --extended-rest (ADR-B2)
    # The three exposure defaults are OFF only so unit tests can step the state machine instantly.
    # Every real session is built by main.py with them ON; --no-exposure-floor turns them off for development.

@dataclass(frozen=True)
class BridgeOptions:
    """Sensor-bridge selection parsed from the command line (main.py)."""
    mode: str                         # "auto" | "serial" | "stub" | "replay"
    port: str | None                  # --bridge-port: skip the scan and use this device
    source: Path | None               # --bridge-source: CSV file or directory of recordings (replay)
    follow: bool                      # --bridge-follow: tail a CSV that serial_reader.py is writing

@dataclass(frozen=True)
class SensorRow:
    """One validated stream row plus the host-side arrival time (sensor_stream.py)."""
    sample_idx: int
    timestamp_ms: int                 # Device clock (millis())
    unix_ts_ms: int                   # Host clock at arrival — the cross-stream join key
    pulse_raw: int
    gsr_raw: int
    acc_x: int
    acc_y: int
    acc_z: int

@dataclass(frozen=True)
class BridgeSetup:
    """What create_bridge() returns: the bridge plus a one-line status for the operator."""
    bridge: BridgeInterface
    mode: str                         # The mode actually in effect: "serial", "replay" or "stub"
    detail: str

@dataclass
class UIEffectState:
    """Aggregate per-frame effect state passed from engine to UIRenderer."""
    jitter_offset: tuple[int, int] = (0, 0)    # (dx, dy) pixel offset for text jitter
    vibration_offset: tuple[int, int] = (0, 0) # (dx, dy) pixel offset for screen vibration
    is_flashing: bool = False                  # True during 200ms MIST wrong-answer flash
    timer_bar_color: tuple[int, int, int] = COLOR_TIMER_GREEN  # Current RGB of the timer bar
```

---

## 3. CSV Schema — `events.csv`

| Column | Type | Description | Example |
|---|---|---|---|
| `unix_ts_ms` | `int` | Unix epoch milliseconds (join key with `serial_reader.py`) | `1724688000000` |
| `event_type` | `str` | `EventType.value` | `OPTION_SELECTED` |
| `domain` | `str` | `DomainID.value` or empty | `academic_pressure` |
| `scenario_id` | `str` | Scenario ID or empty | `academic_pressure_a` |
| `choice_data` | `str` (JSON) | JSON-encoded selection data or `{}` | `{"key": 2, "text": "Study harder"}` |
| `key_pressed` | `int\|""` | Key number (1–4) or empty | `2` |
| `option_index` | `int\|""` | 0-based option index or empty | `1` |
| `response_time_ms` | `int\|""` | ms from decision presented to keypress or empty. Measured on the monotonic clock; for MIST and BART rows it is cumulative from decision onset (per-item time is `metadata.item_rt_ms`). Resolution is one frame (≤16.7ms). | `4523` |
| `metadata` | `str` (JSON) | JSON-encoded dict of extra fields | `{"correct": true, "item_rt_ms": 2140, "item_limit_ms": 8000}` |

### Metadata Keys by Event (2026-10-02)

The 9 columns and the 22 `EventType` values are unchanged. These keys live inside the `metadata` JSON:

| Event | Keys |
|---|---|
| `SYNC_PULSE` | `bridge` (class name: `StubBridge`, `SerialBridge`, `ReplayBridge`), `audio_loaded`, `hold_full_decision`, `min_priming_s`, `min_active_epoch_s`, `inter_domain_rest_s` |
| `BASELINE_START` | `duration_s` |
| `OPTION_SELECTED` | `is_conforming` (peer_influence only) |
| `MATH_ANSWER` | `correct`, `item_rt_ms`, `item_limit_ms` (the adaptive countdown that applied to this item), `problem`; plus `timed_out: true` when the item ran out — that row has empty `key_pressed` and `option_index` |
| `BART_PUMP` | `value`, `item_rt_ms`, `pump` (1-based pump number), `burst_prob` (hazard this pump faced), `instability` |
| `BART_SECURE` | `value`, `item_rt_ms`, `pumps` (pumps taken), `next_burst_prob` (hazard that was declined) |
| `BART_BURST` | `pump` |
| `REWARD_CLAIM` | `value` |
| `DECEPTION_TRIGGER` | `mpu_var`, `threshold` |
| `CLOCK_ANOMALY` | `wall_delta_ms`, `frame_dt_ms`, `state` |
| `FOCUS_LOST`, `FOCUS_GAINED` | `state` |
| `REST_START` | `is_inter`, `duration_s` (30 or 60 for an inter-domain rest, 15 intra-domain) |
| `SESSION_END` | `scenarios_completed`; plus `aborted: true` and `state` when the session was ended with ESC/QUIT before debrief |

**Reconstructing the BART pressure curve:** the `BART_PUMP` rows of one scenario, in order, give `(pump, burst_prob, value, item_rt_ms)`. `item_rt_ms` is the latency since the previous accepted response (or since `DECISION_PRESENTED` for the first pump); it includes the 1.5 s pacing cooldown, so deliberation time is `item_rt_ms − 1500` for every pump after the first. A key pressed inside the cooldown is ignored and is not logged.

**MIST adaptation trace:** the sequence of `item_limit_ms` values across `MATH_ANSWER` rows is the difficulty trajectory for that participant.

### CSV Constraints
- **Header row:** Always written as first row.
- **Delimiter:** Comma (`,`).
- **Quoting:** `csv.QUOTE_MINIMAL` — only quote fields containing commas/newlines.
- **Line terminator:** `\n` (Unix-style, even on Windows).
- **Empty numerics:** Written as empty string `""`, never `null`, `None`, or `NaN`.
- **`metadata` column:** Always valid JSON. `{}` when no metadata.
- **Flush:** Every row is flushed immediately after write (`file.flush()`).

### Sensor Recording — `sensor_stream.csv`

Written by `SerialBridge` into the session folder only when the engine owns the serial port (integrated topology). The column order is the one `src/hardware/serial_reader.py` writes, so `hardware_loader.py` and `align_signals.py` read either file.

| Column | Type | Description |
|---|---|---|
| `sample_idx` | `int` | Firmware sample counter |
| `timestamp_ms` | `int` | Device clock (`millis()`) |
| `unix_ts_ms` | `int` | Host clock at arrival — join key with `events.csv` |
| `pulse_raw` | `int` | Raw PPG ADC value |
| `gsr_raw` | `int` | Raw GSR ADC value (0–4095) |
| `acc_x`, `acc_y`, `acc_z` | `int` | Raw MPU-6050 acceleration |

Line terminator `\n`; every row is flushed on write. Only rows that pass `parse_sensor_line()` are recorded.

**Accepted stream formats** (`parse_sensor_line(line, arrival_unix_ms) -> SensorRow | None`):

1. Firmware CSV — 7 integers: `sample_idx,timestamp_ms,pulse_raw,gsr_raw,acc_x,acc_y,acc_z`. `unix_ts_ms` is the arrival time.
2. Recorded CSV — 8 integers in the column order above. The recorded `unix_ts_ms` is kept.
3. JSON object — keys by name or alias: `sample_idx|idx|n`, `timestamp_ms|ts|t`, `pulse_raw|pulse|ppg|bvp`, `gsr_raw|gsr|eda`, `acc_x|ax`, `acc_y|ay`, `acc_z|az`, optional `unix_ts_ms`. `sample_idx` and `timestamp_ms` may be absent (−1 and 0). Any other key (for example a firmware-side `hr`) is ignored.

Rejected (returns `None`, counted in `rows_rejected`): empty lines, `#` comments, a header row, a wrong field count, non-numeric fields, JSON booleans, and non-finite numbers.

---

## 4. JSON Schema — `domain_order.json`

```json
{
  "subject_id": "S01",
  "session_start_unix_ts_ms": 1724688000000,
  "random_seed": 42,
  "domain_order": [
    "future_uncertainty",
    "academic_pressure",
    "social_evaluation",
    "peer_influence",
    "impulsivity_gratification",
    "risk_reward",
    "rule_ambiguity"
  ]
}
```

---

## 5. Function Signatures — Public API Contracts

### `main.py`

```python
SENSOR_RECORDING_NAME: str = "sensor_stream.csv"

def parse_cli(argv: list[str] | None = None) -> tuple[SessionConfig, BridgeOptions]:
    """Parse CLI arguments into the session configuration and the bridge selection.
    Required: --subject (str, pattern S\\d{2,3}; rejected by parser.error if it does not match).
    Optional: --fast-baseline (flag), --fullscreen / --no-fullscreen,
              --window-size WxH (str), --domain (DomainID value),
              --no-exposure-floor (flag, developer testing only),
              --extended-rest (flag: inter_domain_rest_s = 60.0 instead of 30.0),
              --bridge {auto,serial,stub,replay} (default auto), --bridge-port DEVICE,
              --bridge-source PATH (required for replay), --bridge-follow (flag).
    The returned config has hold_full_decision=True, min_priming_s=MIN_PRIMING_DURATION_S and
    min_active_epoch_s=MIN_ACTIVE_EPOCH_S unless --no-exposure-floor is given.
    Raises: SystemExit on invalid args (argparse default behavior).
    """

def parse_args() -> SessionConfig:
    """Compatibility wrapper: parse_cli()[0]."""

def main() -> None:
    """Entry point. Creates the sensor bridge BEFORE the window opens, initializes pygame,
    creates GameEngine(config, screen, bridge=...), calls run(), and always closes the bridge.
    A bridge that was required but is unavailable exits with status 2.
    Catches KeyboardInterrupt → clean shutdown.
    """
```

### `engine.py`, `engine_state.py`, `engine_input.py`, `engine_timer.py`

`GameEngine(EngineInputMixin, EngineTimerMixin)` lives in `engine.py` (`run()`, `_render()`). State, transitions and the exposure floors are in `EngineBase` (`engine_state.py`); input handlers in `EngineInputMixin`; per-frame updates in `EngineTimerMixin`. `SessionConfig` is defined in `engine_state.py` and re-exported by `engine.py`, so `from src.game.engine import GameEngine, SessionConfig` is unchanged.

```python
def session_output_dir(config: SessionConfig) -> Path:
    """outputs/game_logs/{subject_id}_{session_start_unix_ts_ms} — shared by the event log and the bridge recording."""

class GameEngine:
    def __init__(self, config: SessionConfig, screen: pygame.Surface,
                 bridge: BridgeInterface | None = None,
                 audio: AudioController | None = None,
                 logger: EventLogger | None = None) -> None:
        """Initialize all subsystems. Does NOT start the loop. bridge defaults to StubBridge."""

    def _exit_decision(self, next_state: EngineState) -> None:
        """Leave DECISION now, or keep the committed outcome on screen until the timer expires (C1)."""

    def _decision_floor_ms(self, scenario: Scenario) -> int:
        """Full decision window when config.hold_full_decision, else 0."""

    def _priming_floor_ms(self, scenario: Scenario) -> int:
        """max(min_priming_s, min_active_epoch_s - decision_duration_s - DEFAULT_CONSEQUENCE_DURATION_S, 0) in ms."""

    def _update_composure(self, dt_ms: int, scenario: Scenario) -> None:
        """4 Hz poll. Drop 0.15 only after COMPOSURE_DROP_CONSECUTIVE_SAMPLES supra-threshold
        samples and outside the COMPOSURE_DROP_COOLDOWN_S window; recover 0.05 per quiet sample."""

    def _monitor_clock(self, dt_ms: int) -> None:
        """Log CLOCK_ANOMALY on a frame stall or a wall-clock step beyond the threshold."""

    def _log_abort(self) -> None:
        """Write SESSION_END with aborted=true when the session ends before DEBRIEF."""

    def _mono_ms(self) -> int:
        """Monotonic ms clock for reaction-time intervals. unix_ts_ms stays wall-clock (join key)."""

    def run(self) -> None:
        """Main Pygame event loop. Blocks until session completes or ESC pressed.
        Handles all state transitions, input routing, and rendering.
        """

    def _transition_to(self, new_state: EngineState) -> None:
        """Validated state transition. Logs the transition as a GameEvent.
        Raises InvalidStateTransition if transition is not in VALID_TRANSITIONS.
        """

    def _handle_input(self, event: pygame.event.Event) -> None:
        """Route keyboard events to the appropriate state handler.
        Only processes KEYDOWN events. Ignores mouse events entirely.
        """

    def _update(self, dt_ms: int) -> None:
        """Per-frame update: timers, UI effects, audio triggers, bridge polling."""

    def _render(self) -> None:
        """Per-frame render: delegates to UIRenderer based on current state."""

    def _get_safe_scenario(self) -> Scenario | None:
        """Returns the currently active Scenario, or None outside the scenario loop."""

    def _tick_mist(self, dt_ms: int, scenario: Scenario) -> None:
        """Advance the MIST per-item countdown. A timed-out item is logged as MATH_ANSWER with
        key_pressed=None and metadata {correct: false, timed_out: true, ...} and triggers the flash."""

    def _shutdown(self) -> None:
        """Stop the drone, close the sensor bridge, close the event log."""

    # Input handlers return True only when the key was acted on. The per-item latency clock
    # (_last_response_mono_ms) restarts only from an accepted response.
    def _handle_standard_input(self, key: int, scenario: Scenario, now: int, rt_ms: int) -> bool: ...
    def _handle_mist_input(self, key: int, scenario: Scenario, now: int, rt_ms: int, item_rt_ms: int) -> bool: ...
    def _handle_bart_input(self, key: int, scenario: Scenario, now: int, rt_ms: int, item_rt_ms: int) -> bool:
        """Key 1 secures. Key 2 pumps only when runner.can_pump(); inside the cooldown it returns False."""
    def _handle_reward_input(self, key: int, scenario: Scenario, now: int, rt_ms: int) -> bool: ...
```

### `scenarios.py`

```python
def build_domain_registry() -> list[Domain]:
    """Constructs and returns the complete list of 7 Domains with 14 Scenarios.
    Pure function — no side effects.
    """

def get_domain_by_id(registry: list[Domain], domain_id: DomainID) -> Domain:
    """Lookup a domain by ID. Raises DomainNotFoundError if not found."""

def generate_math_problems(count: int = 4, difficulty: str = "medium") -> list[MathProblem]:
    """Generate arithmetic problems for MIST scenario.
    difficulty: 'easy' (2-digit), 'medium' (3-digit), 'hard' (4-digit).
    Returns list of MathProblem with 4 options each, one correct.
    """

# There is no pretest calibration function. MIST difficulty adapts during the run
# (MISTRunner, per-item countdown) — ADR-B3.
```

### `scenario_logic.py`

```python
class MISTRunner:
    item_limit_ms: int       # Current per-item countdown; starts at MIST_ITEM_LIMIT_START_MS
    item_elapsed_ms: int     # Time spent on the current item
    correct_count: int
    answered_count: int      # Includes timed-out items
    timeout_count: int

    def __init__(self, problems: list[MathProblem], total_duration_s: int) -> None: ...
    def handle_keypress(self, key: int) -> tuple[bool, bool]:
        """Returns (answer_was_correct, all_problems_done)."""
    def update(self, dt_ms: int) -> bool:
        """Advance the per-item countdown. Returns True when the current item has just timed out;
        the item is then scored incorrect and the next problem is presented."""
    def get_item_time_fraction(self) -> float:
        """1.0 down to 0.0 — share of the current item's countdown that remains."""
    def get_current_problem(self) -> MathProblem | None: ...
    def get_accuracy_pct(self) -> int: ...
    def get_peer_average_pct(self) -> int:
        """Always returns accuracy_pct + 15 (MIST manipulation).
        The engine caps the figure at 100 when it builds the consequence text."""
    def get_progress_fraction(self) -> float:
        """0.0 to 1.0 — participant's progress through the problem set."""
    def get_peer_progress_fraction(self) -> float:
        """Always slightly ahead of participant's progress."""
    # Adaptation rule (applied after every answer or timeout):
    #   MIST_ADAPT_STREAK consecutive correct   → item_limit_ms = max(MIN, round(limit × (1 − MIST_ADAPT_STEP)))
    #   MIST_ADAPT_STREAK consecutive incorrect → item_limit_ms = min(MAX, round(limit × (1 + MIST_ADAPT_STEP)))
    #   The streak counter resets after each adaptation and whenever the outcome changes.

class BARTRunner:
    def __init__(self, config: BARTConfig, seed: int | None = None, cooldown_ms: int = 0) -> None:
        """cooldown_ms paces successive pumps; 0 (the default) leaves the runner unpaced.
        The engine passes BART_PUMP_COOLDOWN_MS."""
    def burst_probability(self, pump_number: int) -> float:
        """Hazard of the 1-based pump: base + increment × (pump_number − 1), and 1.0 at max_pumps."""
    def next_burst_probability(self) -> float:
        """Hazard of the participant's next pump."""
    def can_pump(self) -> bool:
        """True when the task is live and the pacing cooldown has elapsed."""
    def update(self, dt_ms: int) -> None:
        """Advance the pacing cooldown."""
    def get_cooldown_fraction(self) -> float:
        """1.0 just after a pump down to 0.0 when the next pump is allowed."""
    def pump(self) -> tuple[int, bool]:
        """Press Key 2. Returns (new_total_value, did_burst)."""
    def secure(self) -> int:
        """Press Key 1. Returns final secured value."""
    def get_instability_fraction(self) -> float:
        """0.0 to 1.0 — pump_count / max_pumps, the visual risk gauge."""
    def get_pumps_remaining_after_burst(self) -> int:
        """How many further pumps would have survived, replayed from a copy of this runner's RNG state.
        The live generator is not consumed, so the consequence text states the true counterfactual."""

class RewardAccumulator:
    def __init__(self, config: RewardAccumulatorConfig, seed: int | None = None) -> None: ...
    def update(self, dt_ms: int) -> bool:
        """Called every frame. Returns True if collapse occurred."""
    def claim(self) -> int:
        """Returns current accumulated value at time of claim."""
    def get_current_value(self) -> int: ...
    def get_instability_fraction(self) -> float:
        """0.0 to 1.0 — visual instability indicator."""
    def has_collapsed(self) -> bool: ...

class DelayWaitRunner:
    def __init__(self, duration_s: int, display_text: str) -> None: ...
    def update(self, dt_ms: int) -> bool:
        """Returns True when wait period is complete."""
    def get_elapsed_fraction(self) -> float: ...
```

### `event_logger.py`

```python
class EventLogger:
    def __init__(self, output_dir: Path, subject_id: str) -> None:
        """Creates output directory if needed. Opens CSV. Writes header row."""

    def log_event(self, event: GameEvent) -> None:
        """Writes one CSV row. Calls flush() immediately. Thread-safe."""

    def save_domain_order(self, order: list[DomainID], seed: int, start_ms: int) -> None:
        """Writes domain_order.json to the same output directory."""

    def close(self) -> None:
        """Flush and close the CSV file handle. Idempotent."""
```

### `ui.py` (facade) and the UI modules

`UIRenderer(UIDomainSkins, UIScreens, UIPostWait)` is the only UI class callers import. Its methods are defined in `ui_core.py`, `ui_components.py`, `ui_screens.py`, `ui_post_wait.py`, `ui_domains.py` and one module per skin under `skins/`.

```python
class UIRenderer:
    def __init__(self, screen: pygame.Surface) -> None:
        """Load fonts, precompute layout rects."""

    def draw_id_input(self, current_text: str, error_msg: str | None) -> None: ...
    def draw_baseline(self, elapsed_s: float, total_s: float) -> None: ...
    def draw_priming(self, scenario: Scenario, elapsed_s: float, skip_available: bool = True) -> None:
        """Never renders scenario.paradigm or the domain name: the heading is the skin's setting
        (ui_screens.SETTING_LABELS). Shows the SPACE prompt only when skip_available."""
    def draw_decision(self, scenario: Scenario, time_remaining_s: float,
                      selected_index: int | None,
                      effects: UIEffectState,
                      mist_runner: MISTRunner | None,
                      bart_runner: BARTRunner | None,
                      reward_runner: RewardAccumulator | None,
                      composure_fraction: float | None) -> None: ...
    def draw_post_wait(self, text: str, elapsed_fraction: float) -> None: ...
    def draw_feedback(self, consequence_text: str, elapsed_s: float) -> None: ...
    def draw_rest(self, is_inter_domain: bool, time_remaining_s: float, total_s: float | None = None) -> None:
        """total_s, when given, draws the progress line of the rest."""
    def draw_debrief(self, total_duration_s: float, scenarios_completed: int) -> None: ...
    def draw_composure_bar(self, fraction: float | None, pos: tuple[int, int],
                           width: int | None = None, is_drone_active: bool = False) -> None:
        """fraction=None means no live telemetry: renders a STANDBY state, never a reading."""
    def set_last_choice(self, option_index: int) -> None:
        """Record the committed option so post-decision screens reflect it."""
    def _draw_text(self, text: str, font: pygame.font.Font, color: tuple[int, int, int],
                   pos: tuple[int, int], center: bool = False, center_y: bool = False,
                   midleft: bool = False, midright: bool = False,
                   max_width: int | None = None) -> pygame.Rect:
        """max_width steps down the same-family font ladder, then ellipsizes."""
    @staticmethod
    def _mix(color: tuple[int, int, int], toward: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
        """Blend a palette token toward a neutral (canvas or white). The hue is unchanged."""
    def _draw_key_badge(self, rect: pygame.Rect, label: str, selected: bool = False, enabled: bool = True) -> None:
        """Keyboard-key prompt: canvas plate, white label, Grigio border. selected inverts it
        (white plate, canvas ink); enabled=False draws it muted (BART pump key inside its cooldown)."""

# Every skin module defines one class with one method of this shape; it returns False when it
# cannot render (wrong runner), and draw_decision then falls back to the skinless layout.
def _draw_skin_<skin>(self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
                      effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
                      reward_runner: RewardAccumulator | None, composure_fraction: float | None) -> bool: ...
```

### `audio.py`

```python
class AudioController:
    def __init__(self, drone_path: Path) -> None:
        """Load the tension drone WAV. Raises AudioLoadError if missing."""

    def start_drone(self, fade_in_ms: int = 2000) -> None:
        """Begin playing drone on loop with fade-in. Idempotent if already playing."""

    def stop_drone(self, fade_out_ms: int = 500) -> None:
        """Stop drone with fade-out. Idempotent if not playing."""

    def pause(self) -> None:
        """Suspend the drone in place (window focus lost). No effect if not playing."""

    def resume(self) -> None:
        """Resume a drone suspended by pause(). No effect if not playing."""

    def is_playing(self) -> bool: ...
```

### `bridge_interface.py`

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class BridgeInterface(Protocol):
    def get_latest_sample(self) -> SensorSample | None:
        """Return the most recent unread sample. None if nothing new has arrived."""
        ...

    def get_mpu_variance(self) -> float | None:
        """Return rolling 1s variance of 3-axis acceleration magnitude sqrt(x^2+y^2+z^2).
        None when there is no data or the data is stale."""
        ...

    def close(self) -> None:
        """Release the port / file and stop any reader thread. Idempotent."""
        ...

class StubBridge:
    """No-op implementation for hardware-less testing."""
    def get_latest_sample(self) -> SensorSample | None:
        return None

    def get_mpu_variance(self) -> float | None:
        return None

    def close(self) -> None:
        return None
```

### `sensor_stream.py`, `sensor_replay.py`, `sensor_bridge.py`

All public names are importable from `src.game.sensor_bridge`.

```python
RECORD_FIELDNAMES: tuple[str, ...]            # The 8 recording columns (§3)
KNOWN_USB_SERIAL_VIDS: frozenset[int] = frozenset({0x10C4, 0x1A86, 0x0403, 0x303A})

def parse_sensor_line(line: str, arrival_unix_ms: int) -> SensorRow | None: ...

class SerialPortLike(Protocol):               # The slice of a pyserial port the bridge needs
    def readline(self) -> bytes: ...          # One line, or b"" on timeout
    def close(self) -> None: ...

PortOpener = Callable[[str, int], SerialPortLike]   # (device, baud) -> open port; raises OSError if busy

class StreamBridge:
    """Thread-safe latest-sample buffer and rolling accelerometer window."""
    rows_ingested: int
    rows_rejected: int
    gap_events: int                           # sample_idx discontinuities
    def __init__(self, clock_ms: Callable[[], int] | None = None) -> None: ...
    def get_latest_sample(self) -> SensorSample | None: ...
    def get_mpu_variance(self) -> float | None:
        """Population variance of the magnitudes received in the last BRIDGE_VARIANCE_WINDOW_MS.
        None with fewer than BRIDGE_MIN_WINDOW_SAMPLES samples, or when the newest sample is older
        than BRIDGE_STALE_AFTER_MS."""
    def close(self) -> None: ...

class SerialBridge(StreamBridge):
    error: str | None                         # Last port or recording failure, for the operator
    def __init__(self, port: SerialPortLike, device: str = "", baud: int = 0,
                 record_path: Path | None = None, clock_ms: Callable[[], int] | None = None) -> None:
        """Wrap an already-open port. record_path enables the sensor_stream.csv recording."""
    def read_once(self) -> bool:
        """Read and process one line. False when the port yielded nothing or failed."""
    def start(self) -> None:
        """Start the daemon reader thread. Idempotent."""
    def close(self) -> None:
        """Stop the reader, release the port and the recording. Idempotent."""

class ReplayBridge(StreamBridge):
    def __init__(self, source: Path, follow: bool = False, clock_ms: Callable[[], int] | None = None) -> None:
        """follow=False: replay a finished recording, paced by its own timestamps.
        follow=True: tail rows appended to a CSV that serial_reader.py is writing."""
    def advance(self) -> int: ...             # Replay mode: ingest every row that is due; returns the count
    def poll_follow(self) -> int: ...         # Follow mode: ingest complete new lines; a partial line is left for the next poll
    def is_finished(self) -> bool: ...
    def start(self) -> None: ...
    def close(self) -> None: ...

def load_recorded_rows(source: Path) -> list[SensorRow]: ...
def resolve_replay_source(source: Path) -> Path:
    """A file is returned as is; a directory resolves to its newest recorded_*.csv (else newest *.csv).
    Raises BridgeUnavailableError when nothing is found."""

@dataclass(frozen=True)
class PortInfo:
    device: str
    description: str
    vid: int

def pyserial_available() -> bool: ...
def list_candidate_ports(comports: Callable[[], Iterable[object]] | None = None) -> list[PortInfo]:
    """Serial ports whose USB vendor ID is in KNOWN_USB_SERIAL_VIDS. Empty when pyserial is missing."""
def open_serial_port(device: str, baud: int) -> SerialPortLike:
    """serial.Serial(device, baud, timeout=0.25) — the same open serial_reader.py performs."""
def probe_port(device: str, opener: PortOpener, bauds: Sequence[int] = BRIDGE_BAUD_CANDIDATES,
               timeout_s: float = BRIDGE_PROBE_TIMEOUT_S, min_valid_rows: int = BRIDGE_PROBE_VALID_ROWS,
               monotonic: Callable[[], float] = time.monotonic) -> tuple[SerialPortLike, int] | None:
    """Baud negotiation: (open port, baud) for the first rate that yields min_valid_rows valid rows.
    The port is handed back open so the board is not reset a second time. None when busy or silent."""

def create_bridge(mode: str, port: str | None = None, source: Path | None = None, follow: bool = False,
                  record_path: Path | None = None, opener: PortOpener | None = None,
                  comports: Callable[[], Iterable[object]] | None = None) -> BridgeSetup:
    """auto   → SerialBridge if an ESP32 answers, else StubBridge (never raises for missing hardware)
    serial → SerialBridge, or BridgeUnavailableError
    replay → ReplayBridge(resolve_replay_source(source), follow), or BridgeUnavailableError
    stub   → StubBridge
    Serial and replay bridges are returned already started."""
```

---

## 6. Custom Exceptions

```python
class PulseEngineError(Exception):
    """Base exception for all game engine errors."""

class InvalidStateTransition(PulseEngineError):
    """Raised when engine attempts a disallowed state transition."""
    def __init__(self, from_state: EngineState, to_state: EngineState) -> None: ...

class DomainNotFoundError(PulseEngineError):
    """Raised when a DomainID lookup fails against the registry."""
    def __init__(self, domain_id: str) -> None: ...

class ScenarioConfigError(PulseEngineError):
    """Raised when a Scenario dataclass has invalid/contradictory fields."""
    def __init__(self, scenario_id: str, detail: str) -> None: ...

class AudioLoadError(PulseEngineError):
    """Raised when tension_drone.wav cannot be loaded."""
    def __init__(self, path: str) -> None: ...

class BridgeUnavailableError(PulseEngineError):
    """Raised when a sensor bridge was explicitly required but cannot be established."""
    def __init__(self, detail: str) -> None: ...

class LoggerIOError(PulseEngineError):
    """Raised when CSV file cannot be opened or written."""
    def __init__(self, path: str, detail: str) -> None: ...
```

---

## 7. Systemic Constants (exact values)

```python
# --- Display ---
SCREEN_WIDTH: int = 1280
SCREEN_HEIGHT: int = 720
FPS: int = 60

# --- Timing (seconds) ---
BASELINE_DURATION_S: int = 180
FAST_BASELINE_DURATION_S: int = 10
INTRA_DOMAIN_REST_S: int = 15
INTER_DOMAIN_REST_S: int = 30           # Default wash-out between domains (ADR-B2)
INTER_DOMAIN_REST_EXTENDED_S: int = 60  # --extended-rest: full wash-out for clinical protocols
DEFAULT_CONSEQUENCE_DURATION_S: int = 4
DEFAULT_PRIMING_DURATION_S: int = 20    # Locked for all 14 scenarios (ADR-B3)
DEFAULT_DECISION_DURATION_S: int = 45   # Locked decision window for every scenario except the MIST run
MIST_DECISION_DURATION_S: int = 40      # MIST arithmetic run (academic_pressure_a)
MIN_PRIMING_DURATION_S: int = 8         # Briefing cannot be skipped before it can plausibly be read
MIN_ACTIVE_EPOCH_S: int = 60            # PRIMING + DECISION + FEEDBACK must span one 60s HRV feature window

# --- Audio ---
DRONE_VOLUME: float = 0.30
DRONE_FADE_IN_MS: int = 2000
DRONE_FADE_OUT_MS: int = 500
DRONE_TRIGGER_FRACTION: float = 0.333   # Start drone at this fraction of timer remaining

# --- UI Effects ---
JITTER_MAX_PX: int = 3
JITTER_MAX_HZ: float = 2.0
BUTTON_FLASH_DURATION_MS: int = 200
TIMER_BAR_AMBER_FRACTION: float = 0.333
TIMER_BAR_RED_FRACTION: float = 0.10
VIBRATION_MAX_PX: int = 2               # Displacement is bounded as a vector magnitude, not per axis
VIBRATION_MAX_HZ: float = 2.0

# --- Deception Metric & Composure Gating ---
DECEPTION_THRESHOLD_SIGMA: float = 1.5
COMPOSURE_BAR_UPDATE_HZ: float = 4.0    # Update composure bar 4× per second, not every frame
COMPOSURE_DROP_CONSECUTIVE_SAMPLES: int = 3   # Sustained tremor elevation (~0.75s at 4Hz)
COMPOSURE_DROP_COOLDOWN_S: float = 5.0         # Minimum interval between composure bar drops

# --- Skin-Specific Visual Effects (Safety Limits) ---
BRIGHTNESS_FLICKER_MAX_PCT: float = 5.0
BRIGHTNESS_FLICKER_MAX_HZ: float = 2.0        # WCAG safety cap <= 3Hz
NOTIFICATION_PULSE_HZ: float = 1.0
COMPASS_SPIN_MAX_RPM: float = 4.0             # Continuous slow rotation
PENDULUM_SWING_MAX_HZ: float = 1.0

# --- Clock Monitoring ---
CLOCK_JUMP_WARNING_THRESHOLD_MS: int = 50     # Flag non-monotonic jump via CLOCK_ANOMALY

# --- Sensor Bridge (ESP32 serial stream) ---
BRIDGE_BAUD_CANDIDATES: tuple[int, ...] = (115200,)  # Firmware is fixed at 115200; extend only if it changes
BRIDGE_PROBE_TIMEOUT_S: float = 3.0     # Covers an ESP32 auto-reset on port open
BRIDGE_PROBE_VALID_ROWS: int = 3        # Parseable rows required before a port is accepted
BRIDGE_VARIANCE_WINDOW_MS: int = 1000   # Rolling window for the accelerometer-magnitude variance
BRIDGE_MIN_WINDOW_SAMPLES: int = 20     # Below this the variance is not reported (about 0.3 s at 66.67 Hz)
BRIDGE_STALE_AFTER_MS: int = 1500       # No sample for this long means telemetry is lost

# --- MIST ---
MIST_PEER_ADVANTAGE_PCT: int = 15       # Fake peer average is always +15% higher
MIST_WRONG_FLASH_COLOR: tuple[int, int, int] = (218, 41, 28)  # Rosso Corsa
MIST_PROBLEM_COUNT: int = 4             # Problems stored on the Scenario dataclass
MIST_RUNTIME_PROBLEM_COUNT: int = 60    # Problems generated at DECISION entry so the window, not the item count, ends the task
MIST_ITEM_LIMIT_START_MS: int = 8000    # First per-item countdown
MIST_ITEM_LIMIT_MIN_MS: int = 3000      # Tightest the adaptive countdown may become
MIST_ITEM_LIMIT_MAX_MS: int = 12000     # Loosest the adaptive countdown may become
MIST_ADAPT_STEP: float = 0.10           # Countdown tightens/eases by this fraction per adaptation
MIST_ADAPT_STREAK: int = 2              # Consecutive correct (or incorrect) answers that trigger an adaptation
MIST_ITEM_BAR_RED_FRACTION: float = 0.25  # Item countdown bar turns Rosso below this remaining fraction

# --- BART ---
# Burst hazard on pump k is BASE + INCREMENT × (k − 1): 2% on the first pump rising to 41% on the
# fourteenth, with the fifteenth certain. Expected safe pumps are about 6.
BART_INITIAL_VALUE: int = 100
BART_INCREMENT: int = 50
BART_BURST_PROB_BASE: float = 0.02
BART_BURST_PROB_INCREMENT: float = 0.03
BART_MAX_PUMPS: int = 15
BART_PUMP_COOLDOWN_MS: int = 1500       # Each pump is a paced, deliberate decision (no key mashing)

# --- Reward Accumulator ---
REWARD_INITIAL_VALUE: int = 10
REWARD_GROWTH_RATE: float = 1.15        # Multiplier per second
REWARD_COLLAPSE_RANGE: tuple[int, int] = (20, 40)  # Collapse between 20–40s
REWARD_MAX_DISPLAY: int = 9999

# --- Colors (RGB) --- Ferrari Luxury-Automotive Editorial System (values from DESIGN-ferrari.md)
# Palette rule (ADR-B5): the six chromatic tokens below are the only chromatic colours the UI may
# draw. Every other surface, border, and label is a neutral grey (r == g == b). Rosso Corsa marks
# stress triggers, danger states, and timer expiry only; never a key prompt or the participant's selection.
COLOR_BG: tuple[int, int, int] = (24, 24, 24)                # #181818 Near-black canvas (never pure black)
COLOR_CARD_BG: tuple[int, int, int] = (48, 48, 48)           # #303030 Canvas elevated / surface-card
COLOR_TEXT_PRIMARY: tuple[int, int, int] = (255, 255, 255)   # #ffffff Ink / Display
COLOR_TEXT_SECONDARY: tuple[int, int, int] = (150, 150, 150) # #969696 Body / Grigio borders
COLOR_TEXT_MUTED: tuple[int, int, int] = (102, 102, 102)     # #666666 Muted caption
COLOR_PRIMARY_ROSSO: tuple[int, int, int] = (218, 41, 28)    # #da291c Rosso Corsa
COLOR_PRIMARY_ACTIVE: tuple[int, int, int] = (176, 30, 10)   # #b01e0a Rosso Corsa active (dimmed alert)
COLOR_SEMANTIC_WARNING: tuple[int, int, int] = (241, 58, 44) # #f13a2c Small alert text on dark surfaces
COLOR_ACCENT_CYAN: tuple[int, int, int] = (76, 152, 185)     # #4c98b9 Semantic info telemetry
COLOR_ACCENT_YELLOW: tuple[int, int, int] = (246, 229, 0)    # #f6e500 Ferrari yellow accent
COLOR_TIMER_GREEN: tuple[int, int, int] = (3, 144, 74)       # #03904a Semantic success
COLOR_TIMER_AMBER: tuple[int, int, int] = (246, 229, 0)      # #f6e500 Caution / telemetry standby
COLOR_TIMER_RED: tuple[int, int, int] = (218, 41, 28)        # #da291c Rosso Corsa / critical
COLOR_REST_GRADIENT_TOP: tuple[int, int, int] = (24, 24, 24)
COLOR_REST_GRADIENT_BOTTOM: tuple[int, int, int] = (14, 14, 14)
COLOR_HAIRLINE: tuple[int, int, int] = (48, 48, 48)          # #303030 Hairline divider
COLOR_HAIRLINE_SUBTLE: tuple[int, int, int] = (58, 58, 58)   # Subtle contrast divider
# COLOR_ACCENT_INDIGO (an alias of Rosso Corsa) was removed.

# --- Subject ID Validation ---
SUBJECT_ID_PATTERN: str = r"^S\d{2,3}$"   # S01–S999
```

---

## 8. Valid State Transitions (Adjacency List)

```python
VALID_TRANSITIONS: dict[EngineState, set[EngineState]] = {
    EngineState.INIT:       {EngineState.ID_INPUT},
    EngineState.ID_INPUT:   {EngineState.BASELINE},
    EngineState.BASELINE:   {EngineState.PRIMING},
    EngineState.PRIMING:    {EngineState.DECISION},
    EngineState.DECISION:   {EngineState.POST_WAIT, EngineState.FEEDBACK},
    EngineState.POST_WAIT:  {EngineState.FEEDBACK},
    EngineState.FEEDBACK:   {EngineState.INTRA_REST, EngineState.INTER_REST, EngineState.DEBRIEF},
    EngineState.INTRA_REST: {EngineState.PRIMING},
    EngineState.INTER_REST: {EngineState.PRIMING},
    EngineState.DEBRIEF:    set(),  # Terminal state
}
```
