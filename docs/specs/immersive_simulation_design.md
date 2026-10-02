# Pulse — Immersive Simulation Interface Design
## From Questionnaire → Simulation/Game/Video for All 7 Domains

> **Revision 2 (2026-10-02, UI review, ADR-B9).** The interface was reviewed screen by screen against this document: all 14 skins and every wrapper screen were rendered headlessly in their idle, committed and final-seconds states (94 frames) and read against the rules below. §"Review Record" lists what the review found and what changed. Everything in this document describes the build as it now stands unless it is listed under "Specified, Not Built".

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
- **No construct labels on screen (2026-10-02, extended by ADR-B9):** nothing a participant can read names the paradigm, the construct, the manipulation, or the target cohort. "TSST", "MIST", "Asch", "conform/dissent", "marshmallow", "diegetic", "ambiguity", "uncertainty", "impulsivity", "15–25 demographic" belong in this document, not in the UI. The rule covers four places that the first pass missed:
  - **Scenario titles.** A title names the situation, not the paradigm or a verdict on it (see "Scenario Titles").
  - **The briefing.** It is headed by where the scenario takes place ("EXAM HALL", "CAMPUS IT PORTAL"), never by the research domain ("RULE AMBIGUITY", "PEER INFLUENCE").
  - **Option cards.** An option shows what the participant would do or say. It carries no label that says what choosing it means ("[ AUTHORITY CHALLENGE ]", "(Loyalty)", "Non-Conformist Orientation").
  - **Wait screens.** A wait never says how long it lasts or that information is being withheld.
- **Options are shown as logged (ADR-B9):** a skin draws the registry's option text. Where that text has the form "action — trade-off", the card shows the action as its heading and the trade-off beneath it. No skin keeps its own reworded copy, so what the participant read is what `choice_data` records.
- **Committed choice is held (2026-10-02):** after a keypress the skin shows the locked-in state (chosen card, sent chat bubble, suspension notice, collapsed chest) until the decision timer expires. Every skin must render that state cleanly, and the footer line changes from the key instruction to "RESPONSE RECORDED • PLEASE REMAIN STILL UNTIL THE TIMER ENDS".
- **Sharp 0px corners**, neutral window controls (no OS traffic-light dots).
- **Ferrari palette only (2026-10-02, ADR-B5):** a skin draws neutral greys plus six tokens — Rosso Corsa `#da291c`, Rosso active `#b01e0a`, warning `#f13a2c`, info cyan `#4c98b9`, caution yellow `#f6e500`, success green `#03904a`. No navy panels, no purple accents, no neon cyan, no orange, no coloured avatars. A dimmer shade of a token is made with `_mix()` toward the canvas, never with a new hex.
- **Rosso Corsa means a stress trigger** (wrong answer, failed module, suspension, collapse, a deadline line, the critique bubble, the final seconds). It never fills a key prompt and never marks the option the participant chose.
- **White marks the participant's own choice, on every skin (ADR-B9):** one shared option plate. Chosen: white border, inverted key badge, a white plate carrying the state word ("SENT", "ENTERED", "LOCKED IN"). Passed over: dimmed text and a muted key. No skin marks a choice with green, yellow, cyan or Rosso.
- **Colour never grades a choice (ADR-B9):** on the dilemma and social skins the option cards are neutral — no green "compliant" tag, no Rosso "contest" tag. On the risk skins an option's described risk is a 4px left rule that is drawn identically before and after the choice.
- **Key prompts are neutral plates:** canvas fill, white digit, Grigio border (`_draw_key_badge`). The chosen key inverts to a white plate. A key that is inert is drawn muted, and **an action that takes no key has no key prompt** (ADR-B9).
- **Fixed timing (ADR-B3):** every skin is shown for a 20s briefing, then a 45s decision window (40s for the exam hall), then 4s of consequence. A skin never ends early, so it must look right for the whole window.
- **One layout grid (ADR-B9):** 1280×720, content inside 50px side margins, starting at y=96 under the timer bar, with the one-line instruction on the footer line at y=704.

---

## Design Philosophy

The shift is from **"Read a situation → Pick an answer"** to **"Experience a situation → React to it"**.

Each domain gets a dedicated **simulation skin** — a persistent visual world that wraps the existing mechanics. The underlying data (MIST arithmetic, BART pump counter, reward accumulator) is unchanged. What changes is:

1. **Where the participant feels they ARE** (diegetic context, rendered as a simple Pygame scene)
2. **What the mechanics look like** (re-skinned, not rebuilt)
3. **What they hear** (ambient, subtle, diegetic)

All skins are drawn by code from geometric shapes. No image assets and no video (no synchronization overhead).

