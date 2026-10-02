"""Simulation skin `defense_stage` for scenario `social_evaluation_a`."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_BG,
    COLOR_HAIRLINE,
    COLOR_HAIRLINE_SUBTLE,
    COLOR_PRIMARY_ROSSO,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_GREEN,
    COLOR_TIMER_RED,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState


class DefenseStageSkin(UIComponents):
    """Renders the `defense_stage` decision skin."""

    def _draw_skin_defense_stage(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render defense_stage simulation skin for live project defense in front of an expert panel."""
        jx, jy = effects.jitter_offset
        frac = max(0.0, time_remaining_s / float(scenario.decision_duration_s))
        is_drone_active = frac <= scenario.drone_trigger_fraction

        # -----------------------------------------------------------------
        # 1. Question Projection (Wall Projection above Evaluators)
        # -----------------------------------------------------------------
        proj_rect = pygame.Rect(70 + jx, 95 + jy, self.width - 140, 68)
        pygame.draw.rect(self.screen, (32, 32, 32), proj_rect, border_radius=0)
        border_col = (93, 93, 93) if not is_drone_active else COLOR_PRIMARY_ROSSO
        pygame.draw.rect(self.screen, border_col, proj_rect, width=1, border_radius=0)

        # Subtle projector scanlines
        for ly in range(proj_rect.top + 12, proj_rect.bottom - 8, 14):
            pygame.draw.line(self.screen, (28, 28, 28), (proj_rect.left + 10, ly), (proj_rect.right - 10, ly), 1)

        # Header tag
        self._draw_text(
            "PROJECTED INQUIRY — REVIEW PANEL DEFENSE",
            self.font_small,
            COLOR_ACCENT_CYAN if not is_drone_active else COLOR_TIMER_AMBER,
            (proj_rect.left + 16, proj_rect.top + 8),
        )
        if is_drone_active:
            alert_str = "[ TENSION ESCALATION: FINAL ROUND INQUIRY ]"
            aw = self.font_small.size(alert_str)[0]
            self._draw_text(
                alert_str,
                self.font_small,
                COLOR_TIMER_RED,
                (proj_rect.right - 16 - aw, proj_rect.top + 8),
            )

        # Challenge question projected on the wall
        challenge_q = "Can you substantiate your methodology, or does your data collapse under rigorous examination?"
        self._draw_text(
            f'"{challenge_q}"',
            self.font_body,
            COLOR_TEXT_PRIMARY,
            (proj_rect.centerx, proj_rect.top + 38),
            center=True,
        )

        # -----------------------------------------------------------------
        # 2. Panel Bench & 3 Expert Evaluators (Grayscale TSST Silhouettes)
        # -----------------------------------------------------------------
        dais_rect = pygame.Rect(120 + jx, 172 + jy, self.width - 240, 108)
        pygame.draw.rect(self.screen, (28, 28, 28), dais_rect, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, dais_rect, width=1, border_radius=0)

        # 3 Evaluators seated behind the bench (completely still & unresponsive)
        eval_xs = [320 + jx, 640 + jx, 960 + jx]
        eval_roles = [
            ("EVALUATOR 1", "METHODOLOGY CHAIR"),
            ("PANEL LEAD", "STATISTICAL REVIEW"),
            ("EVALUATOR 3", "EXTERNAL ASSESSOR"),
        ]

        for k in range(3):
            ex = eval_xs[k]
            head_y = 198 + jy
            torso_bottom_y = 250 + jy

            # Grayscale suit torso silhouette
            torso_pts = [
                (ex - 42, torso_bottom_y),
                (ex + 42, torso_bottom_y),
                (ex + 28, head_y + 16),
                (ex - 28, head_y + 16),
            ]
            suit_col = (38, 38, 38) if k != 1 else (30, 30, 30)
            pygame.draw.polygon(self.screen, suit_col, torso_pts)

            # Collar and tie
            pygame.draw.polygon(self.screen, (165, 165, 165), [(ex - 9, head_y + 16), (ex + 9, head_y + 16), (ex, head_y + 30)])
            pygame.draw.line(self.screen, (48, 48, 48), (ex, head_y + 24), (ex, head_y + 42), 2)

            # Portrait silhouette head
            pygame.draw.circle(self.screen, (62, 62, 62), (ex, head_y), 18)
            pygame.draw.circle(self.screen, (48, 48, 48), (ex, head_y), 16)

            # Expressionless face: neutral horizontal line mouth (TSST uncontrollability mechanism)
            # Eyes: narrow horizontal neutral slits
            pygame.draw.line(self.screen, (80, 80, 80), (ex - 8, head_y - 2), (ex - 2, head_y - 2), 2)
            pygame.draw.line(self.screen, (80, 80, 80), (ex + 2, head_y - 2), (ex + 8, head_y - 2), 2)
            # Mouth: neutral horizontal line (completely still, unresponsive)
            pygame.draw.line(self.screen, (85, 85, 85), (ex - 7, head_y + 7), (ex + 7, head_y + 7), 2)

        # Imposing Evaluation Bench (Wood / Slate surface)
        bench_top_y = 244 + jy
        bench_rect = pygame.Rect(120 + jx, bench_top_y, self.width - 240, 36)
        pygame.draw.rect(self.screen, (32, 32, 32), bench_rect, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, bench_rect, width=1, border_radius=0)
        pygame.draw.line(self.screen, (87, 87, 87), (bench_rect.left, bench_top_y + 1), (bench_rect.right, bench_top_y + 1), 2)

        # Nameplates & dossiers on bench
        for k in range(3):
            ex = eval_xs[k]
            pygame.draw.rect(self.screen, (165, 165, 165), (ex - 70, bench_top_y + 6, 20, 16), border_radius=0)
            plate_rect = pygame.Rect(ex - 42, bench_top_y + 7, 130, 20)
            pygame.draw.rect(self.screen, (24, 24, 24), plate_rect, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE, plate_rect, width=1, border_radius=0)
            title = eval_roles[k][0]
            self._draw_text(title, self.font_small, (187, 187, 187), (plate_rect.centerx, plate_rect.centery), center=True)

        # TSST unresponsiveness label
        self._draw_text(
            "PANEL IN SESSION • AWAITING YOUR RESPONSE",
            self.font_small,
            (110, 110, 110),
            (self.width // 2 + jx, bench_top_y + 44),
            center=True,
        )

        # -----------------------------------------------------------------
        # 3. Podium Defense Terminal (Speaker's Perspective) & Options
        # -----------------------------------------------------------------
        podium_y = 302 + jy
        podium_banner = pygame.Rect(70 + jx, podium_y, self.width - 140, 32)
        pygame.draw.rect(self.screen, (32, 32, 32), podium_banner, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, podium_banner, width=1, border_radius=0)

        # Microphone live cue
        pygame.draw.circle(self.screen, COLOR_TIMER_GREEN, (podium_banner.left + 14, podium_banner.centery), 4)
        self._draw_text("PODIUM MIC: LIVE", self.font_small, COLOR_TIMER_GREEN, (podium_banner.left + 24, podium_banner.centery), midleft=True)
        self._draw_text("DEFENSE TERMINAL CONSOLE — SELECT STRATEGY", self.font_small, COLOR_ACCENT_CYAN, (podium_banner.centerx, podium_banner.centery), center=True)
        if is_drone_active:
            dt_str = "[ TIME CRITICAL ]"
            self._draw_text(dt_str, self.font_small, COLOR_TIMER_AMBER, (podium_banner.right - 14, podium_banner.centery), midright=True)

        # 3 Options displayed on podium console screen
        opts = scenario.options
        card_h = 68
        gap = 10
        start_y = podium_y + 38
        stance_tags = [
            "[ TECHNICAL JUSTIFICATION ]",
            "[ LIMITATION CONCESSION ]",
            "[ AUTHORITY CHALLENGE ]",
        ]

        for i, opt in enumerate(opts):
            cy = start_y + i * (card_h + gap)
            rect = pygame.Rect(70 + jx, cy, self.width - 140, card_h)
            is_sel = (selected_index == i)

            # The participant's own choice is marked in white; Rosso stays reserved for stress triggers
            if is_sel:
                bg_col = (37, 37, 37)
                sel_border = COLOR_TEXT_PRIMARY
            else:
                bg_col = (28, 28, 28)
                sel_border = COLOR_HAIRLINE if selected_index is not None else COLOR_HAIRLINE_SUBTLE

            pygame.draw.rect(self.screen, bg_col, rect, border_radius=0)
            pygame.draw.rect(self.screen, sel_border, rect, width=1, border_radius=0)

            # Key badge [1], [2], [3]
            key_rect = pygame.Rect(rect.left + 14, rect.centery - 18, 36, 36)
            self._draw_key_badge(key_rect, str(opt.key), selected=is_sel)

            # Tactical stance tag & option text
            tag_str = stance_tags[i] if i < len(stance_tags) else ""
            self._draw_text(tag_str, self.font_small, COLOR_TEXT_PRIMARY if is_sel else COLOR_TEXT_SECONDARY, (key_rect.right + 14, rect.top + 9))
            opt_rect = pygame.Rect(key_rect.right + 14, rect.top + 31, rect.width - 210, 30)
            self._draw_wrapped_text(opt.text, self.font_body, COLOR_TEXT_PRIMARY, opt_rect, center_v=True)

            # Selected indicator tag (inverted: white plate, canvas ink)
            if is_sel:
                sel_badge = pygame.Rect(rect.right - 120, rect.centery - 13, 104, 26)
                pygame.draw.rect(self.screen, COLOR_TEXT_PRIMARY, sel_badge, border_radius=0)
                self._draw_text("SELECTED", self.font_small, COLOR_BG, sel_badge.center, center=True)

        # -----------------------------------------------------------------
        # 4. Active Deception Composure Bar (Bottom Biofeedback Bar)
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
            "PRESS KEY [1], [2], OR [3] TO DELIVER ORAL DEFENSE TO THE PANEL",
            self.font_small,
            (128, 128, 128),
            (self.width // 2, self.height - 18),
            center=True,
        )

        return True
