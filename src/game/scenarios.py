"""Dataclasses and registry definitions for scenarios and domains in Pulse."""
from __future__ import annotations

import random
from dataclasses import dataclass

from src.game.constants import (
    BART_BURST_PROB_BASE,
    BART_BURST_PROB_INCREMENT,
    BART_INCREMENT,
    BART_INITIAL_VALUE,
    BART_MAX_PUMPS,
    REWARD_COLLAPSE_RANGE,
    REWARD_GROWTH_RATE,
    REWARD_INITIAL_VALUE,
    REWARD_MAX_DISPLAY,
    DomainID,
    DomainNotFoundError,
    ScenarioType,
)


@dataclass(frozen=True)
class Option:
    """A response option presented to the participant."""

    key: int
    text: str
    consequence_text: str
    is_conforming: bool | None = None


@dataclass(frozen=True)
class MathProblem:
    """An arithmetic problem utilized in MIST scenarios."""

    question_text: str
    options: list[int]
    correct_index: int


@dataclass(frozen=True)
class BARTConfig:
    """Configuration parameters for BART balloon pump escalation."""

    initial_value: int
    increment_per_pump: int
    burst_probability_base: float
    burst_probability_increment: float
    max_pumps: int


@dataclass(frozen=True)
class RewardAccumulatorConfig:
    """Configuration parameters for continuous reward accumulation."""

    initial_value: int
    growth_rate: float
    collapse_time_range: tuple[int, int]
    max_display_value: int


@dataclass(frozen=True)
class Scenario:
    """Specification of an interactive experiment scenario."""

    id: str
    domain_id: DomainID
    title: str
    paradigm: str
    priming_text: str
    priming_duration_s: int
    decision_duration_s: int
    consequence_duration_s: int
    options: list[Option]
    scenario_type: ScenarioType
    has_deception_metric: bool = False
    has_post_wait: bool = False
    post_wait_duration_s: int = 0
    post_wait_text: str = ""
    math_problems: list[MathProblem] | None = None
    bart_config: BARTConfig | None = None
    reward_config: RewardAccumulatorConfig | None = None
    delay_wait_outcomes: list[str] | None = None
    timeout_consequence: str = "The system has made a decision for you."
    jitter_trigger_s: int | None = None
    drone_trigger_fraction: float = 0.333


@dataclass(frozen=True)
class Domain:
    """A behavioral domain containing exactly two scenarios."""

    id: DomainID
    name: str
    scenarios: tuple[Scenario, Scenario]


def generate_math_problems(count: int = 4, difficulty: str = "medium") -> list[MathProblem]:
    """Generate arithmetic problems for the MIST scenario."""
    problems: list[MathProblem] = []
    rng = random.Random(101)
    low, high = (10, 89) if difficulty == "easy" else ((1000, 4999) if difficulty == "hard" else (100, 499))
    for i in range(count):
        num_a, num_b = rng.randint(low, high), rng.randint(low, high)
        correct_ans = num_a + num_b
        distractors: set[int] = set()
        offsets = [-10, 10, -21, 19, -2, 2, -100, 100]
        rng.shuffle(offsets)
        for off in offsets:
            candidate = correct_ans + off
            if candidate != correct_ans and candidate > 0:
                distractors.add(candidate)
            if len(distractors) == 3:
                break
        opts = list(distractors)
        correct_idx = i % 4
        opts.insert(correct_idx, correct_ans)
        problems.append(MathProblem(f"{num_a} + {num_b} = ?", opts, correct_idx))
    return problems