Revision 2 adds a fourth principle: **the world is the stimulus; the interface around it is neutral.** The scene carries the pressure (the panel that does not react, the peers who have all voted, the chest that cracks). The parts the participant operates — option cards, key prompts, the footer — look the same in every scenario and say nothing about which answer is expected. A participant should not be able to learn the "right" answer from a colour, a tag, or a title.

---

## Review Record (2026-10-02)

| # | Finding in the build | Resolution |
|---|---|---|
| 1 | The briefing card and the re-read popup were headed by the research domain in capitals ("RULE AMBIGUITY", "IMPULSIVITY GRATIFICATION", "SOCIAL EVALUATION"). | Headed by the setting (`SETTING_LABELS` in `ui_screens.py`). The domain stays in the registry and the logs. |
| 2 | Four scenario titles named the paradigm or judged the situation: "Ambiguous Feedback Before Finals", "Unfair Team Blame", "Instant Loot vs. Multiplier Trap", "Portal Access Dilemma". | Retitled (see "Scenario Titles"). |
| 3 | Option cards carried analyst labels: stance tags on the stage and the classroom, "(Loyalty)" / "(Compliance)" / "(Grey Area)" and "[ STRICTLY COMPLIANT // FRIEND FAILS ]" on the portal, "Draft 3: Critical / Non-Conformist Orientation" on the lock screen, "[ACCEPT]" / "[CONTEST]" / "[ABSTAIN]" on the Kanban board. | Removed. Cards show the registry text only. |
| 4 | Those labels were colour-graded (green for the compliant option, Rosso for contesting, yellow for the risky one), and six skins marked the chosen option in its own colour instead of white. | One shared option plate; white is the only selection mark; dilemma skins have no option colour at all. |
| 5 | Several skins stated the manipulation: "[DECISION UNRESOLVED: BOTH BRANCHES HARBOR CRITICAL UNCERTAINTY]", "[ EVALUATOR INTENT UNRESOLVED: COMMENDATION VS. CRITIQUE FULLY INDETERMINATE ]", "[ TENSION ESCALATION: FINAL ROUND INQUIRY ]", "EXPONENTIAL VALUE MULTIPLIER"; the draft on the document page was titled "An Empirical Investigation of Delayed Rewards & Cognitive Self-Regulation". | Removed or replaced with neutral scene text. |
| 6 | The wait screens announced "12-second algorithmic projection in progress", "[ COMPLETE OUTCOME AMBIGUITY MAINTAINED: ZERO FEEDBACK GRANTED ]" and "[ NO FEEDBACK REVEALED: ASSESSMENT PARAMETERS UNDER EMBARGO ]". A wait that states its length is not an uninformative wait. | Waits show the registry status line and "This will finish on its own. No key is needed." — nothing else. |
| 7 | Portal and diff skins drew their own rewording of the options, different from the text written to `choice_data`. | Skins draw the registry text. |
| 8 | Exam hall: the wrong-answer cross and "INCORRECT" were drawn over the question box. By the time they show, the runner has already advanced, so they covered the *next* item for 200ms. | Cross in the page margin, stamp in the corner of the question box; the item stays readable. |
| 9 | Reward chest: the collapse cross was drawn through its own headline; the claimed state looked the same as the live one; the "KEEP WAITING" card showed a `2` key that the engine ignores. | Collapse is drawn as wreckage with the headline below it; claiming seals the chest in green and stops the pulse; waiting has no key prompt. |
| 10 | Analytics: after suspension the stale figure showed above the notice and the stop card still offered to "lock in" reach. | The notice replaces the dashboard; the cards describe the state they are in. |
| 11 | Document wait: the two status lines overlapped. Hearing: the panel's heads ran into the header rule. Kanban: subtitle and footer collided with their neighbours. | Re-laid out on the shared grid. |
| 12 | The re-read hint floated at x≈870 to dodge the exam clock, off the grid on every other skin. | The exam clock moved onto the hall wall; the hint is right-aligned to the margin everywhere. |
| 13 | Wrapper screens (setup, baseline, briefing, outcome, rest, debrief) were unrelated grey cards; the rest screen was titled "Inter-Domain Rest Period". | One heading plate for all of them; plain wording. |
| 14 | Promised here but missing from the build: staggered chat messages, the chat notification pulse, the portal inactivity notice, the diff deadline counter, the blank participant entry on the Kanban board, the clock pendulum. | Built. What is still missing is listed under "Specified, Not Built". |
| 15 | 15 `_draw_skin_*` methods were 134–304 lines (ARCHITECTURE_SPEC §7.3). | Every skin is split into helpers of at most 60 lines; `skins/` went from 3,127 to 1,725 lines. |

---

## Scenario Titles

The title is participant-facing: it heads the briefing and stays in the header for the whole decision window.

