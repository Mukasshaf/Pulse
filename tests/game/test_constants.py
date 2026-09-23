"""Unit tests for constants, enumerations, and state transition graph."""
from __future__ import annotations

from enum import StrEnum

from src.game.constants import (
    BRIGHTNESS_FLICKER_MAX_HZ,
    COMPASS_SPIN_MAX_RPM,
    DRONE_VOLUME,
    FPS,
    JITTER_MAX_PX,
    NOTIFICATION_PULSE_HZ,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    VALID_TRANSITIONS,
    DomainID,
    DomainNotFoundError,
    EngineState,
    EventType,
    InvalidStateTransition,
    LoggerIOError,
    PulseEngineError,
    ScenarioConfigError,
    ScenarioType,
)


def test_enums_are_str_enum() -> None:
    """Verify all categorical enumerations subclass StrEnum."""
    assert issubclass(EngineState, StrEnum)
    assert issubclass(EventType, StrEnum)
    assert issubclass(ScenarioType, StrEnum)
    assert issubclass(DomainID, StrEnum)


def test_enum_member_counts() -> None:
    """Verify exact count of enum members."""
    assert len(DomainID) == 7
    assert len(EngineState) == 10
    assert len(ScenarioType) == 5
    assert len(EventType) == 22


def test_valid_transitions_completeness() -> None:
    """Verify transition graph defines entries for all states and debrief is terminal."""
    assert set(VALID_TRANSITIONS.keys()) == set(EngineState)
    for state, targets in VALID_TRANSITIONS.items():
        assert state not in targets, f"Self-transition detected for state {state}"
    assert VALID_TRANSITIONS[EngineState.DEBRIEF] == set()


def test_systemic_constants_bounds() -> None:
    """Verify systemic bounds and hardware safety constants."""
    assert isinstance(SCREEN_WIDTH, int)
    assert isinstance(SCREEN_HEIGHT, int)
    assert isinstance(FPS, int)
    assert JITTER_MAX_PX <= 3
    assert DRONE_VOLUME <= 0.30
    assert BRIGHTNESS_FLICKER_MAX_HZ <= 2.0
    assert NOTIFICATION_PULSE_HZ <= 1.0
    assert COMPASS_SPIN_MAX_RPM <= 4.0


def test_exception_hierarchy() -> None:
    """Verify all custom exceptions inherit from PulseEngineError."""
    assert issubclass(InvalidStateTransition, PulseEngineError)
    assert issubclass(DomainNotFoundError, PulseEngineError)
    assert issubclass(ScenarioConfigError, PulseEngineError)
    assert issubclass(LoggerIOError, PulseEngineError)
