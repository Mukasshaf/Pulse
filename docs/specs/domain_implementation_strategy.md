## type: implementation-strategy status: active updated: 2026-09-17

# Pulse — 7 Domain Implementation Strategy

Research-grounded scenario designs for each behavioral domain. Every mechanic is mapped to a validated stress paradigm and a specific biosignal target (GSR phasic, GSR tonic, or HRV suppression).

---

## Session Flow

```
Baseline (3 min) → [Domain A → Scenario 1 → 15s rest → Scenario 2 → 60s rest] × 7 domains → Debrief
```

All domains presented in **randomized order**, all unconditional. Keyboard-only input. No scores. No music during active scenarios.

---

## Domain 1: Academic Performance Pressure (`academic_pressure`)

### Core Mechanism
Combines **cognitive overload** with **social-evaluative threat** — the participant's competence is under visible, timed evaluation. Grounded in the MIST protocol (Dedovic et al., 2005) and PASAT (Gronwall, 1977; Lejuez et al., 2003).

> **Key finding:** The MIST's adaptive difficulty algorithm (targeting ~45–50% failure rate) combined with a fake "peer average" comparison bar reliably induces cortisol, elevated HR, and EDA increases. The stress comes from *perceived underperformance relative to peers*, not task difficulty alone.

### Expected Biosignal Profile

| Signal | Expected Change | Why |
|---|---|---|
| `scr_count` / `scr_max_amp` | ↑ Phasic spikes at failure moments | Each "wrong answer" or timer expiry triggers acute sympathetic activation |
| `scl_mean` | ↑ Elevated tonic level | Sustained cognitive effort maintains sympathetic tone |
| `rmssd` / `sdnn` | ↓ Suppressed | Vagal withdrawal under sustained cognitive load (Taelman et al., 2011) |
| `mean_hr` | ↑ 5–15 BPM above baseline | Combined cognitive + evaluative demand |

### Scenario A: "Exam Countdown Rush" — Factor: Time Pressure + Stakes

**Paradigm basis:** MIST arithmetic stress (Dedovic et al., 2005)

**Priming (8s):**
> *"Your semester final grade / GPA hinges on this assessment. You have 40 seconds. The system will compare your results against other participants."*

*Note on Adaptive Difficulty Calibration (Dedovic et al., 2005):* Immediately before the countdown begins, participants complete 3 untimed practice problems (`calibrate_mist_difficulty()`) to establish starting tier (`easy`, `medium`, or `hard`), ensuring the session targets the validated ~45–50% error rate across varying arithmetic skills.

**Decision phase (40s):**
A rapid-fire sequence of **4 arithmetic problems** presented one at a time. Each problem has 4 answer options (keys `1`, `2`, `3`, `4`). A visible countdown timer ticks down for the entire sequence. After each answer (right or wrong), the next problem appears immediately.
*(Note: Per C1 architectural contract, the DECISION state holds for the full 40s to guarantee the required 60s active epoch for ML classification).*

**Stress mechanics:**
- A fake **"Peer Average" progress bar** sits at the top of the screen, always slightly ahead of the participant's position — creating the impression of underperformance (MIST's core manipulation).
- Timer bar transitions green → amber → red with the locked diegetic tension drone kicking in during the final third.
- Subtle text jitter (≤3px, ≤2Hz) activates on the last 2 problems.
- If the participant gets one wrong, a brief red flash on the answer button (200ms, no full-screen flash).

**Consequence (4s):**
> *"Assessment complete. Your accuracy: [X]%. Peer average: [X+15]%. Results have been logged."*

The peer average is always shown as higher regardless of actual performance — this is the MIST's validated social-comparison manipulation.

---

### Scenario B: "Academic Misconduct Hearing" — Factor: Stakes without Time Urgency

**Paradigm basis:** Evaluative observation paradigm (Geen, 1991) — the *anticipation* of judgment is the stressor, not time pressure.

**Priming (8s):**
> *"You've been called before your school's academic integrity committee following an incident during your last exam. You must submit a written statement. The committee's decision will affect your academic standing — it is final."*

