"""Simulation skin `misconduct_hearing` for scenario `academic_pressure_b`."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_HAIRLINE,
    COLOR_PRIMARY_ACTIVE,
    COLOR_SEMANTIC_WARNING,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_RED,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState

PANEL_SEATS: tuple[tuple[int, str], ...] = ((320, "PROF. DR. VANCE (CHAIR)"), (640, "DEAN OF ACADEMIC AFFAIRS"), (960, "STUDENT ADVOCATE (OBSERVER)"))


class MisconductHearingSkin(UIComponents):
    """Renders the `misconduct_hearing` decision skin."""

    def _draw_skin_misconduct_hearing(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render misconduct_hearing simulation skin for academic integrity inquiry."""
        jx, jy = effects.jitter_offset
        self._draw_hearing_room()
        self._draw_hearing_terminal(scenario, selected_index, (jx, jy))
        self._draw_footer_prompt("PRESS 1, 2 OR 3 TO ENTER YOUR STATEMENT. IT CANNOT BE WITHDRAWN.", selected_index is not None)
        return True

    def _draw_hearing_room(self) -> None:
        """Draw the committee room: case line, three seated figures that never react, the table and nameplates."""
        left, right = self.MARGIN, self.width - self.MARGIN
        pygame.draw.circle(self.screen, COLOR_TIMER_RED, (left + 6, self.CONTENT_TOP + 10), 4)
        self._draw_text("REC", self.font_mono_small, COLOR_SEMANTIC_WARNING, (left + 18, self.CONTENT_TOP + 10), midleft=True)
        self._draw_text("ACADEMIC INTEGRITY BOARD  •  CASE FILE #AIB-2026-08492  •  INQUIRY PROCEEDING", self.font_mono_small, COLOR_TEXT_SECONDARY, (left + 56, self.CONTENT_TOP + 10), midleft=True)

        room = pygame.Rect(left, self.CONTENT_TOP + 26, right - left, 150)
        pygame.draw.rect(self.screen, (28, 28, 28), room, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, room, width=1, border_radius=0)
        table = pygame.Rect(room.left + 1, room.bottom - 46, room.width - 2, 45)
        for seat_x, _ in PANEL_SEATS:
            self._draw_silhouette(seat_x, table.top + 8, 96, shade=50, collar=True)

        pygame.draw.rect(self.screen, (36, 36, 36), table, border_radius=0)
        pygame.draw.line(self.screen, (86, 86, 86), (table.left, table.top), (table.right, table.top), 2)
        for seat_x, title in PANEL_SEATS:
            # Case dossier with its tab, then the nameplate
            pygame.draw.rect(self.screen, (180, 180, 180), (seat_x - 150, table.top + 12, 26, 20), border_radius=0)
            pygame.draw.rect(self.screen, COLOR_PRIMARY_ACTIVE, (seat_x - 150, table.top + 12, 6, 20), border_radius=0)
            plate = pygame.Rect(seat_x - 110, table.top + 11, 220, 24)
            pygame.draw.rect(self.screen, (24, 24, 24), plate, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE, plate, width=1, border_radius=0)
            self._draw_text(title, self.font_small, (185, 185, 185), plate.center, center=True, max_width=plate.width - 12)

        self._draw_text("COMMITTEE PANEL IS OBSERVING — FORMAL RECORDING IN PROGRESS", self.font_small, (125, 125, 125), (self.width // 2, room.bottom + 16), center=True)

    def _draw_hearing_terminal(self, scenario: Scenario, selected_index: int | None, offset: tuple[int, int]) -> None:
        """Draw the statement terminal with the three statements the participant can enter into the record."""
        term = pygame.Rect(self.MARGIN + offset[0], 306 + offset[1], self.width - 2 * self.MARGIN, 372)
        self._draw_card(term, COLOR_HAIRLINE, bg_color=(24, 24, 24))
        top_bar = pygame.Rect(term.left, term.top, term.width, 34)
        pygame.draw.rect(self.screen, (36, 36, 36), top_bar, border_radius=0)
        self._draw_text("OFFICIAL STATEMENT TERMINAL", self.font_small, COLOR_ACCENT_CYAN, (top_bar.left + 20, top_bar.centery), midleft=True)
        self._draw_text("BINDING SUBMISSION", self.font_small, COLOR_TIMER_RED, (top_bar.right - 20, top_bar.centery), midright=True)
        self._draw_text("Select the statement to enter into the permanent inquiry record:", self.font_body, COLOR_TEXT_SECONDARY, (term.left + 20, term.top + 44))

        card_h, gap = 84, 10
        for i, opt in enumerate(scenario.options):
            rect = pygame.Rect(term.left + 20, term.top + 80 + i * (card_h + gap), term.width - 40, card_h)
            self._draw_option_card(rect, opt.key, opt.text, i, selected_index, plate="ENTERED")
