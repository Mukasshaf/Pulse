# Mukasshaf Integration Evaluation

> **Date:** 2026-09-16
> **Scope:** Cross-reference Mukasshaf's completed hardware/ML pipeline (Phases 1–3.1) against our gamification engine specs (Phase 4). Identify conflicts, confirm compatibilities, and propose resolutions.

---

## Summary Verdict

Mukasshaf's work is **high-quality and mostly compatible** with our specs. There are **3 conflicts requiring resolution** and **2 hardware changes** that need to propagate into our architecture. Everything else aligns cleanly.

| Category | Count | Items |
|---|---|---|
| ✅ Compatible | 5 | Clock domain, decoupled architecture, 60s windowing, LOSO-CV, 9-feature set |
| ⚠️ Conflict — resolvable | 3 | Domain ID naming, timestamp field name, game event CSV schema columns |
| 🔧 Hardware change — impacts our specs | 2 | MAX30102 → analog Pulse Sensor, sampling rate 66.67 Hz (not 64) |
| 📌 Confirmed by Mukasshaf — no action needed | 2 | M2 closed, Phase 3.1 data collection unblocked |

---

## Detailed Evaluation

### ✅ COMPATIBLE: Decoupled Architecture (No Live IPC)

**Mukasshaf's spec:** Game engine and `serial_reader.py` run as separate processes. No live socket. Post-session join on `unix_ts_ms`.

**Our spec:** `BridgeInterface` / `StubBridge` pattern with `queue.Queue()` for optional in-process bridge.

**Verdict:** No conflict. Our `StubBridge` is the default (no hardware), and Mukasshaf's approach (separate process, offline join) is the *primary* integration path. Our `BridgeInterface` becomes a *future enhancement* for real-time deception metric feedback, not the primary data path. Both approaches coexist.

---

### ✅ COMPATIBLE: Clock Domain

**Mukasshaf's spec:** `unix_ts_ms = int(time.time() * 1000)` — host-PC Unix milliseconds.

**Our spec:** `epoch_ms = time.time_ns() // 1_000_000` — same clock domain, different precision.

**Verdict:** Both produce Unix epoch milliseconds. The `time.time_ns()` approach is strictly higher precision (no float rounding). Mukasshaf's pipeline joins on this value — our timestamps will work perfectly. **One naming alignment needed** (see conflicts below).

---

### ✅ COMPATIBLE: 60s Windowing Constraint

**Mukasshaf's spec:** "Scenarios must last 30–90 seconds minimum for the 60-second ML windowing to capture domain response."

**Our spec:** Decision phases range from 35–45s, and when combined with priming (8–10s) + consequence (4s) + potential post-wait (10–12s), every scenario block is 47–72s total.

**Verdict:** Our scenario timing is within the required window. No change needed.

---

### ✅ COMPATIBLE: Feature Set and Model

Both sides use the same 9-feature set and Random Forest classifier. No drift.

---

### ✅ COMPATIBLE: Session Structure

Both sides agree on: 3-min baseline → 7 randomized domains → 2 scenarios/domain → rest periods → debrief. No conflict.

---

## ⚠️ CONFLICT 1: Domain ID Naming Convention

**Mukasshaf's `domains.py`:**
```
academic_pressure, peer_influence, impulsivity_gratification,
risk_reward, rule_ambiguity, future_uncertainty, social_evaluation
```

**Our `constants.py` (DomainID enum):**
```
acad_press, peer_conf, imp_grat, risk_rew, rule_amb, fut_uncert, soc_eval
```