def _build_academic_pressure() -> Domain:
    """Build the Academic Performance Pressure domain."""
    conseq_b = "Your justification has been submitted to the review board. The committee's decision is pending and will be communicated separately."
    s_a = Scenario(
        id="academic_pressure_a",
        domain_id=DomainID.ACADEMIC_PRESSURE,
        title="Exam Countdown Rush",
        paradigm="MIST (Dedovic et al., 2005)",
        priming_text="Your semester GPA hinges on this assessment. You have 40 seconds. The system will compare your results against other participants.",
        priming_duration_s=8,
        decision_duration_s=40,
        consequence_duration_s=4,
        options=[Option(1, "Option 1", "Assessment complete."), Option(2, "Option 2", "Assessment complete."), Option(3, "Option 3", "Assessment complete."), Option(4, "Option 4", "Assessment complete.")],
        scenario_type=ScenarioType.MIST_ARITHMETIC,
        math_problems=generate_math_problems(4),
        jitter_trigger_s=20,
    )
    s_b = Scenario(
        id="academic_pressure_b",
        domain_id=DomainID.ACADEMIC_PRESSURE,
        title="High-Stakes Grade Waiver",
        paradigm="Evaluative Observation Paradigm (Geen, 1991)",
        priming_text="Your academic board has flagged your transcript for review. You must submit a written justification to retain your scholarship. The board's decision will be final.",
        priming_duration_s=8,
        decision_duration_s=45,
        consequence_duration_s=4,
        options=[
            Option(1, "Accept responsibility and request leniency", conseq_b),
            Option(2, "Challenge the board's criteria as unfair", conseq_b),
            Option(3, "Provide evidence that the evaluation was an error", conseq_b),
        ],
        scenario_type=ScenarioType.STANDARD_MCQ,
    )
    return Domain(DomainID.ACADEMIC_PRESSURE, "Academic Performance Pressure", (s_a, s_b))


def _build_peer_influence() -> Domain:
    """Build the Peer Influence & Social Conformity domain."""
    s_a = Scenario(
        id="peer_influence_a",
        domain_id=DomainID.PEER_INFLUENCE,
        title="Group Hacking Mandate",
        paradigm="Digital Asch Conformity (Stoll et al., 2022; Berns et al., 2005)",
        priming_text="Your project team has been assigned a critical system audit. Four team members have already voted on the approach. You are the final vote.",
        priming_duration_s=8,
        decision_duration_s=35,
        consequence_duration_s=4,
        options=[
            Option(1, "Agree with the team — skip the security audit", "The team proceeds with the shortcut. Audit flag has been raised by the system.", is_conforming=True),
            Option(2, "Disagree — insist on the full audit", "The team has noted your objection. Team lead has requested a private meeting.", is_conforming=False),
        ],
        scenario_type=ScenarioType.STANDARD_MCQ,
    )
    s_b = Scenario(
        id="peer_influence_b",
        domain_id=DomainID.PEER_INFLUENCE,
        title="Unfair Team Blame",
        paradigm="Taboo Trade-Off Paradigm (Tetlock et al., 2000)",
        priming_text="Your team project received a failing grade. The instructor says one team member must be identified as responsible for the core section that failed. The rest of the team has already submitted their assessment.",
        priming_duration_s=8,
        decision_duration_s=40,
        consequence_duration_s=4,
        options=[
            Option(1, "Accept responsibility to preserve team harmony", "You accepted responsibility. The team received course credit while your record reflects the failure.", is_conforming=True),
            Option(2, "Challenge the attribution and name the actual responsible member", "You challenged the attribution. Interpersonal conflict escalated, and a disciplinary hearing has been scheduled.", is_conforming=False),
            Option(3, "Refuse to participate in the blame assignment", "You refused to assign blame. The instructor penalized the entire group equally for non-compliance.", is_conforming=False),
        ],
        scenario_type=ScenarioType.STANDARD_MCQ,
    )
    return Domain(DomainID.PEER_INFLUENCE, "Peer Influence & Social Conformity", (s_a, s_b))


