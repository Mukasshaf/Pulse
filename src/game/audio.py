"""Audio controller for tension drone synthesis and playback in Pulse."""
from __future__ import annotations

from pathlib import Path

import pygame

from src.game.constants import (
    DRONE_FADE_IN_MS,
    DRONE_FADE_OUT_MS,
    DRONE_VOLUME,
    AudioLoadError,
)


class AudioController:
    """Manages playback and fading of the diegetic 60-80 Hz tension drone."""

    def __init__(self, drone_path: Path) -> None:
        """Load tension drone sound from file path, validating asset existence."""
        self.drone_path: Path = drone_path
        self._sound: pygame.mixer.Sound | None = None
        self._channel: pygame.mixer.Channel | None = None
        self._is_playing: bool = False

        if not self.drone_path.is_file():
            raise AudioLoadError(str(self.drone_path))

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self._sound = pygame.mixer.Sound(str(self.drone_path))
            self._sound.set_volume(DRONE_VOLUME)
        except (pygame.error, OSError) as exc:
            raise AudioLoadError(f"{self.drone_path} ({exc})") from exc

    def start_drone(self, fade_in_ms: int = DRONE_FADE_IN_MS) -> None:
        """Begin looping playback with fade-in. Idempotent if already playing."""
        if self._is_playing or self._sound is None:
            return

        try:
            self._channel = self._sound.play(loops=-1, fade_ms=fade_in_ms)
            self._is_playing = True
        except pygame.error:
            self._channel = None
            self._is_playing = False

    def stop_drone(self, fade_out_ms: int = DRONE_FADE_OUT_MS) -> None:
        """Fade out and stop tension drone. Idempotent if not playing."""
        if not self._is_playing:
            return

        try:
            if self._sound is not None:
                self._sound.fadeout(fade_out_ms)
        except pygame.error:
            pass
        finally:
            self._is_playing = False
            self._channel = None

    def is_playing(self) -> bool:
        """Return whether the tension drone is actively playing."""
        return self._is_playing
