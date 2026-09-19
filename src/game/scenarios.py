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
    conseq_b = "Your statement has been submitted to the committee. Their decision will be communicated to you separately."
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
        title="Academic Misconduct Hearing",
        paradigm="Evaluative Observation Paradigm (Geen, 1991)",
        priming_text="You've been called before your school's academic integrity committee following an incident during your last exam. You must submit a written statement. The committee's decision will affect your academic standing — it is final.",
        priming_duration_s=8,
        decision_duration_s=45,
        consequence_duration_s=4,
        options=[
            Option(1, "Accept responsibility and request leniency", conseq_b),
            Option(2, "Challenge the committee's conclusion as based on incomplete evidence", conseq_b),
            Option(3, "Provide documentation that the incident was a misunderstanding", conseq_b),
        ],
        scenario_type=ScenarioType.STANDARD_MCQ,
    )
    return Domain(DomainID.ACADEMIC_PRESSURE, "Academic Performance Pressure", (s_a, s_b))


def _build_peer_influence() -> Domain:
    """Build the Peer Influence & Social Conformity domain."""
    s_a = Scenario(
        id="peer_influence_a",
        domain_id=DomainID.PEER_INFLUENCE,
        title="Group Chat Vote",
        paradigm="Digital Asch Conformity (Stoll et al., 2022; Berns et al., 2005)",
        priming_text="Your friend group is deciding in a chat whether to share a private video of a classmate. Four friends have already voted. You are the last to respond.",
        priming_duration_s=8,
        decision_duration_s=35,
        consequence_duration_s=4,
        options=[
            Option(1, "Agree — share it", "The video has been shared. The classmate found out — they're upset and asking who agreed to it.", is_conforming=True),
            Option(2, "Disagree — refuse and ask others to delete it", "The group has noted your objection. Some members are calling it an overreaction.", is_conforming=False),
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
        title="Submit Now vs. Improve More",
        paradigm="Kirby Monetary Choice Questionnaire (Kirby et al., 1999)",
        priming_text="You've finished a draft of your assignment. You can submit it now for a guaranteed adequate grade, or spend more time refining it — which could significantly improve your grade, but might also make things worse if you second-guess yourself.",
        priming_duration_s=8,
        decision_duration_s=35,
        consequence_duration_s=4,
        options=[
            Option(1, "Submit now — guaranteed 'Adequate — Requirements Met'", "Grade recorded: Adequate — Requirements Met."),
            Option(2, "Request more time — outcome unknown", "Extended review complete."),
        ],
        scenario_type=ScenarioType.DELAY_WAIT,
        delay_wait_outcomes=["Extended review complete: Excellent.", "Extended review complete: Insufficient — major revision required."],
        post_wait_duration_s=15,
        post_wait_text="Reviewing additional changes...",
    )
    return Domain(DomainID.IMPULSIVITY_GRATIFICATION, "Impulsivity vs. Delayed Gratification", (s_a, s_b))


def _build_risk_reward() -> Domain:
    """Build the Risk-Reward Tradeoff domain."""
    b_cfg = BARTConfig(BART_INITIAL_VALUE, BART_INCREMENT, BART_BURST_PROB_BASE, BART_BURST_PROB_INCREMENT, BART_MAX_PUMPS)
    s_a = Scenario(
        id="risk_reward_a",
        domain_id=DomainID.RISK_REWARD,
        title="Tournament Strategy",
        paradigm="Iowa Gambling Task (Bechara et al., 1994)",
        priming_text="You're competing in an online tournament with limited attempts remaining. Three strategies are available. Historical performance data for each approach is incomplete — some strategies carry hidden risks. Your final ranking will be recorded.",
        priming_duration_s=8,
        decision_duration_s=40,
        consequence_duration_s=4,
        options=[
            Option(1, "Strategy A: Safe approach — Low variance, reliable 8% average score improvement per round", "Tournament updated: Moderate gain realized as projected."),
            Option(2, "Strategy B: Aggressive approach — High variance, avg 22% improvement, [2 rounds of data missing]", "Tournament updated: Volatility triggered an unhedged score drop."),
            Option(3, "Strategy C: Experimental approach — Extreme variance, avg 45% improvement, [4 rounds of data missing]", "Critical error: Ranking dropped significantly."),
        ],
        scenario_type=ScenarioType.STANDARD_MCQ,
    )
    s_b = Scenario(
        id="risk_reward_b",
        domain_id=DomainID.RISK_REWARD,
        title="Viral Post Escalation",
        paradigm="BART (Lejuez et al., 2002)",
        priming_text="You've been posting increasingly bold content online. Each post gets more attention — but the risk of being reported and losing access to your account grows with every step. You can stop now, or push further.",
        priming_duration_s=8,
        decision_duration_s=40,
        consequence_duration_s=4,
        options=[Option(1, "STOP POSTING", "Following secured."), Option(2, "POST ANOTHER", "Account suspended. All accumulated following lost.")],
        scenario_type=ScenarioType.BART_ESCALATION,
        bart_config=b_cfg,
    )
    return Domain(DomainID.RISK_REWARD, "Risk-Reward Tradeoff", (s_a, s_b))


def _build_rule_ambiguity() -> Domain:
    """Build the Rule-Boundary Ambiguity domain."""
    s_a = Scenario(
        id="rule_ambiguity_a",
        domain_id=DomainID.RULE_AMBIGUITY,
        title="Portal Access Dilemma",
        paradigm="Personal Moral Dilemma (Greene et al., 2001)",
        priming_text="Your close friend is locked out of the school's submission portal due to a technical error that won't be fixed for three weeks — past the assignment deadline. You still have their login saved from a previous help session. Using it violates the school's IT policy.",
        priming_duration_s=8,
        decision_duration_s=45,
        consequence_duration_s=4,
        options=[
            Option(1, "Log in with their credentials to submit for them — helps your friend, violates policy", "Submission successful. The system flagged a login from an unrecognized device on your friend's account."),
            Option(2, "Tell them to file an official complaint — follows policy, friend misses the deadline", "Your friend's appeal was denied. They missed the deadline and lost 20% of their grade."),
            Option(3, "Find a workaround through the system's guest access feature — technically not their credentials, but exploits a known loophole", "The guest access loophole has been patched. An investigation into unusual submissions has been opened."),
        ],
        scenario_type=ScenarioType.STANDARD_MCQ,
        jitter_trigger_s=15,
    )
    s_b = Scenario(
        id="rule_ambiguity_b",
        domain_id=DomainID.RULE_AMBIGUITY,
        title="Borrowed Template",
        paradigm="Taboo Trade-Off (Tetlock et al., 2000)",
        priming_text="Your group has been building on an old assignment from a senior student who graduated. You just realized the work was never formally shared — it could be classified as academic plagiarism. Removing it now sets your entire project back by days before the deadline.",
        priming_duration_s=8,
        decision_duration_s=40,
        consequence_duration_s=4,
        options=[
            Option(1, "Remove the borrowed sections and accept the delay — academically honest, harms the team's timeline", "Sections removed. Project delayed by several days before submission."),
            Option(2, "Keep it and add an acknowledgement crediting the original work — a compromise, still academically questionable", "Acknowledgement added. Academic integrity board has flagged the submission for retroactive review."),
            Option(3, "Contact the original student and ask for formal permission — transparent, but their response is unpredictable and time is short", "Permission request pending. Project submission frozen awaiting authorization."),
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
        title="Track Selection Crossroads",
        paradigm="Ambiguous Feedback Paradigm (Hirsh & Inzlicht, 2008)",
        priming_text="You've been offered two paths forward. Both have significant implications for your future, but the outcomes of each path are influenced by factors you cannot predict or control.",
        priming_duration_s=8,
        decision_duration_s=45,
        consequence_duration_s=4,
        options=[
            Option(1, "Path A: Familiar, established track — Predictable progression. Long-term growth potential: [DATA UNAVAILABLE].", rec_conseq),
            Option(2, "Path B: New, challenging path — Unpredictable trajectory. Support structure: [UNDER REVIEW].", rec_conseq),
        ],
        scenario_type=ScenarioType.STANDARD_MCQ,
        has_post_wait=True,
        post_wait_duration_s=12,
        post_wait_text="Processing your selection...",
    )
    s_b = Scenario(
        id="future_uncertainty_b",
        domain_id=DomainID.FUTURE_UNCERTAINTY,
        title="Ambiguous Feedback Before Finals",
        paradigm="Ambiguous Feedback + Uncertain Threat (Grillon et al., 2004; de Berker et al., 2016)",
        priming_text="Before your final assessment, your teacher pulls you aside: 'Your approach throughout this term has been... atypical compared to your peers.' You don't know if this is a compliment or a warning. You must now respond.",
        priming_duration_s=8,
        decision_duration_s=40,
        consequence_duration_s=4,
        options=[
            Option(1, "I've been approaching each task based on my instincts and what made sense to me.", flag_conseq),
            Option(2, "I've been carefully considering each step before committing to anything.", flag_conseq),
            Option(3, "I don't think the standard approach was appropriate for what we were being asked to do.", flag_conseq),
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
    crit_conseq = "Your response has been logged. Updated assessment: Under continued review."
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
        title="Public Critique",
        paradigm="Evaluative Observation + Negative Feedback (Geen, 1991; Smeets et al., 2012)",
        priming_text="Your teacher or coach has singled you out in front of the group for a critical review — one you didn't request. The system is monitoring your composure in real-time.",
        priming_duration_s=10,
        decision_duration_s=40,
        consequence_duration_s=4,
        options=[
            Option(1, "Accept the criticism and commit to improving", crit_conseq),
            Option(2, "Provide context — external factors affected your performance", crit_conseq),
            Option(3, "Push back — the criticism is too vague and not specific enough to act on", crit_conseq),
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
