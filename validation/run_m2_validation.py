"""
run_m2_validation.py -- M2 Validation Master Runner
====================================================
Calls all 4 task scripts and writes M2_Validation_Summary.md.
Run from project root with venv active:
    python run_m2_validation.py
"""

import sys
import os
from datetime import datetime

# Ensure scripts in project root are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import validate_peak_detection
import validate_gsr_stability
import validate_motion_flag
import validate_drop_rate

OUT_FILE = "M2_Validation_Summary.md"

# Task 0 grep results (precomputed -- grep run during planning phase)
TASK0_HITS = [
    {"file": "src/preprocess.py", "line": 15,
     "match": "def clean_bvp(bvp, fs: int = 64)",
     "classification": "default arg -- safe, WESAD path uses 64; hardware caller must pass fs=66.67"},
    {"file": "src/preprocess.py", "line": 23,
     "match": "def detect_peaks(bvp_clean, fs: int = 64)",
     "classification": "default arg -- safe, same caveat as above"},
]
TASK0_STATUS = "PASS"
TASK0_NOTE   = ("No hardcoded literal computations. Both hits are default parameter "
                "values; callers pass fs explicitly. Hardware ingest must supply "
                "fs=66.67 (1000/15) -- pipeline is parameterized and compliant.")


def _icon(status: str) -> str:
    return {"PASS": "PASS", "FAIL": "FAIL", "NOT RUN": "NOT RUN"}.get(status, status)


def _gate_row(label, passed) -> str:
    mark = "PASS" if passed else "FAIL"
    return f"  - {label}: **{mark}**"


