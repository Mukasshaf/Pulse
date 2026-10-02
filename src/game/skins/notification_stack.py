"""Simulation skin `notification_stack` for scenario `future_uncertainty_b`, with its post-decision wait."""
from __future__ import annotations

import math

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_CARD_BG,
    COLOR_HAIRLINE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_GREEN,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState

CARD_W = 840
REMARK = ("Your approach throughout this term has been... ", "? atypical ?", " compared to your peers.")


class NotificationStackSkin(UIComponents):
    """Renders the `notification_stack` decision skin and its wait screen from one shared lock screen."""

    def _draw_skin_notification_stack(
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
        """Render notification_stack simulation skin: minimalist lockscreen notification and 3 draft responses."""
        offset = (effects.vibration_offset[0] + effects.jitter_offset[0], effects.vibration_offset[1] + effects.jitter_offset[1])
        notice = self._draw_lockscreen(offset, dimmed=False)

        # Reply drafts: the words the participant would send, exactly as logged, with no label on what they mean
        self._draw_text("REPLY DRAFTS", self.font_mono_small, COLOR_TEXT_SECONDARY, (notice.left, notice.bottom + 22), midleft=True)
        card_h, gap = 92, 12
        for i, opt in enumerate(scenario.options):
            rect = pygame.Rect(notice.left, notice.bottom + 40 + i * (card_h + gap), CARD_W, card_h)
            self._draw_option_card(rect, opt.key, f'"{opt.text}"', i, selected_index, plate="SENT")
        self._draw_footer_prompt("PRESS 1, 2 OR 3 TO SEND A REPLY", selected_index is not None)
        return True

    def _draw_lockscreen(self, offset: tuple[int, int], dimmed: bool) -> pygame.Rect:
        """Draw the lock screen with the one notification on it and return the notification's rect."""
        cx = self.width // 2 + offset[0]
        top = self.CONTENT_TOP + offset[1]
        self._draw_text("23:42", self.font_title, (150, 150, 150) if dimmed else (219, 219, 219), (cx, top + 12), center=True)
        self._draw_text("Friday, September 19  •  Midterm Assessment Period", self.font_small, COLOR_TEXT_MUTED if dimmed else (140, 140, 140), (cx, top + 40), center=True)

        # Status icons: signal bars and battery
        stat_x = self.width - self.MARGIN - 86 + offset[0]
        for bar in range(4):
            bar_h = 4 + bar * 3
            pygame.draw.rect(self.screen, (189, 189, 189), (stat_x + bar * 5, top + 18 - bar_h, 3, bar_h))
        pygame.draw.rect(self.screen, (150, 150, 150), (stat_x + 30, top + 6, 22, 12), width=1, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TIMER_GREEN, (stat_x + 32, top + 8, 14, 8))
        pygame.draw.rect(self.screen, (150, 150, 150), (stat_x + 52, top + 9, 2, 6))

        notice = pygame.Rect(cx - CARD_W // 2, top + 62, CARD_W, 138)
        self._draw_card(notice, border_color=COLOR_HAIRLINE, bg_color=(22, 22, 22) if dimmed else COLOR_CARD_BG)
        self._draw_lockscreen_seal((notice.left + 36, notice.top + 34))
        ink = (150, 150, 150) if dimmed else COLOR_TEXT_PRIMARY
        self._draw_text("ACADEMIC SUPERVISOR", self.font_body, ink, (notice.left + 64, notice.top + 12))
        self._draw_text("FACULTY PORTAL  •  MESSAGE", self.font_mono_small, (144, 144, 144), (notice.left + 64, notice.top + 38))
        self._draw_text("now", self.font_small, COLOR_TEXT_SECONDARY, (notice.right - 20, notice.top + 26), midright=True)
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (notice.left + 20, notice.top + 68), (notice.right - 20, notice.top + 68), 1)

        # The remark, with the one word that carries it set apart in the info token
        prefix, word, suffix = REMARK
        line_y = notice.top + 102
        body_ink = (130, 130, 130) if dimmed else (227, 227, 227)
        lead = self._draw_text(prefix, self.font_body, body_ink, (notice.left + 24, line_y), midleft=True)
        word_colour = self._mix(COLOR_ACCENT_CYAN, (22, 22, 22), 0.4) if dimmed else COLOR_ACCENT_CYAN
        tag = self._draw_tag(word, (lead.right + 2, line_y), ink=word_colour, fill=(28, 28, 28), border=word_colour, font=self.font_lead)
        self._draw_text(suffix, self.font_body, body_ink, (tag.right + 6, line_y), midleft=True)
        return notice

    def _draw_lockscreen_seal(self, center: tuple[int, int]) -> None:
        """Draw the sender's neutral institutional seal."""
        pygame.draw.circle(self.screen, (42, 42, 42), center, 18)
        pygame.draw.circle(self.screen, (167, 167, 167), center, 18, width=2)
        pygame.draw.circle(self.screen, (167, 167, 167), center, 14, width=1)
        star = []
        for point in range(10):
            radius = 7.0 if point % 2 == 0 else 3.2
            angle = -math.pi / 2 + point * (math.pi / 5)
            star.append((center[0] + int(radius * math.cos(angle)), center[1] + int(radius * math.sin(angle))))
        pygame.draw.polygon(self.screen, (167, 167, 167), star)

    def _draw_post_wait_notification_stack(self, text: str, elapsed_fraction: float) -> None:
        """Render the wait after a reply is sent: the same lock screen, the message unanswered, and no information."""
        notice = self._draw_lockscreen((0, 0), dimmed=True)
        sent = pygame.Rect(notice.right - 300, notice.bottom + 18, 300, 40)
        pygame.draw.rect(self.screen, (40, 40, 40), sent, border_radius=0)
        self._draw_text("Your reply  •  Sent", self.font_small, COLOR_TEXT_SECONDARY, (sent.left + 14, sent.centery), midleft=True)

        modal = pygame.Rect(self.width // 2 - 330, notice.bottom + 96, 660, 132)
        self._draw_card(modal, border_color=COLOR_ACCENT_CYAN, bg_color=COLOR_CARD_BG)
        self._draw_spinner((modal.left + 58, modal.centery), 20, elapsed_fraction * 5.0)
        self._draw_text(text, self.font_title, COLOR_TEXT_PRIMARY, (modal.left + 104, modal.top + 30), max_width=modal.width - 128)
        self._draw_text("No reply yet. This will finish on its own.", self.font_small, COLOR_TEXT_SECONDARY, (modal.left + 104, modal.top + 78))
        self._draw_text("PLEASE REMAIN STILL", self.font_small, (140, 140, 140), (self.width // 2, self.FOOTER_Y), center=True)
