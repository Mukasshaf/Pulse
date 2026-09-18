"""CLI entry point and top-level execution runner for Pulse."""
from __future__ import annotations

import argparse
import sys
import time

import pygame

from src.game.constants import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    DomainID,
    PulseEngineError,
)
from src.game.engine import GameEngine, SessionConfig


def parse_args() -> SessionConfig:
    """Parse command line arguments and generate initial SessionConfig."""
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
        action="store_true",
        help="Launch in borderless fullscreen mode",
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

    args = parser.parse_args()

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

    return SessionConfig(
        subject_id=args.subject,
        fast_baseline=args.fast_baseline,
        fullscreen=args.fullscreen,
        window_size=window_size,
        domain_filter=domain_filter,
        session_start_unix_ts_ms=start_ts,
        random_seed=seed,
    )


def main() -> None:
    """Initialize display and run game engine with top-level error trapping."""
    config = parse_args()

    pygame.init()
    if config.fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode(config.window_size)

    pygame.display.set_caption("Pulse — Stress Assessment Engine")

    try:
        engine = GameEngine(config, screen)
        engine.run()
        print(f"Session complete for subject {config.subject_id}.")
    except PulseEngineError as exc:
        print(f"PulseEngineError occurred: {exc}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nSession interrupted by user.", file=sys.stderr)
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