def _build_impulsivity_gratification() -> Domain:
    """Build the Impulsivity vs. Delayed Gratification domain."""
    r_cfg = RewardAccumulatorConfig(REWARD_INITIAL_VALUE, REWARD_GROWTH_RATE, REWARD_COLLAPSE_RANGE, REWARD_MAX_DISPLAY)
    s_a = Scenario(
        id="impulsivity_gratification_a",
        domain_id=DomainID.IMPULSIVITY_GRATIFICATION,
        title="Instant Loot vs. Multiplier Trap",
        paradigm="Real-Time Waiting Task / Digital Marshmallow Test (McGuire & Kable, 2012)",
        priming_text="You've unlocked a reward chest. You can claim it now for a small payout, or wait as the value multiplies. But the chest is unstable — it could collapse at any moment, and you'd lose everything.",
        priming_duration_s=8,
        decision_duration_s=45,
        consequence_duration_s=4,
        options=[Option(1, "CLAIM NOW", "Reward secured."), Option(2, "KEEP WAITING", "Chest collapsed. All accumulated value lost.")],
        scenario_type=ScenarioType.REWARD_ACCUMULATOR,
        reward_config=r_cfg,
    )
    s_b = Scenario(
        id="impulsivity_gratification_b",
        domain_id=DomainID.IMPULSIVITY_GRATIFICATION,
        title="Instant Cashout vs. Long-Term Bonus",
        paradigm="Kirby Monetary Choice Questionnaire (Kirby et al., 1999)",
        priming_text="You've completed a performance review. You can receive your evaluation now, or wait for the extended assessment which may yield a significantly better outcome — but you won't know for certain.",
        priming_duration_s=8,
        decision_duration_s=35,
        consequence_duration_s=4,
        options=[
            Option(1, 'Receive a guaranteed moderate outcome now ("Competent — meets expectations")', "Assessment recorded: Meets Expectations."),
            Option(2, "Wait for the extended assessment — outcome unknown", "Extended assessment complete."),
        ],
        scenario_type=ScenarioType.DELAY_WAIT,
        delay_wait_outcomes=["Extended assessment complete: Exceeds Expectations.", "Extended assessment complete: Needs Improvement."],
        post_wait_duration_s=15,
        post_wait_text="Processing extended evaluation...",
    )
    return Domain(DomainID.IMPULSIVITY_GRATIFICATION, "Impulsivity vs. Delayed Gratification", (s_a, s_b))


def _build_risk_reward() -> Domain:
    """Build the Risk-Reward Tradeoff domain."""
    b_cfg = BARTConfig(BART_INITIAL_VALUE, BART_INCREMENT, BART_BURST_PROB_BASE, BART_BURST_PROB_INCREMENT, BART_MAX_PUMPS)
    s_a = Scenario(
        id="risk_reward_a",
        domain_id=DomainID.RISK_REWARD,
        title="High-Yield Volatile Market",
        paradigm="Iowa Gambling Task (Bechara et al., 1994)",
        priming_text="You're managing an investment portfolio. Three assets are available. Historical performance data is incomplete — some assets carry hidden risks. Your final portfolio value will be recorded.",
        priming_duration_s=8,
        decision_duration_s=40,
        consequence_duration_s=4,
        options=[
            Option(1, "Asset A: Low volatility, consistent 8% yield", "Portfolio updated: Moderate gain realized as projected."),
            Option(2, "Asset B: High volatility, avg 22% yield, [2 quarters of data missing]", "Portfolio updated: Volatility triggered an unhedged 15% loss."),
            Option(3, "Asset C: Extreme volatility, avg 45% yield, [4 quarters of data missing]", "Market crash: Portfolio value reduced by 70%."),
        ],
        scenario_type=ScenarioType.STANDARD_MCQ,
    )
    s_b = Scenario(
        id="risk_reward_b",
        domain_id=DomainID.RISK_REWARD,
        title="Safe Exit vs. Double Down",
        paradigm="BART (Lejuez et al., 2002)",
        priming_text="You've accumulated significant progress in a high-risk operation. You can secure your gains now, or push further — but the probability of a total system failure increases with each step.",
        priming_duration_s=8,
        decision_duration_s=40,
        consequence_duration_s=4,
        options=[Option(1, "SECURE GAINS", "Gains secured."), Option(2, "PUSH FURTHER", "System failure. All accumulated progress lost.")],
        scenario_type=ScenarioType.BART_ESCALATION,
        bart_config=b_cfg,
    )
    return Domain(DomainID.RISK_REWARD, "Risk-Reward Tradeoff", (s_a, s_b))


