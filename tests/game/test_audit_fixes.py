"""Regression tests for the gamification-engine audit fixes."""
from __future__ import annotations

import csv
import itertools
import math
import time
from pathlib import Path

import pygame

from src.game.constants import (
    COMPASS_SPIN_MAX_RPM,
    JITTER_MAX_HZ,
    JITTER_MAX_PX,
    MIN_ACTIVE_EPOCH_S,
    VIBRATION_MAX_HZ,
    VIBRATION_MAX_PX,
    DomainID,
    EngineState,
    EventType,
)
from src.game.engine import GameEngine, SessionConfig
from src.game.event_logger import EventLogger
from src.game.scenarios import generate_math_problems
from src.game.ui import UIRenderer
from src.game.ui_effects import ScreenVibration, TextJitter


def _state(engine: GameEngine) -> EngineState:
    """Read the state through a call: mypy would otherwise narrow the attribute across a transition."""
    return engine._current_state


class _FakeBridge:
    """Bridge returning a caller-controlled MPU variance."""

    def __init__(self, value: float | None) -> None:
        self.value: float | None = value
        self.closed: bool = False

    def get_latest_sample(self) -> None:
        return None

    def get_mpu_variance(self) -> float | None:
        return self.value

    def close(self) -> None:
        self.closed = True


