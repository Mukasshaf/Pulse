"""Canonical behavioral domains for Pulse — single source of truth across all tracks.

Shared between:
- Phase 4 Gamification Engine (Ayush)
- Phase 1-3 ML and Hardware Pipeline (Mukasshaf)
"""
from __future__ import annotations

from enum import StrEnum

CANONICAL_DOMAINS: list[str] = [
    "academic_pressure",
    "peer_influence",
    "impulsivity_gratification",
    "risk_reward",
    "rule_ambiguity",
    "future_uncertainty",
    "social_evaluation",
]


class DomainID(StrEnum):
    """The 7 canonical behavioral domains in Pulse."""

    ACADEMIC_PRESSURE = "academic_pressure"
    PEER_INFLUENCE = "peer_influence"
    IMPULSIVITY_GRATIFICATION = "impulsivity_gratification"
    RISK_REWARD = "risk_reward"
    RULE_AMBIGUITY = "rule_ambiguity"
    FUTURE_UNCERTAINTY = "future_uncertainty"
    SOCIAL_EVALUATION = "social_evaluation"
