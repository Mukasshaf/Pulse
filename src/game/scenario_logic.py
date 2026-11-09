"""Interactive scenario behavioral runners for MIST, BART, and waiting tasks."""
from __future__ import annotations

import random

from src.game.constants import (
    MIST_ADAPT_STEP,
    MIST_ADAPT_STREAK,
    MIST_ITEM_LIMIT_MAX_MS,
    MIST_ITEM_LIMIT_MIN_MS,
    MIST_ITEM_LIMIT_START_MS,
    MIST_PEER_ADVANTAGE_PCT,
)
from src.game.scenarios import BARTConfig, MathProblem, RewardAccumulatorConfig


class MISTRunner:
    """Manages the rapid-fire arithmetic sequence, its adaptive item countdown, and fake peer progress."""

    def __init__(self, problems: list[MathProblem], total_duration_s: int) -> None:
        """Initialize problem set and tracking state."""
        self.problems: list[MathProblem] = problems
        self.total_duration_s: int = total_duration_s
        self.current_problem_index: int = 0
        self.correct_count: int = 0
        self.answered_count: int = 0
        self.timeout_count: int = 0
        self.all_problems_done: bool = False
        self.item_limit_ms: int = MIST_ITEM_LIMIT_START_MS
        self.item_elapsed_ms: int = 0
        self._correct_streak: int = 0
        self._incorrect_streak: int = 0

    def _register(self, is_correct: bool) -> None:
        """Record one outcome, move to the next problem, and adapt the countdown on a streak.

        This is the in-run form of the MIST difficulty adaptation: the per-item time limit
        tightens after consecutive successes and eases after consecutive failures, so the task
        stays at the edge of each participant's ability without a separate pretest block.
        """
        if is_correct:
            self.correct_count += 1
            self._correct_streak += 1
            self._incorrect_streak = 0
        else:
            self._incorrect_streak += 1
            self._correct_streak = 0
        self.answered_count += 1
        self.current_problem_index += 1
        self.item_elapsed_ms = 0

        if self._correct_streak >= MIST_ADAPT_STREAK:
            self.item_limit_ms = max(MIST_ITEM_LIMIT_MIN_MS, round(self.item_limit_ms * (1.0 - MIST_ADAPT_STEP)))
            self._correct_streak = 0
        elif self._incorrect_streak >= MIST_ADAPT_STREAK:
            self.item_limit_ms = min(MIST_ITEM_LIMIT_MAX_MS, round(self.item_limit_ms * (1.0 + MIST_ADAPT_STEP)))
            self._incorrect_streak = 0

        if self.current_problem_index >= len(self.problems):
            self.all_problems_done = True

    def handle_keypress(self, key: int) -> tuple[bool, bool]:
        """Evaluate keypress (keys 1-4) against current problem and advance."""
        if self.all_problems_done or self.current_problem_index >= len(self.problems):
            return (False, True)

        problem = self.problems[self.current_problem_index]
        is_correct = (key - 1) == problem.correct_index
        self._register(is_correct)
        return (is_correct, self.all_problems_done)

    def update(self, dt_ms: int) -> bool:
        """Advance the per-item countdown. Return True when the current item has just timed out.

        A timed-out item is scored as incorrect and the next problem is presented.
        """
        if self.all_problems_done or self.current_problem_index >= len(self.problems):
            return False
        self.item_elapsed_ms += dt_ms
        if self.item_elapsed_ms < self.item_limit_ms:
            return False
        self.timeout_count += 1
        self._register(False)
        return True

    def get_item_time_fraction(self) -> float:
        """Return the fraction of the current item's countdown that remains, from 1.0 down to 0.0."""
        return max(0.0, 1.0 - self.item_elapsed_ms / float(self.item_limit_ms))

    def get_current_problem(self) -> MathProblem | None:
        """Return the currently presented MathProblem or None if exhausted."""
        if self.all_problems_done or self.current_problem_index >= len(self.problems):
            return None
        return self.problems[self.current_problem_index]

    def get_accuracy_pct(self) -> int:
        """Calculate participant's current accuracy percentage."""
        if self.answered_count == 0:
            return 0
        return round((self.correct_count / self.answered_count) * 100)

    def get_peer_average_pct(self) -> int:
        """Return fake peer average always +15% above participant (MIST manipulation)."""
        return self.get_accuracy_pct() + MIST_PEER_ADVANTAGE_PCT

    def get_progress_fraction(self) -> float:
        """Return fractional completion of the arithmetic problem set."""
        if not self.problems:
            return 1.0
        return min(1.0, self.current_problem_index / len(self.problems))

    def get_peer_progress_fraction(self) -> float:
        """Return fake peer progress maintaining an apparent lead over participant."""
        user_prog = self.get_progress_fraction()
        if user_prog >= 1.0:
            return 1.0
        lead = 0.15
        return min(1.0, max(user_prog + 0.05, user_prog + lead))


