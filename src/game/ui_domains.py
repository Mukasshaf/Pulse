"""Decision-phase renderer for Pulse: skin dispatch plus the skinless fallback layouts."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_BG,
    COLOR_CARD_BG,
    COLOR_HAIRLINE,
    COLOR_HAIRLINE_SUBTLE,
    COLOR_PRIMARY_ROSSO,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    MIST_ITEM_BAR_RED_FRACTION,
    MIST_WRONG_FLASH_COLOR,
    DomainID,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.skins.classroom_critique import ClassroomCritiqueSkin
from src.game.skins.code_diff import CodeDiffSkin
from src.game.skins.defense_stage import DefenseStageSkin
from src.game.skins.document_workspace import DocumentWorkspaceSkin
from src.game.skins.exam_hall import ExamHallSkin
from src.game.skins.fork_map import ForkMapSkin
from src.game.skins.group_chat import GroupChatSkin
from src.game.skins.misconduct_hearing import MisconductHearingSkin
from src.game.skins.notification_stack import NotificationStackSkin
from src.game.skins.portal_log import PortalLogSkin
from src.game.skins.reward_crate import RewardCrateSkin
from src.game.skins.social_analytics import SocialAnalyticsSkin
from src.game.skins.team_kanban import TeamKanbanSkin
from src.game.skins.tournament_bracket import TournamentBracketSkin
from src.game.ui_effects import UIEffectState


class UIDomainSkins(
    ExamHallSkin,
    MisconductHearingSkin,
    GroupChatSkin,
    TeamKanbanSkin,
    RewardCrateSkin,
    DocumentWorkspaceSkin,
    TournamentBracketSkin,
    SocialAnalyticsSkin,
    PortalLogSkin,
    CodeDiffSkin,
    ForkMapSkin,
    NotificationStackSkin,
    DefenseStageSkin,
    ClassroomCritiqueSkin,
):
    """Composes the 14 simulation skins and dispatches the decision screen to the right one."""

    def draw_decision(
        self,
        scenario: Scenario,
        time_remaining_s: float,
        selected_index: int | None,
        effects: UIEffectState,
        mist_runner: MISTRunner | None,
        bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None,
        composure_fraction: float | None,
    ) -> None:
        """Render active decision screen with options, timer bar, and domain widgets."""
        self.screen.fill(COLOR_BG)
        jx, jy = effects.jitter_offset

        # Header bar
        self._draw_text(scenario.title, self.font_title, COLOR_TEXT_PRIMARY, (50 + jx, 30 + jy))

        # Hold TAB / Q question popup hint pill
        hint_rect = pygame.Rect(self.width - 410 + jx, 28 + jy, 230, 28)
        pygame.draw.rect(self.screen, (32, 32, 32), hint_rect, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE_SUBTLE, hint_rect, width=1, border_radius=0)
        self._draw_text("[ HOLD TAB: VIEW QUESTION ]", self.font_mono_small, COLOR_ACCENT_CYAN, hint_rect.center, center=True)

        # Timer bar (sharp automotive precision)
        frac = max(0.0, time_remaining_s / float(scenario.decision_duration_s))
        bar_w = int((self.width - 100) * frac)
        pygame.draw.rect(self.screen, (36, 36, 36), (50, 75, self.width - 100, 10), border_radius=0)
        pygame.draw.rect(self.screen, effects.timer_bar_color, (50, 75, bar_w, 10), border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, (50, 75, self.width - 100, 10), width=1, border_radius=0)

        rendered = self._render_skin(
            scenario,
            time_remaining_s,
            selected_index,
            effects,
            mist_runner,
            bart_runner,
            reward_runner,
            composure_fraction,
        )
        if not rendered:
            if mist_runner is not None:
                self._draw_mist_decision(mist_runner, effects, selected_index)
            elif bart_runner is not None:
                self._draw_bart_decision(scenario, bart_runner, selected_index)
            elif reward_runner is not None:
                self._draw_reward_decision(scenario, reward_runner, effects, selected_index)
            else:
                self._draw_standard_decision(scenario, selected_index, effects)

            if scenario.has_deception_metric:
                self.draw_evaluator_panel((self.width - 340, 105))
                if composure_fraction is not None:
                    self.draw_composure_bar(composure_fraction, (50, self.height - 50))

    def _draw_standard_decision(self, scenario: Scenario, selected_index: int | None, effects: UIEffectState) -> None:
        """Render standard MCQ options with jitter and selection highlighting."""
        jx, jy = effects.jitter_offset
        opts = scenario.options
        n = len(opts)

        if scenario.domain_id == DomainID.PEER_INFLUENCE and scenario.id == "peer_influence_a":
            self.draw_team_chat((60 + jx, 95 + jy))
            start_y = 205
            gap = 14
            card_h = 78
        else:
            start_y = 125
            gap = 12
            card_h = 100 if n <= 2 else (84 if n == 3 else 78)

        for i, opt in enumerate(opts):
            y = start_y + i * (card_h + gap)
            rect = pygame.Rect(60 + jx, y + jy, self.width - 120, card_h)
            is_sel = selected_index == i
            # The participant's own choice is marked in white; Rosso is reserved for stress triggers
            border = COLOR_TEXT_PRIMARY if is_sel else (COLOR_HAIRLINE_SUBTLE if selected_index is not None else None)
            self._draw_card(rect, border, COLOR_CARD_BG)

            key_badge = pygame.Rect(rect.left + 16, rect.centery - 18, 36, 36)
            self._draw_key_badge(key_badge, str(opt.key), selected=is_sel)

            text_rect = pygame.Rect(key_badge.right + 20, rect.top + 10, rect.width - 90, rect.height - 20)
            self._draw_wrapped_text(opt.text, self.font_body, COLOR_TEXT_PRIMARY, text_rect, spacing=4)

    def _draw_mist_decision(self, runner: MISTRunner, effects: UIEffectState, selected_index: int | None) -> None:
        """Render MIST arithmetic layout with peer progress bar."""
        self.draw_peer_average_bar(runner.get_progress_fraction(), runner.get_peer_progress_fraction())
        prob = runner.get_current_problem()
        if not prob:
            return

        q_rect = pygame.Rect(self.width // 2 - 300, 170, 600, 90)
        self._draw_card(q_rect, COLOR_HAIRLINE_SUBTLE)
        self._draw_text(prob.question_text, self.font_hero, COLOR_TEXT_PRIMARY, q_rect.center, center=True)

        # Per-item countdown (adaptive MIST limit); Rosso only once the item is about to expire
        item_frac = runner.get_item_time_fraction()
        item_col = COLOR_PRIMARY_ROSSO if item_frac <= MIST_ITEM_BAR_RED_FRACTION else COLOR_TEXT_SECONDARY
        pygame.draw.rect(self.screen, item_col, (q_rect.left, q_rect.bottom - 5, int(q_rect.width * item_frac), 5), border_radius=0)

        for i, ans in enumerate(prob.options):
            col = i % 2
            row = i // 2
            bx = self.width // 2 - 300 + col * 315
            by = 285 + row * 85
            btn_rect = pygame.Rect(bx, by, 285, 70)

            is_sel = selected_index == i
            bg = MIST_WRONG_FLASH_COLOR if (effects.is_flashing and is_sel) else COLOR_CARD_BG
            self._draw_card(btn_rect, COLOR_TEXT_PRIMARY if is_sel else None, bg)

            badge = pygame.Rect(btn_rect.left + 15, btn_rect.centery - 16, 32, 32)
            self._draw_key_badge(badge, str(i + 1), selected=is_sel)
            self._draw_text(str(ans), self.font_hero, COLOR_TEXT_PRIMARY, (badge.right + 45, btn_rect.centery), center=True)

    def _draw_bart_decision(self, scenario: Scenario, runner: BARTRunner, selected_index: int | None) -> None:
        """Render BART escalating pump layout."""
        self.draw_instability_gauge(runner.get_instability_fraction(), (self.width // 2, 170))
        val_rect = pygame.Rect(self.width // 2 - 200, 220, 400, 60)
        self._draw_card(val_rect)
        self._draw_text(f"Accumulated Cycles: {runner.pump_count}", self.font_title, COLOR_ACCENT_CYAN, val_rect.center, center=True)

        for i, opt in enumerate(scenario.options):
            by = 310 + i * 85
            rect = pygame.Rect(self.width // 2 - 260, by, 520, 70)
            is_sel = selected_index == i
            self._draw_card(rect, COLOR_TEXT_PRIMARY if is_sel else None)
            badge = pygame.Rect(rect.left + 15, rect.centery - 16, 32, 32)
            # The pump key is shown disabled while the previous pump is still inside its pacing cooldown
            self._draw_key_badge(badge, str(opt.key), selected=is_sel, enabled=(opt.key != 2 or runner.can_pump()))
            self._draw_text(opt.text, self.font_title, COLOR_TEXT_PRIMARY, (rect.centerx + 15, rect.centery), center=True)

    def _draw_reward_decision(
        self,
        scenario: Scenario,
        runner: RewardAccumulator,
        effects: UIEffectState,
        selected_index: int | None,
    ) -> None:
        """Render reward accumulator with screen vibration."""
        vx, vy = effects.vibration_offset
        self.draw_instability_gauge(runner.get_instability_fraction(), (self.width // 2, 160))

        counter_rect = pygame.Rect(self.width // 2 - 200 + vx, 210 + vy, 400, 70)
        self._draw_card(counter_rect, COLOR_ACCENT_CYAN)
        self._draw_text(f"Chest Multiplier: {runner.get_current_value()}", self.font_hero, COLOR_ACCENT_CYAN, counter_rect.center, center=True)

        for i, opt in enumerate(scenario.options):
            by = 310 + i * 85
            rect = pygame.Rect(self.width // 2 - 260 + vx, by + vy, 520, 70)
            is_sel = selected_index == i
            self._draw_card(rect, COLOR_TEXT_PRIMARY if is_sel else None)
            badge = pygame.Rect(rect.left + 15, rect.centery - 16, 32, 32)
            self._draw_key_badge(badge, str(opt.key), selected=is_sel)
            self._draw_text(opt.text, self.font_title, COLOR_TEXT_PRIMARY, (rect.centerx + 15, rect.centery), center=True)

    def _render_skin(
        self,
        scenario: Scenario,
        time_remaining_s: float,
        selected_index: int | None,
        effects: UIEffectState,
        mist_runner: MISTRunner | None,
        bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None,
        composure_fraction: float | None,
    ) -> bool:
        """Dispatch rendering to a domain simulation skin. Return True if handled, False otherwise."""
        if not scenario.skin:
            return False
        skin_method = getattr(self, f"_draw_skin_{scenario.skin}", None)
        if skin_method is not None and callable(skin_method):
            return bool(
                skin_method(
                    scenario,
                    time_remaining_s,
                    selected_index,
                    effects,
                    mist_runner,
                    bart_runner,
                    reward_runner,
                    composure_fraction,
                )
            )
        return False
