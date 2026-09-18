"""Unit tests for interactive logic runners: MIST, BART, Reward, and Delay."""
from __future__ import annotations

from src.game.constants import (
    BART_BURST_PROB_BASE,
    BART_BURST_PROB_INCREMENT,
    BART_INCREMENT,
    BART_INITIAL_VALUE,
    BART_MAX_PUMPS,
)
from src.game.scenario_logic import (
    BARTRunner,
    DelayWaitRunner,
    MISTRunner,
    RewardAccumulator,
)
from src.game.scenarios import (
    BARTConfig,
    RewardAccumulatorConfig,
    generate_math_problems,
)


def test_mist_runner_correct_and_accuracy() -> None:
    """Verify MIST arithmetic scoring and social comparison manipulation."""
    problems = generate_math_problems(4)
    runner = MISTRunner(problems, 40)

    assert runner.get_accuracy_pct() == 0
    assert runner.get_peer_average_pct() == 15

    # Answer all 4 correctly
    for p in problems:
        correct_key = p.correct_index + 1
        is_corr, done = runner.handle_keypress(correct_key)
        assert is_corr is True

    assert done is True
    assert runner.get_accuracy_pct() == 100
    assert runner.get_peer_average_pct() == 115


def test_mist_peer_progress_lead() -> None:
    """Verify peer progress fraction maintains consistent lead over user."""
    problems = generate_math_problems(4)
    runner = MISTRunner(problems, 40)
    for p in problems:
        assert runner.get_peer_progress_fraction() > runner.get_progress_fraction()
        runner.handle_keypress(p.correct_index + 1)


def test_bart_runner_pumps_and_burst() -> None:
    """Verify BART value escalation and deterministic cap burst."""
    cfg = BARTConfig(
        initial_value=BART_INITIAL_VALUE,
        increment_per_pump=BART_INCREMENT,
        burst_probability_base=0.0,  # Zero base to test mechanics
        burst_probability_increment=0.0,
        max_pumps=5,
    )
    runner = BARTRunner(cfg)
    val, burst = runner.pump()
    assert val == BART_INITIAL_VALUE + BART_INCREMENT
    assert burst is False
    assert runner.get_instability_fraction() == 1.0 / 5.0

    # Pump until max_pumps
    for _ in range(4):
        val, burst = runner.pump()

    assert burst is True
    assert val == 0


def test_bart_runner_secure() -> None:
    """Verify securing locks in BART value."""
    cfg = BARTConfig(
        initial_value=BART_INITIAL_VALUE,
        increment_per_pump=BART_INCREMENT,
        burst_probability_base=0.0,
        burst_probability_increment=0.0,
        max_pumps=10,
    )
    runner = BARTRunner(cfg)
    runner.pump()
    runner.pump()
    secured = runner.secure()
    assert secured == BART_INITIAL_VALUE + 2 * BART_INCREMENT


def test_reward_accumulator_growth_and_claim() -> None:
    """Verify continuous exponential reward growth and claim action."""
    cfg = RewardAccumulatorConfig(
        initial_value=10,
        growth_rate=1.15,
        collapse_time_range=(20, 40),
        max_display_value=9999,
    )
    acc = RewardAccumulator(cfg, seed=42)
    assert acc.get_current_value() == 10

    # Advance 2 seconds
    acc.update(2000)
    assert acc.get_current_value() > 10

    claimed = acc.claim()
    assert claimed == acc.get_current_value()
    assert acc.is_claimed is True


def test_reward_accumulator_collapse_bounds() -> None:
    """Verify collapse point always falls strictly within defined range."""
    cfg = RewardAccumulatorConfig(
        initial_value=10,
        growth_rate=1.15,
        collapse_time_range=(20, 40),
        max_display_value=9999,
    )
    for s in range(50):
        acc = RewardAccumulator(cfg, seed=s)
        assert 20000 <= acc.collapse_time_ms <= 40000


def test_delay_wait_runner() -> None:
    """Verify delay wait elapsed fraction and completion flag."""
    runner = DelayWaitRunner(10, "Processing...")
    assert runner.get_elapsed_fraction() == 0.0

    done = runner.update(5000)
    assert done is False
    assert abs(runner.get_elapsed_fraction() - 0.5) < 0.01

    done = runner.update(5000)
    assert done is True
    assert runner.get_elapsed_fraction() == 1.0