| Scenario | Title | Was |
|---|---|---|
| `peer_influence_b` | Team Project Review | Unfair Team Blame — "unfair" tells the participant how to read the blame before they decide |
| `impulsivity_gratification_a` | The Reward Chest | Instant Loot vs. Multiplier Trap — "trap" gives the answer |
| `rule_ambiguity_a` | Portal Lockout | Portal Access Dilemma — names the paradigm family (moral dilemma) |
| `future_uncertainty_b` | A Remark Before Finals | Ambiguous Feedback Before Finals — "Ambiguous Feedback" is the paradigm's name |

The other ten titles are unchanged. Scenario IDs, domains, option text, consequences and timing are unchanged, so nothing in the event log or the pipeline moves.

---

## The Shared Interface Kit

These parts are identical on every skin. They live in `ui_components.py` and `ui_domains.py`.

| Part | Rendering | Code |
|---|---|---|
| Header | Scenario title top-left. Top-right, aligned to the margin: a `TAB` key plate and "HOLD TO RE-READ THE BRIEFING". | `draw_decision` |
| Timer bar | Full content width at y=75, green → yellow → Rosso in the last tenth. | `draw_decision` |
| Option plate | Idle: dark plate, hairline border. Chosen: lighter plate, white border, inverted key, white state plate at the right. Passed over: darker plate, grey text, muted key. The state plate's width is reserved in every state so the text does not reflow at the keypress. | `_draw_option_frame`, `_draw_option_card` |
| Accent rule | Optional 4px rule down the left edge of an option plate. Risk skins use it for the option's described risk; the fork uses it as the route's legend colour. Dimmed toward the canvas when the option is passed over. | `_draw_option_frame(accent=…)` |
| Key badge | Canvas fill, white label, Grigio border; inverted when chosen; muted when inert. | `_draw_key_badge` |
| Tag | Small sharp-cornered label plate. | `_draw_tag` |
| Footer prompt | One line at y=704. Idle: the key instruction. Over: "RESPONSE RECORDED • PLEASE REMAIN STILL UNTIL THE TIMER ENDS" (the chest and the analytics skin name their own ending: "THE CHEST HAS COLLAPSED", "THE ACCOUNT IS SUSPENDED"). | `_draw_footer_prompt` |
| Silhouette | Featureless head and shoulders, any size. Observers have no eyes and no mouth: nothing can be read from them. | `_draw_silhouette` |
| Window chrome | Title bar with three neutral square controls. | `_draw_window_chrome` |
| Spinner | Ring of eight square marks, at most 0.5 revolutions per second. | `_draw_spinner` |
| Progress line | 3px track and fill. | `_draw_progress_line` |

---

## Session Frame Screens

The screens around the scenarios share one heading plate (`_draw_plate`): a small cyan label, a title, a hairline, left-aligned at x=140.

| Screen | Rendering |
|---|---|
| Setup (`ID_INPUT`) | "SESSION SETUP / PULSE", the subject-ID field, `ENTER` confirm and `ESC` quit as key plates. An invalid ID is reported in the warning token. |
| Baseline | "RESTING BASELINE", the instruction, a static fixation cross. The time left is a thin muted progress line and a small `m:ss remaining` in the corner, so it does not pull the eyes off the cross. No breathing pacer (audit finding B2). |
| Briefing (`PRIMING`) | "BRIEFING • <SETTING>", the scenario title, the briefing text at 24px, a key legend (the answer keys and `TAB`), a progress line for the 20s, and the start line. Before the read floor: "Read the briefing • starts in N s". After it: a `SPACE` plate, "begin now • starts by itself in N s". |
| Re-read popup | The same heading over a dimmed scene, the briefing, "YOUR CHOICES" with the registry options (not shown for the arithmetic run), "HOLDING TAB — RELEASE TO RETURN", and "The timer keeps running while this briefing is open." |
| Outcome (`FEEDBACK`) | "OUTCOME" and the consequence text at 24px beside a 4px rule: grey normally, Rosso for a collapse or a suspension. A thin line fills over the 4s. The suspension badge and the shatter particles appear for those outcomes only. |
| Rest | "REST", "Short pause" (15s, inside a domain) or "Rest break" (30s / 60s, between domains), one instruction, the seconds left in cyan, a progress line. |
| Debrief | "SESSION COMPLETE", "Thank you for taking part.", session length, scenarios completed, `ESC` to close. |

Settings shown on the briefing: `exam_hall` EXAM HALL · `misconduct_hearing` INTEGRITY BOARD · `group_chat` CLASS GROUP CHAT · `team_kanban` SPRINT REVIEW · `reward_crate` REWARD VAULT · `document_workspace` ASSIGNMENT EDITOR · `tournament_bracket` TOURNAMENT LOBBY · `social_analytics` CREATOR STUDIO · `portal_log` CAMPUS IT PORTAL · `code_diff` CODE REVIEW · `fork_map` ROUTE PLANNER · `notification_stack` LOCK SCREEN · `defense_stage` REVIEW PANEL · `classroom_critique` CLASSROOM.

