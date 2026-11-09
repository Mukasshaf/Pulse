"""Simulation skin `defense_stage` for scenario `social_evaluation_a`."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_HAIRLINE,
    COLOR_PRIMARY_ROSSO,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_GREEN,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState

PANEL_SEATS: tuple[tuple[int, str], ...] = ((320, "EVALUATOR 1"), (640, "PANEL LEAD"), (960, "EVALUATOR 3"))
CHALLENGE = "Can you substantiate your methodology, or does your data collapse under rigorous examination?"


class DefenseStageSkin(UIComponents):
    """Renders the `defense_stage` decision skin."""

    def _draw_skin_defense_stage(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render defense_stage simulation skin for live project defense in front of an expert panel."""
        jx, jy = effects.jitter_offset
        final_third = max(0.0, time_remaining_s / float(scenario.decision_duration_s)) <= scenario.drone_trigger_fraction
        left, width = self.MARGIN + jx, self.width - 2 * self.MARGIN

        # The challenge is projected on the wall above the panel; its frame turns Rosso for the final third
        projection = pygame.Rect(left, self.CONTENT_TOP + jy, width, 66)
        pygame.draw.rect(self.screen, (32, 32, 32), projection, border_radius=0)
        for line_y in range(projection.top + 12, projection.bottom - 8, 14):
            pygame.draw.line(self.screen, (28, 28, 28), (projection.left + 10, line_y), (projection.right - 10, line_y), 1)
        pygame.draw.rect(self.screen, COLOR_PRIMARY_ROSSO if final_third else (93, 93, 93), projection, width=1, border_radius=0)
        self._draw_text("REVIEW PANEL  •  QUESTION TO THE PRESENTER", self.font_mono_small, COLOR_ACCENT_CYAN, (projection.left + 16, projection.top + 16), midleft=True)
        self._draw_text(f'"{CHALLENGE}"', self.font_body, COLOR_TEXT_PRIMARY, (projection.centerx, projection.top + 42), center=True, max_width=projection.width - 40)

        self._draw_defense_panel(pygame.Rect(left, projection.bottom + 10, width, 150))
        self._draw_text("PANEL IN SESSION  •  AWAITING YOUR RESPONSE", self.font_small, (120, 120, 120), (self.width // 2 + jx, projection.bottom + 174), center=True)

        podium = pygame.Rect(left, projection.bottom + 190, width, 30)
        pygame.draw.rect(self.screen, (32, 32, 32), podium, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, podium, width=1, border_radius=0)
        pygame.draw.circle(self.screen, COLOR_TIMER_GREEN, (podium.left + 14, podium.centery), 4)
        self._draw_text("PODIUM MIC: LIVE", self.font_small, COLOR_TIMER_GREEN, (podium.left + 26, podium.centery), midleft=True)
        self._draw_text("YOUR RESPONSE", self.font_small, COLOR_TEXT_SECONDARY, (podium.right - 14, podium.centery), midright=True)

        card_h, gap = 58, 8
        for i, opt in enumerate(scenario.options):
            rect = pygame.Rect(left, podium.bottom + 8 + i * (card_h + gap), width, card_h)
            self._draw_option_card(rect, opt.key, opt.text, i, selected_index, plate="DELIVERED")
        if scenario.has_deception_metric:
            bar_top = podium.bottom + 8 + len(scenario.options) * (card_h + gap) + 4
            self.draw_composure_bar(composure_fraction, (left, bar_top + 18), width=width, is_drone_active=final_third)
        self._draw_footer_prompt("PRESS 1, 2 OR 3 TO DELIVER YOUR RESPONSE TO THE PANEL", selected_index is not None)
        return True

    def _draw_defense_panel(self, room: pygame.Rect) -> None:
        """Draw three evaluators behind their bench. They are featureless and never move: nothing can be read from them."""
        pygame.draw.rect(self.screen, (28, 28, 28), room, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, room, width=1, border_radius=0)
        bench = pygame.Rect(room.left + 1, room.bottom - 42, room.width - 2, 41)
        shift = room.left - self.MARGIN
        for k, (seat_x, _) in enumerate(PANEL_SEATS):
            self._draw_silhouette(seat_x + shift, bench.top + 8, 104, shade=44 if k == 1 else 52, collar=True)
        pygame.draw.rect(self.screen, (36, 36, 36), bench, border_radius=0)
        pygame.draw.line(self.screen, (87, 87, 87), (bench.left, bench.top), (bench.right, bench.top), 2)
        for seat_x, title in PANEL_SEATS:
            pygame.draw.rect(self.screen, (165, 165, 165), (seat_x + shift - 120, bench.top + 11, 24, 18), border_radius=0)
            plate = pygame.Rect(seat_x + shift - 80, bench.top + 9, 160, 24)
            pygame.draw.rect(self.screen, (24, 24, 24), plate, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE, plate, width=1, border_radius=0)
            self._draw_text(title, self.font_small, (187, 187, 187), plate.center, center=True)