def _engine(
    tmp_path: Path,
    domain: DomainID,
    hold: bool = False,
    priming_s: int = 0,
    epoch_s: int = 0,
    bridge: _FakeBridge | None = None,
) -> GameEngine:
    cfg = SessionConfig(
        subject_id="S01",
        fast_baseline=True,
        fullscreen=False,
        window_size=(1280, 720),
        domain_filter=domain,
        session_start_unix_ts_ms=int(time.time_ns() // 1_000_000),
        random_seed=42,
        hold_full_decision=hold,
        min_priming_s=priming_s,
        min_active_epoch_s=epoch_s,
    )
    return GameEngine(cfg, pygame.Surface((1280, 720)), bridge=bridge, logger=EventLogger(tmp_path, "S01"))


def _to_decision(engine: GameEngine, scenario_idx: int = 0) -> None:
    engine._transition_to(EngineState.ID_INPUT)
    engine._transition_to(EngineState.BASELINE)
    engine._current_scenario_idx = scenario_idx
    engine._transition_to(EngineState.PRIMING)
    engine._transition_to(EngineState.DECISION)


def _key(code: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": code, "unicode": ""})


def _events(tmp_path: Path) -> list[dict[str, str]]:
    with open(tmp_path / "events.csv", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _zero_crossing_hz(values: list[int], seconds: float) -> float:
    signs = [v for v in values if v != 0]
    crossings = sum(1 for a, b in itertools.pairwise(signs) if (a > 0) != (b > 0))
    return crossings / 2.0 / seconds


def test_decision_floor_holds_reflex_choice(tmp_path: Path) -> None:
    """Verify a reflex keypress is logged at once but DECISION is held until its timer expires (spec C1)."""
    engine = _engine(tmp_path, DomainID.RULE_AMBIGUITY, hold=True)
    _to_decision(engine)
    scenario = engine._get_safe_scenario()
    assert scenario is not None
    engine._handle_input(_key(pygame.K_2))
    assert _state(engine) == EngineState.DECISION
    assert engine._selected_option_index == 1

    # A second keypress cannot change the committed choice
    engine._handle_input(_key(pygame.K_1))
    assert engine._selected_option_index == 1

    engine._update((scenario.decision_duration_s - 1) * 1000)
    assert _state(engine) == EngineState.DECISION
    engine._update(1000)
    assert _state(engine) == EngineState.FEEDBACK
    engine._shutdown()
    rows = _events(tmp_path)
    selected = [r for r in rows if r["event_type"] == EventType.OPTION_SELECTED.value]
    assert len(selected) == 1
    assert selected[0]["key_pressed"] == "2"
    assert not any(r["event_type"] == EventType.TIMEOUT_NO_RESPONSE.value for r in rows)


def test_floor_applies_to_every_scenario(tmp_path: Path) -> None:
    """Verify no scenario can leave DECISION before its timer expires, whatever is pressed."""
    for domain in DomainID:
        for idx in (0, 1):
            engine = _engine(tmp_path / f"{domain.value}_{idx}", domain, hold=True)
            _to_decision(engine, idx)
            scenario = engine._get_safe_scenario()
            assert scenario is not None
            for _ in range(8):
                engine._handle_input(_key(pygame.K_1))
            engine._update((scenario.decision_duration_s - 1) * 1000)
            assert _state(engine) == EngineState.DECISION, f"{scenario.id} left early"
            engine._update(1000)
            assert _state(engine) != EngineState.DECISION, f"{scenario.id} did not advance on expiry"
            engine._shutdown()


def test_priming_floor_blocks_early_skip(tmp_path: Path) -> None:
    """Verify SPACE is ignored until the read floor, and until the 60 s active epoch is protected."""
    engine = _engine(tmp_path / "read", DomainID.PEER_INFLUENCE, priming_s=8)
    engine._transition_to(EngineState.ID_INPUT)
    engine._transition_to(EngineState.BASELINE)
    engine._transition_to(EngineState.PRIMING)
    engine._handle_input(_key(pygame.K_SPACE))
    assert _state(engine) == EngineState.PRIMING
    engine._update(8000)
    engine._handle_input(_key(pygame.K_SPACE))
    assert _state(engine) == EngineState.DECISION
    engine._shutdown()

    # MIST: 40 s decision + 4 s feedback leaves 16 s of priming owed to a 60 s epoch
    mist = _engine(tmp_path / "epoch", DomainID.ACADEMIC_PRESSURE, hold=True, priming_s=8, epoch_s=MIN_ACTIVE_EPOCH_S)
    mist._transition_to(EngineState.ID_INPUT)
    mist._transition_to(EngineState.BASELINE)
    mist._transition_to(EngineState.PRIMING)
    mist._update(15000)
    mist._handle_input(_key(pygame.K_SPACE))
    assert _state(mist) == EngineState.PRIMING
    mist._update(1000)
    mist._handle_input(_key(pygame.K_SPACE))
    assert _state(mist) == EngineState.DECISION
    mist._shutdown()


def test_delay_wait_branch_enters_post_wait(tmp_path: Path) -> None:
    """Verify only the 'request more time' option of the DELAY_WAIT scenario waits."""
    wait = _engine(tmp_path / "wait", DomainID.IMPULSIVITY_GRATIFICATION)
    _to_decision(wait, 1)
    wait._handle_input(_key(pygame.K_2))
    assert _state(wait) == EngineState.POST_WAIT
    wait._shutdown()

    submit = _engine(tmp_path / "submit", DomainID.IMPULSIVITY_GRATIFICATION)
    _to_decision(submit, 1)
    submit._handle_input(_key(pygame.K_1))
    assert _state(submit) == EngineState.FEEDBACK
    submit._shutdown()


def test_post_wait_reflects_chosen_fork(tmp_path: Path) -> None:
    """Verify the post-decision fork map lights the branch that was actually chosen."""
    engine = _engine(tmp_path, DomainID.FUTURE_UNCERTAINTY)
    _to_decision(engine, 0)
    engine._handle_input(_key(pygame.K_2))
    assert _state(engine) == EngineState.POST_WAIT
    assert engine.renderer._last_fork_choice == 1
    engine._shutdown()


def test_mist_runs_on_the_clock_and_caps_peer_figure(tmp_path: Path) -> None:
    """Verify four answers no longer end MIST and the peer average never exceeds 100%."""
    engine = _engine(tmp_path, DomainID.ACADEMIC_PRESSURE)
    _to_decision(engine, 0)
    assert engine._mist_runner is not None
    for problem in engine._mist_runner.problems[:6]:
        engine._handle_input(_key(pygame.K_1 + problem.correct_index))
    assert _state(engine) == EngineState.DECISION
    engine._update(41000)
    assert _state(engine) == EngineState.FEEDBACK
    assert "Peer average: 100%" in engine._consequence_text
    engine._shutdown()
    rows = _events(tmp_path)
    assert not any(r["event_type"] == EventType.TIMEOUT_NO_RESPONSE.value for r in rows)
    assert all("item_rt_ms" in r["metadata"] for r in rows if r["event_type"] == EventType.MATH_ANSWER.value)


def test_mist_answer_position_is_not_a_fixed_cycle() -> None:
    """Verify the correct answer no longer cycles through keys 1-2-3-4 in order."""
    positions = [p.correct_index for p in generate_math_problems(20)]
    assert positions != [i % 4 for i in range(20)]


def test_popup_blocks_decision_keys(tmp_path: Path) -> None:
    """Verify no choice can be committed while the briefing modal hides the options."""
    engine = _engine(tmp_path, DomainID.RULE_AMBIGUITY)
    _to_decision(engine)
    engine._handle_input(_key(pygame.K_TAB))
    engine._handle_input(_key(pygame.K_3))
    assert _state(engine) == EngineState.DECISION
    assert engine._selected_option_index is None
    engine._shutdown()


def test_composure_requires_sustained_motion_and_cooldown(tmp_path: Path) -> None:
    """Verify a single spike does not move the bar and sustained motion drops it once per cooldown."""
    bridge = _FakeBridge(0.2)
    engine = _engine(tmp_path, DomainID.SOCIAL_EVALUATION, bridge=bridge)
    _to_decision(engine, 0)

    bridge.value = 0.9
    engine._update(250)
    bridge.value = 0.2
    engine._update(250)
    assert engine._composure_fraction == 1.0

    bridge.value = 0.9
    for _ in range(8):
        engine._update(250)
    assert math.isclose(engine._composure_fraction, 0.85)
    engine._shutdown()
    triggers = [r for r in _events(tmp_path) if r["event_type"] == EventType.DECEPTION_TRIGGER.value]
    assert len(triggers) == 1


def test_composure_is_none_without_telemetry(tmp_path: Path) -> None:
    """Verify the stub bridge never produces a live composure reading."""
    engine = _engine(tmp_path, DomainID.SOCIAL_EVALUATION)
    _to_decision(engine, 0)
    engine._update(5000)
    assert engine._telemetry_live is False
    engine._render()
    engine._shutdown()


def test_clock_anomaly_and_focus_are_logged(tmp_path: Path) -> None:
    """Verify frame stalls and focus changes are logged, and timers freeze while unfocused (spec M3)."""
    engine = _engine(tmp_path, DomainID.RULE_AMBIGUITY)
    _to_decision(engine)
    engine._last_wall_ms = engine._now_ms()
    engine._monitor_clock(16)
    engine._monitor_clock(400)
    timer_before = engine._state_timer_ms
    engine._handle_input(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    engine._update(5000)
    assert engine._state_timer_ms == timer_before
    engine._handle_input(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
    engine._update(5000)
    assert engine._state_timer_ms == timer_before - 5000
    engine._log_abort()
    engine._shutdown()
    kinds = [r["event_type"] for r in _events(tmp_path)]
    assert kinds.count(EventType.CLOCK_ANOMALY.value) == 1
    assert EventType.FOCUS_LOST.value in kinds
    assert EventType.FOCUS_GAINED.value in kinds
    assert '"aborted": true' in _events(tmp_path)[-1]["metadata"]


def test_edited_subject_id_reaches_session_metadata(tmp_path: Path) -> None:
    """Verify an ID changed on the entry screen is written to domain_order.json."""
    engine = _engine(tmp_path, DomainID.RULE_AMBIGUITY)
    engine._transition_to(EngineState.ID_INPUT)
    engine._id_input_text = "S77"
    engine._handle_input(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "unicode": "\r"}))
    engine._shutdown()
    assert '"subject_id": "S77"' in (tmp_path / "domain_order.json").read_text(encoding="utf-8")


def test_effect_limits_are_vector_and_frequency_bounded() -> None:
    """Verify jitter and vibration respect displacement and frequency limits on both axes."""
    jitter = [TextJitter().get_offset(ms) for ms in range(10000)]
    assert max(math.hypot(dx, dy) for dx, dy in jitter) <= JITTER_MAX_PX
    assert _zero_crossing_hz([p[0] for p in jitter], 10.0) <= JITTER_MAX_HZ
    assert _zero_crossing_hz([p[1] for p in jitter], 10.0) <= JITTER_MAX_HZ

    vib = [ScreenVibration().get_offset(ms) for ms in range(10000)]
    assert VIBRATION_MAX_PX <= 2
    assert max(math.hypot(dx, dy) for dx, dy in vib) <= VIBRATION_MAX_PX
    assert _zero_crossing_hz([p[0] for p in vib], 10.0) <= VIBRATION_MAX_HZ
    assert _zero_crossing_hz([p[1] for p in vib], 10.0) <= VIBRATION_MAX_HZ
    assert COMPASS_SPIN_MAX_RPM <= 4.0


def test_text_width_guard_and_feedback_badge(screen: pygame.Surface) -> None:
    """Verify single-line text honours max_width and the suspension badge is scenario-specific."""
    renderer = UIRenderer(screen)
    long_label = "[ DELIBERATIVE CAUTION // ADHERES TO COMPLIANT REASONING ]"
    rect = renderer._draw_text(long_label, renderer.font_mono_small, (255, 255, 255), (640, 360), center=True, max_width=410)
    assert rect.width <= 410
    clipped = renderer._draw_text("W" * 200, renderer.font_small, (255, 255, 255), (640, 360), center=True, max_width=200)
    assert clipped.width <= 200

    drawn: list[str] = []
    original = renderer._draw_text

    def spy(text: str, *args: object, **kwargs: object) -> pygame.Rect:
        drawn.append(text)
        return original(text, *args, **kwargs)  # type: ignore[arg-type]

    renderer._draw_text = spy  # type: ignore[method-assign]
    renderer.draw_feedback("You accepted responsibility. The team received course credit while your record reflects the failure.", 1.0)
    assert not any("ACCOUNT SUSPENDED" in t for t in drawn)
    renderer.draw_feedback("Account suspended. All accumulated following lost.", 1.0)
    assert any("ACCOUNT SUSPENDED" in t for t in drawn)
