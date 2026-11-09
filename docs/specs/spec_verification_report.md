# Spec Verification Report — Pulse/specs/

> Cross-consistency audit of all 6 specification files. 3 issues found and fixed.
>
> **Reading note (2026-10-02):** the eight checks below are the original pre-implementation audit and are kept as a record. Line numbers and a few quoted values in them (the BART parameters in check 6, the timer colours in check 8) describe the specs as they were then. The two addenda at the end describe the current state.

---

## Audit Checklist (8 Points)

### ✅ 1. DomainID Enum Consistency
**Status: PASS — No issues found.**

`DomainID` values in [DATA_MODELS_AND_CONTRACTS.md](file:///c:/Users/AyushShetty/OneDrive/문서/Major%20project%20documents/Pulse/specs/DATA_MODELS_AND_CONTRACTS.md#L54-L61) use canonical full-word IDs (`academic_pressure`, `peer_influence`, etc.). These match:
- [domain_implementation_strategy.md](file:///c:/Users/AyushShetty/OneDrive/문서/Major%20project%20documents/Pulse/specs/domain_implementation_strategy.md) section headers ✅
- [IMPLEMENTATION_PLAN.md](file:///c:/Users/AyushShetty/OneDrive/문서/Major%20project%20documents/Pulse/specs/IMPLEMENTATION_PLAN.md) verification checkpoint code ✅
- [ARCHITECTURE_SPEC.md](file:///c:/Users/AyushShetty/OneDrive/문서/Major%20project%20documents/Pulse/specs/ARCHITECTURE_SPEC.md) domain_order.json example ✅

No stale short IDs (`acad_press`, etc.) found anywhere.

---

### ✅ 2. CSV Schema (9 Columns)
**Status: PASS — No issues found.**

The 9-column schema (`unix_ts_ms, event_type, domain, scenario_id, choice_data, key_pressed, option_index, response_time_ms, metadata`) is consistent across:
- DATA_MODELS §3 (lines 167–186) ✅
- ARCHITECTURE_SPEC §4.1 (lines 227–228) ✅
- IMPLEMENTATION_PLAN Task 3 checkpoint (lines 106–129) ✅
- TEST_CRITERIA Gate 4 (line 392) ✅

---

### ✅ 3. GameEvent Dataclass → CSV Column Match
**Status: PASS — No issues found.**

`GameEvent` fields (DATA_MODELS §2, lines 131–140) map exactly to CSV columns:
| GameEvent field | CSV column | Match |
|---|---|---|
| `unix_ts_ms: int` | `unix_ts_ms` | ✅ |
| `event_type: EventType` | `event_type` | ✅ |
| `domain: str` | `domain` | ✅ |
| `scenario_id: str` | `scenario_id` | ✅ |
| `choice_data: str` | `choice_data` | ✅ |
| `key_pressed: int \| None` | `key_pressed` | ✅ |
| `option_index: int \| None` | `option_index` | ✅ |
| `response_time_ms: int \| None` | `response_time_ms` | ✅ |
| `metadata: dict` | `metadata` | ✅ |

---

### ✅ 4. ScenarioType Coverage
**Status: PASS — No issues found.**

All 5 `ScenarioType` enum members map to specific scenarios in `domain_implementation_strategy.md`:

| ScenarioType | Used By | Strategy Reference |
|---|---|---|
| `STANDARD_MCQ` | All scenarios not listed below | Default for 9 scenarios |
| `MIST_ARITHMETIC` | `academic_pressure_a` | Domain 1 Scenario A ✅ |
| `BART_ESCALATION` | `risk_reward_b` | Domain 4 Scenario B ✅ |
| `REWARD_ACCUMULATOR` | `impulsivity_gratification_a` | Domain 3 Scenario A ✅ |
| `DELAY_WAIT` | `future_uncertainty_a`, `future_uncertainty_b` | Domain 6 both scenarios ✅ |

TEST_CRITERIA assertions reference these correctly (lines 105–108).

---

### ✅ 5. Function Signatures vs Implementation Checkpoints
**Status: PASS — No issues found.**

Key verified matches:
- `build_domain_registry() → list[Domain]` (DATA_MODELS line 268) matches Task 2 checkpoint import (IMPL_PLAN line 74) ✅
- `get_domain_by_id(registry, domain_id)` (DATA_MODELS line 273) matches Task 2 checkpoint (IMPL_PLAN line 80) ✅
- `GameEngine.__init__(config, screen)` (DATA_MODELS line 234) matches Task 9 checkpoint (IMPL_PLAN lines 330–331) ✅
- `EventLogger.__init__(output_dir, subject_id)` (DATA_MODELS line 334) matches Task 3 checkpoint (IMPL_PLAN line 113) ✅

---

### ✅ 6. Constants Values Consistency
**Status: PASS — No issues found.**

Cross-checked BART, Reward, and timing constants between DATA_MODELS §7 and IMPLEMENTATION_PLAN Task 8 checkpoint:
- `BART_INITIAL_VALUE=100`, `BART_INCREMENT=50`, `BART_BURST_PROB_BASE=0.05`, `BART_BURST_PROB_INCREMENT=0.08`, `BART_MAX_PUMPS=15` — all match ✅
- `RewardAccumulatorConfig(10, 1.15, (20, 40), 9999)` in checkpoint matches `REWARD_INITIAL_VALUE=10`, `REWARD_GROWTH_RATE=1.15`, `REWARD_COLLAPSE_RANGE=(20,40)`, `REWARD_MAX_DISPLAY=9999` — all match ✅
- Timing constants match ARCHITECTURE_SPEC §6 hard constraints table ✅

---

### ✅ 7. State Transitions Match
**Status: PASS — No issues found.**

`VALID_TRANSITIONS` adjacency list (DATA_MODELS §8, lines 515–526) precisely matches the state diagram in ARCHITECTURE_SPEC §5 (lines 264–331):
- `INIT → ID_INPUT` ✅
- `ID_INPUT → BASELINE` ✅
- `BASELINE → PRIMING` ✅
- `PRIMING → DECISION` ✅
- `DECISION → {POST_WAIT, FEEDBACK}` ✅
- `POST_WAIT → FEEDBACK` ✅
- `FEEDBACK → {INTRA_REST, INTER_REST, DEBRIEF}` ✅
- `INTRA_REST → PRIMING` ✅
- `INTER_REST → PRIMING` ✅
- `DEBRIEF → ∅` (terminal) ✅

---

### ✅ 8. Test Assertions vs Constants
**Status: PASS — No issues found.**

Spot-checked:
- TEST_CRITERIA line 84: `EngineState.DEBRIEF` terminal assertion → DATA_MODELS line 525 `DEBRIEF: set()` ✅
- TEST_CRITERIA line 87: `JITTER_MAX_PX <= 3` → DATA_MODELS line 464 `JITTER_MAX_PX: int = 3` ✅
- TEST_CRITERIA line 87: `DRONE_VOLUME <= 0.30` → DATA_MODELS line 458 `DRONE_VOLUME: float = 0.30` ✅
- TEST_CRITERIA line 231: Timer bar color at 100% `== (34, 197, 94)` → DATA_MODELS line 500 `COLOR_TIMER_GREEN = (34, 197, 94)` ✅
- TEST_CRITERIA line 232: Timer bar color at 5% `== (239, 68, 68)` → DATA_MODELS line 502 `COLOR_TIMER_RED = (239, 68, 68)` ✅

---

## Issues Found & Fixed

### 🔧 Fix 1: `AudioController.__init__` Exception Type Mismatch
**File:** [DATA_MODELS_AND_CONTRACTS.md](file:///c:/Users/AyushShetty/OneDrive/문서/Major%20project%20documents/Pulse/specs/DATA_MODELS_AND_CONTRACTS.md#L375)
**Problem:** Docstring said `Raises FileNotFoundError` but the custom exception hierarchy defines `AudioLoadError(PulseEngineError)` — and every other document (CODING_STANDARDS, TEST_CRITERIA, IMPLEMENTATION_PLAN) uses `AudioLoadError`.
**Fix:** Changed to `Raises AudioLoadError if missing`.

### 🔧 Fix 2: `UIEffectState` Dataclass Missing from §2
**File:** [DATA_MODELS_AND_CONTRACTS.md](file:///c:/Users/AyushShetty/OneDrive/문서/Major%20project%20documents/Pulse/specs/DATA_MODELS_AND_CONTRACTS.md#L163-L169)
**Problem:** `UIEffectState` was referenced in `UIRenderer.draw_decision()` signature (§5) and in IMPLEMENTATION_PLAN Tasks 6 & 7, but never formally defined in the Dataclasses section. A code generator would have to invent its fields.
**Fix:** Added `UIEffectState` dataclass with fields `jitter_offset`, `vibration_offset`, `is_flashing`, `timer_bar_color`.

### 🔧 Fix 3: `GameEvent` Placement Ambiguity
**File:** [IMPLEMENTATION_PLAN.md](file:///c:/Users/AyushShetty/OneDrive/문서/Major%20project%20documents/Pulse/specs/IMPLEMENTATION_PLAN.md#L99)
**Problem:** Task 3 said `"GameEvent dataclass (if not already in constants — place here alongside the logger)"` — the hedge creates ambiguity for a code generator.
**Fix:** Changed to `"GameEvent dataclass (defined here in event_logger.py — not in constants.py)"`.

### 🔧 Fix 4: File Count Off-by-One in Gate 1
**File:** [TEST_CRITERIA_AND_EDGE_CASES.md](file:///c:/Users/AyushShetty/OneDrive/문서/Major%20project%20documents/Pulse/specs/TEST_CRITERIA_AND_EDGE_CASES.md#L362)
**Problem:** Gate 1 said "All 10 source files exist in `src/game/`" but ARCHITECTURE_SPEC lists 11 files (including `__init__.py`).
**Fix:** Changed to explicit enumeration of all 11 files.

---

## Stale Reference Check

| Pattern | Result |
|---|---|
| `MAX30102` | ✅ Not found |
| `epoch_ms` | ✅ Not found |
| `acad_press` (short domain IDs) | ✅ Not found |
| `scr_energy_per_peak` | ✅ Not found |

---

## Verdict

All 6 spec files are now **mutually consistent** and ready for handover to Antigravity IDE for implementation.

---

## Addendum (2026-10-02): Spec-vs-Code Verification After the Independent Audit

This report verified the specs against each other. The 2026-10-02 audit verified the code against the specs and found that several specified behaviours had never been implemented. After remediation:

| Specified behaviour | Before | After |
|---|---|---|
| C1 — DECISION holds for the full timer | Not implemented (instant exit) | ✅ Implemented (`hold_full_decision`, on in `main.py`) |
| M3 — focus loss freezes timers and audio | Not implemented | ✅ Implemented |
| `CLOCK_ANOMALY`, `FOCUS_LOST`, `FOCUS_GAINED` events | Defined, never emitted | ✅ Emitted |
| Composure gating: 3 consecutive samples + 5s cooldown | Constants defined, never used | ✅ Implemented |
| `COMPASS_SPIN_MAX_RPM`, jitter ≤2Hz | Exceeded (40 RPM, 3Hz axis) | ✅ Enforced |
| `impulsivity_gratification_b` 15s POST_WAIT on Key 2 | Unreachable | ✅ Implemented |
| `mypy --strict` clean (Gate 2) | 5 errors | ✅ Clean; `ruff check src/game tests/game` also clean |
| `calibrate_mist_difficulty()` pretest (C4) | Not implemented | ✅ Superseded: difficulty adapts in-run (`MISTRunner` per-item countdown); the pretest was removed from the specs (ADR-B3) |
| `SerialBridge` for Domain 7 (C3) | Not implemented | ✅ Implemented (`sensor_bridge.py`, ADR-B1). Not yet run on the physical ESP32 |
| `social_evaluation_b` decision 46s (C5) | Code uses 45s | ✅ Specs aligned to 45s (ADR-B3) |
| Inter-domain rest 60s | Code uses 30s | ✅ Decided: 30s default, 60s with `--extended-rest`; `Decisions.md` updated (ADR-B2) |
| Priming 5–10s | Code uses 20s | ✅ Specs aligned to 20s for all 14 scenarios (ADR-B3) |
| Gate 1: files ≤500 lines | `ui.py` ~3,280, `engine.py` ~600 | ✅ Split; every file in `src/` and `tests/` is ≤500 lines (ADR-B6). The 60-line function rule is still unmet for the skin methods |

The specs were updated on 2026-10-02 to describe the remediated behaviour. The six rows that were open at that point were closed in the following round (second addendum); what is still open is tracked in ARCHITECTURE_SPEC §7.3.

---

## Second Addendum (2026-10-02): Machine Check of the Specs Against the Code

After the open-issues round, `DATA_MODELS_AND_CONTRACTS.md` was checked against the running code by script rather than by eye. Each documented item was parsed out of the spec and compared with the imported module:

| Check | Compared | Result |
|---|---|---|
| Constants (§7) | 79 values, each against `src/game/constants.py`; also every public constant in the module must appear in the spec | ✅ 79 equal, none undocumented |
| Enumerations (§1) | `EngineState` (10), `EventType` (22), `ScenarioType` (5), `DomainID` (7): names and values | ✅ identical |
| Transitions (§8) | `VALID_TRANSITIONS` adjacency dict | ✅ identical |
| Dataclasses (§2) | 13 classes: field order, names, annotations, defaults, `frozen` flag | ✅ identical (`Scenario` 22 fields, `SessionConfig` 11) |
| Public API (§5) | 99 documented function, method and class names must exist in `src/game/` | ✅ all present |
| Exceptions (§6) | Documented classes against the `PulseEngineError` hierarchy, both directions | ✅ identical (7 classes incl. `BridgeUnavailableError`) |

Result: **0 discrepancies.** The check is a script, not a test in the suite; rerun it after any change to the contracts.

Cross-document consistency for the values changed in this round:

| Value | ARCHITECTURE_SPEC | DATA_MODELS | TEST_CRITERIA | Strategy / Design | Code |
|---|---|---|---|---|---|
| Priming duration | 20s (§5, §6) | `DEFAULT_PRIMING_DURATION_S = 20` | locked-durations test | 20s on all 14 scenarios | 20 |
| Decision duration | 45s / 40s MIST (§6) | `DEFAULT_DECISION_DURATION_S = 45`, `MIST_DECISION_DURATION_S = 40` | locked-durations test | 45s (40s for 1A) | 45 / 40 |
| Inter-domain rest | 30s, 60s extended (§5 Rule 6, §6) | `INTER_DOMAIN_REST_S = 30`, `…_EXTENDED_S = 60` | §2.10 | 30s in the session flow | 30 / 60 |
| BART hazard | `0.02 + 0.03·(k−1)`, certain at 15 (§3) | `BART_BURST_PROB_BASE = 0.02`, `…_INCREMENT = 0.03`, `BART_MAX_PUMPS = 15` | §2.7, B-01 | 2% → 41%, fifteenth certain | same |
| BART pacing | 1.5s cooldown (§5 Rule 3) | `BART_PUMP_COOLDOWN_MS = 1500` | B-07…B-09 | "PUBLISHING POST..." | 1500 |
| MIST adaptation | 8s start, ±10% per 2-streak, 3–12s (§5 Rule 3) | `MIST_ITEM_LIMIT_*`, `MIST_ADAPT_*` | M-07…M-11 | same | same |
| Palette | §6.1 token table | §7 colour block | §2.11 | palette map | `constants.py` |
| Test count | 111 game tests in 13 modules | — | 114 total | — | `uv run pytest`: 114 passed |

Known remaining mismatches between the standards and the code are listed in ARCHITECTURE_SPEC §7.3 (function length; one 542-line validation script).
