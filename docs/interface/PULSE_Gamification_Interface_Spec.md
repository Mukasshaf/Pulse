# Pulse — Gamification Engine Interface Spec (Phase 4 Update)

*For the agent/teammate implementing the Phase 4 Game Engine. This document outlines exactly how the game must interface with the already-completed Pulse ML/Sensor pipeline.*

---

## 1. Clock Synchronization (BLOCKER RESOLVED)
**Status:** Solved on the pipeline side.
**Constraint:** The game engine **MUST** log all events using host-PC Unix time in milliseconds (`unix_ts_ms`). 
*   **Do not** use the ESP32's `millis()` or relative times.
*   **Python implementation:** `int(time.time_ns() // 1_000_000)` (the game engine and its sensor bridge); `int(time.time() * 1000)` in `serial_reader.py` is the same clock.
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

### 4.1 Sensor bridge for the Domain 7 composure display (2026-10-02)
The one place the game uses a live signal is the `social_evaluation` composure bar, which needs the wrist accelerometer. The sequence is still fixed; nothing adapts to physiology. A serial port can be opened by one process only, so there are two ways to run a session:

| | Decoupled (recommended for data collection) | Integrated (single process) |
|---|---|---|
| Who owns the COM port | `serial_reader.py` | the game (`SerialBridge`) |
| Sensor recording | `serial_reader.py`'s `recorded_*.csv`, as before | `outputs/game_logs/S{id}_{ts}/sensor_stream.csv` |
| Game command | `uv run python -m src.game.main --subject S01 --bridge replay --bridge-follow --bridge-source <recorded csv or its folder>` | `uv run python -m src.game.main --subject S01` (default `--bridge auto`) or `--bridge serial` to refuse to start without the ESP32 |
| Start order | `serial_reader.py` first, then the game | game only; do not start `serial_reader.py` |

*   **Same file format either way.** `sensor_stream.csv` has exactly `serial_reader.py`'s columns in the same order (`sample_idx, timestamp_ms, unix_ts_ms, pulse_raw, gsr_raw, acc_x, acc_y, acc_z`), with `unix_ts_ms` stamped on arrival from the same host clock. `hardware_loader.py` and `align_signals.py` read it unchanged.
*   **The game never takes the port from the recorder.** If `serial_reader.py` already has it, the game's open fails, `--bridge auto` falls back to no telemetry with a message, and the recording is undisturbed.
*   **Auto-detection is conservative.** It opens only ports whose USB vendor ID is a known ESP32 serial bridge (CP210x, CH340/CH9102, FTDI, Espressif) and accepts a port only after 3 valid rows at 115200 baud. `--bridge-port COM3` names the port explicitly.
*   **Firmware contract unchanged:** 7 comma-separated integers per line at 66.67 Hz. The bridge also accepts the 8-column recorded format and a JSON object per line, so a later firmware revision can add fields without breaking the game.
*   **Not yet run on hardware.** The bridge is tested against simulated ports and recorded rows only. The first session on the real ESP32 should be a dry run with `--bridge serial --fast-baseline --domain social_evaluation`.
*   `SYNC_PULSE` metadata names the bridge in use (`StubBridge`, `SerialBridge`, `ReplayBridge`), so every log states whether the composure display was live.

## 5. Model Limitations (CRITICAL FOR PACING)
The analysis pipeline uses a Random Forest classifier that **requires 60-second sliding windows** to validly compute Heart Rate Variability (HRV) metrics like `RMSSD` and `SDNN`.
*   **What this means for the game:** The model cannot output a stress classification for a 5-second event. 
*   **Pacing:** Scenarios must be paced to last 30–90 seconds minimum, or be treated as continuous blocks, to allow the 60-second ML windowing to capture the domain's physiological response. Only GSR (phasic SCR peaks) can be attributed to sudden micro-events (like a jumpscare or sudden timer).
*   **Engine guarantee (2026-10-02):** the game now enforces this itself. A keypress is logged immediately but the decision screen is held until its timer expires, and priming can only be shortened as far as keeps priming + decision + feedback at 60 seconds or more. Per scenario the pipeline can rely on `SCENARIO_PRIMING` → `SCENARIO_END` spanning at least 60s. Sessions run with `--no-exposure-floor` do not carry this guarantee; they are marked by `hold_full_decision: false` in the `SYNC_PULSE` metadata and must be excluded from analysis.

### 5.1 Event-log additions the pipeline should know (2026-10-02)
The 9-column schema and the first 5 pipeline columns are unchanged. New information lives in the `metadata` JSON only:
*   `SYNC_PULSE` metadata records `bridge`, `audio_loaded`, `hold_full_decision`, `min_priming_s`, `min_active_epoch_s`, `inter_domain_rest_s`.
*   `CLOCK_ANOMALY` rows mark frame stalls and wall-clock steps (>50ms); `FOCUS_LOST` / `FOCUS_GAINED` bracket intervals in which the game was frozen. Windows overlapping these should be flagged.
*   `SESSION_END` with `aborted: true` marks a session ended early.
*   `response_time_ms` is measured on a monotonic clock; `MATH_ANSWER` and `BART_*` rows add per-item `item_rt_ms`.
*   `MATH_ANSWER` adds `item_limit_ms` (the adaptive per-item countdown in force) and `timed_out: true` for an item that ran out unanswered (that row has no key).
*   `BART_PUMP` adds `pump`, `burst_prob` (the hazard that pump faced) and `instability`; `BART_SECURE` adds `pumps` and `next_burst_prob`; `BART_BURST` adds `pump`. Together they give the per-pump pressure curve.
*   `REST_START` adds `duration_s`: 15 intra-domain; 30 inter-domain by default, 60 with `--extended-rest`.
*   The baseline period is spontaneous breathing (no paced-breathing visual), so baseline HRV is a true resting reference.

## 6. Context already settled (Do not revisit)
*   **Branching:** MCQ + branching follow-up is the adopted decision-point pattern.
*   **Priming:** Clips are short (5–10s), animated/illustrated only — no licensed video footage. *(Superseded 2026-10-02, ADR-B3: the priming phase is a 20s text briefing in all 14 scenarios, skippable with SPACE only after the read floor.)*
*   **Scope:** 2 scenarios per domain, ~14min total scenario time within a 45–60min session. *(As built: 13 scenarios of 69s and one of 64s, about 16min of scenario time; with the 3min baseline and the rests the game runs about 24min, or 27min with `--extended-rest`.)*
*   **No adaptive selection:** The sequence is fixed. Log the randomized domain order as session metadata for redundancy.