---

## Domain 1: Academic Performance Pressure (`academic_pressure`)
### Simulation Skin: **"The Exam Hall"**

**Visual world:**
The participant's desk fills the lower two thirds of the screen, with the exam script on it. The back of the hall runs along the top: three classmates at their desks, the wall clock, and in the final 20s the invigilator.

**Scenario A — Exam Countdown Rush (MIST Arithmetic):**

| Element | Rendering |
|---|---|
| Exam script | Off-white page with a margin line and a printed header. The current item sits in a framed box; four answers in a two-by-two grid with paper-white key squares. "PRESS 1, 2, 3 OR 4 TO ANSWER" is printed at the foot of the page. |
| Per-item countdown | A bar along the bottom edge of the question box. It drains in dark ink and turns Rosso in the last quarter of the item's time. |
| Wrong or timed-out item | For 200ms: a Rosso cross in the page margin and an "INCORRECT" stamp in the corner of the question box. Neither covers the item, because by then the next item is already on the page. |
| Classmates | Three seated silhouettes, each with a completion bar that stays 13 / 15 / 17 points ahead of the participant ("Desk 2 • 65%"). |
| Wall clock | On the wall at the right. Its hand is dark ink and turns Rosso in the last tenth; the seconds are printed beside it in the timer colour. A pendulum swings at 0.5Hz, rising to 1Hz (`PENDULUM_SWING_MAX_HZ`) in the final third; its phase is continuous across the change. |
| Invigilator | A standing silhouette with a clipboard walks the back row, behind the desks, for the final 20s (there and back about every 8s). It carries no label. |
| Jitter | The page drifts ≤3px at ≤2Hz for the final 20s. |

**Adaptive difficulty (ADR-B3):** each problem has its own countdown, 8s at the start. Two correct answers in a row shorten it by 10%, two failures in a row lengthen it by 10% (3–12s). An unanswered problem is marked wrong and replaced. This is the MIST adaptation done inside the run; there is no separate practice or pretest block.

**Scenario B — Academic Misconduct Hearing (MCQ):**

A committee room. Three silhouettes sit behind a long table with a dossier and a nameplate each (chair, dean, student advocate). They are featureless and never move: the unresponsiveness is shown, never stated. Above them, a recording dot and the case line ("ACADEMIC INTEGRITY BOARD • CASE FILE #AIB-2026-08492 • INQUIRY PROCEEDING"); below, the caption "COMMITTEE PANEL IS OBSERVING — FORMAL RECORDING IN PROGRESS". The lower half is the statement terminal: "BINDING SUBMISSION" in Rosso, and the three statements as option plates. The chosen one is marked "ENTERED".

---

## Domain 2: Peer Influence & Social Conformity (`peer_influence`)
### Simulation Skin: **"The Group Chat Simulator"**

**Scenario A — Group Chat Vote (Asch Conformity):**

A phone frame in the centre of the screen: "Class Group", five members, four online.

| Element | Rendering |
|---|---|
| Peer messages | Four messages arrive 0.6s apart. The wording differs so it reads as a chat; the position is unanimous ("Share it. It's already going around anyway." / "Yeah, share it." / "Agreed, send it to the other group." / "Do it. Share."). Each has a timestamp and a double read tick. |
| Avatars | Neutral grey plates with white initials (ADR-B5). Peers are told apart by initial and name, not by hue. This also applies to the four teammate cards on the Kanban board in Scenario B. |
| Visibility notice | "Everyone in this group will see your reply." in the caution yellow, pinned under the header. |
| Typing indicator | "Jake is typing..." once all four messages are in, until the participant replies. |
| Notification pulse | The phone's border breathes between two dim shades of the caution yellow at 1Hz (`NOTIFICATION_PULSE_HZ`) — strictly non-strobing. |
| Quick replies | Two option plates with the option text only. They are NOT tagged "[CONFORM]" / "[DISSENT]" (removed 2026-10-02): conformity is recorded in the log (`is_conforming`), never shown. |
| Sent reply | After the keypress the reply appears as the participant's own bubble ("You • 12:44", one delivery tick) for the rest of the timer, and the chosen quick reply is marked "SENT". The bubble is the same neutral grey for either reply: its colour must not grade the choice. |

**Scenario B — Team Project Review (MCQ):**

A sprint review board, cold and impersonal. Four module cards: three passed (green status), "Core Integration" failed (Rosso border, "FAILED" plate). Under them, four teammate review cards, each ending in "Failure Attribution: YOU". The participant's own entry is the response panel: "YOUR ASSESSMENT:" followed by a cursor that blinks at 1Hz until a response is committed, then "SUBMITTED". The three responses are plain option plates — no "[ACCEPT]" / "[CONTEST]" / "[ABSTAIN]" tags.

---

