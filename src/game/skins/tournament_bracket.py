"""Simulation skin `tournament_bracket` for scenario `risk_reward_a`."""
from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_BG,
    COLOR_CARD_BG,
    COLOR_HAIRLINE,
    COLOR_PRIMARY_ACTIVE,
    COLOR_PRIMARY_ROSSO,
    COLOR_SEMANTIC_WARNING,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_GREEN,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState

ROUNDS = 6


@dataclass(frozen=True)
class StrategyCard:
    """The described risk shown on one strategy card."""

    name: str
    protocol: str
    gain: str
    variance_label: str
    variance: float  # share of the variance bar that is filled: wider spread, longer bar
    history: list[int]  # gains of the rounds on record; the rest of the six are untracked
    bar_scale: float
    record: str
    risk_line: str
    summary: str
    colour: tuple[int, int, int]


STRATEGIES: tuple[StrategyCard, ...] = (
    StrategyCard("Strategy Alpha", "CONSERVATIVE PROTOCOL", "+8% AVG", "Variance: LOW (σ = ±1.5%)", 0.08, [8, 9, 7, 8, 9, 8], 4.5,
                 "[OK] 6/6 ROUNDS AUDITED & VERIFIED", "Risk Profile: 1 / 10 (Predictable)", "Guaranteed gain. Zero downside exposure.", COLOR_TIMER_GREEN),
    StrategyCard("Strategy Beta", "AGGRESSIVE PROTOCOL", "+22% AVG", "Variance: HIGH (σ = ±14.2%)", 0.48, [18, 26, 20, 24], 2.2,
                 "[ 2 ROUNDS UNTRACKED ]", "Risk Profile: 6 / 10 (Moderate Volatility)", "Higher payout, but latent unhedged loss probability.", COLOR_TIMER_AMBER),
    StrategyCard("Strategy Gamma", "EXPERIMENTAL HIGH-YIELD", "+45% AVG", "Variance: EXTREME (σ = ±38.0%)", 0.94, [44, 46], 1.5,
                 "[ 4 ROUNDS UNTRACKED — EXTREME VARIANCE ]", "Risk Profile: 9.5 / 10 (Critical Downside)", "Massive potential gain, but catastrophic ranking drop risk.", COLOR_PRIMARY_ROSSO),
)


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
        ox = effects.vibration_offset[0] + effects.jitter_offset[0]
        oy = effects.vibration_offset[1] + effects.jitter_offset[1]

        header = pygame.Rect(self.MARGIN + ox, self.CONTENT_TOP + oy, self.width - 2 * self.MARGIN, 44)
        self._draw_card(header, border_color=COLOR_HAIRLINE, bg_color=COLOR_CARD_BG)
        self._draw_text("CURRENT DIVISION STANDING: TIER 1 BRACKET", self.font_lead, COLOR_ACCENT_CYAN, (header.left + 20, header.centery), midleft=True)
        self._draw_text("SEASON PLAYOFFS  •  MATCH 1 OF 1", self.font_mono_small, COLOR_TEXT_SECONDARY, (header.right - 20, header.centery), midright=True)

        # 1 Hz pulse for the "rounds untracked" tags; it follows the decision clock
        pulse = (math.sin(time_remaining_s * 2.0 * math.pi) + 1.0) / 2.0
        card_w, gap = 376, 26
        for i, strategy in enumerate(STRATEGIES):
            card = pygame.Rect(self.MARGIN + ox + i * (card_w + gap), header.bottom + 12, card_w, 520)
            self._draw_strategy_card(card, i, strategy, selected_index, pulse)
        self._draw_footer_prompt("PRESS 1, 2 OR 3 TO COMMIT YOUR STRATEGY", selected_index is not None)
        return True

    def _draw_strategy_card(self, card: pygame.Rect, index: int, strategy: StrategyCard, selected_index: int | None, pulse: float) -> None:
        """Draw one strategy: projected gain, variance, the round history with its gaps, and the risk line."""
        style = self._draw_option_frame(card, index, selected_index, accent=strategy.colour)
        colour = self._mix(strategy.colour, COLOR_BG, 0.55) if style.passed else strategy.colour
        left, inner_w = card.left + 20, card.width - 40
        badge = pygame.Rect(left, card.top + 16, 36, 36)
        self._draw_key_badge(badge, str(index + 1), selected=style.chosen, enabled=not style.passed)
        self._draw_text(strategy.name, self.font_body, style.ink, (badge.right + 14, card.top + 12))
        self._draw_text(strategy.protocol, self.font_small, colour, (badge.right + 14, card.top + 38))
        if style.chosen:
            self._draw_tag("SELECTED", (card.right - 16, card.top + 34), anchor="midright", ink=COLOR_BG, fill=style.ink)

        gain_box = pygame.Rect(left, card.top + 70, inner_w, 70)
        pygame.draw.rect(self.screen, (24, 24, 24), gain_box, border_radius=0)
        pygame.draw.rect(self.screen, colour, gain_box, width=1, border_radius=0)
        self._draw_text(strategy.gain, self.font_hero, colour, (gain_box.centerx, gain_box.top + 26), center=True)
        self._draw_text("Projected Round Gain", self.font_small, style.sub_ink, (gain_box.centerx, gain_box.top + 56), center=True)

        self._draw_text(strategy.variance_label, self.font_small, style.sub_ink, (left, card.top + 152))
        self._draw_progress_line(pygame.Rect(left, card.top + 176, inner_w, 8), strategy.variance, colour)

        on_record = len(strategy.history)
        self._draw_text(f"ROUND HISTORY ({on_record} OF {ROUNDS} ON RECORD)", self.font_small, style.sub_ink, (left, card.top + 200))
        self._draw_strategy_history(pygame.Rect(left, card.top + 228, inner_w, 96), strategy, colour)

        # The record tag is steady when the history is complete and pulses when rounds are missing
        complete = on_record == ROUNDS
        tag_colour = colour if complete or style.passed else self._mix(colour, COLOR_BG, 0.35 * (1.0 - pulse))
        tag = pygame.Rect(left, card.top + 356, inner_w, 36)
        pygame.draw.rect(self.screen, (30, 30, 30), tag, border_radius=0)
        pygame.draw.rect(self.screen, tag_colour, tag, width=1, border_radius=0)
        self._draw_text(strategy.record, self.font_small, tag_colour, tag.center, center=True, max_width=tag.width - 16)

        risk_ink = style.sub_ink if strategy.colour != COLOR_PRIMARY_ROSSO or style.passed else COLOR_SEMANTIC_WARNING
        self._draw_text(strategy.risk_line, self.font_small, risk_ink, (left, card.top + 412))
        self._draw_wrapped_text(strategy.summary, self.font_small, style.sub_ink, pygame.Rect(left, card.top + 438, inner_w, 60), spacing=2)

    def _draw_strategy_history(self, area: pygame.Rect, strategy: StrategyCard, colour: tuple[int, int, int]) -> None:
        """Draw six round bars; a round with no record is an empty slot marked with a question mark."""
        bar_w = (area.width - (ROUNDS - 1) * 8) // ROUNDS
        base_y = area.bottom - 22
        for round_idx in range(ROUNDS):
            bar_x = area.left + round_idx * (bar_w + 8)
            if round_idx < len(strategy.history):
                bar_h = int(strategy.history[round_idx] * strategy.bar_scale)
                pygame.draw.rect(self.screen, colour, (bar_x, base_y - bar_h, bar_w, bar_h), border_radius=0)
            else:
                slot = pygame.Rect(bar_x, base_y - 52, bar_w, 52)
                pygame.draw.rect(self.screen, (24, 24, 24), slot, border_radius=0)
                edge = COLOR_PRIMARY_ACTIVE if strategy.colour == COLOR_PRIMARY_ROSSO else self._mix(colour, COLOR_BG, 0.4)
                pygame.draw.rect(self.screen, edge, slot, width=1, border_radius=0)
                self._draw_text("?", self.font_body, colour, slot.center, center=True)
            self._draw_text(f"R{round_idx + 1}", self.font_small, (133, 133, 133), (bar_x + bar_w // 2, base_y + 12), center=True)
