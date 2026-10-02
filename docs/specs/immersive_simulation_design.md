# Pulse — Immersive Simulation Interface Design
## From Questionnaire → Simulation/Game/Video for All 7 Domains

**Constraints locked in:**
- Pygame desktop renderer (Windows native)
- Keyboard-only: keys `1`–`4`, `SPACE` to start a scenario after the read floor, hold `TAB`/`Q` to re-read the briefing (sensors on dominant hand)
- Score-free consequence design
- All 5 mechanics preserved: MIST arithmetic, BART escalation, REWARD_ACCUMULATOR, DELAY_WAIT, STANDARD_MCQ (enhanced)
- Jitter ≤ 3px (vector magnitude), ≤ 2Hz on both axes; vibration ≤ 2px, ≤ 2Hz — no full-screen flashing, no strobing > 3Hz
- Diegetic audio OK (subtle tension drone); no blaring alarms
- Deception metric (MPU6050) — `social_evaluation` domain only
- Age range: 15–25, universal contexts
- No scores displayed; narrative consequences only
- **No construct labels on screen (2026-10-02):** a skin never names its paradigm, the manipulation, or the target cohort. "TSST", "MIST", "Asch", "conform/dissent", "marshmallow", "diegetic", "15–25 demographic" belong in this document, not in the UI.
- **Committed choice is held (2026-10-02):** after a keypress the skin shows the locked-in state (highlighted card, sent chat bubble, suspension splash, collapsed chest) until the decision timer expires. Every skin must render that state cleanly.
- **Sharp 0px corners**, neutral window controls (no OS traffic-light dots).
- **Ferrari palette only (2026-10-02, ADR-B5):** a skin draws neutral greys plus six tokens — Rosso Corsa `#da291c`, Rosso active `#b01e0a`, warning `#f13a2c`, info cyan `#4c98b9`, caution yellow `#f6e500`, success green `#03904a`. No navy panels, no purple accents, no neon cyan, no orange, no coloured avatars. A dimmer shade of a token is made with `_mix()` toward the canvas, never with a new hex.
- **Rosso Corsa means a stress trigger** (wrong answer, failed module, suspension, collapse, a deadline line, the critique bubble, the final seconds). It never fills a key prompt and never marks the option the participant chose.
- **Key prompts are neutral plates:** canvas fill, white digit, Grigio border (`_draw_key_badge`). The chosen key inverts to a white plate. A key that is temporarily inert is drawn muted.
- **Fixed timing (ADR-B3):** every skin is shown for a 20s briefing, then a 45s decision window (40s for the exam hall), then 4s of consequence. A skin never ends early, so it must look right for the whole window.

---

## Design Philosophy

The shift is from **"Read a situation → Pick an answer"** to **"Experience a situation → React to it"**.

Each domain gets a dedicated **simulation skin** — a persistent visual world that wraps the existing mechanics. The underlying data (MIST arithmetic, BART pump counter, reward accumulator) is unchanged. What changes is:

1. **Where the participant feels they ARE** (diegetic context, rendered as a simple Pygame scene)
2. **What the mechanics look like** (re-skinned, not rebuilt)
3. **What they hear** (ambient, subtle, diegetic)

All skins are achievable with Pygame's 2D renderer, simple geometric shapes, and pre-loaded PNG assets. No videos required — simulation is sufficient and preferred (no synchronization overhead).

---

## Domain 1: Academic Performance Pressure (`academic_pressure`)
### Simulation Skin: **"The Exam Hall"**

**Visual world:**  
A top-down view of an exam hall with the participant's desk in the foreground. The desk shows a paper with math problems on it. Other desks (4–6) are visible in the periphery with silhouette figures that subtly animate (slight pen-moving motion).

**Scenario A — Exam Countdown Rush (MIST Arithmetic):**

The paper on the desk IS the math problem. Questions appear handwritten-style (monospace font). A wall clock in the background ticks down visibly. The **Peer Average bar** is now rendered as "classmates' completion bars" visible at the far end of each silhouette desk — always slightly ahead. The participant fills in answers with `1`/`2`/`3`/`4` keys.

