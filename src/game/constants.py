"""Systemic constants, enumerations, exceptions, and transition graph for Pulse."""
from __future__ import annotations

from enum import StrEnum


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

from src.domains import DomainID, CANONICAL_DOMAINS


# --- Display ---
SCREEN_WIDTH: int = 1280
SCREEN_HEIGHT: int = 720
FPS: int = 60

# --- Timing (seconds) ---
BASELINE_DURATION_S: int = 180
FAST_BASELINE_DURATION_S: int = 10
INTRA_DOMAIN_REST_S: int = 15
INTER_DOMAIN_REST_S: int = 30
DEFAULT_CONSEQUENCE_DURATION_S: int = 4
DEFAULT_PRIMING_DURATION_S: int = 20

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
VIBRATION_MAX_PX: int = 3

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

# --- MIST ---
MIST_PEER_ADVANTAGE_PCT: int = 15
MIST_WRONG_FLASH_COLOR: tuple[int, int, int] = (218, 41, 28)  # Rosso Corsa
MIST_PROBLEM_COUNT: int = 4

# --- BART ---
BART_INITIAL_VALUE: int = 100
BART_INCREMENT: int = 50
BART_BURST_PROB_BASE: float = 0.05
BART_BURST_PROB_INCREMENT: float = 0.08
BART_MAX_PUMPS: int = 15

# --- Reward Accumulator ---
REWARD_INITIAL_VALUE: int = 10
REWARD_GROWTH_RATE: float = 1.15
REWARD_COLLAPSE_RANGE: tuple[int, int] = (20, 40)
REWARD_MAX_DISPLAY: int = 9999

# --- Colors (RGB) --- Ferrari Luxury-Automotive Editorial System
COLOR_BG: tuple[int, int, int] = (24, 24, 24)                # #181818 Near-black canvas
COLOR_CARD_BG: tuple[int, int, int] = (48, 48, 48)           # #303030 Canvas elevated / surface-card
COLOR_TEXT_PRIMARY: tuple[int, int, int] = (255, 255, 255)   # #ffffff Ink / Display
COLOR_TEXT_SECONDARY: tuple[int, int, int] = (150, 150, 150) # #969696 Body
COLOR_TEXT_MUTED: tuple[int, int, int] = (102, 102, 102)     # #666666 Muted caption
COLOR_PRIMARY_ROSSO: tuple[int, int, int] = (218, 41, 28)    # #da291c Rosso Corsa
COLOR_PRIMARY_ACTIVE: tuple[int, int, int] = (176, 30, 10)   # #b01e0a Rosso Corsa active
COLOR_ACCENT_CYAN: tuple[int, int, int] = (76, 152, 185)     # #4c98b9 Semantic info telemetry
COLOR_ACCENT_YELLOW: tuple[int, int, int] = (246, 229, 0)    # #f6e500 Ferrari yellow accent
COLOR_TIMER_GREEN: tuple[int, int, int] = (3, 144, 74)       # #03904a Semantic success
COLOR_TIMER_AMBER: tuple[int, int, int] = (246, 229, 0)      # #f6e500 Semantic warning / yellow
COLOR_TIMER_RED: tuple[int, int, int] = (218, 41, 28)        # #da291c Rosso Corsa / critical
COLOR_REST_GRADIENT_TOP: tuple[int, int, int] = (24, 24, 24)
COLOR_REST_GRADIENT_BOTTOM: tuple[int, int, int] = (14, 14, 14)
COLOR_HAIRLINE: tuple[int, int, int] = (48, 48, 48)          # #303030 Hairline divider
COLOR_HAIRLINE_SUBTLE: tuple[int, int, int] = (58, 58, 58)   # Subtle contrast divider
COLOR_ACCENT_INDIGO: tuple[int, int, int] = (218, 41, 28)    # Alias to Rosso Corsa for backwards compatibility

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


class LoggerIOError(PulseEngineError):
    """Raised when CSV file cannot be opened or written."""

    def __init__(self, path: str, detail: str) -> None:
        """Store path, detail, and initialize message."""
        super().__init__(f"File I/O error at '{path}': {detail}")
        self.path: str = path
        self.detail: str = detail