**Impact:** `align_signals.py` (Mukasshaf's downstream joiner) will fail to match domain labels between the game event CSV and the analysis pipeline if these don't match exactly.

**Resolution:** Adopt Mukasshaf's full-word naming since it's already in the pipeline code and is more readable. Update our `DomainID` enum:

| Ours (old) | Mukasshaf (adopt) |
|---|---|
| `acad_press` | `academic_pressure` |
| `peer_conf` | `peer_influence` |
| `imp_grat` | `impulsivity_gratification` |
| `risk_rew` | `risk_reward` |
| `rule_amb` | `rule_ambiguity` |
| `fut_uncert` | `future_uncertainty` |
| `soc_eval` | `social_evaluation` |

**Propagation:** This change hits `constants.py`, `scenarios.py`, all event CSV data, and `domain_order.json`. Purely a string rename — no logic changes.

---

## ⚠️ CONFLICT 2: Timestamp Column Name

**Mukasshaf's expected column:** `unix_ts_ms`
**Our CSV schema column:** `epoch_ms`

**Impact:** `hardware_loader.py` performs a join on `unix_ts_ms`. If our CSV uses `epoch_ms`, the join silently fails or requires manual column rename.

**Resolution:** Rename our CSV column from `epoch_ms` to `unix_ts_ms` to match Mukasshaf's pipeline expectation. Update `GameEvent.epoch_ms` field name to `unix_ts_ms` and all references.

---

## ⚠️ CONFLICT 3: Game Event CSV Schema Columns

**Mukasshaf's expected schema:**
```
unix_ts_ms, event_type, domain, scenario_id, choice_data
```

**Our CSV schema:**
```
epoch_ms, event_type, domain_id, scenario_id, key_pressed, option_index, response_time_ms, metadata
```

**Impact:** Mukasshaf's `align_signals.py` (to be written) will need to parse our schema. If we output a different column set, it adds mapping burden.

**Resolution:** Keep our richer schema (we need `key_pressed`, `option_index`, `response_time_ms` for behavioral analysis), but ensure the **first 5 columns** match Mukasshaf's expected names:

| Position | Mukasshaf expects | Our output (aligned) |
|---|---|---|
| 1 | `unix_ts_ms` | `unix_ts_ms` ✅ (renamed from `epoch_ms`) |
| 2 | `event_type` | `event_type` ✅ (already matches) |
| 3 | `domain` | `domain` ✅ (renamed from `domain_id`) |
| 4 | `scenario_id` | `scenario_id` ✅ (already matches) |
| 5 | `choice_data` | `choice_data` ✅ (new: JSON-encode key/option/RT into this) |
| 6+ | *(not expected)* | `key_pressed`, `option_index`, `response_time_ms`, `metadata` (extra — harmless) |

The `choice_data` column absorbs what Mukasshaf needs (the user's selection), while our additional columns preserve the granular behavioral data we need.

---

## 🔧 HARDWARE CHANGE 1: MAX30102 → Analog Pulse Sensor

**What happened:** MAX30102 was fried by reverse polarity. Replaced with a generic analog Pulse Sensor on `GPIO35`.

**Impact on our specs:**
- `ARCHITECTURE_SPEC.md` §6 hardware wiring tables → update MAX30102 rows to Pulse Sensor
- `bridge_interface.py` `SensorSample.bvp` field → remains `float`, no code change needed (analog ADC reading is still a float)
- `SensorSample` field semantics are unchanged (raw PPG value, just from a different physical sensor)
- I2C bus now only has MPU6050 (`0x68`), not MAX30102 (`0x57`)

**Resolution:** Update Architecture.md hardware wiring section. No code changes to gamification engine — `SensorSample.bvp` is sensor-agnostic by design.

---

## 🔧 HARDWARE CHANGE 2: True Sampling Rate is 66.67 Hz

**What happened:** Mukasshaf measured the actual firmware loop at 66.67 Hz (15ms per sample), not the 64 Hz assumed from WESAD.

**Impact on our specs:**
- Our specs don't assume any specific hardware sampling rate (the game engine runs at 60 FPS independently)
- The ML pipeline in WSL2 (`preprocess.py`) already handles this via `fs=66.6667` parameter
- `bridge_interface.py` doesn't reference sampling rate — it just receives whatever samples arrive

**Resolution:** Update Architecture.md to document the correct 66.67 Hz rate. No gamification engine code changes.

---

## 📌 CONFIRMED: Mukasshaf's Open Questions — Resolved

### Q1: "Domain ID list not yet confirmed with teammate"
**Answer:** Confirmed. We adopt Mukasshaf's domain ID naming (`academic_pressure`, etc.). Our `DomainID` enum will be updated to match.

### Q2: "`align_signals.py` blocked on game engine event log schema"
**Answer:** Unblocked. Our finalized CSV schema (with the column renames above) gives Mukasshaf everything needed: `unix_ts_ms` join key, `event_type` enum, `domain` strings, `scenario_id`, and `choice_data`.

### Q3: "ACC_THRESHOLD_HW calibrated for typing only"
**Answer:** Acknowledged. Our game engine uses keyboard-only input (non-dominant hand), so the participant's sensor hand is stationary during gameplay — different motion profile from typing. Mukasshaf should re-validate the threshold during pilot gameplay sessions.

---

## Integration Summary — What Changes in Our Specs

| Spec Document | Change | Severity |
|---|---|---|
| `ARCHITECTURE_SPEC.md` | Update hardware wiring (Pulse Sensor on GPIO35), sampling rate 66.67 Hz, domain IDs | Minor |
| `DATA_MODELS_AND_CONTRACTS.md` | Rename `DomainID` enum values, rename `epoch_ms` → `unix_ts_ms`, rename `domain_id` → `domain` in CSV, add `choice_data` column | Medium |
| `CODING_STANDARDS_AND_RULES.md` | No changes | None |
| `IMPLEMENTATION_PLAN.md` | Update verification checkpoints to use new domain IDs | Minor |
| `TEST_CRITERIA_AND_EDGE_CASES.md` | Update domain ID assertions | Minor |
| Vault `Architecture.md` | Major update: hardware pivot, new repo structure, pipeline additions | Major |
| Vault `Progress.md` | Add Mukasshaf's Phase 2–3.1 timeline | Major |
| Vault `Decisions.md` | Add Mukasshaf's motion-artifact methodology decisions | Medium |
| Vault `Project Overview.md` | Update team status, hardware status | Minor |