**Decision phase (45s):**
A single, high-stakes MCQ with 3 options representing different response strategies:
- **Option 1 (Key 1):** Accept responsibility and request leniency
- **Option 2 (Key 2):** Challenge the committee's conclusion as based on incomplete evidence
- **Option 3 (Key 3):** Provide documentation that the incident was a misunderstanding

No time-rushing mechanics here — the stress comes from the *weight of the decision* and the stated finality of the outcome.

**Consequence (4s):**
> *"Your statement has been submitted to the committee. Their decision will be communicated to you separately."*

Deliberately unresolved — sustains evaluative anxiety past the scenario boundary.

---

## Domain 2: Peer Influence & Social Conformity (`peer_influence`)

### Core Mechanism
The stress arises from **normative social influence** — the conflict between personal judgment and perceived group consensus. Grounded in the Asch conformity paradigm (Asch, 1951) and neuroimaging work showing amygdala activation during dissent (Berns et al., 2005, *Biological Psychiatry*).

> **Key finding:** Non-conforming responses (going *against* the group) produce higher GSR than conforming responses — the stress is specifically associated with the *act of social resistance*, not the decision difficulty (Tomlin et al., 2013).

### Expected Biosignal Profile

| Signal | Expected Change | Why |
|---|---|---|
| `scr_count` / `scr_max_amp` | ↑ Acute spike at the *decision moment* | The conflict between personal judgment and group opinion triggers phasic sympathetic activation |
| `scl_mean` | Moderate ↑ | Sustained social-threat processing |
| `rmssd` | ↓ During conflict deliberation | Cognitive-emotional regulation engages vagal withdrawal |
| `mean_hr` | Moderate ↑ | Social threat elevates HR |

### Scenario A: "Group Chat Vote" — Factor: Explicit Group Pressure + Visibility of Dissent

**Paradigm basis:** Digital Asch conformity (Stoll et al., 2022; Berns et al., 2005)

**Priming (8s):**
> *"Your friend group is deciding in a chat whether to share a private video of a classmate. Four friends have already voted. You are the last to respond."*

**Decision phase (35s):**
The screen shows a simulated group chat with **4 friend avatars**, each displaying their choice. All 4 unanimously selected **"Share it — it's already going around anyway"** (conforming). The participant must now respond:

- **Option 1 (Key 1):** Agree — share it *(conforming)*
- **Option 2 (Key 2):** Disagree — refuse and ask others to delete it *(dissenting)*

A small label reads: *"Your response is visible to all group members."*

**Stress mechanics:**
- The unanimity of the group is critical — Asch showed that even one ally eliminates conformity pressure. All 4 must agree.
- The participant's choice is framed as *publicly visible* to the group, amplifying the social cost of dissent.
- No timer urgency needed — the social pressure itself is the stressor.

**Consequence (4s):**
- If conformed: *"The video has been shared. The classmate found out — they're upset and asking who agreed to it."*
- If dissented: *"The group has noted your objection. Some members are calling it an overreaction."*

Both outcomes carry negative implications — there's no "safe" choice.

---

### Scenario B: "Unfair Team Blame" — Factor: Accountability Pressure + Conformity by Default

**Paradigm basis:** Taboo trade-off paradigm (Tetlock et al., 2000) — forced attribution of blame violates social fairness norms.

**Priming (8s):**
> *"Your team project received a failing grade. The instructor says one team member must be identified as responsible for the core section that failed. The rest of the team has already submitted their assessment."*

**Decision phase (40s):**
The screen shows the team's submitted assessments — all 4 teammates have identified **you** as the responsible party. You must now respond:

- **Option 1 (Key 1):** Accept responsibility to preserve team harmony
- **Option 2 (Key 2):** Challenge the attribution and name the actual responsible member
- **Option 3 (Key 3):** Refuse to participate in the blame assignment

**Consequence (4s):**
Varies by choice, but all consequences involve some form of social friction — there is no clean exit.

---

## Domain 3: Impulsivity vs. Delayed Gratification (`impulsivity_gratification`)

### Core Mechanism
Measures **self-regulation and executive control** — the tension between the "hot" impulsive system (limbic, favoring immediate reward) and the "cool" deliberative system (prefrontal cortex, favoring long-term gain). Grounded in delay discounting theory (Mazur, 1987; McClure et al., 2004, *Science*) and the somatic marker framework.

