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
    burst_probability_base: float     # Starting burst probability (e.g. 0.05)
    burst_probability_increment: float # Added to burst prob after each pump (e.g. 0.08)
    max_pumps: int                    # Hard cap (e.g. 15)

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
    paradigm: str                     # e.g. "MIST (Dedovic et al., 2005)"
    priming_text: str                 # Full priming message
    priming_duration_s: int           # 8 or 10
    decision_duration_s: int          # 35–45
    consequence_duration_s: int       # 4
    options: list[Option]             # 2–4 options
    scenario_type: ScenarioType       # Determines which runner to use
    has_deception_metric: bool = False # True only for social_evaluation scenarios
    has_post_wait: bool = False       # True only for future_uncertainty scenarios
    post_wait_duration_s: int = 0     # 10 or 12 for future_uncertainty, 0 otherwise
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
    response_time_ms: int | None      # ms from DECISION_PRESENTED to selection, or None
    metadata: dict[str, str | int | float | bool]  # Arbitrary k/v (scenario-specific data)

@dataclass
class SensorSample:
    """Produced by the serial bridge. The game engine consumes these read-only."""
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

@dataclass
class UIEffectState:
    """Aggregate per-frame effect state passed from engine to UIRenderer."""
    jitter_offset: tuple[int, int] = (0, 0)    # (dx, dy) pixel offset for text jitter
    vibration_offset: tuple[int, int] = (0, 0) # (dx, dy) pixel offset for screen vibration
    is_flashing: bool = False                  # True during 200ms MIST wrong-answer flash
    timer_bar_color: tuple[int, int, int] = (34, 197, 94)  # Current RGB of the timer bar
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
| `response_time_ms` | `int\|""` | ms from decision presented to keypress or empty | `4523` |
| `metadata` | `str` (JSON) | JSON-encoded dict of extra fields | `{"accuracy_pct": 50, "peer_avg": 65}` |

### CSV Constraints
- **Header row:** Always written as first row.
- **Delimiter:** Comma (`,`).
- **Quoting:** `csv.QUOTE_MINIMAL` — only quote fields containing commas/newlines.
- **Line terminator:** `\n` (Unix-style, even on Windows).
- **Empty numerics:** Written as empty string `""`, never `null`, `None`, or `NaN`.
- **`metadata` column:** Always valid JSON. `{}` when no metadata.
- **Flush:** Every row is flushed immediately after write (`file.flush()`).

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
def parse_args() -> SessionConfig:
    """Parse CLI arguments. Returns a fully populated SessionConfig.
    Required: --subject (str, pattern S\\d{2,3}).
    Optional: --fast-baseline (flag), --fullscreen (flag),
              --window-size WxH (str), --domain (DomainID value).
    Raises: SystemExit on invalid args (argparse default behavior).
    """

def main() -> None:
    """Entry point. Calls parse_args(), initializes pygame, creates GameEngine, calls run().
    Catches KeyboardInterrupt → clean shutdown.
    """
```

### `engine.py`

```python
class GameEngine:
    def __init__(self, config: SessionConfig, screen: pygame.Surface) -> None:
        """Initialize all subsystems. Does NOT start the loop."""

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

    def _get_current_scenario(self) -> Scenario:
        """Returns the currently active Scenario. Raises if not in a scenario state."""

    def _advance_scenario(self) -> None:
        """Move to next scenario or next domain. Determines rest type."""
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

def calibrate_mist_difficulty(pretest_correct: int, pretest_total: int = 3) -> str:
    """Calibrate starting difficulty tier for MIST arithmetic based on 3-problem pretest.
    Returns 'hard' (>=67%), 'medium' (34-66%), or 'easy' (<=33%).
    """
```

### `scenario_logic.py`

```python
class MISTRunner:
    def __init__(self, problems: list[MathProblem], total_duration_s: int) -> None: ...
    def handle_keypress(self, key: int) -> tuple[bool, bool]:
        """Returns (answer_was_correct, all_problems_done)."""
    def get_current_problem(self) -> MathProblem | None: ...
    def get_accuracy_pct(self) -> int: ...
    def get_peer_average_pct(self) -> int:
        """Always returns accuracy_pct + 15 (MIST manipulation)."""
    def get_progress_fraction(self) -> float:
        """0.0 to 1.0 — participant's progress through the problem set."""
    def get_peer_progress_fraction(self) -> float:
        """Always slightly ahead of participant's progress."""

