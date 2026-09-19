"""Unit tests for UIRenderer skin dispatching, stubs, and fallback rendering."""
from __future__ import annotations

import pygame
import pytest

from src.game.constants import DomainID, ScenarioType
from src.game.scenarios import Domain, Scenario
from src.game.ui import UIRenderer
from src.game.ui_effects import UIEffectState


def test_skin_stubs_exist(screen: pygame.Surface) -> None:
    """Verify all 14 domain-specific simulation skin stubs exist on UIRenderer."""
    renderer = UIRenderer(screen)
    canonical_skins = [
        "exam_hall",
        "misconduct_hearing",
        "group_chat",
        "team_kanban",
        "reward_crate",
        "document_workspace",
        "tournament_bracket",
        "social_analytics",
        "portal_log",
        "code_diff",
        "fork_map",
        "notification_stack",
        "defense_stage",
        "classroom_critique",
    ]
    for skin in canonical_skins:
        method_name = f"_draw_skin_{skin}"
        assert hasattr(renderer, method_name), f"Missing stub method {method_name}"
        method = getattr(renderer, method_name)
        assert callable(method)


def test_skin_stubs_return_false(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify that un-implemented skin stubs return False by default so they fall back to default UI."""
    renderer = UIRenderer(screen)
    effects = UIEffectState()

    implemented_skins = {
        "exam_hall",
        "misconduct_hearing",
        "group_chat",
        "team_kanban",
        "reward_crate",
        "document_workspace",
        "tournament_bracket",
        "social_analytics",
        "portal_log",
        "code_diff",
        "fork_map",
        "notification_stack",
        "defense_stage",
        "classroom_critique",
    }

    for domain in domain_registry:
        for scenario in domain.scenarios:
            assert scenario.skin != ""
            if scenario.skin in implemented_skins:
                continue
            result = renderer._render_skin(
                scenario=scenario,
                time_remaining_s=10.0,
                selected_index=None,
                effects=effects,
                mist_runner=None,
                bart_runner=None,
                reward_runner=None,
                composure_fraction=1.0,
            )
            assert result is False, f"Expected skin {scenario.skin} stub to return False"


def test_academic_pressure_skins(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify procedural rendering for Domain 1 (Academic Pressure) simulation skins."""
    from src.game.constants import DomainID
    from src.game.scenario_logic import MISTRunner
    from src.game.scenarios import get_domain_by_id

    renderer = UIRenderer(screen)
    effects = UIEffectState()
    acad_domain = get_domain_by_id(domain_registry, DomainID.ACADEMIC_PRESSURE)
    scen_a = acad_domain.scenarios[0]
    scen_b = acad_domain.scenarios[1]

    # Scenario A (exam_hall) with missing mist_runner falls back
    assert renderer._render_skin(scen_a, 25.0, None, effects, None, None, None, None) is False

    # Scenario A (exam_hall) with MISTRunner renders successfully
    assert scen_a.math_problems is not None
    runner = MISTRunner(scen_a.math_problems, total_duration_s=scen_a.decision_duration_s)
    assert renderer._render_skin(scen_a, 25.0, 0, effects, runner, None, None, None) is True

    # Scenario A with time <= 20.0 (triggers pacing invigilator) and flashing error X
    flash_effects = UIEffectState(is_flashing=True)
    assert renderer._render_skin(scen_a, 15.0, 1, flash_effects, runner, None, None, None) is True

    # Scenario B (misconduct_hearing) renders successfully
    assert renderer._render_skin(scen_b, 40.0, 0, effects, None, None, None, None) is True

    # Verify draw_decision works for both Domain 1 scenarios
    renderer.draw_decision(scen_a, 18.0, 0, effects, runner, None, None, 1.0)
    renderer.draw_decision(scen_b, 30.0, 2, effects, None, None, None, 1.0)


def test_peer_influence_skins(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify procedural rendering for Domain 2 (Peer Influence) simulation skins."""
    from src.game.constants import DomainID
    from src.game.scenarios import get_domain_by_id

    renderer = UIRenderer(screen)
    effects = UIEffectState()
    peer_domain = get_domain_by_id(domain_registry, DomainID.PEER_INFLUENCE)
    scen_a = peer_domain.scenarios[0]
    scen_b = peer_domain.scenarios[1]

    # Scenario A (group_chat): unselected shows typing indicator
    assert renderer._render_skin(scen_a, 20.0, None, effects, None, None, None, None) is True

    # Scenario A (group_chat): selected choice 0 (conforming) and choice 1 (dissent)
    assert renderer._render_skin(scen_a, 15.0, 0, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_a, 10.0, 1, effects, None, None, None, None) is True

    # Scenario B (team_kanban): unselected and selected
    assert renderer._render_skin(scen_b, 30.0, None, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_b, 25.0, 1, effects, None, None, None, None) is True

    # Verify draw_decision works for both Domain 2 scenarios
    renderer.draw_decision(scen_a, 20.0, 0, effects, None, None, None, None)
    renderer.draw_decision(scen_b, 25.0, 1, effects, None, None, None, None)


def test_impulsivity_skins(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify procedural rendering for Domain 3 (Impulsivity vs. Delayed Gratification) simulation skins."""
    from src.game.constants import DomainID
    from src.game.scenario_logic import RewardAccumulator
    from src.game.scenarios import get_domain_by_id

    renderer = UIRenderer(screen)
    effects = UIEffectState(vibration_offset=(2, -2))
    imp_domain = get_domain_by_id(domain_registry, DomainID.IMPULSIVITY_GRATIFICATION)
    scen_a = imp_domain.scenarios[0]
    scen_b = imp_domain.scenarios[1]

    # Scenario A (reward_crate): missing reward_runner falls back
    assert renderer._render_skin(scen_a, 40.0, None, effects, None, None, None, None) is False

    # Scenario A (reward_crate) with RewardAccumulator renders successfully
    assert scen_a.reward_config is not None
    reward_runner = RewardAccumulator(scen_a.reward_config, seed=42)
    assert renderer._render_skin(scen_a, 40.0, None, effects, None, None, reward_runner, None) is True
    assert renderer._render_skin(scen_a, 35.0, 0, effects, None, None, reward_runner, None) is True
    assert renderer._render_skin(scen_a, 30.0, 1, effects, None, None, reward_runner, None) is True

    # Scenario A on collapse: trigger shatter effect
    reward_runner.is_collapsed = True
    assert renderer._render_skin(scen_a, 20.0, None, effects, None, None, reward_runner, None) is True
    assert renderer.shatter_effect.is_active is True
    assert len(renderer.shatter_effect.particles) == 12

    # Scenario B (document_workspace) renders successfully with margins, text lines, options
    assert renderer._render_skin(scen_b, 30.0, None, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_b, 25.0, 0, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_b, 20.0, 1, effects, None, None, None, None) is True

    # Scenario B POST_WAIT delay wait animation
    renderer.draw_post_wait(scen_b.post_wait_text, 0.45)
    renderer.draw_post_wait("Generic wait...", 0.5)

    # Verify draw_decision works for both Domain 3 scenarios
    reward_active = RewardAccumulator(scen_a.reward_config, seed=123)
    renderer.draw_decision(scen_a, 38.0, 0, effects, None, None, reward_active, None)
    renderer.draw_decision(scen_b, 28.0, 1, effects, None, None, None, None)

    # Verify feedback with collapse consequence disperses shatter particles
    renderer.draw_feedback("Chest collapsed. All accumulated value lost.", 1.0)


def test_risk_reward_skins(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify procedural rendering for Domain 4 (Risk-Reward Tradeoff) simulation skins."""
    from src.game.constants import DomainID
    from src.game.scenario_logic import BARTRunner
    from src.game.scenarios import get_domain_by_id

    renderer = UIRenderer(screen)
    effects = UIEffectState(vibration_offset=(-1, 2))
    rr_domain = get_domain_by_id(domain_registry, DomainID.RISK_REWARD)
    scen_a = rr_domain.scenarios[0]
    scen_b = rr_domain.scenarios[1]

    # Scenario A (tournament_bracket): unselected and all 3 strategy options
    assert renderer._render_skin(scen_a, 35.0, None, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_a, 30.0, 0, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_a, 25.0, 1, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_a, 20.0, 2, effects, None, None, None, None) is True

    # Scenario B (social_analytics): missing bart_runner falls back
    assert renderer._render_skin(scen_b, 35.0, None, effects, None, None, None, None) is False

    # Scenario B (social_analytics) with BARTRunner active
    assert scen_b.bart_config is not None
    bart_runner = BARTRunner(scen_b.bart_config, seed=42)
    assert renderer._render_skin(scen_b, 35.0, None, effects, None, bart_runner, None, None) is True
    assert renderer._render_skin(scen_b, 30.0, 0, effects, None, bart_runner, None, None) is True
    assert renderer._render_skin(scen_b, 25.0, 1, effects, None, bart_runner, None, None) is True

    # Scenario B with pumps and elevated risk
    bart_runner.pump()
    bart_runner.pump()
    assert renderer._render_skin(scen_b, 20.0, 1, effects, None, bart_runner, None, None) is True

    # Scenario B on burst: shows ACCOUNT SUSPENDED splash card
    bart_runner.is_burst = True
    assert renderer._render_skin(scen_b, 15.0, None, effects, None, bart_runner, None, None) is True

    # Verify draw_decision works for both Domain 4 scenarios
    bart_fresh = BARTRunner(scen_b.bart_config, seed=99)
    renderer.draw_decision(scen_a, 32.0, 1, effects, None, None, None, None)
    renderer.draw_decision(scen_b, 24.0, 0, effects, None, bart_fresh, None, None)

    # Verify draw_feedback with account suspension consequence
    renderer.draw_feedback("System failure. All accumulated progress lost.", 1.2)


def test_rule_ambiguity_skins(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify procedural rendering for Domain 5 (Rule-Boundary Ambiguity) simulation skins."""
    from src.game.constants import DomainID
    from src.game.scenarios import get_domain_by_id

    renderer = UIRenderer(screen)
    effects = UIEffectState(vibration_offset=(1, -1), jitter_offset=(2, -2))
    ra_domain = get_domain_by_id(domain_registry, DomainID.RULE_AMBIGUITY)
    scen_a = ra_domain.scenarios[0]
    scen_b = ra_domain.scenarios[1]

    # Scenario A (portal_log): unselected and all 3 decision options
    assert renderer._render_skin(scen_a, 35.0, None, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_a, 30.0, 0, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_a, 25.0, 1, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_a, 20.0, 2, effects, None, None, None, None) is True

    # Scenario A: Diegetic urgency test (time <= 15.0 triggers timestamp jitter)
    assert renderer._render_skin(scen_a, 12.0, 0, effects, None, None, None, None) is True
    default_effects = UIEffectState()
    assert renderer._render_skin(scen_a, 10.0, None, default_effects, None, None, None, None) is True

    # Scenario B (code_diff): unselected and all 3 decision options
    assert renderer._render_skin(scen_b, 35.0, None, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_b, 30.0, 0, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_b, 25.0, 1, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_b, 20.0, 2, effects, None, None, None, None) is True

    # Verify draw_decision works for both Domain 5 scenarios
    renderer.draw_decision(scen_a, 14.0, 0, effects, None, None, None, None)
    renderer.draw_decision(scen_b, 28.0, 2, effects, None, None, None, None)

    # Verify draw_feedback with Domain 5 consequence text
    renderer.draw_feedback("Sections removed. Project delayed by several days before submission.", 1.0)


def test_future_uncertainty_skins(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify procedural rendering for Domain 6 (Future Uncertainty) simulation skins."""
    from src.game.constants import DomainID
    from src.game.scenarios import get_domain_by_id

    renderer = UIRenderer(screen)
    effects = UIEffectState(vibration_offset=(1, -1), jitter_offset=(-1, 1))
    fu_domain = get_domain_by_id(domain_registry, DomainID.FUTURE_UNCERTAINTY)
    scen_a = fu_domain.scenarios[0]
    scen_b = fu_domain.scenarios[1]

    # Scenario A (fork_map): unselected, choice 0 (Path A), and choice 1 (Path B)
    assert renderer._render_skin(scen_a, 40.0, None, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_a, 35.0, 0, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_a, 30.0, 1, effects, None, None, None, None) is True
    assert renderer._last_fork_choice == 1

    # Scenario A (fork_map): POST_WAIT delay wait suspension
    renderer.draw_post_wait(scen_a.post_wait_text, 0.45)
    renderer.draw_post_wait("Synthesizing outcome projections...", 0.8)

    # Scenario B (notification_stack): unselected and all 3 response options
    assert renderer._render_skin(scen_b, 35.0, None, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_b, 30.0, 0, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_b, 25.0, 1, effects, None, None, None, None) is True
    assert renderer._render_skin(scen_b, 20.0, 2, effects, None, None, None, None) is True

    # Scenario B (notification_stack): POST_WAIT delay wait recalculation
    renderer.draw_post_wait(scen_b.post_wait_text, 0.5)
    renderer.draw_post_wait("Recalculating assessment parameters...", 0.9)

    # Verify draw_decision works for both Domain 6 scenarios
    renderer.draw_decision(scen_a, 24.0, 0, effects, None, None, None, None)
    renderer.draw_decision(scen_b, 18.0, 1, effects, None, None, None, None)

    # Verify draw_feedback with Domain 6 consequence text
    renderer.draw_feedback("Assessment updated. Your response pattern has been flagged for secondary review.", 1.0)


def test_social_evaluation_skins(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify procedural rendering for Domain 7 (Social Evaluation & Authority Response) simulation skins."""
    from src.game.constants import DomainID
    from src.game.scenarios import get_domain_by_id

    renderer = UIRenderer(screen)
    effects = UIEffectState()
    jitter_effects = UIEffectState(jitter_offset=(2, -2))
    soc_domain = get_domain_by_id(domain_registry, DomainID.SOCIAL_EVALUATION)
    scen_a = soc_domain.scenarios[0]
    scen_b = soc_domain.scenarios[1]

    assert scen_a.skin == "defense_stage"
    assert scen_b.skin == "classroom_critique"
    assert scen_a.has_deception_metric is True
    assert scen_b.has_deception_metric is True

    # Scenario A (defense_stage): unselected and selected options
    assert renderer._render_skin(scen_a, 35.0, None, effects, None, None, None, 1.0) is True
    assert renderer._render_skin(scen_a, 30.0, 0, effects, None, None, None, 0.8) is True
    assert renderer._render_skin(scen_a, 25.0, 1, effects, None, None, None, 0.45) is True
    assert renderer._render_skin(scen_a, 20.0, 2, effects, None, None, None, 0.15) is True
    # Scenario A with None composure (calibrating baseline)
    assert renderer._render_skin(scen_a, 20.0, 0, effects, None, None, None, None) is True
    # Scenario A with diegetic tension drone active (time <= 45 * 0.333 = 14.985s) and jitter
    assert renderer._render_skin(scen_a, 10.0, 0, jitter_effects, None, None, None, 0.25) is True

    # Scenario B (classroom_critique): unselected and selected options
    assert renderer._render_skin(scen_b, 30.0, None, effects, None, None, None, 1.0) is True
    assert renderer._render_skin(scen_b, 25.0, 0, effects, None, None, None, 0.75) is True
    assert renderer._render_skin(scen_b, 20.0, 1, effects, None, None, None, 0.5) is True
    assert renderer._render_skin(scen_b, 15.0, 2, effects, None, None, None, 0.1) is True
    # Scenario B with None composure
    assert renderer._render_skin(scen_b, 15.0, 1, effects, None, None, None, None) is True
    # Scenario B with diegetic tension drone active (time <= 40 * 0.333 = 13.32s)
    assert renderer._render_skin(scen_b, 8.0, 2, jitter_effects, None, None, None, 0.2) is True

    # Direct test of draw_composure_bar with various fractions and drone states
    renderer.draw_composure_bar(1.0, (50, 650))
    renderer.draw_composure_bar(0.5, (50, 650), width=1000, is_drone_active=True)
    renderer.draw_composure_bar(0.1, (50, 650), width=1000, is_drone_active=True)

    # Verify draw_decision works end-to-end for both Domain 7 scenarios
    renderer.draw_decision(scen_a, 20.0, 0, effects, None, None, None, 0.9)
    renderer.draw_decision(scen_b, 15.0, 1, effects, None, None, None, 0.35)

    # Verify draw_feedback with Domain 7 consequence text
    renderer.draw_feedback("The panel has recorded your response. Composure score: evaluated.", 1.0)



def test_render_skin_fallback_on_empty_or_unknown(screen: pygame.Surface) -> None:
    """Verify _render_skin returns False on empty string or unrecognized skin IDs."""
    renderer = UIRenderer(screen)
    effects = UIEffectState()

    dummy_empty = Scenario(
        id="dummy_empty",
        domain_id=DomainID.ACADEMIC_PRESSURE,
        title="Empty Skin",
        paradigm="test",
        priming_text="test",
        priming_duration_s=5,
        decision_duration_s=10,
        consequence_duration_s=5,
        options=[],
        scenario_type=ScenarioType.STANDARD_MCQ,
        skin="",
    )
    assert (
        renderer._render_skin(
            scenario=dummy_empty,
            time_remaining_s=10.0,
            selected_index=None,
            effects=effects,
            mist_runner=None,
            bart_runner=None,
            reward_runner=None,
            composure_fraction=1.0,
        )
        is False
    )

    dummy_unknown = Scenario(
        id="dummy_unknown",
        domain_id=DomainID.ACADEMIC_PRESSURE,
        title="Unknown Skin",
        paradigm="test",
        priming_text="test",
        priming_duration_s=5,
        decision_duration_s=10,
        consequence_duration_s=5,
        options=[],
        scenario_type=ScenarioType.STANDARD_MCQ,
        skin="non_existent_skin_xyz",
    )
    assert (
        renderer._render_skin(
            scenario=dummy_unknown,
            time_remaining_s=10.0,
            selected_index=None,
            effects=effects,
            mist_runner=None,
            bart_runner=None,
            reward_runner=None,
            composure_fraction=1.0,
        )
        is False
    )


def test_render_skin_dispatches_when_implemented(
    screen: pygame.Surface,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify _render_skin returns True when a skin stub is implemented/returns True."""
    renderer = UIRenderer(screen)
    effects = UIEffectState()

    dummy_scenario = Scenario(
        id="dummy_custom",
        domain_id=DomainID.ACADEMIC_PRESSURE,
        title="Custom Skin",
        paradigm="test",
        priming_text="test",
        priming_duration_s=5,
        decision_duration_s=10,
        consequence_duration_s=5,
        options=[],
        scenario_type=ScenarioType.STANDARD_MCQ,
        skin="exam_hall",
    )

    # Monkeypatch stub to simulate implemented skin returning True
    called = []

    def mock_exam_hall(*args: object, **kwargs: object) -> bool:
        called.append(True)
        return True

    monkeypatch.setattr(renderer, "_draw_skin_exam_hall", mock_exam_hall)

    result = renderer._render_skin(
        scenario=dummy_scenario,
        time_remaining_s=10.0,
        selected_index=0,
        effects=effects,
        mist_runner=None,
        bart_runner=None,
        reward_runner=None,
        composure_fraction=1.0,
    )
    assert result is True
    assert len(called) == 1


def test_draw_decision_renders_all_scenarios(
    screen: pygame.Surface,
    domain_registry: list[Domain],
) -> None:
    """Verify draw_decision safely executes across all 14 scenarios via fallback."""
    renderer = UIRenderer(screen)
    effects = UIEffectState()

    for domain in domain_registry:
        for scenario in domain.scenarios:
            renderer.draw_decision(
                scenario=scenario,
                time_remaining_s=5.0,
                selected_index=0,
                effects=effects,
                mist_runner=None,
                bart_runner=None,
                reward_runner=None,
                composure_fraction=1.0,
            )
            # Ensure drawing did not crash and screen surface is valid
            assert renderer.screen.get_width() == 1280

