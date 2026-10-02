"""Simulation skin `classroom_critique` for scenario `social_evaluation_b`."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_BG,
    COLOR_PRIMARY_ACTIVE,
    COLOR_PRIMARY_ROSSO,
    COLOR_TEXT_PRIMARY,
    COLOR_TIMER_AMBER,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState

CRITIQUE = "Your approach lacks standard rigor. Explain why the group should consider this acceptable."
BACK_ROW = 11
FRONT_ROW = 9


class ClassroomCritiqueSkin(UIComponents):
    """Renders the `classroom_critique` decision skin."""

    def _draw_skin_classroom_critique(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render classroom_critique simulation skin for public critique before a full cohort."""
        jx, jy = effects.jitter_offset
        final_third = max(0.0, time_remaining_s / float(scenario.decision_duration_s)) <= scenario.drone_trigger_fraction
        left, width = self.MARGIN + jx, self.width - 2 * self.MARGIN

        self._draw_classroom_instructor((left + 62, self.CONTENT_TOP + 244 + jy), final_third, jx)
        self._draw_classroom_audience(left + 170, self.CONTENT_TOP + 88 + jy, width - 170)
        self._draw_text(f"{BACK_ROW + FRONT_ROW} CLASSMATES ARE WATCHING IN SILENCE", self.font_small, (122, 122, 122), (left + 170 + (width - 170) // 2, self.CONTENT_TOP + 266 + jy), center=True)

        card_h, gap = 58, 8
        options_top = self.CONTENT_TOP + 288 + jy
        for i, opt in enumerate(scenario.options):
            rect = pygame.Rect(left, options_top + i * (card_h + gap), width, card_h)
            self._draw_option_card(rect, opt.key, opt.text, i, selected_index, plate="DELIVERED")
        if scenario.has_deception_metric:
            bar_top = options_top + len(scenario.options) * (card_h + gap) + 4
            self.draw_composure_bar(composure_fraction, (left, bar_top + 18), width=width, is_drone_active=final_third)
        self._draw_footer_prompt("PRESS 1, 2 OR 3 TO ANSWER IN FRONT OF THE CLASS", selected_index is not None)
        return True

    def _draw_classroom_instructor(self, feet: tuple[int, int], final_third: bool, jitter_x: int) -> None:
        """Draw the standing instructor, the arm that singles the participant out, and the critique it delivers."""
        base_x, base_y = feet
        pygame.draw.line(self.screen, (48, 48, 48), (base_x - 50, base_y), (base_x + 70, base_y), 2)
        self._draw_silhouette(base_x, base_y, 160, shade=52, collar=True)
        hand = (base_x + 104, base_y - 96)
        pygame.draw.line(self.screen, (52, 52, 52), (base_x + 40, base_y - 62), (base_x + 70, base_y - 80), 8)
        pygame.draw.line(self.screen, (52, 52, 52), (base_x + 70, base_y - 80), hand, 6)
        pygame.draw.circle(self.screen, (72, 72, 72), hand, 5)
        self._draw_text("COURSE INSTRUCTOR", self.font_small, (175, 175, 175), (base_x + 10, base_y + 14), center=True)

        # Speech bubble: dim Rosso frame, full Rosso for the final third
        bubble = pygame.Rect(self.MARGIN + 170 + jitter_x, base_y - 244, self.width - 2 * self.MARGIN - 170, 76)
        frame = COLOR_PRIMARY_ROSSO if final_third else COLOR_PRIMARY_ACTIVE
        pointer = [(bubble.left, bubble.top + 30), (bubble.left, bubble.top + 54), (bubble.left - 30, bubble.top + 66)]
        pygame.draw.polygon(self.screen, COLOR_BG, pointer)
        pygame.draw.polygon(self.screen, frame, pointer, width=1)
        pygame.draw.rect(self.screen, COLOR_BG, bubble, border_radius=0)
        pygame.draw.rect(self.screen, frame, bubble, width=1, border_radius=0)
        self._draw_text("THE INSTRUCTOR, TO YOU, IN FRONT OF THE CLASS", self.font_mono_small, COLOR_TIMER_AMBER, (bubble.left + 16, bubble.top + 18), midleft=True)
        self._draw_text(f'"{CRITIQUE}"', self.font_body, COLOR_TEXT_PRIMARY, (bubble.centerx, bubble.top + 48), center=True, max_width=bubble.width - 40)

    def _draw_classroom_audience(self, left: int, top: int, width: int) -> None:
        """Draw two rows of seated classmates facing the participant: 11 behind, 9 in front."""
        rows = ((BACK_ROW, top + 72, 68, 40), (FRONT_ROW, top + 156, 86, 50))
        for count, base_y, height, shade in rows:
            spacing = width / count
            for seat in range(count):
                self._draw_silhouette(left + int(spacing * (seat + 0.5)), base_y, height, shade=shade)
            pygame.draw.rect(self.screen, (shade - 8, shade - 8, shade - 8), (left, base_y - 4, width, 10), border_radius=0)
            pygame.draw.line(self.screen, (shade + 22, shade + 22, shade + 22), (left, base_y - 4), (left + width, base_y - 4), 1)
