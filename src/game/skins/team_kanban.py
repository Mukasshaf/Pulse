"""Simulation skin `team_kanban` for scenario `peer_influence_b`."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_HAIRLINE,
    COLOR_SEMANTIC_WARNING,
    COLOR_TEXT_MUTED,
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

MODULES: tuple[tuple[str, str, str, bool], ...] = (
    ("Module A: Frontend UI", "STATUS: PASS", "Grade: A (94%)", True),
    ("Module B: Data Pipeline", "STATUS: PASS", "Grade: A- (90%)", True),
    ("Module C: Docs & QA", "STATUS: PASS", "Grade: B+ (88%)", True),
    ("Core Integration", "STATUS: FAILED", "Grade: F (0%)", False),
)
TEAMMATES: tuple[tuple[str, str, str], ...] = (
    ("Alex (Lead)", "A", "Core integration module not delivered on time."),
    ("Brandon", "B", "All other modules ready; bottleneck was in core."),
    ("Chloe", "C", "Core module team assigned owner failed to merge."),
    ("Danielle", "D", "System integration broke downstream testing."),
)
COLUMN_GAP = 14


class TeamKanbanSkin(UIComponents):
    """Renders the `team_kanban` decision skin."""

    def _draw_skin_team_kanban(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render team_kanban simulation skin: project board showing unanimous blame attribution."""
        jx, jy = effects.jitter_offset
        left = self.MARGIN + jx
        top = self.CONTENT_TOP + jy
        self._draw_text("PROJECT SPRINT REVIEW  •  FINAL EVALUATION BOARD", self.font_mono_small, COLOR_TEXT_SECONDARY, (left, top + 10), midleft=True)
        self._draw_text("SPRINT GRADE: CRITICAL DEFICIENCY", self.font_mono_small, COLOR_SEMANTIC_WARNING, (self.width - self.MARGIN + jx, top + 10), midright=True)
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (self.MARGIN, top + 24), (self.width - self.MARGIN, top + 24), 1)

        self._draw_kanban_board(left, top + 34)
        elapsed_s = max(0.0, float(scenario.decision_duration_s) - time_remaining_s)
        self._draw_kanban_response(scenario, selected_index, pygame.Rect(left, top + 268, self.width - 2 * self.MARGIN, 320), elapsed_s)
        self._draw_footer_prompt("PRESS 1, 2 OR 3 TO SUBMIT YOUR RESPONSE TO THE COURSE RECORD", selected_index is not None)
        return True

    def _draw_kanban_board(self, left: int, top: int) -> None:
        """Draw the four module cards and, under each, the teammate review that attributes the failure."""
        card_w = (self.width - 2 * self.MARGIN - 3 * COLUMN_GAP) // 4
        for k, (title, status, grade, passed) in enumerate(MODULES):
            card = pygame.Rect(left + k * (card_w + COLUMN_GAP), top, card_w, 78)
            pygame.draw.rect(self.screen, (32, 32, 32) if passed else (24, 24, 24), card, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE if passed else COLOR_TIMER_RED, card, width=1 if passed else 2, border_radius=0)
            self._draw_text(title, self.font_body, COLOR_TEXT_PRIMARY, (card.left + 12, card.top + 8))
            self._draw_text(status, self.font_small, COLOR_TIMER_GREEN if passed else COLOR_TIMER_RED, (card.left + 12, card.top + 34))
            self._draw_text(grade, self.font_small, (145, 145, 145), (card.left + 12, card.top + 53))
            if not passed:
                self._draw_tag("FAILED", (card.right - 10, card.top + 20), anchor="midright", ink=COLOR_TEXT_PRIMARY, fill=COLOR_TIMER_RED, font=self.font_small)

        self._draw_text("PEER REVIEW ASSESSMENTS  •  4 OF 4 SUBMITTED", self.font_mono_small, (170, 170, 170), (left, top + 96), midleft=True)
        for k, (name, initial, comment) in enumerate(TEAMMATES):
            card = pygame.Rect(left + k * (card_w + COLUMN_GAP), top + 110, card_w, 108)
            pygame.draw.rect(self.screen, (32, 32, 32), card, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE, card, width=1, border_radius=0)
            # Avatar: neutral plate, teammates are told apart by initial and name rather than by hue
            pygame.draw.circle(self.screen, COLOR_TEXT_MUTED, (card.left + 24, card.top + 22), 12)
            self._draw_text(initial, self.font_small, COLOR_TEXT_PRIMARY, (card.left + 24, card.top + 22), center=True)
            self._draw_text(name, self.font_small, COLOR_TEXT_PRIMARY, (card.left + 44, card.top + 12))
            self._draw_wrapped_text(comment, self.font_small, (150, 150, 150), pygame.Rect(card.left + 12, card.top + 38, card.width - 24, 40), spacing=2)
            tag = pygame.Rect(card.left + 8, card.bottom - 26, card.width - 16, 20)
            pygame.draw.rect(self.screen, (24, 24, 24), tag, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_TIMER_RED, tag, width=1, border_radius=0)
            self._draw_text("Failure Attribution: YOU", self.font_mono_small, COLOR_SEMANTIC_WARNING, tag.center, center=True)

    def _draw_kanban_response(self, scenario: Scenario, selected_index: int | None, panel: pygame.Rect, elapsed_s: float) -> None:
        """Draw the participant's own entry on the board: blank and waiting until a response is submitted."""
        self._draw_card(panel, (60, 60, 60), bg_color=(24, 24, 24))
        top_bar = pygame.Rect(panel.left, panel.top, panel.width, 34)
        pygame.draw.rect(self.screen, (36, 36, 36), top_bar, border_radius=0)
        label = self._draw_text("YOUR ASSESSMENT:", self.font_small, COLOR_ACCENT_CYAN, (top_bar.left + 18, top_bar.centery), midleft=True)
        if selected_index is not None:
            self._draw_text("SUBMITTED", self.font_small, COLOR_TEXT_PRIMARY, (label.right + 10, top_bar.centery), midleft=True)
        elif int(elapsed_s * 2.0) % 2 == 0:
            # The empty entry's cursor blinks at 1 Hz
            pygame.draw.rect(self.screen, COLOR_TEXT_PRIMARY, (label.right + 10, top_bar.centery - 8, 9, 16), border_radius=0)
        self._draw_text("FINAL SUBMISSION", self.font_small, COLOR_TIMER_AMBER, (top_bar.right - 18, top_bar.centery), midright=True)
        self._draw_text("Choose your response to the team's assessment:", self.font_body, COLOR_TEXT_SECONDARY, (panel.left + 20, panel.top + 42))

        card_h, gap = 72, 8
        for i, opt in enumerate(scenario.options):
            rect = pygame.Rect(panel.left + 20, panel.top + 74 + i * (card_h + gap), panel.width - 40, card_h)
            self._draw_option_card(rect, opt.key, opt.text, i, selected_index, plate="SUBMITTED")
