"""Tests for the interface rules of the UI review (ADR-B9): settings, held state, waits, honest prompts."""
from __future__ import annotations

import re

import pygame

from src.game.constants import DomainID, ScenarioType
from src.game.scenario_logic import MISTRunner, RewardAccumulator
from src.game.scenarios import Domain, get_domain_by_id
from src.game.ui import UIRenderer
from src.game.ui_effects import UIEffectState
from src.game.ui_screens import SETTING_LABELS


def _drawn_text(renderer: UIRenderer) -> list[tuple[str, pygame.Rect]]:
    """Record every string the renderer draws from now on, with the rect it was drawn in."""
    drawn: list[tuple[str, pygame.Rect]] = []
    original = renderer._draw_text

    def spy(text: str, *args: object, **kwargs: object) -> pygame.Rect:
        rect = original(text, *args, **kwargs)  # type: ignore[arg-type]
        drawn.append((text, rect))
        return rect

    renderer._draw_text = spy  # type: ignore[method-assign]
    return drawn


def test_briefing_names_the_setting_not_the_research_domain(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify the priming screen and the briefing popup show where the scenario happens, never the domain name."""
    renderer = UIRenderer(screen)
    drawn = _drawn_text(renderer)
    for domain in domain_registry:
        for scenario in domain.scenarios:
            assert scenario.skin in SETTING_LABELS, scenario.skin
            domain_words = scenario.domain_id.value.replace("_", " ").upper()
            for popup in (False, True):
                drawn.clear()
                if popup:
                    renderer.draw_question_popup(scenario)
                else:
                    renderer.draw_priming(scenario, 3.0, skip_available=False)
                texts = [text.upper() for text, _ in drawn]
                assert not any(domain_words in text for text in texts), scenario.id
                assert any(SETTING_LABELS[scenario.skin] in text for text in texts), scenario.id


def test_committed_choice_changes_the_footer_to_a_stillness_prompt(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify every skin that commits one option tells the participant the response is recorded, and only then."""
    renderer = UIRenderer(screen)
    drawn = _drawn_text(renderer)
    checked = 0
    for domain in domain_registry:
        for scenario in domain.scenarios:
            if scenario.scenario_type not in (ScenarioType.STANDARD_MCQ, ScenarioType.DELAY_WAIT):
                continue
            for selected, expected in ((None, False), (0, True)):
                drawn.clear()
                renderer.draw_decision(scenario, 30.0, selected, UIEffectState(), None, None, None, None)
                assert any("RESPONSE RECORDED" in text for text, _ in drawn) is expected, f"{scenario.skin} selected={selected}"
            checked += 1
    assert checked == 11


def test_wait_screens_say_nothing_about_the_wait(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify a post-decision wait never states its length or that information is being withheld."""
    # A clock face, a file name, or a bearing may carry digits; a duration is a number with a time unit
    duration = re.compile(r"\d+\s*-?\s*(s\b|sec|min)", re.IGNORECASE)
    withheld = re.compile(r"embargo|feedback|withheld|maintained|uncalibrated|revealed", re.IGNORECASE)
    renderer = UIRenderer(screen)
    drawn = _drawn_text(renderer)
    waits = [scenario for domain in domain_registry for scenario in domain.scenarios if scenario.post_wait_text]
    assert len(waits) == 3
    for scenario in waits:
        drawn.clear()
        renderer.draw_post_wait(scenario.post_wait_text, 0.5)
        texts = [text for text, _ in drawn]
        assert scenario.post_wait_text in texts, scenario.id
        assert not [text for text in texts if duration.search(text) or withheld.search(text)], scenario.id
    assert duration.search("12-second algorithmic projection") and duration.search("ready in 10 s")
    assert not duration.search("23:42") and not duration.search("BEARING 115") and not duration.search("Words: 3,420")


def test_reward_waiting_carries_no_key_prompt(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify the reward chest prompts only the key the engine accepts: waiting is passive and has no badge."""
    scenario = get_domain_by_id(domain_registry, DomainID.IMPULSIVITY_GRATIFICATION).scenarios[0]
    assert scenario.reward_config is not None
    renderer = UIRenderer(screen)
    badges: list[str] = []
    original = renderer._draw_key_badge

    def spy(rect: pygame.Rect, label: str, selected: bool = False, enabled: bool = True) -> None:
        badges.append(label)
        original(rect, label, selected=selected, enabled=enabled)

    renderer._draw_key_badge = spy  # type: ignore[method-assign]
    renderer.draw_decision(scenario, 30.0, None, UIEffectState(), None, None, RewardAccumulator(scenario.reward_config, seed=42), None)
    assert badges == ["1"]


def test_exam_wrong_mark_does_not_cover_the_question(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify the wrong-answer stamp sits clear of the arithmetic item that is on the page while it shows."""
    scenario = get_domain_by_id(domain_registry, DomainID.ACADEMIC_PRESSURE).scenarios[0]
    assert scenario.math_problems is not None
    runner = MISTRunner(scenario.math_problems, scenario.decision_duration_s)
    problem = runner.get_current_problem()
    assert problem is not None
    renderer = UIRenderer(screen)
    drawn = _drawn_text(renderer)
    renderer.draw_decision(scenario, 30.0, None, UIEffectState(is_flashing=True), runner, None, None, None)
    rects = dict(drawn)
    assert "INCORRECT" in rects
    assert not rects["INCORRECT"].colliderect(rects[problem.question_text])

    drawn.clear()
    renderer.draw_decision(scenario, 30.0, None, UIEffectState(is_flashing=False), runner, None, None, None)
    assert "INCORRECT" not in dict(drawn)
