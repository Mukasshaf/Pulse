"""
run_session.py — Per-subject session orchestrator.

One command per subject, start to finish:
    1. Pre-session sensor quality gate (pre_session_check.py)
    2. Serial capture + game engine launched simultaneously (decoupled, no IPC)
    3. Wait for game engine to exit cleanly
    4. Stop serial capture (SIGINT)
    5. Align sensor CSV with game event log (align_signals.py)
    6. Extract per-subject domain features (per_subject_features.py)
    7. Generate individual radar chart and summary markdown report
    8. Print one-line completion summary

Usage:
    uv run python run_session.py --subject HW05
    uv run python run_session.py --subject HW05 --port COM5
    uv run python run_session.py --subject HW05 --no-check          # skip pre-session gate
    uv run python run_session.py --subject HW05 --fast-baseline     # 10s baseline (testing only)
    uv run python run_session.py --subject HW05 --no-fullscreen     # windowed game

Output layout:
    outputs/raw/{subject}_raw_{ts}.csv
    outputs/aligned/{subject}_aligned.csv
    outputs/features/domain/{subject}_domain_features.csv
    outputs/reports/{subject}/{subject}_radar.png
    outputs/reports/{subject}/{subject}_summary.md
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import datetime
from pathlib import Path

import numpy as np

# ── Path setup ────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT / "src" / "pipeline"))
sys.path.insert(0, str(_ROOT / "src"))

from per_subject_features import (
    extract_domain_features,
    save_domain_features_csv,
    plot_subject_radar,
    DOMAIN_IDS,
    PRIMARY_FEATURE,
)

# ── Configuration ─────────────────────────────────────────────────────────────
DEFAULT_PORT = "COM9"
DEFAULT_BAUD = 115200
SUBJECT_COLORS = [
    "#d62728", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


# ── Subprocess helpers ────────────────────────────────────────────────────────

def _uv_run(*args: str) -> list[str]:
    """Build a command list using the current Python executable.
    
    Using sys.executable directly avoids the 'uv' middleman, which
    prevents orphaned child processes on Windows when we call proc.terminate().
    """
    return [sys.executable] + list(args)


def _stop_process(proc: subprocess.Popen, name: str, timeout: float = 8.0) -> None:
    """Terminate a subprocess and wait for it to exit.

    Uses proc.terminate() on all platforms (TerminateProcess on Windows,
    SIGTERM on POSIX).  CTRL_C_EVENT was used previously but silently fails
    on Windows unless the process was spawned with CREATE_NEW_PROCESS_GROUP.
    proc.terminate() is unconditional and always works.
    """
    if proc.poll() is not None:
        return   # already exited

    print(f"  Stopping {name} ...", end="", flush=True)
    try:
        proc.terminate()
    except Exception:
        pass  # process may have already exited between poll() and terminate()

    try:
        proc.wait(timeout=timeout)
        print(" done.")
    except subprocess.TimeoutExpired:
        print(" timed out — force killing.")
        try:
            proc.kill()
            proc.wait(timeout=3.0)
        except (subprocess.TimeoutExpired, KeyboardInterrupt, OSError):
            pass   # nothing more we can do; data is already flushed to disk
    except (KeyboardInterrupt, OSError):
        # If the operator hits Ctrl+C during cleanup, absorb it — data is safe
        pass


# ── Step implementations ──────────────────────────────────────────────────────

def step_pre_check(subject: str, port: str, baud: int) -> bool:
    """Run pre_session_check.py as a subprocess. Returns True if passed/overridden."""
    print("\n── Step 1: Pre-Session Sensor Check ──────────────────────")
    cmd = _uv_run(
        str(_ROOT / "pre_session_check.py"),
        "--subject", subject,
        "--port", port,
        "--baud", str(baud),
    )
    result = subprocess.run(cmd, cwd=str(_ROOT))
    return result.returncode == 0


def step_launch_capture(subject: str, port: str, baud: int, ts: str) -> tuple[subprocess.Popen, Path]:
    """Launch serial_reader.py in the background. Returns (proc, raw_csv_path)."""
    raw_dir  = _ROOT / "outputs" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # serial_reader writes its own timestamped filename; we match it by ts
    raw_csv = raw_dir / f"{subject}_raw_{ts}.csv"

    cmd = _uv_run(
        "-m", "src.hardware.serial_reader",
        "--port", port,
        "--baud", str(baud),
        "--out-dir", str(raw_dir),
    )
    proc = subprocess.Popen(
        cmd,
        cwd=str(_ROOT),
        # Keep stdout/stderr connected so the operator can see live row counts
    )
    print(f"  Serial capture started (PID {proc.pid})")
    print(f"  Writing to: outputs/raw/  (timestamped by serial_reader)")
    time.sleep(1.0)   # let the port open before the game starts
    return proc, raw_csv


def step_launch_game(subject: str, fast_baseline: bool, fullscreen: bool) -> subprocess.Popen:
    """Launch the game engine. Returns process handle to wait on."""
    cmd = _uv_run(
        "-m", "src.game.main",
        "--subject", subject,
    )
    if fast_baseline:
        cmd.append("--fast-baseline")
    if not fullscreen:
        cmd.append("--no-fullscreen")

    proc = subprocess.Popen(cmd, cwd=str(_ROOT))
    print(f"  Game engine started  (PID {proc.pid})")
    return proc


def step_align(subject: str, sensor_csv: Path, events_dir: Path = None) -> Path:
    """Run align_signals.py. Returns path to aligned CSV."""
    print("\n── Step 3: Aligning Sensor + Game Logs ──────────────────")
    aligned_dir = _ROOT / "outputs" / "aligned"
    aligned_csv = aligned_dir / f"{subject}_aligned.csv"

    # Find raw sensor CSV — serial_reader uses its own timestamp, not ours
    if not sensor_csv.exists():
        raw_dir = _ROOT / "outputs" / "raw"
        candidates = sorted(raw_dir.glob("recorded_*.csv"), key=lambda p: p.stat().st_mtime)
        if candidates:
            sensor_csv = candidates[-1]
            print(f"  Using most recent raw CSV: {sensor_csv.name}")
        else:
            raise FileNotFoundError(f"No raw sensor CSV found in {raw_dir}")

    # Find events CSV — game engine writes to outputs/game_logs/{subject}_{ts}/events.csv
    game_logs_dir = _ROOT / "outputs" / "game_logs"
    subject_dirs = sorted(
        [d for d in game_logs_dir.glob(f"{subject}_*") if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    events_csv = None
    for d in subject_dirs:
        candidate = d / "events.csv"
        if candidate.exists():
            events_csv = candidate
            print(f"  Using events CSV: {events_csv.relative_to(_ROOT)}")
            break

    if events_csv is None:
        raise FileNotFoundError(
            f"No events.csv found for subject '{subject}' under {game_logs_dir}.\n"
            f"       Expected pattern: outputs/game_logs/{subject}_{{timestamp}}/events.csv"
        )

    cmd = _uv_run(
        str(_ROOT / "src" / "align_signals.py"),
        "--sensor-csv", str(sensor_csv),
        "--events-csv",  str(events_csv),
        "--output-csv",  str(aligned_csv),
    )
    result = subprocess.run(cmd, cwd=str(_ROOT))
    if result.returncode != 0:
        raise RuntimeError("align_signals.py failed — see output above.")

    print(f"  Aligned CSV: {aligned_csv}")
    return aligned_csv


def step_extract_features(subject: str, aligned_csv: Path) -> dict:
    """Run per-subject domain feature extraction. Returns results dict."""
    print("\n── Step 4: Domain Feature Extraction ────────────────────")
    results = extract_domain_features(subject, aligned_csv)

    out_csv = _ROOT / "outputs" / "features" / "domain" / f"{subject}_domain_features.csv"
    save_domain_features_csv(results, subject, out_csv)
    return results


def step_generate_report(subject: str, results: dict) -> Path:
    """Generate per-subject radar chart + markdown summary. Returns report dir."""
    print("\n── Step 5: Generating Report ─────────────────────────────")
    report_dir = _ROOT / "outputs" / "reports" / subject
    report_dir.mkdir(parents=True, exist_ok=True)

    # Radar chart
    radar_out = report_dir / f"{subject}_radar.png"
    if results:
        color_idx = 0   # first color; group_report will assign distinct colors
        plot_subject_radar(subject, results, radar_out, color=SUBJECT_COLORS[color_idx])
    else:
        print(f"  WARNING: No results to plot — radar chart skipped.")

    # Markdown summary
    summary_path = report_dir / f"{subject}_summary.md"
    _write_summary_md(subject, results, summary_path)
    print(f"  Summary MD: {summary_path}")

    return report_dir


def _write_summary_md(subject: str, results: dict, out_path: Path) -> None:
    """Write a human-readable per-domain markdown summary."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# {subject} — Session Domain Summary",
        f"*Generated: {ts}*",
        "",
        "## Domain Results",
        "",
        "| Domain | n windows | Normalized | Art. fraction | scl_mean (z) |",
        "|---|---|---|---|---|",
    ]

    valid_count = 0
    for domain in DOMAIN_IDS:
        res = results.get(domain)
        if res is None:
            art = results.get(f"_art_{domain}", "—")
            lines.append(f"| {domain} | 0 | — | — | *excluded* |")
            continue

        n           = res["n"]
        normalized  = "yes (z-score)" if res.get("normalized", True) else "**NO (raw units)**"
        art_frac    = res.get("art_frac_mean", float("nan"))
        art_str     = f"{art_frac:.1%}" if not (isinstance(art_frac, float) and art_frac != art_frac) else "—"
        scl_val     = res["mean"].get(PRIMARY_FEATURE, float("nan"))
        scl_str     = f"{scl_val:.3f}" if not (isinstance(scl_val, float) and scl_val != scl_val) else "NaN"

        lines.append(f"| {domain} | {n} | {normalized} | {art_str} | {scl_str} |")
        valid_count += 1

    lines += [
        "",
        f"**Valid domains: {valid_count}/7**",
        "",
        "## Normalization Notes",
        "",
    ]

    # Check if any subject fell back to raw units
    raw_subjects = [
        d for d, res in results.items()
        if res is not None and not res.get("normalized", True)
    ]
    if raw_subjects:
        lines += [
            f"> ⚠️  Subject {subject} had insufficient baseline windows (< 4). "
            "Z-score normalization was skipped. Values are in raw ADC units and "
            "**cannot be directly compared** to normalized subjects in the group report.",
            "",
        ]
    else:
        lines.append("> ✓  Z-score normalization applied successfully against resting baseline.")
        lines.append("")

    lines += [
        "## Open Items",
        "",
        "- GSR polarity confirmation: confirm that higher `scl_mean` z-score corresponds to "
        "higher sympathetic arousal for this specific Grove GSR wiring before reporting "
        "directional claims (e.g., 'Domain X caused most stress').",
        "",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ── Main orchestrator ─────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pulse per-subject session orchestrator — one command, start to finish",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--subject",       required=True,  help="Subject ID (e.g. HW05)")
    parser.add_argument("--port",          default=DEFAULT_PORT, help="Serial port")
    parser.add_argument("--baud",          default=DEFAULT_BAUD, type=int)
    parser.add_argument("--no-check",      action="store_true",
                        help="Skip pre-session sensor quality check")
    parser.add_argument("--fast-baseline", action="store_true",
                        help="Reduce baseline calibration to 10s (testing only)")
    parser.add_argument("--no-fullscreen", action="store_true",
                        help="Launch game in windowed mode")
    args = parser.parse_args()

    subject  = args.subject
    ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n{'='*60}")
    print(f"  Pulse Session Orchestrator — Subject: {subject}")
    print(f"  {ts}")
    print(f"{'='*60}")

    # Step 1: Pre-session check
    if not args.no_check:
        passed = step_pre_check(subject, args.port, args.baud)
        if not passed:
            print("\nPre-session check failed and was not overridden. Session aborted.")
            sys.exit(1)
    else:
        print("\n── Step 1: Pre-Session Sensor Check  [SKIPPED via --no-check] ──")

    # Step 2: Launch capture + game simultaneously
    print("\n── Step 2: Session Recording ─────────────────────────────")
    sensor_proc, raw_csv = step_launch_capture(subject, args.port, args.baud, ts)
    game_proc  = step_launch_game(subject, args.fast_baseline, not args.no_fullscreen)

    print(f"\n  Session in progress. Waiting for game engine to complete...")
    print(f"  (Do not close this terminal — it will proceed automatically when the game exits.)\n")

    try:
        game_proc.wait()   # blocks until game engine exits cleanly
    except KeyboardInterrupt:
        print("\n  Session interrupted by operator. Stopping both processes...")
        _stop_process(game_proc, "game engine")
    finally:
        _stop_process(sensor_proc, "serial capture")

    print(f"\n  Game engine exited. Proceeding to post-processing...")

    # Step 3: Align — events CSV is auto-discovered from outputs/game_logs/{subject}_*/
    try:
        aligned_csv = step_align(subject, raw_csv)
    except FileNotFoundError as exc:
        print(f"\nERROR: {exc}")
        print("       Session data was captured but post-processing could not complete.")
        print(f"       Raw sensor data is in outputs/raw/  — align manually when ready.")
        sys.exit(1)

    # Step 4: Feature extraction
    try:
        results = step_extract_features(subject, aligned_csv)
    except Exception as exc:
        print(f"\nERROR during feature extraction: {exc}")
        sys.exit(1)

    # Step 5: Report
    report_dir = step_generate_report(subject, results)

    # Final summary line
    valid_count = sum(1 for v in results.values() if v is not None) if results else 0
    print(f"\n{'='*60}")
    print(f"  ✓  Session complete.")
    print(f"     Subject      : {subject}")
    print(f"     Valid domains: {valid_count}/7")
    print(f"     Report       : {report_dir}/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