| Old presentation | New presentation |
|---|---|
| Plain centered text with timer bar | Diegetic exam desk scene |
| "Peer Average: X%" progress bar | Other desks showing completion progress (always ahead) |
| Red flash on wrong answer | Rosso Corsa X ink mark appearing on paper (also when an item runs out of time) |
| (new) per-item time limit | A thin countdown bar along the bottom edge of the question box. It drains in dark ink and turns Rosso only in the last quarter of the item's time |
| Timer bar turning red | Wall clock pendulum swinging faster (visual only) |

**Adaptive difficulty (ADR-B3):** each problem has its own countdown, 8s at the start. Two correct answers in a row shorten it by 10%, two failures in a row lengthen it by 10% (3–12s). An unanswered problem is marked wrong and replaced. This is the MIST adaptation done inside the run; there is no separate practice or pretest block.

**Stress amplifiers added:**
- At 20s mark: a supervisor silhouette walks slowly across the back of the hall
- Subtle ambient: background pencil-on-paper rustling sound loop (< -20dB relative to threshold)
- The hall flickers subtly (brightness ±5% via `BRIGHTNESS_FLICKER_MAX_PCT`) when time is critical — capped at ≤2Hz via `BRIGHTNESS_FLICKER_MAX_HZ` (strictly below WCAG 3Hz safety threshold).
- Wall clock pendulum swing rate capped at ≤1Hz via `PENDULUM_SWING_MAX_HZ`.

**Scenario B — Academic Misconduct Hearing (MCQ):**

The scene shifts to a stark **committee room** — a long table with 3 silhouette figures seated behind it. The participant's text is presented as a "statement input terminal" in front of them. The 3 silhouettes remain completely still (unresponsive — this is the TSST uncontrollability mechanism, applied early). Timer shows as an analog clock on the wall, ticking in silence. The on-screen caption reads "COMMITTEE PANEL IS OBSERVING — FORMAL RECORDING IN PROGRESS"; the unresponsiveness is shown, never stated.

---

## Domain 2: Peer Influence & Social Conformity (`peer_influence`)
### Simulation Skin: **"The Group Chat Simulator"**

**Visual world:**  
A phone-style UI rendered inside the Pygame window — dark background, chat bubbles, avatar icons. Feels like a messaging app. The participant's chat input cursor is blinking at the bottom.

**Scenario A — Group Chat Vote (Asch Conformity):**

The chat fills in real-time (pre-scripted) — 4 friend avatar messages scroll in one by one with a short delay (0.5s each). Each one votes to share the video. Names are deliberately ambiguous (initials only: "M.", "J.", "R.", "T."). The participant's name cursor blinks at the bottom, and 2 option buttons appear as chat-input quick replies:

```
[ 1 — "Agree — share it" ]   [ 2 — "Refuse & ask them to delete" ]
```

**Stress amplifiers:**
- A "5 people are typing..." indicator appears briefly after all 4 have voted — implying more pressure coming
- The 4 completed votes have a small "seen by all" tick — participant's dissent will be equally visible
- A subtle notification pulse (amber border, 1Hz via `NOTIFICATION_PULSE_HZ`) on the chat window — strictly non-strobing
- The quick-reply chips carry the option text only. They are NOT tagged "[CONFORM]" / "[DISSENT]" (removed 2026-10-02): conformity is recorded in the log (`is_conforming`), never shown.
- After a reply is committed it appears as the participant's own sent bubble for the rest of the timer. The bubble is the same neutral grey for either reply: its colour must not grade the choice.
- Avatars are neutral grey plates with white initials (ADR-B5). Peers are told apart by initial and name, not by hue. This also applies to the four teammate cards on the Kanban board in Scenario B.

**Scenario B — Unfair Team Blame (MCQ):**