## Domain 3: Impulsivity vs. Delayed Gratification (`impulsivity_gratification`)
### Simulation Skin: **"The Crate"**

**Scenario A — The Reward Chest (REWARD_ACCUMULATOR):**

A vault ("VAULT 03 • SECURE REWARD STORAGE") with a chest in the centre, its value above it and a stability gauge on the left wall.

| Element | Rendering |
|---|---|
| Chest | Drawn from scaled rects (not `pygame.transform.smoothscale()`): 380×224 at rest, growing to 1.15× as the value rises, with a 2% pulse at 0.8Hz. |
| Glow | The seam, lock core and vents run along the semantic tokens: info cyan → caution yellow → Rosso as collapse risk grows — one of the three sanctioned token-to-token gradients. |
| Cracks | Four cracks appear at 20%, 45%, 70% and 85% instability; the last two are Rosso. |
| Stability gauge | Success green → caution yellow → Rosso Corsa as it drains, with its own cracks at 35% and 65%. |
| Value | "CHEST VALUE" and the number, in the glow colour. |
| Claim | `[1] CLAIM NOW`, "Secure the current value: N", with a green accent rule. |
| Wait | "KEEP WAITING — The value keeps multiplying. The chest may collapse.", with a yellow accent rule and **no key badge**. Waiting is what happens when no key is pressed; the engine ignores key 2 in this scenario, so the screen does not prompt it. |
| Claimed (held) | The glow turns green, the pulse stops, the readout becomes "VALUE SECURED", the claim card is marked "CLAIMED". |
| Collapse (held) | The chest is replaced by broken halves outlined in Rosso, 12 shards scatter for 600ms, the headline "CHEST COLLAPSED / ALL ACCUMULATED VALUE LOST" sits below the wreck, the gauge reads "0% COLLAPSED", both cards dim, and the claim card reads "Nothing is left to claim." |

**Scenario B — Submit Now vs. Improve More (DELAY_WAIT):**

An assignment editor: title bar, menu, the draft on a white page, a status bar ("Draft status: Adequate — requirements met"). The draft is titled as an ordinary coursework paper ("Urban Green Space and Summer Air Temperature: A Field Study"); one paragraph carries the unsaved-revision highlight, which is the caution yellow washed into the paper white, not a separate pastel. Two option plates: submit now (green accent rule), request more time (yellow accent rule). Key 1 goes to the consequence; Key 2 enters the 15s `POST_WAIT`, described under "Wait Screens".

---

## Domain 4: Risk-Reward Tradeoff (`risk_reward`)
### Simulation Skin: **"The Console"**

**Scenario A — Tournament Strategy (one-shot risky choice / Standard MCQ):**

Three strategy cards side by side. Each card is one option plate with a key badge and an accent rule in its risk colour (green / yellow / Rosso), and inside it:

```
┌───────────────────────┐
│ [1] Strategy Alpha    │   name, protocol line
│ ┌───────────────────┐ │
│ │     +8% AVG       │ │   projected round gain
│ └───────────────────┘ │
│ Variance: LOW  ▬      │   bar length = spread (short is low)
│ ROUND HISTORY 6 OF 6  │
│ ▮ ▮ ▮ ▮ ▮ ▮           │   one bar per round on record,
│ R1 … R6               │   an empty "?" slot per missing round
│ [OK] 6/6 AUDITED      │   record tag
│ Risk Profile: 1 / 10  │
└───────────────────────┘
```

Beta has two missing rounds and Gamma four; their record tags ("[ 2 ROUNDS UNTRACKED ]", "[ 4 ROUNDS UNTRACKED — EXTREME VARIANCE ]") pulse at 1Hz. The variance bar now reads the way it is labelled — longer means more spread (it was inverted). The chosen card gets the white border and a "SELECTED" plate; the other two dim. This is a single choice between described risks with a fixed outcome per option; it borrows the Iowa Gambling Task's payoff structure but is not the IGT (no repeated draws, no learning from feedback). The card and consequence text never use the word "score".

**Scenario B — Viral Post Escalation (BART):**

The BART balloon is a creator-studio dashboard.

| Element | Rendering |
|---|---|
| Reach | "ACCUMULATED AUDIENCE REACH (IMPRESSIONS)" and the number, starting at 100 and rising by 50 per post. |
| Posts | A row of 15 slots, one per possible post. A slot fills when its post is published; the newest fills left to right over the 1.5s it takes to publish. |
| Risk gauge | "Content Flag & Suspension Risk": advances one fifteenth per post; green below 40%, yellow below 75%, Rosso above, with a status line under it. |
| Stop | `[1] STOP POSTING`, "Lock in N impressions and stop here.", green accent rule. Always available. |
| Post | `[2] POST ANOTHER`, yellow accent rule, Rosso once the gauge passes 75%. While a post is publishing the card reads "PUBLISHING POST...", shows a progress line, and its key is muted; a second press during that time does nothing. |
| Secured (held) | The number turns green under "REACH SECURED", the status reads "CAMPAIGN CLOSED — REACH LOCKED IN", the stop card is marked "SECURED". |
| Suspension (held) | The whole dashboard is replaced by a charcoal notice with a Rosso border: "ACCOUNT SUSPENDED", the violation line, "Reach: 0 impressions | Account standing: suspended" — never a "Final Score". No stale figure remains on screen. The stop card dims to "Nothing is left to secure." |

