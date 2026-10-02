"""Simulation skin `group_chat` for scenario `peer_influence_a`."""
from __future__ import annotations

import math

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_HAIRLINE,
    COLOR_HAIRLINE_SUBTLE,
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


class GroupChatSkin(UIComponents):
    """Renders the `group_chat` decision skin."""

    def _draw_skin_group_chat(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render group_chat simulation skin: mobile chat interface simulating Asch conformity."""
        jx, jy = effects.jitter_offset

        # Device Frame (Smartphone Mockup in screen center)
        frame_w = 560
        frame_h = 608
        frame_x = (self.width - frame_w) // 2 + jx
        frame_y = 94 + jy
        frame_rect = pygame.Rect(frame_x, frame_y, frame_w, frame_h)

        # Drop shadow
        pygame.draw.rect(self.screen, (16, 16, 16), (frame_x + 6, frame_y + 6, frame_w, frame_h), border_radius=0)
        # Device background
        pygame.draw.rect(self.screen, (28, 28, 28), frame_rect, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE_SUBTLE, frame_rect, width=1, border_radius=0)

        # Chat Header: Group title and online status
        header_rect = pygame.Rect(frame_x, frame_y, frame_w, 54)
        pygame.draw.rect(self.screen, (36, 36, 36), header_rect, border_top_left_radius=0, border_top_right_radius=0)
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (frame_x, frame_y + 54), (frame_x + frame_w, frame_y + 54), 1)

        # Group avatar circle
        pygame.draw.circle(self.screen, (54, 54, 54), (frame_x + 30, frame_y + 27), 16)
        self._draw_text("CG", self.font_small, COLOR_TEXT_PRIMARY, (frame_x + 30, frame_y + 27), center=True)

        # Header titles
        self._draw_text("Class Group (5 members)", self.font_body, COLOR_TEXT_PRIMARY, (frame_x + 55, frame_y + 11))
        self._draw_text("Maya, Jake, Rohan, Tess, You", self.font_small, (140, 140, 140), (frame_x + 55, frame_y + 32))

        # Online indicator
        dot_cx = frame_x + frame_w - 85
        pygame.draw.circle(self.screen, COLOR_TIMER_GREEN, (dot_cx, frame_y + 27), 4)
        self._draw_text("4 online", self.font_small, COLOR_TIMER_GREEN, (dot_cx + 10, frame_y + 27), midleft=True)

        # Public Visibility Cue banner inside chat
        vis_banner = pygame.Rect(frame_x + 24, frame_y + 62, frame_w - 48, 26)
        pygame.draw.rect(self.screen, (30, 30, 30), vis_banner, border_radius=0)
        pygame.draw.rect(self.screen, (68, 68, 68), vis_banner, width=1, border_radius=0)
        self._draw_text("Notice: Your response will be visible to all members.", self.font_small, COLOR_TIMER_AMBER, vis_banner.center, center=True)

        # 4 Incoming Peer Votes (Asch conformity: all vote conforming)
        peers = [
            ("Maya", "M.", "12:41 PM"),
            ("Jake", "J.", "12:42 PM"),
            ("Rohan", "R.", "12:42 PM"),
            ("Tess", "T.", "12:43 PM"),
        ]
        bubble_y_start = frame_y + 94
        bubble_w = frame_w - 75
        bubble_h = 52
        bubble_gap = 8

        for k, (name, init, time_str) in enumerate(peers):
            by = bubble_y_start + k * (bubble_h + bubble_gap)
            # Avatar: neutral plate, peers are told apart by initial and name rather than by hue
            avatar_cx = frame_x + 28
            avatar_cy = by + 20
            pygame.draw.circle(self.screen, COLOR_TEXT_MUTED, (avatar_cx, avatar_cy), 13)
            self._draw_text(init, self.font_small, COLOR_TEXT_PRIMARY, (avatar_cx, avatar_cy), center=True)

            # Chat bubble
            bubble_rect = pygame.Rect(frame_x + 48, by, bubble_w, bubble_h)
            pygame.draw.rect(self.screen, (38, 38, 38), bubble_rect, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE, bubble_rect, width=1, border_radius=0)

            # Name and timestamp
            self._draw_text(name, self.font_small, COLOR_TEXT_SECONDARY, (bubble_rect.left + 12, bubble_rect.top + 4))
            self._draw_text(time_str, self.font_small, (115, 115, 115), (bubble_rect.right - 10, bubble_rect.top + 14), midright=True)

            # Conforming message text
            self._draw_text(
                "Share it — it's already circulating everywhere.",
                self.font_small,
                (235, 235, 235),
                (bubble_rect.left + 12, bubble_rect.top + 23),
            )

            # Read receipts: double blue checkmarks (procedural lines)
            rcx = bubble_rect.right - 24
            rcy = bubble_rect.bottom - 13
            # First checkmark
            pygame.draw.line(self.screen, COLOR_ACCENT_CYAN, (rcx - 10, rcy), (rcx - 7, rcy + 4), 2)
            pygame.draw.line(self.screen, COLOR_ACCENT_CYAN, (rcx - 7, rcy + 4), (rcx - 2, rcy - 4), 2)
            # Second checkmark
            pygame.draw.line(self.screen, COLOR_ACCENT_CYAN, (rcx - 6, rcy), (rcx - 3, rcy + 4), 2)
            pygame.draw.line(self.screen, COLOR_ACCENT_CYAN, (rcx - 3, rcy + 4), (rcx + 2, rcy - 4), 2)

        # Typing Indicator or Outgoing Reply
        typing_y = bubble_y_start + 4 * (bubble_h + bubble_gap)
        if selected_index is None:
            type_rect = pygame.Rect(frame_x + 48, typing_y, 140, 28)
            pygame.draw.rect(self.screen, (32, 32, 32), type_rect, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE, type_rect, width=1, border_radius=0)
            ticks = pygame.time.get_ticks()
            for d in range(3):
                phase = (ticks / 200.0 + d * 0.8) % (2.0 * math.pi)
                dy = int(math.sin(phase) * 3)
                dot_x = type_rect.left + 22 + d * 14
                dot_y = type_rect.centery + dy
                pygame.draw.circle(self.screen, (164, 164, 164), (dot_x, dot_y), 3)
            self._draw_text("typing...", self.font_small, (125, 125, 125), (type_rect.left + 64, type_rect.top + 6))
        else:
            # Participant's sent message bubble (right-aligned, wrapped to avoid blowout)
            opt_text = scenario.options[selected_index].text if selected_index < len(scenario.options) else ""
            out_w = 370
            out_h = 56
            out_rect = pygame.Rect(frame_x + frame_w - out_w - 20, typing_y - 2, out_w, out_h)
            # Same neutral bubble for either reply: the colour must not grade the participant's choice
            pygame.draw.rect(self.screen, COLOR_HAIRLINE_SUBTLE, out_rect, border_radius=0)
            text_rect = pygame.Rect(out_rect.left + 10, out_rect.top + 6, out_rect.width - 20, out_rect.height - 12)
            self._draw_wrapped_text(opt_text, self.font_small, COLOR_TEXT_PRIMARY, text_rect, spacing=2)

        # Quick-Reply Action Area at bottom of device
        action_y = frame_y + 406
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (frame_x, action_y), (frame_x + frame_w, action_y), 1)
        self._draw_text(
            "QUICK REPLY (KEYS 1 – 2):",
            self.font_small,
            (135, 135, 135),
            (frame_x + frame_w // 2, action_y + 8),
            center=True,
        )

        chip_h = 82
        chip_gap = 10
        for i, opt in enumerate(scenario.options):
            cy = action_y + 26 + i * (chip_h + chip_gap)
            chip_rect = pygame.Rect(frame_x + 18, cy, frame_w - 36, chip_h)
            is_sel = (selected_index == i)

            # The participant's own choice is marked in white; Rosso stays reserved for stress triggers
            bg = (37, 37, 37) if is_sel else (28, 28, 28)
            border = COLOR_TEXT_PRIMARY if is_sel else COLOR_HAIRLINE

            pygame.draw.rect(self.screen, bg, chip_rect, border_radius=0)
            pygame.draw.rect(self.screen, border, chip_rect, width=1, border_radius=0)

            badge = pygame.Rect(chip_rect.left + 12, chip_rect.centery - 16, 32, 32)
            self._draw_key_badge(badge, str(opt.key), selected=is_sel)

            text_rect = pygame.Rect(badge.right + 12, chip_rect.top + 8, chip_rect.width - 135, chip_rect.height - 16)
            self._draw_wrapped_text(opt.text, self.font_small, COLOR_TEXT_PRIMARY, text_rect, spacing=3, center_v=True)

        return True
