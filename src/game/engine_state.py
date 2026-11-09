"""Session configuration and the state-machine core of the Pulse engine."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path

import pygame

from src.game.audio import AudioController
from src.game.bridge_interface import BridgeInterface, StubBridge
from src.game.constants import (
    BART_PUMP_COOLDOWN_MS,
    BASELINE_DURATION_S,
    DEFAULT_CONSEQUENCE_DURATION_S,
    FAST_BASELINE_DURATION_S,
    INTER_DOMAIN_REST_S,
    INTRA_DOMAIN_REST_S,
    MIST_RUNTIME_PROBLEM_COUNT,
    VALID_TRANSITIONS,
    AudioLoadError,
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
from src.game.scenarios import (
    Domain,
    Scenario,
    build_domain_registry,
    generate_math_problems,
)
from src.game.ui import UIRenderer
from src.game.ui_effects import (
    ButtonFlash,
    ScreenVibration,
    TextJitter,
    TimerBarColorTransition,
    UIEffectState,
)

_SCENARIO_STATES: frozenset[EngineState] = frozenset(
    {EngineState.PRIMING, EngineState.DECISION, EngineState.POST_WAIT, EngineState.FEEDBACK}
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
    hold_full_decision: bool = False
    min_priming_s: int = 0
    min_active_epoch_s: int = 0
    inter_domain_rest_s: float = float(INTER_DOMAIN_REST_S)


def session_output_dir(config: SessionConfig) -> Path:
    """Return the per-session log directory shared by the event log and the bridge recording."""
    return Path("outputs/game_logs") / f"{config.subject_id}_{config.session_start_unix_ts_ms}"


class EngineBase:
    """Owns engine state, validated transitions, decision entry/exit, and the exposure floors."""

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
            except AudioLoadError:
                # Audio is non-critical; its absence is recorded in the SYNC_PULSE metadata
                self.audio = None

        self.logger: EventLogger = logger if logger is not None else EventLogger(session_output_dir(config), config.subject_id)

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
        self._decision_presented_mono_ms: int = 0
        self._last_response_mono_ms: int = 0
        self._pending_exit: EngineState | None = None
        self._focus_paused: bool = False
        self._is_question_popup_active: bool = False

        self._mist_runner: MISTRunner | None = None
        self._bart_runner: BARTRunner | None = None
        self._reward_runner: RewardAccumulator | None = None
        self._delay_runner: DelayWaitRunner | None = None

        self._baseline_var_samples: list[float] = []
        self._deception_threshold: float = 0.5
        self._composure_fraction: float = 1.0
        self._composure_poll_timer_ms: int = 0
        self._composure_over_count: int = 0
        self._composure_cooldown_ms: int = 0
        self._telemetry_live: bool = False

        self._last_wall_ms: int = 0
        self._rng: random.Random = random.Random(config.random_seed)

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

    def _shutdown(self) -> None:
        """Clean shutdown closing audio, the sensor bridge, and logs."""
        self._running = False
        if self.audio is not None:
            self.audio.stop_drone(fade_out_ms=100)
        self.bridge.close()
        self.logger.close()

    def _now_ms(self) -> int:
        """Return current epoch timestamp in milliseconds."""
        return int(time.time_ns() // 1_000_000)

    def _mono_ms(self) -> int:
        """Return a monotonic millisecond clock for reaction-time intervals (immune to wall-clock steps)."""
        return time.perf_counter_ns() // 1_000_000

    def _event_context(self) -> tuple[str, str]:
        """Return (domain, scenario_id) while inside a scenario, else empty strings."""
        scenario = self._get_safe_scenario()
        if scenario and self._current_state in _SCENARIO_STATES:
            return (scenario.domain_id.value, scenario.id)
        return ("", "")

    def _log_abort(self) -> None:
        """Record an early exit so truncated sessions are distinguishable from completed ones."""
        if self._current_state == EngineState.DEBRIEF:
            return
        meta: dict[str, str | int | float | bool] = {
            "scenarios_completed": self._scenarios_completed,
            "aborted": True,
            "state": self._current_state.value,
        }
        self.logger.log_event(GameEvent(self._now_ms(), EventType.SESSION_END, "", "", "{}", None, None, None, meta))

    def _transition_to(self, new_state: EngineState) -> None:
        """Validate and execute state transition, logging entry events."""
        valid_targets = VALID_TRANSITIONS.get(self._current_state, set())
        if new_state not in valid_targets:
            raise InvalidStateTransition(self._current_state, new_state)

        self._current_state = new_state
        self._state_elapsed_ms = 0
        self._selected_option_index = None
        self._pending_exit = None
        self._is_question_popup_active = False
        now = self._now_ms()
        curr_scenario = self._get_safe_scenario()

        if new_state == EngineState.BASELINE:
            dur_s = FAST_BASELINE_DURATION_S if self.config.fast_baseline else BASELINE_DURATION_S
            self._state_timer_ms = dur_s * 1000
            sync_meta: dict[str, str | int | float | bool] = {
                "bridge": type(self.bridge).__name__,
                "audio_loaded": self.audio is not None,
                "hold_full_decision": self.config.hold_full_decision,
                "min_priming_s": self.config.min_priming_s,
                "min_active_epoch_s": self.config.min_active_epoch_s,
                "inter_domain_rest_s": self.config.inter_domain_rest_s,
            }
            self.logger.log_event(GameEvent(now, EventType.SYNC_PULSE, "", "", "{}", None, None, None, sync_meta))
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
            is_inter = new_state == EngineState.INTER_REST
            rest_s = self.config.inter_domain_rest_s if is_inter else float(INTRA_DOMAIN_REST_S)
            self._state_timer_ms = int(rest_s * 1000)
            rest_meta: dict[str, str | int | float | bool] = {"is_inter": is_inter, "duration_s": rest_s}
            self.logger.log_event(GameEvent(now, EventType.REST_START, "", "", "{}", None, None, None, rest_meta))
        elif new_state == EngineState.DEBRIEF:
            self.logger.log_event(GameEvent(now, EventType.SESSION_END, "", "", "{}", None, None, None, {"scenarios_completed": self._scenarios_completed}))

    def _enter_decision(self, scenario: Scenario | None, now_ms: int) -> None:
        """Initialize decision runners, timers, and presented event."""
        if not scenario:
            return
        self._state_timer_ms = scenario.decision_duration_s * 1000
        self._decision_presented_mono_ms = self._mono_ms()
        self._last_response_mono_ms = self._decision_presented_mono_ms
        # Runners and composure never carry over from a previous scenario
        self._mist_runner, self._bart_runner, self._reward_runner = None, None, None
        self._composure_fraction = 1.0
        self._composure_poll_timer_ms = 0
        self._composure_over_count = 0
        self._composure_cooldown_ms = 0
        if scenario.scenario_type == ScenarioType.MIST_ARITHMETIC and scenario.math_problems:
            # Enough problems to fill the whole window: MIST ends on the clock, not on item count
            problems = generate_math_problems(max(MIST_RUNTIME_PROBLEM_COUNT, len(scenario.math_problems)))
            self._mist_runner = MISTRunner(problems, scenario.decision_duration_s)
        elif scenario.scenario_type == ScenarioType.BART_ESCALATION and scenario.bart_config:
            self._bart_runner = BARTRunner(scenario.bart_config, seed=self.config.random_seed, cooldown_ms=BART_PUMP_COOLDOWN_MS)
        elif scenario.scenario_type == ScenarioType.REWARD_ACCUMULATOR and scenario.reward_config:
            self._reward_runner = RewardAccumulator(scenario.reward_config, seed=self.config.random_seed)
        self.logger.log_event(GameEvent(now_ms, EventType.DECISION_PRESENTED, scenario.domain_id.value, scenario.id, "{}", None, None, None, {}))

    def _get_safe_scenario(self) -> Scenario | None:
        """Return active Scenario or None if outside scenario loops."""
        if self._current_domain_idx < len(self._domains):
            return self._domains[self._current_domain_idx].scenarios[self._current_scenario_idx]
        return None

    def _decision_floor_ms(self, scenario: Scenario) -> int:
        """Return how long DECISION must stay on screen: the whole window when the hold is enabled."""
        return scenario.decision_duration_s * 1000 if self.config.hold_full_decision else 0

    def _priming_floor_ms(self, scenario: Scenario) -> int:
        """Return the earliest skip point that keeps PRIMING + DECISION + FEEDBACK at or above the active epoch."""
        epoch_gap_s = self.config.min_active_epoch_s - scenario.decision_duration_s - DEFAULT_CONSEQUENCE_DURATION_S
        return max(self.config.min_priming_s, epoch_gap_s, 0) * 1000

    def _exit_decision(self, next_state: EngineState) -> None:
        """Leave DECISION now, or keep the committed outcome on screen until the decision timer expires."""
        scenario = self._get_safe_scenario()
        floor_ms = self._decision_floor_ms(scenario) if scenario else 0
        if self._state_elapsed_ms >= floor_ms:
            if self.audio:
                self.audio.stop_drone()
            self._transition_to(next_state)
        else:
            self._pending_exit = next_state

    def _mist_summary(self) -> str:
        """Return the MIST consequence line with the peer figure capped at a possible value."""
        if not self._mist_runner:
            return "Assessment complete."
        acc = self._mist_runner.get_accuracy_pct()
        peer = min(100, self._mist_runner.get_peer_average_pct())
        return f"Assessment complete. Your accuracy: {acc}%. Peer average: {peer}%. Results have been logged."