> **Key finding:** Higher skin conductance during deliberation is associated with more impulsive (immediate) choices (Lempert et al., 2012, *Frontiers in Neuroscience*). Successful delay is accompanied by higher baseline HRV but *suppressed* HRV during the active waiting period (Segerstrom & Nes, 2007, *Psychological Bulletin*).

### Expected Biosignal Profile

| Signal | Expected Change | Why |
|---|---|---|
| `scl_mean` | ↑ Sustained elevation during waiting | Ongoing sympathetic activation from impulse suppression |
| `scr_count` | Moderate ↑ | Periodic temptation spikes during the wait |
| `rmssd` / `sdnn` | ↓ Sustained suppression during wait | Active self-regulation consumes vagal resources |
| `mean_hr` | Slight ↑ | Approach-avoidance conflict |

### Scenario A: "Instant Loot vs. Multiplier Trap" — Factor: Visible Temptation + Risk of Total Loss

**Paradigm basis:** Real-time waiting task / digital Marshmallow Test (McGuire & Kable, 2012, *PLOS ONE*)

**Priming (8s):**
> *"You've unlocked a reward chest. You can claim it now for a small payout, or wait as the value multiplies. But the chest is unstable — it could collapse at any moment, and you'd lose everything."*

**Decision phase (45s):**
The screen shows a **visually accumulating reward counter** (a progress bar that fills and a number that climbs). Two buttons are permanently available:

- **Key 1: "CLAIM NOW"** — locks in the current value immediately
- **Key 2: "KEEP WAITING"** — continues accumulation but risk increases

The reward counter visibly accelerates (creating increasing temptation), and a subtle **instability indicator** (a slight screen vibration that intensifies over time, ≤3px) signals growing risk of collapse. The actual collapse point is randomized between 20–40 seconds.

**Stress mechanics:**
- The participant must *actively* resist pressing "CLAIM NOW" — this is the impulse suppression that produces sustained sympathetic activation.
- The visible, growing number creates escalating temptation.
- The unpredictable collapse point creates genuine uncertainty about when to stop.

**Consequence (4s):**
- If claimed early: *"Reward secured: [small value]. The chest continued to grow for [X] more seconds after you claimed."* — Induces regret.
- If waited and chest collapsed: *"Chest collapsed. All accumulated value lost."*
- If waited and claimed at high value: *"Reward secured: [high value]. Chest collapsed [X] seconds after your claim."*

---

### Scenario B: "Submit Now vs. Improve More" — Factor: Temporal Discounting under Explicit Tradeoff

**Paradigm basis:** Kirby Monetary Choice Questionnaire (Kirby et al., 1999)

**Priming (8s):**
> *"You've finished a draft of your assignment. You can submit it now for a guaranteed adequate grade, or spend more time refining it — which could significantly improve your grade, but might also make things worse if you second-guess yourself."*

**Decision phase (35s):**
A single, clear binary choice:

- **Key 1:** Submit now — guaranteed **"Adequate — Requirements Met"**
- **Key 2:** Request more time — outcome unknown, could be **"Excellent"** or **"Needs significant revision"**

If the participant chooses to wait (Key 2), a 15-second waiting screen appears with a *"Reviewing additional changes..."* message and a slowly spinning indicator. No information about the outcome is revealed during the wait — this combines delayed gratification with future uncertainty.

**Consequence (4s):**
- If submitted immediately: *"Grade recorded: Adequate — Requirements Met."*
- If waited: *"Extended review complete: [randomized — either 'Excellent' or 'Insufficient — major revision required']."*

---

## Domain 4: Risk-Reward Tradeoff (`risk_reward`)

### Core Mechanism
Activates the **somatic marker system** — the body generates anticipatory physiological signals (especially anticipatory SCR) *before* consciously recognizing a choice as risky. Grounded in the Iowa Gambling Task (Bechara et al., 1994, 1997) and the Balloon Analogue Risk Task (Lejuez et al., 2002).

> **Key finding:** Bechara et al. (1997, *Science*) demonstrated that anticipatory skin conductance responses rise before selecting from "bad" decks — even before participants can consciously articulate which decks are dangerous. This anticipatory GSR is the strongest and most replicable physiological finding in risk decision-making.

### Expected Biosignal Profile

