"""Visual stress and feedback effects for UI rendering in Pulse."""
from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from src.game.constants import (
    BUTTON_FLASH_DURATION_MS,
    COLOR_ACCENT_CYAN,
    COLOR_PRIMARY_ACTIVE,
    COLOR_TEXT_PRIMARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_GREEN,
    COLOR_TIMER_RED,
    JITTER_MAX_HZ,
    JITTER_MAX_PX,
    TIMER_BAR_AMBER_FRACTION,
    TIMER_BAR_RED_FRACTION,
    VIBRATION_MAX_HZ,
    VIBRATION_MAX_PX,
)


def _clamp_radial(fx: float, fy: float, max_px: int) -> tuple[int, int]:
    """Bound an offset by vector magnitude (not per axis), truncating toward zero."""
    mag = math.hypot(fx, fy)
    if mag > max_px > 0:
        fx, fy = fx * max_px / mag, fy * max_px / mag
    return (int(fx), int(fy))


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
        """Compute (dx, dy) with displacement <= max_px and both axes at or below max_hz."""
        sec = elapsed_ms / 1000.0
        angle = 2.0 * math.pi * self.max_hz * sec
        # Second axis runs at 0.75x so the fastest component is max_hz itself
        return _clamp_radial(math.sin(angle) * self.max_px, math.cos(angle * 0.75) * self.max_px, self.max_px)


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
        angle = 2.0 * math.pi * VIBRATION_MAX_HZ * sec
        amp = self.max_px * scaled_intensity
        return _clamp_radial(math.sin(angle) * amp, math.cos(angle * 0.7) * amp, self.max_px)


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


@dataclass
class ShatterParticle:
    """Individual rectangular fragment in a radial shatter dispersal."""

    x: float
    y: float
    vx: float
    vy: float
    width: int
    height: int
    color: tuple[int, int, int]
    life_ms: int = 600
    elapsed_ms: int = 0


class RadialShatterEffect:
    """Computes and renders a 12-particle radial rectangular shatter dispersal on chest collapse."""

    def __init__(self, num_particles: int = 12, duration_ms: int = 600) -> None:
        """Initialize shatter effect parameters."""
        self.num_particles: int = num_particles
        self.duration_ms: int = duration_ms
        self.particles: list[ShatterParticle] = []
        self.is_active: bool = False

    def trigger(self, center: tuple[int, int], base_speed: float = 220.0) -> None:
        """Initialize radial burst of rectangular particles from the given center."""
        cx, cy = center
        self.particles = []
        self.is_active = True
        colors = [
            COLOR_ACCENT_CYAN,
            COLOR_TIMER_AMBER,
            COLOR_PRIMARY_ACTIVE,
            (76, 76, 76),
            COLOR_TEXT_PRIMARY,
            COLOR_TIMER_RED,
        ]
        for i in range(self.num_particles):
            angle = (2.0 * math.pi * i) / float(self.num_particles)
            speed = base_speed * (0.85 + (i % 3) * 0.15)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            col = colors[i % len(colors)]
            pw = 10 + (i % 3) * 3
            ph = 7 + ((i + 1) % 3) * 2
            self.particles.append(
                ShatterParticle(
                    x=float(cx),
                    y=float(cy),
                    vx=vx,
                    vy=vy,
                    width=pw,
                    height=ph,
                    color=col,
                    life_ms=self.duration_ms,
                    elapsed_ms=0,
                )
            )

    def update(self, dt_ms: int) -> None:
        """Advance particle trajectories and life timers."""
        if not self.is_active:
            return
        all_expired = True
        dt_sec = dt_ms / 1000.0
        for p in self.particles:
            p.elapsed_ms += dt_ms
            if p.elapsed_ms < p.life_ms:
                all_expired = False
                p.x += p.vx * dt_sec
                p.y += p.vy * dt_sec
        if all_expired:
            self.is_active = False

    def draw(self, screen: pygame.Surface) -> None:
        """Draw active particle rectangles with lifetime decay."""
        if not self.is_active:
            return
        for p in self.particles:
            if p.elapsed_ms < p.life_ms:
                decay = 1.0 - (p.elapsed_ms / float(p.life_ms))
                w = max(2, int(p.width * decay))
                h = max(2, int(p.height * decay))
                rect = pygame.Rect(int(p.x - w // 2), int(p.y - h // 2), w, h)
                pygame.draw.rect(screen, p.color, rect, border_radius=0)
