"""Keyboard and window-focus handling for the Pulse engine."""
from __future__ import annotations

import json
import re

import pygame

from src.game.constants import SUBJECT_ID_PATTERN, EngineState, EventType, ScenarioType
from src.game.engine_state import EngineBase
from src.game.event_logger import GameEvent
from src.game.scenarios import Scenario


class EngineInputMixin(EngineBase):
    """Routes input events to the handler for the current state and scenario type."""

    def _handle_input(self, event: pygame.event.Event) -> None:
        """Route keyboard and window-focus events to current state handler."""
        if event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWFOCUSGAINED):
            # Timers and the drone freeze while the window is unfocused, so no artificial timeout can occur
            self._focus_paused = event.type == pygame.WINDOWFOCUSLOST
            if self.audio and self._focus_paused:
                self.audio.pause()
            elif self.audio:
                self.audio.resume()
            kind = EventType.FOCUS_LOST if self._focus_paused else EventType.FOCUS_GAINED
            domain, scenario_id = self._event_context()
            self.logger.log_event(GameEvent(self._now_ms(), kind, domain, scenario_id, "{}", None, None, None, {"state": self._current_state.value}))
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_TAB, pygame.K_q, pygame.K_h):
                self._is_question_popup_active = True
                return
            if self._current_state == EngineState.ID_INPUT:
                self._handle_id_input(event)
            elif self._current_state == EngineState.PRIMING:
                self._handle_priming_input(event)
            elif self._current_state == EngineState.DECISION:
                self._handle_decision_input(event)
        elif event.type == pygame.KEYUP:
            if event.key in (pygame.K_TAB, pygame.K_q, pygame.K_h):
                self._is_question_popup_active = False

    def _handle_priming_input(self, event: pygame.event.Event) -> None:
        """Allow skipping remaining priming countdown with SPACE or ENTER once the priming floor has passed."""
        scenario = self._get_safe_scenario()
        if scenario and self._state_elapsed_ms < self._priming_floor_ms(scenario):
            return
        if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self._transition_to(EngineState.DECISION)

    def _handle_id_input(self, event: pygame.event.Event) -> None:
        """Process Subject ID text entry."""
        if event.key == pygame.K_RETURN:
            if re.match(SUBJECT_ID_PATTERN, self._id_input_text.strip()):
                self.config.subject_id = self._id_input_text.strip()
                self._id_error = None
                # Keep session metadata in step with an ID edited on this screen
                self.logger.subject_id = self.config.subject_id
                self.logger.save_domain_order([d.id for d in self._domains], self.config.random_seed, self.config.session_start_unix_ts_ms)
                self._transition_to(EngineState.BASELINE)
            else:
                self._id_error = "Enter a valid Subject ID (e.g. S01, S99)"
        elif event.key == pygame.K_BACKSPACE:
            self._id_input_text = self._id_input_text[:-1]
        elif len(self._id_input_text) < 6 and event.unicode.isprintable():
            self._id_input_text += event.unicode.upper()

    def _handle_decision_input(self, event: pygame.event.Event) -> None:
        """Route numeric choice keypresses."""
        key_map = {pygame.K_1: 1, pygame.K_KP1: 1, pygame.K_2: 2, pygame.K_KP2: 2, pygame.K_3: 3, pygame.K_KP3: 3, pygame.K_4: 4, pygame.K_KP4: 4}
        if event.key not in key_map:
            return
        # A committed choice is final, and nothing is accepted while the briefing modal hides the options
        if self._pending_exit is not None or self._is_question_popup_active:
            return
        choice = key_map[event.key]
        scenario = self._get_safe_scenario()
        if not scenario or self._selected_option_index is not None:
            return

        # Row timestamp is wall-clock (the sensor join key); intervals come from the monotonic clock
        now = self._now_ms()
        mono = self._mono_ms()
        rt_ms = mono - self._decision_presented_mono_ms
        item_rt_ms = mono - self._last_response_mono_ms

        if scenario.scenario_type == ScenarioType.MIST_ARITHMETIC and self._mist_runner:
            accepted = self._handle_mist_input(choice, scenario, now, rt_ms, item_rt_ms)
        elif scenario.scenario_type == ScenarioType.BART_ESCALATION and self._bart_runner:
            accepted = self._handle_bart_input(choice, scenario, now, rt_ms, item_rt_ms)
        elif scenario.scenario_type == ScenarioType.REWARD_ACCUMULATOR and self._reward_runner:
            accepted = self._handle_reward_input(choice, scenario, now, rt_ms)
        else:
            accepted = self._handle_standard_input(choice, scenario, now, rt_ms)
        # Per-item intervals restart only from an accepted response, never from an ignored keypress
        if accepted:
            self._last_response_mono_ms = mono

    def _handle_standard_input(self, key: int, scenario: Scenario, now: int, rt_ms: int) -> bool:
        """Handle standard MCQ selection. Return True when the key committed a choice."""
        if key > len(scenario.options):
            return False
        opt_idx = key - 1
        opt = scenario.options[opt_idx]
        self._selected_option_index = opt_idx
        self.renderer.set_last_choice(opt_idx)
        if opt.key == 2 and scenario.delay_wait_outcomes:
            self._consequence_text = self._rng.choice(scenario.delay_wait_outcomes)
        else:
            self._consequence_text = opt.consequence_text
        choice_json = json.dumps({"key": key, "text": opt.text})
        meta: dict[str, str | int | float | bool] = {"is_conforming": opt.is_conforming} if opt.is_conforming is not None else {}
        self.logger.log_event(GameEvent(now, EventType.OPTION_SELECTED, scenario.domain_id.value, scenario.id, choice_json, key, opt_idx, rt_ms, meta))
        # DELAY_WAIT: choosing to wait (key 2) is the only branch that actually waits
        waits = scenario.has_post_wait or (
            scenario.scenario_type == ScenarioType.DELAY_WAIT and opt.key == 2 and scenario.post_wait_duration_s > 0
        )
        self._exit_decision(EngineState.POST_WAIT if waits else EngineState.FEEDBACK)
        return True

    def _handle_mist_input(self, key: int, scenario: Scenario, now: int, rt_ms: int, item_rt_ms: int) -> bool:
        """Process MIST arithmetic answer input. Return True when an answer was scored."""
        if not self._mist_runner:
            return False
        problem = self._mist_runner.get_current_problem()
        limit_ms = self._mist_runner.item_limit_ms
        is_corr, done = self._mist_runner.handle_keypress(key)
        meta: dict[str, str | int | float | bool] = {"correct": is_corr, "item_rt_ms": item_rt_ms, "item_limit_ms": limit_ms}
        if problem is not None:
            meta["problem"] = problem.question_text
        self.logger.log_event(GameEvent(now, EventType.MATH_ANSWER, scenario.domain_id.value, scenario.id, "{}", key, key - 1, rt_ms, meta))
        if not is_corr:
            self._button_flash.trigger()
        if done:
            self._consequence_text = self._mist_summary()
            self._exit_decision(EngineState.FEEDBACK)
        return True

    def _handle_bart_input(self, key: int, scenario: Scenario, now: int, rt_ms: int, item_rt_ms: int) -> bool:
        """Process BART secure or pump actions. Return True when the key was acted on."""
        runner = self._bart_runner
        if not runner:
            return False
        domain = scenario.domain_id.value
        if key == 1:
            val = runner.secure()
            self._selected_option_index = 0
            rem = runner.get_pumps_remaining_after_burst()
            self._consequence_text = f"Gains secured. System remained stable for {rem} more cycles."
            secure_meta: dict[str, str | int | float | bool] = {
                "value": val,
                "item_rt_ms": item_rt_ms,
                "pumps": runner.pump_count,
                "next_burst_prob": round(runner.next_burst_probability(), 4),
            }
            self.logger.log_event(GameEvent(now, EventType.BART_SECURE, domain, scenario.id, "{}", key, 0, rt_ms, secure_meta))
            self._exit_decision(EngineState.FEEDBACK)
            return True
        if key != 2 or not runner.can_pump():
            return False  # other keys, or a pump attempted inside the pacing cooldown
        hazard = runner.next_burst_probability()
        val, burst = runner.pump()
        # One row per pump reconstructs the pressure curve: hazard faced, value reached, decision latency
        pump_meta: dict[str, str | int | float | bool] = {
            "value": val,
            "item_rt_ms": item_rt_ms,
            "pump": runner.pump_count,
            "burst_prob": round(hazard, 4),
            "instability": round(runner.get_instability_fraction(), 4),
        }
        self.logger.log_event(GameEvent(now, EventType.BART_PUMP, domain, scenario.id, "{}", key, 1, rt_ms, pump_meta))
        if burst:
            self._selected_option_index = 1
            self._consequence_text = "System failure. All accumulated progress lost."
            self.logger.log_event(GameEvent(now, EventType.BART_BURST, domain, scenario.id, "{}", key, 1, rt_ms, {"pump": runner.pump_count}))
            self._exit_decision(EngineState.FEEDBACK)
        return True

    def _handle_reward_input(self, key: int, scenario: Scenario, now: int, rt_ms: int) -> bool:
        """Process reward accumulator claim action. Return True when the reward was claimed."""
        if not self._reward_runner or key != 1:
            return False
        val = self._reward_runner.claim()
        self._selected_option_index = 0
        self._consequence_text = f"Reward secured. Chest value: {val}."
        self.logger.log_event(GameEvent(now, EventType.REWARD_CLAIM, scenario.domain_id.value, scenario.id, "{}", key, 0, rt_ms, {"value": val}))
        self._exit_decision(EngineState.FEEDBACK)
        return True
