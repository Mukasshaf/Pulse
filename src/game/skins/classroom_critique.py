"""Simulation skin `classroom_critique` for scenario `social_evaluation_b`."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_BG,
    COLOR_HAIRLINE,
    COLOR_HAIRLINE_SUBTLE,
    COLOR_PRIMARY_ACTIVE,
    COLOR_PRIMARY_ROSSO,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_RED,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState


class ClassroomCritiqueSkin(UIComponents):
    """Renders the `classroom_critique` decision skin."""

    def _draw_skin_classroom_critique(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render classroom_critique simulation skin for public critique before a full cohort."""
        jx, jy = effects.jitter_offset
        frac = max(0.0, time_remaining_s / float(scenario.decision_duration_s))
        is_drone_active = frac <= scenario.drone_trigger_fraction

        # -----------------------------------------------------------------
        # 1. Authority Figure Silhouette (Instructor Standing on Left)
        # -----------------------------------------------------------------
        inst_x = 90 + jx
        inst_base_y = 285 + jy

        # Floor line / boundary
        pygame.draw.line(self.screen, (48, 48, 48), (inst_x - 45, inst_base_y), (inst_x + 65, inst_base_y), 2)

        # Instructor Suit / Jacket Silhouette
        torso_pts = [
            (inst_x - 26, inst_base_y),
            (inst_x + 26, inst_base_y),
            (inst_x + 20, inst_base_y - 110),
            (inst_x - 20, inst_base_y - 110),
        ]
        pygame.draw.polygon(self.screen, (48, 48, 48), torso_pts)
        # Collar and tie
        pygame.draw.polygon(self.screen, (155, 155, 155), [(inst_x - 7, inst_base_y - 110), (inst_x + 7, inst_base_y - 110), (inst_x, inst_base_y - 96)])
        pygame.draw.line(self.screen, (35, 35, 35), (inst_x, inst_base_y - 96), (inst_x, inst_base_y - 80), 2)

        # Head silhouette
        head_cy = inst_base_y - 132
        pygame.draw.circle(self.screen, (64, 64, 64), (inst_x, head_cy), 17)
        pygame.draw.circle(self.screen, (48, 48, 48), (inst_x, head_cy), 15)

        # Authoritative Gesturing Arm: extended toward the right / participant
        arm_start = (inst_x + 18, inst_base_y - 100)
        arm_elbow = (inst_x + 55, inst_base_y - 88)
        arm_hand = (inst_x + 102, inst_base_y - 96)
        pygame.draw.line(self.screen, (48, 48, 48), arm_start, arm_elbow, 6)
        pygame.draw.line(self.screen, (48, 48, 48), arm_elbow, arm_hand, 5)
        # Pointing hand
        pygame.draw.circle(self.screen, (68, 68, 68), arm_hand, 5)
        pygame.draw.line(self.screen, (68, 68, 68), arm_hand, (arm_hand[0] + 12, arm_hand[1] - 3), 2)

        # Authority tag
        self._draw_text(
            "COURSE INSTRUCTOR",
            self.font_small,
            (175, 175, 175),
            (inst_x, inst_base_y + 12),
            center=True,
        )

        # -----------------------------------------------------------------
        # 2. Harsh Critique Speech Bubble (Originating from Instructor)
        # -----------------------------------------------------------------
        bubble_rect = pygame.Rect(210 + jx, 95 + jy, self.width - 280, 78)
        # Pointer triangle connecting hand to bubble
        pointer_pts = [
            (bubble_rect.left, bubble_rect.top + 26),
            (bubble_rect.left, bubble_rect.top + 48),
            (arm_hand[0] + 12, arm_hand[1] - 3),
        ]
        bubble_bg = COLOR_BG
        bubble_border = COLOR_PRIMARY_ROSSO if is_drone_active else COLOR_PRIMARY_ACTIVE
        pygame.draw.polygon(self.screen, bubble_bg, pointer_pts)
        pygame.draw.polygon(self.screen, bubble_border, pointer_pts, width=1)
        pygame.draw.rect(self.screen, bubble_bg, bubble_rect, border_radius=0)
        pygame.draw.rect(self.screen, bubble_border, bubble_rect, width=1, border_radius=0)

        # Speech bubble content
        self._draw_text(
            "[ PUBLIC COHORT CRITIQUE — DIRECT INQUIRY ]",
            self.font_small,
            COLOR_TIMER_AMBER if not is_drone_active else COLOR_TIMER_RED,
            (bubble_rect.left + 14, bubble_rect.top + 8),
        )
        if is_drone_active:
            alert_str = "[ TIMEOUT ESCALATION ]"
            aw = self.font_small.size(alert_str)[0]
            self._draw_text(
                alert_str,
                self.font_small,
                COLOR_TIMER_RED,
                (bubble_rect.right - 14 - aw, bubble_rect.top + 8),
            )

        harsh_critique = "Your approach lacks standard rigor. Explain why the cohort should consider this acceptable."
        self._draw_text(
            f'"{harsh_critique}"',
            self.font_body,
            COLOR_TEXT_PRIMARY,
            (bubble_rect.centerx, bubble_rect.top + 38),
            center=True,
        )

        # -----------------------------------------------------------------
        # 3. Audience Rows (Seated Silhouette Heads Facing Participant)
        # -----------------------------------------------------------------
        row2_y = 208 + jy
        row2_bench = pygame.Rect(210 + jx, row2_y + 12, self.width - 280, 6)
        pygame.draw.rect(self.screen, (32, 32, 32), row2_bench, border_radius=0)
        row2_xs = [245 + k * 86 + jx for k in range(11)]
        for sx in row2_xs:
            pygame.draw.polygon(
                self.screen,
                (36, 36, 36),
                [(sx - 18, row2_y + 14), (sx + 18, row2_y + 14), (sx + 12, row2_y - 4), (sx - 12, row2_y - 4)],
            )
            pygame.draw.circle(self.screen, (48, 48, 48), (sx, row2_y - 12), 11)
            pygame.draw.circle(self.screen, (78, 78, 78), (sx - 4, row2_y - 13), 2)
            pygame.draw.circle(self.screen, (78, 78, 78), (sx + 4, row2_y - 13), 2)

        # Row 1 (Front row, closer, larger)
        row1_y = 254 + jy
        row1_bench = pygame.Rect(190 + jx, row1_y + 14, self.width - 260, 8)
        pygame.draw.rect(self.screen, (36, 36, 36), row1_bench, border_radius=0)
        pygame.draw.line(self.screen, (68, 68, 68), (row1_bench.left, row1_y + 14), (row1_bench.right, row1_y + 14), 1)

        row1_xs = [230 + k * 110 + jx for k in range(9)]
        for sx in row1_xs:
            pygame.draw.polygon(
                self.screen,
                (48, 48, 48),
                [(sx - 24, row1_y + 16), (sx + 24, row1_y + 16), (sx + 16, row1_y - 6), (sx - 16, row1_y - 6)],
            )
            pygame.draw.circle(self.screen, (62, 62, 62), (sx, row1_y - 16), 14)
            pygame.draw.circle(self.screen, (102, 102, 102), (sx - 5, row1_y - 17), 2)
            pygame.draw.circle(self.screen, (102, 102, 102), (sx + 5, row1_y - 17), 2)
            pygame.draw.rect(self.screen, (72, 72, 72), (sx - 12, row1_y + 8, 24, 6), border_radius=0)

        self._draw_text(
            "COHORT AUDIENCE: 20 PEERS OBSERVING IN SILENCE • EVALUATING YOUR DEFENSE",
            self.font_small,
            (122, 122, 122),
            (self.width // 2 + jx, 288 + jy),
            center=True,
        )

        # -----------------------------------------------------------------
        # 4. False Dichotomy Cards (Podium Defense Options)
        # -----------------------------------------------------------------
        opts = scenario.options
        card_h = 68
        gap = 10
        start_y = 312 + jy
        posture_tags = [
            "[ COMPLIANCE / COMMITMENT TO IMPROVE ]",
            "[ ATTRIBUTION / EXTERNAL CIRCUMSTANCES ]",
            "[ CHALLENGE / DISPUTING VAGUENESS ]",
        ]

        for i, opt in enumerate(opts):
            cy = start_y + i * (card_h + gap)
            rect = pygame.Rect(70 + jx, cy, self.width - 140, card_h)
            is_sel = (selected_index == i)

            # The participant's own choice is marked in white; Rosso stays reserved for stress triggers
            if is_sel:
                bg_col = (37, 37, 37)
                border_col = COLOR_TEXT_PRIMARY
            else:
                bg_col = (28, 28, 28)
                border_col = COLOR_HAIRLINE if selected_index is not None else COLOR_HAIRLINE_SUBTLE

            pygame.draw.rect(self.screen, bg_col, rect, border_radius=0)
            pygame.draw.rect(self.screen, border_col, rect, width=1, border_radius=0)

            # Key badge [1], [2], [3]
            key_rect = pygame.Rect(rect.left + 14, rect.centery - 18, 36, 36)
            self._draw_key_badge(key_rect, str(opt.key), selected=is_sel)

            # Posture tag & option text
            tag_str = posture_tags[i] if i < len(posture_tags) else ""
            self._draw_text(tag_str, self.font_small, COLOR_TEXT_PRIMARY if is_sel else COLOR_TEXT_SECONDARY, (key_rect.right + 14, rect.top + 9))
            opt_rect = pygame.Rect(key_rect.right + 14, rect.top + 31, rect.width - 210, 30)
            self._draw_wrapped_text(opt.text, self.font_body, COLOR_TEXT_PRIMARY, opt_rect, center_v=True)

            # Selected indicator tag (inverted: white plate, canvas ink)
            if is_sel:
                sel_badge = pygame.Rect(rect.right - 120, rect.centery - 13, 104, 26)
                pygame.draw.rect(self.screen, COLOR_TEXT_PRIMARY, sel_badge, border_radius=0)
                self._draw_text("SELECTED", self.font_small, COLOR_BG, sel_badge.center, center=True)

        # -----------------------------------------------------------------
        # 5. Active Deception Composure Bar (Bottom Biofeedback Bar)
        # -----------------------------------------------------------------
        if scenario.has_deception_metric:
            comp_bar_y = start_y + len(opts) * (card_h + gap) + 16
            self.draw_composure_bar(
                composure_fraction,
                (70 + jx, comp_bar_y),
                width=self.width - 140,
                is_drone_active=is_drone_active,
            )

        # Bottom prompt
        self._draw_text(
            "PRESS KEY [1], [2], OR [3] TO DELIVER RESPONSE TO INSTRUCTOR AND COHORT",
            self.font_small,
            (128, 128, 128),
            (self.width // 2, self.height - 18),
            center=True,
        )

        return True
