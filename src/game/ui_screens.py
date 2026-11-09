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
    COLOR_SEMANTIC_WARNING,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_RED,
    DEFAULT_CONSEQUENCE_DURATION_S,
    ScenarioType,
)
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents

# Where each scenario takes place, shown on the briefing in place of the research domain name.
# The domain is a construct label and stays in the registry and the logs.
SETTING_LABELS: dict[str, str] = {
    "exam_hall": "EXAM HALL",
    "misconduct_hearing": "INTEGRITY BOARD",
    "group_chat": "CLASS GROUP CHAT",
    "team_kanban": "SPRINT REVIEW",
    "reward_crate": "REWARD VAULT",
    "document_workspace": "ASSIGNMENT EDITOR",
    "tournament_bracket": "TOURNAMENT LOBBY",
    "social_analytics": "CREATOR STUDIO",
    "portal_log": "CAMPUS IT PORTAL",
    "code_diff": "CODE REVIEW",
    "fork_map": "ROUTE PLANNER",
    "notification_stack": "LOCK SCREEN",
    "defense_stage": "REVIEW PANEL",
    "classroom_critique": "CLASSROOM",
}
PLATE_LEFT = 140
PLATE_WIDTH = 1000


class UIScreens(UIComponents):
    """ID input, baseline, priming, briefing popup, feedback, rest, and debrief screens."""

    def _draw_plate(self, label: str, title: str, top: int, title_font: pygame.font.Font | None = None) -> int:
        """Draw the shared screen heading (small label, title, hairline) and return the y below the hairline."""
        self._draw_text(label, self.font_mono_small, COLOR_ACCENT_CYAN, (PLATE_LEFT, top), midleft=True)
        heading = self._draw_text(title, title_font if title_font is not None else self.font_hero, COLOR_TEXT_PRIMARY, (PLATE_LEFT, top + 16), max_width=PLATE_WIDTH)
        pygame.draw.line(self.screen, COLOR_HAIRLINE_SUBTLE, (PLATE_LEFT, heading.bottom + 14), (PLATE_LEFT + PLATE_WIDTH, heading.bottom + 14), 1)
        return heading.bottom + 15

    def _draw_key_legend(self, entries: list[tuple[list[str], str]], pos: tuple[int, int]) -> None:
        """Draw a row of key plates, each group followed by what the keys do."""
        x, y = pos
        for keys, meaning in entries:
            for key in keys:
                plate = self._draw_tag(key, (x, y), ink=COLOR_TEXT_PRIMARY, fill=COLOR_BG, border=COLOR_TEXT_SECONDARY)
                x = plate.right + 6
            text = self._draw_text(meaning, self.font_small, COLOR_TEXT_SECONDARY, (x + 6, y), midleft=True)
            x = text.right + 36

    def draw_id_input(self, current_text: str, error_msg: str | None) -> None:
        """Render participant ID entry screen."""
        self.screen.fill(COLOR_BG)
        top = self._draw_plate("SESSION SETUP", "PULSE", 232)
        self._draw_text("Enter the subject ID (for example S01).", self.font_lead, COLOR_TEXT_SECONDARY, (PLATE_LEFT, top + 22))

        box = pygame.Rect(PLATE_LEFT, top + 76, 280, 54)
        pygame.draw.rect(self.screen, (28, 28, 28), box, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TEXT_SECONDARY, box, width=1, border_radius=0)
        cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
        self._draw_text(current_text + cursor, self.font_title, COLOR_TEXT_PRIMARY, (box.left + 16, box.centery), midleft=True)

        if error_msg:
            self._draw_text(error_msg, self.font_small, COLOR_SEMANTIC_WARNING, (PLATE_LEFT, box.bottom + 28), midleft=True)
        else:
            self._draw_key_legend([(["ENTER"], "confirm"), (["ESC"], "quit")], (PLATE_LEFT, box.bottom + 28))

    def draw_baseline(self, elapsed_s: float, total_s: float) -> None:
        """Render the resting baseline: a static fixation cross and an unobtrusive progress line."""
        self.screen.fill(COLOR_BG)
        self._draw_plate("RESTING BASELINE", "Baseline calibration", 84, self.font_title)
        self._draw_text("Relax your hands, keep still, and breathe normally.", self.font_lead, COLOR_TEXT_SECONDARY, (PLATE_LEFT, 168))

        # Static fixation target. No respiratory pacing: a paced slow breath entrains RSA and
        # inflates resting RMSSD/SDNN, which would bias every baseline-relative z-score.
        center = (self.width // 2, self.height // 2 + 30)
        pygame.draw.circle(self.screen, (30, 30, 30), center, 120)
        pygame.draw.circle(self.screen, COLOR_HAIRLINE_SUBTLE, center, 76, width=1)
        pygame.draw.line(self.screen, COLOR_TEXT_SECONDARY, (center[0] - 12, center[1]), (center[0] + 12, center[1]), 2)
        pygame.draw.line(self.screen, COLOR_TEXT_SECONDARY, (center[0], center[1] - 12), (center[0], center[1] + 12), 2)
        self._draw_text("Rest your eyes on the cross", self.font_body, COLOR_TEXT_SECONDARY, (self.width // 2, center[1] + 150), center=True)

        # The time left is kept small and muted so it does not pull the eyes off the cross
        remaining = max(0, round(total_s - elapsed_s))
        self._draw_progress_line(pygame.Rect(PLATE_LEFT, self.height - 66, PLATE_WIDTH, 3), elapsed_s / total_s if total_s > 0 else 1.0, COLOR_TEXT_MUTED)
        self._draw_text(f"{remaining // 60}:{remaining % 60:02d} remaining", self.font_mono_small, COLOR_TEXT_MUTED, (PLATE_LEFT + PLATE_WIDTH, self.height - 44), midright=True)

    def draw_priming(self, scenario: Scenario, elapsed_s: float, skip_available: bool = True) -> None:
        """Render scenario priming instructions and stakes briefing."""
        self.screen.fill(COLOR_BG)
        # The setting names the place; the paradigm and the research domain are never shown to participants
        top = self._draw_plate(f"BRIEFING  •  {SETTING_LABELS.get(scenario.skin, 'SCENARIO')}", scenario.title, 132)
        text_rect = pygame.Rect(PLATE_LEFT, top + 26, PLATE_WIDTH, 236)
        self._draw_wrapped_text(scenario.priming_text, self.font_lead, COLOR_TEXT_PRIMARY, text_rect, spacing=8)

        keys = ["1"] if scenario.scenario_type == ScenarioType.REWARD_ACCUMULATOR else [str(opt.key) for opt in scenario.options]
        self._draw_key_legend([(keys, "respond"), (["TAB"], "hold to re-read this briefing")], (PLATE_LEFT, 520))

        duration = float(scenario.priming_duration_s)
        self._draw_progress_line(pygame.Rect(PLATE_LEFT, 558, PLATE_WIDTH, 3), elapsed_s / duration if duration > 0 else 1.0, COLOR_ACCENT_CYAN)
        remaining = max(0, round(duration - elapsed_s))
        if skip_available:
            self._draw_key_legend([(["SPACE"], f"begin now  •  starts by itself in {remaining} s")], (PLATE_LEFT, 592))
        else:
            self._draw_text(f"Read the briefing  •  starts in {remaining} s", self.font_small, COLOR_TEXT_SECONDARY, (PLATE_LEFT, 592), midleft=True)

    def draw_question_popup(self, scenario: Scenario) -> None:
        """Render modal overlay displaying the scenario briefing, question, and context."""
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((16, 16, 16, 236))
        self.screen.blit(overlay, (0, 0))

        card = pygame.Rect(PLATE_LEFT - 40, 96, PLATE_WIDTH + 80, 528)
        self._draw_card(card, border_color=COLOR_HAIRLINE_SUBTLE, bg_color=COLOR_BG)
        top = self._draw_plate(f"BRIEFING  •  {SETTING_LABELS.get(scenario.skin, 'SCENARIO')}", scenario.title, card.top + 36)
        self._draw_text("HOLDING TAB — RELEASE TO RETURN", self.font_mono_small, COLOR_TIMER_AMBER, (card.right - 40, card.top + 36), midright=True)
        briefing = pygame.Rect(PLATE_LEFT, top + 20, PLATE_WIDTH, 180)
        self._draw_wrapped_text(scenario.priming_text, self.font_body, COLOR_TEXT_PRIMARY, briefing, spacing=8)

        # Options summary (the arithmetic run has no fixed options to list)
        if scenario.options and scenario.scenario_type != ScenarioType.MIST_ARITHMETIC:
            box = pygame.Rect(PLATE_LEFT, card.bottom - 178, PLATE_WIDTH, 116)
            pygame.draw.rect(self.screen, (32, 32, 32), box, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE, box, width=1, border_radius=0)
            self._draw_text("YOUR CHOICES", self.font_mono_small, COLOR_TEXT_SECONDARY, (box.left + 16, box.top + 16), midleft=True)
            summary = "\n".join(f"[{opt.key}]  {opt.text}" for opt in scenario.options)
            self._draw_wrapped_text(summary, self.font_small, (229, 229, 229), pygame.Rect(box.left + 16, box.top + 32, box.width - 32, 78), spacing=2)
        self._draw_text("The timer keeps running while this briefing is open.", self.font_small, (140, 140, 140), (self.width // 2, card.bottom - 30), center=True)

    def draw_feedback(self, consequence_text: str, elapsed_s: float) -> None:
        """Render scenario consequence narrative feedback."""
        self.screen.fill(COLOR_BG)
        lowered = consequence_text.lower()
        suspended = "account suspended" in lowered or "system failure" in lowered
        collapsed = "collapsed" in lowered
        rule = COLOR_TIMER_RED if suspended or collapsed else COLOR_TEXT_SECONDARY

        block = pygame.Rect(PLATE_LEFT, 214, PLATE_WIDTH, 292)
        pygame.draw.rect(self.screen, rule, (block.left, block.top, 4, block.height), border_radius=0)
        self._draw_text("OUTCOME", self.font_mono_small, COLOR_TEXT_SECONDARY, (block.left + 32, block.top + 12), midleft=True)
        text_rect = pygame.Rect(block.left + 32, block.top + 46, block.width - 64, 160)
        self._draw_wrapped_text(consequence_text, self.font_lead, COLOR_TEXT_PRIMARY, text_rect, spacing=8)

        # The suspension badge is shown for that outcome only
        if suspended:
            badge = pygame.Rect(block.left + 32, block.bottom - 62, block.width - 64, 36)
            pygame.draw.rect(self.screen, COLOR_BG, badge, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_TIMER_RED, badge, width=1, border_radius=0)
            self._draw_text("ACCOUNT SUSPENDED — REACH RESET TO ZERO", self.font_small, COLOR_TIMER_RED, badge.center, center=True)
        self._draw_progress_line(pygame.Rect(block.left + 32, block.bottom - 3, block.width - 64, 3), elapsed_s / float(DEFAULT_CONSEQUENCE_DURATION_S), COLOR_TEXT_MUTED)

        # Disperse shatter particles if active or if consequence was collapse
        if collapsed and not self.shatter_effect.particles:
            self.shatter_effect.trigger((self.width // 2, self.height // 2))
        if self.shatter_effect.is_active:
            self.shatter_effect.update(16)
            self.shatter_effect.draw(self.screen)

    def draw_rest(self, is_inter_domain: bool, time_remaining_s: float, total_s: float | None = None) -> None:
        """Render the rest screen between scenarios or domains: a quiet gradient, one instruction, the time left."""
        for y in range(self.height):
            pygame.draw.line(self.screen, self._mix(COLOR_REST_GRADIENT_TOP, COLOR_REST_GRADIENT_BOTTOM, y / float(self.height)), (0, y), (self.width, y))

        top = self._draw_plate("REST", "Rest break" if is_inter_domain else "Short pause", 236)
        self._draw_text("Keep your hand relaxed and still. The next part begins by itself.", self.font_lead, COLOR_TEXT_SECONDARY, (PLATE_LEFT, top + 24))
        remaining = max(0, round(time_remaining_s))
        number = self._draw_text(str(remaining), self.font_hero, COLOR_ACCENT_CYAN, (PLATE_LEFT, top + 84))
        self._draw_text("seconds", self.font_body, COLOR_TEXT_SECONDARY, (number.right + 12, number.bottom - 12), midleft=True)
        if total_s is not None and total_s > 0:
            self._draw_progress_line(pygame.Rect(PLATE_LEFT, number.bottom + 22, PLATE_WIDTH, 3), 1.0 - time_remaining_s / total_s, COLOR_ACCENT_CYAN)

    def draw_debrief(self, total_duration_s: float, scenarios_completed: int) -> None:
        """Render final session completion debrief screen."""
        self.screen.fill(COLOR_BG)
        top = self._draw_plate("SESSION COMPLETE", "Thank you for taking part.", 232)
        minutes, seconds = int(total_duration_s // 60), int(total_duration_s % 60)
        self._draw_text(f"Session length  {minutes:02d}:{seconds:02d}", self.font_lead, COLOR_TEXT_SECONDARY, (PLATE_LEFT, top + 24))
        self._draw_text(f"Scenarios completed  {scenarios_completed}", self.font_lead, COLOR_TEXT_SECONDARY, (PLATE_LEFT, top + 62))
        self._draw_text("The session has ended. You may relax your hand now.", self.font_body, COLOR_TEXT_PRIMARY, (PLATE_LEFT, top + 122))
        self._draw_key_legend([(["ESC"], "close the session")], (PLATE_LEFT, top + 184))
