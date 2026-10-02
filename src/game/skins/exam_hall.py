"""Simulation skin `exam_hall` for scenario `academic_pressure_a`."""
from __future__ import annotations

import math

import pygame

from src.game.constants import (
    COLOR_BG,
    COLOR_HAIRLINE,
    COLOR_PRIMARY_ROSSO,
    COLOR_TEXT_PRIMARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_RED,
    MIST_ITEM_BAR_RED_FRACTION,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState


class ExamHallSkin(UIComponents):
    """Renders the `exam_hall` decision skin."""

    def _draw_skin_exam_hall(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render exam_hall simulation skin: student desk perspective, paper, peer desks, pacing invigilator."""
        if mist_runner is None:
            return False
        problem = mist_runner.get_current_problem()
        if problem is None:
            return False

        jx, jy = effects.jitter_offset

        # Upper hall perspective wall (y = 90 to 215)
        hall_wall_rect = pygame.Rect(0, 90, self.width, 125)
        pygame.draw.rect(self.screen, (24, 24, 24), hall_wall_rect)
        pygame.draw.line(self.screen, (44, 44, 44), (0, 215), (self.width, 215), 2)
        # Subtle architectural vertical pillars
        for px in (320, 640, 960):
            pygame.draw.line(self.screen, (33, 33, 33), (px, 90), (px, 215), 1)

        # Analog Wall Clock at top-right (counts down with timer)
        clock_cx = self.width - 55
        clock_cy = 42
        clock_radius = 22
        pygame.draw.circle(self.screen, (80, 80, 80), (clock_cx, clock_cy), clock_radius, width=3)
        pygame.draw.circle(self.screen, (235, 235, 235), (clock_cx, clock_cy), clock_radius - 3)
        for hour_idx in range(12):
            ang = hour_idx * (math.pi / 6.0)
            mx = clock_cx + int(math.cos(ang) * (clock_radius - 5))
            my = clock_cy + int(math.sin(ang) * (clock_radius - 5))
            pygame.draw.circle(self.screen, (95, 95, 95), (mx, my), 1)

        duration = max(1.0, float(scenario.decision_duration_s))
        time_frac = max(0.0, min(1.0, time_remaining_s / duration))
        hand_ang = -math.pi / 2.0 + (1.0 - time_frac) * 2.0 * math.pi
        hx = clock_cx + int(math.cos(hand_ang) * 14)
        hy = clock_cy + int(math.sin(hand_ang) * 14)
        pygame.draw.line(self.screen, COLOR_TIMER_RED, (clock_cx, clock_cy), (hx, hy), 2)
        pygame.draw.circle(self.screen, (41, 41, 41), (clock_cx, clock_cy), 3)
        # Digital readout to the left of analog clock
        self._draw_text(f"{time_remaining_s:.1f}s", self.font_title, effects.timer_bar_color, (clock_cx - 56, clock_cy), center=True)

        # Pacing Supervisor (Invigilator) Silhouette along back wall if time_remaining_s <= 20.0
        if time_remaining_s <= 20.0:
            pace_time = 20.0 - time_remaining_s
            invig_x = int(640 + math.sin(pace_time * 0.75) * 260)
            invig_y = 112
            torso_pts = [
                (invig_x - 14, invig_y + 46),
                (invig_x + 14, invig_y + 46),
                (invig_x + 10, invig_y + 15),
                (invig_x - 10, invig_y + 15),
            ]
            pygame.draw.polygon(self.screen, (20, 20, 20), torso_pts)
            pygame.draw.circle(self.screen, (24, 24, 24), (invig_x, invig_y + 6), 11)
            # Clipboard in hand
            pygame.draw.rect(self.screen, (145, 145, 145), (invig_x + 10, invig_y + 20, 10, 14), border_radius=0)
            pygame.draw.line(self.screen, (41, 41, 41), (invig_x + 13, invig_y + 23), (invig_x + 17, invig_y + 23), 1)
            self._draw_text("INVIGILATOR PATROL", self.font_small, COLOR_PRIMARY_ROSSO, (invig_x, invig_y - 12), center=True)

        # Classmate Peer Desks along upper periphery (MIST social-evaluative comparison ~15% ahead)
        user_frac = mist_runner.get_progress_fraction()
        desk_xs = [240, 640, 1040]
        lead_offsets = [0.13, 0.15, 0.17]
        for k in range(3):
            dx = desk_xs[k]
            dy = 168
            # Miniature student silhouette
            pygame.draw.circle(self.screen, (40, 40, 40), (dx, dy - 16), 9)
            torso_pts = [(dx - 15, dy), (dx + 15, dy), (dx + 9, dy - 11), (dx - 9, dy - 11)]
            pygame.draw.polygon(self.screen, (32, 32, 32), torso_pts)
            # Miniature desk & exam paper
            pygame.draw.rect(self.screen, (36, 36, 36), (dx - 40, dy, 80, 16), border_radius=0)
            pygame.draw.rect(self.screen, (215, 215, 215), (dx - 12, dy + 2, 24, 11))
            # Peer progress bar (dynamically stays ~15% ahead)
            peer_val = min(1.0, max(0.12, user_frac + lead_offsets[k]))
            bar_w = 84
            bar_h = 7
            bar_rect = pygame.Rect(dx - 42, dy - 34, bar_w, bar_h)
            pygame.draw.rect(self.screen, (28, 28, 28), bar_rect, border_radius=0)
            fill_col = COLOR_TIMER_AMBER if peer_val < 0.85 else COLOR_TIMER_RED
            pygame.draw.rect(self.screen, fill_col, (bar_rect.left, bar_rect.top, int(bar_w * peer_val), bar_h), border_radius=0)
            self._draw_text(f"Desk {k + 1}: {int(peer_val * 100)}%", self.font_small, (155, 155, 155), (dx, dy - 48), center=True)

        # Foreground Desk: Wood surface
        desk_y = 215
        pygame.draw.rect(self.screen, (31, 31, 31), (0, desk_y, self.width, self.height - desk_y))
        pygame.draw.rect(self.screen, (43, 43, 43), (0, desk_y, self.width, 8))
        pygame.draw.line(self.screen, (19, 19, 19), (0, desk_y + 8), (self.width, desk_y + 8), 2)

        # Exam Paper Surface: Cream / off-white tint (235, 235, 230)
        paper_w = 840
        paper_h = 475
        paper_x = (self.width - paper_w) // 2 + jx
        paper_y = desk_y + 14 + jy
        paper_rect = pygame.Rect(paper_x, paper_y, paper_w, paper_h)
        # Paper drop shadow
        pygame.draw.rect(self.screen, (18, 18, 18), (paper_x + 6, paper_y + 6, paper_w, paper_h), border_radius=0)
        # Paper fill and outline
        pygame.draw.rect(self.screen, (240, 240, 240), paper_rect, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, paper_rect, width=1, border_radius=0)
        # Margin line
        margin_x = paper_x + 55
        pygame.draw.line(self.screen, (190, 190, 190), (margin_x, paper_y + 10), (margin_x, paper_y + paper_h - 10), 1)

        # Printed paper header
        self._draw_text("OFFICIAL EXAMINATION SCRIPT — ARITHMETIC SPEED & ACCURACY", self.font_small, (95, 95, 95), (margin_x + 16, paper_y + 16))
        self._draw_text(f"CANDIDATE: [CONFIDENTIAL]    |    SECTION 1 / 1    |    TIME LIMIT: {scenario.decision_duration_s}s", self.font_small, (125, 125, 125), (margin_x + 16, paper_y + 36))
        pygame.draw.line(self.screen, (195, 195, 195), (margin_x + 14, paper_y + 56), (paper_x + paper_w - 30, paper_y + 56), 1)

        # MIST Arithmetic Question Overlay
        q_rect = pygame.Rect(margin_x + 15, paper_y + 68, paper_w - 110, 85)
        pygame.draw.rect(self.screen, (248, 248, 248), q_rect, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, q_rect, width=1, border_radius=0)
        self._draw_text("EVALUATE RAPIDLY:", self.font_small, (90, 90, 90), (q_rect.left + 15, q_rect.top + 8))
        self._draw_text(problem.question_text, self.font_hero, (31, 31, 31), (q_rect.centerx, q_rect.centery + 6), center=True)

        # Per-item countdown: the adaptive MIST limit drains along the question box, Rosso only near expiry
        item_frac = mist_runner.get_item_time_fraction()
        item_col = COLOR_PRIMARY_ROSSO if item_frac <= MIST_ITEM_BAR_RED_FRACTION else COLOR_BG
        item_track = pygame.Rect(q_rect.left + 1, q_rect.bottom - 7, q_rect.width - 2, 6)
        pygame.draw.rect(self.screen, (210, 210, 210), item_track, border_radius=0)
        pygame.draw.rect(self.screen, item_col, (item_track.left, item_track.top, int(item_track.width * item_frac), item_track.height), border_radius=0)

        # Wrong Answer Feedback: Prominent red ink cross X for 200ms
        if effects.is_flashing:
            pygame.draw.line(self.screen, COLOR_PRIMARY_ROSSO, (q_rect.left + 25, q_rect.top + 10), (q_rect.right - 25, q_rect.bottom - 10), 6)
            pygame.draw.line(self.screen, COLOR_PRIMARY_ROSSO, (q_rect.left + 25, q_rect.bottom - 10), (q_rect.right - 25, q_rect.top + 10), 6)
            self._draw_text("INCORRECT", self.font_title, COLOR_PRIMARY_ROSSO, (q_rect.centerx, q_rect.centery + 6), center=True)

        # 4 Answer Checkboxes: [1], [2], [3], [4]
        box_w = (q_rect.width - 20) // 2
        box_h = 70
        for i, ans in enumerate(problem.options):
            col = i % 2
            row = i // 2
            bx = q_rect.left + col * (box_w + 20)
            by = paper_y + 172 + row * (box_h + 15)
            btn_rect = pygame.Rect(bx, by, box_w, box_h)

            is_sel = (selected_index == i)
            bg = (228, 228, 228) if is_sel else (246, 246, 246)
            border_col = COLOR_BG if is_sel else (189, 189, 189)
            border_w = 2 if is_sel else 1
            pygame.draw.rect(self.screen, bg, btn_rect, border_radius=0)
            pygame.draw.rect(self.screen, border_col, btn_rect, width=border_w, border_radius=0)

            # Checkbox square [1], [2], etc.: paper-white with dark ink, inverted once chosen
            chk_rect = pygame.Rect(btn_rect.left + 15, btn_rect.centery - 18, 36, 36)
            chk_bg, chk_ink = (COLOR_BG, COLOR_TEXT_PRIMARY) if is_sel else (COLOR_TEXT_PRIMARY, COLOR_BG)
            pygame.draw.rect(self.screen, chk_bg, chk_rect, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE, chk_rect, width=1, border_radius=0)
            self._draw_text(f"[{i + 1}]", self.font_title, chk_ink, chk_rect.center, center=True)

            # Answer value in dark charcoal font (30, 30, 40)
            self._draw_text(str(ans), self.font_hero, (31, 31, 31), (chk_rect.right + 70, btn_rect.centery), center=True)

        self._draw_text("RECORD YOUR CHOICE: PRESS KEY [1], [2], [3], OR [4]", self.font_small, (125, 125, 125), (paper_x + paper_w // 2, paper_y + paper_h - 22), center=True)
        return True
