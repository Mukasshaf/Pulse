"""Full-screen state renderers for Pulse outside the decision phase."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_BG,
    COLOR_HAIRLINE,
    COLOR_HAIRLINE_SUBTLE,
    COLOR_REST_GRADIENT_BOTTOM,
    COLOR_REST_GRADIENT_TOP,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_RED,
    ScenarioType,
)
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents


class UIScreens(UIComponents):
    """ID input, baseline, priming, briefing popup, feedback, rest, and debrief screens."""

    def draw_id_input(self, current_text: str, error_msg: str | None) -> None:
        """Render participant ID entry screen."""
        self.screen.fill(COLOR_BG)
        card_rect = pygame.Rect(self.width // 2 - 250, self.height // 2 - 140, 500, 280)
        self._draw_card(card_rect, COLOR_HAIRLINE_SUBTLE)

        self._draw_text("PULSE ENGINE", self.font_hero, COLOR_TEXT_PRIMARY, (self.width // 2, card_rect.top + 50), center=True)
        self._draw_text("Enter Subject ID (e.g. S01):", self.font_body, COLOR_TEXT_SECONDARY, (self.width // 2, card_rect.top + 105), center=True)

        box_rect = pygame.Rect(self.width // 2 - 120, card_rect.top + 140, 240, 48)
        pygame.draw.rect(self.screen, (28, 28, 28), box_rect, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TEXT_SECONDARY, box_rect, width=1, border_radius=0)

        display_str = current_text + ("_" if (pygame.time.get_ticks() // 500) % 2 == 0 else "")
        self._draw_text(display_str, self.font_title, COLOR_TEXT_PRIMARY, box_rect.center, center=True)

        if error_msg:
            self._draw_text(error_msg, self.font_small, COLOR_TIMER_RED, (self.width // 2, box_rect.bottom + 20), center=True)
        else:
            self._draw_text("Press ENTER to confirm", self.font_small, COLOR_TEXT_SECONDARY, (self.width // 2, box_rect.bottom + 20), center=True)

    def draw_baseline(self, elapsed_s: float, total_s: float) -> None:
        """Render physiological baseline calibration with breathing pacer."""
        self.screen.fill(COLOR_BG)
        rem_s = max(0, round(total_s - elapsed_s))

        # Static fixation target. No respiratory pacing: a paced slow breath entrains RSA and
        # inflates resting RMSSD/SDNN, which would bias every baseline-relative z-score.
        center = (self.width // 2, self.height // 2 - 20)
        pygame.draw.circle(self.screen, (32, 32, 32), center, 125)
        pygame.draw.circle(self.screen, COLOR_HAIRLINE_SUBTLE, center, 80, width=1)
        pygame.draw.line(self.screen, COLOR_TEXT_SECONDARY, (center[0] - 12, center[1]), (center[0] + 12, center[1]), 2)
        pygame.draw.line(self.screen, COLOR_TEXT_SECONDARY, (center[0], center[1] - 12), (center[0], center[1] + 12), 2)

        self._draw_text("BASELINE PHYSIOLOGICAL CALIBRATION", self.font_title, COLOR_TEXT_PRIMARY, (self.width // 2, 80), center=True)
        self._draw_text("Relax your hands, keep still, and breathe normally.", self.font_body, COLOR_TEXT_SECONDARY, (self.width // 2, 120), center=True)
        self._draw_text("Rest your eyes on the cross", self.font_title, COLOR_TEXT_SECONDARY, (self.width // 2, self.height // 2 + 130), center=True)
        self._draw_text(f"Calibration Time Remaining: {rem_s}s", self.font_body, COLOR_TEXT_SECONDARY, (self.width // 2, self.height - 80), center=True)

    def draw_priming(self, scenario: Scenario, elapsed_s: float, skip_available: bool = True) -> None:
        """Render scenario priming instructions and stakes briefing."""
        self.screen.fill(COLOR_BG)
        rem_s = max(0, round(scenario.priming_duration_s - elapsed_s))

        card_rect = pygame.Rect(self.width // 2 - 500, self.height // 2 - 225, 1000, 450)
        self._draw_card(card_rect, COLOR_HAIRLINE_SUBTLE)

        self._draw_text(scenario.domain_id.value.replace("_", " ").upper(), self.font_small, COLOR_ACCENT_CYAN, (card_rect.left + 45, card_rect.top + 28))

        # Dynamic title font size to prevent overflow
        title_font = self.font_hero if self.font_hero.size(scenario.title)[0] <= card_rect.width - 90 else self.font_title
        self._draw_text(scenario.title, title_font, COLOR_TEXT_PRIMARY, (card_rect.left + 45, card_rect.top + 52))

        # The paradigm name stays in the scenario registry and logs; it is never shown to participants

        # Priming text container with generous room
        text_rect = pygame.Rect(card_rect.left + 45, card_rect.top + 148, card_rect.width - 90, 230)
        self._draw_wrapped_text(scenario.priming_text, self.font_body, COLOR_TEXT_PRIMARY, text_rect, spacing=8)
        self._draw_text(
            f"Press [SPACE] to start immediately • Auto-starting in {rem_s}s..." if skip_available else f"Read carefully • Starting in {rem_s}s...",
            self.font_body,
            COLOR_ACCENT_CYAN,
            (self.width // 2, card_rect.bottom - 35),
            center=True,
        )

    def draw_question_popup(self, scenario: Scenario) -> None:
        """Render modal overlay displaying the scenario briefing, question, and context."""
        # Dim background with semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((16, 16, 16, 230))
        self.screen.blit(overlay, (0, 0))

        # Modal Card
        card_w = 980
        card_h = 490
        card_rect = pygame.Rect(self.width // 2 - card_w // 2, self.height // 2 - card_h // 2, card_w, card_h)
        self._draw_card(card_rect, border_color=COLOR_HAIRLINE_SUBTLE, bg_color=COLOR_BG)

        # Header: Domain tag + Active Hold Notice
        self._draw_text(scenario.domain_id.value.replace("_", " ").upper(), self.font_small, COLOR_ACCENT_CYAN, (card_rect.left + 40, card_rect.top + 24))

        rel_notice = "[ HOLDING TAB / Q — RELEASE TO RETURN ]"
        rn_w = self.font_mono_small.size(rel_notice)[0]
        self._draw_text(rel_notice, self.font_mono_small, COLOR_TIMER_AMBER, (card_rect.right - 40 - rn_w, card_rect.top + 24))

        # Title
        title_font = self.font_hero if self.font_hero.size(scenario.title)[0] <= card_rect.width - 80 else self.font_title
        self._draw_text(scenario.title, title_font, COLOR_TEXT_PRIMARY, (card_rect.left + 40, card_rect.top + 48))

        # Divider
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (card_rect.left + 35, card_rect.top + 130), (card_rect.right - 35, card_rect.top + 130), 1)

        # Question / Priming Section
        self._draw_text("SCENARIO QUESTION & BRIEFING:", self.font_small, COLOR_ACCENT_CYAN, (card_rect.left + 40, card_rect.top + 144))
        briefing_rect = pygame.Rect(card_rect.left + 40, card_rect.top + 170, card_rect.width - 80, 160)
        self._draw_wrapped_text(scenario.priming_text, self.font_body, COLOR_TEXT_PRIMARY, briefing_rect, spacing=8)

        # Options Summary Box (if scenario has options)
        if scenario.options and scenario.scenario_type not in (ScenarioType.MIST_ARITHMETIC,):
            opt_box = pygame.Rect(card_rect.left + 40, card_rect.top + 345, card_rect.width - 80, 104)
            pygame.draw.rect(self.screen, (32, 32, 32), opt_box, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE, opt_box, width=1, border_radius=0)
            self._draw_text("AVAILABLE CHOICES:", self.font_mono_small, COLOR_TEXT_SECONDARY, (opt_box.left + 16, opt_box.top + 8))
            opt_summary = "\n".join(f"[{opt.key}] {opt.text}" for opt in scenario.options)
            opt_summary_rect = pygame.Rect(opt_box.left + 16, opt_box.top + 28, opt_box.width - 32, 70)
            self._draw_wrapped_text(opt_summary, self.font_small, (229, 229, 229), opt_summary_rect, spacing=2)

        # Bottom release hint
        self._draw_text("Release [TAB] or [Q] to resume scenario decision", self.font_small, (140, 140, 140), (self.width // 2, card_rect.bottom - 24), center=True)

    def draw_feedback(self, consequence_text: str, elapsed_s: float) -> None:
        """Render scenario consequence narrative feedback."""
        self.screen.fill(COLOR_BG)
        card_rect = pygame.Rect(self.width // 2 - 460, self.height // 2 - 165, 920, 330)
        self._draw_card(card_rect, COLOR_HAIRLINE_SUBTLE)

        self._draw_text("CONSEQUENCE RECORDED", self.font_small, COLOR_TEXT_SECONDARY, (self.width // 2, card_rect.top + 32), center=True)
        text_rect = pygame.Rect(card_rect.left + 50, card_rect.top + 70, card_rect.width - 100, 165)
        self._draw_wrapped_text(consequence_text, self.font_body, COLOR_TEXT_PRIMARY, text_rect, spacing=6)

        # Display account suspension warning badge if burst occurred
        if "account suspended" in consequence_text.lower() or "system failure" in consequence_text.lower():
            warn_badge = pygame.Rect(card_rect.left + 50, card_rect.bottom - 50, card_rect.width - 100, 34)
            pygame.draw.rect(self.screen, (24, 24, 24), warn_badge, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_TIMER_RED, warn_badge, width=1, border_radius=0)
            self._draw_text("ACCOUNT SUSPENDED — REACH RESET TO ZERO", self.font_small, COLOR_TIMER_RED, warn_badge.center, center=True)

        # Disperse shatter particles if active or if consequence was collapse
        if "collapsed" in consequence_text.lower() and not self.shatter_effect.particles:
            self.shatter_effect.trigger((self.width // 2, self.height // 2))
        if self.shatter_effect.is_active:
            self.shatter_effect.update(16)
            self.shatter_effect.draw(self.screen)

    def draw_rest(self, is_inter_domain: bool, time_remaining_s: float) -> None:
        """Render soothing rest gradient screen between scenarios or domains."""
        # Top-to-bottom gradient
        for y in range(self.height):
            ratio = y / float(self.height)
            r = int(COLOR_REST_GRADIENT_TOP[0] + (COLOR_REST_GRADIENT_BOTTOM[0] - COLOR_REST_GRADIENT_TOP[0]) * ratio)
            g = int(COLOR_REST_GRADIENT_TOP[1] + (COLOR_REST_GRADIENT_BOTTOM[1] - COLOR_REST_GRADIENT_TOP[1]) * ratio)
            b = int(COLOR_REST_GRADIENT_TOP[2] + (COLOR_REST_GRADIENT_BOTTOM[2] - COLOR_REST_GRADIENT_TOP[2]) * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (self.width, y))

        rem_s = max(0, round(time_remaining_s))
        title = "Inter-Domain Rest Period" if is_inter_domain else "Intra-Domain Recovery"
        self._draw_text(title, self.font_hero, COLOR_TEXT_PRIMARY, (self.width // 2, self.height // 2 - 60), center=True)
        self._draw_text("Rest quietly. Next section begins shortly.", self.font_body, COLOR_TEXT_SECONDARY, (self.width // 2, self.height // 2 - 5), center=True)
        self._draw_text(f"{rem_s}s", self.font_hero, COLOR_ACCENT_CYAN, (self.width // 2, self.height // 2 + 65), center=True)

    def draw_debrief(self, total_duration_s: float, scenarios_completed: int) -> None:
        """Render final session completion debrief screen."""
        self.screen.fill(COLOR_BG)
        card_rect = pygame.Rect(self.width // 2 - 350, self.height // 2 - 160, 700, 320)
        self._draw_card(card_rect, COLOR_HAIRLINE_SUBTLE)

        self._draw_text("SESSION COMPLETE", self.font_hero, COLOR_TEXT_PRIMARY, (self.width // 2, card_rect.top + 45), center=True)
        self._draw_text("Thank you for your participation.", self.font_title, COLOR_TEXT_PRIMARY, (self.width // 2, card_rect.top + 105), center=True)

        mins = int(total_duration_s // 60)
        secs = int(total_duration_s % 60)
        time_str = f"{mins:02d}:{secs:02d}"
        self._draw_text(f"Total Session Duration: {time_str}", self.font_body, COLOR_TEXT_SECONDARY, (self.width // 2, card_rect.top + 165), center=True)
        self._draw_text(f"Scenarios Completed: {scenarios_completed}", self.font_body, COLOR_TEXT_SECONDARY, (self.width // 2, card_rect.top + 205), center=True)
        self._draw_text("Press ESC or close the window to exit.", self.font_small, COLOR_TEXT_SECONDARY, (self.width // 2, card_rect.bottom - 40), center=True)