class BARTRunner:
    """Implements the Balloon Analogue Risk Task escalating pump mechanic."""

    def __init__(self, config: BARTConfig, seed: int | None = None, cooldown_ms: int = 0) -> None:
        """Initialize balloon parameters and state. cooldown_ms paces successive pumps."""
        self.config: BARTConfig = config
        self._rng: random.Random = random.Random(seed)
        self.current_value: int = config.initial_value
        self.pump_count: int = 0
        self.is_burst: bool = False
        self.is_secured: bool = False
        self.cooldown_ms: int = cooldown_ms
        self.cooldown_remaining_ms: int = 0

    def burst_probability(self, pump_number: int) -> float:
        """Return the burst hazard of the given 1-based pump: linear escalation, certain at the cap."""
        if pump_number >= self.config.max_pumps:
            return 1.0
        return min(1.0, self.config.burst_probability_base + (pump_number - 1) * self.config.burst_probability_increment)

    def next_burst_probability(self) -> float:
        """Return the hazard the participant faces on their next pump (the pressure curve)."""
        return self.burst_probability(self.pump_count + 1)

    def can_pump(self) -> bool:
        """Return True when the task is live and the pacing cooldown has elapsed."""
        return not (self.is_burst or self.is_secured) and self.cooldown_remaining_ms <= 0

    def update(self, dt_ms: int) -> None:
        """Advance the pacing cooldown."""
        self.cooldown_remaining_ms = max(0, self.cooldown_remaining_ms - dt_ms)

    def get_cooldown_fraction(self) -> float:
        """Return the remaining share of the pacing cooldown, from 1.0 just after a pump down to 0.0."""
        if self.cooldown_ms <= 0:
            return 0.0
        return self.cooldown_remaining_ms / float(self.cooldown_ms)

    def pump(self) -> tuple[int, bool]:
        """Increment pump count and test probabilistic bursting."""
        if self.is_burst or self.is_secured:
            return (self.current_value, self.is_burst)

        self.pump_count += 1
        self.cooldown_remaining_ms = self.cooldown_ms
        if self.pump_count >= self.config.max_pumps:
            self.is_burst = True
            self.current_value = 0
            return (0, True)

        if self._rng.random() < self.burst_probability(self.pump_count):
            self.is_burst = True
            self.current_value = 0
            return (0, True)

        self.current_value += self.config.increment_per_pump
        return (self.current_value, False)

    def secure(self) -> int:
        """Lock in accumulated gains and conclude scenario."""
        if not self.is_burst:
            self.is_secured = True
        return self.current_value

    def get_instability_fraction(self) -> float:
        """Return 0.0 to 1.0 gauge fraction representing system instability."""
        return min(1.0, self.pump_count / float(self.config.max_pumps))

    def get_pumps_remaining_after_burst(self) -> int:
        """Return how many further pumps would have survived, replayed from this runner's own RNG state.

        The live generator is copied, not consumed, so the figure shown in the consequence text is
        the true counterfactual for this session rather than an invented number.
        """
        shadow = random.Random()
        shadow.setstate(self._rng.getstate())
        survived = 0
        pump_number = self.pump_count
        while True:
            pump_number += 1
            if pump_number >= self.config.max_pumps or shadow.random() < self.burst_probability(pump_number):
                return survived
            survived += 1


class RewardAccumulator:
    """Manages continuous exponential reward growth with a latent collapse point."""

    def __init__(
        self, config: RewardAccumulatorConfig, seed: int | None = None
    ) -> None:
        """Initialize reward accumulation state and schedule collapse time."""
        self.config: RewardAccumulatorConfig = config
        self._rng: random.Random = random.Random(seed)
        min_s, max_s = config.collapse_time_range
        self.collapse_time_ms: int = self._rng.randint(min_s * 1000, max_s * 1000)
        self.elapsed_ms: int = 0
        self._current_value: float = float(config.initial_value)
        self.is_claimed: bool = False
        self.is_collapsed: bool = False

    def update(self, dt_ms: int) -> bool:
        """Advance time by dt_ms and evaluate collapse threshold. Returns True on collapse."""
        if self.is_claimed or self.is_collapsed:
            return False

        self.elapsed_ms += dt_ms
        sec = self.elapsed_ms / 1000.0
        grown = self.config.initial_value * (self.config.growth_rate**sec)
        self._current_value = min(float(self.config.max_display_value), grown)

        if self.elapsed_ms >= self.collapse_time_ms:
            self.is_collapsed = True
            self._current_value = 0.0
            return True

        return False

    def claim(self) -> int:
        """Secure and freeze accumulated reward."""
        if not self.is_collapsed:
            self.is_claimed = True
        return self.get_current_value()

    def get_current_value(self) -> int:
        """Return the current integer reward value."""
        return int(self._current_value)

    def get_instability_fraction(self) -> float:
        """Return visual instability level approaching maximum collapse boundary."""
        max_collapse_ms = self.config.collapse_time_range[1] * 1000
        return min(1.0, self.elapsed_ms / float(max_collapse_ms))

    def has_collapsed(self) -> bool:
        """Return whether the chest has collapsed."""
        return self.is_collapsed


class DelayWaitRunner:
    """Tracks a timed waiting state with fractional progress calculation."""

    def __init__(self, duration_s: int, display_text: str) -> None:
        """Initialize delay interval and display text."""
        self.duration_ms: int = duration_s * 1000
        self.display_text: str = display_text
        self.elapsed_ms: int = 0

    def update(self, dt_ms: int) -> bool:
        """Advance wait timer. Returns True when interval completes."""
        self.elapsed_ms = min(self.duration_ms, self.elapsed_ms + dt_ms)
        return self.elapsed_ms >= self.duration_ms

    def get_elapsed_fraction(self) -> float:
        """Return fractional completion of the delay wait from 0.0 to 1.0."""
        if self.duration_ms <= 0:
            return 1.0
        return min(1.0, self.elapsed_ms / float(self.duration_ms))
