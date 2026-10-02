"""Systemic constants, enumerations, exceptions, and transition graph for Pulse."""
from __future__ import annotations

from enum import StrEnum

from src import domains as _domains

# Canonical domain identifiers live in src/domains.py; bound here so engine modules share one import site
DomainID = _domains.DomainID
CANONICAL_DOMAINS: list[str] = _domains.CANONICAL_DOMAINS


class EngineState(StrEnum):
    """Lifecycle states of the Pulse scenario state machine."""

    INIT = "INIT"
    ID_INPUT = "ID_INPUT"
    BASELINE = "BASELINE"
    PRIMING = "PRIMING"
    DECISION = "DECISION"
    POST_WAIT = "POST_WAIT"
    FEEDBACK = "FEEDBACK"
    INTRA_REST = "INTRA_REST"
    INTER_REST = "INTER_REST"
    DEBRIEF = "DEBRIEF"


class EventType(StrEnum):
    """Categorical types of game session events logged to CSV."""

    SYNC_PULSE = "SYNC_PULSE"
    BASELINE_START = "BASELINE_START"
    BASELINE_END = "BASELINE_END"
    DOMAIN_START = "DOMAIN_START"
    SCENARIO_PRIMING = "SCENARIO_PRIMING"
    DECISION_PRESENTED = "DECISION_PRESENTED"
    OPTION_SELECTED = "OPTION_SELECTED"
    TIMEOUT_NO_RESPONSE = "TIMEOUT_NO_RESPONSE"
    MATH_ANSWER = "MATH_ANSWER"
    BART_PUMP = "BART_PUMP"
    BART_SECURE = "BART_SECURE"
    BART_BURST = "BART_BURST"
    REWARD_CLAIM = "REWARD_CLAIM"
    REWARD_COLLAPSE = "REWARD_COLLAPSE"
    SCENARIO_END = "SCENARIO_END"
    REST_START = "REST_START"
    REST_END = "REST_END"
    SESSION_END = "SESSION_END"
    DECEPTION_TRIGGER = "DECEPTION_TRIGGER"
    FOCUS_LOST = "FOCUS_LOST"
    FOCUS_GAINED = "FOCUS_GAINED"
    CLOCK_ANOMALY = "CLOCK_ANOMALY"


class ScenarioType(StrEnum):
    """Mechanic paradigm variants governing scenario execution."""

    STANDARD_MCQ = "STANDARD_MCQ"
    MIST_ARITHMETIC = "MIST_ARITHMETIC"
    BART_ESCALATION = "BART_ESCALATION"
    REWARD_ACCUMULATOR = "REWARD_ACCUMULATOR"
    DELAY_WAIT = "DELAY_WAIT"


# --- Display ---
SCREEN_WIDTH: int = 1280
SCREEN_HEIGHT: int = 720
FPS: int = 60

# --- Timing (seconds) ---
BASELINE_DURATION_S: int = 180
FAST_BASELINE_DURATION_S: int = 10
INTRA_DOMAIN_REST_S: int = 15
INTER_DOMAIN_REST_S: int = 30  # Default wash-out between domains (ADR-B2)
INTER_DOMAIN_REST_EXTENDED_S: int = 60  # --extended-rest: full wash-out for clinical protocols
DEFAULT_CONSEQUENCE_DURATION_S: int = 4
DEFAULT_PRIMING_DURATION_S: int = 20  # Locked for all 14 scenarios (ADR-B3): immersive read-through, not a 5-10 s flash
DEFAULT_DECISION_DURATION_S: int = 45  # Locked decision window for every scenario except the MIST run
MIST_DECISION_DURATION_S: int = 40  # MIST arithmetic run (academic_pressure_a)
MIN_PRIMING_DURATION_S: int = 8  # Briefing cannot be skipped before it can plausibly be read
MIN_ACTIVE_EPOCH_S: int = 60  # PRIMING + DECISION + FEEDBACK must span one 60 s HRV feature window

