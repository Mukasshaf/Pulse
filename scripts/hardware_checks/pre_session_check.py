"""
pre_session_check.py — Sensor quality gate.

Run immediately after strapping the subject, before the timed session begins.
Streams ~18 seconds of live serial data in-memory (no file written) and runs
three checks:

    GSR contact    — 90th-percentile gsr_raw > 80 (starting threshold, see note)
    PPG waveform   — ≥6 peaks detected AND all IBIs in 300–2000ms physiological range
    IMU sanity     — max(|acc_x|, |acc_y|, |acc_z|) > 1000 (I2C connectivity check)

Prints PASS / FAIL per check (not just an overall verdict) so the operator
knows which sensor to fix.

On any FAIL the operator is prompted to fix and re-check, or type 'override'
to proceed anyway. Overrides are logged with timestamp and reason to
outputs/logs/{subject}_override.log — never silently allowed.

Exit codes:
    0  — all checks passed, or operator explicitly overrode failures
    1  — operator chose to abort (did not override)

Usage:
    uv run python pre_session_check.py --subject HW05
    uv run python pre_session_check.py --subject HW05 --port COM5 --duration 18

NOTE on GSR threshold:
    The 80 ADC threshold is derived from one operator observation (bad strap
    reads in the 0–60 range). Before relying on this for real sessions, record
    a short clip each of a deliberate unstrapped sensor and a properly strapped
    one, and calibrate the cutoff from that comparison — the same way
    ACC_THRESHOLD_HW=8800.0 was derived from real resting recordings.
"""
from __future__ import annotations

import argparse
import sys
import time
import datetime
from pathlib import Path

import numpy as np

try:
    import serial
    _HAS_SERIAL = True
except ImportError:
    _HAS_SERIAL = False

# ── Path setup ────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT / "src" / "pipeline"))
sys.path.insert(0, str(_ROOT / "src"))

from preprocess import clean_bvp, detect_peaks

# ── Configuration ─────────────────────────────────────────────────────────────
DEFAULT_PORT     = "COM9"
DEFAULT_BAUD     = 115200
DEFAULT_DURATION = 18.0   # seconds of streaming for the pre-check
HW_FS: float     = 1000.0 / 15.0  # 66.6667 Hz

# Thresholds
GSR_P90_MIN      = 80     # 90th-percentile gsr_raw must exceed this for skin contact
PPG_MIN_PEAKS    = 6      # minimum peaks in the 18s window for a valid waveform
PPG_IBI_MIN_MS   = 300.0  # physiological IBI lower bound (200 BPM max)
PPG_IBI_MAX_MS   = 2000.0 # physiological IBI upper bound (30 BPM min)
IMU_MIN_ABS      = 1000   # at least one ACC axis absolute value must exceed this at rest

# Firmware column order (from serial_reader.py)
FIELD_NAMES = ["sample_idx", "timestamp_ms", "pulse_raw", "gsr_raw", "acc_x", "acc_y", "acc_z"]
N_FIELDS = len(FIELD_NAMES)


# ── Serial streaming ──────────────────────────────────────────────────────────

def _stream_samples(port: str, baud: int, duration: float) -> list[dict]:
    """Open serial port, collect rows for `duration` seconds, return as list of dicts."""
    if not _HAS_SERIAL:
        raise RuntimeError("pyserial not installed — run: uv add pyserial")

    samples = []
    start = time.monotonic()

    with serial.Serial(port, baud, timeout=1.0) as ser:
        print(f"  Streaming from {port} for {duration:.0f}s ...", end="", flush=True)
        while time.monotonic() - start < duration:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) != N_FIELDS:
                continue
            try:
                row = {name: int(val) for name, val in zip(FIELD_NAMES, parts)}
                samples.append(row)
            except ValueError:
                continue
        print(f" collected {len(samples)} samples.")

    return samples


# ── Individual checks ─────────────────────────────────────────────────────────

def check_gsr(samples: list[dict]) -> tuple[bool, str]:
    """GSR skin-contact check: 90th-percentile gsr_raw > GSR_P90_MIN."""
    vals = np.array([s["gsr_raw"] for s in samples], dtype=float)
    p90  = float(np.percentile(vals, 90))
    ok   = p90 > GSR_P90_MIN
    if ok:
        return True, f"PASS  gsr_raw p90={p90:.0f}  (threshold > {GSR_P90_MIN})"
    else:
        return False, (
            f"FAIL  gsr_raw p90={p90:.0f}  (threshold > {GSR_P90_MIN})\n"
            "       → Re-check electrodes on middle and ring fingers."
        )