| Signal | Expected Change | Why |
|---|---|---|
| `scr_max_amp` | ↑↑ Strong anticipatory spike *before* risky choice | Somatic marker — the body "warns" before conscious awareness |
| `scr_count` | ↑ Multiple spikes during deliberation | Each evaluation of a risky option triggers anticipatory arousal |
| `scl_mean` | Moderate ↑ | Sustained engagement with uncertain outcomes |
| `rmssd` | ↓ During deliberation | Sympathetic dominance while evaluating risk |
| `mean_hr` | ↑ Acute acceleration on loss feedback | Post-decision cardiac response to negative outcome |

### Scenario A: "Tournament Strategy" — Factor: Ambiguous Probabilities + Potential for Large Loss

**Paradigm basis:** Iowa Gambling Task (Bechara et al., 1994)

**Priming (8s):**
> *"You're competing in an online tournament with limited attempts remaining. Three strategies are available. Historical performance data for each approach is incomplete — some strategies carry hidden risks. Your final ranking will be recorded."*

**Decision phase (40s):**
Three strategy options are displayed, each with partial information:

- **Strategy A (Key 1):** Safe, consistent approach — *"Low variance, reliable 8% average score improvement per round"*
- **Strategy B (Key 2):** Aggressive approach — *"High variance, avg 22% improvement, [2 rounds of data missing]"*
- **Strategy C (Key 3):** Experimental approach — *"Extreme variance, avg 45% improvement, [4 rounds of data missing]"*

The missing data is the critical manipulation — it maps directly to the IGT's hidden loss structure. The participant must decide how much risk to accept *without full information*.

**Stress mechanics:**
- The incomplete data forces a gut-level risk assessment — this is exactly where anticipatory SCR activates.
- Timer bar provides moderate time pressure (not extreme — the deliberation itself is the measurement window).

**Consequence (4s):**
Outcome is probabilistic:
- Strategy A: Always returns moderate gain.
- Strategy B: 60% chance of high gain, 40% chance of moderate loss.
- Strategy C: 40% chance of very high gain, 60% chance of severe loss (*"Critical error: Ranking dropped significantly"*).

---

### Scenario B: "Viral Post Escalation" — Factor: Escalation of Commitment + Sunk Cost

**Paradigm basis:** BART (Lejuez et al., 2002) — each additional "pump" increases both reward and risk.

**Priming (8s):**
> *"You've been posting increasingly bold content online. Each post gets more attention — but the risk of being reported and losing access to your account grows with every step. You can stop now, or push further."*

**Decision phase (40s):**
A **reach meter** shows the participant's accumulated audience. Two options are always visible:

- **Key 1: "STOP POSTING"** — locks in current reach, ends the run
- **Key 2: "POST ANOTHER"** — gains more reach but visibly increases a "Report Risk" gauge

The participant can press Key 2 multiple times (each press adds to the reach but raises the instability gauge). They can press Key 1 at any point to exit. If the report risk gauge hits critical, an "Account Suspended" event triggers and all accumulated reach is lost.

This directly translates the BART's escalating-commitment mechanic into a keyboard-only interface.

**Consequence (4s):**
- If stopped early: *"Following secured. Your account remained active for [X] more potential posts."* — Potential regret.
- If pushed to suspension: *"Account suspended. All accumulated following lost."*
- If pushed far and stopped: *"Maximum reach achieved. You stopped [X] posts before suspension."*

---

## Domain 5: Rule-Boundary Ambiguity (`rule_ambiguity`)

### Core Mechanism
Produces stress through **moral-cognitive conflict** — competing ethical principles where no option is clearly "correct." Engages the dual-process model: emotional/intuitive (vmPFC, amygdala) vs. deliberative/rational (dlPFC) systems. Grounded in Greene et al. (2001, 2004, *Science/Neuron*) and Cushman (2008, *Cognition*).

> **Key finding:** Utilitarian judgments (choosing the "rule-breaking" option for a greater good) produce *larger* anticipatory SCRs than deontological judgments — the stress is specifically in *choosing to violate* a rule, not in the decision difficulty per se (Moretto et al., 2010, *Emotion*).

### Expected Biosignal Profile

