"""Simulation skin `social_analytics` for scenario `risk_reward_b`."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_BG,
    COLOR_CARD_BG,
    COLOR_HAIRLINE,
    COLOR_HAIRLINE_SUBTLE,
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
        ox = effects.vibration_offset[0] + effects.jitter_offset[0]
        oy = effects.vibration_offset[1] + effects.jitter_offset[1]

        nav = pygame.Rect(self.MARGIN + ox, self.CONTENT_TOP + oy, self.width - 2 * self.MARGIN, 40)
        self._draw_card(nav, border_color=COLOR_HAIRLINE, bg_color=COLOR_CARD_BG)
        pygame.draw.rect(self.screen, COLOR_ACCENT_CYAN, (nav.left + 18, nav.centery - 4, 8, 8), border_radius=0)
        self._draw_text("LIVE CAMPAIGN", self.font_mono_small, COLOR_ACCENT_CYAN, (nav.left + 36, nav.centery), midleft=True)
        self._draw_text("CREATOR STUDIO  •  REACH ANALYTICS", self.font_mono_small, COLOR_TEXT_PRIMARY, (nav.left + 170, nav.centery), midleft=True)
        self._draw_text("AUDIENCE: GENERAL FEED", self.font_mono_small, (140, 140, 140), (nav.right - 20, nav.centery), midright=True)

        panel = pygame.Rect(self.width // 2 - 460 + ox, nav.bottom + 14, 920, 420)
        self._draw_card(panel, border_color=COLOR_HAIRLINE, bg_color=COLOR_CARD_BG)
        if bart_runner.is_burst:
            self._draw_analytics_suspension(panel)
        else:
            self._draw_analytics_dashboard(panel, bart_runner)
        self._draw_analytics_actions(scenario, bart_runner, selected_index, (ox, oy))
        over = bart_runner.is_burst or bart_runner.is_secured
        self._draw_footer_prompt("PRESS 1 TO STOP  •  PRESS 2 TO POST AGAIN", over, "THE ACCOUNT IS SUSPENDED" if bart_runner.is_burst else "RESPONSE RECORDED")
        return True

    def _draw_analytics_dashboard(self, panel: pygame.Rect, runner: BARTRunner) -> None:
        """Draw the live dashboard: reach, the row of posts published so far, and the suspension-risk gauge."""
        instability = runner.get_instability_fraction()
        secured = runner.is_secured
        self._draw_text("REACH SECURED (IMPRESSIONS)" if secured else "ACCUMULATED AUDIENCE REACH (IMPRESSIONS)", self.font_small, COLOR_TEXT_SECONDARY, (panel.centerx, panel.top + 32), center=True)
        self._draw_text(f"{runner.current_value:,}", self.font_hero, COLOR_TIMER_GREEN if secured else COLOR_ACCENT_CYAN, (panel.centerx, panel.top + 76), center=True)

        # One slot per possible post: filled once published, a progress fill while the newest one is going out
        max_posts = runner.config.max_pumps
        slot_w, slot_gap = 46, 8
        row_left = panel.centerx - (max_posts * slot_w + (max_posts - 1) * slot_gap) // 2
        self._draw_text(f"POSTS PUBLISHED: {runner.pump_count} OF {max_posts}", self.font_mono_small, (169, 169, 169), (row_left, panel.top + 140), midleft=True)
        self._draw_text(f"VIRAL VELOCITY: TIER {min(5, 1 + runner.pump_count // 3)}", self.font_mono_small, COLOR_ACCENT_CYAN, (row_left + max_posts * (slot_w + slot_gap) - slot_gap, panel.top + 140), midright=True)
        cooldown = runner.get_cooldown_fraction()
        for post in range(max_posts):
            slot = pygame.Rect(row_left + post * (slot_w + slot_gap), panel.top + 156, slot_w, 34)
            pygame.draw.rect(self.screen, (32, 32, 32), slot, border_radius=0)
            published = post < runner.pump_count
            if published:
                going_out = post == runner.pump_count - 1 and cooldown > 0.0
                fill_w = int((slot.width - 4) * (1.0 - cooldown)) if going_out else slot.width - 4
                pygame.draw.rect(self.screen, self._mix(COLOR_ACCENT_CYAN, COLOR_BG, 0.35), (slot.left + 2, slot.top + 2, fill_w, slot.height - 4), border_radius=0)
            pygame.draw.rect(self.screen, COLOR_ACCENT_CYAN if published else COLOR_HAIRLINE_SUBTLE, slot, width=1, border_radius=0)

        gauge = pygame.Rect(row_left, panel.top + 262, max_posts * (slot_w + slot_gap) - slot_gap, 26)
        risk_colour = COLOR_TIMER_GREEN if instability < 0.4 else (COLOR_TIMER_AMBER if instability < 0.75 else COLOR_TIMER_RED)
        self._draw_text("Content Flag & Suspension Risk", self.font_small, COLOR_TEXT_SECONDARY, (gauge.left, gauge.top - 16), midleft=True)
        self._draw_text(f"{int(instability * 100)}% RISK LEVEL", self.font_small, risk_colour, (gauge.right, gauge.top - 16), midright=True)
        pygame.draw.rect(self.screen, (32, 32, 32), gauge, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, gauge, width=1, border_radius=0)
        fill_w = int((gauge.width - 4) * instability)
        if fill_w > 4:
            pygame.draw.rect(self.screen, risk_colour, (gauge.left + 2, gauge.top + 2, fill_w, gauge.height - 4), border_radius=0)
        for tick in range(1, 5):
            tick_x = gauge.left + int(gauge.width * (tick / 5.0))
            pygame.draw.line(self.screen, (68, 68, 68), (tick_x, gauge.top + 3), (tick_x, gauge.bottom - 3), 1)

        if secured:
            status = "CAMPAIGN CLOSED — REACH LOCKED IN"
        elif instability < 0.4:
            status = "ALGORITHM STATUS: COMPLIANT — REACH EXPANSION STEADY"
        elif instability < 0.75:
            status = "ALGORITHM STATUS: ELEVATED FLAGGING — AUTOMATED REVIEW TRIGGERED"
        else:
            status = "ALGORITHM STATUS: CRITICAL RISK — ACCOUNT SUSPENSION IMMINENT ON NEXT POST"
        self._draw_text(status, self.font_small, COLOR_TIMER_GREEN if secured else risk_colour, (panel.centerx, gauge.bottom + 34), center=True)
        self._draw_text("Each post adds reach. Each post is more likely to be flagged than the last.", self.font_small, (140, 140, 140), (panel.centerx, panel.bottom - 36), center=True)

    def _draw_analytics_suspension(self, panel: pygame.Rect) -> None:
        """Replace the whole dashboard with the suspension notice, so no stale figure shows around it."""
        pygame.draw.rect(self.screen, (19, 19, 19), panel, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TIMER_RED, panel, width=1, border_radius=0)
        self._draw_text("ACCOUNT SUSPENDED", self.font_hero, COLOR_TIMER_RED, (panel.centerx, panel.top + 96), center=True)
        pygame.draw.line(self.screen, COLOR_TIMER_RED, (panel.left + 120, panel.top + 136), (panel.right - 120, panel.top + 136), 2)
        self._draw_text("Community Guidelines Violation: Content Report Threshold Exceeded", self.font_lead, COLOR_TEXT_PRIMARY, (panel.centerx, panel.top + 178), center=True, max_width=panel.width - 60)
        self._draw_text("All accumulated impressions have been revoked by platform moderation.", self.font_body, (181, 181, 181), (panel.centerx, panel.top + 224), center=True)
        self._draw_text("Reach: 0 impressions  |  Account standing: suspended", self.font_small, COLOR_SEMANTIC_WARNING, (panel.centerx, panel.top + 280), center=True)

    def _draw_analytics_actions(self, scenario: Scenario, runner: BARTRunner, selected_index: int | None, offset: tuple[int, int]) -> None:
        """Draw the two action cards. The post key is muted while the previous post is still publishing."""
        over = runner.is_burst or runner.is_secured
        labels = [opt.text for opt in scenario.options] + ["STOP POSTING", "POST ANOTHER"]
        top = 600 + offset[1]
        stop = pygame.Rect(self.width // 2 - 470 + offset[0], top, 460, 78)
        stop_detail = "Nothing is left to secure." if runner.is_burst else f"Lock in {runner.current_value:,} impressions and stop here."
        self._draw_option_card(stop, 1, labels[0], 0, selected_index, detail=stop_detail, accent=COLOR_TIMER_GREEN, plate="SECURED")

        post = pygame.Rect(self.width // 2 + 10 + offset[0], top, 460, 78)
        publishing = not over and runner.get_cooldown_fraction() > 0.0
        accent = COLOR_TIMER_RED if runner.get_instability_fraction() >= 0.75 else COLOR_TIMER_AMBER
        style = self._draw_option_frame(post, 1, selected_index, accent, dimmed=runner.is_secured)
        badge = pygame.Rect(post.left + 18, post.centery - 18, 36, 36)
        self._draw_key_badge(badge, "2", selected=style.chosen, enabled=style.chosen or not (over or publishing))
        title = "PUBLISHING POST..." if publishing else labels[1]
        self._draw_text(title, self.font_body, COLOR_TEXT_SECONDARY if publishing else style.ink, (badge.right + 18, post.top + 14))
        if runner.is_burst:
            post_detail = "The last post was reported."
        else:
            post_detail = f"+{runner.config.increment_per_pump:,} reach, and a higher chance of being flagged."
        self._draw_text(post_detail, self.font_small, style.sub_ink, (badge.right + 18, post.top + 44), max_width=post.width - 90)
        if publishing:
            self._draw_progress_line(pygame.Rect(post.left + 5, post.bottom - 4, post.width - 6, 3), 1.0 - runner.get_cooldown_fraction())
