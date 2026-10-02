"""Simulation skin `document_workspace` for scenario `impulsivity_gratification_b`."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_BG,
    COLOR_CARD_BG,
    COLOR_HAIRLINE,
    COLOR_HAIRLINE_SUBTLE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_GREEN,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState


class DocumentWorkspaceSkin(UIComponents):
    """Renders the `document_workspace` decision skin."""

    def _draw_skin_document_workspace(
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
        """Render document_workspace simulation skin: assignment editor, simulated text lines, word count, decision cards."""
        vx, vy = effects.vibration_offset
        jx, jy = effects.jitter_offset
        ox = vx + jx
        oy = vy + jy

        # 1. Main Document Editor Window
        win_w = 920
        win_h = 425
        win_rect = pygame.Rect(self.width // 2 - win_w // 2 + ox, 90 + oy, win_w, win_h)

        # Window Frame Background & Border
        pygame.draw.rect(self.screen, (28, 28, 28), win_rect, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, win_rect, width=1, border_radius=0)

        # Window Title Bar (Header)
        hdr_h = 36
        hdr_rect = pygame.Rect(win_rect.left, win_rect.top, win_w, hdr_h)
        pygame.draw.rect(self.screen, (30, 30, 30), hdr_rect, border_top_left_radius=0, border_top_right_radius=0)
        pygame.draw.line(self.screen, (48, 48, 48), (win_rect.left, hdr_rect.bottom), (win_rect.right, hdr_rect.bottom), 1)

        # Window controls: neutral square outlines (no OS-specific traffic-light colours)
        for ctl_x in (win_rect.left + 20, win_rect.left + 36, win_rect.left + 52):
            pygame.draw.rect(self.screen, COLOR_HAIRLINE_SUBTLE, (ctl_x - 4, hdr_rect.centery - 4, 9, 9), width=1, border_radius=0)

        # Document Title in header
        self._draw_text(
            "Term_Paper_Final_Draft_v4.docx — Assignment Editor",
            self.font_small,
            COLOR_TEXT_PRIMARY,
            (win_rect.centerx, hdr_rect.centery),
            center=True,
        )
        self._draw_text("[Auto-Saved]", self.font_small, (123, 123, 123), (win_rect.right - 20, hdr_rect.centery), midright=True)

        # Menu / Formatting Ribbon
        ribbon_rect = pygame.Rect(win_rect.left, hdr_rect.bottom, win_w, 28)
        pygame.draw.rect(self.screen, (24, 24, 24), ribbon_rect)
        pygame.draw.line(self.screen, (48, 48, 48), (win_rect.left, ribbon_rect.bottom), (win_rect.right, ribbon_rect.bottom), 1)
        self._draw_text(
            "File    Edit    View    Insert    Format    Tools    Extensions    Help",
            self.font_small,
            (134, 134, 134),
            (win_rect.left + 24, ribbon_rect.centery),
            midleft=True,
        )

        # 2. Document Page Surface (Canvas)
        canvas_rect = pygame.Rect(win_rect.left + 24, ribbon_rect.bottom + 12, win_w - 48, win_h - 115)
        paper_col = (244, 244, 244)
        pygame.draw.rect(self.screen, paper_col, canvas_rect, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, canvas_rect, width=1, border_radius=0)

        # Margins inside document
        margin_x = canvas_rect.left + 45
        margin_w = canvas_rect.width - 90

        # Document Header / Assignment Title
        self._draw_text(
            "An Empirical Investigation of Delayed Rewards & Cognitive Self-Regulation",
            self.font_body,
            (32, 32, 32),
            (margin_x, canvas_rect.top + 16),
        )
        self._draw_text(
            "Course: Behavioral Neuroscience (PSYC-340)  |  Draft Revision: 4.2",
            self.font_small,
            COLOR_TEXT_MUTED,
            (margin_x, canvas_rect.top + 40),
        )
        pygame.draw.line(self.screen, (210, 210, 210), (margin_x, canvas_rect.top + 58), (canvas_rect.right - 45, canvas_rect.top + 58), 1)

        # Simulated Text Lines (horizontal gray bars)
        p1_lines = [
            (0, 1.0),
            (14, 0.96),
            (28, 0.98),
            (42, 0.72),
        ]
        base_y1 = canvas_rect.top + 70
        for dy, frac in p1_lines:
            pygame.draw.rect(
                self.screen,
                (190, 190, 190),
                (margin_x, base_y1 + dy, int(margin_w * frac), 7),
                border_radius=0,
            )

        # Paragraph 2 with revision highlight (caution yellow washed into the paper)
        base_y2 = base_y1 + 68
        pygame.draw.rect(
            self.screen,
            self._mix(COLOR_TIMER_AMBER, paper_col, 0.72),
            (margin_x - 4, base_y2 - 3, int(margin_w * 0.70), 38),
            border_radius=0,
        )
        p2_lines = [
            (0, 0.68),
            (14, 0.65),
            (28, 0.50),
        ]
        for dy, frac in p2_lines:
            pygame.draw.rect(
                self.screen,
                (155, 155, 155),
                (margin_x, base_y2 + dy, int(margin_w * frac), 7),
                border_radius=0,
            )

        # Revision tag bubble in right margin (safely anchored inside canvas right border)
        rev_tag_rect = pygame.Rect(canvas_rect.right - 185, base_y2 + 2, 170, 26)
        pygame.draw.rect(self.screen, self._mix(COLOR_TIMER_AMBER, paper_col, 0.85), rev_tag_rect, border_radius=0)
        pygame.draw.rect(self.screen, self._mix(COLOR_TIMER_AMBER, COLOR_BG, 0.35), rev_tag_rect, width=1, border_radius=0)
        self._draw_text("[Unsaved Edits: Rev 4.2]", self.font_small, COLOR_BG, rev_tag_rect.center, center=True)

        # Paragraph 3
        base_y3 = base_y2 + 50
        p3_lines = [
            (0, 0.97),
            (14, 0.88),
            (28, 0.40),
        ]
        for dy, frac in p3_lines:
            pygame.draw.rect(
                self.screen,
                (190, 190, 190),
                (margin_x, base_y3 + dy, int(margin_w * frac), 7),
                border_radius=0,
            )

        # 3. Document Editor Bottom Status Bar
        status_h = 30
        status_rect = pygame.Rect(win_rect.left, win_rect.bottom - status_h, win_w, status_h)
        pygame.draw.rect(self.screen, (28, 28, 28), status_rect, border_bottom_left_radius=0, border_bottom_right_radius=0)
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (win_rect.left, status_rect.top), (win_rect.right, status_rect.top), 1)

        self._draw_text(
            "Words: 3,420    |    Characters: 21,850    |    Page 6 of 6",
            self.font_small,
            COLOR_TEXT_SECONDARY,
            (status_rect.left + 24, status_rect.centery),
            midleft=True,
        )
        self._draw_text(
            "Status: Draft Quality 'Adequate' (Grade B+)    |    [OK] Citations Checked",
            self.font_small,
            COLOR_ACCENT_CYAN,
            (status_rect.right - 24, status_rect.centery),
            midright=True,
        )

        # 4. Decision Split: Option 1 vs Option 2
        card_y = self.height - 110 + oy
        card_h = 86
        card_w = 460

        opts = scenario.options
        for i in range(min(2, len(opts))):
            opt = opts[i]
            rx = self.width // 2 - card_w - 15 + ox if i == 0 else self.width // 2 + 15 + ox
            r = pygame.Rect(rx, card_y, card_w, card_h)
            is_sel = (selected_index == i)

            if i == 0:
                tag_label = "SUBMIT NOW (GUARANTEED ADEQUATE)"
                tag_col = COLOR_TIMER_GREEN
            else:
                tag_label = "REQUEST EXTENDED REVIEW (HIGH RISK)"
                tag_col = COLOR_TIMER_AMBER
            # Accent border while undecided or chosen; the unchosen card falls back to a neutral hairline
            border_col = tag_col if (is_sel or selected_index is None) else COLOR_HAIRLINE_SUBTLE
            bg_col = (40, 40, 40) if is_sel else COLOR_CARD_BG

            self._draw_card(r, border_color=border_col, bg_color=bg_col)

            k_badge = pygame.Rect(r.left + 14, r.centery - 18, 36, 36)
            self._draw_key_badge(k_badge, str(opt.key), selected=is_sel)

            self._draw_text(tag_label, self.font_small, tag_col if is_sel else (189, 189, 189), (k_badge.right + 14, r.top + 10))
            text_rect = pygame.Rect(k_badge.right + 14, r.top + 32, r.width - 85, r.height - 38)
            self._draw_wrapped_text(opt.text, self.font_body, COLOR_TEXT_PRIMARY, text_rect, spacing=2, center_v=True)

        return True
