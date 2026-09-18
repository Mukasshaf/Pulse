"""Unit tests for UI visual effects, color transitions, and animations."""
from __future__ import annotations

from src.game.constants import (
    COLOR_TIMER_AMBER,
    COLOR_TIMER_GREEN,
    COLOR_TIMER_RED,
    JITTER_MAX_PX,
    VIBRATION_MAX_PX,
)
from src.game.ui_effects import (
    ButtonFlash,
    ScreenVibration,
    TextJitter,
    TimerBarColorTransition,
)


def test_jitter_bounds() -> None:
    """Verify jitter offset never exceeds ±JITTER_MAX_PX across 1000 frames."""
    jitter = TextJitter()
    for elapsed in range(0, 10000, 10):
        dx, dy = jitter.get_offset(elapsed)
        assert abs(dx) <= JITTER_MAX_PX
        assert abs(dy) <= JITTER_MAX_PX


def test_timer_bar_color_transitions() -> None:
    """Verify timer bar color matches exact checkpoints at key fractions."""
    transition = TimerBarColorTransition()
    assert transition.get_color(1.0) == COLOR_TIMER_GREEN
    assert transition.get_color(0.333) == COLOR_TIMER_AMBER
    assert transition.get_color(0.10) == COLOR_TIMER_RED
    assert transition.get_color(0.0) == COLOR_TIMER_RED


def test_screen_vibration_bounds() -> None:
    """Verify vibration offset never exceeds ±VIBRATION_MAX_PX."""
    vib = ScreenVibration()
    for elapsed in range(0, 5000, 16):
        dx, dy = vib.get_offset(elapsed, intensity=1.0)
        assert abs(dx) <= VIBRATION_MAX_PX
        assert abs(dy) <= VIBRATION_MAX_PX


def test_button_flash_lifecycle() -> None:
    """Verify 200ms duration and state reset for button flash."""
    flash = ButtonFlash()
    assert flash.is_flashing() is False

    flash.trigger()
    assert flash.is_flashing() is True

    flash.update(100)
    assert flash.is_flashing() is True

    flash.update(100)
    assert flash.is_flashing() is False
