"""Unit tests for GameEngine state transitions, input routing, and timing logic."""
from __future__ import annotations

import time
from pathlib import Path

import pygame
import pytest

from src.game.constants import (
    DomainID,
    EngineState,
    EventType,
    InvalidStateTransition,
    VALID_TRANSITIONS,
)
from src.game.engine import GameEngine, SessionConfig
from src.game.event_logger import EventLogger


def _make_engine(tmp_path: Path, domain: DomainID | None = None) -> GameEngine:
    screen = pygame.Surface((1280, 720))
    cfg = SessionConfig(
        subject_id="S01",
        fast_baseline=True,
        fullscreen=False,
        window_size=(1280, 720),
        domain_filter=domain,
        session_start_unix_ts_ms=int(time.time_ns() // 1_000_000),
        random_seed=42,
    )
    logger = EventLogger(tmp_path, "S01")
    return GameEngine(cfg, screen, logger=logger)


def test_engine_initial_state_and_valid_transition(tmp_path: Path) -> None:
    """Verify INIT state and valid state progression."""
    engine = _make_engine(tmp_path)
    assert engine._current_state == EngineState.INIT

    engine._transition_to(EngineState.ID_INPUT)
    assert engine._current_state == EngineState.ID_INPUT

    engine._transition_to(EngineState.BASELINE)
    assert engine._current_state == EngineState.BASELINE
    engine._shutdown()


def test_invalid_transitions_raise(tmp_path: Path) -> None:
    """Verify disallowed state transitions raise InvalidStateTransition."""
    engine = _make_engine(tmp_path)
    # Skipping states is disallowed
    with pytest.raises(InvalidStateTransition):
        engine._transition_to(EngineState.DEBRIEF)

    # Self transitions are disallowed
    with pytest.raises(InvalidStateTransition):
        engine._transition_to(EngineState.INIT)
    engine._shutdown()


def test_mouse_events_ignored(tmp_path: Path) -> None:
    """Verify mouse events do not affect state or cause exceptions."""
    engine = _make_engine(tmp_path)
    engine._transition_to(EngineState.ID_INPUT)

    mouse_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (100, 100), "button": 1})
    engine._handle_input(mouse_event)
    assert engine._current_state == EngineState.ID_INPUT
    engine._shutdown()


def test_domain_filtering(tmp_path: Path) -> None:
    """Verify --domain flag restricts presentation to single domain."""
    engine = _make_engine(tmp_path, domain=DomainID.ACADEMIC_PRESSURE)
    assert len(engine._domains) == 1
    assert engine._domains[0].id == DomainID.ACADEMIC_PRESSURE
    engine._shutdown()


def test_timeout_and_consequence_flow(tmp_path: Path) -> None:
    """Verify timer expiry triggers timeout consequence transition."""
    engine = _make_engine(tmp_path, domain=DomainID.ACADEMIC_PRESSURE)
    engine._transition_to(EngineState.ID_INPUT)
    engine._transition_to(EngineState.BASELINE)
    engine._transition_to(EngineState.PRIMING)
    engine._transition_to(EngineState.DECISION)
    assert engine._current_state == EngineState.DECISION

    # Advance decision timer to 0
    engine._update(50000)
    # academic_pressure_a has no post_wait -> transitions directly to FEEDBACK
    assert engine._current_state == EngineState.FEEDBACK
    engine._shutdown()


def test_keydown_option_selection_and_invalid_keys(tmp_path: Path) -> None:
    """Verify numeric keys select options and invalid keys are safely ignored."""
    engine = _make_engine(tmp_path, domain=DomainID.ACADEMIC_PRESSURE)
    engine._transition_to(EngineState.ID_INPUT)
    engine._transition_to(EngineState.BASELINE)
    # Fast forward to scenario B (standard MCQ)
    engine._current_scenario_idx = 1
    engine._transition_to(EngineState.PRIMING)
    engine._transition_to(EngineState.DECISION)
    assert engine._current_state == EngineState.DECISION

    # Invalid key 9 has no effect
    invalid_event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_9})
    engine._handle_input(invalid_event)
    assert engine._selected_option_index is None
    assert engine._current_state == EngineState.DECISION

    # Non-numeric key has no effect
    space_event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE})
    engine._handle_input(space_event)
    assert engine._selected_option_index is None
    assert engine._current_state == EngineState.DECISION

    # Valid key 1 selects option and transitions to FEEDBACK
    key1_event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_1})
    engine._handle_input(key1_event)
    assert engine._current_state == EngineState.FEEDBACK
    curr_scenario = engine._get_safe_scenario()
    assert curr_scenario is not None
    assert engine._consequence_text == curr_scenario.options[0].consequence_text
    engine._shutdown()


