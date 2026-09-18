"""Canonical behavioral domains for Pulse — single source of truth across all tracks.

Shared between:
- Phase 4 Gamification Engine (Ayush)
- Phase 1-3 ML and Hardware Pipeline (Mukasshaf)
"""
from __future__ import annotations

from enum import StrEnum

DOMAIN_IDS: list[str] = [
    "academic_pressure",
    "peer_influence",
    "impulsivity_gratification",
    "risk_reward",
    "rule_ambiguity",
    "future_uncertainty",
    "social_evaluation",
]

CANONICAL_DOMAINS: list[str] = DOMAIN_IDS
N_DOMAINS: int = len(DOMAIN_IDS)


class DomainID(StrEnum):
    """The 7 canonical behavioral domains in Pulse."""

    ACADEMIC_PRESSURE = "academic_pressure"
    PEER_INFLUENCE = "peer_influence"
    IMPULSIVITY_GRATIFICATION = "impulsivity_gratification"
    RISK_REWARD = "risk_reward"
    RULE_AMBIGUITY = "rule_ambiguity"
    FUTURE_UNCERTAINTY = "future_uncertainty"
    SOCIAL_EVALUATION = "social_evaluation"


DOMAIN_DISPLAY: dict[str, str] = {
    "academic_pressure": "Academic Performance Pressure",
    "peer_influence": "Peer Influence & Social Conformity",
    "impulsivity_gratification": "Impulsivity vs Delayed Gratification",
    "risk_reward": "Risk-Reward Tradeoff",
    "rule_ambiguity": "Rule-Boundary Ambiguity",
    "future_uncertainty": "Future Uncertainty",
    "social_evaluation": "Social Evaluation & Authority Response",
}