| Signal | Expected Change | Why |
|---|---|---|
| `scr_max_amp` | ↑ Peak *during deliberation*, not at outcome | Anticipatory somatic marker for the morally loaded choice |
| `scl_mean` | ↑ Sustained elevation | Cognitive-emotional conflict maintenance |
| `rmssd` | ↓ Suppressed during deliberation | Executive function engagement draws vagal resources |
| Response time | ↑↑ Significantly longer than non-moral decisions | Genuine internal conflict — log this as `response_time_ms` |

### Scenario A: "Portal Access Dilemma" — Factor: Personal Loyalty vs. Institutional Rules

**Paradigm basis:** Personal moral dilemma (Greene et al., 2001) — participant is directly responsible for the consequence.

**Priming (8s):**
> *"Your close friend is locked out of the school's submission portal due to a technical error that won't be fixed for three weeks — past the assignment deadline. You still have their login saved from a previous help session. Using it violates the school's IT policy."*

**Decision phase (45s):**
- **Option 1 (Key 1):** Log in with their credentials to submit for them — helps your friend, violates policy
- **Option 2 (Key 2):** Tell them to file an official complaint — follows policy, friend misses the deadline
- **Option 3 (Key 3):** Find a workaround through the system's guest access feature — technically not their credentials, but exploits a known loophole

**Stress mechanics:**
- No option is "clean." Option 1 is loyal but rule-breaking. Option 2 is rule-following but harms a friend. Option 3 is a gray-area compromise that introduces its own ethical ambiguity.
- Moderate timer (45s) — enough to deliberate but not enough to fully resolve the internal conflict.
- Subtle UI jitter activates at the 30s mark.

**Consequence (4s):**
All consequences are deliberately ambiguous:
- Option 1: *"Submission successful. The system flagged a login from an unrecognized device on your friend's account."*
- Option 2: *"Your friend's appeal was denied. They missed the deadline and lost 20% of their grade."*
- Option 3: *"The guest access loophole has been patched. An investigation into unusual submissions has been opened."*

---

### Scenario B: "Borrowed Template" — Factor: Short-Term Harm vs. Long-Term Benefit

**Paradigm basis:** Taboo trade-off (Tetlock et al., 2000) — assigning utilitarian value to something treated as sacred (academic integrity).

**Priming (8s):**
> *"Your group has been building on an old assignment from a senior student who graduated. You just realized the work was never formally shared — it could be classified as academic plagiarism. Removing it now sets your entire project back by days before the deadline."*

**Decision phase (40s):**
- **Option 1 (Key 1):** Remove the borrowed sections and accept the delay — academically honest, harms the team's timeline
- **Option 2 (Key 2):** Keep it and add an acknowledgement crediting the original work — a compromise, still academically questionable
- **Option 3 (Key 3):** Contact the original student and ask for formal permission — transparent, but their response is unpredictable and time is short

**Consequence (4s):**
No clear resolution — each outcome introduces a new complication.

---

## Domain 6: Future Uncertainty (`future_uncertainty`)

### Core Mechanism
Triggers **anticipatory anxiety** — the sustained distress caused by unpredictable, uncontrollable future outcomes. Grounded in the NPU-Threat paradigm (Grillon et al., 2004, 2008), intolerance of uncertainty theory (Buhr & Dugas, 2002; Carleton, 2016), and the landmark finding that *subjective uncertainty* (not objective probability) is the strongest predictor of stress (de Berker et al., 2016, *Nature Communications*).

> **Key finding:** Stress peaks at ~50% outcome probability (maximum uncertainty), NOT at 100% probability of a bad outcome. The *not knowing* is more stressful than *knowing something bad will happen* (de Berker et al., 2016).

### Expected Biosignal Profile

| Signal | Expected Change | Why |
|---|---|---|
| `scl_mean` | ↑↑ **Primary marker** — sustained tonic elevation | Continuous sympathetic arousal during uncertainty window |
| `scr_count` | Low / normal | Fewer phasic spikes — this is *tonic* not *phasic* arousal |
| `rmssd` / `sdnn` | ↓↓ **Sustained suppression** | Prolonged vagal withdrawal during anticipatory anxiety (Thayer & Lane, 2009) |
| `mean_hr` | Moderate ↑ | Sustained elevation, not acute spikes |