def test_esc_key_shuts_down_cleanly(tmp_path: Path) -> None:
    """Verify shutdown closes logger and disables running flag."""
    engine = _make_engine(tmp_path)
    engine._running = True
    engine._shutdown()
    assert engine._running is False
    assert engine.logger._closed is True


def test_domain_order_randomization(tmp_path: Path) -> None:
    """Verify distinct random seeds produce varied domain orders."""
    orders = []
    for s in range(10):
        cfg = SessionConfig(
            subject_id=f"S{s:02d}",
            fast_baseline=True,
            fullscreen=False,
            window_size=(1280, 720),
            domain_filter=None,
            session_start_unix_ts_ms=1000 + s,
            random_seed=s * 137,
        )
        sub_path = tmp_path / f"sub_{s}"
        logger = EventLogger(sub_path, cfg.subject_id)
        eng = GameEngine(cfg, pygame.Surface((1280, 720)), logger=logger)
        orders.append(tuple(d.id for d in eng._domains))
        eng._shutdown()

    # Across 10 distinct seeds, at least 2 distinct orders must exist
    assert len(set(orders)) > 1


def test_post_wait_isolation(tmp_path: Path) -> None:
    """Verify POST_WAIT state is entered exclusively for future_uncertainty."""
    # future_uncertainty enters POST_WAIT
    engine_fu = _make_engine(tmp_path / "fu", domain=DomainID.FUTURE_UNCERTAINTY)
    engine_fu._transition_to(EngineState.ID_INPUT)
    engine_fu._transition_to(EngineState.BASELINE)
    engine_fu._transition_to(EngineState.PRIMING)
    engine_fu._transition_to(EngineState.DECISION)
    engine_fu._handle_input(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_1}))
    assert engine_fu._current_state == EngineState.POST_WAIT
    engine_fu._shutdown()

    # academic_pressure skips POST_WAIT directly to FEEDBACK
    engine_acad = _make_engine(tmp_path / "acad", domain=DomainID.ACADEMIC_PRESSURE)
    engine_acad._current_scenario_idx = 1
    engine_acad._transition_to(EngineState.ID_INPUT)
    engine_acad._transition_to(EngineState.BASELINE)
    engine_acad._transition_to(EngineState.PRIMING)
    engine_acad._transition_to(EngineState.DECISION)
    engine_acad._handle_input(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_1}))
    assert engine_acad._current_state == EngineState.FEEDBACK
    engine_acad._shutdown()


def test_intra_and_inter_rest_intervals(tmp_path: Path) -> None:
    """Verify 15s intra-domain rest and 60s inter-domain rest intervals."""
    engine = _make_engine(tmp_path)
    engine._transition_to(EngineState.ID_INPUT)
    engine._transition_to(EngineState.BASELINE)
    engine._transition_to(EngineState.PRIMING)
    engine._transition_to(EngineState.DECISION)
    engine._transition_to(EngineState.FEEDBACK)

    # After Scenario A feedback expires -> INTRA_REST (15s)
    engine._update(4500)
    assert engine._current_state == EngineState.INTRA_REST
    assert engine._state_timer_ms == 15000

    # Advance rest timer -> Scenario B PRIMING
    engine._update(16000)
    assert engine._current_state == EngineState.PRIMING
    assert engine._current_scenario_idx == 1

    # Advance through Scenario B
    engine._transition_to(EngineState.DECISION)
    engine._transition_to(EngineState.FEEDBACK)
    # After Scenario B feedback expires -> INTER_REST (60s)
    engine._update(4500)
    assert engine._current_state == EngineState.INTER_REST
    assert engine._state_timer_ms == 60000
    engine._shutdown()


def test_debrief_after_all_domains(tmp_path: Path) -> None:
    """Verify completion of all domains leads directly to DEBRIEF state."""
    engine = _make_engine(tmp_path, domain=DomainID.RULE_AMBIGUITY)
    engine._current_scenario_idx = 1
    engine._transition_to(EngineState.ID_INPUT)
    engine._transition_to(EngineState.BASELINE)
    engine._transition_to(EngineState.PRIMING)
    engine._transition_to(EngineState.DECISION)
    engine._transition_to(EngineState.FEEDBACK)

    # Feedback on final scenario of final domain expires -> DEBRIEF
    engine._update(4500)
    assert engine._current_state == EngineState.DEBRIEF
    assert VALID_TRANSITIONS[engine._current_state] == set()
    engine._shutdown()
