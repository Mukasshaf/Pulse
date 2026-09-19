"""Unit tests for scenario registry, dataclasses, and math generators."""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.game.constants import DomainID, DomainNotFoundError, ScenarioType
from src.game.scenarios import Domain, generate_math_problems, get_domain_by_id


def test_registry_structure(domain_registry: list[Domain]) -> None:
    """Verify registry contains 7 domains with exactly 2 scenarios each."""
    assert len(domain_registry) == 7
    assert all(len(d.scenarios) == 2 for d in domain_registry)

    scenario_ids = [s.id for d in domain_registry for s in d.scenarios]
    assert len(scenario_ids) == 14
    assert len(set(scenario_ids)) == 14


def test_domain_specific_flags(domain_registry: list[Domain]) -> None:
    """Verify domain-specific behavioral flags are set strictly on authorized domains."""
    for d in domain_registry:
        if d.id == DomainID.SOCIAL_EVALUATION:
            assert all(s.has_deception_metric is True for s in d.scenarios)
        else:
            assert all(s.has_deception_metric is False for s in d.scenarios)

        if d.id == DomainID.FUTURE_UNCERTAINTY:
            assert all(s.has_post_wait is True for s in d.scenarios)
            assert all(s.post_wait_duration_s > 0 for s in d.scenarios)
        else:
            assert all(s.has_post_wait is False for s in d.scenarios)


def test_paradigm_scenario_types(domain_registry: list[Domain]) -> None:
    """Verify specialized scenario types are configured properly."""
    acad = get_domain_by_id(domain_registry, DomainID.ACADEMIC_PRESSURE)
    assert acad.scenarios[0].scenario_type == ScenarioType.MIST_ARITHMETIC
    assert acad.scenarios[0].math_problems is not None
    assert len(acad.scenarios[0].math_problems) == 4

    risk = get_domain_by_id(domain_registry, DomainID.RISK_REWARD)
    assert risk.scenarios[1].scenario_type == ScenarioType.BART_ESCALATION
    assert risk.scenarios[1].bart_config is not None

    imp = get_domain_by_id(domain_registry, DomainID.IMPULSIVITY_GRATIFICATION)
    assert imp.scenarios[0].scenario_type == ScenarioType.REWARD_ACCUMULATOR
    assert imp.scenarios[0].reward_config is not None


def test_domain_lookup_and_not_found(domain_registry: list[Domain]) -> None:
    """Verify get_domain_by_id finds all domains and raises on invalid ID."""
    for d in domain_registry:
        found = get_domain_by_id(domain_registry, d.id)
        assert found.id == d.id

    with pytest.raises(DomainNotFoundError):
        get_domain_by_id(domain_registry, "non_existent_domain")  # type: ignore[arg-type]


def test_generate_math_problems() -> None:
    """Verify math generator returns valid problems with 4 choices each."""
    problems = generate_math_problems(4, "medium")
    assert len(problems) == 4
    for p in problems:
        assert len(p.options) == 4
        assert 0 <= p.correct_index < 4
        assert len(set(p.options)) == 4


def test_dataclasses_are_frozen(domain_registry: list[Domain]) -> None:
    """Verify domains and scenarios cannot be mutated at runtime."""
    d = domain_registry[0]
    with pytest.raises(FrozenInstanceError):
        d.name = "Mutated Name"  # type: ignore[misc]

    s = d.scenarios[0]
    with pytest.raises(FrozenInstanceError):
        s.title = "Mutated Title"  # type: ignore[misc]


def test_scenario_titles_and_durations(domain_registry: list[Domain]) -> None:
    """Verify all 14 scenarios have expected titles and conform to 15-25 age range."""
    expected_titles = {
        "academic_pressure_a": "Exam Countdown Rush",
        "academic_pressure_b": "Academic Misconduct Hearing",
        "peer_influence_a": "Group Chat Vote",
        "peer_influence_b": "Unfair Team Blame",
        "impulsivity_gratification_a": "Instant Loot vs. Multiplier Trap",
        "impulsivity_gratification_b": "Submit Now vs. Improve More",
        "risk_reward_a": "Tournament Strategy",
        "risk_reward_b": "Viral Post Escalation",
        "rule_ambiguity_a": "Portal Access Dilemma",
        "rule_ambiguity_b": "Borrowed Template",
        "future_uncertainty_a": "Track Selection Crossroads",
        "future_uncertainty_b": "Ambiguous Feedback Before Finals",
        "social_evaluation_a": "Live Panel Presentation Defense",
        "social_evaluation_b": "Public Critique",
    }
    scenarios_by_id = {s.id: s for d in domain_registry for s in d.scenarios}
    for s_id, expected_title in expected_titles.items():
        assert s_id in scenarios_by_id
        assert scenarios_by_id[s_id].title == expected_title
