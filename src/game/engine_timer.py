"""Per-frame timers, clock monitoring, and composure polling for the Pulse engine."""
from __future__ import annotations

import pygame

from src.game.constants import (
    CLOCK_JUMP_WARNING_THRESHOLD_MS,
    COMPOSURE_BAR_UPDATE_HZ,
    COMPOSURE_DROP_CONSECUTIVE_SAMPLES,
    COMPOSURE_DROP_COOLDOWN_S,
    DECEPTION_THRESHOLD_SIGMA,
    FPS,
    EngineState,
    EventType,
)
from src.game.engine_state import EngineBase
from src.game.event_logger import GameEvent
from src.game.scenarios import Scenario


class EngineTimerMixin(EngineBase):
    """Advances state timers each frame and decides when a state is allowed to end."""

    def _monitor_clock(self, dt_ms: int) -> None:
        """Log CLOCK_ANOMALY when a frame stalls or the wall clock diverges from the frame clock."""
        now = self._now_ms()
        wall_delta_ms = now - self._last_wall_ms
        self._last_wall_ms = now
        stalled = dt_ms > (1000 // FPS) + CLOCK_JUMP_WARNING_THRESHOLD_MS
        jumped = abs(wall_delta_ms - dt_ms) > CLOCK_JUMP_WARNING_THRESHOLD_MS
        if not (stalled or jumped):
            return
        domain, scenario_id = self._event_context()
        meta: dict[str, str | int | float | bool] = {
            "wall_delta_ms": wall_delta_ms,
            "frame_dt_ms": dt_ms,
            "state": self._current_state.value,
        }
        self.logger.log_event(GameEvent(now, EventType.CLOCK_ANOMALY, domain, scenario_id, "{}", None, None, None, meta))

    def _update(self, dt_ms: int) -> None:
        """Advance state timers, UI effects, and runners each frame."""
        if dt_ms <= 0 or self._focus_paused:
            return
        self._state_elapsed_ms += dt_ms
        self._button_flash.update(dt_ms)
        self._ui_effects.is_flashing = self._button_flash.is_flashing()

        # Update active question popup state if keys are actively pressed
        try:
            keys = pygame.key.get_pressed()
        except pygame.error:
            # No video subsystem (headless unit tests): KEYDOWN/KEYUP events alone drive the popup
            keys = None
        if keys is not None:
            if keys[pygame.K_TAB] or keys[pygame.K_q] or keys[pygame.K_h]:
                self._is_question_popup_active = True
            elif any(keys):
                self._is_question_popup_active = False

        if self._current_state == EngineState.BASELINE:
            self._update_baseline(dt_ms)
        elif self._current_state == EngineState.PRIMING:
            self._update_timer_state(dt_ms, EngineState.DECISION)
        elif self._current_state == EngineState.DECISION:
            self._update_decision(dt_ms)
        elif self._current_state == EngineState.POST_WAIT:
            self._update_timer_state(dt_ms, EngineState.FEEDBACK)
        elif self._current_state == EngineState.FEEDBACK:
            self._update_feedback(dt_ms)
        elif self._current_state in (EngineState.INTRA_REST, EngineState.INTER_REST):
            self._update_rest(dt_ms)

    def _update_baseline(self, dt_ms: int) -> None:
        """Track baseline countdown and collect MPU variance samples."""
        var = self.bridge.get_mpu_variance()
        self._telemetry_live = var is not None
        if var is not None:
            self._baseline_var_samples.append(var)
        self._state_timer_ms = max(0, self._state_timer_ms - dt_ms)
        if self._state_timer_ms <= 0:
            self.logger.log_event(GameEvent(self._now_ms(), EventType.BASELINE_END, "", "", "{}", None, None, None, {}))
            if self._baseline_var_samples:
                mean_v = sum(self._baseline_var_samples) / len(self._baseline_var_samples)
                sigma = max(0.01, (sum((x - mean_v) ** 2 for x in self._baseline_var_samples) / len(self._baseline_var_samples)) ** 0.5)
                self._deception_threshold = mean_v + DECEPTION_THRESHOLD_SIGMA * sigma
            self._transition_to(EngineState.PRIMING)

    def _update_timer_state(self, dt_ms: int, next_state: EngineState) -> None:
        """Countdown timer advancing to next state on expiry."""
        self._state_timer_ms = max(0, self._state_timer_ms - dt_ms)
        if self._state_timer_ms <= 0:
            self._transition_to(next_state)

    def _update_composure(self, dt_ms: int, scenario: Scenario) -> None:
        """Poll tremor telemetry; drop composure only on sustained supra-threshold motion, with a cooldown."""
        self._composure_cooldown_ms = max(0, self._composure_cooldown_ms - dt_ms)
        self._composure_poll_timer_ms += dt_ms
        if self._composure_poll_timer_ms < int(1000 / COMPOSURE_BAR_UPDATE_HZ):
            return
        self._composure_poll_timer_ms = 0
        var = self.bridge.get_mpu_variance()
        # A bridge that has gone silent (unplugged, stale) puts the bar back on STANDBY
        self._telemetry_live = var is not None
        if var is None:
            return
        if var > self._deception_threshold:
            self._composure_over_count += 1
        else:
            self._composure_over_count = 0
            self._composure_fraction = min(1.0, self._composure_fraction + 0.05)
        if self._composure_over_count >= COMPOSURE_DROP_CONSECUTIVE_SAMPLES and self._composure_cooldown_ms <= 0:
            self._composure_over_count = 0
            self._composure_cooldown_ms = int(COMPOSURE_DROP_COOLDOWN_S * 1000)
            self._composure_fraction = max(0.1, self._composure_fraction - 0.15)
            meta: dict[str, str | int | float | bool] = {"mpu_var": var, "threshold": self._deception_threshold}
            self.logger.log_event(GameEvent(self._now_ms(), EventType.DECEPTION_TRIGGER, scenario.domain_id.value, scenario.id, "{}", None, None, None, meta))

    def _tick_mist(self, dt_ms: int, scenario: Scenario) -> None:
        """Advance the MIST item countdown and log an item that timed out as an incorrect answer."""
        if self._mist_runner is None:
            return
        problem = self._mist_runner.get_current_problem()
        limit_ms = self._mist_runner.item_limit_ms
        if not self._mist_runner.update(dt_ms):
            return
        mono = self._mono_ms()
        meta: dict[str, str | int | float | bool] = {
            "correct": False,
            "timed_out": True,
            "item_rt_ms": limit_ms,
            "item_limit_ms": limit_ms,
        }
        if problem is not None:
            meta["problem"] = problem.question_text
        rt_ms = mono - self._decision_presented_mono_ms
        self.logger.log_event(GameEvent(self._now_ms(), EventType.MATH_ANSWER, scenario.domain_id.value, scenario.id, "{}", None, None, rt_ms, meta))
        self._last_response_mono_ms = mono
        self._button_flash.trigger()

    def _update_decision(self, dt_ms: int) -> None:
        """Update decision countdown, audio trigger, jitter, collapse checks, and the committed-choice hold."""
        scenario = self._get_safe_scenario()
        if not scenario:
            return
        self._state_timer_ms = max(0, self._state_timer_ms - dt_ms)
        frac = self._state_timer_ms / float(scenario.decision_duration_s * 1000)

        # Drone, timer colour and jitter follow the clock only, so the stimulus is identical
        # for every participant whether or not a choice has already been committed
        if self.audio and frac <= scenario.drone_trigger_fraction:
            self.audio.start_drone()
        self._ui_effects.timer_bar_color = self._color_transition.get_color(frac)
        if scenario.jitter_trigger_s and self._state_timer_ms <= scenario.jitter_trigger_s * 1000:
            self._ui_effects.jitter_offset = self._jitter.get_offset(self._state_elapsed_ms)
        else:
            self._ui_effects.jitter_offset = (0, 0)

        if scenario.has_deception_metric:
            self._update_composure(dt_ms, scenario)

        if self._pending_exit is not None:
            # Choice already committed: the locked-in state stays on screen until the timer expires
            next_state = self._pending_exit
            if self._state_elapsed_ms >= self._decision_floor_ms(scenario) or self._state_timer_ms <= 0:
                if self.audio:
                    self.audio.stop_drone()
                self._transition_to(next_state)
            return

        if self._bart_runner:
            self._bart_runner.update(dt_ms)
        self._tick_mist(dt_ms, scenario)
        if self._reward_runner and self._reward_runner.update(dt_ms):
            self._consequence_text = "Chest collapsed. All accumulated value lost."
            self.logger.log_event(GameEvent(self._now_ms(), EventType.REWARD_COLLAPSE, scenario.domain_id.value, scenario.id, "{}", None, None, None, {}))
            self._exit_decision(EngineState.FEEDBACK)
            return

        if self._state_timer_ms <= 0:
            if self.audio:
                self.audio.stop_drone()
            if self._mist_runner is not None and self._mist_runner.answered_count > 0:
                # MIST runs on the clock: expiry after answering is completion, not a non-response
                self._consequence_text = self._mist_summary()
            else:
                self._consequence_text = scenario.timeout_consequence
                self.logger.log_event(GameEvent(self._now_ms(), EventType.TIMEOUT_NO_RESPONSE, scenario.domain_id.value, scenario.id, "{}", None, None, None, {}))
            self._transition_to(EngineState.POST_WAIT if scenario.has_post_wait else EngineState.FEEDBACK)

    def _update_feedback(self, dt_ms: int) -> None:
        """Countdown consequence display and transition to rest or debrief."""
        self._state_timer_ms = max(0, self._state_timer_ms - dt_ms)
        if self._state_timer_ms <= 0:
            scenario = self._get_safe_scenario()
            if scenario:
                self.logger.log_event(GameEvent(self._now_ms(), EventType.SCENARIO_END, scenario.domain_id.value, scenario.id, "{}", None, None, None, {}))
            self._scenarios_completed += 1
            if self._current_scenario_idx == 0:
                self._current_scenario_idx = 1
                self._transition_to(EngineState.INTRA_REST)
            else:
                self._current_scenario_idx = 0
                self._current_domain_idx += 1
                self._transition_to(EngineState.INTER_REST if self._current_domain_idx < len(self._domains) else EngineState.DEBRIEF)

    def _update_rest(self, dt_ms: int) -> None:
        """Advance rest timer and return to priming on completion."""
        self._state_timer_ms = max(0, self._state_timer_ms - dt_ms)
        if self._state_timer_ms <= 0:
            self.logger.log_event(GameEvent(self._now_ms(), EventType.REST_END, "", "", "{}", None, None, None, {}))
            self._transition_to(EngineState.PRIMING)