The "LIVE CAMPAIGN" marker in the navigation bar is the info cyan. It is a status, not a stress trigger, so it is not Rosso.

**Single balloon, continuous escalation (ADR-B4).** The run is one balloon inside one 45s window, not a series of trials. The chance that a post triggers suspension starts at 2% and rises 3 points per post (5%, 8%, … 41% on the fourteenth); the fifteenth is certain. On average about six posts survive, so risk and reward escalate across the whole window instead of ending in three presses. Every accepted post logs its number, the hazard it faced, the reach afterwards and the latency since the previous action, which reconstructs the pressure curve per participant.

---

## Domain 5: Rule-Boundary Ambiguity (`rule_ambiguity`)
### Simulation Skin: **"The Incident Room"**

**Scenario A — Portal Lockout (MCQ):**

Split screen. Left, a terminal on the campus IT gateway's audit log: a system clock that counts with the timer, the lockout, the 21-day ticket, the deadline line, the stored session, and at the bottom the policy clause in a Rosso frame. The moral weight is not in imagery; it is in the specificity of the log. Right, the decision terminal with three neutral option plates. Each shows the registry text: the action as its heading, the trade-off beneath ("Tell them to file an official complaint / Follows policy, friend misses the deadline").

**Stress amplifier:** for the final 15s — the moment the jitter starts — a sixth entry is written to the log: "[SESSION] INACTIVITY DETECTED — DECISION REQUIRED", and the system clock turns to the warning token. Both follow the clock only, so they appear whether or not a choice has been made.

**Scenario B — Borrowed Template (MCQ):**

A diff viewer. A banner in the caution yellow reads "INTEGRITY CHECK: 38% OVERLAP WITH AN UNCREDITED SOURCE" and, at its right, a deadline that counts down ("SUBMISSION DEADLINE IN 2d 06:14:41"). Two panes: the group's file and the graduated senior's archive. The three matched lines sit on a translucent yellow band with a solid left rule, in white ink. Below, three neutral option plates with the registry action and trade-off; the chosen one is marked "COMMITTED".

---

## Domain 6: Future Uncertainty (`future_uncertainty`)
### Simulation Skin: **"The Fork"**

**Scenario A — Track Selection Crossroads (MCQ + 12s wait):**

A route planner. An approach road leads up from "PRESENT LOCATION" to a junction, where two routes diverge: Path A solid, in the info cyan; Path B dashed, in the caution yellow. The halo under a path is the same token dimmed toward the canvas. Each ends in a destination card that holds the one thing the registry says about it — "LONG-TERM GROWTH: [DATA UNAVAILABLE]" and "SUPPORT STRUCTURE: [UNDER REVIEW]" — and the new path's destination sits in fog. The cyan and yellow are the routes' legend colours: each option plate carries its route's colour as an accent rule so the card can be matched to the road. They are not a risk grade.

In the corner a compass needle drifts at 4 RPM (`COMPASS_SPIN_MAX_RPM`) and never settles. Beside it is its true bearing ("BEARING 264°"), which also shows that the software is alive. The needle is white and grey; the compass carries no cardinal letters.

After the keypress the chosen route is lit, the other turns grey, the header reads "ROUTE LOCKED IN", and the chosen plate is marked "LOCKED IN". When the timer expires the 12s wait follows on the same map (see "Wait Screens").

**Scenario B — A Remark Before Finals (MCQ + 10s wait):**

A phone lock screen: the time, the date, and one notification from "ACADEMIC SUPERVISOR": *"Your approach throughout this term has been... `? atypical ?` compared to your peers."* The one word that carries the remark is set apart in the info cyan. There is no further context: the screen shows only this message. Below it, "REPLY DRAFTS": three option plates, each holding the sentence the participant would send, in quotation marks. The drafts are not named or classified. The chosen one is marked "SENT".

---

## Domain 7: Social Evaluation & Authority Response (`social_evaluation`)
### Simulation Skin: **"The Stage"** *(MPU6050 Deception Metric Active)*

**Scenario A — Live Panel Presentation Defense (MCQ + Deception):**

