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
    PENDULUM_SWING_MAX_HZ,
    TIMER_BAR_RED_FRACTION,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import MathProblem, Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState

WALL_TOP = 90
WALL_BOTTOM = 220
PEER_DESKS: tuple[tuple[int, float], ...] = ((210, 0.13), (520, 0.15), (830, 0.17))  # (x, lead over the participant)
INK = (31, 31, 31)


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
        self._draw_exam_wall(scenario, time_remaining_s, effects, mist_runner)
        self._draw_exam_paper(scenario, problem, mist_runner, effects, selected_index)
        return True

    def _draw_exam_wall(self, scenario: Scenario, time_remaining_s: float, effects: UIEffectState, runner: MISTRunner) -> None:
        """Draw the back of the hall: the pacing invigilator, three peer desks that stay ahead, and the wall clock."""
        pygame.draw.rect(self.screen, (28, 28, 28), (0, WALL_TOP, self.width, WALL_BOTTOM - WALL_TOP))
        for pillar_x in (365, 675, 985):
            pygame.draw.line(self.screen, (36, 36, 36), (pillar_x, WALL_TOP), (pillar_x, WALL_BOTTOM), 1)

        # The invigilator walks the back row for the final 20 s, behind the desks (about 0.12 Hz)
        if time_remaining_s <= 20.0:
            invig_x = int(520 + math.sin((20.0 - time_remaining_s) * 0.75) * 380)
            self._draw_silhouette(invig_x, WALL_BOTTOM, 104, shade=70, collar=True)
            pygame.draw.rect(self.screen, (200, 200, 200), (invig_x + 24, WALL_BOTTOM - 48, 14, 20), border_radius=0)

        # Peer desks: each completion bar stays a fixed step ahead of the participant
        user_frac = runner.get_progress_fraction()
        for k, (desk_x, lead) in enumerate(PEER_DESKS):
            desk_y = WALL_BOTTOM - 16
            self._draw_silhouette(desk_x, desk_y, 62, shade=46)
            pygame.draw.rect(self.screen, (52, 52, 52), (desk_x - 58, desk_y, 116, 16), border_radius=0)
            pygame.draw.rect(self.screen, (215, 215, 215), (desk_x - 14, desk_y + 3, 28, 10), border_radius=0)
            peer_val = min(1.0, max(0.12, user_frac + lead))
            bar = pygame.Rect(desk_x - 58, WALL_TOP + 30, 116, 7)
            self._draw_progress_line(bar, peer_val, COLOR_TIMER_AMBER if peer_val < 0.85 else COLOR_TIMER_RED)
            self._draw_text(f"Desk {k + 1}  •  {int(peer_val * 100)}%", self.font_small, (160, 160, 160), (desk_x, WALL_TOP + 16), center=True)

        self._draw_exam_clock(scenario, time_remaining_s, effects)
        pygame.draw.line(self.screen, (52, 52, 52), (0, WALL_BOTTOM), (self.width, WALL_BOTTOM), 2)

    def _draw_exam_clock(self, scenario: Scenario, time_remaining_s: float, effects: UIEffectState) -> None:
        """Draw the wall clock, its pendulum, and the digital readout beside it."""
        duration = max(1.0, float(scenario.decision_duration_s))
        frac = max(0.0, min(1.0, time_remaining_s / duration))
        cx, cy, radius = self.width - 100, WALL_TOP + 52, 32

        # Pendulum: 0.5 Hz, rising to the capped rate in the final third; phase is continuous across the change
        elapsed = duration - max(0.0, time_remaining_s)
        steady_s = duration * (2.0 / 3.0)
        cycles = 0.5 * min(elapsed, steady_s) + PENDULUM_SWING_MAX_HZ * max(0.0, elapsed - steady_s)
        swing = math.sin(2.0 * math.pi * cycles) * 0.32
        bob = (cx + int(math.sin(swing) * 34), cy + radius + int(math.cos(swing) * 34))
        pygame.draw.line(self.screen, (120, 120, 120), (cx, cy + radius), bob, 2)
        pygame.draw.circle(self.screen, (170, 170, 170), bob, 5)

        pygame.draw.circle(self.screen, (80, 80, 80), (cx, cy), radius, width=3)
        pygame.draw.circle(self.screen, (235, 235, 235), (cx, cy), radius - 3)
        for hour in range(12):
            ang = hour * (math.pi / 6.0)
            pygame.draw.circle(self.screen, (95, 95, 95), (cx + int(math.cos(ang) * (radius - 7)), cy + int(math.sin(ang) * (radius - 7))), 1)
        hand_ang = -math.pi / 2.0 + (1.0 - frac) * 2.0 * math.pi
        hand_col = COLOR_TIMER_RED if frac <= TIMER_BAR_RED_FRACTION else INK
        pygame.draw.line(self.screen, hand_col, (cx, cy), (cx + int(math.cos(hand_ang) * (radius - 10)), cy + int(math.sin(hand_ang) * (radius - 10))), 3)
        pygame.draw.circle(self.screen, INK, (cx, cy), 3)
        self._draw_text(f"{time_remaining_s:.1f}s", self.font_title, effects.timer_bar_color, (cx - radius - 18, cy), midright=True)

    def _draw_exam_paper(
        self, scenario: Scenario, problem: MathProblem, runner: MISTRunner, effects: UIEffectState, selected_index: int | None,
    ) -> None:
        """Draw the participant's desk and exam script: header, the current item with its countdown, and four answers."""
        jx, jy = effects.jitter_offset
        pygame.draw.rect(self.screen, (31, 31, 31), (0, WALL_BOTTOM, self.width, self.height - WALL_BOTTOM))

        paper = pygame.Rect((self.width - 840) // 2 + jx, WALL_BOTTOM + 14 + jy, 840, 456)
        pygame.draw.rect(self.screen, (18, 18, 18), paper.move(6, 6), border_radius=0)
        pygame.draw.rect(self.screen, (240, 240, 240), paper, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, paper, width=1, border_radius=0)
        margin_x = paper.left + 55
        pygame.draw.line(self.screen, (190, 190, 190), (margin_x, paper.top + 10), (margin_x, paper.bottom - 10), 1)

        self._draw_text("OFFICIAL EXAMINATION SCRIPT — ARITHMETIC SPEED & ACCURACY", self.font_small, (95, 95, 95), (margin_x + 16, paper.top + 16))
        self._draw_text(f"CANDIDATE: [CONFIDENTIAL]    |    SECTION 1 / 1    |    TIME LIMIT: {scenario.decision_duration_s}s", self.font_small, (125, 125, 125), (margin_x + 16, paper.top + 36))
        pygame.draw.line(self.screen, (195, 195, 195), (margin_x + 14, paper.top + 58), (paper.right - 30, paper.top + 58), 1)

        q_rect = pygame.Rect(margin_x + 15, paper.top + 70, paper.width - 110, 104)
        pygame.draw.rect(self.screen, (248, 248, 248), q_rect, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, q_rect, width=1, border_radius=0)
        self._draw_text("EVALUATE RAPIDLY:", self.font_small, (90, 90, 90), (q_rect.left + 15, q_rect.top + 10))
        self._draw_text(problem.question_text, self.font_hero, INK, (q_rect.centerx, q_rect.centery + 8), center=True)

        # Per-item countdown: the adaptive limit drains along the question box, Rosso only near expiry
        item_frac = runner.get_item_time_fraction()
        item_col = COLOR_PRIMARY_ROSSO if item_frac <= MIST_ITEM_BAR_RED_FRACTION else COLOR_BG
        item_track = pygame.Rect(q_rect.left + 1, q_rect.bottom - 7, q_rect.width - 2, 6)
        pygame.draw.rect(self.screen, (210, 210, 210), item_track, border_radius=0)
        pygame.draw.rect(self.screen, item_col, (item_track.left, item_track.top, int(item_track.width * item_frac), item_track.height), border_radius=0)

        if effects.is_flashing:
            self._draw_exam_wrong_mark(paper, q_rect)
        self._draw_exam_answers(problem, q_rect, selected_index)
        self._draw_text("PRESS 1, 2, 3 OR 4 TO ANSWER", self.font_small, (125, 125, 125), (paper.centerx, paper.bottom - 24), center=True)

    def _draw_exam_wrong_mark(self, paper: pygame.Rect, q_rect: pygame.Rect) -> None:
        """Mark a wrong or timed-out item in the margin and stamp it, without covering the item now on the page."""
        cx, cy, arm = paper.left + 28, q_rect.centery, 15
        pygame.draw.line(self.screen, COLOR_PRIMARY_ROSSO, (cx - arm, cy - arm), (cx + arm, cy + arm), 5)
        pygame.draw.line(self.screen, COLOR_PRIMARY_ROSSO, (cx - arm, cy + arm), (cx + arm, cy - arm), 5)
        self._draw_tag("INCORRECT", (q_rect.right - 12, q_rect.top + 20), anchor="midright", ink=COLOR_PRIMARY_ROSSO, border=COLOR_PRIMARY_ROSSO, font=self.font_small)

    def _draw_exam_answers(self, problem: MathProblem, q_rect: pygame.Rect, selected_index: int | None) -> None:
        """Draw the four answer boxes in a two-by-two grid with paper-white key squares."""
        box_w = (q_rect.width - 20) // 2
        box_h = 84
        for i, answer in enumerate(problem.options):
            box = pygame.Rect(q_rect.left + (i % 2) * (box_w + 20), q_rect.bottom + 18 + (i // 2) * (box_h + 16), box_w, box_h)
            is_sel = selected_index == i
            pygame.draw.rect(self.screen, (228, 228, 228) if is_sel else (246, 246, 246), box, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_BG if is_sel else (189, 189, 189), box, width=2 if is_sel else 1, border_radius=0)

            # Key square: paper-white with dark ink, inverted once chosen
            key_rect = pygame.Rect(box.left + 18, box.centery - 20, 40, 40)
            key_bg, key_ink = (COLOR_BG, COLOR_TEXT_PRIMARY) if is_sel else (COLOR_TEXT_PRIMARY, COLOR_BG)
            pygame.draw.rect(self.screen, key_bg, key_rect, border_radius=0)
            pygame.draw.rect(self.screen, (110, 110, 110), key_rect, width=1, border_radius=0)
            self._draw_text(str(i + 1), self.font_title, key_ink, key_rect.center, center=True)
            self._draw_text(str(answer), self.font_hero, INK, (key_rect.right + 28, box.centery), midleft=True)
