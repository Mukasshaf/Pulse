"""Simulation skin `document_workspace` for scenario `impulsivity_gratification_b`, with its review wait."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_BG,
    COLOR_CARD_BG,
    COLOR_HAIRLINE,
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

PAPER = (244, 244, 244)
# Paragraphs as (line widths); the second one is the unsaved revision
PARAGRAPHS: tuple[tuple[float, ...], ...] = ((1.0, 0.96, 0.98, 0.72), (0.68, 0.65, 0.50), (0.97, 0.88, 0.93, 0.40), (0.99, 0.94, 0.61))
REVISED_PARAGRAPH = 1


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
        ox = effects.vibration_offset[0] + effects.jitter_offset[0]
        oy = effects.vibration_offset[1] + effects.jitter_offset[1]
        self._draw_document_window((ox, oy), "Assignment Editor", "Draft status: Adequate — requirements met")

        accents = (COLOR_TIMER_GREEN, COLOR_TIMER_AMBER)
        for i, opt in enumerate(scenario.options[:2]):
            rect = pygame.Rect(self.width // 2 - 470 + i * 480 + ox, 606 + oy, 460, 76)
            action, outcome = self._split_option(opt.text)
            self._draw_option_card(rect, opt.key, action, i, selected_index, detail=outcome, accent=accents[i])
        self._draw_footer_prompt("PRESS 1 TO SUBMIT NOW  •  PRESS 2 TO REQUEST MORE TIME", selected_index is not None)
        return True

    def _draw_document_window(self, offset: tuple[int, int], mode: str, status: str) -> pygame.Rect:
        """Draw the editor window with the draft on its page and return the page rect."""
        window = pygame.Rect(self.width // 2 - 460 + offset[0], self.CONTENT_TOP + offset[1], 920, 494)
        pygame.draw.rect(self.screen, (28, 28, 28), window, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, window, width=1, border_radius=0)
        bar = self._draw_window_chrome(window, f"Term_Paper_Final_Draft_v4.docx — {mode}", "Auto-saved")

        ribbon = pygame.Rect(window.left, bar.bottom, window.width, 28)
        pygame.draw.rect(self.screen, (24, 24, 24), ribbon, border_radius=0)
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (window.left, ribbon.bottom), (window.right, ribbon.bottom), 1)
        self._draw_text("File    Edit    View    Insert    Format    Tools    Help", self.font_small, (134, 134, 134), (window.left + 24, ribbon.centery), midleft=True)

        page = pygame.Rect(window.left + 24, ribbon.bottom + 12, window.width - 48, window.height - 118)
        pygame.draw.rect(self.screen, PAPER, page, border_radius=0)
        self._draw_document_page(page)

        status_bar = pygame.Rect(window.left, window.bottom - 30, window.width, 30)
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (window.left, status_bar.top), (window.right, status_bar.top), 1)
        self._draw_text("Words: 3,420    |    Page 6 of 6", self.font_small, COLOR_TEXT_SECONDARY, (status_bar.left + 24, status_bar.centery), midleft=True)
        self._draw_text(status, self.font_small, COLOR_ACCENT_CYAN, (status_bar.right - 24, status_bar.centery), midright=True)
        return page

    def _draw_document_page(self, page: pygame.Rect) -> None:
        """Draw the draft: a title, grey text lines, and one paragraph highlighted as an unsaved revision."""
        left = page.left + 45
        text_w = page.width - 90
        self._draw_text("Urban Green Space and Summer Air Temperature: A Field Study", self.font_body, (32, 32, 32), (left, page.top + 16))
        self._draw_text("Course: Environmental Science (ENVS-210)  |  Draft revision 4.2", self.font_small, COLOR_TEXT_MUTED, (left, page.top + 42))
        pygame.draw.line(self.screen, (210, 210, 210), (left, page.top + 64), (page.right - 45, page.top + 64), 1)

        line_y = page.top + 80
        for index, widths in enumerate(PARAGRAPHS):
            revised = index == REVISED_PARAGRAPH
            if revised:
                # The revision highlight is the caution yellow washed into the paper white, not a separate pastel
                pygame.draw.rect(self.screen, self._mix(COLOR_TIMER_AMBER, PAPER, 0.72), (left - 4, line_y - 4, int(text_w * 0.72), len(widths) * 16 + 4), border_radius=0)
                self._draw_tag("Unsaved edits: rev 4.2", (page.right - 20, line_y + 18), anchor="midright", ink=COLOR_BG, fill=self._mix(COLOR_TIMER_AMBER, PAPER, 0.85), border=self._mix(COLOR_TIMER_AMBER, COLOR_BG, 0.35), font=self.font_small)
            for width in widths:
                pygame.draw.rect(self.screen, (155, 155, 155) if revised else (190, 190, 190), (left, line_y, int(text_w * width), 7), border_radius=0)
                line_y += 16
            line_y += 18

    def _draw_post_wait_document_workspace(self, text: str, elapsed_fraction: float) -> None:
        """Render the review wait: the same editor, a scan line over the page, and an unhurried status card."""
        page = self._draw_document_window((0, 0), "Review in progress", "Review pending")
        # The scan line crosses the page once every 2.5 s of the 15 s wait
        scan_y = page.top + int(((elapsed_fraction * 6.0) % 1.0) * page.height)
        pygame.draw.line(self.screen, COLOR_ACCENT_CYAN, (page.left, scan_y), (page.right, scan_y), 3)

        modal = pygame.Rect(self.width // 2 - 300, page.centery + 24, 600, 112)
        self._draw_card(modal, border_color=COLOR_ACCENT_CYAN, bg_color=COLOR_CARD_BG)
        self._draw_spinner((modal.left + 56, modal.centery), 20, elapsed_fraction * 7.5)
        self._draw_text(text, self.font_title, COLOR_TEXT_PRIMARY, (modal.left + 100, modal.top + 22), max_width=modal.width - 124)
        self._draw_text("The review will finish on its own. No key is needed.", self.font_small, COLOR_TEXT_SECONDARY, (modal.left + 100, modal.top + 68))
        self._draw_text("PLEASE REMAIN STILL DURING THE REVIEW", self.font_small, (140, 140, 140), (self.width // 2, self.FOOTER_Y), center=True)