| Element | Rendering |
|---|---|
| Challenge question | Projected on the wall above the panel, white on dark, under "REVIEW PANEL • QUESTION TO THE PRESENTER". The projection's frame turns Rosso for the final third. That frame is the only escalation cue; the skin no longer prints "[ TENSION ESCALATION ]". |
| Panel (3 evaluators) | Large featureless silhouettes behind a bench with dossiers and nameplates — unresponsive (TSST protocol). Caption: "PANEL IN SESSION • AWAITING YOUR RESPONSE" — the protocol name is never displayed. |
| Podium | "PODIUM MIC: LIVE" in green. |
| Response options | Three option plates with the registry text only (keyboard 1–3). The chosen plate gets the white border and a "DELIVERED" plate — not Rosso. |
| Composure bar | Under the options, labeled "Physiological Composure Analysis: Active", drops 15% after ≥3 consecutive supra-threshold samples (5s cooldown). With no live telemetry it reads "Standby / TELEMETRY LINK: STANDBY" and shows no value. Status wording is "MOTION: STEADY / ELEVATED / HIGH" — no fabricated σ figures. |
| Jitter (15s mark) | The scene drifts ≤3px at ≤2Hz — simulates evaluator impatience |
| Drone | Low-frequency tension drone activates at final third (≈ last 15s of 45s timer) |

**Scenario B — Public Critique (MCQ + Deception):**

The front of a classroom. The instructor stands at the left, arm out toward the participant; the critique is a speech bubble from the instructor, framed in dim Rosso and in full Rosso for the final third ("THE INSTRUCTOR, TO YOU, IN FRONT OF THE CLASS"). Two rows of silhouettes watch: 11 behind and 9 in front, 20 in all, and the caption says 20 ("20 CLASSMATES ARE WATCHING IN SILENCE"). Three plain option plates, then the composure bar.

---

## Wait Screens

A wait redraws the scene the participant just left, so the world does not change under them. It never states its length and never says that information is being withheld (`test_wait_screens_say_nothing_about_the_wait`).

| Wait | Rendering |
|---|---|
| `document_workspace`, 15s (Key 2 only) | The same editor, titled "Review in progress". A cyan scan line crosses the page every 2.5s. A status card: spinner, the registry line "Reviewing additional changes...", "The review will finish on its own. No key is needed." |
| `fork_map`, 12s | The same map with the committed route lit. The header shows the spinner and "Synthesizing outcome projections..."; the compass keeps drifting at 4 RPM and does not accelerate; the option cards are replaced by "YOUR ROUTE IS LOCKED IN / Nothing further can be changed." |
| `notification_stack`, 10s | The same lock screen, dimmed, with "Your reply • Sent" under the message. A status card: spinner, "Recalculating assessment parameters...", "No reply yet. This will finish on its own." |

---

## Implementation Notes — Where Things Are

| Layer | Contents |
|---|---|
| `ui_core.py` | Surface, fonts (44 / 28 / 24 / 20 / 16 / 13 sans, 17 / 14 / 12 mono), the layout grid (`MARGIN`, `CONTENT_TOP`, `FOOTER_Y`), `_draw_text`, `_wrap_lines`, `_draw_wrapped_text`, `_mix`, `_draw_card` |
| `ui_components.py` | The shared interface kit, the compass, the composure bar, and the widgets of the skinless fallback layout |
| `ui_domains.py` | `draw_decision` (header, timer bar, skin dispatch) and the fallback layouts used only when a skin has no runner |
| `ui_screens.py` | The session frame screens and `SETTING_LABELS` |
| `ui_post_wait.py` | `draw_post_wait`: picks the wait scene from the scenario's status text |
| `skins/<skin>.py` | One module per skin: `_draw_skin_<skin>` plus its helpers. The three skins with a wait also hold `_draw_post_wait_<skin>`, built from the same scene helper as the decision screen |
| `ui_effects.py` | Jitter, vibration, timer colour, flash, shatter — unchanged |
| `scenarios.py` | Four titles changed; nothing else |
| `engine.py` | `_render` passes the rest duration to `draw_rest` for its progress line; nothing else |
| `scenario_logic.py`, `audio.py`, the other engine modules | Unchanged |

### What Pygame Draws Per Domain

| Domain Skin | Background | Primary Element | Special Element |
|---|---|---|---|
| Exam Hall | Hall wall and desk | Exam script (question, countdown, four answers) | Peer desks with completion bars, pendulum clock, invigilator |
| Group Chat | Phone frame | Chat bubbles (staggered arrival) | Notification pulse border, typing indicator |
| The Crate | Vault | Chest (scaled rect cluster) | Stability gauge, cracks, wreckage on collapse |
| The Console | Dashboard | Strategy cards / reach dashboard | Missing-round slots / post slots and risk gauge |
| Incident Room | Institutional grey | Split panel (evidence + decision) | Inactivity log entry / deadline counter |
| The Fork | Route map / lock screen | Two routes / one notification | Drifting compass with bearing, fog |
| The Stage | Panel room / classroom | Silhouettes that do not react | Composure bar (MPU6050) |

