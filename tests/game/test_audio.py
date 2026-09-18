"""Unit tests for audio controller lifecycle and error handling."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.game.audio import AudioController
from src.game.constants import AudioLoadError


def test_audio_load_missing_file() -> None:
    """Verify AudioLoadError is raised when asset file is missing."""
    with pytest.raises(AudioLoadError):
        AudioController(Path("assets/audio/missing_asset.wav"))


def test_audio_lifecycle_with_real_asset() -> None:
    """Verify audio controller lifecycle idempotency with tension_drone.wav."""
    asset_path = Path("assets/audio/tension_drone.wav")
    if not asset_path.is_file():
        pytest.skip("Audio asset not found")

    ctrl = AudioController(asset_path)
    assert ctrl.is_playing() is False

    ctrl.start_drone(fade_in_ms=10)
    assert ctrl.is_playing() is True

    # Idempotent start
    ctrl.start_drone(fade_in_ms=10)
    assert ctrl.is_playing() is True

    ctrl.stop_drone(fade_out_ms=10)
    assert ctrl.is_playing() is False

    # Idempotent stop
    ctrl.stop_drone(fade_out_ms=10)
    assert ctrl.is_playing() is False
