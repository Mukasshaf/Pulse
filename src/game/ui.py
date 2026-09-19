"""UI rendering primitives and full-screen state renderers for Pulse."""
from __future__ import annotations

import math

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_ACCENT_INDIGO,
    COLOR_BG,
    COLOR_CARD_BG,
    COLOR_REST_GRADIENT_BOTTOM,
    COLOR_REST_GRADIENT_TOP,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_GREEN,
    COLOR_TIMER_RED,
    DomainID,
    MIST_WRONG_FLASH_COLOR,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_effects import UIEffectState


class UIRenderer:
    """Master rendering subsystem responsible for frame composition and presentation."""

    FONT_FALLBACKS: list[str | None] = ["segoeui", "arial", "helvetica", None]

    def __init__(self, screen: pygame.Surface) -> None:
        """Initialize font caches and display geometry."""
        self.screen: pygame.Surface = screen
        self.width: int = screen.get_width()
        self.height: int = screen.get_height()
        self._init_fonts()

    def _init_fonts(self) -> None:
        """Load system fonts with fallback to default pygame font."""
        if not pygame.font.get_init():
            pygame.font.init()

        def load_font(size: int, bold: bool = False) -> pygame.font.Font:
            for name in self.FONT_FALLBACKS:
                try:
                    if name is not None:
                        return pygame.font.SysFont(name, size, bold=bold)
                    return pygame.font.Font(None, size)
                except (pygame.error, OSError):
                    continue
            return pygame.font.Font(None, size)

        self.font_hero: pygame.font.Font = load_font(44, bold=True)
        self.font_title: pygame.font.Font = load_font(28, bold=True)
        self.font_body: pygame.font.Font = load_font(20, bold=False)
        self.font_small: pygame.font.Font = load_font(16, bold=False)

    def _draw_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        pos: tuple[int, int],
        center: bool = False,
    ) -> pygame.Rect:
        """Render a single line of text."""
        surf = font.render(text, True, color)
        rect = surf.get_rect()
        if center:
            rect.center = pos
        else:
            rect.topleft = pos
        self.screen.blit(surf, rect)
        return rect

    def _draw_wrapped_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        rect: pygame.Rect,
        spacing: int = 5,
    ) -> int:
        """Render multi-line text wrapped within a bounding rect. Returns final y."""
        words = text.split(" ")
        lines: list[str] = []
        curr_line = ""
        for word in words:
            test_line = f"{curr_line} {word}".strip()
            if font.size(test_line)[0] <= rect.width:
                curr_line = test_line
            else:
                if curr_line:
                    lines.append(curr_line)
                curr_line = word
        if curr_line:
            lines.append(curr_line)

        y = rect.top
        for line in lines:
            surf = font.render(line, True, color)
            self.screen.blit(surf, (rect.left, y))
            y += surf.get_height() + spacing
        return y

    def _draw_card(
        self,
        rect: pygame.Rect,
        border_color: tuple[int, int, int] | None = None,
        bg_color: tuple[int, int, int] = COLOR_CARD_BG,
    ) -> None:
        """Draw a rounded panel card with optional accent border."""
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=8)
        if border_color is not None:
            pygame.draw.rect(self.screen, border_color, rect, width=2, border_radius=8)

    def draw_id_input(self, current_text: str, error_msg: str | None) -> None:
        """Render participant ID entry screen."""
        self.screen.fill(COLOR_BG)
        card_rect = pygame.Rect(self.width // 2 - 250, self.height // 2 - 140, 500, 280)
        self._draw_card(card_rect, COLOR_ACCENT_INDIGO)

        self._draw_text("PULSE ENGINE", self.font_hero, COLOR_TEXT_PRIMARY, (self.width // 2, card_rect.top + 50), center=True)
        self._draw_text("Enter Subject ID (e.g. S01):", self.font_body, COLOR_TEXT_SECONDARY, (self.width // 2, card_rect.top + 105), center=True)

        box_rect = pygame.Rect(self.width // 2 - 120, card_rect.top + 140, 240, 48)
        pygame.draw.rect(self.screen, (22, 22, 32), box_rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_ACCENT_CYAN, box_rect, width=2, border_radius=6)

        display_str = current_text + ("_" if (pygame.time.get_ticks() // 500) % 2 == 0 else "")
        self._draw_text(display_str, self.font_title, COLOR_TEXT_PRIMARY, box_rect.center, center=True)

        if error_msg:
            self._draw_text(error_msg, self.font_small, COLOR_TIMER_RED, (self.width // 2, box_rect.bottom + 20), center=True)
        else:
            self._draw_text("Press ENTER to confirm", self.font_small, COLOR_TEXT_SECONDARY, (self.width // 2, box_rect.bottom + 20), center=True)

    def draw_baseline(self, elapsed_s: float, total_s: float) -> None:
        """Render physiological baseline calibration with breathing pacer."""
        self.screen.fill(COLOR_BG)
        rem_s = max(0, int(round(total_s - elapsed_s)))

        cycle = 8.0  # 4s inhale, 4s exhale
        phase = (elapsed_s % cycle) / cycle
        t_cycle = (math.sin(phase * 2.0 * math.pi - math.pi / 2.0) + 1.0) / 2.0
        radius = int(50 + t_cycle * 60)
        center = (self.width // 2, self.height // 2 - 20)

        pygame.draw.circle(self.screen, (25, 35, 55), center, 125)
        pygame.draw.circle(self.screen, COLOR_ACCENT_INDIGO, center, radius, width=4)
        pygame.draw.circle(self.screen, (45, 65, 105), center, max(5, radius - 4))

        guide = "Breathe In..." if phase < 0.5 else "Breathe Out..."
        self._draw_text("BASELINE PHYSIOLOGICAL CALIBRATION", self.font_title, COLOR_TEXT_PRIMARY, (self.width // 2, 80), center=True)
        self._draw_text("Relax your hands and follow the breathing circle.", self.font_body, COLOR_TEXT_SECONDARY, (self.width // 2, 120), center=True)
        self._draw_text(guide, self.font_title, COLOR_ACCENT_CYAN, (self.width // 2, self.height // 2 + 130), center=True)
        self._draw_text(f"Calibration Time Remaining: {rem_s}s", self.font_body, COLOR_TEXT_SECONDARY, (self.width // 2, self.height - 80), center=True)

    def draw_priming(self, scenario: Scenario, elapsed_s: float) -> None:
        """Render scenario priming instructions and stakes briefing."""
        self.screen.fill(COLOR_BG)
        rem_s = max(0, int(round(scenario.priming_duration_s - elapsed_s)))

        card_rect = pygame.Rect(self.width // 2 - 450, self.height // 2 - 190, 900, 380)
        self._draw_card(card_rect, COLOR_ACCENT_INDIGO)

        self._draw_text(scenario.domain_id.value.replace("_", " ").upper(), self.font_small, COLOR_ACCENT_CYAN, (card_rect.left + 40, card_rect.top + 30))
        self._draw_text(scenario.title, self.font_hero, COLOR_TEXT_PRIMARY, (card_rect.left + 40, card_rect.top + 55))
        self._draw_text(f"Paradigm: {scenario.paradigm}", self.font_small, COLOR_TEXT_SECONDARY, (card_rect.left + 40, card_rect.top + 108))

        text_rect = pygame.Rect(card_rect.left + 40, card_rect.top + 145, card_rect.width - 80, 150)
        self._draw_wrapped_text(scenario.priming_text, self.font_body, COLOR_TEXT_PRIMARY, text_rect, spacing=8)
        self._draw_text(f"Scenario begins in {rem_s}s...", self.font_body, COLOR_ACCENT_CYAN, (self.width // 2, card_rect.bottom - 40), center=True)

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

        # Timer bar
        frac = max(0.0, time_remaining_s / float(scenario.decision_duration_s))
        bar_w = int((self.width - 100) * frac)
        pygame.draw.rect(self.screen, (40, 40, 50), (50, 75, self.width - 100, 10), border_radius=4)
        pygame.draw.rect(self.screen, effects.timer_bar_color, (50, 75, bar_w, 10), border_radius=4)

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
            card_h = 75
        else:
            start_y = 130
            gap = 14
            card_h = 100 if n <= 2 else (75 if n == 3 else 64)

        for i, opt in enumerate(opts):
            y = start_y + i * (card_h + gap)
            rect = pygame.Rect(60 + jx, y + jy, self.width - 120, card_h)
            is_sel = selected_index == i
            border = COLOR_ACCENT_CYAN if is_sel else ((60, 60, 80) if selected_index is not None else None)
            bg = (40, 45, 65) if is_sel else COLOR_CARD_BG
            self._draw_card(rect, border, bg)

            key_badge = pygame.Rect(rect.left + 15, rect.centery - 18, 36, 36)
            pygame.draw.rect(self.screen, COLOR_ACCENT_INDIGO, key_badge, border_radius=6)
            self._draw_text(str(opt.key), self.font_title, COLOR_TEXT_PRIMARY, key_badge.center, center=True)

            text_rect = pygame.Rect(key_badge.right + 20, rect.top + 12, rect.width - 90, rect.height - 24)
            self._draw_wrapped_text(opt.text, self.font_body, COLOR_TEXT_PRIMARY, text_rect)

    def _draw_mist_decision(self, runner: MISTRunner, effects: UIEffectState, selected_index: int | None) -> None:
        """Render MIST arithmetic layout with peer progress bar."""
        self.draw_peer_average_bar(runner.get_progress_fraction(), runner.get_peer_progress_fraction())
        prob = runner.get_current_problem()
        if not prob:
            return

        q_rect = pygame.Rect(self.width // 2 - 300, 170, 600, 90)
        self._draw_card(q_rect, COLOR_ACCENT_INDIGO)
        self._draw_text(prob.question_text, self.font_hero, COLOR_TEXT_PRIMARY, q_rect.center, center=True)

        for i, ans in enumerate(prob.options):
            col = i % 2
            row = i // 2
            bx = self.width // 2 - 300 + col * 315
            by = 285 + row * 85
            btn_rect = pygame.Rect(bx, by, 285, 70)

            bg = MIST_WRONG_FLASH_COLOR if (effects.is_flashing and selected_index == i) else COLOR_CARD_BG
            border = COLOR_ACCENT_CYAN if selected_index == i else None
            self._draw_card(btn_rect, border, bg)

            badge = pygame.Rect(btn_rect.left + 15, btn_rect.centery - 16, 32, 32)
            pygame.draw.rect(self.screen, COLOR_ACCENT_INDIGO, badge, border_radius=6)
            self._draw_text(str(i + 1), self.font_title, COLOR_TEXT_PRIMARY, badge.center, center=True)
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
            self._draw_card(rect, COLOR_ACCENT_CYAN if is_sel else None)
            badge = pygame.Rect(rect.left + 15, rect.centery - 16, 32, 32)
            pygame.draw.rect(self.screen, COLOR_ACCENT_INDIGO, badge, border_radius=6)
            self._draw_text(str(opt.key), self.font_title, COLOR_TEXT_PRIMARY, badge.center, center=True)
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
        self._draw_card(counter_rect, COLOR_ACCENT_INDIGO)
        self._draw_text(f"Chest Multiplier: {runner.get_current_value()}", self.font_hero, COLOR_ACCENT_CYAN, counter_rect.center, center=True)

        for i, opt in enumerate(scenario.options):
            by = 310 + i * 85
            rect = pygame.Rect(self.width // 2 - 260 + vx, by + vy, 520, 70)
            is_sel = selected_index == i
            self._draw_card(rect, COLOR_ACCENT_CYAN if is_sel else None)
            badge = pygame.Rect(rect.left + 15, rect.centery - 16, 32, 32)
            pygame.draw.rect(self.screen, COLOR_ACCENT_INDIGO, badge, border_radius=6)
            self._draw_text(str(opt.key), self.font_title, COLOR_TEXT_PRIMARY, badge.center, center=True)
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

    def _draw_skin_exam_hall(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render exam_hall simulation skin (stub)."""
        return False

    def _draw_skin_misconduct_hearing(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render misconduct_hearing simulation skin (stub)."""
        return False

    def _draw_skin_group_chat(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render group_chat simulation skin (stub)."""
        return False

    def _draw_skin_team_kanban(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render team_kanban simulation skin (stub)."""
        return False

    def _draw_skin_reward_crate(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render reward_crate simulation skin (stub)."""
        return False

    def _draw_skin_document_workspace(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render document_workspace simulation skin (stub)."""
        return False

    def _draw_skin_tournament_bracket(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render tournament_bracket simulation skin (stub)."""
        return False

    def _draw_skin_social_analytics(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render social_analytics simulation skin (stub)."""
        return False

    def _draw_skin_portal_log(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render portal_log simulation skin (stub)."""
        return False

    def _draw_skin_code_diff(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render code_diff simulation skin (stub)."""
        return False

    def _draw_skin_fork_map(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render fork_map simulation skin (stub)."""
        return False

    def _draw_skin_notification_stack(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render notification_stack simulation skin (stub)."""
        return False

    def _draw_skin_defense_stage(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render defense_stage simulation skin (stub)."""
        return False

    def _draw_skin_classroom_critique(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render classroom_critique simulation skin (stub)."""
        return False

    def draw_peer_average_bar(self, user_frac: float, peer_frac: float) -> None:
        """Render MIST social comparison progress bars."""
        rect = pygame.Rect(self.width // 2 - 320, 100, 640, 50)
        self._draw_card(rect)
        # Peer bar (red)
        self._draw_text("Peer Group Average:", self.font_small, COLOR_TEXT_SECONDARY, (rect.left + 10, rect.top + 8))
        pygame.draw.rect(self.screen, (50, 50, 60), (rect.left + 170, rect.top + 10, 450, 12), border_radius=3)
        pygame.draw.rect(self.screen, COLOR_TIMER_RED, (rect.left + 170, rect.top + 10, int(450 * peer_frac), 12), border_radius=3)
        # User bar (cyan)
        self._draw_text("Your Progress:", self.font_small, COLOR_TEXT_SECONDARY, (rect.left + 10, rect.top + 28))
        pygame.draw.rect(self.screen, (50, 50, 60), (rect.left + 170, rect.top + 30, 450, 12), border_radius=3)
        pygame.draw.rect(self.screen, COLOR_ACCENT_CYAN, (rect.left + 170, rect.top + 30, int(450 * user_frac), 12), border_radius=3)

    def draw_instability_gauge(self, fraction: float, pos: tuple[int, int]) -> None:
        """Render system instability meter for BART and Accumulator."""
        frac = max(0.0, min(1.0, fraction))
        cx, cy = pos
        rect = pygame.Rect(cx - 180, cy, 360, 20)
        self._draw_text("System Instability Meter", self.font_small, COLOR_TEXT_SECONDARY, (cx, cy - 14), center=True)
        pygame.draw.rect(self.screen, (40, 40, 55), rect, border_radius=4)
        gauge_color = COLOR_TIMER_GREEN if frac < 0.4 else (COLOR_TIMER_AMBER if frac < 0.75 else COLOR_TIMER_RED)
        pygame.draw.rect(self.screen, gauge_color, (rect.left, rect.top, int(rect.width * frac), rect.height), border_radius=4)

    def draw_team_chat(self, pos: tuple[int, int]) -> None:
        """Render Asch conformity group display with 4 avatars for Peer Influence."""
        x, y = pos
        rect = pygame.Rect(x, y, self.width - 120, 95)
        self._draw_card(rect, (50, 50, 70))
        self._draw_text("Project Team Discussion & Submissions (4/4 Completed)", self.font_small, COLOR_TEXT_SECONDARY, (rect.left + 20, rect.top + 8))
        avatars = ["Dev 1 (Lead)", "Dev 2", "Dev 3", "Dev 4"]
        for i, name in enumerate(avatars):
            ax = rect.left + 25 + i * 280
            ay = rect.top + 34
            pygame.draw.circle(self.screen, COLOR_ACCENT_INDIGO, (ax + 14, ay + 14), 14)
            self._draw_text(str(i + 1), self.font_small, COLOR_TEXT_PRIMARY, (ax + 14, ay + 14), center=True)
            self._draw_text(f"{name}: Vote Option 1", self.font_small, COLOR_TEXT_PRIMARY, (ax + 35, ay + 4))
        self._draw_text("Notice: Your vote is visible to all team members.", self.font_small, COLOR_ACCENT_CYAN, (rect.left + 20, rect.bottom - 22))

    def draw_evaluator_panel(self, pos: tuple[int, int]) -> None:
        """Render simulated neutral evaluator panel for TSST (Domain 7)."""
        x, y = pos
        rect = pygame.Rect(x, y, 300, 110)
        self._draw_card(rect, (50, 50, 70))
        self._draw_text("Evaluation Committee (Active)", self.font_small, COLOR_TEXT_SECONDARY, (rect.centerx, rect.top + 12), center=True)
        for i in range(3):
            px = rect.left + 35 + i * 85
            py = rect.top + 55
            pygame.draw.circle(self.screen, (70, 75, 95), (px, py), 22)
            pygame.draw.circle(self.screen, (40, 45, 60), (px, py), 18)
            # Neutral line mouth
            pygame.draw.line(self.screen, COLOR_TEXT_SECONDARY, (px - 8, py + 6), (px + 8, py + 6), 2)

    def draw_composure_bar(self, fraction: float, pos: tuple[int, int]) -> None:
        """Render MPU6050 biofeedback deception composure bar."""
        frac = max(0.0, min(1.0, fraction))
        x, y = pos
        rect = pygame.Rect(x, y, self.width - 100, 16)
        self._draw_text("Physiological Composure Analysis: Active", self.font_small, COLOR_ACCENT_CYAN, (x, y - 16))
        pygame.draw.rect(self.screen, (40, 40, 50), rect, border_radius=4)
        col = COLOR_TIMER_GREEN if frac > 0.6 else (COLOR_TIMER_AMBER if frac > 0.3 else COLOR_TIMER_RED)
        pygame.draw.rect(self.screen, col, (rect.left, rect.top, int(rect.width * frac), rect.height), border_radius=4)

    def draw_post_wait(self, text: str, elapsed_fraction: float) -> None:
        """Render delay wait screen for Future Uncertainty domain."""
        self.screen.fill(COLOR_BG)
        card_rect = pygame.Rect(self.width // 2 - 300, self.height // 2 - 120, 600, 240)
        self._draw_card(card_rect, COLOR_ACCENT_INDIGO)

        # Spinning arc indicator
        angle = (elapsed_fraction * 720) % 360
        center = (self.width // 2, self.height // 2 - 30)
        arc_rect = pygame.Rect(center[0] - 30, center[1] - 30, 60, 60)
        pygame.draw.arc(self.screen, COLOR_ACCENT_CYAN, arc_rect, math.radians(angle), math.radians(angle + 120), 4)

        self._draw_text(text, self.font_title, COLOR_TEXT_PRIMARY, (self.width // 2, self.height // 2 + 35), center=True)
        self._draw_text("Please remain still during analysis.", self.font_small, COLOR_TEXT_SECONDARY, (self.width // 2, self.height // 2 + 75), center=True)

    def draw_feedback(self, consequence_text: str, elapsed_s: float) -> None:
        """Render scenario consequence narrative feedback."""
        self.screen.fill(COLOR_BG)
        card_rect = pygame.Rect(self.width // 2 - 400, self.height // 2 - 130, 800, 260)
        self._draw_card(card_rect, COLOR_ACCENT_INDIGO)

        self._draw_text("CONSEQUENCE RECORDED", self.font_small, COLOR_ACCENT_CYAN, (self.width // 2, card_rect.top + 35), center=True)
        text_rect = pygame.Rect(card_rect.left + 50, card_rect.top + 80, card_rect.width - 100, 140)
        self._draw_wrapped_text(consequence_text, self.font_title, COLOR_TEXT_PRIMARY, text_rect, spacing=8)

    def draw_rest(self, is_inter_domain: bool, time_remaining_s: float) -> None:
        """Render soothing rest gradient screen between scenarios or domains."""
        # Top-to-bottom gradient
        for y in range(self.height):
            ratio = y / float(self.height)
            r = int(COLOR_REST_GRADIENT_TOP[0] + (COLOR_REST_GRADIENT_BOTTOM[0] - COLOR_REST_GRADIENT_TOP[0]) * ratio)
            g = int(COLOR_REST_GRADIENT_TOP[1] + (COLOR_REST_GRADIENT_BOTTOM[1] - COLOR_REST_GRADIENT_TOP[1]) * ratio)
            b = int(COLOR_REST_GRADIENT_TOP[2] + (COLOR_REST_GRADIENT_BOTTOM[2] - COLOR_REST_GRADIENT_TOP[2]) * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (self.width, y))

        rem_s = max(0, int(round(time_remaining_s)))
        title = "Inter-Domain Rest Period" if is_inter_domain else "Intra-Domain Recovery"
        self._draw_text(title, self.font_hero, COLOR_TEXT_PRIMARY, (self.width // 2, self.height // 2 - 60), center=True)
        self._draw_text("Rest quietly. Next section begins shortly.", self.font_body, COLOR_TEXT_SECONDARY, (self.width // 2, self.height // 2 - 5), center=True)
        self._draw_text(f"{rem_s}s", self.font_hero, COLOR_ACCENT_CYAN, (self.width // 2, self.height // 2 + 65), center=True)

    def draw_debrief(self, total_duration_s: float, scenarios_completed: int) -> None:
        """Render final session completion debrief screen."""
        self.screen.fill(COLOR_BG)
        card_rect = pygame.Rect(self.width // 2 - 350, self.height // 2 - 160, 700, 320)
        self._draw_card(card_rect, COLOR_ACCENT_CYAN)

        self._draw_text("SESSION COMPLETE", self.font_hero, COLOR_TEXT_PRIMARY, (self.width // 2, card_rect.top + 45), center=True)
        self._draw_text("Thank you for your participation.", self.font_title, COLOR_ACCENT_CYAN, (self.width // 2, card_rect.top + 105), center=True)

        mins = int(total_duration_s // 60)
        secs = int(total_duration_s % 60)
        time_str = f"{mins:02d}:{secs:02d}"
        self._draw_text(f"Total Session Duration: {time_str}", self.font_body, COLOR_TEXT_SECONDARY, (self.width // 2, card_rect.top + 165), center=True)
        self._draw_text(f"Scenarios Completed: {scenarios_completed}", self.font_body, COLOR_TEXT_SECONDARY, (self.width // 2, card_rect.top + 205), center=True)
        self._draw_text("Press ESC or close the window to exit.", self.font_small, COLOR_TEXT_SECONDARY, (self.width // 2, card_rect.bottom - 40), center=True)
