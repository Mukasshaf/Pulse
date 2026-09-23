"""Shared fixtures for Pulse test suite."""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
import pygame

from src.game.constants import DomainID, EventType
from src.game.event_logger import GameEvent
from src.game.scenarios import Domain, build_domain_registry

# Headless SDL video and audio drivers for automated testing
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"


from collections.abc import Generator


@pytest.fixture(scope="session", autouse=True)
def init_pygame() -> Generator[None, None, None]:
    """Initialize pygame subsystems in headless mode."""
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def screen() -> pygame.Surface:
    """Provide a headless 1280x720 surface for renderer tests."""
    return pygame.Surface((1280, 720))


@pytest.fixture
def domain_registry() -> list[Domain]:
    """Provide fully populated domain registry."""
    return build_domain_registry()


@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    """Provide temporary directory for log testing."""
    return tmp_path / "test_output"


@pytest.fixture
def sample_event() -> GameEvent:
    """Provide a representative GameEvent instance."""
    return GameEvent(
        unix_ts_ms=int(time.time_ns() // 1_000_000),
        event_type=EventType.BASELINE_START,
        domain="",
        scenario_id="",
        choice_data="{}",
        key_pressed=None,
        option_index=None,
        response_time_ms=None,
        metadata={},
    )