## Palette Map — What Each Colour Means On Screen (ADR-B5, revised ADR-B9)

| Token | Where a skin uses it |
|---|---|
| Rosso Corsa `#da291c` | Wrong-answer cross, "INCORRECT" stamp and expiring item bar (exam hall); the clock hand in the last tenth; recording dot and "BINDING SUBMISSION" (hearing); failed module and "FAILED" plate (Kanban); policy box (portal log); critique bubble in the final third (classroom); projection frame in the final third (stage); risk gauge above 75%, the post card's rule at that point, and the suspension notice (analytics); late chest cracks, wreckage and collapse; the highest-risk strategy card's rule and figures (tournament); timer bar in its last tenth; the outcome rule after a collapse or suspension |
| Rosso active `#b01e0a` | Dossier tabs; the critique bubble before the final third; the missing-round slots on the highest-risk strategy; composure-panel border in the final seconds |
| Warning `#f13a2c` | Small alert text on dark surfaces: "REC", "Failure Attribution: YOU", "SPRINT GRADE", "CAMPUS IT POLICY", the deadline lines, the inactivity entry, the third strategy's risk line, account-standing line, an invalid subject ID |
| Info cyan `#4c98b9` | Telemetry and system labels, screen heading labels, Path A, the "? atypical ?" word, read receipts, spinners and scan lines, the "LIVE CAMPAIGN" marker, published post slots, progress lines on the briefing and rest screens |
| Caution yellow `#f6e500` | Integrity banner and matched code lines, Path B, the visibility notice and the phone's notification pulse, unsaved-revision highlight, mid-risk states, the waiting card's rule (chest), "HOLDING TAB" |
| Success green `#03904a` | Safe states and the accent rule of the safe option on risk skins: claim / stop / submit now, a secured reach or a claimed chest, passed modules, audited rounds, mic live, "4 online", the terminal's command line, "present location" |
| White `#ffffff` | Ink — and the only mark of the participant's own selection (border, inverted key badge, state plate) |
| Neutral greys | Everything else: rooms, desks, silhouettes, device frames, panels, option plates, avatars, the seal, the compass needle, body text |

Colour is never used to say which option is the proper one. On the dilemma and social skins (hearing, chat, Kanban, portal, diff, lock screen, stage, classroom) the option plates have no chromatic colour in any state.

---

## Specified, Not Built

| Item | State |
|---|---|
| Pencil-on-paper ambience in the exam hall | Not built. `audio.py` plays the tension drone only. |
| Hall brightness flicker (±5%, ≤2Hz) in the final seconds | Not built. `BRIGHTNESS_FLICKER_MAX_PCT` / `_HZ` exist in `constants.py` and are unused. It would be the only full-screen luminance change in the session, so it is left for an explicit decision. |
| Chest growth to 1.6× and a value figure growing 32pt → 54pt | The chest grows to 1.15× and the figure is fixed at 44pt. |
| Fork info cards that cycle for 3s each before the keys appear | Dropped. Both destination cards and both options are on screen from the first frame; nothing delays the decision keys. |
| Screen vibration for the unstable chest | `ScreenVibration` exists and is bounded (≤2px, ≤2Hz), and the skins apply `vibration_offset`, but the engine never sets it: no commit has wired it. The chest therefore does not shake in a real session. |

## Open Questions for the Owner

1. **Risk colour on the risk skins.** Tournament, analytics, chest and editor still colour an option's described risk green / yellow / Rosso. It is now a left rule instead of a full border, and it is the same before and after the choice, but it is still a valence cue. Whether it biases choice is an experimental-design question (also listed in ARCHITECTURE_SPEC §7.3). The neutral alternative is one argument away: drop `accent=` on those cards.
2. **Tournament card copy.** "Risk Profile: 9.5 / 10 (Critical Downside)" and "catastrophic ranking drop risk" state the risk of the third strategy outright. If the scenario is meant to be a choice under incomplete information, the missing-round slots already carry that; the verdict lines could go.
3. **Vibration.** Wire `ScreenVibration` into the reward scenario, or delete it from the specs.
4. **The four new titles.** They are in `scenarios.py` and pinned by `test_scenario_titles_and_durations`; change them there if different wording is preferred.
5. **"PLEASE REMAIN STILL" after a commit.** The footer asks for stillness during the held state, which helps the PPG and GSR traces. On the two `social_evaluation` skins it sits beside the composure bar and reinforces it. Confirm that is wanted there.

## Earlier Approval Questions (answered by the build)

1. **Visual fidelity** — code-drawn geometric shapes; no image assets.
2. **Exam hall framing** — kept.
3. **Chat peers** — names and initials on neutral avatar plates.
4. **`future_uncertainty` environments** — the two scenarios use different environments (route planner, lock screen).
