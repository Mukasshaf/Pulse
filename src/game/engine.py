"""Master Pygame event loop and state machine engine for Pulse."""
from __future__ import annotations

import json
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path

import pygame

from src.game.audio import AudioController
from src.game.bridge_interface import BridgeInterface, StubBridge
from src.game.constants import (
    BASELINE_DURATION_S,
    COMPOSURE_BAR_UPDATE_HZ,
    DECEPTION_THRESHOLD_SIGMA,
    DEFAULT_CONSEQUENCE_DURATION_S,
    FAST_BASELINE_DURATION_S,
    FPS,
    INTER_DOMAIN_REST_S,
    INTRA_DOMAIN_REST_S,
    SUBJECT_ID_PATTERN,
    VALID_TRANSITIONS,
    DomainID,
    EngineState,
    EventType,
    InvalidStateTransition,
    ScenarioType,
)
from src.game.event_logger import EventLogger, GameEvent
from src.game.scenario_logic import (
    BARTRunner,
    DelayWaitRunner,
    MISTRunner,
    RewardAccumulator,
)
from src.game.scenarios import Domain, Scenario, build_domain_registry
from src.game.ui import UIRenderer
from src.game.ui_effects import (
    ButtonFlash,
    ScreenVibration,
    TextJitter,
    TimerBarColorTransition,
    UIEffectState,
)


@dataclass
class SessionConfig:
    """Runtime configuration for a single subject session."""

    subject_id: str
    fast_baseline: bool
    fullscreen: bool
    window_size: tuple[int, int]
    domain_filter: DomainID | None
    session_start_unix_ts_ms: int
    random_seed: int


