"""Post-decision waiting screens for Pulse (delay-wait and future-uncertainty scenarios)."""
from __future__ import annotations

import math

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_BG,
    COLOR_CARD_BG,
    COLOR_HAIRLINE,
    COLOR_HAIRLINE_SUBTLE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_RED,
    COMPASS_SPIN_MAX_RPM,
)
from src.game.ui_components import UIComponents


class UIPostWait(UIComponents):
    """Renders the uninformative waiting phase between a committed choice and its consequence."""

    def draw_post_wait(self, text: str, elapsed_fraction: float) -> None:
        """Render delay wait screen for Future Uncertainty and Impulsivity domains."""
        self.screen.fill(COLOR_BG)

        # Check if this is the document_workspace delay wait animation
        if "reviewing" in text.lower() or "changes" in text.lower():
            # 1. Render Document Workspace background
            win_w = 920
            win_h = 440
            win_rect = pygame.Rect(self.width // 2 - win_w // 2, 70, win_w, win_h)

            pygame.draw.rect(self.screen, (28, 28, 28), win_rect, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE, win_rect, width=1, border_radius=0)

            # Title bar
            hdr_rect = pygame.Rect(win_rect.left, win_rect.top, win_w, 36)
            pygame.draw.rect(self.screen, (30, 30, 30), hdr_rect, border_top_left_radius=0, border_top_right_radius=0)
            self._draw_text("Term_Paper_Final_Draft_v4.docx — Automated Assessment", self.font_small, COLOR_TEXT_PRIMARY, (win_rect.centerx, hdr_rect.centery), center=True)

            # Document sheet canvas
            canvas_rect = pygame.Rect(win_rect.left + 24, hdr_rect.bottom + 16, win_w - 48, win_h - 80)
            pygame.draw.rect(self.screen, (244, 244, 244), canvas_rect, border_radius=0)

            # Simulated text lines on canvas
            margin_x = canvas_rect.left + 45
            margin_w = canvas_rect.width - 90
            for line_idx in range(16):
                ly = canvas_rect.top + 20 + line_idx * 18
                lw = int(margin_w * (0.92 if line_idx % 4 != 3 else 0.55))
                pygame.draw.rect(self.screen, (195, 195, 195), (margin_x, ly, lw, 7), border_radius=0)

            # 2. Animated Document Scanner Line moving vertically over the text
            scan_cycle = (elapsed_fraction * 15.0 / 2.5) % 1.0
            scan_y = canvas_rect.top + int(scan_cycle * canvas_rect.height)
            # Laser beam line
            pygame.draw.line(self.screen, COLOR_ACCENT_CYAN, (canvas_rect.left, scan_y), (canvas_rect.right, scan_y), 3)
            # Laser glow lines
            glow_col = self._mix(COLOR_ACCENT_CYAN, COLOR_TEXT_PRIMARY, 0.5)
            pygame.draw.line(self.screen, glow_col, (canvas_rect.left, scan_y - 1), (canvas_rect.right, scan_y - 1), 1)
            pygame.draw.line(self.screen, glow_col, (canvas_rect.left, scan_y + 1), (canvas_rect.right, scan_y + 1), 1)

            # 3. Central Analysis Engine Modal Card
            modal_w = 640
            modal_h = 190
            modal_rect = pygame.Rect(self.width // 2 - modal_w // 2, self.height // 2 - 75, modal_w, modal_h)
            self._draw_card(modal_rect, border_color=COLOR_ACCENT_CYAN, bg_color=COLOR_CARD_BG)

            # 4. Slow Uncalibrated Spinning Progress Ring
            ring_cx = modal_rect.left + 55
            ring_cy = modal_rect.top + 65
            ring_r = 26
            pygame.draw.circle(self.screen, (44, 44, 44), (ring_cx, ring_cy), ring_r, width=3)
            angle = (elapsed_fraction * 360 * 3.0) % 360
            arc_rect = pygame.Rect(ring_cx - ring_r, ring_cy - ring_r, ring_r * 2, ring_r * 2)
            pygame.draw.arc(self.screen, COLOR_ACCENT_CYAN, arc_rect, math.radians(angle), math.radians(angle + 110), 4)

            # 5. Animated Typing Indicator: "AI Analysis Engine reviewing revisions..."
            num_dots = int(elapsed_fraction * 15 * 3) % 4
            dots_str = "." * num_dots
            typing_text = f"AI Analysis Engine reviewing revisions{dots_str}"
            self._draw_text(typing_text, self.font_title, COLOR_TEXT_PRIMARY, (ring_cx + 42, ring_cy - 14))
            self._draw_text("Evaluating deep structural revisions and citation depth...", self.font_small, COLOR_TEXT_SECONDARY, (ring_cx + 42, ring_cy + 14))

            # Uncalibrated delay message
            self._draw_text("Uncalibrated Turnaround: Please wait for algorithmic verification...", self.font_small, COLOR_TIMER_AMBER, (modal_rect.centerx, modal_rect.bottom - 24), center=True)

            self._draw_text("Please remain still during analysis.", self.font_small, (140, 140, 140), (self.width // 2, self.height - 40), center=True)
            return

        # Check if this is the fork_map delay wait animation (Scenario A)
        elif "synthesizing" in text.lower() or "projections" in text.lower() or "crossroads" in text.lower() or "selection" in text.lower():
            # 1. Render Fork Map scene in post-decision suspension
            cx = self.width // 2
            fork_node_y = 380
            trunk_bottom_y = 480

            # Background grid lines
            for gy in range(80, 680, 60):
                pygame.draw.line(self.screen, (20, 20, 20), (50, gy), (self.width - 50, gy), 1)

            # Stem
            stem_rect = pygame.Rect(cx - 18, fork_node_y, 36, trunk_bottom_y - fork_node_y)
            pygame.draw.rect(self.screen, (24, 24, 24), stem_rect)
            pygame.draw.line(self.screen, (60, 60, 60), (stem_rect.left, stem_rect.top), (stem_rect.left, stem_rect.bottom), 2)
            pygame.draw.line(self.screen, (60, 60, 60), (stem_rect.right, stem_rect.top), (stem_rect.right, stem_rect.bottom), 2)

            # Fork junction
            pygame.draw.circle(self.screen, (36, 36, 36), (cx, fork_node_y), 20)
            pygame.draw.circle(self.screen, (84, 84, 84), (cx, fork_node_y), 20, width=2)

            # Branch A points
            p0 = (float(cx), float(fork_node_y))
            p1 = (float(cx - 100), float(fork_node_y - 90))
            p2 = (float(cx - 310), float(fork_node_y - 180))
            pts_a = [
                (int((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]),
                 int((1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]))
                for t in [s / 20.0 for s in range(21)]
            ]

            # Branch B points
            p1_r = (float(cx + 100), float(fork_node_y - 90))
            p2_r = (float(cx + 310), float(fork_node_y - 180))
            pts_b = [
                (int((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1_r[0] + t ** 2 * p2_r[0]),
                 int((1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1_r[1] + t ** 2 * p2_r[1]))
                for t in [s / 20.0 for s in range(21)]
            ]

            # Dim unchosen path and illuminate chosen branch
            chosen = self._last_fork_choice
            if chosen == 0:
                # Path A illuminated, Path B dimmed
                pygame.draw.lines(self.screen, self._mix(COLOR_ACCENT_CYAN, COLOR_BG, 0.65), False, pts_a, 16)
                pygame.draw.lines(self.screen, COLOR_ACCENT_CYAN, False, pts_a, 6)
                pygame.draw.lines(self.screen, (44, 44, 44), False, pts_b, 4)
            else:
                # Path B illuminated, Path A dimmed
                pygame.draw.lines(self.screen, (44, 44, 44), False, pts_a, 4)
                pygame.draw.lines(self.screen, self._mix(COLOR_TIMER_AMBER, COLOR_BG, 0.65), False, pts_b, 16)
                for d_i in range(0, len(pts_b) - 1, 2):
                    pygame.draw.line(self.screen, COLOR_TIMER_AMBER, pts_b[d_i], pts_b[d_i + 1], 6)

            # Accelerated Compass Rose at top right
            # 12 s wait at COMPASS_SPIN_MAX_RPM (4 RPM) is 0.8 of a revolution
            comp_angle = (elapsed_fraction * 360.0 * COMPASS_SPIN_MAX_RPM * 0.2) % 360.0
            self._draw_compass((self.width - 95, 114), 34, comp_angle, show_cardinals=False)
            self._draw_text("[ COMPASS SPINNING ]", self.font_mono_small, COLOR_TIMER_RED, (self.width - 95, 162), center=True)

            # Central Post-Decision Suspension Modal Card
            modal_w = 740
            modal_h = 220
            modal_rect = pygame.Rect(self.width // 2 - modal_w // 2, self.height // 2 - 80, modal_w, modal_h)
            self._draw_card(modal_rect, border_color=COLOR_ACCENT_CYAN, bg_color=COLOR_CARD_BG)

            # Spinning Synthesis Arc
            ring_cx = modal_rect.left + 60
            ring_cy = modal_rect.top + 70
            ring_r = 28
            pygame.draw.circle(self.screen, (48, 48, 48), (ring_cx, ring_cy), ring_r, width=3)
            arc_angle = (elapsed_fraction * 360.0 * 4.0) % 360.0
            arc_rect = pygame.Rect(ring_cx - ring_r, ring_cy - ring_r, ring_r * 2, ring_r * 2)
            pygame.draw.arc(self.screen, COLOR_ACCENT_CYAN, arc_rect, math.radians(arc_angle), math.radians(arc_angle + 120), 4)

            self._draw_text("Synthesizing outcome projections...", self.font_title, COLOR_TEXT_PRIMARY, (ring_cx + 46, ring_cy - 16))
            self._draw_text("Trajectory pathway locked • 12-second algorithmic projection in progress", self.font_small, COLOR_ACCENT_CYAN, (ring_cx + 46, ring_cy + 18))

            # Complete outcome ambiguity callout
            susp_box = pygame.Rect(modal_rect.left + 30, modal_rect.bottom - 65, modal_w - 60, 36)
            pygame.draw.rect(self.screen, (32, 32, 32), susp_box, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_TIMER_AMBER, susp_box, width=1, border_radius=0)
            self._draw_text("[ COMPLETE OUTCOME AMBIGUITY MAINTAINED: ZERO FEEDBACK GRANTED ]", self.font_small, COLOR_TIMER_AMBER, susp_box.center, center=True)

            self._draw_text("Please remain still during trajectory synthesis.", self.font_small, (140, 140, 140), (self.width // 2, self.height - 35), center=True)
            return

        # Check if this is the notification_stack delay wait animation (Scenario B)
        elif "recalculating" in text.lower() or "parameters" in text.lower() or "assessment" in text.lower():
            # 1. Render Lockscreen background
            cx = self.width // 2
            self._draw_text("23:42", self.font_title, COLOR_TEXT_SECONDARY, (cx, 84), center=True)
            self._draw_text("Friday, September 19 • Midterm Assessment Period", self.font_small, COLOR_TEXT_MUTED, (cx, 114), center=True)

            # Dimmed notification card in background
            card_w = 840
            card_h = 140
            notif_rect = pygame.Rect(cx - card_w // 2, 140, card_w, card_h)
            self._draw_card(notif_rect, border_color=(48, 48, 48), bg_color=(18, 18, 18))
            self._draw_text("ACADEMIC EVALUATOR / SUPERVISOR", self.font_body, (160, 160, 160), (notif_rect.left + 24, notif_rect.top + 16))
            self._draw_text("Your methodology throughout this term has been... [? atypical ?] compared to your peers.", self.font_small, (129, 129, 129), (notif_rect.left + 24, notif_rect.top + 46))
            self._draw_text("[Draft Response Dispatched • Pending Committee Review]", self.font_mono_small, (113, 113, 113), (notif_rect.left + 24, notif_rect.bottom - 28))

            # Central Recalculation Modal
            modal_w = 740
            modal_h = 220
            modal_rect = pygame.Rect(cx - modal_w // 2, self.height // 2 - 50, modal_w, modal_h)
            self._draw_card(modal_rect, border_color=COLOR_ACCENT_CYAN, bg_color=COLOR_CARD_BG)

            # Progress Ring (10s progress ring)
            ring_cx = modal_rect.left + 60
            ring_cy = modal_rect.top + 70
            ring_r = 28
            pygame.draw.circle(self.screen, (48, 48, 48), (ring_cx, ring_cy), ring_r, width=3)
            ring_angle = (elapsed_fraction * 360.0 * 5.0) % 360.0
            arc_rect = pygame.Rect(ring_cx - ring_r, ring_cy - ring_r, ring_r * 2, ring_r * 2)
            pygame.draw.arc(self.screen, COLOR_ACCENT_CYAN, arc_rect, math.radians(ring_angle), math.radians(ring_angle + 140), 4)

            self._draw_text("Recalculating assessment parameters...", self.font_title, COLOR_TEXT_PRIMARY, (ring_cx + 46, ring_cy - 16))
            self._draw_text("Evaluation committee integrating response into cohort metric baseline", self.font_small, COLOR_ACCENT_CYAN, (ring_cx + 46, ring_cy + 18))

            # Outcome embargo callout (no feedback revealed)
            emb_box = pygame.Rect(modal_rect.left + 30, modal_rect.bottom - 65, modal_w - 60, 36)
            pygame.draw.rect(self.screen, (32, 32, 32), emb_box, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_TIMER_AMBER, emb_box, width=1, border_radius=0)
            self._draw_text("[ NO FEEDBACK REVEALED: ASSESSMENT PARAMETERS UNDER EMBARGO ]", self.font_small, COLOR_TIMER_AMBER, emb_box.center, center=True)

            self._draw_text("Please remain still during parameter recalculation.", self.font_small, (140, 140, 140), (self.width // 2, self.height - 35), center=True)
            return

        # Default fallback delay wait screen
        card_rect = pygame.Rect(self.width // 2 - 300, self.height // 2 - 120, 600, 240)
        self._draw_card(card_rect, COLOR_HAIRLINE_SUBTLE)

        # Spinning arc indicator
        angle = (elapsed_fraction * 720) % 360
        center = (self.width // 2, self.height // 2 - 30)
        arc_rect = pygame.Rect(center[0] - 30, center[1] - 30, 60, 60)
        pygame.draw.arc(self.screen, COLOR_ACCENT_CYAN, arc_rect, math.radians(angle), math.radians(angle + 120), 4)

        self._draw_text(text, self.font_title, COLOR_TEXT_PRIMARY, (self.width // 2, self.height // 2 + 35), center=True)
        self._draw_text("Please remain still during analysis.", self.font_small, COLOR_TEXT_SECONDARY, (self.width // 2, self.height // 2 + 75), center=True)