> **NOTE:** This domain's biosignal profile is **distinctly different** from acute stressors (Domains 1, 2, 4). It produces sustained tonic changes, not phasic spikes. `scl_mean` and `rmssd` are the primary discriminating features.

### Scenario A: "Track Selection Crossroads" — Factor: Outcome Uncertainty

**Paradigm basis:** Ambiguous feedback paradigm (Hirsh & Inzlicht, 2008, *Psychological Science*)

**Priming (8s):**
> *"You've been offered two paths forward. Both have significant implications for your future, but the outcomes of each path are influenced by factors you cannot predict or control."*

**Decision phase (45s):**
Two paths are described with deliberately **incomplete information**:

- **Path A (Key 1):** Familiar, established track — *"Predictable progression. Long-term growth potential: [DATA UNAVAILABLE]."*
- **Path B (Key 2):** New, challenging path — *"Unpredictable trajectory. Support structure: [UNDER REVIEW]."*

The missing information (`[DATA UNAVAILABLE]`, `[UNDER REVIEW]`) is the core manipulation — it prevents the participant from making a fully informed decision, triggering intolerance of uncertainty. "Track" is intentionally ambiguous — an academic stream for younger participants, a course or program for older ones.

**Post-decision waiting phase (12s):**
After selecting, a *"Processing your selection..."* screen appears with a slowly spinning indicator. **No information is revealed during this wait.** This 12-second window sustains the uncertainty manipulation through the domain-active span; HRV features are extracted over the full ~65s continuous active epoch (priming + decision + post-wait + feedback), satisfying the ML pipeline's 60s sliding window requirement (see `PULSE_Gamification_Interface_Spec.md` §5).

**Consequence (4s):**
> *"Your selection has been recorded. Outcome details will be provided at the end of the evaluation."*