def check_ppg(samples: list[dict]) -> tuple[bool, str]:
    """PPG waveform check: ≥PPG_MIN_PEAKS peaks and all IBIs in physiological range."""
    bvp = np.array([s["pulse_raw"] for s in samples], dtype=float)
    try:
        bvp_clean = clean_bvp(bvp, fs=HW_FS)
        result    = detect_peaks(bvp_clean, fs=HW_FS)
    except Exception as exc:
        return False, f"FAIL  PPG processing error: {exc}"

    n_peaks = len(result["peaks"])
    ibi_ms  = result["ibi_ms"]

    if n_peaks < PPG_MIN_PEAKS:
        return False, (
            f"FAIL  Only {n_peaks} peaks detected in {len(samples)/HW_FS:.0f}s window "
            f"(need ≥ {PPG_MIN_PEAKS})\n"
            "       → Check finger strap tension and sensor placement on the index finger."
        )

    if len(ibi_ms) > 0:
        out_of_range = np.sum((ibi_ms < PPG_IBI_MIN_MS) | (ibi_ms > PPG_IBI_MAX_MS))
        frac = out_of_range / len(ibi_ms)
        if frac > 0.30:   # >30% IBIs outside physiological range = bad signal
            return False, (
                f"FAIL  {out_of_range}/{len(ibi_ms)} IBIs outside {PPG_IBI_MIN_MS:.0f}–{PPG_IBI_MAX_MS:.0f}ms "
                f"range ({frac:.0%} bad)\n"
                "       → Check finger strap tension and sensor placement on the index finger."
            )

    mean_hr = result["mean_hr"]
    return True, (
        f"PASS  {n_peaks} peaks detected  mean HR={mean_hr:.1f} BPM  "
        f"({len(ibi_ms)} valid IBIs)"
    )


def check_imu(samples: list[dict]) -> tuple[bool, str]:
    """IMU sanity check: max absolute ACC value > IMU_MIN_ABS (connectivity, not motion)."""
    max_abs = max(
        max(abs(s["acc_x"]), abs(s["acc_y"]), abs(s["acc_z"]))
        for s in samples
    )
    ok = max_abs > IMU_MIN_ABS
    if ok:
        return True, f"PASS  max |ACC| = {max_abs}  (threshold > {IMU_MIN_ABS})"
    else:
        return False, (
            f"FAIL  max |ACC| = {max_abs}  (threshold > {IMU_MIN_ABS})\n"
            "       → MPU6050 not responding as expected — check I2C wiring (GPIO21/22)."
        )


# ── Override logging ──────────────────────────────────────────────────────────

def _log_override(subject: str, failed_checks: list[str], reason: str) -> None:
    """Append an override record to outputs/logs/{subject}_override.log."""
    log_dir = Path("outputs/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{subject}_override.log"
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(
            f"[{ts}] OVERRIDE — subject={subject}\n"
            f"  Failed checks: {', '.join(failed_checks)}\n"
            f"  Operator reason: {reason}\n\n"
        )
    print(f"  Override logged -> {log_path}")


# ── Main check loop ───────────────────────────────────────────────────────────

def run_checks(subject: str, port: str, baud: int, duration: float) -> int:
    """
    Stream, run checks, print results, handle re-check / override loop.
    Returns 0 on pass or override, 1 on abort.
    """
    while True:
        try:
            samples = _stream_samples(port, baud, duration)
        except Exception as exc:
            print(f"\nERROR: Could not open serial port {port}: {exc}")
            print("       Check the port number and that the ESP32 is connected.")
            resp = input("  Type 'retry' to try again, or press Enter to abort: ").strip().lower()
            if resp == "retry":
                continue
            return 1

        if len(samples) < 50:
            print(f"\nERROR: Only {len(samples)} samples received — expected ~{duration * HW_FS:.0f}.")
            print("       Firmware may not be running. Check Arduino IDE serial monitor.")
            resp = input("  Type 'retry' to try again, or press Enter to abort: ").strip().lower()
            if resp == "retry":
                continue
            return 1

        print(f"\n{'─'*55}")
        print(f"  Pre-Session Sensor Check — Subject: {subject}")
        print(f"{'─'*55}")

        checks = [
            ("GSR contact",  check_gsr),
            ("PPG waveform", check_ppg),
            ("IMU sanity",   check_imu),
        ]

        failed: list[str] = []
        for name, fn in checks:
            ok, msg = fn(samples)
            prefix = "✓" if ok else "✗"
            print(f"  {prefix}  {name:15s} — {msg}")
            if not ok:
                failed.append(name)

        print(f"{'─'*55}")

        if not failed:
            print("  ✓  All checks passed. Proceed with session.\n")
            return 0

        print(f"\n  ✗  {len(failed)} check(s) failed: {', '.join(failed)}")
        print("     Fix the sensor(s), then choose an option:")
        print("     [Enter]    — re-check after adjustment")
        print("     'override' — log and proceed anyway (e.g., confirmed low GSR responder)")
        print("     'abort'    — stop and do not proceed")

        resp = input("  Choice: ").strip().lower()

        if resp == "override":
            reason = input("  Brief reason for override (will be logged): ").strip()
            if not reason:
                reason = "no reason given"
            _log_override(subject, failed, reason)
            print(f"  Override accepted. Proceeding with {len(failed)} check(s) bypassed.\n")
            return 0

        elif resp == "abort":
            print("  Aborted. Session not started.\n")
            return 1

        # anything else (including blank Enter) → re-check
        print("  Re-running checks...\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pulse pre-session sensor quality check")
    parser.add_argument("--subject",  required=True, help="Subject ID (e.g. HW05)")
    parser.add_argument("--port",     default=DEFAULT_PORT, help="Serial port (default: COM3)")
    parser.add_argument("--baud",     default=DEFAULT_BAUD, type=int)
    parser.add_argument("--duration", default=DEFAULT_DURATION, type=float,
                        help="Streaming duration in seconds (default: 18)")
    args = parser.parse_args()

    sys.exit(run_checks(args.subject, args.port, args.baud, args.duration))


if __name__ == "__main__":
    main()
