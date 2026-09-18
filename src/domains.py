# domains.py -- single source of truth for the 7 behavioral domain IDs.
# Imported by: game scenario configs, activation-mapping analysis code
# (activation_map_S{id}.csv, domain_ranking.csv columns).
#
# Do not redefine this list anywhere else. See GPAMS_Phase1_Reference.docx
# section 4.5 for what happened last time a canonical list got duplicated
# (feature_cols NameError bug from half-edited copies).
#
# These IDs are proposed/settled -- confirm with teammate before both sides
# start hardcoding a mismatched set in the game engine.

DOMAIN_IDS = [
    "academic_pressure",
    "peer_influence",
    "impulsivity_gratification",
    "risk_reward",
    "rule_ambiguity",
    "future_uncertainty",
    "social_evaluation",
]

N_DOMAINS = len(DOMAIN_IDS)

# Map domain ID -> display name (for plots, reports, UI labels)
DOMAIN_DISPLAY = {
    "academic_pressure":        "Academic Performance Pressure",
    "peer_influence":           "Peer Influence & Social Conformity",
    "impulsivity_gratification":"Impulsivity vs Delayed Gratification",
    "risk_reward":              "Risk-Reward Tradeoff",
    "rule_ambiguity":           "Rule-Boundary Ambiguity",
    "future_uncertainty":       "Future Uncertainty",
    "social_evaluation":        "Social Evaluation & Authority Response",
}
