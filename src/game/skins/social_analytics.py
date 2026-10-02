"""Simulation skin `social_analytics` for scenario `risk_reward_b`."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_BG,
    COLOR_CARD_BG,
    COLOR_HAIRLINE,
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


class SocialAnalyticsSkin(UIComponents):
    """Renders the `social_analytics` decision skin."""

    def _draw_skin_social_analytics(
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
        """Render social_analytics simulation skin: creator studio, reach meter, suspension risk gauge, BART controls."""
        if bart_runner is None:
            return False

        vx, vy = effects.vibration_offset
        jx, jy = effects.jitter_offset
        ox = vx + jx
        oy = vy + jy

        pump_count = bart_runner.pump_count
        reach_value = bart_runner.current_value
        max_pumps = bart_runner.config.max_pumps
        instability = bart_runner.get_instability_fraction()
        is_burst = bart_runner.is_burst

        # 1. Top Navigation Bar (Creator Studio)
        nav_rect = pygame.Rect(50 + ox, 90 + oy, self.width - 100, 44)
        self._draw_card(nav_rect, border_color=COLOR_HAIRLINE, bg_color=COLOR_CARD_BG)

        # Live feed indicator
        pygame.draw.circle(self.screen, COLOR_TIMER_RED, (nav_rect.left + 22, nav_rect.centery), 5)
        self._draw_text("LIVE CAMPAIGN", self.font_small, COLOR_TIMER_RED, (nav_rect.left + 36, nav_rect.centery), midleft=True)
        self._draw_text(
            "CREATOR STUDIO // VIRAL FEED REACH ANALYTICS",
            self.font_small,
            COLOR_TEXT_PRIMARY,
            (nav_rect.left + 160, nav_rect.centery),
            midleft=True,
        )
        self._draw_text("Target Audience: General Feed", self.font_small, (140, 140, 140), (nav_rect.right - 24, nav_rect.centery), midright=True)

        # 2. Main Creator Studio Analytics Panel
        panel_w = 920
        panel_h = 280
        panel_rect = pygame.Rect(self.width // 2 - panel_w // 2 + ox, 150 + oy, panel_w, panel_h)
        self._draw_card(panel_rect, border_color=COLOR_HAIRLINE, bg_color=COLOR_CARD_BG)

        # Audience Reach Meter (Large Dynamic Counter)
        self._draw_text(
            "ACCUMULATED AUDIENCE REACH (IMPRESSIONS)",
            self.font_small,
            COLOR_TEXT_SECONDARY,
            (panel_rect.centerx, panel_rect.top + 24),
            center=True,
        )

        reach_str = f"+{reach_value:,}" if not is_burst else "0"
        reach_color = COLOR_ACCENT_CYAN if not is_burst else COLOR_TIMER_RED
        self._draw_text(reach_str, self.font_hero, reach_color, (panel_rect.centerx, panel_rect.top + 62), center=True)

        # Metric badges directly below counter
        badge_y = panel_rect.top + 106
        viral_tier = min(5, 1 + pump_count // 3)
        self._draw_text(f"VIRAL VELOCITY: TIER {viral_tier}", self.font_small, COLOR_ACCENT_CYAN, (panel_rect.centerx - 200, badge_y), center=True)
        self._draw_text(f"POST ESCALATION: {pump_count} / {max_pumps} CYCLES", self.font_small, (169, 169, 169), (panel_rect.centerx + 200, badge_y), center=True)

        # Horizontal Report Risk Gauge: "Content Flag & Suspension Risk"
        gauge_w = 760
        gauge_h = 24
        gauge_x = panel_rect.centerx - gauge_w // 2
        gauge_y = panel_rect.top + 160

        self._draw_text(
            "Content Flag & Suspension Risk",
            self.font_small,
            COLOR_TEXT_SECONDARY,
            (gauge_x, gauge_y - 20),
        )

        risk_pct = int(instability * 100)
        risk_color = COLOR_TIMER_GREEN if instability < 0.4 else (COLOR_TIMER_AMBER if instability < 0.75 else COLOR_TIMER_RED)
        self._draw_text(
            f"{risk_pct}% RISK LEVEL",
            self.font_small,
            risk_color,
            (gauge_x + gauge_w, gauge_y - 10),
            midright=True,
        )

        # Gauge track
        pygame.draw.rect(self.screen, (32, 32, 32), (gauge_x, gauge_y, gauge_w, gauge_h), border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, (gauge_x, gauge_y, gauge_w, gauge_h), width=1, border_radius=0)

        # Fill bar
        fill_w = max(0, min(gauge_w - 4, int((gauge_w - 4) * instability)))
        if fill_w > 4:
            pygame.draw.rect(self.screen, risk_color, (gauge_x + 2, gauge_y + 2, fill_w, gauge_h - 4), border_radius=0)

        # Segmentation lines every 20%
        for tick_idx in range(1, 5):
            tx = gauge_x + int(gauge_w * (tick_idx / 5.0))
            pygame.draw.line(self.screen, (68, 68, 68), (tx, gauge_y + 3), (tx, gauge_y + gauge_h - 3), 1)

        # Risk status readout
        if instability < 0.4:
            status_desc = "ALGORITHM STATUS: COMPLIANT — REACH EXPANSION STEADY"
        elif instability < 0.75:
            status_desc = "ALGORITHM STATUS: ELEVATED FLAGGING — AUTOMATED REVIEW TRIGGERED"
        else:
            status_desc = "ALGORITHM STATUS: CRITICAL RISK — ACCOUNT SUSPENSION IMMINENT ON NEXT POST"
        self._draw_text(status_desc, self.font_small, risk_color, (panel_rect.centerx, gauge_y + gauge_h + 16), center=True)

        # 3. Live Controls: Two Action Cards at Bottom
        card_y = self.height - 110 + oy
        card_h = 84
        card_w = 460

        # Option 1: SECURE REACH (Stop Posting)
        r1 = pygame.Rect(self.width // 2 - card_w - 15 + ox, card_y, card_w, card_h)
        is_sel1 = (selected_index == 0)
        b1 = COLOR_TIMER_GREEN if is_sel1 else (COLOR_TIMER_GREEN if selected_index is None else COLOR_HAIRLINE)
        bg1 = (41, 41, 41) if is_sel1 else COLOR_CARD_BG
        self._draw_card(r1, border_color=b1, bg_color=bg1)

        k1 = pygame.Rect(r1.left + 16, r1.centery - 18, 36, 36)
        self._draw_key_badge(k1, "1", selected=is_sel1)

        self._draw_text("SECURE REACH (Stop Posting)", self.font_body, COLOR_TIMER_GREEN if is_sel1 else COLOR_TEXT_PRIMARY, (k1.right + 16, r1.top + 12))
        sub1_rect = pygame.Rect(k1.right + 16, r1.top + 36, r1.width - 80, r1.height - 42)
        self._draw_wrapped_text(f"Lock in +{reach_value:,} impressions & conclude safely.", self.font_small, COLOR_TEXT_SECONDARY, sub1_rect, spacing=2, center_v=True)

        # Option 2: POST ANOTHER (Escalate Reach)
        r2 = pygame.Rect(self.width // 2 + 15 + ox, card_y, card_w, card_h)
        is_sel2 = (selected_index == 1)
        # Pacing: while the previous post is still publishing the pump key is inert, and the card says so
        cooldown = 0.0 if is_burst else bart_runner.get_cooldown_fraction()
        is_publishing = cooldown > 0.0
        b2 = COLOR_TIMER_RED if instability >= 0.75 else (COLOR_TIMER_AMBER if is_sel2 else self._mix(COLOR_TIMER_AMBER, COLOR_BG, 0.3))
        bg2 = (35, 35, 35) if is_sel2 else COLOR_CARD_BG
        self._draw_card(r2, border_color=b2, bg_color=bg2)

        k2 = pygame.Rect(r2.left + 16, r2.centery - 18, 36, 36)
        self._draw_key_badge(k2, "2", selected=is_sel2, enabled=not is_publishing)

        if is_publishing:
            self._draw_text("PUBLISHING POST...", self.font_body, COLOR_TEXT_SECONDARY, (k2.right + 16, r2.top + 12))
            pygame.draw.rect(self.screen, COLOR_TEXT_SECONDARY, (r2.left + 1, r2.bottom - 4, int((r2.width - 2) * (1.0 - cooldown)), 3), border_radius=0)
        else:
            self._draw_text("POST ANOTHER (Escalate Reach)", self.font_body, COLOR_TIMER_AMBER if is_sel2 else COLOR_TEXT_PRIMARY, (k2.right + 16, r2.top + 12))
        sub2_rect = pygame.Rect(k2.right + 16, r2.top + 36, r2.width - 80, r2.height - 42)
        self._draw_wrapped_text(f"Push algorithm (+{bart_runner.config.increment_per_pump:,} reach, elevated flag risk).", self.font_small, COLOR_TEXT_SECONDARY, sub2_rect, spacing=2, center_v=True)

        # 4. Suspension Burst Splash Card
        if is_burst:
            splash_w = 820
            splash_h = 220
            splash_rect = pygame.Rect(self.width // 2 - splash_w // 2, self.height // 2 - splash_h // 2 - 20, splash_w, splash_h)
            self._draw_card(splash_rect, border_color=COLOR_TIMER_RED, bg_color=(19, 19, 19))

            # Warning border accent line
            pygame.draw.line(self.screen, COLOR_TIMER_RED, (splash_rect.left + 20, splash_rect.top + 52), (splash_rect.right - 20, splash_rect.top + 52), 2)

            self._draw_text(
                "ACCOUNT SUSPENDED — REACH RESET TO ZERO",
                self.font_hero,
                COLOR_TIMER_RED,
                (splash_rect.centerx, splash_rect.top + 28),
                center=True,
                max_width=splash_rect.width - 40,
            )
            self._draw_text(
                "Community Guidelines Violation: Content Report Threshold Exceeded",
                self.font_title,
                COLOR_TEXT_PRIMARY,
                (splash_rect.centerx, splash_rect.top + 85),
                center=True,
                max_width=splash_rect.width - 40,
            )
            self._draw_text(
                "All accumulated viral impressions have been revoked by platform moderation.",
                self.font_body,
                (181, 181, 181),
                (splash_rect.centerx, splash_rect.top + 125),
                center=True,
            )
            self._draw_text(
                "Reach: 0 impressions | Account standing: suspended",
                self.font_small,
                COLOR_SEMANTIC_WARNING,
                (splash_rect.centerx, splash_rect.top + 168),
                center=True,
            )

        return True
