"""Palette tests: the UI draws only the Ferrari tokens and neutral greys (ADR-B5)."""
from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pygame

from src.game import constants
from src.game.constants import (
    COLOR_BG,
    COLOR_CARD_BG,
    COLOR_HAIRLINE_SUBTLE,
    COLOR_PRIMARY_ROSSO,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    ScenarioType,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Domain, Scenario
from src.game.ui import UIRenderer
from src.game.ui_effects import TimerBarColorTransition, UIEffectState

GAME_DIR = Path(constants.__file__).parent

# DESIGN-ferrari.md colour tokens. Every chromatic colour the UI may draw is one of the last six.
DESIGN_TOKENS: dict[str, tuple[int, int, int]] = {
    "COLOR_BG": (0x18, 0x18, 0x18),
    "COLOR_CARD_BG": (0x30, 0x30, 0x30),
    "COLOR_HAIRLINE": (0x30, 0x30, 0x30),
    "COLOR_TEXT_PRIMARY": (0xFF, 0xFF, 0xFF),
    "COLOR_TEXT_SECONDARY": (0x96, 0x96, 0x96),
    "COLOR_TEXT_MUTED": (0x66, 0x66, 0x66),
    "COLOR_PRIMARY_ROSSO": (0xDA, 0x29, 0x1C),
    "COLOR_PRIMARY_ACTIVE": (0xB0, 0x1E, 0x0A),
    "COLOR_SEMANTIC_WARNING": (0xF1, 0x3A, 0x2C),
    "COLOR_ACCENT_CYAN": (0x4C, 0x98, 0xB9),
    "COLOR_ACCENT_YELLOW": (0xF6, 0xE5, 0x00),
    "COLOR_TIMER_GREEN": (0x03, 0x90, 0x4A),
}
CHROMATIC_TOKENS = ("COLOR_PRIMARY_ROSSO", "COLOR_PRIMARY_ACTIVE", "COLOR_SEMANTIC_WARNING", "COLOR_ACCENT_CYAN", "COLOR_ACCENT_YELLOW", "COLOR_TIMER_GREEN")
CHROMA_FLOOR = 10  # channel spread below which a pixel counts as neutral


def _hue_degrees(rgb: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Return the HSV hue in degrees of each RGB row."""
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    high = rgb.max(axis=1)
    spread = high - rgb.min(axis=1)
    spread = np.where(spread == 0.0, 1.0, spread)
    sector = np.where(high == r, ((g - b) / spread) % 6.0, np.where(high == g, (b - r) / spread + 2.0, (r - g) / spread + 4.0))
    hue: npt.NDArray[np.float64] = sector * 60.0
    return hue


def _token_hue(name: str) -> float:
    return float(_hue_degrees(np.array([DESIGN_TOKENS[name]], dtype=np.float64))[0])


def _off_palette_pixels(surface: pygame.Surface) -> int:
    """Count chromatic pixels whose hue is neither a token hue nor on a token-to-token gradient.

    Blending a token with any grey (anti-aliasing, alpha overlays, a mix toward the canvas) leaves
    the hue unchanged, so only an off-palette colour can produce a foreign hue. The timer bar, the
    composure bar, and the reward glow interpolate between semantic tokens, which is why the arcs
    Rosso -> yellow -> green -> cyan are accepted as well.
    """
    raw = pygame.surfarray.array3d(surface)
    r, g, b = (raw[..., channel].astype(np.int32) for channel in range(3))
    chromatic = (np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)) > CHROMA_FLOOR
    if not chromatic.any():
        return 0
    # Frames are mostly flat fills, so the hue is computed once per distinct chromatic colour
    codes, counts = np.unique((r[chromatic] << 16) | (g[chromatic] << 8) | b[chromatic], return_counts=True)
    pixels = np.stack([(codes >> 16) & 255, (codes >> 8) & 255, codes & 255], axis=1).astype(np.float64)
    hue = _hue_degrees(pixels)
    tolerance = np.maximum(6.0, 420.0 / (pixels.max(axis=1) - pixels.min(axis=1)))
    allowed = np.zeros(hue.shape, dtype=bool)
    for name in CHROMATIC_TOKENS:
        allowed |= np.abs(((hue - _token_hue(name) + 180.0) % 360.0) - 180.0) <= tolerance
    arc = [_token_hue("COLOR_PRIMARY_ROSSO"), _token_hue("COLOR_ACCENT_YELLOW"), _token_hue("COLOR_TIMER_GREEN"), _token_hue("COLOR_ACCENT_CYAN")]
    allowed |= (hue >= arc[0] - tolerance) & (hue <= arc[-1] + tolerance)
    return int(counts[~allowed].sum())


def _rosso_pixels(surface: pygame.Surface) -> int:
    """Count pixels drawn in solid Rosso Corsa."""
    pixels = pygame.surfarray.array3d(surface).reshape(-1, 3)
    return int((pixels == np.array(COLOR_PRIMARY_ROSSO, dtype=pixels.dtype)).all(axis=1).sum())


def _runners(scenario: Scenario) -> tuple[MISTRunner | None, BARTRunner | None, RewardAccumulator | None]:
    mist = MISTRunner(scenario.math_problems, scenario.decision_duration_s) if scenario.math_problems else None
    bart = BARTRunner(scenario.bart_config, seed=42) if scenario.bart_config else None
    reward = RewardAccumulator(scenario.reward_config, seed=42) if scenario.reward_config else None
    if bart is not None:
        bart.pump_count, bart.current_value = 9, 550
    if reward is not None:
        reward.collapse_time_ms = 10**9
        reward.update(18000)
    return mist, bart, reward


def _pixel(surface: pygame.Surface, pos: tuple[int, int]) -> tuple[int, ...]:
    return tuple(surface.get_at(pos))[:3]


def test_palette_tokens_match_the_ferrari_design_system() -> None:
    """Verify every colour token carries the value specified in DESIGN-ferrari.md."""
    for name, expected in DESIGN_TOKENS.items():
        assert getattr(constants, name) == expected, name
    assert constants.COLOR_TIMER_AMBER == constants.COLOR_ACCENT_YELLOW
    assert constants.COLOR_TIMER_RED == constants.COLOR_PRIMARY_ROSSO
    assert min(constants.COLOR_BG) > 0  # the canvas is near-black, never pure black
    assert not hasattr(constants, "COLOR_ACCENT_INDIGO")


def test_ui_code_has_no_chromatic_colour_literals() -> None:
    """Verify chromatic colour reaches the UI only through tokens: every literal colour is a neutral grey."""
    offenders: list[str] = []
    for path in sorted(GAME_DIR.glob("ui*.py")) + sorted((GAME_DIR / "skins").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        membership_tests = {id(comp) for node in ast.walk(tree) if isinstance(node, ast.Compare) for comp in node.comparators}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Tuple) or len(node.elts) not in (3, 4) or id(node) in membership_tests:
                continue
            values = [elt.value for elt in node.elts if isinstance(elt, ast.Constant) and type(elt.value) is int]
            if len(values) != len(node.elts) or max(values) > 255:
                continue
            if not values[0] == values[1] == values[2]:
                offenders.append(f"{path.name}:{node.lineno} {tuple(values)}")
    assert offenders == []


def test_off_palette_detector_flags_foreign_hues(screen: pygame.Surface) -> None:
    """Verify the pixel audit itself: purple and navy are caught, tokens and their grey blends are not."""
    screen.fill(COLOR_BG)
    for index, name in enumerate(CHROMATIC_TOKENS):
        pygame.draw.rect(screen, DESIGN_TOKENS[name], (20 + index * 60, 20, 40, 40))
        pygame.draw.rect(screen, UIRenderer._mix(DESIGN_TOKENS[name], COLOR_BG, 0.7), (20 + index * 60, 80, 40, 40))
        pygame.draw.rect(screen, UIRenderer._mix(DESIGN_TOKENS[name], COLOR_TEXT_PRIMARY, 0.6), (20 + index * 60, 140, 40, 40))
    assert _off_palette_pixels(screen) == 0
    pygame.draw.rect(screen, (180, 120, 255), (500, 20, 10, 10))  # the retired purple accent
    pygame.draw.rect(screen, (22, 28, 44), (500, 40, 10, 10))  # a navy-tinted panel fill
    assert _off_palette_pixels(screen) == 200


def test_every_screen_renders_inside_the_palette(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify all 14 skins and every non-decision screen draw only token hues and neutral greys."""
    renderer = UIRenderer(screen)
    timer = TimerBarColorTransition()
    for domain in domain_registry:
        for scenario in domain.scenarios:
            mist, bart, reward = _runners(scenario)
            composure = 0.5 if scenario.has_deception_metric else None
            for remaining_s, selected in ((float(scenario.decision_duration_s), None), (8.0, 0), (2.0, len(scenario.options) - 1)):
                effects = UIEffectState(timer_bar_color=timer.get_color(remaining_s / scenario.decision_duration_s), is_flashing=selected == 0)
                renderer.draw_decision(scenario, remaining_s, selected, effects, mist, bart, reward, composure)
                assert _off_palette_pixels(screen) == 0, f"{scenario.skin} at {remaining_s}s"
            if bart is not None:
                bart.is_burst = True
                renderer.draw_decision(scenario, 15.0, 1, UIEffectState(), None, bart, None, None)
                assert _off_palette_pixels(screen) == 0, f"{scenario.skin} burst"
            if reward is not None:
                reward.is_collapsed = True
                renderer.draw_decision(scenario, 15.0, None, UIEffectState(), None, None, reward, None)
                assert _off_palette_pixels(screen) == 0, f"{scenario.skin} collapsed"
            renderer.draw_question_popup(scenario)
            assert _off_palette_pixels(screen) == 0, f"{scenario.id} popup"
            renderer.draw_priming(scenario, 3.0, skip_available=False)
            assert _off_palette_pixels(screen) == 0, f"{scenario.id} priming"
            renderer.draw_feedback(scenario.options[-1].consequence_text, 1.0)
            assert _off_palette_pixels(screen) == 0, f"{scenario.id} feedback"
            if scenario.post_wait_text:
                for choice in (0, 1):
                    renderer.set_last_choice(choice)
                    renderer.draw_post_wait(scenario.post_wait_text, 0.4)
                    assert _off_palette_pixels(screen) == 0, f"{scenario.id} post-wait {choice}"

    renderer.draw_id_input("S0", "Enter a valid Subject ID (e.g. S01, S99)")
    assert _off_palette_pixels(screen) == 0
    renderer.draw_baseline(42.0, 180.0)
    assert _off_palette_pixels(screen) == 0
    renderer.draw_rest(True, 22.0)
    assert _off_palette_pixels(screen) == 0
    renderer.draw_debrief(1834.0, 14)
    assert _off_palette_pixels(screen) == 0


def test_key_badge_is_neutral_and_inverts_when_selected(screen: pygame.Surface) -> None:
    """Verify key prompts are dark plates with a Grigio border, never Rosso, and invert once chosen."""
    renderer = UIRenderer(screen)
    rect = pygame.Rect(100, 100, 36, 36)
    screen.fill(COLOR_CARD_BG)

    renderer._draw_key_badge(rect, "1")
    assert _pixel(screen, (100, 100)) == COLOR_TEXT_SECONDARY  # Grigio border
    assert _pixel(screen, (102, 102)) == COLOR_BG  # dark plate
    assert _off_palette_pixels(screen) == 0 and _rosso_pixels(screen) == 0

    renderer._draw_key_badge(rect, "1", selected=True)
    assert _pixel(screen, (102, 102)) == COLOR_TEXT_PRIMARY
    assert _rosso_pixels(screen) == 0

    renderer._draw_key_badge(rect, "2", enabled=False)
    assert _pixel(screen, (100, 100)) == COLOR_HAIRLINE_SUBTLE
    assert _pixel(screen, (102, 102)) == COLOR_BG


def test_selecting_an_option_never_adds_rosso(screen: pygame.Surface, domain_registry: list[Domain]) -> None:
    """Verify Rosso Corsa never marks the participant's own choice on any skin where one option is committed."""
    renderer = UIRenderer(screen)
    neutral_selection_skins = {
        "misconduct_hearing", "group_chat", "team_kanban", "document_workspace", "tournament_bracket", "portal_log",
        "code_diff", "fork_map", "notification_stack", "defense_stage", "classroom_critique",
    }
    checked: set[str] = set()
    for domain in domain_registry:
        for scenario in domain.scenarios:
            if scenario.skin not in neutral_selection_skins:
                continue
            assert scenario.scenario_type in (ScenarioType.STANDARD_MCQ, ScenarioType.DELAY_WAIT)
            remaining_s = float(scenario.decision_duration_s)  # full time: no drone, no expiry colouring
            renderer.draw_decision(scenario, remaining_s, None, UIEffectState(), None, None, None, None)
            baseline_rosso = _rosso_pixels(screen)
            for index in range(len(scenario.options)):
                renderer.draw_decision(scenario, remaining_s, index, UIEffectState(), None, None, None, None)
                assert _rosso_pixels(screen) <= baseline_rosso, f"{scenario.skin} option {index + 1}"
            checked.add(scenario.skin)
    assert checked == neutral_selection_skins


def test_option_frame_marks_the_choice_in_white_and_keeps_the_accent_as_a_rule(screen: pygame.Surface) -> None:
    """Verify the shared option plate: white border once chosen, a hairline when passed over, an accent that is only a left rule."""
    renderer = UIRenderer(screen)
    rect = pygame.Rect(100, 100, 400, 80)
    accent = constants.COLOR_TIMER_GREEN

    screen.fill(COLOR_BG)
    idle = renderer._draw_option_frame(rect, 0, None, accent=accent)
    assert (idle.chosen, idle.passed) == (False, False)
    assert _pixel(screen, rect.topleft) == COLOR_HAIRLINE_SUBTLE
    assert _pixel(screen, (rect.left + 2, rect.centery)) == accent  # the accent is a left rule ...
    assert _pixel(screen, (rect.right - 1, rect.centery)) == COLOR_HAIRLINE_SUBTLE  # ... and never the whole border

    chosen = renderer._draw_option_frame(rect, 0, 0, accent=accent)
    assert chosen.chosen and chosen.ink == COLOR_TEXT_PRIMARY
    assert _pixel(screen, rect.topleft) == COLOR_TEXT_PRIMARY
    assert _pixel(screen, (rect.left + 2, rect.centery)) == accent  # unchanged by the choice, so it cannot grade it

    passed = renderer._draw_option_frame(rect, 0, 1, accent=accent)
    assert passed.passed and passed.ink == COLOR_TEXT_SECONDARY
    assert _pixel(screen, rect.topleft) == constants.COLOR_HAIRLINE
    assert _pixel(screen, (rect.left + 2, rect.centery)) != accent  # dimmed toward the canvas

    screen.fill(COLOR_BG)
    renderer._draw_option_frame(rect, 0, 0)
    raw = pygame.surfarray.array3d(screen).astype(np.int32)
    assert int((raw.max(axis=2) - raw.min(axis=2)).max()) == 0  # with no accent the plate is neutral in every state