class BARTRunner:
    def __init__(self, config: BARTConfig) -> None: ...
    def pump(self) -> tuple[int, bool]:
        """Press Key 2. Returns (new_total_value, did_burst).
        Burst probability increases with each pump.
        """
    def secure(self) -> int:
        """Press Key 1. Returns final secured value."""
    def get_instability_fraction(self) -> float:
        """0.0 to 1.0 — visual instability gauge level."""
    def get_pumps_remaining_after_burst(self) -> int:
        """How many more pumps were possible after the player stopped (for consequence)."""

class RewardAccumulator:
    def __init__(self, config: RewardAccumulatorConfig) -> None: ...
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

### `ui.py`

```python
class UIRenderer:
    def __init__(self, screen: pygame.Surface) -> None:
        """Load fonts, precompute layout rects."""

    def draw_id_input(self, current_text: str, error_msg: str | None) -> None: ...
    def draw_baseline(self, elapsed_s: float, total_s: float) -> None: ...
    def draw_priming(self, scenario: Scenario, elapsed_s: float) -> None: ...
    def draw_decision(self, scenario: Scenario, time_remaining_s: float,
                      selected_index: int | None,
                      effects: UIEffectState,
                      mist_runner: MISTRunner | None,
                      bart_runner: BARTRunner | None,
                      reward_runner: RewardAccumulator | None,
                      composure_fraction: float | None) -> None: ...
    def draw_post_wait(self, text: str, elapsed_fraction: float) -> None: ...
    def draw_feedback(self, consequence_text: str, elapsed_s: float) -> None: ...
    def draw_rest(self, is_inter_domain: bool, time_remaining_s: float) -> None: ...
    def draw_debrief(self, total_duration_s: float, scenarios_completed: int) -> None: ...
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

    def is_playing(self) -> bool: ...
```

### `bridge_interface.py`

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class BridgeInterface(Protocol):
    def get_latest_sample(self) -> SensorSample | None:
        """Drain queue, return most recent sample. None if queue empty."""
        ...

    def get_mpu_variance(self) -> float | None:
        """Return rolling 1s variance of 3-axis acceleration magnitude sqrt(x^2+y^2+z^2). None if no data."""
        ...

class StubBridge:
    """No-op implementation for hardware-less testing."""
    def get_latest_sample(self) -> SensorSample | None:
        return None

    def get_mpu_variance(self) -> float | None:
        return None
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
INTER_DOMAIN_REST_S: int = 60
DEFAULT_CONSEQUENCE_DURATION_S: int = 4
DEFAULT_PRIMING_DURATION_S: int = 8

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
VIBRATION_MAX_PX: int = 3

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

# --- MIST ---
MIST_PEER_ADVANTAGE_PCT: int = 15       # Fake peer average is always +15% higher
MIST_WRONG_FLASH_COLOR: tuple[int, int, int] = (220, 50, 50)
MIST_PROBLEM_COUNT: int = 4

# --- BART ---
BART_INITIAL_VALUE: int = 100
BART_INCREMENT: int = 50
BART_BURST_PROB_BASE: float = 0.05
BART_BURST_PROB_INCREMENT: float = 0.08
BART_MAX_PUMPS: int = 15

# --- Reward Accumulator ---
REWARD_INITIAL_VALUE: int = 10
REWARD_GROWTH_RATE: float = 1.15        # Multiplier per second
REWARD_COLLAPSE_RANGE: tuple[int, int] = (20, 40)  # Collapse between 20–40s
REWARD_MAX_DISPLAY: int = 9999

# --- Colors (RGB) ---
COLOR_BG: tuple[int, int, int] = (18, 18, 24)          # Deep slate
COLOR_CARD_BG: tuple[int, int, int] = (30, 30, 42)     # Card background
COLOR_TEXT_PRIMARY: tuple[int, int, int] = (230, 230, 240)
COLOR_TEXT_SECONDARY: tuple[int, int, int] = (160, 160, 180)
COLOR_ACCENT_INDIGO: tuple[int, int, int] = (99, 102, 241)
COLOR_ACCENT_CYAN: tuple[int, int, int] = (34, 211, 238)
COLOR_TIMER_GREEN: tuple[int, int, int] = (34, 197, 94)
COLOR_TIMER_AMBER: tuple[int, int, int] = (245, 158, 11)
COLOR_TIMER_RED: tuple[int, int, int] = (239, 68, 68)
COLOR_REST_GRADIENT_TOP: tuple[int, int, int] = (15, 23, 42)
COLOR_REST_GRADIENT_BOTTOM: tuple[int, int, int] = (30, 41, 59)

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
