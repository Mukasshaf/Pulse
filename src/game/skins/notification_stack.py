"""Simulation skin `notification_stack` for scenario `future_uncertainty_b`."""
from __future__ import annotations

import math

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_CARD_BG,
    COLOR_HAIRLINE,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_GREEN,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState


class NotificationStackSkin(UIComponents):
    """Renders the `notification_stack` decision skin."""

    def _draw_skin_notification_stack(
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
        """Render notification_stack simulation skin: minimalist lockscreen notification and 3 draft responses."""
        vx, vy = effects.vibration_offset
        jx, jy = effects.jitter_offset
        ox = vx + jx
        oy = vy + jy

        cx = self.width // 2 + ox

        # 1. Lockscreen Top Status Bar
        self._draw_text(
            "23:42",
            self.font_title,
            (219, 219, 219),
            (cx, 106 + oy),
            center=True,
        )
        self._draw_text(
            "Friday, September 19 • Midterm Assessment Period",
            self.font_small,
            (140, 140, 140),
            (cx, 134 + oy),
            center=True,
        )

        # Status icons (Right: Battery + Signal)
        stat_x = self.width - 140 + ox
        stat_y = 106 + oy
        # Battery outline
        pygame.draw.rect(self.screen, (150, 150, 150), (stat_x + 60, stat_y, 22, 12), width=1, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TIMER_GREEN, (stat_x + 62, stat_y + 2, 14, 8))
        pygame.draw.rect(self.screen, (150, 150, 150), (stat_x + 82, stat_y + 3, 2, 6))
        # Signal bars
        for b_i in range(4):
            bh = 4 + b_i * 3
            pygame.draw.rect(self.screen, (189, 189, 189), (stat_x + 36 + b_i * 5, stat_y + 12 - bh, 3, bh))

        # 2. Centered Sparse Notification Card
        card_w = 840
        card_h = 175
        notif_rect = pygame.Rect(cx - card_w // 2, 156 + oy, card_w, card_h)
        self._draw_card(notif_rect, border_color=COLOR_HAIRLINE, bg_color=COLOR_CARD_BG)

        # Card Header: Authority Seal + Sender
        seal_cx = notif_rect.left + 36
        seal_cy = notif_rect.top + 34
        pygame.draw.circle(self.screen, (42, 42, 42), (seal_cx, seal_cy), 18)
        pygame.draw.circle(self.screen, (167, 167, 167), (seal_cx, seal_cy), 18, width=2)
        pygame.draw.circle(self.screen, (167, 167, 167), (seal_cx, seal_cy), 14, width=1)
        star_pts = []
        for p_i in range(10):
            r_pt = 7 if p_i % 2 == 0 else 3.2
            ang = -math.pi / 2 + p_i * (math.pi / 5)
            star_pts.append((seal_cx + int(r_pt * math.cos(ang)), seal_cy + int(r_pt * math.sin(ang))))
        pygame.draw.polygon(self.screen, (167, 167, 167), star_pts)

        self._draw_text(
            "ACADEMIC EVALUATOR / SUPERVISOR",
            self.font_body,
            COLOR_TEXT_PRIMARY,
            (seal_cx + 28, notif_rect.top + 14),
        )
        self._draw_text(
            "FACULTY PORTAL • CONFIDENTIAL PERFORMANCE NOTICE",
            self.font_mono_small,
            (144, 144, 144),
            (seal_cx + 28, notif_rect.top + 38),
        )
        self._draw_text("Now • Priority Tier 1", self.font_small, COLOR_TIMER_AMBER, (notif_rect.right - 20, notif_rect.top + 26), midright=True)

        # Divider
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (notif_rect.left + 20, notif_rect.top + 68), (notif_rect.right - 20, notif_rect.top + 68), 1)

        # Content Message with prominent highlighted "? atypical ?"
        msg_y = notif_rect.top + 84
        prefix = "Your approach throughout this term has been... "
        atypical_str = "? atypical ?"
        suffix = " compared to your peers."

        pref_w = self.font_body.size(prefix)[0]
        atyp_w = self.font_title.size(atypical_str)[0]

        start_text_x = notif_rect.left + 24
        self._draw_text(prefix, self.font_body, (227, 227, 227), (start_text_x, msg_y + 4))

        # Cyan highlighted box for "? atypical ?"
        pill_rect = pygame.Rect(start_text_x + pref_w, msg_y - 2, atyp_w + 16, 36)
        pygame.draw.rect(self.screen, (28, 28, 28), pill_rect, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_ACCENT_CYAN, pill_rect, width=1, border_radius=0)
        self._draw_text(atypical_str, self.font_title, COLOR_ACCENT_CYAN, pill_rect.center, center=True)

        self._draw_text(suffix, self.font_body, (227, 227, 227), (pill_rect.right + 8, msg_y + 4))

        # Ambiguity Subtext Pill
        amb_tag = pygame.Rect(notif_rect.left + 24, notif_rect.bottom - 36, notif_rect.width - 48, 24)
        pygame.draw.rect(self.screen, (32, 32, 32), amb_tag, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TIMER_AMBER, amb_tag, width=1, border_radius=0)
        self._draw_text(
            "[ EVALUATOR INTENT UNRESOLVED: COMMENDATION VS. CRITIQUE FULLY INDETERMINATE ]",
            self.font_mono_small,
            COLOR_TIMER_AMBER,
            amb_tag.center,
            center=True,
        )

        # 3. Draft Responses: 3 Stacked Cards
        draft_header_y = notif_rect.bottom + 12
        self._draw_text(
            "SELECT DRAFT RESPONSE TO SUPERVISOR:",
            self.font_small,
            COLOR_TEXT_SECONDARY,
            (notif_rect.left, draft_header_y),
        )

        drafts = [
            (
                1,
                "Draft 1: Autonomous / Instinctive Orientation",
                '"I\'ve been approaching each task based on my instincts and what made sense to me."',
                "[ AUTONOMOUS ORIENTATION // REJECTS RUBRIC CONSTRAINTS ]",
                COLOR_ACCENT_CYAN,
                (33, 33, 33),
            ),
            (
                2,
                "Draft 2: Methodical / Deliberative Orientation",
                '"I\'ve been carefully considering each step before committing to anything."',
                "[ DELIBERATIVE CAUTION // ADHERES TO COMPLIANT REASONING ]",
                COLOR_TIMER_GREEN,
                (34, 34, 34),
            ),
            (
                3,
                "Draft 3: Critical / Non-Conformist Orientation",
                '"I don\'t think the standard approach was appropriate for what we were being asked to do."',
                "[ DIRECT CHALLENGE // QUESTIONS EVALUATION STANDARD ]",
                COLOR_TEXT_PRIMARY,
                (27, 27, 27),
            ),
        ]

        cards_start_y = draft_header_y + 22
        d_card_h = 92
        d_gap = 12

        for i, (key, label, quote, tag, accent_col, bg_col) in enumerate(drafts):
            dy = cards_start_y + i * (d_card_h + d_gap)
            d_rect = pygame.Rect(cx - card_w // 2, dy, card_w, d_card_h)

            is_sel = (selected_index == i)
            b_col = accent_col if is_sel else COLOR_HAIRLINE
            card_bg = bg_col if is_sel else COLOR_CARD_BG
            self._draw_card(d_rect, border_color=b_col, bg_color=card_bg)

            # Key Badge
            k_badge = pygame.Rect(d_rect.left + 14, d_rect.top + 14, 30, 30)
            self._draw_key_badge(k_badge, str(key), selected=is_sel)

            self._draw_text(label, self.font_body, accent_col if is_sel else COLOR_TEXT_PRIMARY, (k_badge.right + 14, d_rect.top + 10))
            quote_rect = pygame.Rect(k_badge.right + 14, d_rect.top + 34, d_rect.width - 80, 26)
            self._draw_wrapped_text(quote, self.font_small, (227, 227, 227) if is_sel else (179, 179, 179), quote_rect, center_v=True)

            # Bottom tag
            t_rect = pygame.Rect(k_badge.right + 14, d_rect.bottom - 24, 420, 18)
            pygame.draw.rect(self.screen, (32, 32, 32), t_rect, border_radius=0)
            pygame.draw.rect(self.screen, accent_col, t_rect, width=1, border_radius=0)
            self._draw_text(tag, self.font_mono_small, accent_col, t_rect.center, center=True, max_width=t_rect.width - 10)

            if is_sel:
                self._draw_text("[DISPATCHING DRAFT...]", self.font_mono_small, accent_col, (d_rect.right - 20, d_rect.top + 12), midright=True)

        # Bottom Prompt
        self._draw_text(
            "PRESS KEY [1], [2], OR [3] TO DISPATCH RESPONSE TO SUPERVISOR",
            self.font_small,
            (140, 140, 140),
            (self.width // 2, self.height - 20),
            center=True,
        )

        return True
