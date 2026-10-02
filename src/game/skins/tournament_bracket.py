"""Simulation skin `tournament_bracket` for scenario `risk_reward_a`."""
from __future__ import annotations

import math

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_BG,
    COLOR_CARD_BG,
    COLOR_HAIRLINE,
    COLOR_PRIMARY_ACTIVE,
    COLOR_PRIMARY_ROSSO,
    COLOR_SEMANTIC_WARNING,
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


class TournamentBracketSkin(UIComponents):
    """Renders the `tournament_bracket` decision skin."""

    def _draw_skin_tournament_bracket(
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
        """Render tournament_bracket simulation skin: tactical tournament dashboard, 3 strategy cards, incomplete info manipulation."""
        vx, vy = effects.vibration_offset
        jx, jy = effects.jitter_offset
        ox = vx + jx
        oy = vy + jy

        # 1 Hz gentle pulse for anticipatory somatic tension
        pulse_1hz = (math.sin(time_remaining_s * 2.0 * math.pi) + 1.0) / 2.0

        # 1. Header: Tactical tournament telemetry bar
        header_rect = pygame.Rect(50 + ox, 90 + oy, self.width - 100, 48)
        self._draw_card(header_rect, border_color=COLOR_HAIRLINE, bg_color=COLOR_CARD_BG)

        self._draw_text(
            "CURRENT DIVISION STANDING: TIER 1 BRACKET",
            self.font_title,
            COLOR_ACCENT_CYAN,
            (header_rect.left + 24, header_rect.centery),
            midleft=True,
        )

        # Telemetry badges in header
        self._draw_text("SEASON PLAYOFFS // MATCH 1 OF 1", self.font_small, COLOR_TEXT_SECONDARY, (header_rect.right - 260, header_rect.centery), midright=True)
        self._draw_text("[DECISION TIME CRITICAL]", self.font_small, COLOR_TIMER_AMBER, (header_rect.right - 24, header_rect.centery), midright=True)

        # 2. Three Strategy Cards Side-by-Side
        cw = 370
        ch = 475
        gap = 25
        total_w = 3 * cw + 2 * gap
        start_x = (self.width - total_w) // 2 + ox
        card_y = 150 + oy

        # -------------------------------------------------------------
        # Card 1: Strategy Alpha (Safe Approach)
        # -------------------------------------------------------------
        c1_rect = pygame.Rect(start_x, card_y, cw, ch)
        is_sel1 = (selected_index == 0)
        border1 = COLOR_TIMER_GREEN if is_sel1 else (COLOR_TIMER_GREEN if selected_index is None else COLOR_HAIRLINE)
        bg1 = (34, 34, 34) if is_sel1 else (28, 28, 28)
        self._draw_card(c1_rect, border_color=border1, bg_color=bg1)

        # Card header badge
        k1_badge = pygame.Rect(c1_rect.left + 16, c1_rect.top + 16, 36, 36)
        self._draw_key_badge(k1_badge, "1", selected=is_sel1)

        self._draw_text("Strategy Alpha", self.font_body, COLOR_TIMER_GREEN if is_sel1 else COLOR_TEXT_PRIMARY, (k1_badge.right + 14, c1_rect.top + 12))
        self._draw_text("CONSERVATIVE PROTOCOL", self.font_small, COLOR_TIMER_GREEN, (k1_badge.right + 14, c1_rect.top + 38))

        # Projected gain box
        box1 = pygame.Rect(c1_rect.left + 16, c1_rect.top + 68, cw - 32, 64)
        pygame.draw.rect(self.screen, (28, 28, 28), box1, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TIMER_GREEN, box1, width=1, border_radius=0)
        self._draw_text("+8% AVG", self.font_hero, COLOR_TIMER_GREEN, (box1.centerx, box1.top + 22), center=True)
        self._draw_text("Projected Round Gain", self.font_small, (156, 156, 156), (box1.centerx, box1.top + 52), center=True)

        # Variance metric
        self._draw_text("Variance: LOW (σ = ±1.5%)", self.font_small, (173, 173, 173), (c1_rect.left + 16, c1_rect.top + 140))
        var_bar1 = pygame.Rect(c1_rect.left + 16, c1_rect.top + 164, cw - 32, 8)
        pygame.draw.rect(self.screen, (32, 32, 32), var_bar1, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TIMER_GREEN, (var_bar1.left, var_bar1.top, int(var_bar1.width * 0.92), var_bar1.height), border_radius=0)

        # Historical Telemetry Bars (6/6 complete & verified)
        self._draw_text("HISTORICAL TELEMETRY (6 ROUNDS)", self.font_small, COLOR_TEXT_SECONDARY, (c1_rect.left + 16, c1_rect.top + 184))
        chart_w = (cw - 32)
        bar_w = (chart_w - 5 * 8) // 6
        chart_base_y = c1_rect.top + 285
        r1_vals = [8, 9, 7, 8, 9, 8]
        for idx, val in enumerate(r1_vals):
            bx = c1_rect.left + 16 + idx * (bar_w + 8)
            bh = int(val * 4.5)
            by = chart_base_y - bh
            pygame.draw.rect(self.screen, COLOR_TIMER_GREEN, (bx, by, bar_w, bh), border_radius=0)
            self._draw_text(f"R{idx+1}", self.font_small, (133, 133, 133), (bx + bar_w // 2, chart_base_y + 10), center=True)

        # Verified audit tag
        audit_tag = pygame.Rect(c1_rect.left + 16, c1_rect.top + 325, cw - 32, 38)
        pygame.draw.rect(self.screen, (35, 35, 35), audit_tag, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TIMER_GREEN, audit_tag, width=1, border_radius=0)
        self._draw_text("[OK] 6/6 ROUNDS AUDITED & VERIFIED", self.font_small, COLOR_TIMER_GREEN, audit_tag.center, center=True)

        # Risk rating & description
        self._draw_text("Risk Profile: 1 / 10 (Predictable)", self.font_small, (159, 159, 159), (c1_rect.left + 16, c1_rect.top + 380))
        desc1_rect = pygame.Rect(c1_rect.left + 16, c1_rect.top + 404, cw - 32, 45)
        self._draw_wrapped_text("Guaranteed gain. Zero downside exposure.", self.font_small, COLOR_TEXT_SECONDARY, desc1_rect, spacing=2)

        # -------------------------------------------------------------
        # Card 2: Strategy Beta (Aggressive Approach, 2 rounds missing)
        # -------------------------------------------------------------
        c2_rect = pygame.Rect(start_x + cw + gap, card_y, cw, ch)
        is_sel2 = (selected_index == 1)
        border2 = COLOR_TIMER_AMBER if is_sel2 else (COLOR_TIMER_AMBER if selected_index is None else COLOR_HAIRLINE)
        bg2 = (33, 33, 33) if is_sel2 else (28, 28, 28)
        self._draw_card(c2_rect, border_color=border2, bg_color=bg2)

        k2_badge = pygame.Rect(c2_rect.left + 16, c2_rect.top + 16, 36, 36)
        self._draw_key_badge(k2_badge, "2", selected=is_sel2)

        self._draw_text("Strategy Beta", self.font_body, COLOR_TIMER_AMBER if is_sel2 else COLOR_TEXT_PRIMARY, (k2_badge.right + 14, c2_rect.top + 12))
        self._draw_text("AGGRESSIVE PROTOCOL", self.font_small, COLOR_TIMER_AMBER, (k2_badge.right + 14, c2_rect.top + 38))

        # Projected gain box
        box2 = pygame.Rect(c2_rect.left + 16, c2_rect.top + 68, cw - 32, 64)
        pygame.draw.rect(self.screen, (28, 28, 28), box2, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TIMER_AMBER, box2, width=1, border_radius=0)
        self._draw_text("+22% AVG", self.font_hero, COLOR_TIMER_AMBER, (box2.centerx, box2.top + 22), center=True)
        self._draw_text("Projected Round Gain", self.font_small, (163, 163, 163), (box2.centerx, box2.top + 52), center=True)

        # Variance metric
        self._draw_text("Variance: HIGH (σ = ±14.2%)", self.font_small, (173, 173, 173), (c2_rect.left + 16, c2_rect.top + 140))
        var_bar2 = pygame.Rect(c2_rect.left + 16, c2_rect.top + 164, cw - 32, 8)
        pygame.draw.rect(self.screen, (32, 32, 32), var_bar2, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TIMER_AMBER, (var_bar2.left, var_bar2.top, int(var_bar2.width * 0.52), var_bar2.height), border_radius=0)

        # Historical Telemetry Bars (4 verified, 2 missing/untracked)
        self._draw_text("HISTORICAL TELEMETRY (4/6 ROUNDS)", self.font_small, COLOR_TEXT_SECONDARY, (c2_rect.left + 16, c2_rect.top + 184))
        r2_vals = [18, 26, 20, 24]
        for idx in range(6):
            bx = c2_rect.left + 16 + idx * (bar_w + 8)
            if idx < 4:
                bh = int(r2_vals[idx] * 2.2)
                by = chart_base_y - bh
                pygame.draw.rect(self.screen, COLOR_TIMER_AMBER, (bx, by, bar_w, bh), border_radius=0)
            else:
                # Corrupted / Missing bar with hatched border
                pygame.draw.rect(self.screen, (29, 29, 29), (bx, chart_base_y - 45, bar_w, 45), border_radius=0)
                pygame.draw.rect(self.screen, self._mix(COLOR_TIMER_AMBER, COLOR_BG, 0.4), (bx, chart_base_y - 45, bar_w, 45), width=1, border_radius=0)
                self._draw_text("?", self.font_body, COLOR_TIMER_AMBER, (bx + bar_w // 2, chart_base_y - 25), center=True)
            self._draw_text(f"R{idx+1}", self.font_small, (133, 133, 133), (bx + bar_w // 2, chart_base_y + 10), center=True)

        # Pulsing caution tag: "[ 2 ROUNDS UNTRACKED ]" (1 Hz pulse between dimmed and full yellow)
        amber_pulse_col = self._mix(COLOR_TIMER_AMBER, COLOR_BG, 0.3 * (1.0 - pulse_1hz))
        tag_level = int(30 + 14 * pulse_1hz)
        amber_tag_bg = (tag_level, tag_level, tag_level)

        tag2 = pygame.Rect(c2_rect.left + 16, c2_rect.top + 325, cw - 32, 38)
        pygame.draw.rect(self.screen, amber_tag_bg, tag2, border_radius=0)
        pygame.draw.rect(self.screen, amber_pulse_col, tag2, width=1, border_radius=0)
        self._draw_text("[ 2 ROUNDS UNTRACKED ]", self.font_small, amber_pulse_col, tag2.center, center=True)

        # Risk rating & description
        self._draw_text("Risk Profile: 6 / 10 (Moderate Volatility)", self.font_small, (159, 159, 159), (c2_rect.left + 16, c2_rect.top + 380))
        desc2_rect = pygame.Rect(c2_rect.left + 16, c2_rect.top + 404, cw - 32, 45)
        self._draw_wrapped_text("Higher payout, but latent unhedged loss probability.", self.font_small, COLOR_TEXT_SECONDARY, desc2_rect, spacing=2)

        # -------------------------------------------------------------
        # Card 3: Strategy Gamma (Experimental, 4 rounds missing)
        # -------------------------------------------------------------
        c3_rect = pygame.Rect(start_x + (cw + gap) * 2, card_y, cw, ch)
        is_sel3 = (selected_index == 2)
        border3 = COLOR_TIMER_RED if is_sel3 else (COLOR_TIMER_RED if selected_index is None else COLOR_HAIRLINE)
        bg3 = (29, 29, 29) if is_sel3 else (28, 28, 28)
        self._draw_card(c3_rect, border_color=border3, bg_color=bg3)

        k3_badge = pygame.Rect(c3_rect.left + 16, c3_rect.top + 16, 36, 36)
        self._draw_key_badge(k3_badge, "3", selected=is_sel3)

        self._draw_text("Strategy Gamma", self.font_body, COLOR_TIMER_RED if is_sel3 else COLOR_TEXT_PRIMARY, (k3_badge.right + 14, c3_rect.top + 12))
        self._draw_text("EXPERIMENTAL HIGH-YIELD", self.font_small, COLOR_SEMANTIC_WARNING, (k3_badge.right + 14, c3_rect.top + 38))

        # Projected gain box
        box3 = pygame.Rect(c3_rect.left + 16, c3_rect.top + 68, cw - 32, 64)
        pygame.draw.rect(self.screen, (28, 28, 28), box3, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_PRIMARY_ROSSO, box3, width=1, border_radius=0)
        self._draw_text("+45% AVG", self.font_hero, COLOR_PRIMARY_ROSSO, (box3.centerx, box3.top + 22), center=True)
        self._draw_text("Projected Round Gain", self.font_small, (161, 161, 161), (box3.centerx, box3.top + 52), center=True)

        # Variance metric
        self._draw_text("Variance: EXTREME (σ = ±38.0%)", self.font_small, (173, 173, 173), (c3_rect.left + 16, c3_rect.top + 140))
        var_bar3 = pygame.Rect(c3_rect.left + 16, c3_rect.top + 164, cw - 32, 8)
        pygame.draw.rect(self.screen, (32, 32, 32), var_bar3, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TIMER_RED, (var_bar3.left, var_bar3.top, int(var_bar3.width * 0.18), var_bar3.height), border_radius=0)

        # Historical Telemetry Bars (2 verified, 4 missing/untracked)
        self._draw_text("HISTORICAL TELEMETRY (2/6 ROUNDS)", self.font_small, COLOR_TEXT_SECONDARY, (c3_rect.left + 16, c3_rect.top + 184))
        r3_vals = [44, 46]
        for idx in range(6):
            bx = c3_rect.left + 16 + idx * (bar_w + 8)
            if idx < 2:
                bh = int(r3_vals[idx] * 1.5)
                by = chart_base_y - bh
                pygame.draw.rect(self.screen, COLOR_TIMER_RED, (bx, by, bar_w, bh), border_radius=0)
            else:
                # Corrupted / Missing bar with a dimmed Rosso outline
                pygame.draw.rect(self.screen, (24, 24, 24), (bx, chart_base_y - 55, bar_w, 55), border_radius=0)
                pygame.draw.rect(self.screen, COLOR_PRIMARY_ACTIVE, (bx, chart_base_y - 55, bar_w, 55), width=1, border_radius=0)
                self._draw_text("!", self.font_body, COLOR_SEMANTIC_WARNING, (bx + bar_w // 2, chart_base_y - 30), center=True)
            self._draw_text(f"R{idx+1}", self.font_small, (133, 133, 133), (bx + bar_w // 2, chart_base_y + 10), center=True)

        # Blinking Warning Tag: "[ 4 ROUNDS UNTRACKED — EXTREME VARIANCE ]" (1 Hz pulse)
        blink_on = pulse_1hz > 0.35
        red_blink_col = COLOR_TIMER_RED if blink_on else COLOR_PRIMARY_ACTIVE
        red_tag_bg = (24, 24, 24) if blink_on else (16, 16, 16)

        tag3 = pygame.Rect(c3_rect.left + 16, c3_rect.top + 325, cw - 32, 38)
        pygame.draw.rect(self.screen, red_tag_bg, tag3, border_radius=0)
        pygame.draw.rect(self.screen, red_blink_col, tag3, width=1, border_radius=0)
        self._draw_text("[ 4 ROUNDS UNTRACKED — EXTREME VARIANCE ]", self.font_small, red_blink_col, tag3.center, center=True, max_width=tag3.width - 16)

        # Risk rating & description
        self._draw_text("Risk Profile: 9.5 / 10 (Critical Downside)", self.font_small, COLOR_SEMANTIC_WARNING, (c3_rect.left + 16, c3_rect.top + 380))
        desc3_rect = pygame.Rect(c3_rect.left + 16, c3_rect.top + 404, cw - 32, 45)
        self._draw_wrapped_text("Massive potential gain, but catastrophic ranking drop risk.", self.font_small, COLOR_TEXT_SECONDARY, desc3_rect, spacing=2)

        # 3. Bottom Prompt
        self._draw_text(
            "SELECT STRATEGY [1], [2], OR [3] TO COMMIT TOURNAMENT ROSTER",
            self.font_small,
            (140, 140, 140),
            (self.width // 2, self.height - 35),
            center=True,
        )

        return True
