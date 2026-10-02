"""Simulation skin `team_kanban` for scenario `peer_influence_b`."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_HAIRLINE,
    COLOR_HAIRLINE_SUBTLE,
    COLOR_SEMANTIC_WARNING,
    COLOR_TEXT_MUTED,
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


class TeamKanbanSkin(UIComponents):
    """Renders the `team_kanban` decision skin."""

    def _draw_skin_team_kanban(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render team_kanban simulation skin: project board showing unanimous blame attribution."""
        jx, jy = effects.jitter_offset

        # Board Header
        header_y = 92
        self._draw_text(
            "PROJECT SPRINT REVIEW // FINAL EVALUATION BOARD",
            self.font_title,
            COLOR_TEXT_PRIMARY,
            (60 + jx, header_y + jy),
        )
        self._draw_text(
            "SPRINT GRADE: CRITICAL DEFICIENCY — MANDATORY ACCOUNTABILITY ATTRIBUTION TRIGGERED",
            self.font_small,
            COLOR_TIMER_RED,
            (60 + jx, header_y + 30 + jy),
        )
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (60, header_y + 52), (self.width - 60, header_y + 52), 1)

        # 4 Project Columns / Module Cards
        modules = [
            ("Module A: Frontend UI", "STATUS: PASS", "Grade: A (94%)", COLOR_TIMER_GREEN, (32, 32, 32)),
            ("Module B: Data Pipeline", "STATUS: PASS", "Grade: A- (90%)", COLOR_TIMER_GREEN, (32, 32, 32)),
            ("Module C: Docs & QA", "STATUS: PASS", "Grade: B+ (88%)", COLOR_TIMER_GREEN, (32, 32, 32)),
            ("Core Integration", "STATUS: FAILED", "Grade: F (0%)", COLOR_TIMER_RED, (24, 24, 24)),
        ]
        card_w = (self.width - 120 - 3 * 14) // 4
        card_h = 76
        cards_y = 152 + jy

        for k, (mod_title, status_text, grade_text, badge_col, bg_col) in enumerate(modules):
            cx = 60 + jx + k * (card_w + 14)
            card_rect = pygame.Rect(cx, cards_y, card_w, card_h)

            border_col = COLOR_TIMER_RED if k == 3 else COLOR_HAIRLINE
            border_width = 2 if k == 3 else 1
            pygame.draw.rect(self.screen, bg_col, card_rect, border_radius=0)
            pygame.draw.rect(self.screen, border_col, card_rect, width=border_width, border_radius=0)

            self._draw_text(mod_title, self.font_body, COLOR_TEXT_PRIMARY, (card_rect.left + 12, card_rect.top + 10))
            self._draw_text(status_text, self.font_small, badge_col, (card_rect.left + 12, card_rect.top + 34))
            self._draw_text(grade_text, self.font_small, (145, 145, 145), (card_rect.left + 12, card_rect.top + 52))

            if k == 3:
                # Warning badge on failed core module
                tag_rect = pygame.Rect(card_rect.right - 70, card_rect.top + 8, 62, 20)
                pygame.draw.rect(self.screen, COLOR_TIMER_RED, tag_rect, border_radius=0)
                self._draw_text("FAILED", self.font_small, (255, 255, 255), tag_rect.center, center=True)

        # Peer Review Submissions (Unanimous Blame Attribution)
        peer_section_y = 238 + jy
        self._draw_text(
            "PEER REVIEW ASSESSMENTS (4 / 4 COMPLETED — UNANIMOUS ATTRIBUTION RECORDED):",
            self.font_small,
            (185, 185, 185),
            (60 + jx, peer_section_y),
        )

        teammates = [
            ("Alex (Lead)", "A", "Core integration module not delivered on time."),
            ("Brandon", "B", "All other modules ready; bottleneck was in core."),
            ("Chloe", "C", "Core module team assigned owner failed to merge."),
            ("Danielle", "D", "System integration broke downstream testing."),
        ]
        peer_card_w = card_w
        peer_card_h = 100
        peer_cards_y = peer_section_y + 20

        for k, (tname, tinit, comment) in enumerate(teammates):
            tx = 60 + jx + k * (peer_card_w + 14)
            trect = pygame.Rect(tx, peer_cards_y, peer_card_w, peer_card_h)

            pygame.draw.rect(self.screen, (32, 32, 32), trect, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE, trect, width=1, border_radius=0)

            # Avatar: neutral plate, teammates are told apart by initial and name rather than by hue
            avatar_cx = trect.left + 22
            avatar_cy = trect.top + 20
            pygame.draw.circle(self.screen, COLOR_TEXT_MUTED, (avatar_cx, avatar_cy), 12)
            self._draw_text(tinit, self.font_small, COLOR_TEXT_PRIMARY, (avatar_cx, avatar_cy), center=True)

            self._draw_text(tname, self.font_small, COLOR_TEXT_PRIMARY, (avatar_cx + 18, trect.top + 10))

            # Comment wrapped
            comment_rect = pygame.Rect(trect.left + 10, trect.top + 34, trect.width - 20, 36)
            self._draw_wrapped_text(comment, self.font_small, (145, 145, 145), comment_rect, spacing=2)

            # Explicit Blame Attribution Tag
            tag_box = pygame.Rect(trect.left + 8, trect.bottom - 24, trect.width - 16, 18)
            pygame.draw.rect(self.screen, (24, 24, 24), tag_box, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_TIMER_RED, tag_box, width=1, border_radius=0)
            self._draw_text("Failure Attribution: YOU", self.font_mono_small, COLOR_SEMANTIC_WARNING, tag_box.center, center=True)

        # Participant Action Panel (Foreground)
        panel_y = 372 + jy
        panel_h = 330
        panel_rect = pygame.Rect(60 + jx, panel_y, self.width - 120, panel_h)
        self._draw_card(panel_rect, (60, 60, 60), bg_color=(24, 24, 24))

        # Action Panel Header
        top_bar = pygame.Rect(panel_rect.left, panel_rect.top, panel_rect.width, 34)
        pygame.draw.rect(self.screen, (36, 36, 36), top_bar, border_top_left_radius=0, border_top_right_radius=0)
        self._draw_text(
            "FORMAL DISCIPLINARY RESPONSE // MANDATORY PLEA ENTRY",
            self.font_small,
            COLOR_ACCENT_CYAN,
            (top_bar.left + 18, top_bar.centery),
            midleft=True,
        )
        self._draw_text(
            "FINAL SUBMISSION",
            self.font_small,
            COLOR_TIMER_AMBER,
            (top_bar.right - 18, top_bar.centery),
            midright=True,
        )

        self._draw_text(
            "Select your official response to the unanimous team attribution (Keys 1 – 3):",
            self.font_body,
            COLOR_TEXT_SECONDARY,
            (panel_rect.left + 20, panel_rect.top + 44),
        )

        # 3 Response Options (Keys 1-3)
        opt_start_y = panel_rect.top + 68
        opt_card_h = 74
        opt_gap = 8
        tag_labels = ["[ACCEPT]", "[CONTEST]", "[ABSTAIN]"]
        tag_colors = [COLOR_TIMER_AMBER, COLOR_TIMER_RED, COLOR_ACCENT_CYAN]

        for i, opt in enumerate(scenario.options):
            oy = opt_start_y + i * (opt_card_h + opt_gap)
            orect = pygame.Rect(panel_rect.left + 20, oy, panel_rect.width - 40, opt_card_h)
            is_sel = (selected_index == i)

            # The participant's own choice is marked in white; Rosso stays reserved for stress triggers
            border = COLOR_TEXT_PRIMARY if is_sel else (COLOR_HAIRLINE_SUBTLE if selected_index is not None else COLOR_HAIRLINE)
            bg = (37, 37, 37) if is_sel else (28, 28, 28)
            self._draw_card(orect, border, bg_color=bg)

            badge = pygame.Rect(orect.left + 14, orect.centery - 18, 36, 36)
            self._draw_key_badge(badge, str(opt.key), selected=is_sel)

            text_rect = pygame.Rect(badge.right + 18, orect.top + 8, orect.width - 180, orect.height - 16)
            self._draw_wrapped_text(opt.text, self.font_body, COLOR_TEXT_PRIMARY, text_rect, spacing=3, center_v=True)

            tag_label = tag_labels[i] if i < len(tag_labels) else ""
            tag_color = tag_colors[i] if i < len(tag_colors) else COLOR_TEXT_SECONDARY
            self._draw_text(tag_label, self.font_small, tag_color, (orect.right - 90, orect.centery), center=True)

        self._draw_text(
            "PRESS KEY [1], [2], OR [3] TO SUBMIT RESPONSE. YOUR RECORD WILL BE ENTERED IN THE COURSE AUDIT LOG.",
            self.font_small,
            (125, 125, 125),
            (panel_rect.centerx, panel_rect.bottom - 16),
            center=True,
        )

        return True
