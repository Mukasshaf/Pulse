"""Reusable UI widgets for Pulse: compass, meters, panels, and the composure bar."""
from __future__ import annotations

import math

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

        # Rotating needle (red North tip, cyan South tip)
        n_rad = math.radians(angle_deg - 90)
        s_rad = n_rad + math.pi
        w_rad = n_rad + math.pi / 2
        e_rad = n_rad - math.pi / 2

        tip_len = radius - 7
        side_len = 5

        n_pt = (cx + int(tip_len * math.cos(n_rad)), cy + int(tip_len * math.sin(n_rad)))
        s_pt = (cx + int(tip_len * math.cos(s_rad)), cy + int(tip_len * math.sin(s_rad)))
        w_pt = (cx + int(side_len * math.cos(w_rad)), cy + int(side_len * math.sin(w_rad)))
        e_pt = (cx + int(side_len * math.cos(e_rad)), cy + int(side_len * math.sin(e_rad)))

        # North needle polygon (Rosso Corsa)
        pygame.draw.polygon(self.screen, COLOR_PRIMARY_ROSSO, [n_pt, w_pt, (cx, cy)])
        pygame.draw.polygon(self.screen, COLOR_PRIMARY_ACTIVE, [n_pt, e_pt, (cx, cy)])

        # South needle polygon (cyan telemetry)
        pygame.draw.polygon(self.screen, COLOR_ACCENT_CYAN, [s_pt, w_pt, (cx, cy)])
        pygame.draw.polygon(self.screen, COLOR_PRIMARY_ROSSO, [s_pt, e_pt, (cx, cy)])

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
        """Render Asch conformity group display with 4 avatars for Peer Influence."""
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
        """Render simulated neutral evaluator panel for TSST (Domain 7)."""
        x, y = pos
        rect = pygame.Rect(x, y, 300, 110)
        self._draw_card(rect, (48, 48, 48))
        self._draw_text("Evaluation Committee (Active)", self.font_small, COLOR_TEXT_SECONDARY, (rect.centerx, rect.top + 12), center=True)
        for i in range(3):
            px = rect.left + 35 + i * 85
            py = rect.top + 55
            pygame.draw.circle(self.screen, (75, 75, 75), (px, py), 22)
            pygame.draw.circle(self.screen, (48, 48, 48), (px, py), 18)
            # Neutral line mouth
            pygame.draw.line(self.screen, COLOR_TEXT_SECONDARY, (px - 8, py + 6), (px + 8, py + 6), 2)

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
            t = (frac - 0.6) / 0.4
            col = (
                int(COLOR_TIMER_AMBER[0] * (1.0 - t) + COLOR_TIMER_GREEN[0] * t),
                int(COLOR_TIMER_AMBER[1] * (1.0 - t) + COLOR_TIMER_GREEN[1] * t),
                int(COLOR_TIMER_AMBER[2] * (1.0 - t) + COLOR_TIMER_GREEN[2] * t),
            )
            status_text = f"STABILITY: {int(frac * 100)}% | MOTION: STEADY"
            status_col = COLOR_TIMER_GREEN
        elif frac > 0.3:
            t = (frac - 0.3) / 0.3
            col = (
                int(COLOR_TIMER_RED[0] * (1.0 - t) + COLOR_TIMER_AMBER[0] * t),
                int(COLOR_TIMER_RED[1] * (1.0 - t) + COLOR_TIMER_AMBER[1] * t),
                int(COLOR_TIMER_RED[2] * (1.0 - t) + COLOR_TIMER_AMBER[2] * t),
            )
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
