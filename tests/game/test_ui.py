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
    """Verify that all skin stubs return False by default so they fall back to default UI."""
    renderer = UIRenderer(screen)
    effects = UIEffectState()

    for domain in domain_registry:
        for scenario in domain.scenarios:
            assert scenario.skin != ""
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

