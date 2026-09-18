"""Visual stress and feedback effects for UI rendering in Pulse."""
from __future__ import annotations

import math
from dataclasses import dataclass

from src.game.constants import (
    BUTTON_FLASH_DURATION_MS,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_GREEN,
    COLOR_TIMER_RED,
    JITTER_MAX_HZ,
    JITTER_MAX_PX,
    TIMER_BAR_AMBER_FRACTION,
    TIMER_BAR_RED_FRACTION,
    VIBRATION_MAX_PX,
)


@dataclass
class UIEffectState:
    """Aggregate per-frame effect state passed from engine to UIRenderer."""

    jitter_offset: tuple[int, int] = (0, 0)
    vibration_offset: tuple[int, int] = (0, 0)
    is_flashing: bool = False
    timer_bar_color: tuple[int, int, int] = COLOR_TIMER_GREEN


class TextJitter:
    """Computes oscillatory pixel offsets for text under cognitive pressure."""

    def __init__(self, max_px: int = JITTER_MAX_PX, max_hz: float = JITTER_MAX_HZ) -> None:
        """Initialize jitter parameters constrained by WCAG accessibility bounds."""
        self.max_px: int = max_px
        self.max_hz: float = max_hz

    def get_offset(self, elapsed_ms: int) -> tuple[int, int]:
        """Compute (dx, dy) offset within [-max_px, max_px]."""
        sec = elapsed_ms / 1000.0
        angle = 2.0 * math.pi * self.max_hz * sec
        dx = int(round(math.sin(angle) * self.max_px))
        dy = int(round(math.cos(angle * 1.5) * self.max_px))
        dx = max(-self.max_px, min(self.max_px, dx))
        dy = max(-self.max_px, min(self.max_px, dy))
        return (dx, dy)


class TimerBarColorTransition:
    """Computes color transitions along the timer expiration gradient."""

    def get_color(self, fraction_remaining: float) -> tuple[int, int, int]:
        """Return RGB color corresponding to remaining time fraction."""
        frac = max(0.0, min(1.0, fraction_remaining))

        if frac <= TIMER_BAR_RED_FRACTION:
            return COLOR_TIMER_RED

        if frac <= TIMER_BAR_AMBER_FRACTION:
            span = TIMER_BAR_AMBER_FRACTION - TIMER_BAR_RED_FRACTION
            if span <= 0:
                return COLOR_TIMER_AMBER
            ratio = (frac - TIMER_BAR_RED_FRACTION) / span
            r = int(COLOR_TIMER_RED[0] + (COLOR_TIMER_AMBER[0] - COLOR_TIMER_RED[0]) * ratio)
            g = int(COLOR_TIMER_RED[1] + (COLOR_TIMER_AMBER[1] - COLOR_TIMER_RED[1]) * ratio)
            b = int(COLOR_TIMER_RED[2] + (COLOR_TIMER_AMBER[2] - COLOR_TIMER_RED[2]) * ratio)
            return (r, g, b)

        span = 1.0 - TIMER_BAR_AMBER_FRACTION
        ratio = (frac - TIMER_BAR_AMBER_FRACTION) / span
        r = int(COLOR_TIMER_AMBER[0] + (COLOR_TIMER_GREEN[0] - COLOR_TIMER_AMBER[0]) * ratio)
        g = int(COLOR_TIMER_AMBER[1] + (COLOR_TIMER_GREEN[1] - COLOR_TIMER_AMBER[1]) * ratio)
        b = int(COLOR_TIMER_AMBER[2] + (COLOR_TIMER_GREEN[2] - COLOR_TIMER_AMBER[2]) * ratio)
        return (r, g, b)


class ScreenVibration:
    """Computes low-amplitude screen shake offsets for accumulator instability."""

    def __init__(self, max_px: int = VIBRATION_MAX_PX) -> None:
        """Initialize vibration limits."""
        self.max_px: int = max_px

    def get_offset(self, elapsed_ms: int, intensity: float = 1.0) -> tuple[int, int]:
        """Compute (dx, dy) vibration offset scaled by intensity fraction."""
        scaled_intensity = max(0.0, min(1.0, intensity))
        sec = elapsed_ms / 1000.0
        angle = 2.0 * math.pi * 2.0 * sec
        amp = self.max_px * scaled_intensity
        dx = int(round(math.sin(angle * 1.3) * amp))
        dy = int(round(math.cos(angle * 0.9) * amp))
        dx = max(-self.max_px, min(self.max_px, dx))
        dy = max(-self.max_px, min(self.max_px, dy))
        return (dx, dy)


class ButtonFlash:
    """Tracks 200ms red flash state for wrong-answer feedback."""

    def __init__(self, duration_ms: int = BUTTON_FLASH_DURATION_MS) -> None:
        """Initialize flash duration."""
        self.duration_ms: int = duration_ms
        self._timer_ms: int = 0

    def trigger(self) -> None:
        """Initiate button flash sequence."""
        self._timer_ms = self.duration_ms

    def update(self, dt_ms: int) -> None:
        """Decrement flash timer each frame."""
        if self._timer_ms > 0:
            self._timer_ms = max(0, self._timer_ms - dt_ms)

    def is_flashing(self) -> bool:
        """Return True while flash timer is non-zero."""
        return self._timer_ms > 0
