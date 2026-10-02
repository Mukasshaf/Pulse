"""Engine-level tests for session options, the sensor-bridge lifecycle, and the MIST/BART paradigms."""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pygame
import pytest

from src.game.constants import (
    BART_BURST_PROB_BASE,
    BART_BURST_PROB_INCREMENT,
    BART_PUMP_COOLDOWN_MS,
    COLOR_PRIMARY_ROSSO,
    INTER_DOMAIN_REST_EXTENDED_S,
    INTER_DOMAIN_REST_S,
    MIN_ACTIVE_EPOCH_S,
    MIN_PRIMING_DURATION_S,
    MIST_ITEM_BAR_RED_FRACTION,
    MIST_ITEM_LIMIT_START_MS,
    DomainID,
    EngineState,
    EventType,
)
from src.game.engine import GameEngine, SessionConfig
from src.game.event_logger import EventLogger
from src.game.main import parse_cli
from src.game.scenario_logic import BARTRunner, MISTRunner
from src.game.scenarios import Domain
from src.game.ui import UIRenderer
from src.game.ui_effects import UIEffectState


def _state(engine: GameEngine) -> EngineState:
    """Read the state through a call: mypy would otherwise narrow the attribute across a transition."""
    return engine._current_state


class _FakeBridge:
    """Bridge returning a caller-controlled MPU variance and recording its own shutdown."""

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
    rest_s: float | None = None,
    bridge: _FakeBridge | None = None,
    seed: int = 42,
) -> GameEngine:
    cfg = SessionConfig(
        subject_id="S01",
        fast_baseline=True,
        fullscreen=False,
        window_size=(1280, 720),
        domain_filter=domain,
        session_start_unix_ts_ms=int(time.time_ns() // 1_000_000),
        random_seed=seed,
    )
    if rest_s is not None:
        cfg.inter_domain_rest_s = rest_s
    return GameEngine(cfg, pygame.Surface((1280, 720)), bridge=bridge, logger=EventLogger(tmp_path, "S01"))


def _to_decision(engine: GameEngine, scenario_idx: int = 0) -> None:
    engine._transition_to(EngineState.ID_INPUT)
    engine._transition_to(EngineState.BASELINE)
    engine._current_scenario_idx = scenario_idx
    engine._transition_to(EngineState.PRIMING)
    engine._transition_to(EngineState.DECISION)


def _key(code: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": code, "unicode": ""})


def _rows(tmp_path: Path, event_type: EventType) -> list[dict[str, str]]:
    with open(tmp_path / "events.csv", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row["event_type"] == event_type.value]


def test_inter_domain_rest_default_and_extended(tmp_path: Path) -> None:
    """Verify the wash-out between domains is 30 s by default and 60 s when extended."""
    for folder, rest_s, expected_ms in (("default", None, INTER_DOMAIN_REST_S * 1000), ("extended", float(INTER_DOMAIN_REST_EXTENDED_S), 60000)):
        engine = _engine(tmp_path / folder, DomainID.RULE_AMBIGUITY, rest_s=rest_s)
        engine._domains = engine._domains * 2  # a second domain so the last scenario is followed by INTER_REST
        _to_decision(engine, 1)
        engine._transition_to(EngineState.FEEDBACK)
        engine._update(4500)
        assert _state(engine) is EngineState.INTER_REST
        assert engine._state_timer_ms == expected_ms
        engine._shutdown()
        rest = _rows(tmp_path / folder, EventType.REST_START)
        assert json.loads(rest[-1]["metadata"]) == {"is_inter": True, "duration_s": expected_ms / 1000}
        sync = _rows(tmp_path / folder, EventType.SYNC_PULSE)
        assert json.loads(sync[0]["metadata"])["inter_domain_rest_s"] == expected_ms / 1000


def test_cli_defaults_enable_every_guarantee_and_flags_override() -> None:
    """Verify a plain launch is a full-protocol session and each flag maps to its option."""
    config, bridge = parse_cli(["--subject", "S01"])
    assert config.hold_full_decision is True
    assert config.min_priming_s == MIN_PRIMING_DURATION_S
    assert config.min_active_epoch_s == MIN_ACTIVE_EPOCH_S
    assert config.inter_domain_rest_s == float(INTER_DOMAIN_REST_S)
    assert (bridge.mode, bridge.port, bridge.source, bridge.follow) == ("auto", None, None, False)

    config, bridge = parse_cli([
        "--subject", "S12", "--extended-rest", "--no-exposure-floor",
        "--bridge", "replay", "--bridge-source", "data/hardware/raw/HW01", "--bridge-follow", "--bridge-port", "COM3",
    ])
    assert config.inter_domain_rest_s == float(INTER_DOMAIN_REST_EXTENDED_S)
    assert config.hold_full_decision is False
    assert (config.min_priming_s, config.min_active_epoch_s) == (0, 0)
    assert bridge.mode == "replay" and bridge.follow is True and bridge.port == "COM3"
    assert bridge.source == Path("data/hardware/raw/HW01")

    for bad_argv in (["--subject", "bob"], ["--subject", "S01", "--bridge", "replay"]):
        with pytest.raises(SystemExit):
            parse_cli(bad_argv)


def test_engine_closes_bridge_and_reports_lost_telemetry(tmp_path: Path) -> None:
    """Verify a silent bridge returns the display to standby and shutdown releases the bridge."""
    bridge = _FakeBridge(0.2)
    engine = _engine(tmp_path, DomainID.SOCIAL_EVALUATION, bridge=bridge)
    _to_decision(engine, 0)
    engine._update(250)
    assert engine._telemetry_live is True
    bridge.value = None  # sensor unplugged
    engine._update(250)
    assert engine._telemetry_live is False
    engine._render()
    engine._shutdown()
    assert bridge.closed is True


def test_mist_item_timeout_is_logged_as_an_incorrect_answer(tmp_path: Path) -> None:
    """Verify an item left unanswered past its countdown is scored, logged, and replaced."""
    engine = _engine(tmp_path, DomainID.ACADEMIC_PRESSURE)
    _to_decision(engine, 0)
    runner = engine._mist_runner
    assert runner is not None
    first_problem = runner.get_current_problem()
    assert first_problem is not None

    engine._update(MIST_ITEM_LIMIT_START_MS - 1)
    assert runner.answered_count == 0
    engine._update(1)
    assert runner.timeout_count == 1
    assert runner.get_current_problem() is not first_problem
    assert engine._ui_effects.is_flashing is False  # flash flag is refreshed at the start of the next frame
    engine._update(1)
    assert engine._ui_effects.is_flashing is True
    assert _state(engine) is EngineState.DECISION
    engine._shutdown()

    rows = _rows(tmp_path, EventType.MATH_ANSWER)
    assert len(rows) == 1
    assert rows[0]["key_pressed"] == "" and rows[0]["option_index"] == ""
    meta = json.loads(rows[0]["metadata"])
    assert meta["correct"] is False and meta["timed_out"] is True
    assert meta["item_limit_ms"] == MIST_ITEM_LIMIT_START_MS
    assert meta["problem"] == first_problem.question_text


def test_bart_pumps_are_paced_and_log_the_pressure_curve(tmp_path: Path) -> None:
    """Verify a pump inside the cooldown is ignored and every accepted pump records its hazard."""
    # Seed 7 survives the first two pumps (seed 42 bursts on the second, at a 5% hazard)
    engine = _engine(tmp_path, DomainID.RISK_REWARD, seed=7)
    _to_decision(engine, 1)
    runner = engine._bart_runner
    assert runner is not None

    engine._handle_input(_key(pygame.K_2))
    engine._handle_input(_key(pygame.K_2))  # still publishing: ignored
    assert runner.pump_count == 1
    engine._update(BART_PUMP_COOLDOWN_MS)
    engine._handle_input(_key(pygame.K_2))
    assert runner.pump_count == 2
    engine._update(BART_PUMP_COOLDOWN_MS)
    engine._handle_input(_key(pygame.K_1))  # secure
    assert _state(engine) is EngineState.FEEDBACK
    engine._shutdown()

    pumps = [json.loads(row["metadata"]) for row in _rows(tmp_path, EventType.BART_PUMP)]
    assert [meta["pump"] for meta in pumps] == [1, 2]
    assert pumps[0]["burst_prob"] == round(BART_BURST_PROB_BASE, 4)
    assert pumps[1]["burst_prob"] == round(BART_BURST_PROB_BASE + BART_BURST_PROB_INCREMENT, 4)
    assert pumps[1]["instability"] > pumps[0]["instability"]
    assert all("item_rt_ms" in meta for meta in pumps)
    secure = json.loads(_rows(tmp_path, EventType.BART_SECURE)[0]["metadata"])
    assert secure["pumps"] == 2
    assert secure["next_burst_prob"] == round(BART_BURST_PROB_BASE + 2 * BART_BURST_PROB_INCREMENT, 4)


def _rosso_pixels(surface: pygame.Surface) -> int:
    pixels = pygame.surfarray.array3d(surface).reshape(-1, 3)
    return int((pixels == np.array(COLOR_PRIMARY_ROSSO, dtype=pixels.dtype)).all(axis=1).sum())


def test_mist_item_countdown_bar_drains_and_turns_rosso_near_expiry(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify the exam skin shows the per-item countdown, in Rosso only once the item is about to expire."""
    scenario = domain_registry[0].scenarios[0]
    assert scenario.math_problems is not None
    renderer = UIRenderer(screen)
    runner = MISTRunner(scenario.math_problems, scenario.decision_duration_s)

    def rosso_after(elapsed_ms: int) -> int:
        runner.update(elapsed_ms)
        renderer.draw_decision(scenario, 30.0, None, UIEffectState(), runner, None, None, None)
        return _rosso_pixels(screen)

    baseline = rosso_after(0)
    assert rosso_after(MIST_ITEM_LIMIT_START_MS // 2) == baseline  # half the item time left: bar is ink, not Rosso
    at_20_pct = rosso_after(int(MIST_ITEM_LIMIT_START_MS * 0.3)) - baseline
    at_10_pct = rosso_after(int(MIST_ITEM_LIMIT_START_MS * 0.1)) - baseline
    assert runner.get_item_time_fraction() <= MIST_ITEM_BAR_RED_FRACTION
    assert at_20_pct > at_10_pct > 0
    assert abs(at_20_pct - 2 * at_10_pct) <= 24  # the Rosso bar shortens in proportion to the time left


def test_bart_pacing_cooldown_is_shown_on_the_pump_card(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify the pump card reads as busy while a pump is inside its cooldown, and as live once it has elapsed."""
    scenario = domain_registry[3].scenarios[1]
    assert scenario.bart_config is not None
    renderer = UIRenderer(screen)
    runner = BARTRunner(scenario.bart_config, seed=7, cooldown_ms=BART_PUMP_COOLDOWN_MS)
    drawn: list[str] = []
    draw_text = renderer._draw_text

    def record(text: str, *args: Any, **kwargs: Any) -> pygame.Rect:
        drawn.append(text)
        return draw_text(text, *args, **kwargs)

    renderer._draw_text = record  # type: ignore[method-assign]

    def labels() -> list[str]:
        drawn.clear()
        renderer.draw_decision(scenario, 30.0, None, UIEffectState(), None, runner, None, None)
        return list(drawn)

    assert "POST ANOTHER (Escalate Reach)" in labels()
    runner.pump()
    busy = labels()
    assert "PUBLISHING POST..." in busy and "POST ANOTHER (Escalate Reach)" not in busy
    runner.update(BART_PUMP_COOLDOWN_MS)
    assert "POST ANOTHER (Escalate Reach)" in labels()
