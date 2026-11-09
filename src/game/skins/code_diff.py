"""Simulation skin `code_diff` for scenario `rule_ambiguity_b`."""
from __future__ import annotations

import math

import pygame

from src.game.constants import (
    COLOR_BG,
    COLOR_HAIRLINE,
    COLOR_SEMANTIC_WARNING,
    COLOR_TEXT_PRIMARY,
    COLOR_TIMER_AMBER,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState

GROUP_CODE: tuple[str, ...] = (
    "class OptimizationEngine:",
    "    def __init__(self, weights: list[float]):",
    "        self.tensor_map = compute_latent_graph(weights)   # MATCH",
    "        self.matrix_delta = decompose_svd_fast(weights)   # MATCH",
    "        self.gradient_cache = [0.0] * len(weights)        # MATCH",
    "    def step_optimizer(self, lr: float):",
    "        return execute_forward_pass(self.tensor_map, lr)",
    "        # End of implementation block",
)
SENIOR_CODE: tuple[str, ...] = (
    "class LegacyPipelineRunner:",
    "    def __init__(self, weights: list[float]):",
    "        self.tensor_map = compute_latent_graph(weights)   # MATCH",
    "        self.matrix_delta = decompose_svd_fast(weights)   # MATCH",
    "        self.gradient_cache = [0.0] * len(weights)        # MATCH",
    "    def run_iteration(self, rate: float):",
    "        return execute_forward_pass(self.tensor_map, rate)",
    "        # Archived under CC-BY-NC 2022",
)
MATCHED_LINES = range(2, 5)  # lines 03-05 of both panes


class CodeDiffSkin(UIComponents):
    """Renders the `code_diff` decision skin."""

    def _draw_skin_code_diff(
        self,
        scenario: Scenario,
        time_remaining_s: float,
        selected_index: int | None,
        effects: UIEffectState,
        mist_runner: MISTRunner | None,
        bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None,
        composure_fraction: float | None,
    ) -> bool:
        """Render code_diff simulation skin: dual-pane repository diff viewer with highlighted overlapping segments."""
        ox = effects.vibration_offset[0] + effects.jitter_offset[0]
        oy = effects.vibration_offset[1] + effects.jitter_offset[1]
        content_w = self.width - 2 * self.MARGIN
        banner = pygame.Rect(self.MARGIN + ox, self.CONTENT_TOP + oy, content_w, 44)
        self._draw_diff_banner(banner, time_remaining_s)

        half_w = (content_w - 18) // 2
        left_pane = pygame.Rect(banner.left, banner.bottom + 12, half_w, 300)
        right_pane = pygame.Rect(left_pane.right + 18, left_pane.top, half_w, 300)
        self._draw_diff_pane(left_pane, "YOUR GROUP'S SUBMISSION: src/core/engine.py", (214, 214, 214), GROUP_CODE)
        self._draw_diff_pane(right_pane, "UNCREDITED ARCHIVE: repo_2022_grad/core.py (graduated senior)", COLOR_TIMER_AMBER, SENIOR_CODE)

        # Options: the action and its trade-off as logged; no option is colour-graded
        card_w = (content_w - 2 * 20) // 3
        for i, opt in enumerate(scenario.options):
            card = pygame.Rect(banner.left + i * (card_w + 20), left_pane.bottom + 14, card_w, 204)
            style = self._draw_option_frame(card, i, selected_index)
            badge = pygame.Rect(card.left + 16, card.top + 16, 36, 36)
            self._draw_key_badge(badge, str(opt.key), selected=style.chosen, enabled=not style.passed)
            if style.chosen:
                self._draw_tag("COMMITTED", (card.right - 16, badge.centery), anchor="midright", ink=COLOR_BG, fill=COLOR_TEXT_PRIMARY)
            action, trade_off = self._split_option(opt.text)
            end_y = self._draw_wrapped_text(action, self.font_body, style.ink, pygame.Rect(card.left + 16, badge.bottom + 14, card.width - 32, 62), spacing=2)
            self._draw_wrapped_text(trade_off, self.font_small, style.sub_ink, pygame.Rect(card.left + 16, end_y + 8, card.width - 32, card.bottom - end_y - 20), spacing=3)
        self._draw_footer_prompt("PRESS 1, 2 OR 3 TO COMMIT YOUR DECISION", selected_index is not None)
        return True

    def _draw_diff_banner(self, banner: pygame.Rect, time_remaining_s: float) -> None:
        """Draw the integrity-check banner and the submission deadline that keeps counting down."""
        self._draw_card(banner, border_color=COLOR_TIMER_AMBER, bg_color=COLOR_BG)
        # The caution yellow dims toward the canvas and back at about 0.5 Hz
        warn = self._mix(COLOR_TIMER_AMBER, COLOR_BG, 0.22 * (1.0 - (math.sin(time_remaining_s * 3.0) + 1.0) / 2.0))
        pygame.draw.polygon(self.screen, warn, [(banner.left + 24, banner.centery - 10), (banner.left + 14, banner.centery + 8), (banner.left + 34, banner.centery + 8)])
        self._draw_text("!", self.font_small, (20, 20, 20), (banner.left + 24, banner.centery + 1), center=True)
        self._draw_text("INTEGRITY CHECK: 38% OVERLAP WITH AN UNCREDITED SOURCE", self.font_body, warn, (banner.left + 46, banner.centery), midleft=True)
        seconds = int(time_remaining_s) % 60
        self._draw_text(f"SUBMISSION DEADLINE IN 2d 06:14:{seconds:02d}", self.font_mono_small, COLOR_SEMANTIC_WARNING, (banner.right - 20, banner.centery), midright=True)

    def _draw_diff_pane(self, pane: pygame.Rect, title: str, title_colour: tuple[int, int, int], code: tuple[str, ...]) -> None:
        """Draw one code pane; the matched lines sit on a translucent caution-yellow band with a solid left rule."""
        pygame.draw.rect(self.screen, (24, 24, 24), pane, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, pane, width=1, border_radius=0)
        header = pygame.Rect(pane.left, pane.top, pane.width, 32)
        pygame.draw.rect(self.screen, (36, 36, 36), header, border_radius=0)
        self._draw_text(title, self.font_small, title_colour, (header.left + 14, header.centery), midleft=True, max_width=pane.width - 28)

        line_h = 32
        for row, text in enumerate(code):
            line_y = header.bottom + 8 + row * line_h
            matched = row in MATCHED_LINES
            if matched:
                band = pygame.Rect(pane.left + 4, line_y - 2, pane.width - 8, line_h - 2)
                wash = pygame.Surface(band.size, pygame.SRCALPHA)
                wash.fill((*COLOR_TIMER_AMBER, 50))
                self.screen.blit(wash, band.topleft)
                pygame.draw.rect(self.screen, self._mix(COLOR_TIMER_AMBER, COLOR_BG, 0.45), band, width=1, border_radius=0)
                pygame.draw.line(self.screen, COLOR_TIMER_AMBER, band.topleft, band.bottomleft, 3)
            self._draw_text(f"{row + 1:02d}", self.font_mono_small, (114, 114, 114), (pane.left + 14, line_y + 4))
            self._draw_text(text, self.font_mono_small, COLOR_TEXT_PRIMARY if matched else (189, 189, 189), (pane.left + 46, line_y + 4), max_width=pane.width - 60)
