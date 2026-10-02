"""Simulation skin `misconduct_hearing` for scenario `academic_pressure_b`."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_HAIRLINE,
    COLOR_HAIRLINE_SUBTLE,
    COLOR_PRIMARY_ACTIVE,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_RED,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState


class MisconductHearingSkin(UIComponents):
    """Renders the `misconduct_hearing` decision skin."""

    def _draw_skin_misconduct_hearing(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render misconduct_hearing simulation skin for academic integrity inquiry."""
        jx, jy = effects.jitter_offset

        # Stakes Accent Header & Case File Reference Tag
        header_y = 95
        self._draw_text(
            "ACADEMIC INTEGRITY BOARD — INQUIRY PROCEEDING",
            self.font_title,
            COLOR_TEXT_PRIMARY,
            (60 + jx, header_y + jy),
        )
        self._draw_text(
            "CASE FILE: #AIB-2026-08492 // PANEL INQUIRY // FORMAL RECORDING ACTIVE",
            self.font_small,
            COLOR_TIMER_AMBER,
            (60 + jx, header_y + 32 + jy),
        )
        pygame.draw.line(self.screen, (58, 58, 58), (60, header_y + 54), (self.width - 60, header_y + 54), 1)

        # 3 Committee Members (TSST evaluative unreactive observation)
        member_xs = [320, 640, 960]
        titles = ["PROF. DR. VANCE (CHAIR)", "DEAN OF ACADEMIC AFFAIRS", "STUDENT ADVOCATE (OBSERVER)"]
        for k in range(3):
            mx = member_xs[k]
            head_y = 166
            # Silhouette Torso (Grayscale suit)
            torso_pts = [
                (mx - 48, 226),
                (mx + 48, 226),
                (mx + 32, 186),
                (mx - 32, 186),
            ]
            pygame.draw.polygon(self.screen, (36, 36, 36), torso_pts)
            # White collar & tie
            pygame.draw.polygon(self.screen, (165, 165, 165), [(mx - 10, 186), (mx + 10, 186), (mx, 202)])
            pygame.draw.line(self.screen, (58, 58, 58), (mx, 196), (mx, 212), 3)
            # Silhouette Head
            pygame.draw.circle(self.screen, (54, 54, 54), (mx, head_y), 20)
            pygame.draw.circle(self.screen, (40, 40, 40), (mx, head_y), 17)
            # Neutral, completely unreactive observation eyes and mouth (TSST)
            pygame.draw.line(self.screen, (80, 80, 80), (mx - 9, head_y - 2), (mx - 3, head_y - 2), 2)
            pygame.draw.line(self.screen, (80, 80, 80), (mx + 3, head_y - 2), (mx + 9, head_y - 2), 2)
            pygame.draw.line(self.screen, (85, 85, 85), (mx - 6, head_y + 7), (mx + 6, head_y + 7), 2)

        # Imposing Dark Committee Table across Mid-Ground (elevated to clear observation banner)
        table_rect = pygame.Rect(60, 206, self.width - 120, 56)
        pygame.draw.rect(self.screen, (32, 32, 32), table_rect, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, table_rect, width=1, border_radius=0)
        pygame.draw.line(self.screen, (82, 82, 82), (65, 208), (self.width - 65, 208), 2)

        for k in range(3):
            mx = member_xs[k]
            # Case dossier folders on table
            pygame.draw.rect(self.screen, (180, 180, 180), (mx - 85, 214, 24, 18), border_radius=0)
            pygame.draw.rect(self.screen, COLOR_PRIMARY_ACTIVE, (mx - 85, 214, 6, 18), border_radius=0)
            # Nameplate
            plate_rect = pygame.Rect(mx - 110, 234, 220, 22)
            pygame.draw.rect(self.screen, (40, 40, 40), plate_rect, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE, plate_rect, width=1, border_radius=0)
            self._draw_text(titles[k], self.font_small, (175, 175, 175), plate_rect.center, center=True, max_width=plate_rect.width - 12)

        self._draw_text(
            "COMMITTEE PANEL IS OBSERVING — FORMAL RECORDING IN PROGRESS",
            self.font_small,
            (125, 125, 125),
            (self.width // 2, 278),
            center=True,
        )

        # Hearing Statement Terminal (Foreground)
        term_y = 295
        term_h = 405
        term_rect = pygame.Rect(60 + jx, term_y + jy, self.width - 120, term_h)
        self._draw_card(term_rect, COLOR_HAIRLINE, bg_color=(24, 24, 24))

        # Terminal Header Bar
        top_bar = pygame.Rect(term_rect.left, term_rect.top, term_rect.width, 36)
        pygame.draw.rect(self.screen, (36, 36, 36), top_bar, border_top_left_radius=0, border_top_right_radius=0)
        self._draw_text(
            "OFFICIAL STATEMENT TERMINAL — FORMAL SUBMISSION DRAFT",
            self.font_small,
            COLOR_ACCENT_CYAN,
            (top_bar.left + 20, top_bar.centery),
            midleft=True,
        )
        self._draw_text(
            "BINDING SUBMISSION",
            self.font_small,
            COLOR_TIMER_RED,
            (top_bar.right - 20, top_bar.centery),
            midright=True,
        )

        # Instruction text
        self._draw_text(
            "Select your official statement to enter into the permanent inquiry record:",
            self.font_body,
            COLOR_TEXT_SECONDARY,
            (term_rect.left + 25, term_rect.top + 46),
        )

        # Participant Statement Options (Keys 1-3)
        start_opt_y = term_rect.top + 74
        opt_card_h = 80
        opt_gap = 10
        for i, opt in enumerate(scenario.options):
            oy = start_opt_y + i * (opt_card_h + opt_gap)
            orect = pygame.Rect(term_rect.left + 20, oy, term_rect.width - 40, opt_card_h)

            is_sel = (selected_index == i)
            # The participant's own choice is marked in white; Rosso stays reserved for stress triggers
            border = COLOR_TEXT_PRIMARY if is_sel else (COLOR_HAIRLINE_SUBTLE if selected_index is not None else COLOR_HAIRLINE)
            bg = (37, 37, 37) if is_sel else (28, 28, 28)
            self._draw_card(orect, border, bg)

            badge = pygame.Rect(orect.left + 16, orect.centery - 20, 40, 40)
            self._draw_key_badge(badge, str(opt.key), selected=is_sel)

            text_rect = pygame.Rect(badge.right + 20, orect.top + 10, orect.width - 85, orect.height - 20)
            self._draw_wrapped_text(opt.text, self.font_body, COLOR_TEXT_PRIMARY, text_rect, spacing=4, center_v=True)

        self._draw_text(
            "PRESS KEY [1], [2], OR [3] TO LOG FORMAL PLEA. DECISION IS IRREVOCABLE.",
            self.font_small,
            (135, 135, 135),
            (term_rect.centerx, term_rect.bottom - 20),
            center=True,
        )
        return True
