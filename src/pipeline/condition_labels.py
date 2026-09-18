"""
condition_labels.py -- Phase 3.1 protocol condition label definitions.

These are NOT the same as domains.py's 7 game-domain IDs.
- domains.py   : Phase 4+ game-domain labels (academic_pressure, peer_influence, ...)
- THIS FILE    : Phase 3.1 controlled-protocol labels (baseline, mental_arithmetic, stroop)

These map directly to WESAD's label space for the classifier:
    baseline          -> label 1  (matches WESAD label 1 = "baseline")
    mental_arithmetic -> label 2  (maps to WESAD label 2 = "stress")
    stroop            -> label 2  (also stress-class; collapses with mental_arithmetic
                                   for binary baseline-vs-stress classification)

Do not merge with domains.py under any circumstances.
"""

# Ordered list matching the Phase 3.1 session schedule
CONDITION_LABELS = ["baseline", "mental_arithmetic", "stroop"]

# Maps condition name -> classifier integer label
# Both stress conditions collapse to label=2 to match WESAD binary scheme
CONDITION_TO_LABEL = {
    "baseline":           1,
    "mental_arithmetic":  2,
    "stroop":             2,
}

# Reverse map: label int -> human-readable name (for reports)
# Label 2 reports as "stress" because it's the merged stress class
LABEL_TO_NAME = {
    1: "baseline",
    2: "stress",
}

# Phase 3.1 fixed durations in seconds
CONDITION_DURATION_S = {
    "baseline":           180,   # 3 min
    "mental_arithmetic":  180,   # 3 min
    "stroop":             120,   # 2 min
}

TOTAL_SESSION_S = sum(CONDITION_DURATION_S.values())  # 480 s = 8 min