def _build_rule_ambiguity() -> Domain:
    """Build the Rule-Boundary Ambiguity domain."""
    s_a = Scenario(
        id="rule_ambiguity_a",
        domain_id=DomainID.RULE_AMBIGUITY,
        title="Gray-Hat System Bypass",
        paradigm="Personal Moral Dilemma (Greene et al., 2001)",
        priming_text="Your close friend has been locked out of an essential academic system due to an administrative error that won't be resolved for 3 weeks — past the submission deadline. You have admin-level access credentials that could restore their account, but using them violates the institution's IT security policy.",
        priming_duration_s=8,
        decision_duration_s=45,
        consequence_duration_s=4,
        options=[
            Option(1, "Use your credentials to restore their access — helps your friend, violates policy", "Access restored. The IT department has flagged an unauthorized login from your credentials."),
            Option(2, "Refuse and advise them to file an official appeal — follows policy, friend misses the deadline", "Your friend's appeal was denied. They missed the deadline."),
            Option(3, "Restore access anonymously through a workaround — technically doesn't use your credentials directly, but exploits a known system vulnerability", "The vulnerability you exploited has been patched. An investigation has been opened."),
        ],
        scenario_type=ScenarioType.STANDARD_MCQ,
        jitter_trigger_s=15,
    )
    s_b = Scenario(
        id="rule_ambiguity_b",
        domain_id=DomainID.RULE_AMBIGUITY,
        title="Copyright Exemption Dilemma",
        paradigm="Taboo Trade-Off (Tetlock et al., 2000)",
        priming_text="Your research team has discovered that a small open-source library you've been using contains code that was copied — without attribution — from a proprietary system. Removing it would set back your project by months. Your team lead says to keep it and move on.",
        priming_duration_s=8,
        decision_duration_s=40,
        consequence_duration_s=4,
        options=[
            Option(1, "Remove the code and accept the project delay — respects IP rights, harms the team", "Code removed. Project delayed by 8 weeks. Sponsor expressed dissatisfaction."),
            Option(2, "Keep the code and add retroactive attribution — compromise, legally questionable", "Retroactive attribution added. Original copyright owner has issued a formal cease-and-desist notice."),
            Option(3, "Report the issue to the original author and negotiate a license — transparent but unpredictable outcome", "License negotiations stalled indefinitely. Project frozen pending legal clearance."),
        ],
        scenario_type=ScenarioType.STANDARD_MCQ,
    )
    return Domain(DomainID.RULE_AMBIGUITY, "Rule-Boundary Ambiguity", (s_a, s_b))


def _build_future_uncertainty() -> Domain:
    """Build the Future Uncertainty domain."""
    rec_conseq = "Your selection has been recorded. Outcome details will be provided at the end of the evaluation."
    flag_conseq = "Assessment updated. Your response pattern has been flagged for secondary review."
    s_a = Scenario(
        id="future_uncertainty_a",
        domain_id=DomainID.FUTURE_UNCERTAINTY,
        title="Career Track Crossroads",
        paradigm="Ambiguous Feedback Paradigm (Hirsh & Inzlicht, 2008)",
        priming_text="You've been offered two career paths. Both have significant implications for your future, but the outcomes of each path are influenced by factors you cannot predict or control.",
        priming_duration_s=8,
        decision_duration_s=45,
        consequence_duration_s=4,
        options=[
            Option(1, "Path A: Stable role at an established organization — Predictable trajectory. Growth potential: [DATA UNAVAILABLE].", rec_conseq),
            Option(2, "Path B: High-risk role at a startup — Unpredictable trajectory. Compensation structure: [UNDER REVIEW].", rec_conseq),
        ],
        scenario_type=ScenarioType.STANDARD_MCQ,
        has_post_wait=True,
        post_wait_duration_s=12,
        post_wait_text="Processing your selection...",
    )
    s_b = Scenario(
        id="future_uncertainty_b",
        domain_id=DomainID.FUTURE_UNCERTAINTY,
        title="Opaque Evaluation Criteria",
        paradigm="Ambiguous Feedback + Uncertain Threat (Grillon et al., 2004; de Berker et al., 2016)",
        priming_text="Your performance in this session is being evaluated by an algorithm. The evaluation criteria have not been disclosed. Your responses so far have been... atypical compared to other participants.",
        priming_duration_s=8,
        decision_duration_s=40,
        consequence_duration_s=4,
        options=[
            Option(1, "I've been responding honestly based on my instincts.", flag_conseq),
            Option(2, "I've been carefully considering each option before responding.", flag_conseq),
            Option(3, "I don't believe this evaluation is measuring what it claims to.", flag_conseq),
        ],
        scenario_type=ScenarioType.STANDARD_MCQ,
        has_post_wait=True,
        post_wait_duration_s=10,
        post_wait_text="Recalculating assessment parameters...",
    )
    return Domain(DomainID.FUTURE_UNCERTAINTY, "Future Uncertainty", (s_a, s_b))


