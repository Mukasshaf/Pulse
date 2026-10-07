# Pulse  Gamification Engine Interface & Integration Spec

Boundary specification between the Hardware/ML Pipeline and the Gamification Engine. Defines the event contracts, clock synchronization strategy, and sensor schema that both components rely on for post-session alignment.

---

## 1. System Architecture

The sensor pipeline and gamification engine run as **two independent, decoupled processes** on the same host PC. There is no live inter-process communication during a session.

```
┌─────────────────────────────┐        ┌───────────────────────────┐
│   Serial Reader             │        │   Gamification Engine     │
│   (serial_reader.py)        │        │   (src/game/main.py)      │
│                             │        │                           │
│  ESP32 → COM9 → raw CSV     │        │  Pygame → events.csv      │
│  Timestamps: unix_ts_ms     │        │  Timestamps: unix_ts_ms   │
└─────────────┬───────────────┘        └──────────┬────────────────┘
              │                                    │
              └──────────────┬─────────────────────┘
                             ▼
                    align_signals.py
                  (post-session join on unix_ts_ms)
                             │
                             ▼
                  per_subject_features.py
                  (feature extraction + radar chart)
```

Both processes are launched and managed by the single orchestrator: `run_session.py`.

---

## 2. Behavioral Domains

The game engine imports canonical domain definitions from `src/domains.py`. Domain strings must never be hardcoded.

```python
# src/domains.py
DOMAIN_IDS = [
    "academic_pressure",
    "peer_influence",
    "impulsivity_gratification",
    "risk_reward",
    "rule_ambiguity",
    "future_uncertainty",
    "social_evaluation",
]

DOMAIN_DISPLAY = {
    "academic_pressure":         "Academic Performance Pressure",
    "peer_influence":            "Peer Influence & Social Conformity",
    "impulsivity_gratification": "Impulsivity vs Delayed Gratification",
    "risk_reward":               "Risk-Reward Tradeoff",
    "rule_ambiguity":            "Rule-Boundary Ambiguity",
    "future_uncertainty":        "Future Uncertainty",
    "social_evaluation":         "Social Evaluation & Authority Response",
}
```


---

## 3. Clock Synchronization

Both processes timestamp all events using **host-PC wall-clock Unix time in milliseconds** (`unix_ts_ms`).

```python
unix_ts_ms = int(time.time() * 1000)
# equivalent: int(time.time_ns() // 1_000_000)
```

The ESP32's internal `millis()` clock is **not** used for alignment, it is relative and drifts. The `unix_ts_ms` column injected by `serial_reader.py` on packet arrival is the sole join key.

---

## 4. Game Engine Event Log Contract (`events.csv`)

Output path: `outputs/game_logs/{subject}_{timestamp}/events.csv`

### Schema (9 Columns)

| # | Column | Type | Role | Notes |
|---|---|---|---|---|
| 1 | `unix_ts_ms` | int | Join key | Host-PC Unix epoch milliseconds |
| 2 | `event_type` | str | Pipeline contract | `SCENARIO_PRIMING`, `OPTION_SELECTED`, `TIMEOUT_NO_RESPONSE`, `RECOVERY_START`, `RECOVERY_END` |
| 3 | `domain` | str | Pipeline contract | Exact string from `src/domains.py` |
| 4 | `scenario_id` | str | Pipeline contract | e.g. `academic_pressure_a` |
| 5 | `choice_data` | str (JSON) | Pipeline contract | Valid JSON — `{}` if no choice |
| 6 | `key_pressed` | int\|empty | Behavioral | Keyboard key (1–4) |
| 7 | `option_index` | int\|empty | Behavioral | 0-based index of selected option |
| 8 | `response_time_ms` | int\|empty | Behavioral | Milliseconds from prompt to keypress |
| 9 | `metadata` | str (JSON) | Behavioral | Scenario-specific key/value pairs |

### Required Events for Alignment

| Event | Purpose |
|---|---|
| `SCENARIO_PRIMING` | Anchors the start of the 60s feature extraction window |
| `OPTION_SELECTED` or `TIMEOUT_NO_RESPONSE` | Marks the decision timestamp |
| `RECOVERY_START` / `RECOVERY_END` | Delimits rest periods — audio is only permitted during recovery to prevent physiological confounds |

---

## 5. Hardware Sensor Stream Schema

### Firmware Output (ESP32 → Serial)

```
sample_idx, timestamp_ms, pulse_raw, gsr_raw, acc_x, acc_y, acc_z
```

| Field | Sensor | Pin | Notes |
|---|---|---|---|
| `pulse_raw` | Analog Pulse Sensor | GPIO35 | 12-bit ADC, ~1800–2400 at rest |
| `gsr_raw` | Grove GSR | GPIO34 | 12-bit ADC, ~1000–2500 at rest |
| `acc_x/y/z` | MPU6050 | I2C 0x68 | Raw int16 values ±16384 |

Sampling rate: **66.67 Hz** (`SAMPLE_INTERVAL_MS = 15`).

### Serial Reader Output (`outputs/raw/recorded_<ts>.csv`)

```
sample_idx, timestamp_ms, unix_ts_ms, pulse_raw, gsr_raw, acc_x, acc_y, acc_z
```

`unix_ts_ms` is injected on packet arrival and serves as the join key against `events.csv`.

---

## 6. Algorithmic Parameters

### Motion Artifact Gate

```python
ACC_THRESHOLD_HW = 8800.0  # src/pipeline/preprocess.py
```

Tuned for raw int16 MPU6050 variance during seated resting posture. A 30-second window with artifact fraction > 50% is excluded from feature extraction.

### Baseline Normalization Guard

```python
MIN_BASELINE_WINDOWS = 4  # scripts/analysis/per_subject_features.py
```

Subjects with fewer than 4 valid 30-second baseline windows (due to motion artifacts) are reported in raw ADC units rather than z-scores and are excluded from group-level normalized comparisons.

### MPU6050 Composure Metric (`social_evaluation` domain)

The post-session composure score is computed by `align_signals.py` using the ACC magnitude variance relative to the resting baseline:

```
magnitude       = sqrt(acc_x² + acc_y² + acc_z²) − mean(magnitude)
variance_window = Var(magnitude over 1s)

baseline_mean   = Mean(variance_window) over 3-min resting period
baseline_std    = Std(variance_window)  over 3-min resting period

threshold       = baseline_mean + 1.5 × baseline_std
```

Any 1-second window where `variance_window > threshold` is flagged as a composure breach.

---

## 7. Session Execution

A complete session is launched via the single orchestrator script:

```powershell
uv run python run_session.py --subject S01
```

Use `--fast-baseline` to skip the 3-minute resting baseline during development.

### Input Controls

- **Keyboard only:** Keys `1`, `2`, `3`, `4`.
- **Mouse strictly prohibited** to keep the sensor hand stationary.
- The sensor hand rests flat on the desk at all times during scenarios.

### Window Timing Requirements

The Random Forest classifier requires **60-second sliding windows** for valid HRV features (RMSSD, SDNN). All scenarios must be paced to last **30–90 seconds**.
