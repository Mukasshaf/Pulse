# Pulse — Gamification Engine Interface Spec (Phase 4 Update)

*For the agent/teammate implementing the Phase 4 Game Engine. This document outlines exactly how the game must interface with the already-completed Pulse ML/Sensor pipeline.*

---

## 1. Clock Synchronization (BLOCKER RESOLVED)
**Status:** Solved on the pipeline side.
**Constraint:** The game engine **MUST** log all events using host-PC Unix time in milliseconds (`unix_ts_ms`). 
*   **Do not** use the ESP32's `millis()` or relative times.
*   **Python implementation:** `int(time.time() * 1000)`
*   **Why:** `serial_reader.py` now automatically stamps all incoming sensor rows with PC-side `unix_ts_ms`. The downstream pipeline (`hardware_loader.py`) performs a direct numeric join on this timestamp. Using standard Unix-ms guarantees perfect <500ms alignment with zero offset math.

## 2. Shared Source of Truth (DOMAINS)
**Status:** Solved on the pipeline side.
**Constraint:** The game engine **MUST NOT** hardcode domain names as raw strings. 
*   **Action:** You must import the canonical domain list from `src/domains.py`. (If this file doesn't exist on your side yet, create it with the list below and share it).
*   **Why:** In Phase 1, duplicated constant lists caused fatal bugs when they drifted out of sync. `src/domains.py` is the single source of truth for both the Game Engine and the Analysis Pipeline. 
*   *Current list includes:* `academic_pressure`, `peer_influence`, `impulsivity_gratification`, `risk_reward`, `rule_ambiguity`, `future_uncertainty`, `social_evaluation`.

## 3. Game Engine Output (The Event Log)
The Game Engine must run completely decoupled from the sensor script, outputting a standalone CSV event log at the end of the session.

**Required CSV Schema:**
*   `unix_ts_ms` (integer, exactly as described above)
*   `event_type` (string, e.g., `scenario_start`, `choice_made`, `recovery_start`)
*   `domain` (string, imported from `src/domains.py`)
*   `scenario_id` (string/int)
*   `choice_data` (optional string/JSON for logging what the user selected)

*Note on Recovery periods:* `recovery_start` and `recovery_end` are critical. Background music is **only** permitted during recovery, never during active scenarios, to prevent physiological confounding. Logging these bounds accurately is required for the pipeline to exclude music-contaminated data.

## 4. Connection Architecture
*   **Execution:** The Game Engine (Pygame) and `serial_reader.py` will run concurrently as separate processes (e.g., in two terminal windows). 
*   **No Live IPC:** There is no live socket or inter-process communication required. The game does *not* read physiological data to adapt scenarios (the sequence is fixed and deterministic). 
*   **Post-session:** `hardware_loader.py` will read both your event log CSV and the sensor CSV, joining them natively on `unix_ts_ms`.

## 5. Model Limitations (CRITICAL FOR PACING)
The analysis pipeline uses a Random Forest classifier that **requires 60-second sliding windows** to validly compute Heart Rate Variability (HRV) metrics like `RMSSD` and `SDNN`.
*   **What this means for the game:** The model cannot output a stress classification for a 5-second event. 
*   **Pacing:** Scenarios must be paced to last 30–90 seconds minimum, or be treated as continuous blocks, to allow the 60-second ML windowing to capture the domain's physiological response. Only GSR (phasic SCR peaks) can be attributed to sudden micro-events (like a jumpscare or sudden timer).

## 6. Context already settled (Do not revisit)
*   **Branching:** MCQ + branching follow-up is the adopted decision-point pattern.
*   **Priming:** Clips are short (5–10s), animated/illustrated only — no licensed video footage.
*   **Scope:** 2 scenarios per domain, ~14min total scenario time within a 45–60min session.
*   **No adaptive selection:** The sequence is fixed. Log the randomized domain order as session metadata for redundancy.