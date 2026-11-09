"""CLI entry point and top-level execution runner for Pulse."""
from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pygame

from src.game.constants import (
    INTER_DOMAIN_REST_EXTENDED_S,
    INTER_DOMAIN_REST_S,
    MIN_ACTIVE_EPOCH_S,
    MIN_PRIMING_DURATION_S,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SUBJECT_ID_PATTERN,
    DomainID,
    PulseEngineError,
)
from src.game.engine import GameEngine, SessionConfig
from src.game.engine_state import session_output_dir
from src.game.sensor_bridge import create_bridge

SENSOR_RECORDING_NAME: str = "sensor_stream.csv"


@dataclass(frozen=True)
class BridgeOptions:
    """Sensor-bridge selection parsed from the command line."""

    mode: str
    port: str | None
    source: Path | None
    follow: bool


def _build_parser() -> argparse.ArgumentParser:
    """Define the command line interface."""
    parser = argparse.ArgumentParser(
        description="Pulse Gamification Engine — 7-Domain Biosignal Stress Protocol",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--subject",
        type=str,
        required=True,
        help="Participant Subject ID (e.g. S01, S99)",
    )
    parser.add_argument(
        "--fast-baseline",
        action="store_true",
        help="Reduce initial baseline calibration to 10 seconds for testing",
    )
    parser.add_argument(
        "--fullscreen",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Launch in fullscreen mode (use --no-fullscreen for windowed mode)",
    )
    parser.add_argument(
        "--window-size",
        type=str,
        default=f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}",
        help="Window dimensions formatted as WIDTHxHEIGHT",
    )
    parser.add_argument(
        "--domain",
        type=str,
        choices=[d.value for d in DomainID],
        default=None,
        help="Run only a specific domain (e.g. academic_pressure)",
    )
    parser.add_argument(
        "--no-exposure-floor",
        action="store_true",
        help="Developer testing only: allow instant priming skip and early decision exit (breaks the 60 s HRV epoch)",
    )
    parser.add_argument(
        "--extended-rest",
        action="store_true",
        help=f"Use a {INTER_DOMAIN_REST_EXTENDED_S} s wash-out between domains instead of {INTER_DOMAIN_REST_S} s",
    )
    parser.add_argument(
        "--bridge",
        choices=["auto", "serial", "stub", "replay"],
        default="auto",
        help="Sensor bridge: auto = ESP32 if it answers, else stub; serial = require the ESP32; "
        "replay = feed from a recorded CSV; stub = no telemetry",
    )
    parser.add_argument(
        "--bridge-port",
        type=str,
        default=None,
        help="Serial port to use (e.g. COM3) instead of scanning for an ESP32",
    )
    parser.add_argument(
        "--bridge-source",
        type=Path,
        default=None,
        help="CSV file, or directory holding recordings, for --bridge replay",
    )
    parser.add_argument(
        "--bridge-follow",
        action="store_true",
        help="With --bridge replay: tail a CSV that serial_reader.py is writing (it keeps the port)",
    )
    return parser


def parse_cli(argv: list[str] | None = None) -> tuple[SessionConfig, BridgeOptions]:
    """Parse command line arguments into the session configuration and the bridge selection."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not re.match(SUBJECT_ID_PATTERN, args.subject):
        parser.error(f"--subject must match {SUBJECT_ID_PATTERN} (e.g. S01)")
    if args.bridge == "replay" and args.bridge_source is None:
        parser.error("--bridge replay needs --bridge-source")

    # Parse window size
    try:
        parts = args.window_size.lower().split("x")
        w = int(parts[0])
        h = int(parts[1])
        window_size = (w, h)
    except (ValueError, IndexError):
        window_size = (SCREEN_WIDTH, SCREEN_HEIGHT)

    domain_filter = DomainID(args.domain) if args.domain else None
    start_ts = int(time.time_ns() // 1_000_000)
    seed = int(time.time_ns() % (2**31))

    config = SessionConfig(
        subject_id=args.subject,
        fast_baseline=args.fast_baseline,
        fullscreen=args.fullscreen,
        window_size=window_size,
        domain_filter=domain_filter,
        session_start_unix_ts_ms=start_ts,
        random_seed=seed,
        hold_full_decision=not args.no_exposure_floor,
        min_priming_s=0 if args.no_exposure_floor else MIN_PRIMING_DURATION_S,
        min_active_epoch_s=0 if args.no_exposure_floor else MIN_ACTIVE_EPOCH_S,
        inter_domain_rest_s=float(INTER_DOMAIN_REST_EXTENDED_S if args.extended_rest else INTER_DOMAIN_REST_S),
    )
    bridge = BridgeOptions(mode=args.bridge, port=args.bridge_port, source=args.bridge_source, follow=args.bridge_follow)
    return (config, bridge)


def parse_args() -> SessionConfig:
    """Parse command line arguments and generate initial SessionConfig."""
    return parse_cli()[0]


def main() -> None:
    """Initialize the sensor bridge and display, then run the engine with top-level error trapping."""
    config, bridge_options = parse_cli()

    # The bridge is probed before the window opens so a multi-second port scan never shows a frozen screen
    try:
        setup = create_bridge(
            bridge_options.mode,
            port=bridge_options.port,
            source=bridge_options.source,
            follow=bridge_options.follow,
            record_path=session_output_dir(config) / SENSOR_RECORDING_NAME,
        )
    except PulseEngineError as exc:
        print(f"PulseEngineError occurred: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    print(f"Sensor bridge [{setup.mode}]: {setup.detail}")
    if setup.mode == "stub":
        print("WARNING: no live telemetry - the Domain 7 composure display stays on STANDBY for this session.", file=sys.stderr)

    pygame.init()
    if config.fullscreen:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
    else:
        screen = pygame.display.set_mode(config.window_size)

    pygame.display.set_caption("Pulse — Stress Assessment Engine")

    try:
        engine = GameEngine(config, screen, bridge=setup.bridge)
        engine.run()
        print(f"Session complete for subject {config.subject_id}.")
    except PulseEngineError as exc:
        print(f"PulseEngineError occurred: {exc}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nSession interrupted by user.", file=sys.stderr)
    finally:
        setup.bridge.close()
        pygame.quit()


if __name__ == "__main__":
    main()
