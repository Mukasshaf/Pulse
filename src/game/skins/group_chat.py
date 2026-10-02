"""Simulation skin `group_chat` for scenario `peer_influence_a`."""
from __future__ import annotations

import math

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_BG,
    COLOR_HAIRLINE,
    COLOR_HAIRLINE_SUBTLE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_GREEN,
    NOTIFICATION_PULSE_HZ,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState

# Four peers, one vote: the wording differs so it reads as a chat, the position is unanimous
PEER_MESSAGES: tuple[tuple[str, str, str, str], ...] = (
    ("Maya", "M.", "12:41", "Share it. It's already going around anyway."),
    ("Jake", "J.", "12:42", "Yeah, share it."),
    ("Rohan", "R.", "12:42", "Agreed, send it to the other group."),
    ("Tess", "T.", "12:43", "Do it. Share."),
)
MESSAGE_STAGGER_S = 0.6  # each peer message arrives this long after the previous one
FRAME_W = 560
FRAME_H = 590


class GroupChatSkin(UIComponents):
    """Renders the `group_chat` decision skin."""

    def _draw_skin_group_chat(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render group_chat simulation skin: mobile chat interface simulating Asch conformity."""
        jx, jy = effects.jitter_offset
        frame = pygame.Rect((self.width - FRAME_W) // 2 + jx, self.CONTENT_TOP + jy, FRAME_W, FRAME_H)
        elapsed_s = max(0.0, float(scenario.decision_duration_s) - time_remaining_s)

        # Device frame; its border carries the notification pulse (dim caution yellow, 1 Hz, never a flash)
        pulse = (math.sin(elapsed_s * 2.0 * math.pi * NOTIFICATION_PULSE_HZ) + 1.0) / 2.0
        pygame.draw.rect(self.screen, (16, 16, 16), frame.move(6, 6), border_radius=0)
        pygame.draw.rect(self.screen, (28, 28, 28), frame, border_radius=0)
        pygame.draw.rect(self.screen, self._mix(COLOR_TIMER_AMBER, COLOR_BG, 0.55 + 0.30 * (1.0 - pulse)), frame, width=1, border_radius=0)

        self._draw_chat_header(frame)
        arrived = min(len(PEER_MESSAGES), int(elapsed_s / MESSAGE_STAGGER_S))
        self._draw_chat_thread(frame, arrived)
        reply_y = frame.top + 96 + len(PEER_MESSAGES) * 58
        if selected_index is not None and selected_index < len(scenario.options):
            self._draw_chat_own_reply(frame, reply_y, scenario.options[selected_index].text)
        elif arrived == len(PEER_MESSAGES):
            self._draw_chat_typing(frame, reply_y, elapsed_s)

        # Quick replies: the option text only, and the same neutral plate for either reply
        action_y = frame.top + 396
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (frame.left, action_y), (frame.right, action_y), 1)
        self._draw_text("QUICK REPLY", self.font_mono_small, (135, 135, 135), (frame.left + 18, action_y + 16), midleft=True)
        for i, opt in enumerate(scenario.options):
            chip = pygame.Rect(frame.left + 18, action_y + 32 + i * 78, frame.width - 36, 68)
            self._draw_option_card(chip, opt.key, opt.text, i, selected_index, font=self.font_small, plate="SENT")

        self._draw_footer_prompt("PRESS 1 OR 2 TO REPLY TO THE GROUP", selected_index is not None)
        return True

    def _draw_chat_header(self, frame: pygame.Rect) -> None:
        """Draw the chat title bar and the notice that the reply is public."""
        header = pygame.Rect(frame.left + 1, frame.top + 1, frame.width - 2, 54)
        pygame.draw.rect(self.screen, (36, 36, 36), header, border_radius=0)
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (frame.left, header.bottom), (frame.right, header.bottom), 1)
        pygame.draw.circle(self.screen, (54, 54, 54), (frame.left + 30, frame.top + 28), 16)
        self._draw_text("CG", self.font_small, COLOR_TEXT_PRIMARY, (frame.left + 30, frame.top + 28), center=True)
        self._draw_text("Class Group", self.font_body, COLOR_TEXT_PRIMARY, (frame.left + 55, frame.top + 7))
        self._draw_text("Maya, Jake, Rohan, Tess, You", self.font_small, (140, 140, 140), (frame.left + 55, frame.top + 31))
        pygame.draw.circle(self.screen, COLOR_TIMER_GREEN, (frame.right - 88, frame.top + 28), 4)
        self._draw_text("4 online", self.font_small, COLOR_TIMER_GREEN, (frame.right - 78, frame.top + 28), midleft=True)

        notice = pygame.Rect(frame.left + 18, frame.top + 62, frame.width - 36, 26)
        pygame.draw.rect(self.screen, (32, 32, 32), notice, border_radius=0)
        pygame.draw.rect(self.screen, (68, 68, 68), notice, width=1, border_radius=0)
        self._draw_text("Everyone in this group will see your reply.", self.font_small, COLOR_TIMER_AMBER, notice.center, center=True)

    def _draw_chat_thread(self, frame: pygame.Rect, arrived: int) -> None:
        """Draw the peer messages that have arrived so far, each with a neutral avatar and a read receipt."""
        for k, (name, initial, sent_at, message) in enumerate(PEER_MESSAGES[:arrived]):
            top = frame.top + 96 + k * 58
            # Avatar: neutral plate, peers are told apart by initial and name rather than by hue
            pygame.draw.circle(self.screen, COLOR_TEXT_MUTED, (frame.left + 32, top + 20), 13)
            self._draw_text(initial, self.font_small, COLOR_TEXT_PRIMARY, (frame.left + 32, top + 20), center=True)
            bubble = pygame.Rect(frame.left + 54, top, frame.width - 84, 50)
            pygame.draw.rect(self.screen, (38, 38, 38), bubble, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE, bubble, width=1, border_radius=0)
            self._draw_text(name, self.font_small, COLOR_TEXT_SECONDARY, (bubble.left + 12, bubble.top + 4))
            self._draw_text(message, self.font_small, (235, 235, 235), (bubble.left + 12, bubble.top + 24))
            self._draw_text(sent_at, self.font_caption, (115, 115, 115), (bubble.right - 36, bubble.top + 13), midright=True)
            self._draw_chat_ticks((bubble.right - 20, bubble.top + 13), double=True)

    def _draw_chat_ticks(self, pos: tuple[int, int], double: bool) -> None:
        """Draw a delivery tick, or a pair of ticks for a message everyone has seen."""
        for shift in ((-4, 0) if double else (0,)):
            x, y = pos[0] + shift, pos[1]
            pygame.draw.line(self.screen, COLOR_ACCENT_CYAN, (x - 5, y), (x - 2, y + 4), 2)
            pygame.draw.line(self.screen, COLOR_ACCENT_CYAN, (x - 2, y + 4), (x + 4, y - 4), 2)

    def _draw_chat_typing(self, frame: pygame.Rect, top: int, elapsed_s: float) -> None:
        """Draw the typing indicator shown until the participant replies (dots bob at about 0.8 Hz)."""
        box = pygame.Rect(frame.left + 54, top, 190, 30)
        pygame.draw.rect(self.screen, (32, 32, 32), box, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, box, width=1, border_radius=0)
        for dot in range(3):
            lift = int(math.sin(elapsed_s * 5.0 + dot * 0.8) * 3)
            pygame.draw.circle(self.screen, (164, 164, 164), (box.left + 18 + dot * 12, box.centery + lift), 3)
        self._draw_text("Jake is typing...", self.font_small, (140, 140, 140), (box.left + 58, box.centery), midleft=True)

    def _draw_chat_own_reply(self, frame: pygame.Rect, top: int, text: str) -> None:
        """Draw the participant's sent bubble. It is the same neutral grey for either reply."""
        lines = self._wrap_lines(text, self.font_small, 340)
        text_w = max(self.font_small.size(line)[0] for line in lines)
        step = self.font_small.get_linesize()
        bubble = pygame.Rect(0, top, max(150, text_w + 24), 30 + len(lines) * step)
        bubble.right = frame.right - 30
        pygame.draw.rect(self.screen, COLOR_HAIRLINE_SUBTLE, bubble, border_radius=0)
        self._draw_text("You  •  12:44", self.font_caption, (170, 170, 170), (bubble.left + 12, bubble.top + 5))
        for row, line in enumerate(lines):
            self._draw_text(line, self.font_small, COLOR_TEXT_PRIMARY, (bubble.left + 12, bubble.top + 23 + row * step))
        self._draw_chat_ticks((bubble.right - 14, bubble.top + 12), double=False)