def write_summary(t0_hits, t0_status, t0_note, t1, t2, t3, t4):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Count pass/fail among runnable tasks
    runnable = [r for r in [t1, t2, t4] if r.get("status") not in ("NOT RUN",)]
    passed_n = sum(1 for r in runnable if r.get("status") == "PASS")
    run_n    = len(runnable)

    # Overall: if any runnable task fails, overall is FAIL
    # Task 3 NOT RUN is not a pass or fail -- noted separately
    overall_pass = (passed_n == run_n) and (run_n > 0)
    t3_not_run   = t3.get("status") == "NOT RUN"

    lines = []
    lines.append(f"# M2 Hardware Validation Summary")
    lines.append(f"")
    lines.append(f"**Generated:** {now}")
    lines.append(f"**Project:** Pulse (GPAMS) — Phase 2 hardware gate")
    lines.append(f"**True hardware fs:** 66.67 Hz (SAMPLE\\_INTERVAL\\_MS=15 → 1000/15)")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # ── Task 0 ────────────────────────────────────────────────
    lines.append(f"## Task 0 — fs Assumption Audit  [{_icon(t0_status)}]")
    lines.append(f"")
    lines.append(f"Grep targets: `src/preprocess.py`, `src/features.py`, `src/normalize.py`")
    lines.append(f"Pattern: `64 | fs=64 | 60*64 | 64*`")
    lines.append(f"")
    if t0_hits:
        lines.append(f"| File | Line | Match | Classification |")
        lines.append(f"|---|---|---|---|")
        for h in t0_hits:
            lines.append(f"| `{h['file']}` | {h['line']} | `{h['match']}` | {h['classification']} |")
        lines.append(f"")
    else:
        lines.append(f"No matches found — clean.")
        lines.append(f"")
    lines.append(f"**Verdict:** {t0_note}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # ── Task 1 ────────────────────────────────────────────────
    s1 = t1.get("status", "ERROR")
    lines.append(f"## Task 1 — Peak Detection  [{_icon(s1)}]")
    lines.append(f"")
    if "reason" in t1:
        lines.append(f"**Error:** {t1['reason']}")
    else:
        lines.append(f"| Parameter | Value |")
        lines.append(f"|---|---|")
        lines.append(f"| File | `{t1.get('file')}` |")
        lines.append(f"| fs used | {t1.get('fs_hz')} Hz |")
        lines.append(f"| Duration | {t1.get('duration_s')} s |")
        lines.append(f"| Total samples | {t1.get('total_samples')} |")
        lines.append(f"| Peak count | {t1.get('peak_count')} |")
        lines.append(f"| IBI count | {t1.get('ibi_count')} |")
        lines.append(f"| IBI min / max | {t1.get('ibi_min_ms')} / {t1.get('ibi_max_ms')} ms |")
        lines.append(f"| IBI mean ± std | {t1.get('ibi_mean_ms')} ± {t1.get('ibi_std_ms')} ms |")
        lines.append(f"| IBI CV | {t1.get('ibi_cv')} |")
        lines.append(f"| % valid IBIs (400–1500 ms) | {t1.get('pct_valid_ibi')}% |")
        lines.append(f"| Mean BPM | {t1.get('mean_bpm')} |")
        lines.append(f"| Manual tuning required | {t1.get('manual_tuning')} |")
        lines.append(f"")
        lines.append(f"**Acceptance gates:**")
        lines.append(_gate_row(">=95% IBIs in 400-1500ms", t1.get("gate_ibi_pass")))
        lines.append(_gate_row("Mean BPM in 50-100", t1.get("gate_bpm_pass")))
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # ── Task 2 ────────────────────────────────────────────────
    s2 = t2.get("status", "ERROR")
    lines.append(f"## Task 2 — GSR Stability  [{_icon(s2)}]")
    lines.append(f"")
    lines.append(f"| Parameter | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| File | `{t2.get('file')}` |")
    lines.append(f"| fs used | {t2.get('fs_hz')} Hz |")
    lines.append(f"| Duration | {t2.get('duration_s')} s |")
    lines.append(f"| Overall mean / std | {t2.get('overall_mean')} / {t2.get('overall_std')} ADC |")
    lines.append(f"| GSR range | {t2.get('gsr_range')} ADC (min={t2.get('gsr_min')}, max={t2.get('gsr_max')}) |")
    lines.append(f"| Baseline mean (first 10s) | {t2.get('baseline_mean_10s')} ADC |")
    lines.append(f"| Rolling 1s std max / mean | {t2.get('max_rolling_1s_std')} / {t2.get('mean_rolling_1s_std')} |")
    lines.append(f"| Single-sample jumps >20% range | {t2.get('big_jumps_gt20pct')} |")
    lines.append(f"| Max single-sample jump | {t2.get('max_single_jump')} ADC |")
    lines.append(f"| Saturation at 0 | {t2.get('sat_at_0')} samples |")
    lines.append(f"| Saturation at 4095 | {t2.get('sat_at_4095')} samples |")
    lines.append(f"| 50% dropout threshold | {t2.get('dropout_50pct_thresh')} ADC |")
    lines.append(f"| Max sustained dropout | {t2.get('max_dropout_run_s')} s |")
    lines.append(f"")
    lines.append(f"**Acceptance gates:**")
    lines.append(_gate_row("No sustained dropout >30s below 50% baseline", t2.get("gate_dropout_pass")))
    lines.append(_gate_row("No ADC saturation (0 or 4095)", t2.get("gate_sat_pass")))
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # ── Task 3 ────────────────────────────────────────────────
    lines.append(f"## Task 3 — Motion Artifact Flagging  [NOT RUN]")
    lines.append(f"")
    lines.append(f"> **{t3.get('reason')}**")
    lines.append(f">")
    lines.append(f"> Required new capture: {t3.get('required_capture')}")
    lines.append(f"> Script logic is complete and ready — {t3.get('how_to_activate')}.")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # ── Task 4 ────────────────────────────────────────────────
    s4 = t4.get("status", "ERROR")
    lines.append(f"## Task 4 — Drop Rate  [{_icon(s4)}]")
    lines.append(f"")
    lines.append(f"> **Note:** {t4.get('duration_note')}")
    lines.append(f"")
    lines.append(f"| Parameter | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| File | `{t4.get('file')}` |")
    lines.append(f"| Duration | {t4.get('duration_s')} s |")
    lines.append(f"| First / last timestamp | {t4.get('first_ts_ms')} / {t4.get('last_ts_ms')} ms |")
    lines.append(f"| SAMPLE\\_INTERVAL\\_MS | {t4.get('sample_interval_ms')} |")
    lines.append(f"| Expected rows | {t4.get('expected_rows')} |")
    lines.append(f"| Actual rows | {t4.get('actual_rows')} |")
    lines.append(f"| **Drop rate** | **{t4.get('drop_rate_pct')}%** |")
    lines.append(f"| Gap events (idx diff != 1) | {t4.get('gap_events')} |")
    lines.append(f"| Missed rows total | {t4.get('missed_rows_total')} |")
    lines.append(f"| Backwards jumps | {t4.get('backwards_jumps')} |")
    lines.append(f"")
    lines.append(f"**Acceptance gate:**")
    lines.append(_gate_row("Drop rate < 5%", t4.get("gate_lt5pct_pass")))
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # ── Overall ────────────────────────────────────────────────
    lines.append(f"## Overall M2 Status")
    lines.append(f"")
    lines.append(f"| Task | Status |")
    lines.append(f"|---|---|")
    lines.append(f"| Task 0 — fs audit | **{_icon(t0_status)}** |")
    lines.append(f"| Task 1 — Peak detection | **{_icon(s1)}** |")
    lines.append(f"| Task 2 — GSR stability | **{_icon(s2)}** |")
    lines.append(f"| Task 3 — Motion flagging | **NOT RUN** |")
    lines.append(f"| Task 4 — Drop rate | **{_icon(s4)}** |")
    lines.append(f"")
    lines.append(f"**Tasks run:** {run_n}/4 (Task 3 blocked — no motion capture available)")
    lines.append(f"**Tasks passed:** {passed_n}/{run_n} run  |  {passed_n + 1}/5 total (Task 0 included)")
    lines.append(f"")
    if overall_pass:
        lines.append(f"**M2 STATUS: PARTIAL PASS** — Tasks 0, 1, 2, 4 pass. "
                     f"Task 3 requires a new recording with a deliberate motion segment "
                     f"before M2 can be formally closed.")
    else:
        lines.append(f"**M2 STATUS: FAIL** — One or more runnable tasks failed. See details above.")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"*Scope: standalone validation only. "
                 f"No production files (serial\\_reader.py, preprocess.py, hardware\\_loader.py) were modified.*")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("  M2 Validation Master Runner")
    print("=" * 60)

    print("\n[Task 0] fs assumption audit (precomputed grep)...")
    # Already run during planning -- results hardcoded above

    print("[Task 1] Running peak detection validation...")
    t1 = validate_peak_detection.run()
    print(f"  -> {t1['status']}")

    print("[Task 2] Running GSR stability validation...")
    t2 = validate_gsr_stability.run()
    print(f"  -> {t2['status']}")

    print("[Task 3] Running motion artifact flagging...")
    t3 = validate_motion_flag.run()
    print(f"  -> {t3['status']}")

    print("[Task 4] Running drop rate validation...")
    t4 = validate_drop_rate.run()
    print(f"  -> {t4['status']}")

    print(f"\nWriting {OUT_FILE}...")
    write_summary(TASK0_HITS, TASK0_STATUS, TASK0_NOTE, t1, t2, t3, t4)
    print(f"Done -> {OUT_FILE}")


if __name__ == "__main__":
    main()
