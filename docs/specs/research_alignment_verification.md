# Research Alignment Verification — Updated Domain Implementation Strategy

> **Date:** 2026-09-17
> **Sources cross-referenced:**
> 1. [domain_implementation_strategy.md](file:///c:/Users/AyushShetty/OneDrive/문서/Major%20project%20documents/Pulse/specs/domain_implementation_strategy.md) (updated 2026-09-17)
> 2. [Raw Research & Strategy Notes](file:///C:/Users/AyushShetty/.gemini/antigravity/brain/d98b9bb8-a56d-4a1d-8ae0-c45672a398b2/raw_research_and_strategy_notes.md)
> 3. [Gamification Feasibility Review](file:///C:/Users/AyushShetty/.gemini/antigravity/brain/d98b9bb8-a56d-4a1d-8ae0-c45672a398b2/gamification_feasibility_review.md)
> 4. Obsidian Vault: `Decisions.md`, `PULSE Clinical Stress Paradigms.md`

---

## Verification Methodology

For each of the 14 scenarios, I checked:
1. **Paradigm fidelity** — Does the re-framed narrative still activate the *specific psychological mechanism* the cited paradigm was designed to elicit?
2. **Active ingredient preservation** — Is the core manipulation that produces the target biosignal still intact after the context change?
3. **Locked decisions compliance** — Does the scenario obey every constraint in `Decisions.md` (keyboard-only, no scores, deception metric scope, jitter caps, timing)?
4. **Biosignal prediction validity** — Are the expected physiological markers still logically predicted by the new scenario framing?

---

## Domain 1: Academic Performance Pressure (`academic_pressure`)

### Scenario A: "Exam Countdown Rush" — ✅ UNCHANGED
- **Paradigm:** MIST (Dedovic et al., 2005)
- **Status:** No changes. Identical to original. GPA + timed arithmetic + fake peer comparison bar.
- **Active ingredient:** Social-comparative failure feedback (peer bar always ahead). ✅ Intact.

### Scenario B: "Academic Misconduct Hearing" — ✅ ALIGNED
- **Paradigm:** Evaluative observation (Geen, 1991)
- **Old framing:** "Academic board flagged your transcript for scholarship review"
- **New framing:** "School's academic integrity committee… following an incident during your last exam"
- **Active ingredient check:**
  - Social-evaluative threat (being judged)? ✅ A misconduct hearing is equally evaluative as a scholarship review — arguably *more* stressful because it implies personal fault.
  - Uncontrollability (can't change outcome)? ✅ "The committee's decision will affect your academic standing — it is final."
  - Anticipation of judgment as the stressor, not time pressure? ✅ Same 45s window, no time-rushing mechanics.
  - Unresolved consequence sustaining anxiety past the boundary? ✅ "Their decision will be communicated to you separately."
- **Biosignal prediction:** Unchanged. Evaluative anticipation → elevated tonic SCL + HRV suppression. ✅

> [!NOTE]
> The re-frame actually *strengthens* ecological validity for 15-year-olds — academic misconduct is a more immediate, visceral threat than a scholarship review board (which many 15-year-olds have never encountered).

---

## Domain 2: Peer Influence & Social Conformity (`peer_influence`)

### Scenario A: "Group Chat Vote" — ✅ ALIGNED
- **Paradigm:** Digital Asch conformity (Asch, 1951; Stoll et al., 2022; Berns et al., 2005)
- **Old framing:** "Project team voting on whether to skip a security audit" (workplace IT)
- **New framing:** "Friend group deciding in a chat whether to share a private video of a classmate"
- **Active ingredient check:**
  - **Unanimity of group:** ✅ All 4 friends unanimously selected "share it" — Asch's critical variable (any ally breaks conformity pressure).
  - **Public visibility of dissent:** ✅ "Everyone in this group will see your reply."
  - **No safe choice (both outcomes carry social cost):** ✅ Conforming → classmate is upset; Dissenting → peers call it an overreaction.
  - **Binary choice structure:** ✅ 2 options preserved.
  - **Social pressure as the stressor (not time pressure):** ✅ No timer urgency mechanics.
- **Biosignal prediction:** Acute SCR spike at decision moment, especially when dissenting. ✅ Sharing a private video is a morally loaded act — dissenting carries real social cost, preserving the Asch mechanism.

> [!IMPORTANT]
> The new framing is arguably a *more potent* Asch manipulation for 15–25-year-olds than the workplace IT audit. Sharing someone's private video is a personally relevant, emotionally charged scenario that both age groups understand. The original "system audit" framing required professional IT knowledge.

### Scenario B: "Team Project Review" (was "Unfair Team Blame") — ✅ UNCHANGED
- **Paradigm:** Taboo trade-off (Tetlock et al., 2000)
- **Status:** No changes. School project blame attribution. Already age-appropriate.

---

## Domain 3: Impulsivity vs. Delayed Gratification (`impulsivity_gratification`)

### Scenario A: "The Reward Chest" (was "Instant Loot vs. Multiplier Trap") — ✅ UNCHANGED
- **Paradigm:** Digital Marshmallow Test (McGuire & Kable, 2012)
- **Status:** No changes. Game-style reward chest. Already age-neutral.
- **Reward Accumulator mechanic:** ✅ Intact (CLAIM NOW / KEEP WAITING, collapse at 20–40s).

### Scenario B: "Submit Now vs. Improve More" — ✅ ALIGNED (with note)
- **Paradigm:** Kirby Monetary Choice Questionnaire (Kirby et al., 1999)
- **Old framing:** "Performance review — receive evaluation now or wait for extended assessment"
- **New framing:** "Assignment draft — submit now for adequate grade, or spend more time refining"
- **Active ingredient check:**
  - **Intertemporal choice (certain-now vs. uncertain-later):** ✅ Submit now = guaranteed "Adequate"; wait = chance of "Excellent" OR "Needs significant revision."
  - **Delay period with no information (DELAY_WAIT mechanic):** ✅ 15s waiting screen with "Reviewing additional changes…" — no outcome revealed during the wait.
  - **The waiting period as the primary HRV measurement window:** ✅ Same post-decision delay structure.
  - **Uncertainty about the delayed outcome:** ✅ Randomized between good and bad.
- **Biosignal prediction:** Sustained SCL elevation + HRV suppression during the wait. ✅

> [!NOTE]
> The Kirby MCQ was originally about *monetary* choice (smaller-sooner vs. larger-later). The old framing translated it to *performance evaluation* (certain moderate vs. uncertain better/worse). The new framing translates it to *assignment grades*. Both are valid temporal-discounting translations. The critical mechanism — uncertain delayed reward vs. certain immediate reward — is preserved.

---

## Domain 4: Risk-Reward Tradeoff (`risk_reward`)

### Scenario A: "Tournament Strategy" — ✅ ALIGNED
- **Paradigm:** Iowa Gambling Task (Bechara et al., 1994)
- **Old framing:** "Investment portfolio — 3 assets with incomplete historical data"
- **New framing:** "Online tournament — 3 strategies with incomplete performance data"
- **Active ingredient check:**
  - **Ambiguous probabilities (hidden loss structure):** ✅ "[2 rounds of data missing]" / "[4 rounds of data missing]" — same IGT manipulation as "[2 quarters of data missing]" in the old version.
  - **Three-tier risk gradient:** ✅ Safe/moderate/extreme strategies with identical probability structure (always moderate gain / 60-40 split / 40-60 split).
  - **Gut-level risk assessment where anticipatory SCR activates:** ✅ Incomplete data forces somatic-marker processing.
  - **No scores in the UI:** ✅ Outcomes are narrative ("Ranking dropped significantly"), not numerical point tallies.
- **Biosignal prediction:** Anticipatory SCR *before* selecting the risky option. ✅

### Scenario B: "Viral Post Escalation" — ✅ ALIGNED
- **Paradigm:** BART (Lejuez et al., 2002)
- **Old framing:** "High-risk operation — each step increases system failure risk"
- **New framing:** "Posting bold content online — each post increases report/suspension risk"
- **Active ingredient check:**
  - **Escalating commitment (each action increases both reward and risk):** ✅ Each "POST ANOTHER" press adds reach but raises "Report Risk" gauge.
  - **Pump mechanic (repeated Key 2 presses):** ✅ Identical key mapping — Key 1 to secure, Key 2 to pump.
  - **Binary choice available at every step (stop or continue):** ✅ "STOP POSTING" / "POST ANOTHER."
  - **Total loss on burst:** ✅ "Account Suspended. All accumulated following lost."
  - **Sunk cost / regret in secure consequence:** ✅ "Your account remained active for [X] more potential posts."
  - **Instability gauge visual (BART validated):** ✅ "Report Risk" gauge replaces "System Instability" gauge — same visual mechanic.
- **Biosignal prediction:** Anticipatory SCR increasing with each pump, peaked burst probability. ✅

> [!NOTE]
> "Social media suspension risk" is *more* ecologically valid for 15–25-year-olds than "system failure in a high-risk operation." The BART's core mechanism — escalating commitment under increasing risk — is perfectly preserved. The original Lejuez (2002) paper used an abstract balloon metaphor; the mapping to posts/suspension is as valid as the mapping to system operations.

---

## Domain 5: Rule-Boundary Ambiguity (`rule_ambiguity`)

### Scenario A: "Portal Lockout" (was "Portal Access Dilemma") — ✅ ALIGNED
- **Paradigm:** Personal moral dilemma (Greene et al., 2001)
- **Old framing:** "Admin-level credentials to bypass IT security policy for a locked-out friend"
- **New framing:** "Saved login to friend's submission portal (school IT policy violation)"
- **Active ingredient check:**
  - **Personal responsibility for the consequence:** ✅ "You still have their login saved from a previous help session."
  - **Three-way moral conflict (loyal-but-rule-breaking / rule-following-but-friend-harmed / gray-area-compromise):** ✅ Identical structure — help friend (violate policy), follow rules (friend suffers), exploit loophole (guest access feature).
  - **No "clean" option:** ✅ All three consequences are ambiguous.
  - **Utilitarian vs. deontological tension:** ✅ Option 1 prioritizes friend (utilitarian), Option 2 follows rules (deontological), Option 3 compromises.
  - **Jitter activating at 30s mark:** ✅ Preserved.
- **Biosignal prediction:** Peak SCR during deliberation + elevated response time. ✅

### Scenario B: "Borrowed Template" — ✅ ALIGNED
- **Paradigm:** Taboo trade-off (Tetlock et al., 2000)
- **Old framing:** "Open-source library contains copied proprietary code — IP violation"
- **New framing:** "Group built on a senior's old assignment — potential plagiarism"
- **Active ingredient check:**
  - **Sacred value conflict (academic integrity treated as inviolable vs. utilitarian team benefit):** ✅ Plagiarism is a "sacred" violation in academic contexts — exactly the Tetlock taboo trade-off.
  - **Short-term harm vs. long-term benefit tension:** ✅ Removing it = honest but team delay; keeping it = convenient but academically questionable.
  - **Three-option structure with increasing compromise:** ✅ Remove / acknowledge retroactively / contact original author.
  - **No clear resolution:** ✅ Preserved.
- **Biosignal prediction:** Anticipatory SCR during deliberation, elevated response time. ✅

> [!IMPORTANT]
> The old "open-source library with proprietary code" framing required knowledge of intellectual property law and software licensing — completely opaque to a 15-year-old. The new "borrowed assignment from a senior" framing maps to the *identical* Tetlock mechanism (assigning utilitarian value to something treated as sacred), but is universally understood by anyone who has been in school.

---

## Domain 6: Future Uncertainty (`future_uncertainty`)

### Scenario A: "Track Selection Crossroads" — ✅ ALIGNED
- **Paradigm:** Ambiguous feedback (Hirsh & Inzlicht, 2008)
- **Old framing:** "Career Track Crossroads — two career paths"
- **New framing:** "Track Selection Crossroads — two paths forward"
- **Active ingredient check:**
  - **Incomplete information preventing a fully informed decision:** ✅ `[DATA UNAVAILABLE]` and `[UNDER REVIEW]` tags preserved verbatim.
  - **12s post-decision waiting phase (DELAY_WAIT):** ✅ Unchanged.
  - **Unresolved consequence:** ✅ "Your selection has been recorded. Outcome details will be provided at the end of the evaluation." — NEVER revealed.
  - **Grillon's uncertain-threat window kept open:** ✅ By design.
- **Key change:** "Career" removed from title, replaced with "Track" — intentionally ambiguous (academic stream for younger participants, career/program for older ones). The priming text says "two paths forward" without specifying career/academic.
- **Biosignal prediction:** Sustained tonic SCL elevation (not phasic spikes) + sustained HRV suppression. ✅

### Scenario B: "A Remark Before Finals" (was "Ambiguous Feedback Before Finals") — ✅ ALIGNED
- **Paradigm:** Ambiguous feedback + uncertain threat (Grillon et al., 2004; de Berker et al., 2016)
- **Old framing:** "Algorithm evaluating your session performance — your responses are 'atypical'"
- **New framing:** "Teacher pulls you aside before finals — your approach has been 'atypical'"
- **Active ingredient check:**
  - **The word "atypical" as the core manipulation:** ✅ Preserved verbatim. Still ambiguous (could be better or worse).
  - **Social comparison element:** ✅ "compared to your peers" — unchanged.
  - **No right answer — stress from not knowing what the evaluator wants:** ✅ Three response options, none clearly correct.
  - **10s post-decision waiting phase (DELAY_WAIT):** ✅ "Recalculating assessment parameters…"
  - **Unresolved consequence:** ✅ "Your response pattern has been flagged for secondary review."
- **Biosignal prediction:** Sustained tonic SCL + HRV suppression. ✅

> [!NOTE]
> Replacing an abstract "algorithm evaluating your session" with "your teacher pulls you aside" actually *increases* the social-evaluative threat component (Dickerson & Kemeny, 2004). A human authority figure is a more potent uncertainty + social-evaluative stressor than an algorithm, especially for younger participants.

---

## Domain 7: Social Evaluation & Authority Response (`social_evaluation`)

### Scenario A: "Live Panel Presentation Defense" — ✅ UNCHANGED
- **Paradigm:** TSST (Kirschbaum et al., 1993) + biofeedback amplification (Wieser et al., 2010)
- **Status:** No changes. Panel of neutral-faced evaluators + MPU6050 composure bar.
- **Deception metric:** Active. ✅ Scoped to `social_evaluation` only per `Decisions.md`. ✅

### Scenario B: "Public Critique" — ✅ ALIGNED
- **Paradigm:** Evaluative observation + negative feedback (Geen, 1991; MAST, Smeets et al., 2012)
- **Old framing:** "Direct supervisor flagged your deliverables for a performance review"
- **New framing:** "Teacher or coach singled you out in front of the group"
- **Active ingredient check:**
  - **Social-evaluative threat (being judged on competence):** ✅ Public critique in front of peers.
  - **Uncontrollability (can't change evaluator's perception):** ✅ "One you didn't request" — externally imposed.
  - **False dichotomy ("capability issue or commitment issue"):** ✅ Preserved verbatim — forces defensive position.
  - **MPU6050 Deception Metric ACTIVE:** ✅ Composure monitoring.
  - **Biofeedback amplification loop:** ✅ Tremor → bar drops → more anxiety → more tremor.
- **Biosignal prediction:** Strongest combined autonomic response. ✅

> [!NOTE]
> "Teacher or coach" is a direct translation of "supervisor" that maps to both age groups. For a 15-year-old, a teacher's public critique is their primary social-evaluative authority experience. For a 25-year-old, "coach" or "instructor" in a college/postgrad context still works. The TSST's core mechanism (social-evaluative threat + uncontrollability) is fully preserved.

---

## Locked Decisions Compliance Check

| Locked Decision | Status |
|---|---|
| Keyboard-only input (Keys 1,2,3,4 + SPACE/Enter + TAB/Q + Escape) | ✅ All 14 scenarios use key-number input |
| No numerical scores in UI | ✅ All consequences are narrative text, not point tallies |
| Deception metric scoped to `social_evaluation` only | ✅ Only 7A and 7B have `has_deception_metric=True` |
| Jitter ≤3px, ≤2Hz | ✅ Referenced correctly in 1A and 7A |
| No full-screen color inversions | ✅ Not present in any scenario |
| No strobing >3Hz | ✅ Not present in any scenario |
| Drone: 60–80Hz, final 1/3 of timer, ≤30% volume | ✅ Referenced in 1A and 7A |
| 15s intra-domain rest, 30s inter-domain rest (60s with `--extended-rest`) | ✅ Superseded 2026-10-02 by ADR-B2; the session flow diagram shows 30s |
| Baseline 3 min (or `--fast-baseline` 10s) | ✅ Session flow correct |
| Domain order randomized, all unconditional | ✅ Session flow correct |
| Timeout → `TIMEOUT_NO_RESPONSE` + loss-of-agency consequence | ✅ Not contradicted by any scenario |
| `unix_ts_ms` as timestamp/join key | ✅ Not contradicted |
| Domain IDs: full-word convention from `src/domains.py` | ✅ All 7 correct |
| MIST peer average always accuracy + 15% | ✅ Scenario 1A preserves this |
| BART burst probability increases with pumps | ✅ Scenario 4B preserves this |
| Reward accumulator collapse at 20–40s | ✅ Scenario 3A preserves this |
| `DELAY_WAIT` post-decision phase for `future_uncertainty` only | ✅ Only 6A (12s) and 6B (10s) |
| Score-free consequence design | ✅ All consequences are narrative |

---

## Verdict

> [!TIP]
> **All 14 scenarios are fully aligned with their claimed research paradigms.** The re-framing changed only the narrative surface (context, setting, characters) — not the psychological active ingredients, interactive mechanics, or biosignal predictions. In 5 cases (2A, 4B, 5A, 5B, 6B), the new framing arguably *strengthens* ecological validity for the 15–25 age range.

No corrective action required. The updated `domain_implementation_strategy.md` is research-verified and ready for implementation.

---

## Addendum (2026-10-02): Implementation Audit Against These Paradigms

The verdict above verifies the scenario *designs*. An independent audit on 2026-10-02 checked the *implemented engine* against the same paradigms and found that several designs were not being delivered. Status after remediation:

| Paradigm element | Found in code | Now |
|---|---|---|
| 60s HRV window per scenario (all domains) | Any keypress ended the scenario at 0ms | ✅ Choice held to timer expiry; priming floor keeps the active epoch ≥60s |
| Resting baseline (reference for every z-score) | Paced breathing at 7.5 breaths/min, which inflates resting RMSSD/SDNN | ✅ Static fixation cross, spontaneous breathing |
| Deception inherent to MIST / Asch / TSST | Paradigm name and citation printed on the priming card; "[CONFORM]", "TSST PROTOCOL", "MARSHMALLOW PARADIGM" on screen | ✅ Removed from all participant-facing text |
| 1A MIST: sustained time-pressured arithmetic | Ended after 4 answers; correct key cycled 1-2-3-4; "Peer average: 115%" | ✅ Runs on the clock, randomised positions, figure capped at 100%. ✅ Difficulty now adapts in-run (second addendum) |
| 3B delay discounting: the delay itself | "Request more time" never waited | ✅ 15s `POST_WAIT` on Key 2 |
| 7A/7B biofeedback amplification | No sensor bridge exists; bar showed hard-coded readings; a single noisy sample dropped it 15% | ✅ Honest STANDBY, 3-sample + 5s cooldown gating. ✅ A real bridge now exists (second addendum). ⚠ Not yet run on the physical sensor |
| 4B BART | Single balloon, expected 3.5 safe pumps, certain burst by pump 13 | ✅ Decided and retuned (second addendum). ⚠ Still a single balloon, by design |
| 4A IGT | One-shot choice between described risks with a fixed outcome per option; no learning from feedback | ✅ Relabelled honestly (second addendum). ⚠ Still not the IGT, by design |
| Locked decision: 60s inter-domain rest | Code uses 30s since commit `aeee93d` | ✅ Resolved: 30s default, 60s optional (second addendum) |

Rows marked ⚠ mean the "fully aligned" verdict above does not hold for the running engine in those respects; the second addendum says exactly how far each one goes.

---

## Second Addendum (2026-10-02): Decisions on the Open Paradigm Questions

The five ⚠ rows above were decided and implemented (ADR-B1…B4 in `Decisions.md`). This section states what each scenario now delivers against its cited paradigm, and what it does not.

### The governing decision: one acute-stress window per scenario (ADR-B4)

The pipeline's classifier computes RMSSD and SDNN over 60-second windows, and a session has to cover seven domains without fatiguing the participant. So every scenario is one uninterrupted priming → decision → feedback epoch of at least 60 seconds. Paradigms whose classic form is a long series of discrete trials (BART: about 30 balloons; IGT: 100 draws; MIST: several multi-minute blocks) cannot keep that form here. Each scenario keeps the paradigm's stress mechanism and gives up its trial structure. That is a deliberate trade, and it limits what can be claimed: Pulse's scenarios are *derived from* these paradigms; behavioural indices from the literature (adjusted pumps, net IGT score, MIST block accuracy) are not reproduced and must not be compared with published norms.

### Per-paradigm status

| Scenario | What the paradigm requires | What the engine delivers | Verdict |
|---|---|---|---|
| **1A MIST** (Dedovic et al., 2005) | Arithmetic under a time limit that adapts to the individual so that failure stays frequent; visible comparison with a better-performing peer group | A 40s run of problems, each with its own countdown starting at 8s: −10% after two consecutive correct answers, +10% after two consecutive failures, bounds 3–12s. Time-outs count as failures. Peer bar always ahead; peer figure capped at 100% | ✅ Mechanism present. ⚠ The original calibrates on a training run and targets a 20–45% success rate over minutes; here adaptation happens inside 40s, so only a few steps occur per participant. Whether the failure rate reaches the intended range is an empirical question for the pilot (`item_limit_ms` and `timed_out` are logged for it) |
| **4A** (payoff structure after the IGT, Bechara et al., 1994) | IGT: repeated draws from four decks, learning from gains and losses, anticipatory SCR developing over trials | One choice among three described strategies with stated averages, stated variance and partly missing history; fixed outcome per option | ⚠ **Not the IGT, and no longer labelled as one.** The registry now reads "One-shot risky choice under ambiguity (payoff structure after the Iowa Gambling Task)". The supported claim is narrower: arousal while deciding under described risk with missing information (closer to an Ellsberg-type ambiguity choice). The somatic-marker finding about anticipatory SCR *developing through experience* does not transfer |
| **4B BART** (Lejuez et al., 2002) | Repeated pumps, each raising both payoff and burst risk; total loss on burst; many balloons | One balloon in one 45s window. Hazard 2% on the first pump, +3 points per pump, certain on the fifteenth (about six expected safe pumps); each pump takes 1.5s; every pump logs its hazard, payoff and latency | ✅ Escalating commitment with total loss is intact, and risk now builds across the window instead of ending within three presses. ⚠ Single balloon: no averaging over balloons, no learning across balloons |
| **7A / 7B** biofeedback amplification (Wieser et al., 2010) on a TSST-type evaluative threat | The participant sees a display that tracks their own arousal | The composure bar is driven by the wrist accelerometer through `SerialBridge` (live) or `ReplayBridge` (following the recorder's file), gated at μ + 1.5σ of the resting baseline with a 3-sample / 5s rule. Without live data the display says STANDBY | ✅ Implemented. ⚠ Verified against simulated ports and recorded rows only; the loop has not been observed on a participant. A session logged with `bridge: StubBridge` delivered evaluative threat without biofeedback and must be analysed as such |
| **Inter-domain recovery** | Enough time for tonic arousal to return toward baseline before the next domain | 30s by default; 60s with `--extended-rest` | ⚠ See below |

### Inter-domain rest: what 30 seconds does and does not buy (ADR-B2)

- Heart rate and phasic skin conductance responses recover within seconds to tens of seconds; tonic skin conductance level and vagally mediated HRV can take longer, particularly after the social-evaluative domain. 30s is therefore a partial wash-out, not a return to baseline.
- What protects the analysis is not the rest length alone: every feature is z-scored against the participant's own 3-minute resting baseline, not against the preceding rest; and domain order is randomised per session with the seed logged, so carry-over is spread across domains over participants instead of always favouring the same one.
- The cost of the longer rest is small in absolute terms — six rests per session, so 60s instead of 30s adds 3 minutes (about 24 → 27 minutes). The earlier figure of "14 minutes of idle waiting" was a miscount. The case for the 30s default is therefore session length, engagement and drowsiness over a run of rests, not a large time saving.
- Because the choice is logged (`SYNC_PULSE.inter_domain_rest_s`, `REST_START.duration_s`), sessions run with either value can be told apart, and a carry-over check is possible: compare the first 30s of each domain with the preceding rest and with domain position.
- If a protocol needs domain-level HRV to be free of carry-over without relying on counterbalancing, use `--extended-rest`.

### Revised verdict

All 14 scenarios deliver the stress mechanism their design cites. Two of them (4A, 4B) do so in a deliberately reduced form that is not the cited task, one (1A) adapts on a shorter timescale than the original, and Domain 7's biofeedback is implemented but unproven on hardware. None of these blocks data collection; each bounds what the results may be said to show.