class GameEngine:
    """Central game engine executing the 7-domain stress paradigm."""

    def __init__(
        self,
        config: SessionConfig,
        screen: pygame.Surface,
        bridge: BridgeInterface | None = None,
        audio: AudioController | None = None,
        logger: EventLogger | None = None,
    ) -> None:
        """Initialize engine subsystems, registries, and state machine."""
        self.config: SessionConfig = config
        self.screen: pygame.Surface = screen
        self.renderer: UIRenderer = UIRenderer(screen)
        self.bridge: BridgeInterface = bridge if bridge is not None else StubBridge()

        audio_path = Path("assets/audio/tension_drone.wav")
        self.audio: AudioController | None = audio
        if self.audio is None and audio_path.is_file():
            try:
                self.audio = AudioController(audio_path)
            except Exception:
                self.audio = None

        output_dir = Path("outputs/game_logs") / f"{config.subject_id}_{config.session_start_unix_ts_ms}"
        self.logger: EventLogger = logger if logger is not None else EventLogger(output_dir, config.subject_id)

        self._jitter: TextJitter = TextJitter()
        self._color_transition: TimerBarColorTransition = TimerBarColorTransition()
        self._vibration: ScreenVibration = ScreenVibration()
        self._button_flash: ButtonFlash = ButtonFlash()
        self._ui_effects: UIEffectState = UIEffectState()

        self._domains: list[Domain] = self._setup_domains()
        self._current_domain_idx: int = 0
        self._current_scenario_idx: int = 0
        self._scenarios_completed: int = 0

        self._current_state: EngineState = EngineState.INIT
        self._state_timer_ms: int = 0
        self._state_elapsed_ms: int = 0
        self._running: bool = False
        self._id_input_text: str = config.subject_id
        self._id_error: str | None = None
        self._consequence_text: str = ""
        self._selected_option_index: int | None = None
        self._decision_presented_ts_ms: int = 0

        self._mist_runner: MISTRunner | None = None
        self._bart_runner: BARTRunner | None = None
        self._reward_runner: RewardAccumulator | None = None
        self._delay_runner: DelayWaitRunner | None = None

        self._baseline_var_samples: list[float] = []
        self._deception_threshold: float = 0.5
        self._composure_fraction: float = 1.0
        self._composure_poll_timer_ms: int = 0

    def _setup_domains(self) -> list[Domain]:
        """Construct registry and apply filtering and shuffling."""
        registry = build_domain_registry()
        if self.config.domain_filter is not None:
            domains = [d for d in registry if d.id == self.config.domain_filter]
        else:
            domains = list(registry)
            rng = random.Random(self.config.random_seed)
            rng.shuffle(domains)
        self.logger.save_domain_order([d.id for d in domains], self.config.random_seed, self.config.session_start_unix_ts_ms)
        return domains

    def run(self) -> None:
        """Main game loop capped at 60 FPS."""
        pygame.mouse.set_visible(False)
        self._running = True
        clock = pygame.time.Clock()
        self._transition_to(EngineState.ID_INPUT)

        while self._running:
            dt_ms = clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    self._shutdown()
                    return
                self._handle_input(event)

            self._update(dt_ms)
            self._render()
            pygame.display.flip()
        self._shutdown()

    def _shutdown(self) -> None:
        """Clean shutdown closing audio and logs."""
        self._running = False
        if self.audio is not None:
            self.audio.stop_drone(fade_out_ms=100)
        self.logger.close()

    def _now_ms(self) -> int:
        """Return current epoch timestamp in milliseconds."""
        return int(time.time_ns() // 1_000_000)

    def _transition_to(self, new_state: EngineState) -> None:
        """Validate and execute state transition, logging entry events."""
        valid_targets = VALID_TRANSITIONS.get(self._current_state, set())
        if new_state not in valid_targets:
            raise InvalidStateTransition(self._current_state, new_state)

        self._current_state = new_state
        self._state_elapsed_ms = 0
        self._selected_option_index = None
        now = self._now_ms()
        curr_scenario = self._get_safe_scenario()

        if new_state == EngineState.BASELINE:
            dur_s = FAST_BASELINE_DURATION_S if self.config.fast_baseline else BASELINE_DURATION_S
            self._state_timer_ms = dur_s * 1000
            self.logger.log_event(GameEvent(now, EventType.SYNC_PULSE, "", "", "{}", None, None, None, {}))
            self.logger.log_event(GameEvent(now, EventType.BASELINE_START, "", "", "{}", None, None, None, {"duration_s": dur_s}))
        elif new_state == EngineState.PRIMING and curr_scenario:
            if self._current_scenario_idx == 0:
                self.logger.log_event(GameEvent(now, EventType.DOMAIN_START, curr_scenario.domain_id.value, "", "{}", None, None, None, {}))
            self._state_timer_ms = curr_scenario.priming_duration_s * 1000
            self.logger.log_event(GameEvent(now, EventType.SCENARIO_PRIMING, curr_scenario.domain_id.value, curr_scenario.id, "{}", None, None, None, {}))
        elif new_state == EngineState.DECISION:
            self._enter_decision(curr_scenario, now)
        elif new_state == EngineState.POST_WAIT and curr_scenario:
            self._state_timer_ms = curr_scenario.post_wait_duration_s * 1000
        elif new_state == EngineState.FEEDBACK:
            self._state_timer_ms = DEFAULT_CONSEQUENCE_DURATION_S * 1000
        elif new_state in (EngineState.INTRA_REST, EngineState.INTER_REST):
            dur_s = INTRA_DOMAIN_REST_S if new_state == EngineState.INTRA_REST else INTER_DOMAIN_REST_S
            self._state_timer_ms = dur_s * 1000
            self.logger.log_event(GameEvent(now, EventType.REST_START, "", "", "{}", None, None, None, {"is_inter": new_state == EngineState.INTER_REST}))
        elif new_state == EngineState.DEBRIEF:
            self.logger.log_event(GameEvent(now, EventType.SESSION_END, "", "", "{}", None, None, None, {"scenarios_completed": self._scenarios_completed}))

    def _enter_decision(self, scenario: Scenario | None, now_ms: int) -> None:
        """Initialize decision runners, timers, and presented event."""
        if not scenario:
            return
        self._state_timer_ms = scenario.decision_duration_s * 1000
        self._decision_presented_ts_ms = now_ms
        if scenario.scenario_type == ScenarioType.MIST_ARITHMETIC and scenario.math_problems:
            self._mist_runner = MISTRunner(scenario.math_problems, scenario.decision_duration_s)
        elif scenario.scenario_type == ScenarioType.BART_ESCALATION and scenario.bart_config:
            self._bart_runner = BARTRunner(scenario.bart_config, seed=self.config.random_seed)
        elif scenario.scenario_type == ScenarioType.REWARD_ACCUMULATOR and scenario.reward_config:
            self._reward_runner = RewardAccumulator(scenario.reward_config, seed=self.config.random_seed)
        else:
            self._mist_runner, self._bart_runner, self._reward_runner = None, None, None
        self.logger.log_event(GameEvent(now_ms, EventType.DECISION_PRESENTED, scenario.domain_id.value, scenario.id, "{}", None, None, None, {}))

    def _get_safe_scenario(self) -> Scenario | None:
        """Return active Scenario or None if outside scenario loops."""
        if self._current_domain_idx < len(self._domains):
            return self._domains[self._current_domain_idx].scenarios[self._current_scenario_idx]
        return None

    def _handle_input(self, event: pygame.event.Event) -> None:
        """Route KEYDOWN keyboard events to current state handler."""
        if event.type != pygame.KEYDOWN:
            return
        if self._current_state == EngineState.ID_INPUT:
            self._handle_id_input(event)
        elif self._current_state == EngineState.DECISION:
            self._handle_decision_input(event)

    def _handle_id_input(self, event: pygame.event.Event) -> None:
        """Process Subject ID text entry."""
        if event.key == pygame.K_RETURN:
            if re.match(SUBJECT_ID_PATTERN, self._id_input_text.strip()):
                self.config.subject_id = self._id_input_text.strip()
                self._id_error = None
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
        choice = key_map[event.key]
        scenario = self._get_safe_scenario()
        if not scenario or self._selected_option_index is not None:
            return

        now = self._now_ms()
        rt_ms = now - self._decision_presented_ts_ms

        if scenario.scenario_type == ScenarioType.MIST_ARITHMETIC and self._mist_runner:
            self._handle_mist_input(choice, scenario, now, rt_ms)
        elif scenario.scenario_type == ScenarioType.BART_ESCALATION and self._bart_runner:
            self._handle_bart_input(choice, scenario, now, rt_ms)
        elif scenario.scenario_type == ScenarioType.REWARD_ACCUMULATOR and self._reward_runner:
            self._handle_reward_input(choice, scenario, now, rt_ms)
        else:
            self._handle_standard_input(choice, scenario, now, rt_ms)

    def _handle_standard_input(self, key: int, scenario: Scenario, now: int, rt_ms: int) -> None:
        """Handle standard MCQ selection."""
        if key > len(scenario.options):
            return
        opt_idx = key - 1
        opt = scenario.options[opt_idx]
        self._selected_option_index = opt_idx
        if opt.key == 2 and scenario.delay_wait_outcomes:
            rng = random.Random(now)
            self._consequence_text = rng.choice(scenario.delay_wait_outcomes)
        else:
            self._consequence_text = opt.consequence_text
        if self.audio:
            self.audio.stop_drone()
        choice_json = json.dumps({"key": key, "text": opt.text})
        meta: dict[str, str | int | float | bool] = {"is_conforming": opt.is_conforming} if opt.is_conforming is not None else {}
        self.logger.log_event(GameEvent(now, EventType.OPTION_SELECTED, scenario.domain_id.value, scenario.id, choice_json, key, opt_idx, rt_ms, meta))
        self._transition_to(EngineState.POST_WAIT if scenario.has_post_wait else EngineState.FEEDBACK)

    def _handle_mist_input(self, key: int, scenario: Scenario, now: int, rt_ms: int) -> None:
        """Process MIST arithmetic answer input."""
        if not self._mist_runner:
            return
        is_corr, done = self._mist_runner.handle_keypress(key)
        self.logger.log_event(GameEvent(now, EventType.MATH_ANSWER, scenario.domain_id.value, scenario.id, "{}", key, key - 1, rt_ms, {"correct": is_corr}))
        if not is_corr:
            self._button_flash.trigger()
        if done:
            if self.audio:
                self.audio.stop_drone()
            acc = self._mist_runner.get_accuracy_pct()
            peer = self._mist_runner.get_peer_average_pct()
            self._consequence_text = f"Assessment complete. Your accuracy: {acc}%. Peer average: {peer}%. Results have been logged."
            self._transition_to(EngineState.FEEDBACK)

    def _handle_bart_input(self, key: int, scenario: Scenario, now: int, rt_ms: int) -> None:
        """Process BART secure or pump actions."""
        if not self._bart_runner:
            return
        if key == 1:
            val = self._bart_runner.secure()
            if self.audio:
                self.audio.stop_drone()
            rem = self._bart_runner.get_pumps_remaining_after_burst()
            self._consequence_text = f"Gains secured. System remained stable for {rem} more cycles."
            self.logger.log_event(GameEvent(now, EventType.BART_SECURE, scenario.domain_id.value, scenario.id, "{}", key, 0, rt_ms, {"value": val}))
            self._transition_to(EngineState.FEEDBACK)
        elif key == 2:
            val, burst = self._bart_runner.pump()
            self.logger.log_event(GameEvent(now, EventType.BART_PUMP, scenario.domain_id.value, scenario.id, "{}", key, 1, rt_ms, {"value": val}))
            if burst:
                if self.audio:
                    self.audio.stop_drone()
                self._consequence_text = "System failure. All accumulated progress lost."
                self.logger.log_event(GameEvent(now, EventType.BART_BURST, scenario.domain_id.value, scenario.id, "{}", key, 1, rt_ms, {}))
                self._transition_to(EngineState.FEEDBACK)

    def _handle_reward_input(self, key: int, scenario: Scenario, now: int, rt_ms: int) -> None:
        """Process reward accumulator claim action."""
        if self._reward_runner and key == 1:
            val = self._reward_runner.claim()
            if self.audio:
                self.audio.stop_drone()
            self._consequence_text = f"Reward secured. Chest value: {val}."
            self.logger.log_event(GameEvent(now, EventType.REWARD_CLAIM, scenario.domain_id.value, scenario.id, "{}", key, 0, rt_ms, {"value": val}))
            self._transition_to(EngineState.FEEDBACK)

    def _update(self, dt_ms: int) -> None:
        """Advance state timers, UI effects, and runners each frame."""
        if dt_ms <= 0:
            return
        self._state_elapsed_ms += dt_ms
        self._button_flash.update(dt_ms)
        self._ui_effects.is_flashing = self._button_flash.is_flashing()

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

    def _update_decision(self, dt_ms: int) -> None:
        """Update decision countdown, audio trigger, jitter, and collapse checks."""
        scenario = self._get_safe_scenario()
        if not scenario:
            return
        self._state_timer_ms = max(0, self._state_timer_ms - dt_ms)
        frac = self._state_timer_ms / float(scenario.decision_duration_s * 1000)

        if self.audio and frac <= scenario.drone_trigger_fraction:
            self.audio.start_drone()
        self._ui_effects.timer_bar_color = self._color_transition.get_color(frac)
        if scenario.jitter_trigger_s and self._state_timer_ms <= scenario.jitter_trigger_s * 1000:
            self._ui_effects.jitter_offset = self._jitter.get_offset(self._state_elapsed_ms)
        else:
            self._ui_effects.jitter_offset = (0, 0)

        if self._reward_runner and self._reward_runner.update(dt_ms):
            if self.audio:
                self.audio.stop_drone()
            self._consequence_text = "Chest collapsed. All accumulated value lost."
            self.logger.log_event(GameEvent(self._now_ms(), EventType.REWARD_COLLAPSE, scenario.domain_id.value, scenario.id, "{}", None, None, None, {}))
            self._transition_to(EngineState.FEEDBACK)
            return

        if scenario.has_deception_metric:
            self._composure_poll_timer_ms += dt_ms
            if self._composure_poll_timer_ms >= int(1000 / COMPOSURE_BAR_UPDATE_HZ):
                self._composure_poll_timer_ms = 0
                var = self.bridge.get_mpu_variance()
                if var is not None and var > self._deception_threshold:
                    self._composure_fraction = max(0.1, self._composure_fraction - 0.15)
                    self.logger.log_event(GameEvent(self._now_ms(), EventType.DECEPTION_TRIGGER, scenario.domain_id.value, scenario.id, "{}", None, None, None, {"mpu_var": var}))
                else:
                    self._composure_fraction = min(1.0, self._composure_fraction + 0.05)

        if self._state_timer_ms <= 0:
            if self.audio:
                self.audio.stop_drone()
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
            self.renderer.draw_priming(scenario, self._state_elapsed_ms / 1000.0)
        elif self._current_state == EngineState.DECISION and scenario:
            comp = self._composure_fraction if scenario.has_deception_metric else None
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
