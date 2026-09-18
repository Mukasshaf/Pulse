"""
serial_reader.py -- reads live ESP32 sensor stream over serial USB,
validates rows on arrival, and writes a timestamped CSV.

Hardware CSV schema (firmware output):
    sample_idx, timestamp_ms, pulse_raw, gsr_raw, acc_x, acc_y, acc_z

Output CSV schema (adds unix_ts_ms as join key for align_signals.py):
    sample_idx, timestamp_ms, unix_ts_ms, pulse_raw, gsr_raw, acc_x, acc_y, acc_z

unix_ts_ms = wall-clock Unix time in ms at the moment the row is received
             on the PC side. This is the key that align_signals.py will use
             to join against the game engine's event log.
             The device-side timestamp_ms is kept for debugging/drift analysis.

Row validation:
  - Exactly 7 comma-separated fields
  - All fields parseable as their expected types (see FIELD_TYPES)
  - sample_idx gaps (diff != 1) are logged with a running counter
  - timestamp_ms backwards steps are logged with a warning
  - Malformed rows are rejected and logged -- never passed through
"""

import csv
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

try:
    import serial
except ImportError:
    serial = None   # allow import without pyserial for testing

# --- Configuration ---
DEFAULT_PORT     = "COM3"
DEFAULT_BAUD     = 115200
DEFAULT_TIMEOUT  = 1.0          # seconds
DEFAULT_OUT_DIR  = "raw"

# Expected field order from firmware
FIELD_NAMES = [
    "sample_idx", "timestamp_ms",
    "pulse_raw", "gsr_raw",
    "acc_x", "acc_y", "acc_z",
]
FIELD_TYPES = {
    "sample_idx":   int,
    "timestamp_ms": int,
    "pulse_raw":    int,
    "gsr_raw":      int,
    "acc_x":        int,
    "acc_y":        int,
    "acc_z":        int,
}
N_FIELDS = len(FIELD_NAMES)

# Output includes unix_ts_ms inserted after timestamp_ms
OUTPUT_FIELDNAMES = [
    "sample_idx", "timestamp_ms", "unix_ts_ms",
    "pulse_raw", "gsr_raw", "acc_x", "acc_y", "acc_z",
]


def _setup_logging(out_dir: Path) -> None:
    log_path = out_dir / f"serial_reader_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)s  %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout),
        ],
    )


def _validate_row(raw_line: str) -> dict | None:
    """
    Parse and validate one raw serial line.
    Returns a dict of typed field values, or None if invalid.
    """
    parts = raw_line.strip().split(",")
    if len(parts) != N_FIELDS:
        return None

    try:
        return {name: FIELD_TYPES[name](val)
                for name, val in zip(FIELD_NAMES, parts)}
    except (ValueError, TypeError):
        return None


def read_serial(
    port:     str   = DEFAULT_PORT,
    baud:     int   = DEFAULT_BAUD,
    out_dir:  str   = DEFAULT_OUT_DIR,
    duration: float | None = None,
) -> Path:
    """
    Open serial port, read rows until duration (s) elapses or KeyboardInterrupt.
    Writes validated rows to a timestamped CSV in out_dir.
    Returns path to the output CSV.
    """
    if serial is None:
        raise RuntimeError("pyserial is not installed -- run: uv add pyserial")

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    _setup_logging(out_path)

    session_ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path    = out_path / f"recorded_{session_ts}.csv"

    logging.info(f"Opening {port} at {baud} baud")
    logging.info(f"Output -> {csv_path}")

    total_rows    = 0
    rejected_rows = 0
    gap_events    = 0
    last_idx      = None
    last_ts_ms    = None
    start_time    = time.monotonic()

    with serial.Serial(port, baud, timeout=DEFAULT_TIMEOUT) as ser, \
         open(csv_path, "w", newline="", encoding="utf-8") as fh:

        writer = csv.DictWriter(fh, fieldnames=OUTPUT_FIELDNAMES)
        writer.writeheader()

        logging.info("Recording started -- Ctrl+C to stop")

        try:
            while True:
                if duration is not None:
                    if time.monotonic() - start_time >= duration:
                        break

                raw = ser.readline()
                if not raw:
                    continue

                # Arrival timestamp (Unix ms) -- before any processing
                unix_ts_ms = int(time.time() * 1000)

                line = raw.decode("utf-8", errors="replace").strip()
                if not line or line.startswith("#"):
                    continue   # skip header / comment lines from firmware

                row = _validate_row(line)
                if row is None:
                    rejected_rows += 1
                    logging.warning(f"REJECTED malformed row [{rejected_rows}]: {line!r}")
                    continue

                # --- sample_idx gap detection ---
                if last_idx is not None:
                    diff = row["sample_idx"] - last_idx
                    if diff != 1:
                        gap_events += 1
                        missed = diff - 1 if diff > 1 else "?"
                        logging.warning(
                            f"GAP: sample_idx jumped {last_idx}->{row['sample_idx']} "
                            f"(gap_event #{gap_events}, ~{missed} missed sample(s))"
                        )
                last_idx = row["sample_idx"]

                # --- timestamp_ms monotonicity ---
                if last_ts_ms is not None and row["timestamp_ms"] < last_ts_ms:
                    logging.warning(
                        f"BACKWARDS timestamp: {last_ts_ms} -> {row['timestamp_ms']}"
                    )
                last_ts_ms = row["timestamp_ms"]

                # --- Write row (with unix_ts_ms injected) ---
                out_row = dict(row)
                out_row["unix_ts_ms"] = unix_ts_ms
                writer.writerow(out_row)
                fh.flush()

                total_rows += 1
                if total_rows % 1000 == 0:
                    elapsed = time.monotonic() - start_time
                    logging.info(
                        f"{total_rows} rows  |  {elapsed:.1f}s  |  "
                        f"{rejected_rows} rejected  |  {gap_events} gap events"
                    )

        except KeyboardInterrupt:
            logging.info("Recording stopped by user")

    elapsed = time.monotonic() - start_time
    logging.info(
        f"\nSession complete: {total_rows} rows, {elapsed:.1f}s, "
        f"{rejected_rows} rejected, {gap_events} gap events"
    )
    logging.info(f"Saved -> {csv_path}")
    return csv_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pulse ESP32 serial reader")
    parser.add_argument("--port",     default=DEFAULT_PORT,  help="Serial port (default: COM3)")
    parser.add_argument("--baud",     default=DEFAULT_BAUD,  type=int)
    parser.add_argument("--out-dir",  default=DEFAULT_OUT_DIR)
    parser.add_argument("--duration", default=None, type=float,
                        help="Recording duration in seconds (omit for manual stop)")
    args = parser.parse_args()

    read_serial(
        port=args.port,
        baud=args.baud,
        out_dir=args.out_dir,
        duration=args.duration,
    )