def _build_social_evaluation() -> Domain:
    """Build the Social Evaluation & Authority Response domain."""
    panel_conseq = "The panel has recorded your response. Composure score: evaluated. Final evaluation pending."
    sup_conseq = "Your response has been logged. Updated performance assessment: Under continued review."
    s_a = Scenario(
        id="social_evaluation_a",
        domain_id=DomainID.SOCIAL_EVALUATION,
        title="Live Panel Presentation Defense",
        paradigm="TSST Speech Task (Kirschbaum et al., 1993) + Biofeedback Amplification (Wieser et al., 2010)",
        priming_text="You are presenting your project findings to an expert evaluation panel. The panel's assessment will determine your project grade. The system is monitoring your physiological composure in real-time.",
        priming_duration_s=10,
        decision_duration_s=45,
        consequence_duration_s=4,
        options=[
            Option(1, "Defend the methodology with technical justification", panel_conseq),
            Option(2, "Acknowledge limitations and propose revisions", panel_conseq),
            Option(3, "Challenge the reviewer's qualifications", panel_conseq),
        ],
        scenario_type=ScenarioType.STANDARD_MCQ,
        has_deception_metric=True,
        jitter_trigger_s=15,
    )
    s_b = Scenario(
        id="social_evaluation_b",
        domain_id=DomainID.SOCIAL_EVALUATION,
        title="Harsh Manager Review",
        paradigm="Evaluative Observation + Negative Feedback (Geen, 1991; Smeets et al., 2012)",
        priming_text="Your direct supervisor has flagged your recent work for a critical performance review. The review was initiated by the supervisor, not by you. The system is monitoring your response composure.",
        priming_duration_s=10,
        decision_duration_s=40,
        consequence_duration_s=4,
        options=[
            Option(1, "Accept the criticism and commit to improvement", sup_conseq),
            Option(2, "Provide context for the underperformance (external factors)", sup_conseq),
            Option(3, "Push back — the criticism is not specific enough to act on", sup_conseq),
        ],
        scenario_type=ScenarioType.STANDARD_MCQ,
        has_deception_metric=True,
    )
    return Domain(DomainID.SOCIAL_EVALUATION, "Social Evaluation & Authority Response", (s_a, s_b))


def build_domain_registry() -> list[Domain]:
    """Construct and return the complete list of 7 Domains with 14 Scenarios."""
    return [
        _build_academic_pressure(),
        _build_peer_influence(),
        _build_impulsivity_gratification(),
        _build_risk_reward(),
        _build_rule_ambiguity(),
        _build_future_uncertainty(),
        _build_social_evaluation(),
    ]


def get_domain_by_id(registry: list[Domain], domain_id: DomainID) -> Domain:
    """Lookup a domain by ID. Raise DomainNotFoundError if missing."""
    for domain in registry:
        if domain.id == domain_id:
            return domain
    raise DomainNotFoundError(str(domain_id))
