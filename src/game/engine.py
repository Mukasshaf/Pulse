"""Master Pygame event loop and state machine engine for Pulse."""
from __future__ import annotations

import pygame

from src.game.constants import (
    BASELINE_DURATION_S,
    FAST_BASELINE_DURATION_S,
    FPS,
    EngineState,
)
from src.game.engine_input import EngineInputMixin
from src.game.engine_state import SessionConfig
from src.game.engine_timer import EngineTimerMixin

__all__ = ["GameEngine", "SessionConfig"]


class GameEngine(EngineInputMixin, EngineTimerMixin):
    """Central game engine executing the 7-domain stress paradigm."""

    def run(self) -> None:
        """Main game loop capped at 60 FPS."""
        pygame.mouse.set_visible(False)
        # Mouse events never reach the queue during a session (wrist-motion artifact control)
        pygame.event.set_blocked([pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL])
        pygame.event.set_grab(True)
        self._running = True
        clock = pygame.time.Clock()
        self._transition_to(EngineState.ID_INPUT)
        self._last_wall_ms = self._now_ms()

        while self._running:
            dt_ms = clock.tick(FPS)
            self._monitor_clock(dt_ms)
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    self._log_abort()
                    self._shutdown()
                    return
                self._handle_input(event)

            self._update(dt_ms)
            self._render()
            pygame.display.flip()
        self._shutdown()

    def _render(self) -> None:
        """Render frame delegating to UIRenderer based on active state."""
        scenario = self._get_safe_scenario()
        rem_s = self._state_timer_ms / 1000.0

        if self._current_state == EngineState.ID_INPUT:
            self.renderer.draw_id_input(self._id_input_text, self._id_error)
        elif self._current_state == EngineState.BASELINE:
            tot = FAST_BASELINE_DURATION_S if self.config.fast_baseline else BASELINE_DURATION_S
            self.renderer.draw_baseline(self._state_elapsed_ms / 1000.0, float(tot))
        elif self._current_state == EngineState.PRIMING and scenario:
            can_skip = self._state_elapsed_ms >= self._priming_floor_ms(scenario)
            self.renderer.draw_priming(scenario, self._state_elapsed_ms / 1000.0, can_skip)
        elif self._current_state == EngineState.DECISION and scenario:
            # None tells the skin there is no live telemetry, so it never shows a fabricated reading
            comp = self._composure_fraction if scenario.has_deception_metric and self._telemetry_live else None
            self.renderer.draw_decision(scenario, rem_s, self._selected_option_index, self._ui_effects, self._mist_runner, self._bart_runner, self._reward_runner, comp)
        elif self._current_state == EngineState.POST_WAIT and scenario:
            frac = self._state_elapsed_ms / float(scenario.post_wait_duration_s * 1000)
            self.renderer.draw_post_wait(scenario.post_wait_text, frac)
        elif self._current_state == EngineState.FEEDBACK:
            self.renderer.draw_feedback(self._consequence_text, self._state_elapsed_ms / 1000.0)
        elif self._current_state in (EngineState.INTRA_REST, EngineState.INTER_REST):
            self.renderer.draw_rest(self._current_state == EngineState.INTER_REST, rem_s)
        elif self._current_state == EngineState.DEBRIEF:
            dur = (self._now_ms() - self.config.session_start_unix_ts_ms) / 1000.0
            self.renderer.draw_debrief(dur, self._scenarios_completed)

        # Question & Briefing Modal Popup (rendered on top of decision/post-wait when button held)
        if self._is_question_popup_active and scenario and self._current_state in (EngineState.DECISION, EngineState.POST_WAIT):
            self.renderer.draw_question_popup(scenario)