# --- Audio ---
DRONE_VOLUME: float = 0.30
DRONE_FADE_IN_MS: int = 2000
DRONE_FADE_OUT_MS: int = 500
DRONE_TRIGGER_FRACTION: float = 0.333

# --- UI Effects ---
JITTER_MAX_PX: int = 3
JITTER_MAX_HZ: float = 2.0
BUTTON_FLASH_DURATION_MS: int = 200
TIMER_BAR_AMBER_FRACTION: float = 0.333
TIMER_BAR_RED_FRACTION: float = 0.10
VIBRATION_MAX_PX: int = 2
VIBRATION_MAX_HZ: float = 2.0

# --- Deception Metric & Composure Gating ---
DECEPTION_THRESHOLD_SIGMA: float = 1.5
COMPOSURE_BAR_UPDATE_HZ: float = 4.0
COMPOSURE_DROP_CONSECUTIVE_SAMPLES: int = 3
COMPOSURE_DROP_COOLDOWN_S: float = 5.0

# --- Skin-Specific Visual Effects (Safety Limits) ---
BRIGHTNESS_FLICKER_MAX_PCT: float = 5.0
BRIGHTNESS_FLICKER_MAX_HZ: float = 2.0
NOTIFICATION_PULSE_HZ: float = 1.0
COMPASS_SPIN_MAX_RPM: float = 4.0
PENDULUM_SWING_MAX_HZ: float = 1.0

# --- Clock Monitoring ---
CLOCK_JUMP_WARNING_THRESHOLD_MS: int = 50

# --- Sensor Bridge (ESP32 serial stream) ---
BRIDGE_BAUD_CANDIDATES: tuple[int, ...] = (115200,)  # Firmware is fixed at 115200; extend only if it changes
BRIDGE_PROBE_TIMEOUT_S: float = 3.0  # Covers an ESP32 auto-reset on port open
BRIDGE_PROBE_VALID_ROWS: int = 3  # Parseable rows required before a port is accepted
BRIDGE_VARIANCE_WINDOW_MS: int = 1000  # Rolling window for the accelerometer-magnitude variance
BRIDGE_MIN_WINDOW_SAMPLES: int = 20  # Below this the variance is not reported (about 0.3 s at 66.67 Hz)
BRIDGE_STALE_AFTER_MS: int = 1500  # No sample for this long means telemetry is lost

# --- MIST ---
MIST_PEER_ADVANTAGE_PCT: int = 15
MIST_WRONG_FLASH_COLOR: tuple[int, int, int] = (218, 41, 28)  # Rosso Corsa
MIST_PROBLEM_COUNT: int = 4
MIST_RUNTIME_PROBLEM_COUNT: int = 60  # Enough items that the window, not the item count, ends the task
MIST_ITEM_LIMIT_START_MS: int = 8000  # First per-item countdown
MIST_ITEM_LIMIT_MIN_MS: int = 3000  # Tightest the adaptive countdown may become
MIST_ITEM_LIMIT_MAX_MS: int = 12000  # Loosest the adaptive countdown may become
MIST_ADAPT_STEP: float = 0.10  # Countdown tightens/eases by this fraction per adaptation
MIST_ADAPT_STREAK: int = 2  # Consecutive correct (or incorrect) answers that trigger an adaptation
MIST_ITEM_BAR_RED_FRACTION: float = 0.25  # Item countdown bar turns Rosso below this remaining fraction

# --- BART ---
# Burst hazard on pump k is BASE + INCREMENT * (k - 1): 2% on the first pump rising to 41% on the
# fourteenth, with the fifteenth certain. Expected safe pumps are about 6, so risk escalates across
# the whole range instead of ending the task within three presses.
BART_INITIAL_VALUE: int = 100
BART_INCREMENT: int = 50
BART_BURST_PROB_BASE: float = 0.02
BART_BURST_PROB_INCREMENT: float = 0.03
BART_MAX_PUMPS: int = 15
BART_PUMP_COOLDOWN_MS: int = 1500  # Each pump is a paced, deliberate decision (no key mashing)

