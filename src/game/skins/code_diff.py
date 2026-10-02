"""Simulation skin `code_diff` for scenario `rule_ambiguity_b`."""
from __future__ import annotations

import math

import pygame

from src.game.constants import (
    COLOR_BG,
    COLOR_CARD_BG,
    COLOR_HAIRLINE,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_GREEN,
    COLOR_TIMER_RED,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState


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
        vx, vy = effects.vibration_offset
        jx, jy = effects.jitter_offset
        ox = vx + jx
        oy = vy + jy

        # 1. Stakes Callout Top Banner
        banner_w = self.width - 100
        banner_h = 44
        banner_rect = pygame.Rect(50 + ox, 90 + oy, banner_w, banner_h)
        self._draw_card(banner_rect, border_color=COLOR_TIMER_AMBER, bg_color=COLOR_BG)

        # Warning icon/pulse: the caution yellow dims toward the canvas and back (about 0.5 Hz)
        warn_pulse = (math.sin(time_remaining_s * 3.0) + 1.0) / 2.0
        warn_col = self._mix(COLOR_TIMER_AMBER, COLOR_BG, 0.22 * (1.0 - warn_pulse))
        tri_pts = [
            (banner_rect.left + 24, banner_rect.centery - 10),
            (banner_rect.left + 14, banner_rect.centery + 8),
            (banner_rect.left + 34, banner_rect.centery + 8),
        ]
        pygame.draw.polygon(self.screen, warn_col, tri_pts)
        self._draw_text("!", self.font_small, (20, 20, 20), (banner_rect.left + 24, banner_rect.centery + 1), center=True)
        self._draw_text("INTEGRITY CHECK: 38% UNATTRIBUTED OVERLAP IDENTIFIED", self.font_body, warn_col, (banner_rect.left + 46, banner_rect.centery), midleft=True)
        self._draw_text("[PLAGIARISM FLAGGED: SENIOR REPO MATCH]", self.font_small, COLOR_TIMER_RED, (banner_rect.right - 20, banner_rect.centery), midright=True)

        # 2. Dual-Pane Code Diff Container
        diff_top = 144 + oy
        diff_h = 320
        gap = 18
        half_w = (banner_w - gap) // 2

        left_diff = pygame.Rect(50 + ox, diff_top, half_w, diff_h)
        right_diff = pygame.Rect(50 + ox + half_w + gap, diff_top, half_w, diff_h)

        # Pane Header Bars
        pane_hdr_h = 32
        left_hdr = pygame.Rect(left_diff.left, left_diff.top, half_w, pane_hdr_h)
        right_hdr = pygame.Rect(right_diff.left, right_diff.top, half_w, pane_hdr_h)

        # Left Diff Pane (Current Project Submission)
        pygame.draw.rect(self.screen, (24, 24, 24), left_diff, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, left_diff, width=1, border_radius=0)
        pygame.draw.rect(self.screen, (36, 36, 36), left_hdr, border_top_left_radius=0, border_top_right_radius=0)
        self._draw_text("CURRENT PROJECT SUBMISSION: src/core/engine.py (Your Group)", self.font_small, (214, 214, 214), (left_hdr.left + 14, left_hdr.centery), midleft=True)

        # Right Diff Pane (Uncredited Archived Repository)
        pygame.draw.rect(self.screen, (24, 24, 24), right_diff, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, right_diff, width=1, border_radius=0)
        pygame.draw.rect(self.screen, (36, 36, 36), right_hdr, border_top_left_radius=0, border_top_right_radius=0)
        self._draw_text("UNCREDITED ARCHIVED REPOSITORY: repo_2022_grad/core.py (Senior Alumni)", self.font_small, COLOR_TIMER_AMBER, (right_hdr.left + 14, right_hdr.centery), midleft=True)

        # Code lines to render
        left_code = [
            ("01", "class OptimizationEngine:"),
            ("02", "    def __init__(self, weights: list[float]):"),
            ("03", "        self.tensor_map = compute_latent_graph(weights)   # MATCH"),
            ("04", "        self.matrix_delta = decompose_svd_fast(weights)   # MATCH"),
            ("05", "        self.gradient_cache = [0.0] * len(weights)        # MATCH"),
            ("06", "    def step_optimizer(self, lr: float):"),
            ("07", "        return execute_forward_pass(self.tensor_map, lr)"),
            ("08", "        # End of implementation block"),
        ]

        right_code = [
            ("01", "class LegacyPipelineRunner:"),
            ("02", "    def __init__(self, weights: list[float]):"),
            ("03", "        self.tensor_map = compute_latent_graph(weights)   # MATCH"),
            ("04", "        self.matrix_delta = decompose_svd_fast(weights)   # MATCH"),
            ("05", "        self.gradient_cache = [0.0] * len(weights)        # MATCH"),
            ("06", "    def run_iteration(self, rate: float):"),
            ("07", "        return execute_forward_pass(self.tensor_map, rate)"),
            ("08", "        # Archived under CC-BY-NC 2022"),
        ]

        # Overlapping match lines 03-05 sit on a translucent caution-yellow band with a solid left rule
        line_start_y = left_diff.top + pane_hdr_h + 8
        line_h = 32
        match_fill = (*COLOR_TIMER_AMBER, 50)
        match_edge = self._mix(COLOR_TIMER_AMBER, COLOR_BG, 0.45)
        for pane, code_lines in ((left_diff, left_code), (right_diff, right_code)):
            for l_idx, (num, code_text) in enumerate(code_lines):
                ly = line_start_y + l_idx * line_h
                is_match = l_idx in (2, 3, 4)
                if is_match:
                    match_rect = pygame.Rect(pane.left + 4, ly - 2, half_w - 8, line_h - 2)
                    alpha_box = pygame.Surface((match_rect.width, match_rect.height), pygame.SRCALPHA)
                    pygame.draw.rect(alpha_box, match_fill, (0, 0, match_rect.width, match_rect.height), border_radius=0)
                    self.screen.blit(alpha_box, match_rect.topleft)
                    pygame.draw.rect(self.screen, match_edge, match_rect, width=1, border_radius=0)
                    pygame.draw.line(self.screen, COLOR_TIMER_AMBER, (match_rect.left, match_rect.top), (match_rect.left, match_rect.bottom), 3)

                self._draw_text(num, self.font_mono_small, (114, 114, 114), (pane.left + 14, ly + 4))
                code_col = COLOR_TEXT_PRIMARY if is_match else (189, 189, 189)
                self._draw_text(code_text, self.font_mono_small, code_col, (pane.left + 46, ly + 4), max_width=half_w - 60)

        # 3. Decision Options: Three Cards Below
        cards_y = diff_top + diff_h + 14
        card_w = (banner_w - 2 * 20) // 3
        card_h = 160

        diff_opts = [
            (
                1,
                "Remove Borrowed Sections",
                "Remove Sections / Accept Delay",
                "Scrub senior code & accept timeline delay before submission.",
                "[ SECTIONS REMOVED // TIMELINE HIT ]",
                COLOR_TIMER_GREEN,
                (32, 32, 32),
            ),
            (
                2,
                "Keep & Add Acknowledgement",
                "Credit Source / Integrity Risk",
                "Add formal credit in comments. Submits on time; board reviews.",
                "[ TIMELINE KEPT // AUDIT RISK ]",
                COLOR_TIMER_AMBER,
                (33, 33, 33),
            ),
            (
                3,
                "Contact Senior for Consent",
                "Formal Permission / Uncertainty",
                "Request authorization from alumni. Submissions frozen pending response.",
                "[ FORMAL CONSENT // UNCERTAIN ]",
                COLOR_TEXT_PRIMARY,
                (27, 27, 27),
            ),
        ]

        for i, (key, title, subtitle, desc, tag, accent_col, bg_col) in enumerate(diff_opts):
            cx = 50 + ox + i * (card_w + 20)
            c_rect = pygame.Rect(cx, cards_y, card_w, card_h)

            is_sel = (selected_index == i)
            border_col = accent_col if is_sel else COLOR_HAIRLINE
            card_bg = bg_col if is_sel else COLOR_CARD_BG
            self._draw_card(c_rect, border_color=border_col, bg_color=card_bg)

            # Key Badge
            k_badge = pygame.Rect(c_rect.left + 14, c_rect.top + 14, 32, 32)
            self._draw_key_badge(k_badge, str(key), selected=is_sel)

            self._draw_text(title, self.font_body, accent_col if is_sel else COLOR_TEXT_PRIMARY, (k_badge.right + 12, c_rect.top + 12))
            self._draw_text(subtitle, self.font_small, (160, 160, 160), (k_badge.right + 12, c_rect.top + 34))

            # Description wrapped
            text_rect = pygame.Rect(c_rect.left + 14, c_rect.top + 58, c_rect.width - 28, 55)
            self._draw_wrapped_text(desc, self.font_small, COLOR_TEXT_SECONDARY, text_rect, spacing=4, center_v=True)

            # Tag pill
            tag_rect = pygame.Rect(c_rect.left + 14, c_rect.bottom - 30, c_rect.width - 28, 22)
            pygame.draw.rect(self.screen, (32, 32, 32), tag_rect, border_radius=0)
            pygame.draw.rect(self.screen, accent_col, tag_rect, width=1, border_radius=0)
            self._draw_text(tag, self.font_small, accent_col, tag_rect.center, center=True)

        # Bottom Prompt
        self._draw_text(
            "PRESS KEY [1], [2], OR [3] TO COMMIT CODE INTEGRITY DECISION",
            self.font_small,
            (140, 140, 140),
            (self.width // 2, self.height - 24),
            center=True,
        )

        return True
