"""Unit tests for interactive logic runners: MIST, BART, Reward, and Delay."""
from __future__ import annotations

import itertools

from src.game.constants import (
    BART_BURST_PROB_BASE,
    BART_BURST_PROB_INCREMENT,
    BART_INCREMENT,
    BART_INITIAL_VALUE,
    BART_MAX_PUMPS,
    MIST_ADAPT_STEP,
    MIST_ITEM_LIMIT_MAX_MS,
    MIST_ITEM_LIMIT_MIN_MS,
    MIST_ITEM_LIMIT_START_MS,
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


def test_mist_item_limit_tightens_after_correct_streak_and_eases_after_errors() -> None:
    """Verify the adaptive countdown moves 10% per two-answer streak and stays inside its bounds."""
    problems = generate_math_problems(40)
    runner = MISTRunner(problems, 40)
    assert runner.item_limit_ms == MIST_ITEM_LIMIT_START_MS

    # One correct answer is not a streak
    runner.handle_keypress(problems[0].correct_index + 1)
    assert runner.item_limit_ms == MIST_ITEM_LIMIT_START_MS
    runner.handle_keypress(problems[1].correct_index + 1)
    tightened = round(MIST_ITEM_LIMIT_START_MS * (1.0 - MIST_ADAPT_STEP))
    assert runner.item_limit_ms == tightened

    # One wrong answer is not a streak; the second consecutive one eases the countdown again
    wrong_key = (problems[2].correct_index + 1) % 4 + 1
    runner.handle_keypress(wrong_key)
    assert runner.item_limit_ms == tightened
    runner.handle_keypress((problems[3].correct_index + 1) % 4 + 1)
    assert runner.item_limit_ms == round(tightened * (1.0 + MIST_ADAPT_STEP))

    # The countdown never leaves [MIN, MAX] however long the streak
    fast = MISTRunner(problems, 40)
    for problem in problems:
        fast.handle_keypress(problem.correct_index + 1)
    assert fast.item_limit_ms == MIST_ITEM_LIMIT_MIN_MS
    slow = MISTRunner(problems, 40)
    for problem in problems:
        slow.handle_keypress((problem.correct_index + 1) % 4 + 1)
    assert slow.correct_count == 0
    assert slow.item_limit_ms == MIST_ITEM_LIMIT_MAX_MS


def test_mist_item_timeout_scores_incorrect_and_advances() -> None:
    """Verify an unanswered item times out, counts as incorrect, and presents the next problem."""
    problems = generate_math_problems(10)
    runner = MISTRunner(problems, 40)
    assert runner.get_item_time_fraction() == 1.0
    assert runner.update(MIST_ITEM_LIMIT_START_MS // 2) is False
    assert abs(runner.get_item_time_fraction() - 0.5) < 0.01
    assert runner.get_current_problem() is problems[0]

    assert runner.update(MIST_ITEM_LIMIT_START_MS // 2) is True
    assert runner.timeout_count == 1
    assert runner.answered_count == 1
    assert runner.correct_count == 0
    assert runner.get_current_problem() is problems[1]
    assert runner.get_item_time_fraction() == 1.0

    # A second timeout completes an incorrect streak and eases the countdown
    assert runner.update(MIST_ITEM_LIMIT_START_MS) is True
    assert runner.item_limit_ms == round(MIST_ITEM_LIMIT_START_MS * (1.0 + MIST_ADAPT_STEP))


def test_bart_hazard_escalates_across_the_whole_pump_range() -> None:
    """Verify the production burst curve rises monotonically and is not exhausted in a few pumps."""
    cfg = BARTConfig(BART_INITIAL_VALUE, BART_INCREMENT, BART_BURST_PROB_BASE, BART_BURST_PROB_INCREMENT, BART_MAX_PUMPS)
    runner = BARTRunner(cfg, seed=1)
    hazards = [runner.burst_probability(n) for n in range(1, BART_MAX_PUMPS + 1)]
    assert all(later > earlier for earlier, later in itertools.pairwise(hazards))
    assert hazards[0] <= 0.05
    assert hazards[-1] == 1.0
    assert hazards[-2] < 0.5  # no certain burst before the hard cap

    survival = 1.0
    expected_safe_pumps = 0.0
    for hazard in hazards:
        survival *= 1.0 - hazard
        expected_safe_pumps += survival
    assert 5.0 <= expected_safe_pumps <= 8.0


def test_bart_cooldown_paces_pumps() -> None:
    """Verify a paced runner refuses a second pump until the cooldown has elapsed."""
    cfg = BARTConfig(BART_INITIAL_VALUE, BART_INCREMENT, 0.0, 0.0, 10)
    runner = BARTRunner(cfg, seed=1, cooldown_ms=1500)
    assert runner.can_pump() is True
    runner.pump()
    assert runner.can_pump() is False
    assert runner.get_cooldown_fraction() == 1.0
    runner.update(750)
    assert runner.can_pump() is False
    assert abs(runner.get_cooldown_fraction() - 0.5) < 0.01
    runner.update(750)
    assert runner.can_pump() is True

    # An unpaced runner (the default) is always ready
    assert BARTRunner(cfg, seed=1).get_cooldown_fraction() == 0.0


def test_bart_counterfactual_matches_the_real_continuation() -> None:
    """Verify the 'would have survived N more' figure is what actually happens if pumping continues."""
    cfg = BARTConfig(BART_INITIAL_VALUE, BART_INCREMENT, BART_BURST_PROB_BASE, BART_BURST_PROB_INCREMENT, BART_MAX_PUMPS)
    for seed in range(25):
        runner = BARTRunner(cfg, seed=seed)
        runner.pump()
        if runner.is_burst:
            continue
        predicted = runner.get_pumps_remaining_after_burst()
        assert runner.get_pumps_remaining_after_burst() == predicted  # asking does not consume the RNG
        survived = 0
        while True:
            _, burst = runner.pump()
            if burst:
                break
            survived += 1
        assert survived == predicted


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
