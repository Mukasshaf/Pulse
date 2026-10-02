"""Reusable UI widgets for Pulse: option cards, plates, figures, compass, meters, and the composure bar."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_BG,
    COLOR_HAIRLINE,
    COLOR_HAIRLINE_SUBTLE,
    COLOR_PRIMARY_ACTIVE,
    COLOR_PRIMARY_ROSSO,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_GREEN,
    COLOR_TIMER_RED,
)
from src.game.ui_core import UIRendererCore

Anchor = Literal["topleft", "midleft", "center", "midright"]


@dataclass(frozen=True)
class OptionStyle:
    """Resolved state and ink colours of one option card."""

    chosen: bool
    passed: bool
    ink: tuple[int, int, int]
    sub_ink: tuple[int, int, int]


class UIComponents(UIRendererCore):
    """Widgets shared by several screens and simulation skins."""

    def _draw_key_badge(self, rect: pygame.Rect, label: str, selected: bool = False, enabled: bool = True) -> None:
        """Draw a keyboard-key prompt: canvas fill, white label, Grigio border; inverted once chosen."""
        fill, ink = (COLOR_TEXT_PRIMARY, COLOR_BG) if selected else (COLOR_BG, COLOR_TEXT_PRIMARY)
        if not enabled:
            ink = COLOR_TEXT_MUTED
        pygame.draw.rect(self.screen, fill, rect, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TEXT_SECONDARY if enabled else COLOR_HAIRLINE_SUBTLE, rect, width=1, border_radius=0)
        self._draw_text(label, self.font_title, ink, rect.center, center=True)

    def _draw_tag(
        self,
        text: str,
        pos: tuple[int, int],
        anchor: Anchor = "midleft",
        ink: tuple[int, int, int] = COLOR_TEXT_SECONDARY,
        fill: tuple[int, int, int] | None = None,
        border: tuple[int, int, int] | None = None,
        font: pygame.font.Font | None = None,
    ) -> pygame.Rect:
        """Draw a small sharp-cornered label plate anchored at pos and return its rect."""
        tag_font = font if font is not None else self.font_mono_small
        text_w, text_h = tag_font.size(text)
        rect = pygame.Rect(0, 0, text_w + 20, text_h + 10)
        if anchor == "topleft":
            rect.topleft = pos
        elif anchor == "center":
            rect.center = pos
        elif anchor == "midright":
            rect.midright = pos
        else:
            rect.midleft = pos
        if fill is not None:
            pygame.draw.rect(self.screen, fill, rect, border_radius=0)
        if border is not None:
            pygame.draw.rect(self.screen, border, rect, width=1, border_radius=0)
        self._draw_text(text, tag_font, ink, rect.center, center=True)
        return rect

    def _draw_option_frame(
        self,
        rect: pygame.Rect,
        index: int,
        selected_index: int | None,
        accent: tuple[int, int, int] | None = None,
        dimmed: bool = False,
    ) -> OptionStyle:
        """Draw an option plate in its idle, chosen, or passed-over state and return its ink colours.

        White marks the participant's own choice on every skin. An accent is the option's described
        risk or its identity on the scene; it is a left rule drawn before and after the choice, so
        it never grades the choice.
        """
        chosen = selected_index == index and not dimmed
        passed = dimmed or (selected_index is not None and not chosen)
        fill = (44, 44, 44) if chosen else ((28, 28, 28) if passed else (34, 34, 34))
        border = COLOR_TEXT_PRIMARY if chosen else (COLOR_HAIRLINE if passed else COLOR_HAIRLINE_SUBTLE)
        pygame.draw.rect(self.screen, fill, rect, border_radius=0)
        pygame.draw.rect(self.screen, border, rect, width=1, border_radius=0)
        if accent is not None:
            rule = self._mix(accent, COLOR_BG, 0.6) if passed else accent
            pygame.draw.rect(self.screen, rule, (rect.left + 1, rect.top + 1, 4, rect.height - 2), border_radius=0)
        ink = COLOR_TEXT_SECONDARY if passed else COLOR_TEXT_PRIMARY
        return OptionStyle(chosen, passed, ink, COLOR_TEXT_MUTED if passed else COLOR_TEXT_SECONDARY)

    def _draw_option_card(
        self,
        rect: pygame.Rect,
        key: int,
        text: str,
        index: int,
        selected_index: int | None,
        detail: str = "",
        accent: tuple[int, int, int] | None = None,
        font: pygame.font.Font | None = None,
        plate: str = "SELECTED",
        dimmed: bool = False,
    ) -> OptionStyle:
        """Draw a full option row: key badge, option text, optional detail, and the white plate once chosen."""
        style = self._draw_option_frame(rect, index, selected_index, accent, dimmed)
        badge = pygame.Rect(rect.left + 18, rect.centery - 18, 36, 36)
        self._draw_key_badge(badge, str(key), selected=style.chosen, enabled=not style.passed)

        # The plate's width is reserved in every state so the text never reflows when a choice is made
        plate_w = self.font_mono_small.size(plate)[0] + 20
        text_left = badge.right + 18
        text_w = rect.right - 36 - plate_w - text_left
        main_font = font if font is not None else self.font_body
        if detail:
            # Both parts wrap at a fixed size, so every card of a set is set in the same type
            rows = [(line, main_font, style.ink) for line in self._wrap_lines(text, main_font, text_w)]
            rows += [(line, self.font_small, style.sub_ink) for line in self._wrap_lines(detail, self.font_small, text_w)]
            line_y = rect.centery - sum(row_font.get_linesize() + 2 for _, row_font, _ in rows) // 2
            for line, row_font, ink in rows:
                self._draw_text(line, row_font, ink, (text_left, line_y))
                line_y += row_font.get_linesize() + 2
        else:
            self._draw_wrapped_text(text, main_font, style.ink, pygame.Rect(text_left, rect.top + 8, text_w, rect.height - 16), spacing=3, center_v=True)
        if style.chosen:
            self._draw_tag(plate, (rect.right - 18, rect.centery), anchor="midright", ink=COLOR_BG, fill=COLOR_TEXT_PRIMARY)
        return style

    @staticmethod
    def _split_option(text: str) -> tuple[str, str]:
        """Split registry option text at its dash into (action, trade-off), so the screen shows what is logged."""
        head, sep, tail = text.partition(" — ")
        if not sep:
            return (text, "")
        return (head.strip(), tail.strip()[:1].upper() + tail.strip()[1:])

    def _draw_footer_prompt(self, idle_text: str, committed: bool = False, outcome: str = "RESPONSE RECORDED") -> None:
        """Draw the one-line instruction at the foot of a decision screen; once it is over it asks for stillness."""
        text = f"{outcome}  •  PLEASE REMAIN STILL UNTIL THE TIMER ENDS" if committed else idle_text
        self._draw_text(text, self.font_small, COLOR_TEXT_SECONDARY if committed else (140, 140, 140), (self.width // 2, self.FOOTER_Y), center=True)

    def _draw_silhouette(self, center_x: int, base_y: int, height: int, shade: int = 44, collar: bool = False) -> None:
        """Draw a featureless head-and-shoulders figure standing on base_y; observers stay unreadable by design."""
        head_r = max(5, int(height * 0.21))
        shoulder_w = int(height * 0.52)
        shoulder_y = base_y - int(height * 0.50)
        slope = int(height * 0.10)
        neck_w = max(3, head_r // 2)
        body = (shade, shade, shade)
        pts = [
            (center_x - shoulder_w, base_y),
            (center_x + shoulder_w, base_y),
            (center_x + int(shoulder_w * 0.80), shoulder_y + slope),
            (center_x + neck_w + 3, shoulder_y),
            (center_x - neck_w - 3, shoulder_y),
            (center_x - int(shoulder_w * 0.80), shoulder_y + slope),
        ]
        pygame.draw.polygon(self.screen, body, pts)
        pygame.draw.rect(self.screen, body, (center_x - neck_w, shoulder_y - slope, neck_w * 2, slope + 2), border_radius=0)
        if collar:
            pygame.draw.polygon(self.screen, (shade + 90, shade + 90, shade + 90), [(center_x - neck_w - 2, shoulder_y), (center_x + neck_w + 2, shoulder_y), (center_x, shoulder_y + slope + 4)])
        head_rect = pygame.Rect(center_x - head_r, base_y - height, head_r * 2, int(head_r * 2.3))
        pygame.draw.ellipse(self.screen, (shade + 14, shade + 14, shade + 14), head_rect)

    def _draw_window_chrome(self, rect: pygame.Rect, title: str, right_text: str = "", mono: bool = False) -> pygame.Rect:
        """Draw a neutral application title bar across the top of rect and return the bar's rect."""
        bar = pygame.Rect(rect.left, rect.top, rect.width, 36)
        pygame.draw.rect(self.screen, (36, 36, 36), bar, border_radius=0)
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (bar.left, bar.bottom), (bar.right, bar.bottom), 1)
        # Window controls: neutral square outlines (no OS-specific traffic-light colours)
        for ctl_x in (bar.left + 18, bar.left + 34, bar.left + 50):
            pygame.draw.rect(self.screen, COLOR_HAIRLINE_SUBTLE, (ctl_x - 4, bar.centery - 4, 9, 9), width=1, border_radius=0)
        self._draw_text(title, self.font_mono_small if mono else self.font_small, (200, 200, 200), (bar.left + 70, bar.centery), midleft=True)
        if right_text:
            self._draw_text(right_text, self.font_small, (123, 123, 123), (bar.right - 20, bar.centery), midright=True)
        return bar

    def _draw_spinner(self, center: tuple[int, int], radius: int, turns: float) -> None:
        """Draw a ring of eight square marks whose brightest mark has advanced by `turns` revolutions."""
        head = int(turns * 8) % 8
        size = max(3, radius // 4)
        for mark in range(8):
            angle = mark * (math.pi / 4.0) - math.pi / 2.0
            age = (head - mark) % 8
            colour = self._mix(COLOR_ACCENT_CYAN, COLOR_BG, min(0.85, age * 0.14))
            mx = center[0] + int(radius * math.cos(angle))
            my = center[1] + int(radius * math.sin(angle))
            pygame.draw.rect(self.screen, colour, (mx - size // 2, my - size // 2, size, size), border_radius=0)

    def _draw_progress_line(self, rect: pygame.Rect, fraction: float, colour: tuple[int, int, int] = COLOR_TEXT_SECONDARY) -> None:
        """Draw a thin horizontal track with a fill proportional to fraction."""
        frac = max(0.0, min(1.0, fraction))
        pygame.draw.rect(self.screen, (40, 40, 40), rect, border_radius=0)
        if frac > 0.0:
            pygame.draw.rect(self.screen, colour, (rect.left, rect.top, int(rect.width * frac), rect.height), border_radius=0)

    def _draw_compass(self, center: tuple[int, int], radius: int, angle_deg: float, show_cardinals: bool = True) -> None:
        """Render a minimalist compass rose with rotating needle."""
        cx, cy = center
        # Outer dial ring
        pygame.draw.circle(self.screen, (28, 28, 28), (cx, cy), radius)
        pygame.draw.circle(self.screen, COLOR_HAIRLINE_SUBTLE, (cx, cy), radius, width=1)
        pygame.draw.circle(self.screen, COLOR_HAIRLINE, (cx, cy), radius - 6, width=1)

        # Cardinal tick marks & labels
        cardinals = [("N", 0), ("E", 90), ("S", 180), ("W", 270)]
        for label, deg in cardinals:
            rad = math.radians(deg - 90)
            tx1 = cx + int((radius - 5) * math.cos(rad))
            ty1 = cy + int((radius - 5) * math.sin(rad))
            tx2 = cx + int((radius - 1) * math.cos(rad))
            ty2 = cy + int((radius - 1) * math.sin(rad))
            pygame.draw.line(self.screen, COLOR_HAIRLINE_SUBTLE, (tx1, ty1), (tx2, ty2), 2)

            if show_cardinals:
                lx = cx + int((radius + 11) * math.cos(rad))
                ly = cy + int((radius + 11) * math.sin(rad))
                col = COLOR_PRIMARY_ROSSO if label == "N" else COLOR_TEXT_SECONDARY
                self._draw_text(label, self.font_mono_small, col, (lx, ly), center=True)

        # Intermediate ticks
        for deg in (30, 60, 120, 150, 210, 240, 300, 330):
            rad = math.radians(deg - 90)
            tx1 = cx + int((radius - 4) * math.cos(rad))
            ty1 = cy + int((radius - 4) * math.sin(rad))
            tx2 = cx + int((radius - 1) * math.cos(rad))
            ty2 = cy + int((radius - 1) * math.sin(rad))
            pygame.draw.line(self.screen, COLOR_HAIRLINE, (tx1, ty1), (tx2, ty2), 1)

        # Rotating needle: white north tip, grey south tip (Rosso stays reserved for stress triggers)
        n_rad = math.radians(angle_deg - 90)
        s_rad = n_rad + math.pi
        w_rad = n_rad + math.pi / 2
        e_rad = n_rad - math.pi / 2

        tip_len = radius - 7
        side_len = max(4, radius // 7)

        n_pt = (cx + int(tip_len * math.cos(n_rad)), cy + int(tip_len * math.sin(n_rad)))
        s_pt = (cx + int(tip_len * math.cos(s_rad)), cy + int(tip_len * math.sin(s_rad)))
        w_pt = (cx + int(side_len * math.cos(w_rad)), cy + int(side_len * math.sin(w_rad)))
        e_pt = (cx + int(side_len * math.cos(e_rad)), cy + int(side_len * math.sin(e_rad)))

        pygame.draw.polygon(self.screen, COLOR_TEXT_PRIMARY, [n_pt, w_pt, (cx, cy)])
        pygame.draw.polygon(self.screen, (200, 200, 200), [n_pt, e_pt, (cx, cy)])
        pygame.draw.polygon(self.screen, COLOR_TEXT_MUTED, [s_pt, w_pt, (cx, cy)])
        pygame.draw.polygon(self.screen, (84, 84, 84), [s_pt, e_pt, (cx, cy)])

        # Center pivot
        pygame.draw.circle(self.screen, (240, 240, 240), (cx, cy), 4)
        pygame.draw.circle(self.screen, (32, 32, 32), (cx, cy), 2)

    def draw_peer_average_bar(self, user_frac: float, peer_frac: float) -> None:
        """Render MIST social comparison progress bars."""
        rect = pygame.Rect(self.width // 2 - 320, 100, 640, 50)
        self._draw_card(rect)
        # Peer bar (red)
        self._draw_text("Peer Group Average:", self.font_small, COLOR_TEXT_SECONDARY, (rect.left + 10, rect.top + 8))
        pygame.draw.rect(self.screen, (36, 36, 36), (rect.left + 170, rect.top + 10, 450, 12), border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TIMER_RED, (rect.left + 170, rect.top + 10, int(450 * peer_frac), 12), border_radius=0)
        # User bar (cyan)
        self._draw_text("Your Progress:", self.font_small, COLOR_TEXT_SECONDARY, (rect.left + 10, rect.top + 28))
        pygame.draw.rect(self.screen, (36, 36, 36), (rect.left + 170, rect.top + 30, 450, 12), border_radius=0)
        pygame.draw.rect(self.screen, COLOR_ACCENT_CYAN, (rect.left + 170, rect.top + 30, int(450 * user_frac), 12), border_radius=0)

    def draw_instability_gauge(self, fraction: float, pos: tuple[int, int]) -> None:
        """Render system instability meter for BART and Accumulator."""
        frac = max(0.0, min(1.0, fraction))
        cx, cy = pos
        rect = pygame.Rect(cx - 180, cy, 360, 20)
        self._draw_text("System Instability Meter", self.font_small, COLOR_TEXT_SECONDARY, (cx, cy - 14), center=True)
        pygame.draw.rect(self.screen, (36, 36, 36), rect, border_radius=0)
        gauge_color = COLOR_TIMER_GREEN if frac < 0.4 else (COLOR_TIMER_AMBER if frac < 0.75 else COLOR_TIMER_RED)
        pygame.draw.rect(self.screen, gauge_color, (rect.left, rect.top, int(rect.width * frac), rect.height), border_radius=0)

    def draw_team_chat(self, pos: tuple[int, int]) -> None:
        """Render the four-peer vote strip used by the skinless fallback layout for Peer Influence."""
        x, y = pos
        rect = pygame.Rect(x, y, self.width - 120, 95)
        self._draw_card(rect, (48, 48, 48))
        self._draw_text("Project Team Discussion & Submissions (4/4 Completed)", self.font_small, COLOR_TEXT_SECONDARY, (rect.left + 20, rect.top + 8))
        avatars = ["Dev 1 (Lead)", "Dev 2", "Dev 3", "Dev 4"]
        for i, name in enumerate(avatars):
            ax = rect.left + 25 + i * 280
            ay = rect.top + 34
            pygame.draw.circle(self.screen, COLOR_TEXT_MUTED, (ax + 14, ay + 14), 14)
            self._draw_text(str(i + 1), self.font_small, COLOR_TEXT_PRIMARY, (ax + 14, ay + 14), center=True)
            self._draw_text(f"{name}: Vote Option 1", self.font_small, COLOR_TEXT_PRIMARY, (ax + 35, ay + 4))
        self._draw_text("Notice: Your vote is visible to all team members.", self.font_small, COLOR_ACCENT_CYAN, (rect.left + 20, rect.bottom - 22))

    def draw_evaluator_panel(self, pos: tuple[int, int]) -> None:
        """Render the neutral evaluator panel used by the skinless fallback layout."""
        x, y = pos
        rect = pygame.Rect(x, y, 300, 110)
        self._draw_card(rect, (48, 48, 48))
        self._draw_text("Evaluation Committee (Active)", self.font_small, COLOR_TEXT_SECONDARY, (rect.centerx, rect.top + 12), center=True)
        for i in range(3):
            self._draw_silhouette(rect.left + 65 + i * 85, rect.bottom - 8, 62, shade=70)

    def draw_composure_bar(
        self,
        fraction: float | None,
        pos: tuple[int, int],
        width: int | None = None,
        is_drone_active: bool = False,
    ) -> None:
        """Render MPU6050 biofeedback composure bar; fraction=None means no live telemetry (standby)."""
        live = fraction is not None
        frac = max(0.0, min(1.0, fraction)) if fraction is not None else 0.0
        x, y = pos
        bar_w = width if width is not None else (self.width - 100)
        panel_rect = pygame.Rect(x, y - 18, bar_w, 68)

        # Panel card background
        pygame.draw.rect(self.screen, (32, 32, 32), panel_rect, border_radius=0)
        border_col = (54, 54, 54) if not is_drone_active else COLOR_PRIMARY_ACTIVE
        pygame.draw.rect(self.screen, border_col, panel_rect, width=1, border_radius=0)

        # Header / Label
        self._draw_text("Physiological Composure Analysis: Active" if live else "Physiological Composure Analysis: Standby", self.font_small, COLOR_ACCENT_CYAN, (x + 14, panel_rect.top + 10), midleft=True)

        # Dynamic smooth color transition from green -> amber -> red
        if frac > 0.6:
            col = self._mix(COLOR_TIMER_AMBER, COLOR_TIMER_GREEN, (frac - 0.6) / 0.4)
            status_text = f"STABILITY: {int(frac * 100)}% | MOTION: STEADY"
            status_col = COLOR_TIMER_GREEN
        elif frac > 0.3:
            col = self._mix(COLOR_TIMER_RED, COLOR_TIMER_AMBER, (frac - 0.3) / 0.3)
            status_text = f"STABILITY: {int(frac * 100)}% | MOTION: ELEVATED"
            status_col = COLOR_TIMER_AMBER
        else:
            col = COLOR_TIMER_RED
            status_text = f"STABILITY: {int(frac * 100)}% | MOTION: HIGH"
            status_col = COLOR_TIMER_RED

        if not live:
            status_text, status_col = "TELEMETRY LINK: STANDBY", COLOR_TEXT_SECONDARY
        self._draw_text(status_text, self.font_small, status_col, (panel_rect.right - 14, panel_rect.top + 10), midright=True)

        # Track and Bar
        track_rect = pygame.Rect(x + 14, panel_rect.top + 26, bar_w - 28, 14)
        pygame.draw.rect(self.screen, (24, 24, 24), track_rect, border_radius=0)
        fill_w = int(track_rect.width * frac)
        if fill_w > 0:
            pygame.draw.rect(self.screen, col, (track_rect.left, track_rect.top, fill_w, track_rect.height), border_radius=0)

        # Telemetry info line
        sub_text = "HARDWARE TELEMETRY: WRIST MOTION SENSOR (CALIBRATED TO YOUR RESTING BASELINE)"
        self._draw_text(sub_text, self.font_mono_small, (118, 118, 118), (x + 14, panel_rect.top + 50), midleft=True)

        if is_drone_active:
            drone_tag = "[ TIME CRITICAL ]"
            self._draw_text(drone_tag, self.font_mono_small, COLOR_TIMER_AMBER if frac > 0.3 else COLOR_TIMER_RED, (panel_rect.right - 14, panel_rect.top + 50), midright=True)