# --- Reward Accumulator ---
REWARD_INITIAL_VALUE: int = 10
REWARD_GROWTH_RATE: float = 1.15
REWARD_COLLAPSE_RANGE: tuple[int, int] = (20, 40)
REWARD_MAX_DISPLAY: int = 9999

# --- Colors (RGB) --- Ferrari Luxury-Automotive Editorial System (values from DESIGN-ferrari.md)
# Palette rule (ADR-B5): the six chromatic tokens below are the only chromatic colours the UI may
# draw. Every other surface, border, and label is a neutral grey (r == g == b), written either as a
# token or as a literal. Rosso Corsa marks stress triggers, danger states, and timer expiry only;
# it never marks a key prompt or the participant's own selection.
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

# --- Subject ID Validation ---
SUBJECT_ID_PATTERN: str = r"^S\d{2,3}$"

# --- Valid State Transitions (Adjacency List) ---
VALID_TRANSITIONS: dict[EngineState, set[EngineState]] = {
    EngineState.INIT: {EngineState.ID_INPUT},
    EngineState.ID_INPUT: {EngineState.BASELINE},
    EngineState.BASELINE: {EngineState.PRIMING},
    EngineState.PRIMING: {EngineState.DECISION},
    EngineState.DECISION: {EngineState.POST_WAIT, EngineState.FEEDBACK},
    EngineState.POST_WAIT: {EngineState.FEEDBACK},
    EngineState.FEEDBACK: {
        EngineState.INTRA_REST,
        EngineState.INTER_REST,
        EngineState.DEBRIEF,
    },
    EngineState.INTRA_REST: {EngineState.PRIMING},
    EngineState.INTER_REST: {EngineState.PRIMING},
    EngineState.DEBRIEF: set(),
}


# --- Custom Exceptions ---
class PulseEngineError(Exception):
    """Base exception for all game engine errors."""


class InvalidStateTransition(PulseEngineError):
    """Raised when engine attempts a disallowed state transition."""

    def __init__(self, from_state: EngineState, to_state: EngineState) -> None:
        """Store states and initialize message."""
        super().__init__(f"Invalid transition from {from_state} to {to_state}")
        self.from_state: EngineState = from_state
        self.to_state: EngineState = to_state


class DomainNotFoundError(PulseEngineError):
    """Raised when a DomainID lookup fails against the registry."""

    def __init__(self, domain_id: str) -> None:
        """Store domain ID and initialize message."""
        super().__init__(f"Domain not found in registry: {domain_id}")
        self.domain_id: str = domain_id


class ScenarioConfigError(PulseEngineError):
    """Raised when a Scenario dataclass has invalid or contradictory fields."""

    def __init__(self, scenario_id: str, detail: str) -> None:
        """Store scenario ID, detail, and initialize message."""
        super().__init__(f"Invalid scenario config for '{scenario_id}': {detail}")
        self.scenario_id: str = scenario_id
        self.detail: str = detail


class AudioLoadError(PulseEngineError):
    """Raised when tension_drone.wav cannot be loaded."""

    def __init__(self, path: str) -> None:
        """Store path and initialize message."""
        super().__init__(f"Failed to load audio asset from: {path}")
        self.path: str = path


class BridgeUnavailableError(PulseEngineError):
    """Raised when a sensor bridge was explicitly required but cannot be established."""

    def __init__(self, detail: str) -> None:
        """Store detail and initialize message."""
        super().__init__(f"Sensor bridge unavailable: {detail}")
        self.detail: str = detail


class LoggerIOError(PulseEngineError):
    """Raised when CSV file cannot be opened or written."""

    def __init__(self, path: str, detail: str) -> None:
        """Store path, detail, and initialize message."""
        super().__init__(f"File I/O error at '{path}': {detail}")
        self.path: str = path
        self.detail: str = detail