Deliberately unresolved. The outcome is NEVER revealed during this scenario — this is by design (Grillon's uncertain-threat paradigm keeps the uncertainty window open).

---

### Scenario B: "Ambiguous Feedback Before Finals" — Factor: Evaluative Uncertainty

**Paradigm basis:** Ambiguous feedback + uncertain threat (Grillon et al., 2004; de Berker et al., 2016)

**Priming (8s):**
> *"Before your final assessment, your teacher pulls you aside: 'Your approach throughout this term has been... atypical compared to your peers.' You don't know if this is a compliment or a warning. You must now respond."*

The word **"atypical"** is the critical manipulation — it's ambiguous (could mean better or worse than average) and implies the participant is being compared to others in an undefined way.

**Decision phase (40s):**
A question about the participant's approach to the session so far:

- **Option 1 (Key 1):** "I've been approaching each task based on my instincts and what made sense to me."
- **Option 2 (Key 2):** "I've been carefully considering each step before committing to anything."
- **Option 3 (Key 3):** "I don't think the standard approach was appropriate for what we were being asked to do."

There is no right answer — the stress comes from not knowing *what the evaluator is looking for*.

**Post-decision waiting phase (10s):**
> *"Recalculating assessment parameters..."*

**Consequence (4s):**
> *"Assessment updated. Your response pattern has been flagged for secondary review."*

Again, deliberately ambiguous and unresolved — sustains uncertainty.

---

## Domain 7: Social Evaluation & Authority Response (`social_evaluation`)

### Core Mechanism
The strongest known laboratory stressor. Combines **social-evaluative threat** (being judged on competence/identity) with **uncontrollability** (inability to change the evaluator's perception). Grounded in the TSST (Kirschbaum et al., 1993), the Dickerson & Kemeny (2004) meta-analysis (208 studies), and biofeedback amplification research (Ehlers et al., 1988; Wieser et al., 2010).

> **Key finding:** Tasks combining social-evaluative threat + uncontrollability produce the **largest cortisol responses** and **slowest recovery times** of any laboratory stressor. The TSST produces 2–4× cortisol increases, 15–20 BPM HR elevation, and robust GSR increases. Biofeedback (showing participants their own arousal) *amplifies* the stress response (Wieser et al., 2010).

### Expected Biosignal Profile

| Signal | Expected Change | Why |
|---|---|---|
| `scr_count` / `scr_max_amp` | ↑↑ Strong phasic spikes | Social-evaluative threat triggers acute sympathetic activation |
| `scl_mean` | ↑↑ Elevated tonic level | Sustained social threat processing |
| `rmssd` / `sdnn` / `pnn50` | ↓↓ Strong suppression | Sustained vagal withdrawal — largest HRV depression of all domains |
| `mean_hr` | ↑↑ 10–20 BPM above baseline | Combined social + evaluative + biofeedback demand |

> **NOTE:** This is the ONLY domain where the **MPU6050 Deception Metric** is active. Per-subject calibrated (resting μ_acc + 1.5σ_acc threshold). The biofeedback amplification loop (tremor → bar drops → anxiety increases → more tremor) is the key differentiator from other social domains.

### Scenario A: "Live Panel Presentation Defense" — Factor: Public Performance + Evaluative Observation

**Paradigm basis:** TSST speech task (Kirschbaum et al., 1993) + biofeedback amplification (Wieser et al., 2010)

**Priming (10s):**
> *"You are presenting your project findings to an expert evaluation panel. The panel's assessment will determine your project grade. A biometric sensor is tracking your composure for the panel's review."*

The final sentence primes the participant for the biofeedback mechanic — they know their physical tremor is being evaluated.

**Decision phase (45s):**
The screen shows a simulated panel of **3 evaluator portraits** with neutral, expressionless faces (TSST validated — neutral is more stressful than hostile). A challenging question about defending a controversial position is presented:

> *"The panel asks: Your methodology has been questioned by a reviewer. How do you respond?"*

- **Option 1 (Key 1):** Defend the methodology with technical justification
- **Option 2 (Key 2):** Acknowledge limitations and propose revisions
- **Option 3 (Key 3):** Challenge the reviewer's qualifications

**Stress mechanics (unique to this domain):**
- **MPU6050 Deception Metric ACTIVE:** An "Algorithm Confidence" bar is visible at the bottom of the screen. If the participant's hand tremor (3-axis variance from accelerometer magnitude) exceeds their personal baseline threshold (μ + 1.5σ) for ≥3 consecutive samples (~0.75s) outside the 5s cooldown, the bar visibly drops. A small text label reads: *"Composure Analysis: Active"*
- The evaluator portraits remain **completely neutral** — no nodding, no frowning. This unresponsiveness is the TSST's uncontrollability mechanism.
- Subtle text jitter on the question text (≤3px, ≤2Hz) represents the panel's "impatience."
- Diegetic tension drone activates in the final third.

**Consequence (4s):**
> *"The panel has recorded your response. Composure score: [derived from MPU6050 data — low if tremor detected]. Final evaluation pending."*

---

### Scenario B: "Public Critique" — Factor: Authority Evaluation + Unjust Criticism

**Paradigm basis:** Evaluative observation + negative feedback (Geen, 1991; MAST social-evaluative component, Smeets et al., 2012)

**Priming (10s):**
> *"Your teacher or coach has singled you out in front of the group for a critical review — one you didn't request. A biometric sensor is tracking your composure for review."*

Again, the final sentence primes the biofeedback mechanic.

**Decision phase (46s):** *(Note: Calibrated to 46s so that 10s priming + 46s decision + 4s consequence = 60s minimum active epoch).*
The screen displays a harsh, borderline-unfair critique:

> *"Your teacher states: 'Your recent performance has been below the standard expected in this program. I need to understand whether this is a capability issue or a commitment issue. Explain yourself.'"*

Response options:
- **Option 1 (Key 1):** Accept the criticism and commit to improving
- **Option 2 (Key 2):** Provide context — external factors affected your performance
- **Option 3 (Key 3):** Push back — the criticism is too vague and not specific enough to act on

**Stress mechanics:**
- **MPU6050 Deception Metric ACTIVE** — same as Scenario A.
- The framing as a *teacher/coach-initiated* review (not self-requested) creates uncontrollability.
- The phrasing "capability issue or commitment issue" is a deliberate **false dichotomy** that forces the participant into a defensive position — both options are unflattering.

**Consequence (4s):**
> *"Your response has been logged. Updated assessment: [deliberately ambiguous — 'Under continued review']. Composure score: [MPU6050-derived]."*

---

## Cross-Domain Biosignal Prediction Matrix

| Domain | Primary GSR Target | Primary HRV Target | Dominant Feature Expected |
|---|---|---|---|
| `academic_pressure` | ↑ Phasic (failure spikes) + Tonic | ↓ Sustained suppression | `scr_count`, `rmssd` |
| `peer_influence` | ↑ Acute spike at decision moment | ↓ During conflict deliberation | `scr_max_amp` |
| `impulsivity_gratification` | Moderate ↑ during wait | ↓↓ Sustained during impulse resistance | `scl_mean`, `rmssd` |
| `risk_reward` | ↑↑ **Anticipatory** SCR before risky choice | ↓ During deliberation | `scr_max_amp` (anticipatory) |
| `rule_ambiguity` | ↑ During deliberation (not outcome) | ↓ Executive function engagement | `scr_max_amp`, response time |
| `future_uncertainty` | Low phasic, **↑↑ Tonic** SCL elevation | ↓↓ Sustained suppression (primary marker) | `scl_mean`, `rmssd` |
| `social_evaluation` | ↑↑ Both phasic + tonic (strongest overall) | ↓↓ Strongest suppression of all domains | All features elevated |

---

## Key References

| Citation | Relevance |
|---|---|
| Asch, S. E. (1951) | Conformity paradigm — Domain 2 |
| Bechara, A. et al. (1994, 1997) *Cognition*, *Science* | Iowa Gambling Task, anticipatory SCR — Domain 4 |
| Berns, G. S. et al. (2005) *Biological Psychiatry* | Amygdala activation during social dissent — Domain 2 |
| Buhr, K. & Dugas, M. J. (2002) *BRAT* | Intolerance of Uncertainty Scale — Domain 6 |
| Carleton, R. N. (2016) *J. Anxiety Disorders* | IU as transdiagnostic risk factor — Domain 6 |
| Cushman, F. (2008) *Cognition* | Rule-based vs outcome-based moral reasoning — Domain 5 |
| de Berker, A. O. et al. (2016) *Nature Comms* | Uncertainty (not probability) predicts stress — Domain 6 |
| Dedovic, K. et al. (2005) *J. Psychiatry Neurosci* | MIST protocol — Domain 1 |
| Dickerson, S. S. & Kemeny, M. E. (2004) *Psych Bull* | SET + uncontrollability meta-analysis — Domain 7 |
| Ehlers, A. et al. (1988) *BRAT* | False physiological feedback amplifies anxiety — Domain 7 |
| Greene, J. D. et al. (2001, 2004) *Science*, *Neuron* | Moral dilemma dual-process model — Domain 5 |
| Grillon, C. et al. (2004, 2008) *Biol Psychiatry* | NPU uncertain threat paradigm — Domain 6 |
| Hirsh, J. B. & Inzlicht, M. (2008) *Psych Science* | Ambiguous feedback paradigm — Domain 6 |
| Kirby, K. N. et al. (1999) *J. Exp. Psych: General* | Monetary Choice Questionnaire — Domain 3 |
| Kirschbaum, C. et al. (1993) *Neuropsychobiology* | TSST — Domains 1, 7 |
| Lejuez, C. W. et al. (2002) *J. Exp. Clin. Psychopharm* | BART — Domain 4 |
| Lempert, K. M. et al. (2012) *Frontiers Neurosci* | SCR and impulsive choice — Domain 3 |
| McClure, S. M. et al. (2004) *Science* | Dual-system temporal discounting — Domain 3 |
| McGuire, J. T. & Kable, J. W. (2012) *PLOS ONE* | Real-time waiting tasks — Domain 3 |
| Moretto, G. et al. (2010) *Emotion* | Anticipatory SCR in moral dilemmas — Domain 5 |
| Segerstrom, S. C. & Nes, L. S. (2007) *Psych Bull* | HRV reflects self-regulatory effort — Domain 3 |
| Tetlock, P. E. et al. (2000) *JPSP* | Taboo trade-offs — Domains 2, 5 |
| Thayer, J. F. & Lane, R. D. (2009) *Neurosci Biobehav Rev* | Vagal tone and anticipatory anxiety — Domain 6 |
| Wieser, M. J. et al. (2010) *Biol Psychology* | Biofeedback amplifies social stress — Domain 7 |