Scene shifts to a **project management board** UI — looks like a Trello/Kanban screen. 4 teammates' cards are filled in, all pointing to the participant's name. The participant's card is blank and blinking. Three response tiles appear at the bottom. The UI is rendered as a stark professional tool — cold, impersonal, reinforcing the institutional pressure.

---

## Domain 3: Impulsivity vs. Delayed Gratification (`impulsivity_gratification`)
### Simulation Skin: **"The Crate"**

**Visual world:**  
A glowing digital crate/chest in the center of a dark room. The crate pulses with internal light. A numeric counter above it shows the accumulating reward value. The room has a single status bar on the left (stability/instability indicator).

**Scenario A — Instant Loot vs. Multiplier Trap (REWARD_ACCUMULATOR):**

This is the most simulation-native of all scenarios — it already has a visual mechanic. The re-skin makes it feel like a dungeon loot moment or a drop-zone countdown:

- The **chest physically expands** as value accumulates (scale: 1.0 → 1.6x over 45s; implement via scaled polygon vertices/rects redrawn per frame, NOT via `pygame.transform.smoothscale()` to avoid 60 FPS CPU overhead)
- The **stability bar** on the left wall deteriorates (success green → caution yellow → Rosso Corsa; cracks appear on the crate's surface as Rosso polylines). The crate's accent glow runs along the same semantic tokens: info cyan → yellow → Rosso as collapse risk grows — one of the three sanctioned token-to-token gradients
- The **reward number** floats above the chest, growing larger and brighter as it accumulates (font size: 32pt → 54pt)
- At collapse: crate shatters into particles (simple Pygame rect explosion effect, ~12 shards spreading radially)
- Keys displayed as on-screen hint chips at the bottom: `[1] CLAIM` and `[2] WAIT`

**Scenario B — Submit Now vs. Improve More (DELAY_WAIT):**

Scene shows a **document workspace** — a text editor UI with visible progress bars. Two tiles represent the submission options. If the participant waits (Key 2), a "review spinner" plays over the document — this is the existing 15s DELAY_WAIT mechanic but rendered as a word processor with an AI review animation overlaid. An animated "Reviewing..." text types and untypes itself repeatedly. *(Wired 2026-10-02: Key 2 now actually enters the 15s `POST_WAIT`; Key 1 goes straight to feedback. Window controls are neutral square outlines.)* The unsaved-revision highlight on the page is the caution yellow washed into the paper white, not a separate pastel.

---

## Domain 4: Risk-Reward Tradeoff (`risk_reward`)
### Simulation Skin: **"The Console"**

**Visual world:**  
A terminal/strategy-game style interface — dark background, monospace green text, like a command interface. Feels like a competitive gaming overlay or a tactical decision panel.

**Scenario A — Tournament Strategy (one-shot risky choice / Standard MCQ):**

The "strategies" are displayed as three **tournament bracket cards** on screen, each rendered as a card with stats:
```
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│  STRATEGY α        │  │  STRATEGY β        │  │  STRATEGY γ        │
│  Variance: LOW     │  │  Variance: HIGH    │  │  Variance: EXTREME │
│  Avg Δ: +8%        │  │  Avg Δ: +22%       │  │  Avg Δ: +45%       │
│  Rounds tracked: ✓ │  │  [2 rounds ??]     │  │  [4 rounds ??]     │
└────────────────────┘  └────────────────────┘  └────────────────────┘
```
The `??` fields subtly pulse amber — visually suggesting incomplete and potentially dangerous data. The stakes feel like a real tournament interface.

*As built:* the three cards are risk-coded with the semantic tokens (green / yellow / Rosso), the missing rounds are drawn as `?` and `!` placeholders, and the two "rounds untracked" tags pulse at 1Hz. This is a single choice between described risks with a fixed outcome per option; it borrows the Iowa Gambling Task's payoff structure but is not the IGT (no repeated draws, no learning from feedback). The card and consequence text never use the word "score".

**Scenario B — Viral Post Escalation (BART):**

The most dramatic re-skin. The BART balloon pump is reimagined as a **follower count dashboard** — a dark-mode social analytics screen:

```
┌─────────────────────────────────────────────┐
│  REACH: 1,247 followers                     │
│  ENGAGEMENT SPIKE: ████████░░░░ 67%         │
│  REPORT RISK:      ████░░░░░░░░ 28%   ↑     │
│                                             │
│  [1] STOP POSTING    [2] POST ANOTHER +340  │
└─────────────────────────────────────────────┘
```

Each "POST ANOTHER" (Key 2) press:
- Reach rises by a fixed +50 impressions (starting from +100)
- The "Content Flag & Suspension Risk" gauge advances one fifteenth; it reads green below 40%, yellow below 75%, Rosso above
- The post takes 1.5s to "publish": for that long the card reads "PUBLISHING POST...", shows a progress line, and its key badge is muted. A second press during that time does nothing. Securing (Key 1) is always available
- At burst (suspension): a charcoal "ACCOUNT SUSPENDED" card with a Rosso border and headline — minimal, non-strobing, held until the decision timer expires, then consequence text. The splash reports "Reach: 0 impressions", never a "Final Score"

**Single balloon, continuous escalation (ADR-B4).** The run is one balloon inside one 45s window, not a series of trials. The chance that a post triggers suspension starts at 2% and rises 3 points per post (5%, 8%, … 41% on the fourteenth); the fifteenth is certain. On average about six posts survive, so risk and reward escalate across the whole window instead of ending in three presses. Every accepted post logs its number, the hazard it faced, the reach afterwards and the latency since the previous action, which reconstructs the pressure curve per participant.

---

## Domain 5: Rule-Boundary Ambiguity (`rule_ambiguity`)
### Simulation Skin: **"The Incident Room"**

**Visual world:**  
A split-screen layout — left side shows a document/evidence panel (the situation), right side shows a decision terminal. Feels like an investigative or legal interface, cold and procedural. Background: dim, institutional-grey.

**Scenario A — Portal Access Dilemma (MCQ):**

Left panel shows a **portal access log** — system-style text showing the friend's locked account status, the timestamp, the error code. Right panel shows 3 decision tiles. The moral weight isn't from imagery — it's from the specificity of the system log. Seeing "ACCESS_DENIED — LOCK_EXPIRES: 2025-12-15" (past the deadline) makes the dilemma concrete and real.

**Stress amplifier:**  
At 30s mark, a system notification appears at the top: "Inactivity detected. Decision required to proceed." — this is the existing jitter trigger moment, now given a diegetic reason.

**Scenario B — Borrowed Template (MCQ):**

The split panel now shows a **diff viewer** — left side highlights the "borrowed" sections in yellow (the caution token at low opacity with a solid left rule; the matched lines stay in white ink), right side shows the original author's work. The visual is the moral dilemma made tangible: you can see exactly what was taken, how much of the project depends on it, and the deadline counter ticking at the top.

---

## Domain 6: Future Uncertainty (`future_uncertainty`)
### Simulation Skin: **"The Fork"**

**Visual world:**  
A simple but striking visual — two diverging paths rendered as a stylized map/navigation view. Path A is solid, familiar-looking (rendered in the info cyan). Path B is dashed, uncertain (rendered in the caution yellow). The halo under a path is the same token dimmed toward the canvas. Both paths fade to black/fog after a short distance — the participant cannot see where they lead. A compass needle spins slowly in the corner (capped at 4 RPM via `COMPASS_SPIN_MAX_RPM`). A persistent status readout (*"Still processing..."*) sits directly beside the compass to confirm software liveness and eliminate artifactual "is the system frozen?" confusion.

**Scenario A — Track Selection Crossroads (DELAY_WAIT/Post-Wait MCQ):**

The two paths have **tooltips** that appear when the option keys are highlighted — these are the existing "Path A" / "Path B" descriptions but rendered as overlaid info cards that appear when the participant focuses on each option (simulate by auto-showing each info card for 3s cycling before the decision keys appear). The critical [DATA UNAVAILABLE] fields are shown as literally fogged-out sections of the info card.

After selection: the chosen path glows (the path the participant actually chose — the post-wait screen reads the committed option), and the **Processing spinner** is rendered as the compass needle that never settles. The needle stays at or below `COMPASS_SPIN_MAX_RPM` (4 RPM) in both the decision and the post-wait screen; it does not accelerate. The compass carries no cardinal letters in this skin (they collided with the timer bar and the status label). The 12s wait is experienced as a suspended navigation moment. Then consequence text fades in over the foggy path.

**Scenario B — Ambiguous Feedback Before Finals (MCQ):**

The visual world shifts to a **notification/message stack** — like a phone lock screen showing a cryptic message from "INSTRUCTOR" with the ambiguous quote. The 3 response options appear below as draft reply tiles. The message timestamp shows "just now." No further context. The unresolved ambiguity is spatial — the screen shows only this message and nothing else.

---

## Domain 7: Social Evaluation & Authority Response (`social_evaluation`)
### Simulation Skin: **"The Stage"** *(MPU6050 Deception Metric Active)*

**Visual world:**  
The participant faces a **panel of 3 evaluator portraits** — rendered as semi-realistic grayscale silhouettes in a lit room. The participant's "perspective" is from behind a podium. At the bottom of the screen: a horizontal **"Algorithm Confidence"** bar (this is the MPU6050 deception metric visualization).

**Scenario A — Live Panel Presentation Defense (MCQ + Deception):**

The panel portraits are completely neutral — no animation, no expression. The challenge question appears as projected text on the wall behind them. The participant's response options appear as podium cards at the bottom.

| Element | Rendering |
|---|---|
| Panel (3 evaluators) | Grayscale portrait silhouettes, static — unresponsive (TSST protocol). Caption: "PANEL IN SESSION • AWAITING YOUR RESPONSE" — the protocol name is never displayed |
| Challenge question | Projected onto wall panel above evaluators, white text on dark |
| Response options | 3 card tiles at bottom (keyboard 1–3). The chosen card gets a white border and a white "SELECTED" plate — not Rosso |
| Algorithm Confidence bar | Bottom-left, labeled "Composure Analysis: Active", drops 15% after ≥3 consecutive supra-threshold samples (5s cooldown). With no live telemetry it reads "Composure Analysis: Standby / TELEMETRY LINK: STANDBY" and shows no value. Status wording is "MOTION: STEADY / ELEVATED / HIGH" — no fabricated σ figures |
| Jitter (15s mark) | Question text drifts ≤3px at ≤2Hz — simulates evaluator impatience |
| Drone | Low-frequency tension drone activates at final third (≈ last 15s of 45s timer) |

**Scenario B — Public Critique (MCQ + Deception):**

The scene shifts — instead of a panel room, the participant is now at the **front of a classroom**. Rows of seats have silhouette figures watching. A single authority figure (teacher/coach outline) stands to the left, gesturing toward the participant. The critique text appears as speech-bubble text from the authority figure.

The deception metric bar remains active. The "audience silhouettes" create the same uncontrollable evaluation feeling as the TSST panel, but the spatial arrangement (public, classroom) adds a different flavor of social exposure. The skin draws 20 silhouettes (rows of 11 and 9) and its caption says 20; earlier notes that say 28 describe a count that does not fit the layout.

---

## Implementation Notes — What Changes in Code vs. What Stays

| Layer | Change Required | Effort |
|---|---|---|
| `scenario_logic.py` | MIST gained the adaptive per-item countdown; BART gained the linear hazard curve and pump pacing (2026-10-02). REWARD_ACCUMULATOR and DELAY_WAIT are unchanged | — |
| `scenarios.py` | **Minimal** — Add `skin: str` field to `Scenario` dataclass; update priming texts | Low |
| `skins/<skin>.py` | One module per skin, each a class with a single `_draw_skin_<skin>` method; composed in `ui_domains.py` and exposed through `ui.py` (the original single `ui.py` grew to 3,280 lines and was split, ADR-B6) | Medium |
| `ui_effects.py` | **Low** — Skin-specific particle effects (chest shatter, path fade); reuse jitter | Low |
| `audio.py` | **None** — Diegetic drone already implemented | — |
| `engine.py` | **None** — Phase transitions are unchanged | — |

### What Pygame Draws Per Domain

| Domain Skin | Background | Primary Element | Special Element |
|---|---|---|---|
| Exam Hall | Exam room perspective | Desk with paper (text overlay) | Silhouette classmates with completion bars |
| Group Chat | Dark chat UI | Chat bubbles (pre-scripted scroll) | Notification pulse border |
| The Crate | Dark room | Animated chest (scaling rect cluster) | Stability crack polygons |
| The Console | Terminal black | Card tiles (monospace, bordered) | LIVE ranking counter / follower gauge |
| Incident Room | Institutional grey | Split panel (doc + decision) | System notification popup |
| The Fork | Navigation map | Two paths (solid/dashed lines) | Spinning compass, fog overlay |
| The Stage | Evaluation room | 3 portrait silhouettes | Algorithm Confidence bar (MPU6050) |

## Palette Map — What Each Colour Means On Screen (ADR-B5)

| Token | Where a skin uses it |
|---|---|
| Rosso Corsa `#da291c` | Wrong-answer cross and expiring item bar (exam hall); invigilator label; failed module and "FAILED" plate (Kanban); deadline line and policy box (portal log); critique bubble (classroom); projection frame in the final seconds (stage); risk gauge above 75% and the suspension card (analytics); chest cracks and collapse; the highest-risk strategy card (tournament); timer bar in its last tenth |
| Rosso active `#b01e0a` | The dim phase of the 1Hz "rounds untracked" blink; dossier tabs; composure-panel border in the final seconds |
| Warning `#f13a2c` | Small alert text on dark surfaces: "Failure Attribution: YOU", "CAMPUS IT POLICY", risk-profile line, account-standing line |
| Info cyan `#4c98b9` | Telemetry and system labels, Path A, the "? atypical ?" highlight, read receipts, progress arcs |
| Caution yellow `#f6e500` | Integrity banner and matched code lines, Path B, "unresolved / under embargo" tags, visibility notice, unsaved-revision highlight, mid-risk states |
| Success green `#03904a` | Safe options and safe states: secure reach, claim now, passed modules, audited rounds, mic live, "present location" |
| White `#ffffff` | Ink — and the mark of the participant's own selection (border, inverted key badge, "SELECTED" plate) |
| Neutral greys | Everything else: rooms, desks, silhouettes, device frames, panels, cards, avatars, the seal, body text |

The first three questions under "Approval Questions" below are answered by the build: code-drawn geometric shapes; the exam hall framing is kept; chat peers have names and initials on neutral avatar plates. The two `future_uncertainty` scenarios use different environments (fork map, notification stack).

---

## Approval Questions

Before implementation begins, please confirm:

1. **Visual fidelity level** — Should the backgrounds be pre-drawn PNGs (more polished, more asset work) or purely Pygame-drawn geometric shapes (faster, code-only)? Given the 15–25 age range, geometric shapes with good typography may be more credible than low-res hand-drawn art.

2. **Scenario A for `academic_pressure`** — The "exam hall" skin gives it a clear academic setting. The current spec already targets school contexts universally. Do you want to keep the exam hall framing, or should it be more abstract (e.g., a countdown terminal that works for any competitive task)?

3. **Group Chat (peer_influence A)** — Should the chat avatars have placeholder names/initials, or completely anonymous icons (circles with colored fills)? Anonymous may be more universal.

4. **The Fork (future_uncertainty)** — The navigation map metaphor works for track/path selection. For Scenario B (ambiguous feedback), the phone lock-screen metaphor is different from the map. Should the two scenarios share the same skin wrapper, or is it acceptable to have different environments per scenario within the same domain?
