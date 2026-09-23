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
    ScenarioType,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_effects import RadialShatterEffect, UIEffectState


class UIRenderer:
    """Master rendering subsystem responsible for frame composition and presentation."""

    FONT_FALLBACKS: list[str | None] = ["segoeui", "arial", "helvetica", None]
    MONO_FONT_FALLBACKS: list[str | None] = ["consolas", "couriernew", "lucidaconsole", "monospace", None]

    def __init__(self, screen: pygame.Surface) -> None:
        """Initialize font caches and display geometry."""
        self.screen: pygame.Surface = screen
        self.width: int = screen.get_width()
        self.height: int = screen.get_height()
        self.shatter_effect: RadialShatterEffect = RadialShatterEffect()
        self._last_fork_choice: int = 0
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

        def load_mono_font(size: int, bold: bool = False) -> pygame.font.Font:
            for name in self.MONO_FONT_FALLBACKS:
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
        self.font_mono: pygame.font.Font = load_mono_font(17, bold=False)
        self.font_mono_small: pygame.font.Font = load_mono_font(14, bold=False)

    def _draw_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        pos: tuple[int, int],
        center: bool = False,
        center_y: bool = False,
        midleft: bool = False,
        midright: bool = False,
    ) -> pygame.Rect:
        """Render a single line of text with optional centering or alignment."""
        surf = font.render(text, True, color)
        rect = surf.get_rect()
        if center:
            rect.center = pos
        elif midleft or center_y:
            rect.midleft = pos
        elif midright:
            rect.midright = pos
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
        spacing: int = 4,
        center_v: bool = False,
        center_h: bool = False,
    ) -> int:
        """Render multi-line text wrapped within a bounding rect with overflow protection. Returns final y."""
        paragraphs = text.split("\n")

        def _wrap_lines(f: pygame.font.Font) -> list[str]:
            res: list[str] = []
            for p in paragraphs:
                p_clean = p.strip()
                if not p_clean:
                    res.append("")
                    continue
                words = p_clean.split(" ")
                curr_line = ""
                for word in words:
                    test_line = f"{curr_line} {word}".strip()
                    if f.size(test_line)[0] <= rect.width:
                        curr_line = test_line
                    else:
                        if curr_line:
                            res.append(curr_line)
                        curr_line = word
                if curr_line:
                    res.append(curr_line)
            return res

        active_font = font
        lines = _wrap_lines(active_font)
        line_h = active_font.get_linesize()
        total_h = len(lines) * (line_h + spacing) - spacing
        # Auto downscale font if lines exceed container height
        if rect.height > 0 and total_h > rect.height:
            for fallback_font in (self.font_title, self.font_body, self.font_small, self.font_mono_small):
                if active_font != fallback_font and fallback_font.get_linesize() < active_font.get_linesize():
                    test_lines = _wrap_lines(fallback_font)
                    test_total = len(test_lines) * (fallback_font.get_linesize() + spacing) - spacing
                    active_font = fallback_font
                    lines = test_lines
                    line_h = active_font.get_linesize()
                    total_h = test_total
                    if total_h <= rect.height:
                        break

        # Calculate starting y position (optionally vertically centered)
        if center_v and rect.height > 0 and total_h < rect.height:
            y = rect.top + max(0, (rect.height - total_h) // 2)
        else:
            y = rect.top

        for line in lines:
            if not line:
                y += line_h // 2 + spacing
                continue
            # Clamping overflow: do not draw outside the container bottom
            if rect.height > 0 and y + line_h > rect.bottom + 6:
                break
            surf = active_font.render(line, True, color)
            line_x = rect.centerx - surf.get_width() // 2 if center_h else rect.left
            self.screen.blit(surf, (line_x, y))
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

    def _draw_compass(self, center: tuple[int, int], radius: int, angle_deg: float) -> None:
        """Render a minimalist compass rose with rotating needle."""
        cx, cy = center
        # Outer dial ring
        pygame.draw.circle(self.screen, (20, 25, 38), (cx, cy), radius)
        pygame.draw.circle(self.screen, (60, 75, 105), (cx, cy), radius, width=2)
        pygame.draw.circle(self.screen, (38, 48, 70), (cx, cy), radius - 6, width=1)

        # Cardinal tick marks & labels
        cardinals = [("N", 0), ("E", 90), ("S", 180), ("W", 270)]
        for label, deg in cardinals:
            rad = math.radians(deg - 90)
            tx1 = cx + int((radius - 5) * math.cos(rad))
            ty1 = cy + int((radius - 5) * math.sin(rad))
            tx2 = cx + int((radius - 1) * math.cos(rad))
            ty2 = cy + int((radius - 1) * math.sin(rad))
            pygame.draw.line(self.screen, (100, 115, 145), (tx1, ty1), (tx2, ty2), 2)

            lx = cx + int((radius + 11) * math.cos(rad))
            ly = cy + int((radius + 11) * math.sin(rad))
            col = (255, 100, 100) if label == "N" else (140, 150, 175)
            self._draw_text(label, self.font_mono_small, col, (lx, ly), center=True)

        # Intermediate ticks
        for deg in (30, 60, 120, 150, 210, 240, 300, 330):
            rad = math.radians(deg - 90)
            tx1 = cx + int((radius - 4) * math.cos(rad))
            ty1 = cy + int((radius - 4) * math.sin(rad))
            tx2 = cx + int((radius - 1) * math.cos(rad))
            ty2 = cy + int((radius - 1) * math.sin(rad))
            pygame.draw.line(self.screen, (45, 55, 75), (tx1, ty1), (tx2, ty2), 1)

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

        # North needle polygon (red)
        pygame.draw.polygon(self.screen, (255, 75, 75), [n_pt, w_pt, (cx, cy)])
        pygame.draw.polygon(self.screen, (200, 45, 45), [n_pt, e_pt, (cx, cy)])

        # South needle polygon (cyan)
        pygame.draw.polygon(self.screen, COLOR_ACCENT_CYAN, [s_pt, w_pt, (cx, cy)])
        pygame.draw.polygon(self.screen, (0, 175, 200), [s_pt, e_pt, (cx, cy)])

        # Center pivot
        pygame.draw.circle(self.screen, (220, 225, 235), (cx, cy), 4)
        pygame.draw.circle(self.screen, (30, 36, 50), (cx, cy), 2)

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

        card_rect = pygame.Rect(self.width // 2 - 500, self.height // 2 - 225, 1000, 450)
        self._draw_card(card_rect, COLOR_ACCENT_INDIGO)

        self._draw_text(scenario.domain_id.value.replace("_", " ").upper(), self.font_small, COLOR_ACCENT_CYAN, (card_rect.left + 45, card_rect.top + 28))

        # Dynamic title font size to prevent overflow
        title_font = self.font_hero if self.font_hero.size(scenario.title)[0] <= card_rect.width - 90 else self.font_title
        self._draw_text(scenario.title, title_font, COLOR_TEXT_PRIMARY, (card_rect.left + 45, card_rect.top + 52))

        # Paradigm tag
        paradigm_rect = pygame.Rect(card_rect.left + 45, card_rect.top + 106, card_rect.width - 90, 36)
        self._draw_wrapped_text(f"Paradigm: {scenario.paradigm}", self.font_small, COLOR_TEXT_SECONDARY, paradigm_rect, spacing=2)

        # Priming text container with generous room
        text_rect = pygame.Rect(card_rect.left + 45, card_rect.top + 148, card_rect.width - 90, 230)
        self._draw_wrapped_text(scenario.priming_text, self.font_body, COLOR_TEXT_PRIMARY, text_rect, spacing=8)
        self._draw_text(
            f"Press [SPACE] to start immediately • Auto-starting in {rem_s}s...",
            self.font_body,
            COLOR_ACCENT_CYAN,
            (self.width // 2, card_rect.bottom - 35),
            center=True,
        )

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
        pygame.draw.rect(self.screen, (22, 28, 42), hint_rect, border_radius=6)
        pygame.draw.rect(self.screen, (60, 75, 110), hint_rect, width=1, border_radius=6)
        self._draw_text("[ HOLD TAB: VIEW QUESTION ]", self.font_mono_small, (150, 180, 220), hint_rect.center, center=True)

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
            card_h = 78
        else:
            start_y = 125
            gap = 12
            card_h = 100 if n <= 2 else (84 if n == 3 else 78)

        for i, opt in enumerate(opts):
            y = start_y + i * (card_h + gap)
            rect = pygame.Rect(60 + jx, y + jy, self.width - 120, card_h)
            is_sel = selected_index == i
            border = COLOR_ACCENT_CYAN if is_sel else ((60, 60, 80) if selected_index is not None else None)
            bg = (40, 45, 65) if is_sel else COLOR_CARD_BG
            self._draw_card(rect, border, bg)

            key_badge = pygame.Rect(rect.left + 16, rect.centery - 18, 36, 36)
            pygame.draw.rect(self.screen, COLOR_ACCENT_INDIGO, key_badge, border_radius=6)
            self._draw_text(str(opt.key), self.font_title, COLOR_TEXT_PRIMARY, key_badge.center, center=True)

            text_rect = pygame.Rect(key_badge.right + 20, rect.top + 10, rect.width - 90, rect.height - 20)
            self._draw_wrapped_text(opt.text, self.font_body, COLOR_TEXT_PRIMARY, text_rect, spacing=4)

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
        """Render exam_hall simulation skin: student desk perspective, paper, peer desks, pacing invigilator."""
        if mist_runner is None:
            return False
        problem = mist_runner.get_current_problem()
        if problem is None:
            return False

        jx, jy = effects.jitter_offset

        # Upper hall perspective wall (y = 90 to 215)
        hall_wall_rect = pygame.Rect(0, 90, self.width, 125)
        pygame.draw.rect(self.screen, (24, 26, 36), hall_wall_rect)
        pygame.draw.line(self.screen, (40, 44, 58), (0, 215), (self.width, 215), 2)
        # Subtle architectural vertical pillars
        for px in (320, 640, 960):
            pygame.draw.line(self.screen, (30, 33, 46), (px, 90), (px, 215), 1)

        # Analog Wall Clock at top-right (counts down with timer)
        clock_cx = self.width - 55
        clock_cy = 42
        clock_radius = 22
        pygame.draw.circle(self.screen, (75, 80, 95), (clock_cx, clock_cy), clock_radius, width=3)
        pygame.draw.circle(self.screen, (235, 235, 230), (clock_cx, clock_cy), clock_radius - 3)
        for hour_idx in range(12):
            ang = hour_idx * (math.pi / 6.0)
            mx = clock_cx + int(math.cos(ang) * (clock_radius - 5))
            my = clock_cy + int(math.sin(ang) * (clock_radius - 5))
            pygame.draw.circle(self.screen, (90, 95, 105), (mx, my), 1)

        duration = max(1.0, float(scenario.decision_duration_s))
        time_frac = max(0.0, min(1.0, time_remaining_s / duration))
        hand_ang = -math.pi / 2.0 + (1.0 - time_frac) * 2.0 * math.pi
        hx = clock_cx + int(math.cos(hand_ang) * 14)
        hy = clock_cy + int(math.sin(hand_ang) * 14)
        pygame.draw.line(self.screen, COLOR_TIMER_RED, (clock_cx, clock_cy), (hx, hy), 2)
        pygame.draw.circle(self.screen, (40, 40, 50), (clock_cx, clock_cy), 3)
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
            pygame.draw.polygon(self.screen, (18, 20, 28), torso_pts)
            pygame.draw.circle(self.screen, (24, 27, 36), (invig_x, invig_y + 6), 11)
            # Clipboard in hand
            pygame.draw.rect(self.screen, (150, 145, 130), (invig_x + 10, invig_y + 20, 10, 14), border_radius=1)
            pygame.draw.line(self.screen, (40, 40, 50), (invig_x + 13, invig_y + 23), (invig_x + 17, invig_y + 23), 1)
            self._draw_text("INVIGILATOR PATROL", self.font_small, (150, 80, 80), (invig_x, invig_y - 12), center=True)

        # Classmate Peer Desks along upper periphery (MIST social-evaluative comparison ~15% ahead)
        user_frac = mist_runner.get_progress_fraction()
        desk_xs = [240, 640, 1040]
        lead_offsets = [0.13, 0.15, 0.17]
        for k in range(3):
            dx = desk_xs[k]
            dy = 168
            # Miniature student silhouette
            pygame.draw.circle(self.screen, (36, 40, 54), (dx, dy - 16), 9)
            torso_pts = [(dx - 15, dy), (dx + 15, dy), (dx + 9, dy - 11), (dx - 9, dy - 11)]
            pygame.draw.polygon(self.screen, (28, 32, 44), torso_pts)
            # Miniature desk & exam paper
            pygame.draw.rect(self.screen, (42, 46, 60), (dx - 40, dy, 80, 16), border_radius=2)
            pygame.draw.rect(self.screen, (215, 215, 210), (dx - 12, dy + 2, 24, 11))
            # Peer progress bar (dynamically stays ~15% ahead)
            peer_val = min(1.0, max(0.12, user_frac + lead_offsets[k]))
            bar_w = 84
            bar_h = 7
            bar_rect = pygame.Rect(dx - 42, dy - 34, bar_w, bar_h)
            pygame.draw.rect(self.screen, (35, 38, 50), bar_rect, border_radius=3)
            fill_col = COLOR_TIMER_AMBER if peer_val < 0.85 else COLOR_TIMER_RED
            pygame.draw.rect(self.screen, fill_col, (bar_rect.left, bar_rect.top, int(bar_w * peer_val), bar_h), border_radius=3)
            self._draw_text(f"Desk {k + 1}: {int(peer_val * 100)}%", self.font_small, (150, 155, 175), (dx, dy - 48), center=True)

        # Foreground Desk: Wood surface
        desk_y = 215
        pygame.draw.rect(self.screen, (36, 30, 26), (0, desk_y, self.width, self.height - desk_y))
        pygame.draw.rect(self.screen, (50, 42, 36), (0, desk_y, self.width, 8))
        pygame.draw.line(self.screen, (22, 18, 16), (0, desk_y + 8), (self.width, desk_y + 8), 2)

        # Exam Paper Surface: Cream / off-white tint (235, 235, 230)
        paper_w = 840
        paper_h = 475
        paper_x = (self.width - paper_w) // 2 + jx
        paper_y = desk_y + 14 + jy
        paper_rect = pygame.Rect(paper_x, paper_y, paper_w, paper_h)
        # Paper drop shadow
        pygame.draw.rect(self.screen, (18, 15, 14), (paper_x + 6, paper_y + 6, paper_w, paper_h), border_radius=3)
        # Paper fill and outline
        pygame.draw.rect(self.screen, (235, 235, 230), paper_rect, border_radius=3)
        pygame.draw.rect(self.screen, (200, 200, 192), paper_rect, width=2, border_radius=3)
        # Margin line
        margin_x = paper_x + 55
        pygame.draw.line(self.screen, (225, 180, 180), (margin_x, paper_y + 10), (margin_x, paper_y + paper_h - 10), 1)

        # Printed paper header
        self._draw_text("OFFICIAL EXAMINATION SCRIPT — ARITHMETIC SPEED & ACCURACY", self.font_small, (90, 95, 110), (margin_x + 16, paper_y + 16))
        self._draw_text(f"CANDIDATE: [CONFIDENTIAL]    |    SECTION 1 / 1    |    TIME LIMIT: {scenario.decision_duration_s}s", self.font_small, (120, 125, 140), (margin_x + 16, paper_y + 36))
        pygame.draw.line(self.screen, (195, 195, 190), (margin_x + 14, paper_y + 56), (paper_x + paper_w - 30, paper_y + 56), 1)

        # MIST Arithmetic Question Overlay
        q_rect = pygame.Rect(margin_x + 15, paper_y + 68, paper_w - 110, 85)
        pygame.draw.rect(self.screen, (244, 244, 240), q_rect, border_radius=4)
        pygame.draw.rect(self.screen, (205, 205, 198), q_rect, width=1, border_radius=4)
        self._draw_text("EVALUATE RAPIDLY:", self.font_small, (85, 90, 105), (q_rect.left + 15, q_rect.top + 8))
        self._draw_text(problem.question_text, self.font_hero, (30, 30, 40), (q_rect.centerx, q_rect.centery + 6), center=True)

        # Wrong Answer Feedback: Prominent red ink cross X for 200ms
        if effects.is_flashing:
            pygame.draw.line(self.screen, (220, 30, 30), (q_rect.left + 25, q_rect.top + 10), (q_rect.right - 25, q_rect.bottom - 10), 6)
            pygame.draw.line(self.screen, (220, 30, 30), (q_rect.left + 25, q_rect.bottom - 10), (q_rect.right - 25, q_rect.top + 10), 6)
            self._draw_text("INCORRECT", self.font_title, (215, 30, 30), (q_rect.centerx, q_rect.centery + 6), center=True)

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
            bg = (215, 230, 252) if is_sel else (246, 246, 242)
            border_col = (50, 95, 190) if is_sel else (190, 190, 182)
            border_w = 2 if is_sel else 1
            pygame.draw.rect(self.screen, bg, btn_rect, border_radius=5)
            pygame.draw.rect(self.screen, border_col, btn_rect, width=border_w, border_radius=5)

            # Checkbox square [1], [2], etc.
            chk_rect = pygame.Rect(btn_rect.left + 15, btn_rect.centery - 18, 36, 36)
            chk_bg = (255, 255, 255) if not is_sel else (225, 238, 255)
            pygame.draw.rect(self.screen, chk_bg, chk_rect, border_radius=4)
            pygame.draw.rect(self.screen, (90, 95, 110), chk_rect, width=2, border_radius=4)
            self._draw_text(f"[{i + 1}]", self.font_title, (40, 45, 60), chk_rect.center, center=True)

            # Answer value in dark charcoal font (30, 30, 40)
            self._draw_text(str(ans), self.font_hero, (30, 30, 40), (chk_rect.right + 70, btn_rect.centery), center=True)

        self._draw_text("RECORD YOUR CHOICE: PRESS KEY [1], [2], [3], OR [4]", self.font_small, (120, 125, 140), (paper_x + paper_w // 2, paper_y + paper_h - 22), center=True)
        return True

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
        pygame.draw.line(self.screen, (55, 58, 72), (60, header_y + 54), (self.width - 60, header_y + 54), 1)

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
            pygame.draw.polygon(self.screen, (34, 36, 46), torso_pts)
            # White collar & tie
            pygame.draw.polygon(self.screen, (160, 165, 175), [(mx - 10, 186), (mx + 10, 186), (mx, 202)])
            pygame.draw.line(self.screen, (55, 58, 68), (mx, 196), (mx, 212), 3)
            # Silhouette Head
            pygame.draw.circle(self.screen, (50, 54, 66), (mx, head_y), 20)
            pygame.draw.circle(self.screen, (38, 40, 50), (mx, head_y), 17)
            # Neutral, completely unreactive observation eyes and mouth (TSST)
            pygame.draw.line(self.screen, (75, 80, 95), (mx - 9, head_y - 2), (mx - 3, head_y - 2), 2)
            pygame.draw.line(self.screen, (75, 80, 95), (mx + 3, head_y - 2), (mx + 9, head_y - 2), 2)
            pygame.draw.line(self.screen, (80, 85, 100), (mx - 6, head_y + 7), (mx + 6, head_y + 7), 2)

        # Imposing Dark Committee Table across Mid-Ground (elevated to clear observation banner)
        table_rect = pygame.Rect(60, 206, self.width - 120, 56)
        pygame.draw.rect(self.screen, (28, 26, 34), table_rect, border_radius=4)
        pygame.draw.rect(self.screen, (55, 52, 65), table_rect, width=2, border_radius=4)
        pygame.draw.line(self.screen, (85, 80, 95), (65, 208), (self.width - 65, 208), 2)

        for k in range(3):
            mx = member_xs[k]
            # Case dossier folders on table
            pygame.draw.rect(self.screen, (190, 180, 155), (mx - 85, 214, 24, 18), border_radius=2)
            pygame.draw.rect(self.screen, (180, 45, 45), (mx - 85, 214, 6, 18), border_radius=1)
            # Nameplate
            plate_rect = pygame.Rect(mx - 110, 234, 220, 22)
            pygame.draw.rect(self.screen, (40, 38, 48), plate_rect, border_radius=2)
            pygame.draw.rect(self.screen, (90, 85, 75), plate_rect, width=1, border_radius=2)
            self._draw_text(titles[k], self.font_small, (180, 175, 160), plate_rect.center, center=True)

        self._draw_text(
            "COMMITTEE PANEL IS ACTIVELY OBSERVING RESPONDENT TESTIMONY (UNREACTING)",
            self.font_small,
            (120, 125, 140),
            (self.width // 2, 278),
            center=True,
        )

        # Hearing Statement Terminal (Foreground)
        term_y = 295
        term_h = 405
        term_rect = pygame.Rect(60 + jx, term_y + jy, self.width - 120, term_h)
        self._draw_card(term_rect, (60, 65, 85), bg_color=(20, 22, 30))

        # Terminal Header Bar
        top_bar = pygame.Rect(term_rect.left, term_rect.top, term_rect.width, 36)
        pygame.draw.rect(self.screen, (30, 34, 46), top_bar, border_top_left_radius=8, border_top_right_radius=8)
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
            border = COLOR_ACCENT_CYAN if is_sel else ((70, 75, 95) if selected_index is not None else (45, 48, 62))
            bg = (38, 45, 65) if is_sel else (25, 28, 38)
            self._draw_card(orect, border, bg)

            badge = pygame.Rect(orect.left + 16, orect.centery - 20, 40, 40)
            pygame.draw.rect(self.screen, COLOR_ACCENT_INDIGO, badge, border_radius=6)
            self._draw_text(str(opt.key), self.font_title, COLOR_TEXT_PRIMARY, badge.center, center=True)

            text_rect = pygame.Rect(badge.right + 20, orect.top + 10, orect.width - 85, orect.height - 20)
            self._draw_wrapped_text(opt.text, self.font_body, COLOR_TEXT_PRIMARY, text_rect, spacing=4, center_v=True)

        self._draw_text(
            "PRESS KEY [1], [2], OR [3] TO LOG FORMAL PLEA. DECISION IS IRREVOCABLE.",
            self.font_small,
            (130, 135, 150),
            (term_rect.centerx, term_rect.bottom - 20),
            center=True,
        )
        return True


    def _draw_skin_group_chat(
        self, scenario: Scenario, time_remaining_s: float, selected_index: int | None,
        effects: UIEffectState, mist_runner: MISTRunner | None, bart_runner: BARTRunner | None,
        reward_runner: RewardAccumulator | None, composure_fraction: float | None,
    ) -> bool:
        """Render group_chat simulation skin: mobile chat interface simulating Asch conformity."""
        jx, jy = effects.jitter_offset

        # Device Frame (Smartphone Mockup in screen center)
        frame_w = 560
        frame_h = 608
        frame_x = (self.width - frame_w) // 2 + jx
        frame_y = 94 + jy
        frame_rect = pygame.Rect(frame_x, frame_y, frame_w, frame_h)

        # Drop shadow
        pygame.draw.rect(self.screen, (10, 12, 18), (frame_x + 6, frame_y + 6, frame_w, frame_h), border_radius=18)
        # Device background
        pygame.draw.rect(self.screen, (16, 18, 26), frame_rect, border_radius=18)
        pygame.draw.rect(self.screen, (55, 60, 78), frame_rect, width=2, border_radius=18)

        # Chat Header: Group title and online status
        header_rect = pygame.Rect(frame_x, frame_y, frame_w, 54)
        pygame.draw.rect(self.screen, (24, 28, 40), header_rect, border_top_left_radius=18, border_top_right_radius=18)
        pygame.draw.line(self.screen, (40, 45, 62), (frame_x, frame_y + 54), (frame_x + frame_w, frame_y + 54), 1)

        # Group avatar circle
        pygame.draw.circle(self.screen, (48, 56, 76), (frame_x + 30, frame_y + 27), 16)
        self._draw_text("CG", self.font_small, COLOR_TEXT_PRIMARY, (frame_x + 30, frame_y + 27), center=True)

        # Header titles
        self._draw_text("Class Group (5 members)", self.font_body, COLOR_TEXT_PRIMARY, (frame_x + 55, frame_y + 11))
        self._draw_text("Maya, Jake, Rohan, Tess, You", self.font_small, (135, 140, 155), (frame_x + 55, frame_y + 32))

        # Online indicator
        dot_cx = frame_x + frame_w - 85
        pygame.draw.circle(self.screen, COLOR_TIMER_GREEN, (dot_cx, frame_y + 27), 4)
        self._draw_text("4 online", self.font_small, COLOR_TIMER_GREEN, (dot_cx + 10, frame_y + 27), midleft=True)

        # Public Visibility Cue banner inside chat
        vis_banner = pygame.Rect(frame_x + 24, frame_y + 62, frame_w - 48, 26)
        pygame.draw.rect(self.screen, (32, 30, 24), vis_banner, border_radius=13)
        pygame.draw.rect(self.screen, (75, 68, 45), vis_banner, width=1, border_radius=13)
        self._draw_text("Notice: Your response will be visible to all members.", self.font_small, (225, 195, 110), vis_banner.center, center=True)

        # 4 Incoming Peer Votes (Asch conformity: all vote conforming)
        peers = [
            ("Maya", "M.", (38, 148, 132), "12:41 PM"),
            ("Jake", "J.", (128, 64, 168), "12:42 PM"),
            ("Rohan", "R.", (205, 102, 38), "12:42 PM"),
            ("Tess", "T.", (48, 112, 210), "12:43 PM"),
        ]
        bubble_y_start = frame_y + 94
        bubble_w = frame_w - 75
        bubble_h = 52
        bubble_gap = 8

        for k, (name, init, col, time_str) in enumerate(peers):
            by = bubble_y_start + k * (bubble_h + bubble_gap)
            # Avatar
            avatar_cx = frame_x + 28
            avatar_cy = by + 20
            pygame.draw.circle(self.screen, col, (avatar_cx, avatar_cy), 13)
            self._draw_text(init, self.font_small, (255, 255, 255), (avatar_cx, avatar_cy), center=True)

            # Chat bubble
            bubble_rect = pygame.Rect(frame_x + 48, by, bubble_w, bubble_h)
            pygame.draw.rect(self.screen, (28, 32, 45), bubble_rect, border_radius=10)
            pygame.draw.rect(self.screen, (42, 48, 66), bubble_rect, width=1, border_radius=10)

            # Name and timestamp
            self._draw_text(name, self.font_small, col, (bubble_rect.left + 12, bubble_rect.top + 4))
            self._draw_text(time_str, self.font_small, (110, 115, 130), (bubble_rect.right - 58, bubble_rect.top + 4))

            # Conforming message text
            self._draw_text(
                "Share it — it's already circulating everywhere.",
                self.font_small,
                (230, 235, 245),
                (bubble_rect.left + 12, bubble_rect.top + 23),
            )

            # Read receipts: double blue checkmarks (procedural lines)
            rcx = bubble_rect.right - 24
            rcy = bubble_rect.bottom - 13
            # First checkmark
            pygame.draw.line(self.screen, COLOR_ACCENT_CYAN, (rcx - 10, rcy), (rcx - 7, rcy + 4), 2)
            pygame.draw.line(self.screen, COLOR_ACCENT_CYAN, (rcx - 7, rcy + 4), (rcx - 2, rcy - 4), 2)
            # Second checkmark
            pygame.draw.line(self.screen, COLOR_ACCENT_CYAN, (rcx - 6, rcy), (rcx - 3, rcy + 4), 2)
            pygame.draw.line(self.screen, COLOR_ACCENT_CYAN, (rcx - 3, rcy + 4), (rcx + 2, rcy - 4), 2)

        # Typing Indicator or Outgoing Reply
        typing_y = bubble_y_start + 4 * (bubble_h + bubble_gap)
        if selected_index is None:
            type_rect = pygame.Rect(frame_x + 48, typing_y, 140, 28)
            pygame.draw.rect(self.screen, (25, 28, 38), type_rect, border_radius=10)
            pygame.draw.rect(self.screen, (38, 44, 60), type_rect, width=1, border_radius=10)
            ticks = pygame.time.get_ticks()
            for d in range(3):
                phase = (ticks / 200.0 + d * 0.8) % (2.0 * math.pi)
                dy = int(math.sin(phase) * 3)
                dot_x = type_rect.left + 22 + d * 14
                dot_y = type_rect.centery + dy
                pygame.draw.circle(self.screen, (150, 165, 195), (dot_x, dot_y), 3)
            self._draw_text("typing...", self.font_small, (120, 125, 140), (type_rect.left + 64, type_rect.top + 6))
        else:
            # Participant's sent message bubble (right-aligned, wrapped to avoid blowout)
            opt_text = scenario.options[selected_index].text if selected_index < len(scenario.options) else ""
            out_w = 370
            out_h = 56
            out_rect = pygame.Rect(frame_x + frame_w - out_w - 20, typing_y - 2, out_w, out_h)
            out_bg = (36, 70, 130) if selected_index == 0 else (110, 40, 50)
            pygame.draw.rect(self.screen, out_bg, out_rect, border_radius=10)
            text_rect = pygame.Rect(out_rect.left + 10, out_rect.top + 6, out_rect.width - 20, out_rect.height - 12)
            self._draw_wrapped_text(opt_text, self.font_small, (255, 255, 255), text_rect, spacing=2)

        # Quick-Reply Action Area at bottom of device
        action_y = frame_y + 406
        pygame.draw.line(self.screen, (35, 40, 55), (frame_x, action_y), (frame_x + frame_w, action_y), 1)
        self._draw_text(
            "QUICK REPLY (KEYS 1 – 2):",
            self.font_small,
            (130, 135, 150),
            (frame_x + frame_w // 2, action_y + 8),
            center=True,
        )

        chip_h = 82
        chip_gap = 10
        for i, opt in enumerate(scenario.options):
            cy = action_y + 26 + i * (chip_h + chip_gap)
            chip_rect = pygame.Rect(frame_x + 18, cy, frame_w - 36, chip_h)
            is_sel = (selected_index == i)

            if is_sel:
                bg = (40, 50, 75)
                border = COLOR_ACCENT_CYAN
                border_w = 2
            else:
                bg = (24, 28, 38)
                border = (50, 56, 74)
                border_w = 1

            pygame.draw.rect(self.screen, bg, chip_rect, border_radius=8)
            pygame.draw.rect(self.screen, border, chip_rect, width=border_w, border_radius=8)

            badge = pygame.Rect(chip_rect.left + 12, chip_rect.centery - 16, 32, 32)
            badge_bg = COLOR_ACCENT_INDIGO if not is_sel else COLOR_ACCENT_CYAN
            badge_fg = COLOR_TEXT_PRIMARY if not is_sel else (10, 12, 18)
            pygame.draw.rect(self.screen, badge_bg, badge, border_radius=6)
            self._draw_text(str(opt.key), self.font_title, badge_fg, badge.center, center=True)

            text_rect = pygame.Rect(badge.right + 12, chip_rect.top + 8, chip_rect.width - 135, chip_rect.height - 16)
            self._draw_wrapped_text(opt.text, self.font_small, COLOR_TEXT_PRIMARY, text_rect, spacing=3)

            tag_str = "[CONFORM]" if opt.is_conforming else "[DISSENT]"
            tag_col = COLOR_TIMER_AMBER if opt.is_conforming else COLOR_TIMER_RED
            self._draw_text(tag_str, self.font_small, tag_col, (chip_rect.right - 50, chip_rect.centery), center=True)

        # Phone bottom home bar indicator
        home_bar_y = frame_y + frame_h - 10
        pygame.draw.line(self.screen, (90, 95, 110), (frame_x + frame_w // 2 - 45, home_bar_y), (frame_x + frame_w // 2 + 45, home_bar_y), 3)

        return True

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
        pygame.draw.line(self.screen, (50, 54, 70), (60, header_y + 52), (self.width - 60, header_y + 52), 1)

        # 4 Project Columns / Module Cards
        modules = [
            ("Module A: Frontend UI", "STATUS: PASS", "Grade: A (94%)", COLOR_TIMER_GREEN, (24, 34, 30)),
            ("Module B: Data Pipeline", "STATUS: PASS", "Grade: A- (90%)", COLOR_TIMER_GREEN, (24, 34, 30)),
            ("Module C: Docs & QA", "STATUS: PASS", "Grade: B+ (88%)", COLOR_TIMER_GREEN, (24, 34, 30)),
            ("Core Integration", "STATUS: FAILED", "Grade: F (0%)", COLOR_TIMER_RED, (42, 20, 24)),
        ]
        card_w = (self.width - 120 - 3 * 14) // 4
        card_h = 76
        cards_y = 152 + jy

        for k, (mod_title, status_text, grade_text, badge_col, bg_col) in enumerate(modules):
            cx = 60 + jx + k * (card_w + 14)
            card_rect = pygame.Rect(cx, cards_y, card_w, card_h)

            border_col = COLOR_TIMER_RED if k == 3 else (45, 50, 68)
            border_width = 2 if k == 3 else 1
            pygame.draw.rect(self.screen, bg_col, card_rect, border_radius=6)
            pygame.draw.rect(self.screen, border_col, card_rect, width=border_width, border_radius=6)

            self._draw_text(mod_title, self.font_body, COLOR_TEXT_PRIMARY, (card_rect.left + 12, card_rect.top + 10))
            self._draw_text(status_text, self.font_small, badge_col, (card_rect.left + 12, card_rect.top + 34))
            self._draw_text(grade_text, self.font_small, (140, 145, 160), (card_rect.left + 12, card_rect.top + 52))

            if k == 3:
                # Warning badge on failed core module
                tag_rect = pygame.Rect(card_rect.right - 70, card_rect.top + 8, 62, 20)
                pygame.draw.rect(self.screen, COLOR_TIMER_RED, tag_rect, border_radius=3)
                self._draw_text("FAILED", self.font_small, (255, 255, 255), tag_rect.center, center=True)

        # Peer Review Submissions (Unanimous Blame Attribution)
        peer_section_y = 238 + jy
        self._draw_text(
            "PEER REVIEW ASSESSMENTS (4 / 4 COMPLETED — UNANIMOUS ATTRIBUTION RECORDED):",
            self.font_small,
            (180, 185, 200),
            (60 + jx, peer_section_y),
        )

        teammates = [
            ("Alex (Lead)", "A", (38, 112, 210), "Core integration module not delivered on time."),
            ("Brandon", "B", (128, 64, 168), "All other modules ready; bottleneck was in core."),
            ("Chloe", "C", (38, 148, 132), "Core module team assigned owner failed to merge."),
            ("Danielle", "D", (205, 102, 38), "System integration broke downstream testing."),
        ]
        peer_card_w = card_w
        peer_card_h = 100
        peer_cards_y = peer_section_y + 20

        for k, (tname, tinit, tcol, comment) in enumerate(teammates):
            tx = 60 + jx + k * (peer_card_w + 14)
            trect = pygame.Rect(tx, peer_cards_y, peer_card_w, peer_card_h)

            pygame.draw.rect(self.screen, (22, 25, 36), trect, border_radius=6)
            pygame.draw.rect(self.screen, (50, 55, 75), trect, width=1, border_radius=6)

            # Avatar
            avatar_cx = trect.left + 22
            avatar_cy = trect.top + 20
            pygame.draw.circle(self.screen, tcol, (avatar_cx, avatar_cy), 12)
            self._draw_text(tinit, self.font_small, (255, 255, 255), (avatar_cx, avatar_cy), center=True)

            self._draw_text(tname, self.font_small, COLOR_TEXT_PRIMARY, (avatar_cx + 18, trect.top + 10))

            # Comment wrapped
            comment_rect = pygame.Rect(trect.left + 10, trect.top + 34, trect.width - 20, 36)
            self._draw_wrapped_text(comment, self.font_small, (140, 145, 160), comment_rect, spacing=2)

            # Explicit Blame Attribution Tag
            tag_box = pygame.Rect(trect.left + 8, trect.bottom - 24, trect.width - 16, 18)
            pygame.draw.rect(self.screen, (55, 18, 24), tag_box, border_radius=3)
            pygame.draw.rect(self.screen, COLOR_TIMER_RED, tag_box, width=1, border_radius=3)
            self._draw_text("Failure Attribution: YOU", self.font_mono_small, (255, 110, 110), tag_box.center, center=True)

        # Participant Action Panel (Foreground)
        panel_y = 372 + jy
        panel_h = 330
        panel_rect = pygame.Rect(60 + jx, panel_y, self.width - 120, panel_h)
        self._draw_card(panel_rect, (55, 60, 80), bg_color=(20, 22, 30))

        # Action Panel Header
        top_bar = pygame.Rect(panel_rect.left, panel_rect.top, panel_rect.width, 34)
        pygame.draw.rect(self.screen, (28, 32, 45), top_bar, border_top_left_radius=8, border_top_right_radius=8)
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
        tag_labels = ["[CONFORM / ACCEPT]", "[CONTEST / COUNTER]", "[REFUSE TO ASSIGN]"]
        tag_colors = [COLOR_TIMER_AMBER, COLOR_TIMER_RED, COLOR_ACCENT_CYAN]

        for i, opt in enumerate(scenario.options):
            oy = opt_start_y + i * (opt_card_h + opt_gap)
            orect = pygame.Rect(panel_rect.left + 20, oy, panel_rect.width - 40, opt_card_h)
            is_sel = (selected_index == i)

            border = COLOR_ACCENT_CYAN if is_sel else ((65, 70, 92) if selected_index is not None else (45, 48, 64))
            bg = (38, 45, 65) if is_sel else (25, 28, 38)
            self._draw_card(orect, border, bg_color=bg)

            badge = pygame.Rect(orect.left + 14, orect.centery - 18, 36, 36)
            badge_bg = COLOR_ACCENT_INDIGO if not is_sel else COLOR_ACCENT_CYAN
            badge_fg = COLOR_TEXT_PRIMARY if not is_sel else (10, 12, 18)
            pygame.draw.rect(self.screen, badge_bg, badge, border_radius=6)
            self._draw_text(str(opt.key), self.font_title, badge_fg, badge.center, center=True)

            text_rect = pygame.Rect(badge.right + 18, orect.top + 8, orect.width - 180, orect.height - 16)
            self._draw_wrapped_text(opt.text, self.font_body, COLOR_TEXT_PRIMARY, text_rect, spacing=3, center_v=True)

            tag_label = tag_labels[i] if i < len(tag_labels) else ""
            tag_color = tag_colors[i] if i < len(tag_colors) else COLOR_TEXT_SECONDARY
            self._draw_text(tag_label, self.font_small, tag_color, (orect.right - 90, orect.centery), center=True)

        self._draw_text(
            "PRESS KEY [1], [2], OR [3] TO SUBMIT RESPONSE. YOUR RECORD WILL BE ENTERED IN THE COURSE AUDIT LOG.",
            self.font_small,
            (120, 125, 140),
            (panel_rect.centerx, panel_rect.bottom - 16),
            center=True,
        )

        return True


    def _draw_skin_reward_crate(
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
        """Render reward_crate simulation skin: digital reward chest, dynamic scaling/glow, instability gauge, and radial shatter."""
        if reward_runner is None:
            return False

        vx, vy = effects.vibration_offset
        jx, jy = effects.jitter_offset
        ox = vx + jx
        oy = vy + jy

        current_val = reward_runner.get_current_value()
        instability = reward_runner.get_instability_fraction()
        is_collapsed = reward_runner.is_collapsed or reward_runner.has_collapsed()

        # Background vault chamber framing
        header_rect = pygame.Rect(50, 95, self.width - 100, 32)
        self._draw_text("CHAMBER: VAULT-03 // DIGITAL MARSHMALLOW PARADIGM", self.font_small, (130, 140, 165), (header_rect.left + 14, header_rect.centery), midleft=True)
        self._draw_text("EXPONENTIAL VALUE MULTIPLIER", self.font_small, COLOR_ACCENT_CYAN, (header_rect.right - 14, header_rect.centery), midright=True)
        pygame.draw.line(self.screen, (35, 40, 58), (50, 130), (self.width - 50, 130), 1)

        # Ambient floor horizon line and perspective guide
        pygame.draw.line(self.screen, (28, 32, 46), (0, 430), (self.width, 430), 1)

        # 1. Left Wall: Vertical Stability Gauge (positioned cleanly below chamber line y=130)
        card_w = 130
        card_left = 50 + ox
        card_top = 146 + oy
        card_h = 334
        gauge_card = pygame.Rect(card_left, card_top, card_w, card_h)
        self._draw_card(gauge_card, border_color=(45, 50, 72), bg_color=(16, 18, 26))
        self._draw_text("CORE STABILITY", self.font_small, COLOR_TEXT_SECONDARY, (gauge_card.centerx, card_top + 18), center=True)

        # Gauge track centered in card
        gw = 36
        gh = 210
        gx = gauge_card.centerx - gw // 2
        gy = card_top + 38
        stability_frac = max(0.0, min(1.0, 1.0 - instability))

        pygame.draw.rect(self.screen, (22, 25, 36), (gx, gy, gw, gh), border_radius=4)
        pygame.draw.rect(self.screen, (48, 54, 76), (gx, gy, gw, gh), width=2, border_radius=4)

        # Meter fill
        if stability_frac > 0.6:
            meter_col = COLOR_TIMER_GREEN
        elif stability_frac > 0.3:
            meter_col = COLOR_TIMER_AMBER
        else:
            meter_col = COLOR_TIMER_RED

        fill_h = int(gh * stability_frac)
        if fill_h > 4:
            fill_rect = pygame.Rect(gx + 2, gy + gh - fill_h + 2, gw - 4, fill_h - 4)
            pygame.draw.rect(self.screen, meter_col, fill_rect, border_radius=2)

        # Tick marks
        for tick_idx in range(1, 5):
            ty = gy + int(gh * (tick_idx / 5.0))
            pygame.draw.line(self.screen, (55, 62, 85), (gx + 3, ty), (gx + gw - 3, ty), 1)

        # Cracks on gauge frame when instability increases
        if instability > 0.35:
            crack_pts1 = [(gx - 3, gy + 55), (gx + 12, gy + 72), (gx + 7, gy + 88), (gx + 25, gy + 102)]
            pygame.draw.lines(self.screen, (255, 90, 90), False, crack_pts1, 2)
        if instability > 0.65:
            crack_pts2 = [(gx + gw + 3, gy + 135), (gx + 18, gy + 152), (gx + 22, gy + 168), (gx + 6, gy + 182)]
            pygame.draw.lines(self.screen, (255, 60, 60), False, crack_pts2, 2)

        pct_text = f"{int(stability_frac * 100)}%"
        self._draw_text(pct_text, self.font_body, meter_col, (gauge_card.centerx, gy + gh + 16), center=True)

        status_lbl = "CRITICAL" if instability > 0.75 else ("UNSTABLE" if instability > 0.4 else "SECURE")
        status_col = COLOR_TIMER_RED if instability > 0.75 else (COLOR_TIMER_AMBER if instability > 0.4 else COLOR_TIMER_GREEN)
        self._draw_text(status_lbl, self.font_small, status_col, (gauge_card.centerx, gy + gh + 38), center=True)

        # 2. Central Futuristic Supply Chest
        cx = self.width // 2 + ox
        cy = 348 + oy

        # Accent Glow transition: COLOR_ACCENT_CYAN (0, 229, 255) -> COLOR_TIMER_AMBER (255, 179, 0)
        if instability < 0.8:
            ratio = instability / 0.8
            glow_r = int(COLOR_ACCENT_CYAN[0] + (COLOR_TIMER_AMBER[0] - COLOR_ACCENT_CYAN[0]) * ratio)
            glow_g = int(COLOR_ACCENT_CYAN[1] + (COLOR_TIMER_AMBER[1] - COLOR_ACCENT_CYAN[1]) * ratio)
            glow_b = int(COLOR_ACCENT_CYAN[2] + (COLOR_TIMER_AMBER[2] - COLOR_ACCENT_CYAN[2]) * ratio)
        else:
            ratio = (instability - 0.8) / 0.2
            glow_r = int(COLOR_TIMER_AMBER[0] + (255 - COLOR_TIMER_AMBER[0]) * ratio)
            glow_g = int(COLOR_TIMER_AMBER[1] + (70 - COLOR_TIMER_AMBER[1]) * ratio)
            glow_b = int(COLOR_TIMER_AMBER[2] + (70 - COLOR_TIMER_AMBER[2]) * ratio)
        glow_color = (glow_r, glow_g, glow_b)

        # Dynamic Scaling & Pulse
        base_w = 320
        base_h = 190
        scale = 1.0 + 0.15 * min(1.0, current_val / 600.0) + 0.02 * math.sin(time_remaining_s * 5.0)
        if is_collapsed:
            scale = 0.92

        cw = int(base_w * scale)
        ch = int(base_h * scale)
        chest_rect = pygame.Rect(cx - cw // 2, cy - ch // 2, cw, ch)

        if not is_collapsed:
            # Drop shadow
            shadow_rect = pygame.Rect(cx - cw // 2 - 15, chest_rect.bottom - 8, cw + 30, 24)
            pygame.draw.ellipse(self.screen, (12, 14, 20), shadow_rect)

            # Outer glow aura
            aura_rect = chest_rect.inflate(16, 16)
            aura_color = (max(0, glow_r // 6), max(0, glow_g // 6), max(0, glow_b // 6))
            pygame.draw.rect(self.screen, aura_color, aura_rect, border_radius=12)

            # Chest chassis
            pygame.draw.rect(self.screen, (26, 30, 44), chest_rect, border_radius=10)
            pygame.draw.rect(self.screen, (46, 54, 78), chest_rect, width=3, border_radius=10)

            # Corner reinforcement plates
            c_size = int(22 * scale)
            for c_x, c_y in [
                (chest_rect.left, chest_rect.top),
                (chest_rect.right - c_size, chest_rect.top),
                (chest_rect.left, chest_rect.bottom - c_size),
                (chest_rect.right - c_size, chest_rect.bottom - c_size),
            ]:
                pygame.draw.rect(self.screen, (38, 44, 64), (c_x, c_y, c_size, c_size), border_radius=3)
                pygame.draw.rect(self.screen, (58, 66, 94), (c_x, c_y, c_size, c_size), width=1, border_radius=3)
                pygame.draw.circle(self.screen, (80, 90, 120), (c_x + c_size // 2, c_y + c_size // 2), 2)

            # Lid (upper 36%)
            lid_h = int(ch * 0.36)
            lid_rect = pygame.Rect(chest_rect.left, chest_rect.top, cw, lid_h)
            pygame.draw.rect(self.screen, (34, 39, 58), lid_rect, border_top_left_radius=10, border_top_right_radius=10)
            pygame.draw.rect(self.screen, (60, 70, 98), lid_rect, width=2, border_top_left_radius=10, border_top_right_radius=10)

            # Dividing seam line
            seam_y = chest_rect.top + lid_h
            pygame.draw.line(self.screen, (14, 16, 24), (chest_rect.left + 4, seam_y), (chest_rect.right - 4, seam_y), 4)
            pygame.draw.line(self.screen, glow_color, (chest_rect.left + 24, seam_y), (chest_rect.right - 24, seam_y), 2)

            # Central energy lock core
            lock_w = int(64 * scale)
            lock_h = int(46 * scale)
            lock_rect = pygame.Rect(cx - lock_w // 2, seam_y - lock_h // 2, lock_w, lock_h)
            pygame.draw.rect(self.screen, (18, 20, 30), lock_rect, border_radius=6)
            pygame.draw.rect(self.screen, glow_color, lock_rect, width=2, border_radius=6)

            core_r = max(4, int(10 * scale + math.sin(time_remaining_s * 6.0) * 2.5))
            pygame.draw.circle(self.screen, glow_color, lock_rect.center, core_r)
            pygame.draw.circle(self.screen, (255, 255, 255), lock_rect.center, max(2, core_r - 4))

            # Vertical energy cooling vents on lower chassis
            for vent_x in (cx - 85, cx - 42, cx + 42, cx + 85):
                pygame.draw.line(self.screen, (16, 18, 26), (vent_x, seam_y + 24), (vent_x, chest_rect.bottom - 18), 4)
                pygame.draw.line(self.screen, glow_color, (vent_x, seam_y + 26), (vent_x, chest_rect.bottom - 20), 1)

            # Procedural jagged crack lines over chest surface as instability increases
            if instability > 0.20:
                c1 = [(cx - 25, seam_y - 8), (cx - 50, seam_y - 32), (cx - 78, seam_y - 22), (cx - 110, seam_y - 48)]
                pygame.draw.lines(self.screen, glow_color, False, c1, 2)
            if instability > 0.45:
                c2 = [(cx + 28, seam_y + 10), (cx + 56, seam_y + 36), (cx + 80, seam_y + 24), (cx + 115, seam_y + 55)]
                pygame.draw.lines(self.screen, glow_color, False, c2, 2)
            if instability > 0.70:
                c3 = [(cx - 18, seam_y + 16), (cx - 42, seam_y + 46), (cx - 32, seam_y + 68), (cx - 68, seam_y + 82)]
                pygame.draw.lines(self.screen, (255, 75, 75), False, c3, 3)
            if instability > 0.85:
                c4 = [(cx + 20, seam_y - 10), (cx + 48, seam_y - 42), (cx + 82, seam_y - 32), (cx + 122, seam_y - 52)]
                pygame.draw.lines(self.screen, (255, 75, 75), False, c4, 3)

        else:
            # Shattered / collapsed chest graphic
            pygame.draw.rect(self.screen, (20, 22, 30), chest_rect, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_TIMER_RED, chest_rect, width=2, border_radius=6)
            pygame.draw.line(self.screen, COLOR_TIMER_RED, chest_rect.topleft, chest_rect.bottomright, 3)
            pygame.draw.line(self.screen, COLOR_TIMER_RED, chest_rect.topright, chest_rect.bottomleft, 3)
            self._draw_text("CHEST COLLAPSED", self.font_hero, COLOR_TIMER_RED, (cx, cy - 10), center=True)
            self._draw_text("ALL ACCUMULATED VALUE LOST", self.font_body, (220, 80, 80), (cx, cy + 30), center=True)

        # 3. Multiplier Counter Floating Above Chest
        counter_h = 72
        counter_top = 152 + oy
        counter_card = pygame.Rect(cx - 160, counter_top, 320, counter_h)
        self._draw_card(counter_card, border_color=glow_color, bg_color=(20, 24, 38))
        self._draw_text("ACCUMULATED MULTIPLIER", self.font_small, (150, 160, 185), (cx, counter_top + 16), center=True)
        val_str = f"x{current_val}" if not is_collapsed else "0"
        self._draw_text(val_str, self.font_hero, glow_color, (cx, counter_top + 46), center=True)

        # 4. Collapse Shatter Effect Trigger & Rendering
        if is_collapsed:
            if not self.shatter_effect.is_active and not self.shatter_effect.particles:
                self.shatter_effect.trigger((cx, cy))
        else:
            if not self.shatter_effect.is_active and self.shatter_effect.particles:
                self.shatter_effect.particles = []

        if self.shatter_effect.is_active:
            self.shatter_effect.update(16)
            self.shatter_effect.draw(self.screen)

        # 5. Persistent Action Cards at Bottom
        card_y = self.height - 105 + oy
        card_h = 76
        card_w = 400

        # Option 1: CLAIM NOW
        r1 = pygame.Rect(self.width // 2 - card_w - 20 + ox, card_y, card_w, card_h)
        is_sel1 = (selected_index == 0)
        b1 = COLOR_TIMER_GREEN if is_sel1 else ((0, 180, 100) if selected_index is None else (50, 58, 72))
        bg1 = (28, 48, 40) if is_sel1 else COLOR_CARD_BG
        self._draw_card(r1, border_color=b1, bg_color=bg1)

        k1 = pygame.Rect(r1.left + 16, r1.centery - 18, 36, 36)
        pygame.draw.rect(self.screen, (0, 180, 100), k1, border_radius=6)
        self._draw_text("1", self.font_title, COLOR_TEXT_PRIMARY, k1.center, center=True)

        self._draw_text("CLAIM NOW", self.font_title, COLOR_TIMER_GREEN if is_sel1 else COLOR_TEXT_PRIMARY, (k1.right + 18, r1.top + 14))
        self._draw_text(f"Secure {current_val} units immediately", self.font_small, COLOR_TEXT_SECONDARY, (k1.right + 18, r1.top + 42))

        # Option 2: KEEP WAITING
        r2 = pygame.Rect(self.width // 2 + 20 + ox, card_y, card_w, card_h)
        is_sel2 = (selected_index == 1)
        b2 = COLOR_TIMER_AMBER if is_sel2 else ((180, 130, 0) if selected_index is None else (50, 58, 72))
        bg2 = (48, 42, 28) if is_sel2 else COLOR_CARD_BG
        self._draw_card(r2, border_color=b2, bg_color=bg2)

        k2 = pygame.Rect(r2.left + 16, r2.centery - 18, 36, 36)
        pygame.draw.rect(self.screen, (180, 130, 0), k2, border_radius=6)
        self._draw_text("2", self.font_title, COLOR_TEXT_PRIMARY, k2.center, center=True)

        self._draw_text("KEEP WAITING", self.font_title, COLOR_TIMER_AMBER if is_sel2 else COLOR_TEXT_PRIMARY, (k2.right + 18, r2.top + 14))
        self._draw_text("Multiply value (Sudden collapse risk)", self.font_small, COLOR_TEXT_SECONDARY, (k2.right + 18, r2.top + 42))

        return True

    def _draw_skin_document_workspace(
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
        """Render document_workspace simulation skin: assignment editor, simulated text lines, word count, decision cards."""
        vx, vy = effects.vibration_offset
        jx, jy = effects.jitter_offset
        ox = vx + jx
        oy = vy + jy

        # 1. Main Document Editor Window
        win_w = 920
        win_h = 425
        win_rect = pygame.Rect(self.width // 2 - win_w // 2 + ox, 90 + oy, win_w, win_h)

        # Window Frame Background & Border
        pygame.draw.rect(self.screen, (18, 20, 28), win_rect, border_radius=8)
        pygame.draw.rect(self.screen, (48, 54, 76), win_rect, width=2, border_radius=8)

        # Window Title Bar (Header)
        hdr_h = 36
        hdr_rect = pygame.Rect(win_rect.left, win_rect.top, win_w, hdr_h)
        pygame.draw.rect(self.screen, (26, 30, 44), hdr_rect, border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.line(self.screen, (44, 50, 70), (win_rect.left, hdr_rect.bottom), (win_rect.right, hdr_rect.bottom), 1)

        # Window Controls (macOS / modern desktop style dots)
        dots = [
            ((win_rect.left + 20, hdr_rect.centery), (255, 95, 87)),
            ((win_rect.left + 36, hdr_rect.centery), (254, 188, 46)),
            ((win_rect.left + 52, hdr_rect.centery), (40, 201, 64)),
        ]
        for center, color in dots:
            pygame.draw.circle(self.screen, color, center, 5)

        # Document Title in header
        self._draw_text(
            "Term_Paper_Final_Draft_v4.docx — Assignment Editor",
            self.font_small,
            COLOR_TEXT_PRIMARY,
            (win_rect.centerx, hdr_rect.centery),
            center=True,
        )
        self._draw_text("[Auto-Saved]", self.font_small, (110, 125, 145), (win_rect.right - 20, hdr_rect.centery), midright=True)

        # Menu / Formatting Ribbon
        ribbon_rect = pygame.Rect(win_rect.left, hdr_rect.bottom, win_w, 28)
        pygame.draw.rect(self.screen, (22, 25, 36), ribbon_rect)
        pygame.draw.line(self.screen, (40, 45, 62), (win_rect.left, ribbon_rect.bottom), (win_rect.right, ribbon_rect.bottom), 1)
        self._draw_text(
            "File    Edit    View    Insert    Format    Tools    Extensions    Help",
            self.font_small,
            (125, 135, 155),
            (win_rect.left + 24, ribbon_rect.centery),
            midleft=True,
        )

        # 2. Document Page Surface (Canvas)
        canvas_rect = pygame.Rect(win_rect.left + 24, ribbon_rect.bottom + 12, win_w - 48, win_h - 115)
        pygame.draw.rect(self.screen, (240, 242, 246), canvas_rect, border_radius=4)
        pygame.draw.rect(self.screen, (200, 205, 218), canvas_rect, width=1, border_radius=4)

        # Margins inside document
        margin_x = canvas_rect.left + 45
        margin_w = canvas_rect.width - 90

        # Document Header / Assignment Title
        self._draw_text(
            "An Empirical Investigation of Delayed Rewards & Cognitive Self-Regulation",
            self.font_body,
            (28, 32, 45),
            (margin_x, canvas_rect.top + 16),
        )
        self._draw_text(
            "Course: Behavioral Neuroscience (PSYC-340)  |  Draft Revision: 4.2",
            self.font_small,
            (95, 105, 120),
            (margin_x, canvas_rect.top + 40),
        )
        pygame.draw.line(self.screen, (205, 210, 222), (margin_x, canvas_rect.top + 58), (canvas_rect.right - 45, canvas_rect.top + 58), 1)

        # Simulated Text Lines (horizontal gray bars)
        p1_lines = [
            (0, 1.0),
            (14, 0.96),
            (28, 0.98),
            (42, 0.72),
        ]
        base_y1 = canvas_rect.top + 70
        for dy, frac in p1_lines:
            pygame.draw.rect(
                self.screen,
                (185, 190, 202),
                (margin_x, base_y1 + dy, int(margin_w * frac), 7),
                border_radius=2,
            )

        # Paragraph 2 with revision highlight
        base_y2 = base_y1 + 68
        pygame.draw.rect(
            self.screen,
            (255, 238, 185),
            (margin_x - 4, base_y2 - 3, int(margin_w * 0.70), 38),
            border_radius=3,
        )
        p2_lines = [
            (0, 0.68),
            (14, 0.65),
            (28, 0.50),
        ]
        for dy, frac in p2_lines:
            pygame.draw.rect(
                self.screen,
                (150, 155, 170),
                (margin_x, base_y2 + dy, int(margin_w * frac), 7),
                border_radius=2,
            )

        # Revision tag bubble in right margin (safely anchored inside canvas right border)
        rev_tag_rect = pygame.Rect(canvas_rect.right - 185, base_y2 + 2, 170, 26)
        pygame.draw.rect(self.screen, (255, 245, 210), rev_tag_rect, border_radius=4)
        pygame.draw.rect(self.screen, (210, 160, 50), rev_tag_rect, width=1, border_radius=4)
        self._draw_text("[Unsaved Edits: Rev 4.2]", self.font_small, (150, 100, 20), rev_tag_rect.center, center=True)

        # Paragraph 3
        base_y3 = base_y2 + 50
        p3_lines = [
            (0, 0.97),
            (14, 0.88),
            (28, 0.40),
        ]
        for dy, frac in p3_lines:
            pygame.draw.rect(
                self.screen,
                (185, 190, 202),
                (margin_x, base_y3 + dy, int(margin_w * frac), 7),
                border_radius=2,
            )

        # 3. Document Editor Bottom Status Bar
        status_h = 30
        status_rect = pygame.Rect(win_rect.left, win_rect.bottom - status_h, win_w, status_h)
        pygame.draw.rect(self.screen, (22, 25, 36), status_rect, border_bottom_left_radius=8, border_bottom_right_radius=8)
        pygame.draw.line(self.screen, (40, 45, 62), (win_rect.left, status_rect.top), (win_rect.right, status_rect.top), 1)

        self._draw_text(
            "Words: 3,420    |    Characters: 21,850    |    Page 6 of 6",
            self.font_small,
            (140, 150, 170),
            (status_rect.left + 24, status_rect.centery),
            midleft=True,
        )
        self._draw_text(
            "Status: Draft Quality 'Adequate' (Grade B+)    |    [OK] Citations Checked",
            self.font_small,
            COLOR_ACCENT_CYAN,
            (status_rect.right - 24, status_rect.centery),
            midright=True,
        )

        # 4. Decision Split: Option 1 vs Option 2
        card_y = self.height - 110 + oy
        card_h = 86
        card_w = 460

        opts = scenario.options
        for i in range(min(2, len(opts))):
            opt = opts[i]
            rx = self.width // 2 - card_w - 15 + ox if i == 0 else self.width // 2 + 15 + ox
            r = pygame.Rect(rx, card_y, card_w, card_h)
            is_sel = (selected_index == i)

            if i == 0:
                border_col = COLOR_TIMER_GREEN if is_sel else ((0, 180, 120) if selected_index is None else (50, 56, 72))
                bg_col = (24, 46, 38) if is_sel else COLOR_CARD_BG
                key_bg = (0, 180, 120)
                tag_label = "SUBMIT NOW (GUARANTEED ADEQUATE)"
                tag_col = COLOR_TIMER_GREEN
            else:
                border_col = COLOR_TIMER_AMBER if is_sel else ((190, 120, 20) if selected_index is None else (50, 56, 72))
                bg_col = (48, 38, 24) if is_sel else COLOR_CARD_BG
                key_bg = (190, 120, 20)
                tag_label = "REQUEST EXTENDED REVIEW (HIGH RISK)"
                tag_col = COLOR_TIMER_AMBER

            self._draw_card(r, border_color=border_col, bg_color=bg_col)

            k_badge = pygame.Rect(r.left + 14, r.centery - 18, 36, 36)
            pygame.draw.rect(self.screen, key_bg, k_badge, border_radius=6)
            self._draw_text(str(opt.key), self.font_title, COLOR_TEXT_PRIMARY, k_badge.center, center=True)

            self._draw_text(tag_label, self.font_small, tag_col if is_sel else (180, 190, 210), (k_badge.right + 14, r.top + 10))
            text_rect = pygame.Rect(k_badge.right + 14, r.top + 32, r.width - 85, r.height - 38)
            self._draw_wrapped_text(opt.text, self.font_body, COLOR_TEXT_PRIMARY, text_rect, spacing=2, center_v=True)

        return True

    def _draw_skin_tournament_bracket(
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
        """Render tournament_bracket simulation skin: tactical tournament dashboard, 3 strategy cards, incomplete info manipulation."""
        vx, vy = effects.vibration_offset
        jx, jy = effects.jitter_offset
        ox = vx + jx
        oy = vy + jy

        # 1 Hz gentle pulse for anticipatory somatic tension
        pulse_1hz = (math.sin(time_remaining_s * 2.0 * math.pi) + 1.0) / 2.0

        # 1. Header: Tactical tournament telemetry bar
        header_rect = pygame.Rect(50 + ox, 90 + oy, self.width - 100, 48)
        self._draw_card(header_rect, border_color=(50, 60, 85), bg_color=(18, 22, 34))

        self._draw_text(
            "CURRENT DIVISION STANDING: TIER 1 BRACKET",
            self.font_title,
            COLOR_ACCENT_CYAN,
            (header_rect.left + 24, header_rect.centery),
            midleft=True,
        )

        # Telemetry badges in header
        self._draw_text("SEASON PLAYOFFS // MATCH 1 OF 1", self.font_small, (140, 150, 175), (header_rect.right - 260, header_rect.centery), midright=True)
        self._draw_text("[DECISION TIME CRITICAL]", self.font_small, COLOR_TIMER_AMBER, (header_rect.right - 24, header_rect.centery), midright=True)

        # 2. Three Strategy Cards Side-by-Side
        cw = 370
        ch = 475
        gap = 25
        total_w = 3 * cw + 2 * gap
        start_x = (self.width - total_w) // 2 + ox
        card_y = 150 + oy

        # -------------------------------------------------------------
        # Card 1: Strategy Alpha (Safe Approach)
        # -------------------------------------------------------------
        c1_rect = pygame.Rect(start_x, card_y, cw, ch)
        is_sel1 = (selected_index == 0)
        border1 = COLOR_TIMER_GREEN if is_sel1 else ((0, 180, 120) if selected_index is None else (45, 55, 75))
        bg1 = (22, 38, 32) if is_sel1 else (20, 24, 36)
        self._draw_card(c1_rect, border_color=border1, bg_color=bg1)

        # Card header badge
        k1_badge = pygame.Rect(c1_rect.left + 16, c1_rect.top + 16, 36, 36)
        pygame.draw.rect(self.screen, (0, 180, 120), k1_badge, border_radius=6)
        self._draw_text("1", self.font_title, COLOR_TEXT_PRIMARY, k1_badge.center, center=True)

        self._draw_text("Strategy Alpha", self.font_body, COLOR_TIMER_GREEN if is_sel1 else COLOR_TEXT_PRIMARY, (k1_badge.right + 14, c1_rect.top + 12))
        self._draw_text("CONSERVATIVE PROTOCOL", self.font_small, COLOR_TIMER_GREEN, (k1_badge.right + 14, c1_rect.top + 38))

        # Projected score box
        box1 = pygame.Rect(c1_rect.left + 16, c1_rect.top + 68, cw - 32, 64)
        pygame.draw.rect(self.screen, (16, 26, 26), box1, border_radius=6)
        pygame.draw.rect(self.screen, (0, 160, 100), box1, width=1, border_radius=6)
        self._draw_text("+8% AVG", self.font_hero, COLOR_TIMER_GREEN, (box1.centerx, box1.top + 22), center=True)
        self._draw_text("Projected Round Gain", self.font_small, (140, 160, 160), (box1.centerx, box1.top + 48), center=True)

        # Variance metric
        self._draw_text("Variance: LOW (σ = ±1.5%)", self.font_small, (160, 175, 195), (c1_rect.left + 16, c1_rect.top + 144))
        var_bar1 = pygame.Rect(c1_rect.left + 16, c1_rect.top + 164, cw - 32, 8)
        pygame.draw.rect(self.screen, (28, 34, 48), var_bar1, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_TIMER_GREEN, (var_bar1.left, var_bar1.top, int(var_bar1.width * 0.92), var_bar1.height), border_radius=4)

        # Historical Telemetry Bars (6/6 complete & verified)
        self._draw_text("HISTORICAL TELEMETRY (6 ROUNDS)", self.font_small, (140, 150, 170), (c1_rect.left + 16, c1_rect.top + 184))
        chart_w = (cw - 32)
        bar_w = (chart_w - 5 * 8) // 6
        chart_base_y = c1_rect.top + 285
        r1_vals = [8, 9, 7, 8, 9, 8]
        for idx, val in enumerate(r1_vals):
            bx = c1_rect.left + 16 + idx * (bar_w + 8)
            bh = int(val * 4.5)
            by = chart_base_y - bh
            pygame.draw.rect(self.screen, (0, 190, 120), (bx, by, bar_w, bh), border_radius=3)
            self._draw_text(f"R{idx+1}", self.font_small, (120, 135, 145), (bx + bar_w // 2, chart_base_y + 10), center=True)

        # Verified audit tag
        audit_tag = pygame.Rect(c1_rect.left + 16, c1_rect.top + 325, cw - 32, 38)
        pygame.draw.rect(self.screen, (18, 38, 30), audit_tag, border_radius=6)
        pygame.draw.rect(self.screen, (0, 180, 100), audit_tag, width=1, border_radius=6)
        self._draw_text("[OK] 6/6 ROUNDS AUDITED & VERIFIED", self.font_small, COLOR_TIMER_GREEN, audit_tag.center, center=True)

        # Risk rating & description
        self._draw_text("Risk Profile: 1 / 10 (Predictable)", self.font_small, (150, 160, 180), (c1_rect.left + 16, c1_rect.top + 380))
        desc1_rect = pygame.Rect(c1_rect.left + 16, c1_rect.top + 404, cw - 32, 45)
        self._draw_wrapped_text("Guaranteed score gain. Zero downside exposure.", self.font_small, COLOR_TEXT_SECONDARY, desc1_rect, spacing=2)

        # -------------------------------------------------------------
        # Card 2: Strategy Beta (Aggressive Approach, 2 rounds missing)
        # -------------------------------------------------------------
        c2_rect = pygame.Rect(start_x + cw + gap, card_y, cw, ch)
        is_sel2 = (selected_index == 1)
        border2 = COLOR_TIMER_AMBER if is_sel2 else ((180, 130, 0) if selected_index is None else (45, 55, 75))
        bg2 = (38, 32, 22) if is_sel2 else (20, 24, 36)
        self._draw_card(c2_rect, border_color=border2, bg_color=bg2)

        k2_badge = pygame.Rect(c2_rect.left + 16, c2_rect.top + 16, 36, 36)
        pygame.draw.rect(self.screen, (220, 140, 0), k2_badge, border_radius=6)
        self._draw_text("2", self.font_title, COLOR_TEXT_PRIMARY, k2_badge.center, center=True)

        self._draw_text("Strategy Beta", self.font_body, COLOR_TIMER_AMBER if is_sel2 else COLOR_TEXT_PRIMARY, (k2_badge.right + 14, c2_rect.top + 12))
        self._draw_text("AGGRESSIVE PROTOCOL", self.font_small, COLOR_TIMER_AMBER, (k2_badge.right + 14, c2_rect.top + 38))

        # Projected score box
        box2 = pygame.Rect(c2_rect.left + 16, c2_rect.top + 68, cw - 32, 64)
        pygame.draw.rect(self.screen, (32, 26, 16), box2, border_radius=6)
        pygame.draw.rect(self.screen, (180, 120, 0), box2, width=1, border_radius=6)
        self._draw_text("+22% AVG", self.font_hero, COLOR_TIMER_AMBER, (box2.centerx, box2.top + 22), center=True)
        self._draw_text("Projected Round Gain", self.font_small, (180, 160, 140), (box2.centerx, box2.top + 48), center=True)

        # Variance metric
        self._draw_text("Variance: HIGH (σ = ±14.2%)", self.font_small, (160, 175, 195), (c2_rect.left + 16, c2_rect.top + 144))
        var_bar2 = pygame.Rect(c2_rect.left + 16, c2_rect.top + 164, cw - 32, 8)
        pygame.draw.rect(self.screen, (28, 34, 48), var_bar2, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_TIMER_AMBER, (var_bar2.left, var_bar2.top, int(var_bar2.width * 0.52), var_bar2.height), border_radius=4)

        # Historical Telemetry Bars (4 verified, 2 missing/untracked)
        self._draw_text("HISTORICAL TELEMETRY (4/6 ROUNDS)", self.font_small, (140, 150, 170), (c2_rect.left + 16, c2_rect.top + 184))
        r2_vals = [18, 26, 20, 24]
        for idx in range(6):
            bx = c2_rect.left + 16 + idx * (bar_w + 8)
            if idx < 4:
                bh = int(r2_vals[idx] * 2.2)
                by = chart_base_y - bh
                pygame.draw.rect(self.screen, (220, 150, 20), (bx, by, bar_w, bh), border_radius=3)
            else:
                # Corrupted / Missing bar with hatched border
                pygame.draw.rect(self.screen, (35, 28, 20), (bx, chart_base_y - 45, bar_w, 45), border_radius=3)
                pygame.draw.rect(self.screen, (160, 100, 20), (bx, chart_base_y - 45, bar_w, 45), width=1, border_radius=3)
                self._draw_text("?", self.font_body, (190, 130, 20), (bx + bar_w // 2, chart_base_y - 25), center=True)
            self._draw_text(f"R{idx+1}", self.font_small, (120, 135, 145), (bx + bar_w // 2, chart_base_y + 10), center=True)

        # Pulsing Amber Tag: "[ 2 ROUNDS UNTRACKED ]" (1 Hz pulse)
        pulse_r = int(180 + 75 * pulse_1hz)
        pulse_g = int(120 + 50 * pulse_1hz)
        amber_pulse_col = (pulse_r, pulse_g, 0)
        amber_tag_bg = (int(38 + 20 * pulse_1hz), int(26 + 15 * pulse_1hz), 10)

        tag2 = pygame.Rect(c2_rect.left + 16, c2_rect.top + 325, cw - 32, 38)
        pygame.draw.rect(self.screen, amber_tag_bg, tag2, border_radius=6)
        pygame.draw.rect(self.screen, amber_pulse_col, tag2, width=2, border_radius=6)
        self._draw_text("[ 2 ROUNDS UNTRACKED ]", self.font_small, amber_pulse_col, tag2.center, center=True)

        # Risk rating & description
        self._draw_text("Risk Profile: 6 / 10 (Moderate Volatility)", self.font_small, (150, 160, 180), (c2_rect.left + 16, c2_rect.top + 380))
        desc2_rect = pygame.Rect(c2_rect.left + 16, c2_rect.top + 404, cw - 32, 45)
        self._draw_wrapped_text("Higher payout, but latent unhedged loss probability.", self.font_small, COLOR_TEXT_SECONDARY, desc2_rect, spacing=2)

        # -------------------------------------------------------------
        # Card 3: Strategy Gamma (Experimental, 4 rounds missing)
        # -------------------------------------------------------------
        c3_rect = pygame.Rect(start_x + (cw + gap) * 2, card_y, cw, ch)
        is_sel3 = (selected_index == 2)
        border3 = COLOR_TIMER_RED if is_sel3 else ((200, 50, 50) if selected_index is None else (45, 55, 75))
        bg3 = (42, 22, 26) if is_sel3 else (20, 24, 36)
        self._draw_card(c3_rect, border_color=border3, bg_color=bg3)

        k3_badge = pygame.Rect(c3_rect.left + 16, c3_rect.top + 16, 36, 36)
        pygame.draw.rect(self.screen, (220, 50, 50), k3_badge, border_radius=6)
        self._draw_text("3", self.font_title, COLOR_TEXT_PRIMARY, k3_badge.center, center=True)

        self._draw_text("Strategy Gamma", self.font_body, COLOR_TIMER_RED if is_sel3 else COLOR_TEXT_PRIMARY, (k3_badge.right + 14, c3_rect.top + 12))
        self._draw_text("EXPERIMENTAL HIGH-YIELD", self.font_small, (255, 80, 80), (k3_badge.right + 14, c3_rect.top + 38))

        # Projected score box
        box3 = pygame.Rect(c3_rect.left + 16, c3_rect.top + 68, cw - 32, 64)
        pygame.draw.rect(self.screen, (36, 18, 22), box3, border_radius=6)
        pygame.draw.rect(self.screen, (190, 40, 50), box3, width=1, border_radius=6)
        self._draw_text("+45% AVG", self.font_hero, (255, 80, 80), (box3.centerx, box3.top + 22), center=True)
        self._draw_text("Projected Round Gain", self.font_small, (200, 150, 150), (box3.centerx, box3.top + 48), center=True)

        # Variance metric
        self._draw_text("Variance: EXTREME (σ = ±38.0%)", self.font_small, (160, 175, 195), (c3_rect.left + 16, c3_rect.top + 144))
        var_bar3 = pygame.Rect(c3_rect.left + 16, c3_rect.top + 164, cw - 32, 8)
        pygame.draw.rect(self.screen, (28, 34, 48), var_bar3, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_TIMER_RED, (var_bar3.left, var_bar3.top, int(var_bar3.width * 0.18), var_bar3.height), border_radius=4)

        # Historical Telemetry Bars (2 verified, 4 missing/untracked)
        self._draw_text("HISTORICAL TELEMETRY (2/6 ROUNDS)", self.font_small, (140, 150, 170), (c3_rect.left + 16, c3_rect.top + 184))
        r3_vals = [44, 46]
        for idx in range(6):
            bx = c3_rect.left + 16 + idx * (bar_w + 8)
            if idx < 2:
                bh = int(r3_vals[idx] * 1.5)
                by = chart_base_y - bh
                pygame.draw.rect(self.screen, (240, 60, 60), (bx, by, bar_w, bh), border_radius=3)
            else:
                # Corrupted / Missing bar with red flashing outline
                pygame.draw.rect(self.screen, (40, 16, 20), (bx, chart_base_y - 55, bar_w, 55), border_radius=3)
                pygame.draw.rect(self.screen, (200, 40, 50), (bx, chart_base_y - 55, bar_w, 55), width=1, border_radius=3)
                self._draw_text("!", self.font_body, (255, 80, 80), (bx + bar_w // 2, chart_base_y - 30), center=True)
            self._draw_text(f"R{idx+1}", self.font_small, (120, 135, 145), (bx + bar_w // 2, chart_base_y + 10), center=True)

        # Blinking Warning Tag: "[ 4 ROUNDS UNTRACKED — EXTREME VARIANCE ]" (1 Hz pulse)
        blink_on = pulse_1hz > 0.35
        red_blink_col = COLOR_TIMER_RED if blink_on else (160, 40, 45)
        red_tag_bg = (55, 16, 22) if blink_on else (28, 12, 16)

        tag3 = pygame.Rect(c3_rect.left + 16, c3_rect.top + 325, cw - 32, 38)
        pygame.draw.rect(self.screen, red_tag_bg, tag3, border_radius=6)
        pygame.draw.rect(self.screen, red_blink_col, tag3, width=2, border_radius=6)
        self._draw_text("[ 4 ROUNDS UNTRACKED — EXTREME VARIANCE ]", self.font_small, red_blink_col, tag3.center, center=True)

        # Risk rating & description
        self._draw_text("Risk Profile: 9.5 / 10 (Critical Downside)", self.font_small, (255, 120, 120), (c3_rect.left + 16, c3_rect.top + 380))
        desc3_rect = pygame.Rect(c3_rect.left + 16, c3_rect.top + 404, cw - 32, 45)
        self._draw_wrapped_text("Massive potential gain, but catastrophic ranking drop risk.", self.font_small, COLOR_TEXT_SECONDARY, desc3_rect, spacing=2)

        # 3. Bottom Prompt
        self._draw_text(
            "SELECT STRATEGY [1], [2], OR [3] TO COMMIT TOURNAMENT ROSTER",
            self.font_small,
            (130, 140, 165),
            (self.width // 2, self.height - 35),
            center=True,
        )

        return True

    def _draw_skin_social_analytics(
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
        """Render social_analytics simulation skin: creator studio, reach meter, suspension risk gauge, BART controls."""
        if bart_runner is None:
            return False

        vx, vy = effects.vibration_offset
        jx, jy = effects.jitter_offset
        ox = vx + jx
        oy = vy + jy

        pump_count = bart_runner.pump_count
        reach_value = bart_runner.current_value
        max_pumps = bart_runner.config.max_pumps
        instability = bart_runner.get_instability_fraction()
        is_burst = bart_runner.is_burst

        # 1. Top Navigation Bar (Creator Studio)
        nav_rect = pygame.Rect(50 + ox, 90 + oy, self.width - 100, 44)
        self._draw_card(nav_rect, border_color=(45, 52, 75), bg_color=(18, 22, 32))

        # Live feed indicator
        pygame.draw.circle(self.screen, COLOR_TIMER_RED, (nav_rect.left + 22, nav_rect.centery), 5)
        self._draw_text("LIVE CAMPAIGN", self.font_small, COLOR_TIMER_RED, (nav_rect.left + 36, nav_rect.centery), midleft=True)
        self._draw_text(
            "CREATOR STUDIO // VIRAL FEED REACH ANALYTICS",
            self.font_small,
            COLOR_TEXT_PRIMARY,
            (nav_rect.left + 160, nav_rect.centery),
            midleft=True,
        )
        self._draw_text("Target Algorithm: 15–25 Demographic", self.font_small, (130, 140, 165), (nav_rect.right - 24, nav_rect.centery), midright=True)

        # 2. Main Creator Studio Analytics Panel
        panel_w = 920
        panel_h = 280
        panel_rect = pygame.Rect(self.width // 2 - panel_w // 2 + ox, 150 + oy, panel_w, panel_h)
        self._draw_card(panel_rect, border_color=(50, 58, 82), bg_color=(20, 24, 36))

        # Audience Reach Meter (Large Dynamic Counter)
        self._draw_text(
            "ACCUMULATED AUDIENCE REACH (IMPRESSIONS)",
            self.font_small,
            (140, 150, 175),
            (panel_rect.centerx, panel_rect.top + 24),
            center=True,
        )

        reach_str = f"+{reach_value:,}" if not is_burst else "0"
        reach_color = COLOR_ACCENT_CYAN if not is_burst else COLOR_TIMER_RED
        self._draw_text(reach_str, self.font_hero, reach_color, (panel_rect.centerx, panel_rect.top + 62), center=True)

        # Metric badges directly below counter
        badge_y = panel_rect.top + 106
        viral_tier = min(5, 1 + pump_count // 3)
        self._draw_text(f"VIRAL VELOCITY: TIER {viral_tier}", self.font_small, COLOR_ACCENT_CYAN, (panel_rect.centerx - 200, badge_y), center=True)
        self._draw_text(f"POST ESCALATION: {pump_count} / {max_pumps} CYCLES", self.font_small, (160, 170, 190), (panel_rect.centerx + 200, badge_y), center=True)

        # Horizontal Report Risk Gauge: "Content Flag & Suspension Risk"
        gauge_w = 760
        gauge_h = 24
        gauge_x = panel_rect.centerx - gauge_w // 2
        gauge_y = panel_rect.top + 160

        self._draw_text(
            "Content Flag & Suspension Risk",
            self.font_small,
            COLOR_TEXT_SECONDARY,
            (gauge_x, gauge_y - 20),
        )

        risk_pct = int(instability * 100)
        risk_color = COLOR_TIMER_GREEN if instability < 0.4 else (COLOR_TIMER_AMBER if instability < 0.75 else COLOR_TIMER_RED)
        self._draw_text(
            f"{risk_pct}% RISK LEVEL",
            self.font_small,
            risk_color,
            (gauge_x + gauge_w, gauge_y - 20),
            midright=True,
        )

        # Gauge track
        pygame.draw.rect(self.screen, (15, 18, 26), (gauge_x, gauge_y, gauge_w, gauge_h), border_radius=6)
        pygame.draw.rect(self.screen, (45, 52, 74), (gauge_x, gauge_y, gauge_w, gauge_h), width=2, border_radius=6)

        # Fill bar
        fill_w = max(0, min(gauge_w - 4, int((gauge_w - 4) * instability)))
        if fill_w > 4:
            pygame.draw.rect(self.screen, risk_color, (gauge_x + 2, gauge_y + 2, fill_w, gauge_h - 4), border_radius=4)

        # Segmentation lines every 20%
        for tick_idx in range(1, 5):
            tx = gauge_x + int(gauge_w * (tick_idx / 5.0))
            pygame.draw.line(self.screen, (60, 68, 92), (tx, gauge_y + 3), (tx, gauge_y + gauge_h - 3), 1)

        # Risk status readout
        if instability < 0.4:
            status_desc = "ALGORITHM STATUS: COMPLIANT — REACH EXPANSION STEADY"
        elif instability < 0.75:
            status_desc = "ALGORITHM STATUS: ELEVATED FLAGGING — AUTOMATED REVIEW TRIGGERED"
        else:
            status_desc = "ALGORITHM STATUS: CRITICAL RISK — ACCOUNT SUSPENSION IMMINENT ON NEXT POST"
        self._draw_text(status_desc, self.font_small, risk_color, (panel_rect.centerx, gauge_y + gauge_h + 16), center=True)

        # 3. Live Controls: Two Action Cards at Bottom
        card_y = self.height - 110 + oy
        card_h = 84
        card_w = 460

        # Option 1: SECURE REACH (Stop Posting)
        r1 = pygame.Rect(self.width // 2 - card_w - 15 + ox, card_y, card_w, card_h)
        is_sel1 = (selected_index == 0)
        b1 = COLOR_TIMER_GREEN if is_sel1 else ((0, 180, 120) if selected_index is None else (50, 56, 72))
        bg1 = (24, 46, 38) if is_sel1 else COLOR_CARD_BG
        self._draw_card(r1, border_color=b1, bg_color=bg1)

        k1 = pygame.Rect(r1.left + 16, r1.centery - 18, 36, 36)
        pygame.draw.rect(self.screen, (0, 180, 120), k1, border_radius=6)
        self._draw_text("1", self.font_title, COLOR_TEXT_PRIMARY, k1.center, center=True)

        self._draw_text("SECURE REACH (Stop Posting)", self.font_body, COLOR_TIMER_GREEN if is_sel1 else COLOR_TEXT_PRIMARY, (k1.right + 16, r1.top + 12))
        sub1_rect = pygame.Rect(k1.right + 16, r1.top + 36, r1.width - 80, r1.height - 42)
        self._draw_wrapped_text(f"Lock in +{reach_value:,} impressions & conclude safely.", self.font_small, COLOR_TEXT_SECONDARY, sub1_rect, spacing=2, center_v=True)

        # Option 2: POST ANOTHER (Escalate Reach)
        r2 = pygame.Rect(self.width // 2 + 15 + ox, card_y, card_w, card_h)
        is_sel2 = (selected_index == 1)
        b2 = COLOR_TIMER_RED if instability >= 0.75 else (COLOR_TIMER_AMBER if is_sel2 else (190, 120, 20))
        bg2 = (48, 32, 26) if is_sel2 else COLOR_CARD_BG
        self._draw_card(r2, border_color=b2, bg_color=bg2)

        k2 = pygame.Rect(r2.left + 16, r2.centery - 18, 36, 36)
        pygame.draw.rect(self.screen, (190, 120, 20), k2, border_radius=6)
        self._draw_text("2", self.font_title, COLOR_TEXT_PRIMARY, k2.center, center=True)

        self._draw_text("POST ANOTHER (Escalate Reach)", self.font_body, COLOR_TIMER_AMBER if is_sel2 else COLOR_TEXT_PRIMARY, (k2.right + 16, r2.top + 12))
        sub2_rect = pygame.Rect(k2.right + 16, r2.top + 36, r2.width - 80, r2.height - 42)
        self._draw_wrapped_text(f"Push algorithm (+{bart_runner.config.increment_per_pump:,} reach, elevated flag risk).", self.font_small, COLOR_TEXT_SECONDARY, sub2_rect, spacing=2, center_v=True)

        # 4. Suspension Burst Splash Card
        if is_burst:
            splash_w = 820
            splash_h = 220
            splash_rect = pygame.Rect(self.width // 2 - splash_w // 2, self.height // 2 - splash_h // 2 - 20, splash_w, splash_h)
            self._draw_card(splash_rect, border_color=COLOR_TIMER_RED, bg_color=(45, 12, 18))

            # Warning border accent line
            pygame.draw.line(self.screen, COLOR_TIMER_RED, (splash_rect.left + 20, splash_rect.top + 52), (splash_rect.right - 20, splash_rect.top + 52), 2)

            self._draw_text(
                "ACCOUNT SUSPENDED — REACH RESET TO ZERO",
                self.font_hero,
                COLOR_TIMER_RED,
                (splash_rect.centerx, splash_rect.top + 28),
                center=True,
            )
            self._draw_text(
                "Community Guidelines Violation: Content Report Threshold Exceeded",
                self.font_title,
                (255, 210, 210),
                (splash_rect.centerx, splash_rect.top + 85),
                center=True,
            )
            self._draw_text(
                "All accumulated viral impressions have been revoked by platform moderation.",
                self.font_body,
                (220, 170, 170),
                (splash_rect.centerx, splash_rect.top + 125),
                center=True,
            )
            self._draw_text(
                "Final Score: 0 Impressions | Account Standing: Banned",
                self.font_small,
                (255, 140, 140),
                (splash_rect.centerx, splash_rect.top + 168),
                center=True,
            )

        return True

    def _draw_skin_portal_log(
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
        """Render portal_log simulation skin: split-screen IT security log and decision terminal."""
        vx, vy = effects.vibration_offset
        jx, jy = effects.jitter_offset
        ox = vx + jx
        oy = vy + jy

        # Diegetic urgency: text jitter on server timestamp if time_remaining_s <= 15.0
        if time_remaining_s <= 15.0:
            tjx, tjy = effects.jitter_offset
            if tjx == 0 and tjy == 0:
                tjx = int(math.sin(time_remaining_s * 10.0) * 2)
                tjy = int(math.cos(time_remaining_s * 15.0) * 2)
        else:
            tjx, tjy = (0, 0)

        # Split screen setup
        total_w = self.width - 100
        start_x = 50 + ox
        top_y = 95 + oy
        panel_h = 565

        gap = 20
        w_left = int((total_w - gap) * 0.45)
        w_right = (total_w - gap) - w_left

        left_rect = pygame.Rect(start_x, top_y, w_left, panel_h)
        right_rect = pygame.Rect(start_x + w_left + gap, top_y, w_right, panel_h)

        # =============================================================
        # Left Panel (Evidence Log, 45% width): Dark Terminal Container
        # =============================================================
        pygame.draw.rect(self.screen, (10, 12, 18), left_rect, border_radius=8)
        pygame.draw.rect(self.screen, (40, 48, 68), left_rect, width=2, border_radius=8)

        # Terminal Header Bar
        hdr_h = 36
        term_hdr = pygame.Rect(left_rect.left, left_rect.top, w_left, hdr_h)
        pygame.draw.rect(self.screen, (20, 24, 34), term_hdr, border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.line(self.screen, (40, 48, 68), (left_rect.left, term_hdr.bottom), (left_rect.right, term_hdr.bottom), 1)

        # Window controls
        dots = [
            ((left_rect.left + 18, term_hdr.centery), (255, 95, 87)),
            ((left_rect.left + 34, term_hdr.centery), (254, 188, 46)),
            ((left_rect.left + 50, term_hdr.centery), (40, 201, 64)),
        ]
        for d_center, d_col in dots:
            pygame.draw.circle(self.screen, d_col, d_center, 4)

        self._draw_text(
            "root@campus-it-gateway: /var/log/audit.log",
            self.font_mono_small,
            (150, 160, 180),
            (left_rect.left + 68, term_hdr.centery),
            midleft=True,
        )

        # Timestamp line with diegetic jitter
        ms_part = int((time_remaining_s * 1000) % 1000)
        ts_text = f"SYS_TIME: 2026-09-19 23:17:{int(time_remaining_s):02d}.{ms_part:03d} UTC"
        self._draw_text(
            ts_text,
            self.font_mono_small,
            (0, 220, 255) if time_remaining_s > 15.0 else (255, 100, 100),
            (left_rect.left + 20 + tjx, left_rect.top + 50 + tjy),
        )

        # Terminal prompt
        prompt_y = left_rect.top + 76
        self._draw_text("auth_daemon --inspect --target friend_account_id", self.font_mono_small, (100, 180, 120), (left_rect.left + 20, prompt_y))
        pygame.draw.line(self.screen, (28, 34, 48), (left_rect.left + 20, prompt_y + 24), (left_rect.right - 20, prompt_y + 24), 1)

        # Core Log lines
        log_entries = [
            ("[AUTH_DAEMON]", " USER: friend_account_id", (0, 210, 240), (220, 230, 255)),
            ("[STATUS]", " LOCKED — OUTSTANDING SYSTEM GLITCH", (255, 120, 80), (255, 180, 160)),
            ("[TICKET_STATUS]", " PENDING ADMIN REVIEW: 21 DAYS", (255, 180, 0), (240, 210, 140)),
            ("[DEADLINE_ALERT]", " ASSIGNMENT CLOSES IN: 00:42:15", (255, 70, 70), (255, 130, 130)),
            ("[STORED_SESSION]", " ACTIVE TOKEN DETECTED FROM YOUR IP", (0, 229, 255), (180, 240, 255)),
        ]

        log_start_y = prompt_y + 36
        entry_h = 44
        for idx, (tag, detail, tag_col, det_col) in enumerate(log_entries):
            ey = log_start_y + idx * entry_h
            entry_box = pygame.Rect(left_rect.left + 16, ey - 4, w_left - 32, 38)
            pygame.draw.rect(self.screen, (16, 20, 30), entry_box, border_radius=4)
            pygame.draw.rect(self.screen, (32, 40, 58), entry_box, width=1, border_radius=4)

            self._draw_text(tag, self.font_mono_small, tag_col, (entry_box.left + 12, ey + 4))
            tag_w = self.font_mono_small.size(tag)[0]
            self._draw_text(detail, self.font_mono_small, det_col, (entry_box.left + 12 + tag_w, ey + 4))

        # Additional diagnostic lines
        extra_y = log_start_y + len(log_entries) * entry_h + 8
        diag_lines = [
            "--------------------------------------------------",
            ">> ORIGIN_HOST: 192.168.4.120 [TRUSTED_WORKSTATION]",
            ">> CREDENTIAL_CACHE: VALID OAUTH_2.0 REFRESH TOKEN",
            ">> ACCESS_LOG_EVENT: IMMINENT LOCKOUT ENFORCEMENT",
            "--------------------------------------------------",
        ]
        for d_idx, d_line in enumerate(diag_lines):
            self._draw_text(d_line, self.font_mono_small, (90, 105, 130), (left_rect.left + 20, extra_y + d_idx * 18))

        # Institutional Policy Callout Box at bottom of left panel
        clause_box = pygame.Rect(left_rect.left + 16, left_rect.bottom - 92, w_left - 32, 76)
        pygame.draw.rect(self.screen, (32, 14, 18), clause_box, border_radius=6)
        pygame.draw.rect(self.screen, (180, 50, 60), clause_box, width=1, border_radius=6)

        self._draw_text("CAMPUS IT POLICY — SECTION 4.2.1", self.font_small, (255, 100, 100), (clause_box.left + 14, clause_box.top + 10))
        self._draw_text(
            "Accessing another user's portal credentials constitutes",
            self.font_small,
            (210, 170, 170),
            (clause_box.left + 14, clause_box.top + 30),
        )
        self._draw_text(
            "unauthorized authentication and carries disciplinary suspension.",
            self.font_small,
            (210, 170, 170),
            (clause_box.left + 14, clause_box.top + 50),
        )

        # =============================================================
        # Right Panel (Decision Terminal, 55% width): 3 Dilemma Cards
        # =============================================================
        pygame.draw.rect(self.screen, (18, 22, 32), right_rect, border_radius=8)
        pygame.draw.rect(self.screen, (40, 48, 68), right_rect, width=2, border_radius=8)

        # Right Header
        r_hdr = pygame.Rect(right_rect.left, right_rect.top, w_right, hdr_h)
        pygame.draw.rect(self.screen, (24, 28, 42), r_hdr, border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.line(self.screen, (40, 48, 68), (right_rect.left, r_hdr.bottom), (right_rect.right, r_hdr.bottom), 1)

        self._draw_text(
            "DECISION TERMINAL // AUTHORIZATION PROTOCOL",
            self.font_small,
            COLOR_ACCENT_CYAN,
            (right_rect.left + 20, r_hdr.centery),
            midleft=True,
        )
        self._draw_text("RECORDED EVENT", self.font_small, (130, 140, 160), (right_rect.right - 20, r_hdr.centery), midright=True)

        # Three Options on Cards
        cards_start_y = right_rect.top + 50
        card_h = 146
        card_gap = 18

        opts_data = [
            (
                1,
                "Log In With Saved Credentials",
                "Submit assignment on friend's behalf (Loyalty)",
                "Helps close friend avoid deadline failure; explicitly violates IT policy.",
                "[ POLICY VIOLATION // PEER LOYALTY ]",
                COLOR_TIMER_AMBER,
                (45, 34, 18),
            ),
            (
                2,
                "Direct to Official Appeal",
                "Strict compliance with campus procedures (Compliance)",
                "Follows rules strictly; friend misses deadline & incurs 20% penalty.",
                "[ STRICTLY COMPLIANT // FRIEND FAILS ]",
                COLOR_TIMER_GREEN,
                (20, 38, 30),
            ),
            (
                3,
                "Exploit Guest Access Loophole",
                "Use unpatched portal guest feature (Grey Area)",
                "Circumvents login with guest bypass; risks investigation if audited.",
                "[ GREY AREA // UNPATCHED EXPLOIT ]",
                (180, 120, 255),
                (36, 22, 48),
            ),
        ]

        for i, (key, title, subtitle, trade_off, tag, accent_col, bg_col) in enumerate(opts_data):
            cy = cards_start_y + i * (card_h + card_gap)
            c_rect = pygame.Rect(right_rect.left + 20, cy, w_right - 40, card_h)

            is_sel = (selected_index == i)
            border_col = accent_col if is_sel else ((60, 70, 95) if selected_index is not None else (40, 48, 68))
            card_bg = bg_col if is_sel else COLOR_CARD_BG
            self._draw_card(c_rect, border_color=border_col, bg_color=card_bg)

            # Key Badge
            k_badge = pygame.Rect(c_rect.left + 16, c_rect.top + 16, 36, 36)
            pygame.draw.rect(self.screen, accent_col, k_badge, border_radius=6)
            self._draw_text(str(key), self.font_title, COLOR_TEXT_PRIMARY, k_badge.center, center=True)

            # Title & Subtitle (font_body prevents overlap with subtitle at top + 42)
            self._draw_text(title, self.font_body, accent_col if is_sel else COLOR_TEXT_PRIMARY, (k_badge.right + 16, c_rect.top + 14))
            self._draw_text(subtitle, self.font_small, (150, 160, 185), (k_badge.right + 16, c_rect.top + 42))

            # Trade-off text
            trade_rect = pygame.Rect(c_rect.left + 16, c_rect.top + 70, c_rect.width - 32, 38)
            self._draw_wrapped_text(trade_off, self.font_small, COLOR_TEXT_SECONDARY, trade_rect, spacing=2, center_v=True)

            # Bottom pill tag
            tag_rect = pygame.Rect(c_rect.left + 16, c_rect.bottom - 34, c_rect.width - 32, 24)
            pygame.draw.rect(self.screen, (16, 20, 30), tag_rect, border_radius=4)
            pygame.draw.rect(self.screen, accent_col, tag_rect, width=1, border_radius=4)
            self._draw_text(tag, self.font_small, accent_col, tag_rect.center, center=True)

        # Bottom Prompt
        self._draw_text(
            "PRESS KEY [1], [2], OR [3] TO COMMIT DECISION TO AUDIT LOG",
            self.font_small,
            (130, 140, 165),
            (self.width // 2, self.height - 35),
            center=True,
        )

        return True

    def _draw_skin_code_diff(
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
        """Render code_diff simulation skin: dual-pane repository diff viewer with highlighted overlapping segments."""
        vx, vy = effects.vibration_offset
        jx, jy = effects.jitter_offset
        ox = vx + jx
        oy = vy + jy

        # 1. Stakes Callout Top Banner
        banner_w = self.width - 100
        banner_h = 44
        banner_rect = pygame.Rect(50 + ox, 90 + oy, banner_w, banner_h)
        self._draw_card(banner_rect, border_color=(255, 140, 0), bg_color=(42, 22, 16))

        # Warning icon/pulse
        warn_pulse = (math.sin(time_remaining_s * 3.0) + 1.0) / 2.0
        warn_col = (255, int(140 + 50 * warn_pulse), int(40 * warn_pulse))
        tri_pts = [
            (banner_rect.left + 24, banner_rect.centery - 10),
            (banner_rect.left + 14, banner_rect.centery + 8),
            (banner_rect.left + 34, banner_rect.centery + 8),
        ]
        pygame.draw.polygon(self.screen, warn_col, tri_pts)
        self._draw_text("!", self.font_small, (20, 20, 20), (banner_rect.left + 24, banner_rect.centery + 1), center=True)
        self._draw_text("INTEGRITY CHECK: 38% UNATTRIBUTED OVERLAP IDENTIFIED", self.font_body, warn_col, (banner_rect.left + 46, banner_rect.centery), midleft=True)
        self._draw_text("[PLAGIARISM FLAGGED: SENIOR REPO MATCH]", self.font_small, COLOR_TIMER_RED, (banner_rect.right - 20, banner_rect.centery), midright=True)

        # 2. Dual-Pane Code Diff Container
        diff_top = 144 + oy
        diff_h = 320
        gap = 18
        half_w = (banner_w - gap) // 2

        left_diff = pygame.Rect(50 + ox, diff_top, half_w, diff_h)
        right_diff = pygame.Rect(50 + ox + half_w + gap, diff_top, half_w, diff_h)

        # Pane Header Bars
        pane_hdr_h = 32
        left_hdr = pygame.Rect(left_diff.left, left_diff.top, half_w, pane_hdr_h)
        right_hdr = pygame.Rect(right_diff.left, right_diff.top, half_w, pane_hdr_h)

        # Left Diff Pane (Current Project Submission)
        pygame.draw.rect(self.screen, (14, 17, 26), left_diff, border_radius=6)
        pygame.draw.rect(self.screen, (40, 48, 68), left_diff, width=1, border_radius=6)
        pygame.draw.rect(self.screen, (22, 27, 40), left_hdr, border_top_left_radius=6, border_top_right_radius=6)
        self._draw_text("CURRENT PROJECT SUBMISSION: src/core/engine.py (Your Group)", self.font_small, (200, 215, 240), (left_hdr.left + 14, left_hdr.centery), midleft=True)

        # Right Diff Pane (Uncredited Archived Repository)
        pygame.draw.rect(self.screen, (14, 17, 26), right_diff, border_radius=6)
        pygame.draw.rect(self.screen, (40, 48, 68), right_diff, width=1, border_radius=6)
        pygame.draw.rect(self.screen, (22, 27, 40), right_hdr, border_top_left_radius=6, border_top_right_radius=6)
        self._draw_text("UNCREDITED ARCHIVED REPOSITORY: repo_2022_grad/core.py (Senior Alumni)", self.font_small, COLOR_TIMER_AMBER, (right_hdr.left + 14, right_hdr.centery), midleft=True)

        # Code lines to render
        left_code = [
            ("01", "class OptimizationEngine:"),
            ("02", "    def __init__(self, weights: list[float]):"),
            ("03", "        self.tensor_map = compute_latent_graph(weights)   # MATCH"),
            ("04", "        self.matrix_delta = decompose_svd_fast(weights)    # MATCH"),
            ("05", "        self.gradient_cache = [0.0] * len(weights)        # MATCH"),
            ("06", "    def step_optimizer(self, lr: float):"),
            ("07", "        return execute_forward_pass(self.tensor_map, lr)"),
            ("08", "        # End of implementation block"),
        ]

        right_code = [
            ("01", "class LegacyPipelineRunner:"),
            ("02", "    def __init__(self, weights: list[float]):"),
            ("03", "        self.tensor_map = compute_latent_graph(weights)   # MATCH"),
            ("04", "        self.matrix_delta = decompose_svd_fast(weights)    # MATCH"),
            ("05", "        self.gradient_cache = [0.0] * len(weights)        # MATCH"),
            ("06", "    def run_iteration(self, rate: float):"),
            ("07", "        return execute_forward_pass(self.tensor_map, rate)"),
            ("08", "        # Archived under CC-BY-NC 2022"),
        ]

        # Draw left code lines
        line_start_y = left_diff.top + pane_hdr_h + 8
        line_h = 32
        for l_idx, (num, code_text) in enumerate(left_code):
            ly = line_start_y + l_idx * line_h
            # Overlapping match segment lines 03, 04, 05 highlighted in amber/yellow boxes (pygame.draw.rect with alpha)
            is_match = l_idx in (2, 3, 4)
            if is_match:
                match_rect = pygame.Rect(left_diff.left + 4, ly - 2, half_w - 8, line_h - 2)
                alpha_box = pygame.Surface((match_rect.width, match_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(alpha_box, (255, 190, 0, 50), (0, 0, match_rect.width, match_rect.height), border_radius=3)
                self.screen.blit(alpha_box, match_rect.topleft)
                pygame.draw.rect(self.screen, (180, 130, 0), match_rect, width=1, border_radius=3)
                pygame.draw.line(self.screen, (255, 179, 0), (match_rect.left, match_rect.top), (match_rect.left, match_rect.bottom), 3)

            self._draw_text(num, self.font_mono_small, (100, 115, 140), (left_diff.left + 14, ly + 4))
            code_col = (255, 215, 120) if is_match else (180, 190, 210)
            self._draw_text(code_text, self.font_mono_small, code_col, (left_diff.left + 46, ly + 4))

        # Draw right code lines
        for r_idx, (num, code_text) in enumerate(right_code):
            ly = line_start_y + r_idx * line_h
            is_match = r_idx in (2, 3, 4)
            if is_match:
                match_rect = pygame.Rect(right_diff.left + 4, ly - 2, half_w - 8, line_h - 2)
                alpha_box = pygame.Surface((match_rect.width, match_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(alpha_box, (255, 190, 0, 50), (0, 0, match_rect.width, match_rect.height), border_radius=3)
                self.screen.blit(alpha_box, match_rect.topleft)
                pygame.draw.rect(self.screen, (180, 130, 0), match_rect, width=1, border_radius=3)
                pygame.draw.line(self.screen, (255, 179, 0), (match_rect.left, match_rect.top), (match_rect.left, match_rect.bottom), 3)

            self._draw_text(num, self.font_mono_small, (100, 115, 140), (right_diff.left + 14, ly + 4))
            code_col = (255, 215, 120) if is_match else (180, 190, 210)
            self._draw_text(code_text, self.font_mono_small, code_col, (right_diff.left + 46, ly + 4))

        # 3. Decision Options: Three Cards Below
        cards_y = diff_top + diff_h + 14
        card_w = (banner_w - 2 * 20) // 3
        card_h = 160

        diff_opts = [
            (
                1,
                "Remove Borrowed Sections",
                "Academically Honest / Delay",
                "Scrub senior code & accept timeline delay before submission.",
                "[ 100% ETHICAL // TIMELINE HIT ]",
                COLOR_TIMER_GREEN,
                (20, 36, 28),
            ),
            (
                2,
                "Keep & Add Acknowledgement",
                "Credit Source / Integrity Risk",
                "Add formal credit in comments. Submits on time; board reviews.",
                "[ TIMELINE KEPT // AUDIT RISK ]",
                COLOR_TIMER_AMBER,
                (42, 32, 18),
            ),
            (
                3,
                "Contact Senior for Consent",
                "Formal Permission / Uncertainty",
                "Request authorization from alumni. Submissions frozen pending response.",
                "[ FORMAL CONSENT // UNCERTAIN ]",
                (180, 120, 255),
                (36, 22, 48),
            ),
        ]

        for i, (key, title, subtitle, desc, tag, accent_col, bg_col) in enumerate(diff_opts):
            cx = 50 + ox + i * (card_w + 20)
            c_rect = pygame.Rect(cx, cards_y, card_w, card_h)

            is_sel = (selected_index == i)
            border_col = accent_col if is_sel else ((60, 70, 95) if selected_index is not None else (40, 48, 68))
            card_bg = bg_col if is_sel else COLOR_CARD_BG
            self._draw_card(c_rect, border_color=border_col, bg_color=card_bg)

            # Key Badge
            k_badge = pygame.Rect(c_rect.left + 14, c_rect.top + 14, 32, 32)
            pygame.draw.rect(self.screen, accent_col, k_badge, border_radius=6)
            self._draw_text(str(key), self.font_title, COLOR_TEXT_PRIMARY, k_badge.center, center=True)

            self._draw_text(title, self.font_body, accent_col if is_sel else COLOR_TEXT_PRIMARY, (k_badge.right + 12, c_rect.top + 12))
            self._draw_text(subtitle, self.font_small, (150, 160, 185), (k_badge.right + 12, c_rect.top + 34))

            # Description wrapped
            text_rect = pygame.Rect(c_rect.left + 14, c_rect.top + 58, c_rect.width - 28, 55)
            self._draw_wrapped_text(desc, self.font_small, COLOR_TEXT_SECONDARY, text_rect, spacing=4, center_v=True)

            # Tag pill
            tag_rect = pygame.Rect(c_rect.left + 14, c_rect.bottom - 30, c_rect.width - 28, 22)
            pygame.draw.rect(self.screen, (16, 20, 30), tag_rect, border_radius=4)
            pygame.draw.rect(self.screen, accent_col, tag_rect, width=1, border_radius=4)
            self._draw_text(tag, self.font_small, accent_col, tag_rect.center, center=True)

        # Bottom Prompt
        self._draw_text(
            "PRESS KEY [1], [2], OR [3] TO COMMIT CODE INTEGRITY DECISION",
            self.font_small,
            (130, 140, 165),
            (self.width // 2, self.height - 24),
            center=True,
        )

        return True

    def _draw_skin_fork_map(
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
        """Render fork_map simulation skin: diverging crossroads, unsettled compass, and outcome ambiguity."""
        if selected_index is not None:
            self._last_fork_choice = selected_index

        vx, vy = effects.vibration_offset
        jx, jy = effects.jitter_offset
        ox = vx + jx
        oy = vy + jy

        cx = self.width // 2 + ox

        # 1. Top Navigation Telemetry Bar
        hdr_w = self.width - 240
        hdr_rect = pygame.Rect(50 + ox, 90 + oy, hdr_w, 56)
        self._draw_card(hdr_rect, border_color=(45, 55, 78), bg_color=(18, 22, 34))

        if selected_index is None:
            self._draw_text(
                "TRAJECTORY NAVIGATION SYSTEM // DIVERGENT CROSSROADS",
                self.font_body,
                COLOR_ACCENT_CYAN,
                (hdr_rect.left + 20, hdr_rect.top + 9),
            )
            self._draw_text(
                "[DECISION UNRESOLVED: BOTH BRANCHES HARBOR CRITICAL UNCERTAINTY]",
                self.font_small,
                COLOR_TIMER_AMBER,
                (hdr_rect.left + 20, hdr_rect.top + 33),
            )
        else:
            pulse_syn = (math.sin(time_remaining_s * 4.0) + 1.0) / 2.0
            syn_col = (int(0 + 120 * pulse_syn), int(210 + 45 * pulse_syn), 255)
            self._draw_text(
                "Synthesizing outcome projections...",
                self.font_body,
                syn_col,
                (hdr_rect.left + 20, hdr_rect.top + 9),
            )
            self._draw_text(
                "[TRAJECTORY LOCKED • SUSPENDED ACROSS EVALUATION WINDOW]",
                self.font_small,
                COLOR_ACCENT_CYAN,
                (hdr_rect.left + 20, hdr_rect.top + 33),
            )

        # 2. Unsettled Compass Rose at top right (sized & shifted to avoid timer bar)
        compass_center = (self.width - 85 + ox, 122 + oy)
        if selected_index is not None:
            # Accelerated compass rotation
            compass_angle = (time_remaining_s * 360.0) % 360.0
        else:
            # Slow continuous drift without settling on North
            compass_angle = (time_remaining_s * 45.0) % 360.0

        self._draw_compass(compass_center, 28, compass_angle)
        self._draw_text(
            "[ UNSETTLED ]",
            self.font_mono_small,
            COLOR_TIMER_AMBER if selected_index is None else COLOR_TIMER_RED,
            (compass_center[0], compass_center[1] + 36),
            center=True,
        )

        # 3. Crossroads Fork Geometry
        trunk_bottom_y = 480 + oy
        fork_node_y = 380 + oy

        # Approach road (stem)
        stem_rect = pygame.Rect(cx - 18, fork_node_y, 36, trunk_bottom_y - fork_node_y)
        pygame.draw.rect(self.screen, (22, 26, 38), stem_rect)
        pygame.draw.line(self.screen, (50, 60, 85), (stem_rect.left, stem_rect.top), (stem_rect.left, stem_rect.bottom), 2)
        pygame.draw.line(self.screen, (50, 60, 85), (stem_rect.right, stem_rect.top), (stem_rect.right, stem_rect.bottom), 2)

        # Dashed center lane on approach road
        for sy in range(fork_node_y + 8, trunk_bottom_y - 8, 16):
            pygame.draw.line(self.screen, (100, 115, 140), (cx, sy), (cx, sy + 8), 2)

        # Start/Present position indicator
        pygame.draw.circle(self.screen, COLOR_TIMER_GREEN, (cx, trunk_bottom_y - 12), 6)
        pygame.draw.circle(self.screen, (255, 255, 255), (cx, trunk_bottom_y - 12), 3)
        self._draw_text("PRESENT LOCATION", self.font_small, COLOR_TIMER_GREEN, (cx, trunk_bottom_y + 8), center=True)

        # Fork junction circle
        pygame.draw.circle(self.screen, (30, 36, 52), (cx, fork_node_y), 20)
        pygame.draw.circle(self.screen, (70, 85, 115), (cx, fork_node_y), 20, width=2)

        # -------------------------------------------------------------
        # Path A (Key 1, Left Branch): Solid cyan roadway -> Gray Box
        # -------------------------------------------------------------
        is_a_dimmed = (selected_index == 1)
        is_a_active = (selected_index == 0)

        # Compute curve points for Path A (quadratic bezier)
        p0 = (float(cx), float(fork_node_y))
        p1 = (float(cx - 100), float(fork_node_y - 90))
        p2 = (float(cx - 310), float(fork_node_y - 180))

        pts_a: list[tuple[int, int]] = []
        for step in range(21):
            t = step / 20.0
            bx = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
            by = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
            pts_a.append((int(bx), int(by)))

        if is_a_dimmed:
            a_col = (40, 48, 62)
            a_w = 4
        elif is_a_active:
            # Glowing illuminated branch
            pygame.draw.lines(self.screen, (0, 90, 120), False, pts_a, 16)
            a_col = COLOR_ACCENT_CYAN
            a_w = 6
        else:
            pygame.draw.lines(self.screen, (16, 34, 48), False, pts_a, 12)
            a_col = COLOR_ACCENT_CYAN
            a_w = 5

        pygame.draw.lines(self.screen, a_col, False, pts_a, a_w)

        # Path A Label along roadway
        mid_a = pts_a[10]
        self._draw_text(
            "ESTABLISHED TRACK",
            self.font_small,
            (90, 100, 115) if is_a_dimmed else COLOR_ACCENT_CYAN,
            (mid_a[0] - 20, mid_a[1] + 16),
            center=True,
        )

        # Terminal Box A: Opaque Gray Box (expanded to 380px to contain subtitle cleanly)
        box_a = pygame.Rect(cx - 550, fork_node_y - 215, 380, 68)
        box_a_border = (50, 58, 75) if is_a_dimmed else ((0, 229, 255) if is_a_active else (80, 95, 125))
        box_a_bg = (20, 24, 32) if is_a_dimmed else ((20, 36, 48) if is_a_active else (26, 30, 42))
        self._draw_card(box_a, border_color=box_a_border, bg_color=box_a_bg)

        self._draw_text(
            "[ LONG-TERM OUTCOMES: DATA UNAVAILABLE ]",
            self.font_small,
            (120, 130, 145) if is_a_dimmed else COLOR_TEXT_PRIMARY,
            (box_a.centerx, box_a.top + 18),
            center=True,
        )
        self._draw_text(
            "Familiar Track • Predictable • Fixed Ceiling",
            self.font_mono_small,
            (90, 100, 115) if is_a_dimmed else (150, 165, 190),
            (box_a.centerx, box_a.top + 42),
            center=True,
        )

        # -------------------------------------------------------------
        # Path B (Key 2, Right Branch): Dashed amber path -> Dark Fog Box
        # -------------------------------------------------------------
        is_b_dimmed = (selected_index == 0)
        is_b_active = (selected_index == 1)

        p1_r = (float(cx + 100), float(fork_node_y - 90))
        p2_r = (float(cx + 310), float(fork_node_y - 180))

        pts_b: list[tuple[int, int]] = []
        for step in range(21):
            t = step / 20.0
            bx = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1_r[0] + t ** 2 * p2_r[0]
            by = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1_r[1] + t ** 2 * p2_r[1]
            pts_b.append((int(bx), int(by)))

        if is_b_dimmed:
            b_col = (48, 44, 40)
            b_w = 4
        elif is_b_active:
            # Glowing illuminated branch
            pygame.draw.lines(self.screen, (90, 60, 15), False, pts_b, 16)
            b_col = COLOR_TIMER_AMBER
            b_w = 6
        else:
            pygame.draw.lines(self.screen, (34, 26, 16), False, pts_b, 12)
            b_col = COLOR_TIMER_AMBER
            b_w = 5

        # Dashed curve rendering (draw every other segment)
        for d_i in range(0, len(pts_b) - 1, 2):
            pygame.draw.line(self.screen, b_col, pts_b[d_i], pts_b[d_i + 1], b_w)

        # Path B Label
        mid_b = pts_b[10]
        self._draw_text(
            "UNCHARTED TRAJECTORY",
            self.font_small,
            (100, 90, 80) if is_b_dimmed else COLOR_TIMER_AMBER,
            (mid_b[0] + 20, mid_b[1] + 16),
            center=True,
        )

        # Dark Fog / Gradient Overlay around Path B destination
        fog_w = 380
        fog_h = 110
        fog_surf = pygame.Surface((fog_w, fog_h), pygame.SRCALPHA)
        # Concentric dark fog clouds
        for fog_r, fog_alpha in [(160, 160), (120, 190), (80, 220), (40, 240)]:
            pygame.draw.ellipse(fog_surf, (8, 10, 16, fog_alpha), (fog_w // 2 - fog_r, fog_h // 2 - fog_r // 2, fog_r * 2, fog_r))
        self.screen.blit(fog_surf, (cx + 150, fork_node_y - 235))

        # Terminal Box B inside fog (expanded to 380px to contain subtitle cleanly)
        box_b = pygame.Rect(cx + 170, fork_node_y - 215, 380, 68)
        box_b_border = (50, 45, 40) if is_b_dimmed else (COLOR_TIMER_AMBER if is_b_active else (180, 130, 25))
        box_b_bg = (18, 16, 14) if is_b_dimmed else ((36, 26, 16) if is_b_active else (28, 22, 16))
        self._draw_card(box_b, border_color=box_b_border, bg_color=box_b_bg)

        self._draw_text(
            "[ SUPPORT STRUCTURE: UNDER REVIEW ]",
            self.font_small,
            (120, 110, 100) if is_b_dimmed else COLOR_TIMER_AMBER,
            (box_b.centerx, box_b.top + 18),
            center=True,
        )
        self._draw_text(
            "Uncharted • High Volatility • Zero Guarantees",
            self.font_mono_small,
            (90, 85, 80) if is_b_dimmed else (200, 170, 130),
            (box_b.centerx, box_b.top + 42),
            center=True,
        )

        # 4. Decision Options Cards at Bottom
        card_y = self.height - 130 + oy
        card_h = 95
        card_w = 560

        # Option 1: Established Track
        r1 = pygame.Rect(cx - card_w - 15, card_y, card_w, card_h)
        b1_col = COLOR_TIMER_GREEN if selected_index == 0 else (COLOR_ACCENT_CYAN if selected_index is None else (45, 55, 75))
        bg1_col = (20, 38, 45) if selected_index == 0 else COLOR_CARD_BG
        self._draw_card(r1, border_color=b1_col, bg_color=bg1_col)

        k1_badge = pygame.Rect(r1.left + 16, r1.centery - 18, 36, 36)
        pygame.draw.rect(self.screen, COLOR_ACCENT_CYAN, k1_badge, border_radius=6)
        self._draw_text("1", self.font_title, (10, 20, 30), k1_badge.center, center=True)

        self._draw_text(
            "Path A: Familiar, Established Track",
            self.font_body,
            COLOR_ACCENT_CYAN if selected_index == 0 else COLOR_TEXT_PRIMARY,
            (k1_badge.right + 14, r1.top + 14),
        )
        sub1_rect = pygame.Rect(k1_badge.right + 14, r1.top + 36, r1.width - 85, 40)
        self._draw_wrapped_text(
            "Predictable progression. Long-term growth potential: [DATA UNAVAILABLE]",
            self.font_small,
            COLOR_TEXT_SECONDARY,
            sub1_rect,
            spacing=2,
            center_v=True,
        )
        tag1 = pygame.Rect(k1_badge.right + 14, r1.bottom - 28, 270, 20)
        pygame.draw.rect(self.screen, (16, 24, 34), tag1, border_radius=4)
        pygame.draw.rect(self.screen, (0, 180, 210), tag1, width=1, border_radius=4)
        self._draw_text("[ PREDICTABLE // UNKNOWN HORIZON ]", self.font_mono_small, COLOR_ACCENT_CYAN, tag1.center, center=True)

        # Option 2: Uncharted Trajectory
        r2 = pygame.Rect(cx + 15, card_y, card_w, card_h)
        b2_col = COLOR_TIMER_GREEN if selected_index == 1 else (COLOR_TIMER_AMBER if selected_index is None else (45, 55, 75))
        bg2_col = (42, 32, 18) if selected_index == 1 else COLOR_CARD_BG
        self._draw_card(r2, border_color=b2_col, bg_color=bg2_col)

        k2_badge = pygame.Rect(r2.left + 16, r2.centery - 18, 36, 36)
        pygame.draw.rect(self.screen, COLOR_TIMER_AMBER, k2_badge, border_radius=6)
        self._draw_text("2", self.font_title, (20, 15, 10), k2_badge.center, center=True)

        self._draw_text(
            "Path B: New, Challenging Path",
            self.font_body,
            COLOR_TIMER_AMBER if selected_index == 1 else COLOR_TEXT_PRIMARY,
            (k2_badge.right + 14, r2.top + 14),
        )
        sub2_rect = pygame.Rect(k2_badge.right + 14, r2.top + 36, r2.width - 85, 40)
        self._draw_wrapped_text(
            "Unpredictable trajectory. Support structure: [UNDER REVIEW]",
            self.font_small,
            COLOR_TEXT_SECONDARY,
            sub2_rect,
            spacing=2,
            center_v=True,
        )
        tag2 = pygame.Rect(k2_badge.right + 14, r2.bottom - 28, 270, 20)
        pygame.draw.rect(self.screen, (30, 22, 14), tag2, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_TIMER_AMBER, tag2, width=1, border_radius=4)
        self._draw_text("[ HIGH VOLATILITY // ZERO GUARANTEE ]", self.font_mono_small, COLOR_TIMER_AMBER, tag2.center, center=True)

        # Bottom Prompt
        self._draw_text(
            "PRESS KEY [1] OR [2] TO COMMIT TO TRAJECTORY PATHWAY",
            self.font_small,
            (130, 140, 165),
            (self.width // 2, self.height - 20),
            center=True,
        )

        return True

    def _draw_skin_notification_stack(
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
        """Render notification_stack simulation skin: minimalist lockscreen notification and 3 draft responses."""
        vx, vy = effects.vibration_offset
        jx, jy = effects.jitter_offset
        ox = vx + jx
        oy = vy + jy

        cx = self.width // 2 + ox

        # 1. Lockscreen Top Status Bar
        self._draw_text(
            "23:42",
            self.font_title,
            (210, 220, 240),
            (cx, 106 + oy),
            center=True,
        )
        self._draw_text(
            "Friday, September 19 • Midterm Assessment Period",
            self.font_small,
            (130, 140, 165),
            (cx, 134 + oy),
            center=True,
        )

        # Status icons (Right: Battery + Signal)
        stat_x = self.width - 140 + ox
        stat_y = 106 + oy
        # Battery outline
        pygame.draw.rect(self.screen, (140, 150, 175), (stat_x + 60, stat_y, 22, 12), width=1, border_radius=2)
        pygame.draw.rect(self.screen, COLOR_TIMER_GREEN, (stat_x + 62, stat_y + 2, 14, 8))
        pygame.draw.rect(self.screen, (140, 150, 175), (stat_x + 82, stat_y + 3, 2, 6))
        # Signal bars
        for b_i in range(4):
            bh = 4 + b_i * 3
            pygame.draw.rect(self.screen, (180, 190, 210), (stat_x + 36 + b_i * 5, stat_y + 12 - bh, 3, bh))

        # 2. Centered Sparse Notification Card
        card_w = 840
        card_h = 175
        notif_rect = pygame.Rect(cx - card_w // 2, 156 + oy, card_w, card_h)
        self._draw_card(notif_rect, border_color=(60, 72, 100), bg_color=(20, 24, 38))

        # Card Header: Authority Seal + Sender
        seal_cx = notif_rect.left + 36
        seal_cy = notif_rect.top + 34
        pygame.draw.circle(self.screen, (34, 42, 64), (seal_cx, seal_cy), 18)
        pygame.draw.circle(self.screen, (218, 165, 32), (seal_cx, seal_cy), 18, width=2)
        pygame.draw.circle(self.screen, (218, 165, 32), (seal_cx, seal_cy), 14, width=1)
        star_pts = []
        for p_i in range(10):
            r_pt = 7 if p_i % 2 == 0 else 3.2
            ang = -math.pi / 2 + p_i * (math.pi / 5)
            star_pts.append((seal_cx + int(r_pt * math.cos(ang)), seal_cy + int(r_pt * math.sin(ang))))
        pygame.draw.polygon(self.screen, (218, 165, 32), star_pts)

        self._draw_text(
            "ACADEMIC EVALUATOR / SUPERVISOR",
            self.font_body,
            (240, 245, 255),
            (seal_cx + 28, notif_rect.top + 14),
        )
        self._draw_text(
            "FACULTY PORTAL • CONFIDENTIAL PERFORMANCE NOTICE",
            self.font_mono_small,
            (130, 145, 175),
            (seal_cx + 28, notif_rect.top + 38),
        )
        self._draw_text("Now • Priority Tier 1", self.font_small, COLOR_TIMER_AMBER, (notif_rect.right - 20, notif_rect.top + 26), midright=True)

        # Divider
        pygame.draw.line(self.screen, (38, 46, 68), (notif_rect.left + 20, notif_rect.top + 68), (notif_rect.right - 20, notif_rect.top + 68), 1)

        # Content Message with prominent highlighted "? atypical ?"
        msg_y = notif_rect.top + 84
        prefix = "Your approach throughout this term has been... "
        atypical_str = "? atypical ?"
        suffix = " compared to your peers."

        pref_w = self.font_body.size(prefix)[0]
        atyp_w = self.font_title.size(atypical_str)[0]

        start_text_x = notif_rect.left + 24
        self._draw_text(prefix, self.font_body, (220, 228, 242), (start_text_x, msg_y + 4))

        # Cyan highlighted box for "? atypical ?"
        pill_rect = pygame.Rect(start_text_x + pref_w, msg_y - 2, atyp_w + 16, 36)
        pygame.draw.rect(self.screen, (10, 44, 58), pill_rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_ACCENT_CYAN, pill_rect, width=2, border_radius=6)
        self._draw_text(atypical_str, self.font_title, COLOR_ACCENT_CYAN, pill_rect.center, center=True)

        self._draw_text(suffix, self.font_body, (220, 228, 242), (pill_rect.right + 8, msg_y + 4))

        # Ambiguity Subtext Pill
        amb_tag = pygame.Rect(notif_rect.left + 24, notif_rect.bottom - 36, notif_rect.width - 48, 24)
        pygame.draw.rect(self.screen, (28, 20, 16), amb_tag, border_radius=4)
        pygame.draw.rect(self.screen, (180, 120, 20), amb_tag, width=1, border_radius=4)
        self._draw_text(
            "[ EVALUATOR INTENT UNRESOLVED: COMMENDATION VS. CRITIQUE FULLY INDETERMINATE ]",
            self.font_mono_small,
            COLOR_TIMER_AMBER,
            amb_tag.center,
            center=True,
        )

        # 3. Draft Responses: 3 Stacked Cards
        draft_header_y = notif_rect.bottom + 12
        self._draw_text(
            "SELECT DRAFT RESPONSE TO SUPERVISOR:",
            self.font_small,
            (140, 150, 175),
            (notif_rect.left, draft_header_y),
        )

        drafts = [
            (
                1,
                "Draft 1: Autonomous / Instinctive Orientation",
                '"I\'ve been approaching each task based on my instincts and what made sense to me."',
                "[ AUTONOMOUS ORIENTATION // REJECTS RUBRIC CONSTRAINTS ]",
                COLOR_ACCENT_CYAN,
                (20, 36, 48),
            ),
            (
                2,
                "Draft 2: Methodical / Deliberative Orientation",
                '"I\'ve been carefully considering each step before committing to anything."',
                "[ DELIBERATIVE CAUTION // ADHERES TO COMPLIANT REASONING ]",
                COLOR_TIMER_GREEN,
                (20, 38, 30),
            ),
            (
                3,
                "Draft 3: Critical / Non-Conformist Orientation",
                '"I don\'t think the standard approach was appropriate for what we were being asked to do."',
                "[ DIRECT CHALLENGE // QUESTIONS EVALUATION STANDARD ]",
                (180, 120, 255),
                (36, 22, 48),
            ),
        ]

        cards_start_y = draft_header_y + 22
        d_card_h = 92
        d_gap = 12

        for i, (key, label, quote, tag, accent_col, bg_col) in enumerate(drafts):
            dy = cards_start_y + i * (d_card_h + d_gap)
            d_rect = pygame.Rect(cx - card_w // 2, dy, card_w, d_card_h)

            is_sel = (selected_index == i)
            b_col = accent_col if is_sel else ((60, 70, 95) if selected_index is not None else (40, 48, 68))
            card_bg = bg_col if is_sel else COLOR_CARD_BG
            self._draw_card(d_rect, border_color=b_col, bg_color=card_bg)

            # Key Badge
            k_badge = pygame.Rect(d_rect.left + 14, d_rect.top + 14, 30, 30)
            pygame.draw.rect(self.screen, accent_col, k_badge, border_radius=6)
            self._draw_text(str(key), self.font_title, COLOR_TEXT_PRIMARY, k_badge.center, center=True)

            self._draw_text(label, self.font_body, accent_col if is_sel else COLOR_TEXT_PRIMARY, (k_badge.right + 14, d_rect.top + 10))
            quote_rect = pygame.Rect(k_badge.right + 14, d_rect.top + 34, d_rect.width - 80, 26)
            self._draw_wrapped_text(quote, self.font_small, (220, 228, 240) if is_sel else (170, 180, 200), quote_rect, center_v=True)

            # Bottom tag
            t_rect = pygame.Rect(k_badge.right + 14, d_rect.bottom - 24, 420, 18)
            pygame.draw.rect(self.screen, (16, 20, 30), t_rect, border_radius=3)
            pygame.draw.rect(self.screen, accent_col, t_rect, width=1, border_radius=3)
            self._draw_text(tag, self.font_mono_small, accent_col, t_rect.center, center=True)

            if is_sel:
                self._draw_text("[DISPATCHING DRAFT...]", self.font_mono_small, accent_col, (d_rect.right - 20, d_rect.top + 12), midright=True)

        # Bottom Prompt
        self._draw_text(
            "PRESS KEY [1], [2], OR [3] TO DISPATCH RESPONSE TO SUPERVISOR",
            self.font_small,
            (130, 140, 165),
            (self.width // 2, self.height - 20),
            center=True,
        )

        return True

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
        pygame.draw.rect(self.screen, (16, 20, 32), proj_rect, border_radius=6)
        border_col = (70, 95, 140) if not is_drone_active else (180, 75, 75)
        pygame.draw.rect(self.screen, border_col, proj_rect, width=1, border_radius=6)

        # Subtle projector scanlines
        for ly in range(proj_rect.top + 12, proj_rect.bottom - 8, 14):
            pygame.draw.line(self.screen, (22, 28, 44), (proj_rect.left + 10, ly), (proj_rect.right - 10, ly), 1)

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
            (240, 245, 255),
            (proj_rect.centerx, proj_rect.top + 38),
            center=True,
        )

        # -----------------------------------------------------------------
        # 2. Panel Bench & 3 Expert Evaluators (Grayscale TSST Silhouettes)
        # -----------------------------------------------------------------
        dais_rect = pygame.Rect(120 + jx, 172 + jy, self.width - 240, 108)
        pygame.draw.rect(self.screen, (20, 22, 30), dais_rect, border_radius=4)
        pygame.draw.rect(self.screen, (38, 42, 56), dais_rect, width=1, border_radius=4)

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
            suit_col = (36, 38, 48) if k != 1 else (28, 30, 40)
            pygame.draw.polygon(self.screen, suit_col, torso_pts)

            # Collar and tie
            pygame.draw.polygon(self.screen, (160, 165, 175), [(ex - 9, head_y + 16), (ex + 9, head_y + 16), (ex, head_y + 30)])
            pygame.draw.line(self.screen, (45, 48, 60), (ex, head_y + 24), (ex, head_y + 42), 2)

            # Portrait silhouette head
            pygame.draw.circle(self.screen, (58, 62, 74), (ex, head_y), 18)
            pygame.draw.circle(self.screen, (44, 48, 58), (ex, head_y), 16)

            # Expressionless face: neutral horizontal line mouth (TSST uncontrollability mechanism)
            # Eyes: narrow horizontal neutral slits
            pygame.draw.line(self.screen, (75, 80, 95), (ex - 8, head_y - 2), (ex - 2, head_y - 2), 2)
            pygame.draw.line(self.screen, (75, 80, 95), (ex + 2, head_y - 2), (ex + 8, head_y - 2), 2)
            # Mouth: neutral horizontal line (completely still, unresponsive)
            pygame.draw.line(self.screen, (80, 85, 102), (ex - 7, head_y + 7), (ex + 7, head_y + 7), 2)

        # Imposing Evaluation Bench (Wood / Slate surface)
        bench_top_y = 244 + jy
        bench_rect = pygame.Rect(120 + jx, bench_top_y, self.width - 240, 36)
        pygame.draw.rect(self.screen, (34, 30, 40), bench_rect, border_radius=3)
        pygame.draw.rect(self.screen, (60, 56, 72), bench_rect, width=1, border_radius=3)
        pygame.draw.line(self.screen, (90, 84, 105), (bench_rect.left, bench_top_y + 1), (bench_rect.right, bench_top_y + 1), 2)

        # Nameplates & dossiers on bench
        for k in range(3):
            ex = eval_xs[k]
            pygame.draw.rect(self.screen, (175, 165, 140), (ex - 70, bench_top_y + 6, 20, 16), border_radius=2)
            plate_rect = pygame.Rect(ex - 42, bench_top_y + 7, 130, 20)
            pygame.draw.rect(self.screen, (24, 22, 30), plate_rect, border_radius=2)
            pygame.draw.rect(self.screen, (80, 75, 95), plate_rect, width=1, border_radius=2)
            title, role = eval_roles[k]
            self._draw_text(title, self.font_small, (190, 185, 200), (plate_rect.centerx, plate_rect.centery), center=True)

        # TSST unresponsiveness label
        self._draw_text(
            "PANEL STATUS: UNRESPONSIVE (TSST PROTOCOL) • ZERO NON-VERBAL FEEDBACK",
            self.font_small,
            (105, 110, 125),
            (self.width // 2 + jx, bench_top_y + 44),
            center=True,
        )

        # -----------------------------------------------------------------
        # 3. Podium Defense Terminal (Speaker's Perspective) & Options
        # -----------------------------------------------------------------
        podium_y = 302 + jy
        podium_banner = pygame.Rect(70 + jx, podium_y, self.width - 140, 32)
        pygame.draw.rect(self.screen, (22, 26, 36), podium_banner, border_radius=4)
        pygame.draw.rect(self.screen, (45, 54, 75), podium_banner, width=1, border_radius=4)

        # Microphone live cue
        pygame.draw.circle(self.screen, COLOR_TIMER_GREEN, (podium_banner.left + 14, podium_banner.centery), 4)
        self._draw_text("PODIUM MIC: LIVE", self.font_small, COLOR_TIMER_GREEN, (podium_banner.left + 24, podium_banner.centery), midleft=True)
        self._draw_text("DEFENSE TERMINAL CONSOLE — SELECT STRATEGY", self.font_small, COLOR_ACCENT_CYAN, (podium_banner.centerx, podium_banner.centery), center=True)
        if is_drone_active:
            dt_str = "[ DIEGETIC TENSION ACTIVE ]"
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

            if is_sel:
                bg_col = (32, 45, 70)
                border_col = COLOR_ACCENT_CYAN
                border_w = 2
            else:
                bg_col = (20, 24, 34)
                border_col = (45, 50, 68) if selected_index is not None else (55, 62, 85)
                border_w = 1

            pygame.draw.rect(self.screen, bg_col, rect, border_radius=6)
            pygame.draw.rect(self.screen, border_col, rect, width=border_w, border_radius=6)

            # Key badge [1], [2], [3]
            key_rect = pygame.Rect(rect.left + 14, rect.centery - 18, 36, 36)
            badge_bg = COLOR_ACCENT_CYAN if is_sel else COLOR_ACCENT_INDIGO
            pygame.draw.rect(self.screen, badge_bg, key_rect, border_radius=6)
            self._draw_text(str(opt.key), self.font_title, COLOR_TEXT_PRIMARY, key_rect.center, center=True)

            # Tactical stance tag & option text
            tag_str = stance_tags[i] if i < len(stance_tags) else ""
            self._draw_text(tag_str, self.font_small, COLOR_ACCENT_CYAN if is_sel else COLOR_TEXT_SECONDARY, (key_rect.right + 14, rect.top + 9))
            opt_rect = pygame.Rect(key_rect.right + 14, rect.top + 31, rect.width - 210, 30)
            self._draw_wrapped_text(opt.text, self.font_body, COLOR_TEXT_PRIMARY, opt_rect, center_v=True)

            # Selected indicator tag
            if is_sel:
                sel_badge = pygame.Rect(rect.right - 120, rect.centery - 13, 104, 26)
                pygame.draw.rect(self.screen, (0, 180, 216), sel_badge, border_radius=4)
                self._draw_text("SELECTED", self.font_small, (10, 20, 30), sel_badge.center, center=True)

        # -----------------------------------------------------------------
        # 4. Active Deception Composure Bar (Bottom Biofeedback Bar)
        # -----------------------------------------------------------------
        if scenario.has_deception_metric:
            comp_bar_y = start_y + len(opts) * (card_h + gap) + 16
            comp_val = composure_fraction if composure_fraction is not None else 1.0
            self.draw_composure_bar(
                comp_val,
                (70 + jx, comp_bar_y),
                width=self.width - 140,
                is_drone_active=is_drone_active,
            )

        # Bottom prompt
        self._draw_text(
            "PRESS KEY [1], [2], OR [3] TO DELIVER ORAL DEFENSE TO THE PANEL",
            self.font_small,
            (120, 128, 145),
            (self.width // 2, self.height - 18),
            center=True,
        )

        return True

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
        pygame.draw.line(self.screen, (45, 50, 68), (inst_x - 45, inst_base_y), (inst_x + 65, inst_base_y), 2)

        # Instructor Suit / Jacket Silhouette
        torso_pts = [
            (inst_x - 26, inst_base_y),
            (inst_x + 26, inst_base_y),
            (inst_x + 20, inst_base_y - 110),
            (inst_x - 20, inst_base_y - 110),
        ]
        pygame.draw.polygon(self.screen, (42, 48, 64), torso_pts)
        # Collar and tie
        pygame.draw.polygon(self.screen, (150, 155, 170), [(inst_x - 7, inst_base_y - 110), (inst_x + 7, inst_base_y - 110), (inst_x, inst_base_y - 96)])
        pygame.draw.line(self.screen, (32, 35, 48), (inst_x, inst_base_y - 96), (inst_x, inst_base_y - 80), 2)

        # Head silhouette
        head_cy = inst_base_y - 132
        pygame.draw.circle(self.screen, (56, 64, 82), (inst_x, head_cy), 17)
        pygame.draw.circle(self.screen, (40, 46, 60), (inst_x, head_cy), 15)

        # Authoritative Gesturing Arm: extended toward the right / participant
        arm_start = (inst_x + 18, inst_base_y - 100)
        arm_elbow = (inst_x + 55, inst_base_y - 88)
        arm_hand = (inst_x + 102, inst_base_y - 96)
        pygame.draw.line(self.screen, (42, 48, 64), arm_start, arm_elbow, 6)
        pygame.draw.line(self.screen, (42, 48, 64), arm_elbow, arm_hand, 5)
        # Pointing hand
        pygame.draw.circle(self.screen, (60, 68, 86), arm_hand, 5)
        pygame.draw.line(self.screen, (60, 68, 86), arm_hand, (arm_hand[0] + 12, arm_hand[1] - 3), 2)

        # Authority tag
        self._draw_text(
            "COURSE INSTRUCTOR",
            self.font_small,
            (170, 175, 195),
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
        bubble_bg = (30, 20, 24) if is_drone_active else (26, 22, 28)
        bubble_border = (195, 65, 65) if is_drone_active else (165, 75, 75)
        pygame.draw.polygon(self.screen, bubble_bg, pointer_pts)
        pygame.draw.polygon(self.screen, bubble_border, pointer_pts, width=1)
        pygame.draw.rect(self.screen, bubble_bg, bubble_rect, border_radius=6)
        pygame.draw.rect(self.screen, bubble_border, bubble_rect, width=1, border_radius=6)

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
            (250, 245, 245),
            (bubble_rect.centerx, bubble_rect.top + 38),
            center=True,
        )

        # -----------------------------------------------------------------
        # 3. Audience Rows (Seated Silhouette Heads Facing Participant)
        # -----------------------------------------------------------------
        row2_y = 208 + jy
        row2_bench = pygame.Rect(210 + jx, row2_y + 12, self.width - 280, 6)
        pygame.draw.rect(self.screen, (30, 34, 46), row2_bench, border_radius=2)
        row2_xs = [245 + k * 86 + jx for k in range(11)]
        for sx in row2_xs:
            pygame.draw.polygon(
                self.screen,
                (32, 36, 48),
                [(sx - 18, row2_y + 14), (sx + 18, row2_y + 14), (sx + 12, row2_y - 4), (sx - 12, row2_y - 4)],
            )
            pygame.draw.circle(self.screen, (40, 46, 60), (sx, row2_y - 12), 11)
            pygame.draw.circle(self.screen, (70, 78, 98), (sx - 4, row2_y - 13), 2)
            pygame.draw.circle(self.screen, (70, 78, 98), (sx + 4, row2_y - 13), 2)

        # Row 1 (Front row, closer, larger)
        row1_y = 254 + jy
        row1_bench = pygame.Rect(190 + jx, row1_y + 14, self.width - 260, 8)
        pygame.draw.rect(self.screen, (40, 45, 60), row1_bench, border_radius=2)
        pygame.draw.line(self.screen, (60, 68, 88), (row1_bench.left, row1_y + 14), (row1_bench.right, row1_y + 14), 1)

        row1_xs = [230 + k * 110 + jx for k in range(9)]
        for sx in row1_xs:
            pygame.draw.polygon(
                self.screen,
                (45, 50, 66),
                [(sx - 24, row1_y + 16), (sx + 24, row1_y + 16), (sx + 16, row1_y - 6), (sx - 16, row1_y - 6)],
            )
            pygame.draw.circle(self.screen, (55, 62, 80), (sx, row1_y - 16), 14)
            pygame.draw.circle(self.screen, (90, 100, 125), (sx - 5, row1_y - 17), 2)
            pygame.draw.circle(self.screen, (90, 100, 125), (sx + 5, row1_y - 17), 2)
            pygame.draw.rect(self.screen, (65, 72, 92), (sx - 12, row1_y + 8, 24, 6), border_radius=1)

        self._draw_text(
            "COHORT AUDIENCE: 28 PEERS OBSERVING IN SILENCE • EVALUATING YOUR DEFENSE",
            self.font_small,
            (115, 122, 140),
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

            if is_sel:
                bg_col = (32, 45, 70)
                border_col = COLOR_ACCENT_CYAN
                border_w = 2
            else:
                bg_col = (20, 24, 34)
                border_col = (45, 50, 68) if selected_index is not None else (55, 62, 85)
                border_w = 1

            pygame.draw.rect(self.screen, bg_col, rect, border_radius=6)
            pygame.draw.rect(self.screen, border_col, rect, width=border_w, border_radius=6)

            # Key badge [1], [2], [3]
            key_rect = pygame.Rect(rect.left + 14, rect.centery - 18, 36, 36)
            badge_bg = COLOR_ACCENT_CYAN if is_sel else COLOR_ACCENT_INDIGO
            pygame.draw.rect(self.screen, badge_bg, key_rect, border_radius=6)
            self._draw_text(str(opt.key), self.font_title, COLOR_TEXT_PRIMARY, key_rect.center, center=True)

            # Posture tag & option text
            tag_str = posture_tags[i] if i < len(posture_tags) else ""
            self._draw_text(tag_str, self.font_small, COLOR_ACCENT_CYAN if is_sel else COLOR_TEXT_SECONDARY, (key_rect.right + 14, rect.top + 9))
            opt_rect = pygame.Rect(key_rect.right + 14, rect.top + 31, rect.width - 210, 30)
            self._draw_wrapped_text(opt.text, self.font_body, COLOR_TEXT_PRIMARY, opt_rect, center_v=True)

            # Selected indicator tag
            if is_sel:
                sel_badge = pygame.Rect(rect.right - 120, rect.centery - 13, 104, 26)
                pygame.draw.rect(self.screen, (0, 180, 216), sel_badge, border_radius=4)
                self._draw_text("SELECTED", self.font_small, (10, 20, 30), sel_badge.center, center=True)

        # -----------------------------------------------------------------
        # 5. Active Deception Composure Bar (Bottom Biofeedback Bar)
        # -----------------------------------------------------------------
        if scenario.has_deception_metric:
            comp_bar_y = start_y + len(opts) * (card_h + gap) + 16
            comp_val = composure_fraction if composure_fraction is not None else 1.0
            self.draw_composure_bar(
                comp_val,
                (70 + jx, comp_bar_y),
                width=self.width - 140,
                is_drone_active=is_drone_active,
            )

        # Bottom prompt
        self._draw_text(
            "PRESS KEY [1], [2], OR [3] TO DELIVER RESPONSE TO INSTRUCTOR AND COHORT",
            self.font_small,
            (120, 128, 145),
            (self.width // 2, self.height - 18),
            center=True,
        )

        return True

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

    def draw_composure_bar(
        self,
        fraction: float,
        pos: tuple[int, int],
        width: int | None = None,
        is_drone_active: bool = False,
    ) -> None:
        """Render MPU6050 biofeedback deception composure bar with smooth color transition and telemetry."""
        frac = max(0.0, min(1.0, fraction))
        x, y = pos
        bar_w = width if width is not None else (self.width - 100)
        panel_rect = pygame.Rect(x, y - 18, bar_w, 68)

        # Panel card background
        pygame.draw.rect(self.screen, (18, 22, 32), panel_rect, border_radius=6)
        border_col = (45, 54, 75) if not is_drone_active else (140, 50, 50)
        pygame.draw.rect(self.screen, border_col, panel_rect, width=1, border_radius=6)

        # Header / Label
        self._draw_text("Physiological Composure Analysis: Active", self.font_small, COLOR_ACCENT_CYAN, (x + 14, panel_rect.top + 10), midleft=True)

        # Dynamic smooth color transition from green -> amber -> red
        if frac > 0.6:
            t = (frac - 0.6) / 0.4
            col = (
                int(COLOR_TIMER_AMBER[0] * (1.0 - t) + COLOR_TIMER_GREEN[0] * t),
                int(COLOR_TIMER_AMBER[1] * (1.0 - t) + COLOR_TIMER_GREEN[1] * t),
                int(COLOR_TIMER_AMBER[2] * (1.0 - t) + COLOR_TIMER_GREEN[2] * t),
            )
            status_text = f"STABILITY: {int(frac * 100)}% | SMR: NOMINAL (NO TREMOR)"
            status_col = COLOR_TIMER_GREEN
        elif frac > 0.3:
            t = (frac - 0.3) / 0.3
            col = (
                int(COLOR_TIMER_RED[0] * (1.0 - t) + COLOR_TIMER_AMBER[0] * t),
                int(COLOR_TIMER_RED[1] * (1.0 - t) + COLOR_TIMER_AMBER[1] * t),
                int(COLOR_TIMER_RED[2] * (1.0 - t) + COLOR_TIMER_AMBER[2] * t),
            )
            status_text = f"STABILITY: {int(frac * 100)}% | SMR ELEVATION (+1.5σ)"
            status_col = COLOR_TIMER_AMBER
        else:
            col = COLOR_TIMER_RED
            status_text = f"STABILITY: {int(frac * 100)}% | AROUSAL: CRITICAL (+2.8σ)"
            status_col = COLOR_TIMER_RED

        self._draw_text(status_text, self.font_small, status_col, (panel_rect.right - 14, panel_rect.top + 10), midright=True)

        # Track and Bar
        track_rect = pygame.Rect(x + 14, panel_rect.top + 26, bar_w - 28, 14)
        pygame.draw.rect(self.screen, (32, 36, 48), track_rect, border_radius=4)
        fill_w = int(track_rect.width * frac)
        if fill_w > 0:
            pygame.draw.rect(self.screen, col, (track_rect.left, track_rect.top, fill_w, track_rect.height), border_radius=4)

        # Telemetry info line
        sub_text = "HARDWARE TELEMETRY: ESP32 / MPU-6050 RESTING TREMOR METRIC (CALIBRATED μ + 1.5σ)"
        self._draw_text(sub_text, self.font_mono_small, (110, 118, 135), (x + 14, panel_rect.top + 50), midleft=True)

        if is_drone_active:
            drone_tag = "[ DIEGETIC TENSION DRONE ENGAGED ]"
            self._draw_text(drone_tag, self.font_mono_small, COLOR_TIMER_AMBER if frac > 0.3 else COLOR_TIMER_RED, (panel_rect.right - 14, panel_rect.top + 50), midright=True)


    def draw_question_popup(self, scenario: Scenario) -> None:
        """Render modal overlay displaying the scenario briefing, question, and context."""
        # Dim background with semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((8, 12, 20, 220))
        self.screen.blit(overlay, (0, 0))

        # Modal Card
        card_w = 980
        card_h = 490
        card_rect = pygame.Rect(self.width // 2 - card_w // 2, self.height // 2 - card_h // 2, card_w, card_h)
        self._draw_card(card_rect, border_color=COLOR_ACCENT_CYAN, bg_color=(16, 20, 32))

        # Header: Domain tag + Active Hold Notice
        self._draw_text(scenario.domain_id.value.replace("_", " ").upper(), self.font_small, COLOR_ACCENT_CYAN, (card_rect.left + 40, card_rect.top + 24))

        rel_notice = "[ HOLDING TAB / Q — RELEASE TO RETURN ]"
        rn_w = self.font_mono_small.size(rel_notice)[0]
        self._draw_text(rel_notice, self.font_mono_small, COLOR_TIMER_AMBER, (card_rect.right - 40 - rn_w, card_rect.top + 24))

        # Title
        title_font = self.font_hero if self.font_hero.size(scenario.title)[0] <= card_rect.width - 80 else self.font_title
        self._draw_text(scenario.title, title_font, COLOR_TEXT_PRIMARY, (card_rect.left + 40, card_rect.top + 48))

        # Paradigm tag
        paradigm_rect = pygame.Rect(card_rect.left + 40, card_rect.top + 98, card_rect.width - 80, 26)
        self._draw_wrapped_text(f"Paradigm: {scenario.paradigm}", self.font_small, COLOR_TEXT_SECONDARY, paradigm_rect, spacing=2)

        # Divider
        pygame.draw.line(self.screen, (40, 50, 72), (card_rect.left + 35, card_rect.top + 130), (card_rect.right - 35, card_rect.top + 130), 1)

        # Question / Priming Section
        self._draw_text("SCENARIO QUESTION & BRIEFING:", self.font_small, COLOR_ACCENT_CYAN, (card_rect.left + 40, card_rect.top + 144))
        briefing_rect = pygame.Rect(card_rect.left + 40, card_rect.top + 170, card_rect.width - 80, 160)
        self._draw_wrapped_text(scenario.priming_text, self.font_body, COLOR_TEXT_PRIMARY, briefing_rect, spacing=8)

        # Options Summary Box (if scenario has options)
        if scenario.options and scenario.scenario_type not in (ScenarioType.MIST_ARITHMETIC,):
            opt_box = pygame.Rect(card_rect.left + 40, card_rect.top + 345, card_rect.width - 80, 80)
            pygame.draw.rect(self.screen, (22, 26, 40), opt_box, border_radius=6)
            pygame.draw.rect(self.screen, (45, 55, 80), opt_box, width=1, border_radius=6)
            self._draw_text("AVAILABLE CHOICES:", self.font_mono_small, (140, 150, 175), (opt_box.left + 16, opt_box.top + 8))
            opt_summary = "     ".join(f"[{opt.key}] {opt.text}" for opt in scenario.options)
            opt_summary_rect = pygame.Rect(opt_box.left + 16, opt_box.top + 28, opt_box.width - 32, 44)
            self._draw_wrapped_text(opt_summary, self.font_small, (220, 230, 245), opt_summary_rect, spacing=2)

        # Bottom release hint
        self._draw_text("Release [TAB] or [Q] to resume scenario decision", self.font_small, (130, 140, 165), (self.width // 2, card_rect.bottom - 24), center=True)

    def draw_post_wait(self, text: str, elapsed_fraction: float) -> None:
        """Render delay wait screen for Future Uncertainty and Impulsivity domains."""
        self.screen.fill(COLOR_BG)

        # Check if this is the document_workspace delay wait animation
        if "reviewing" in text.lower() or "changes" in text.lower():
            # 1. Render Document Workspace background
            win_w = 920
            win_h = 440
            win_rect = pygame.Rect(self.width // 2 - win_w // 2, 70, win_w, win_h)

            pygame.draw.rect(self.screen, (18, 20, 28), win_rect, border_radius=8)
            pygame.draw.rect(self.screen, (48, 54, 76), win_rect, width=2, border_radius=8)

            # Title bar
            hdr_rect = pygame.Rect(win_rect.left, win_rect.top, win_w, 36)
            pygame.draw.rect(self.screen, (26, 30, 44), hdr_rect, border_top_left_radius=8, border_top_right_radius=8)
            self._draw_text("Term_Paper_Final_Draft_v4.docx — Automated Assessment", self.font_small, COLOR_TEXT_PRIMARY, (win_rect.centerx, hdr_rect.centery), center=True)

            # Document sheet canvas
            canvas_rect = pygame.Rect(win_rect.left + 24, hdr_rect.bottom + 16, win_w - 48, win_h - 80)
            pygame.draw.rect(self.screen, (240, 242, 246), canvas_rect, border_radius=4)

            # Simulated text lines on canvas
            margin_x = canvas_rect.left + 45
            margin_w = canvas_rect.width - 90
            for line_idx in range(16):
                ly = canvas_rect.top + 20 + line_idx * 18
                lw = int(margin_w * (0.92 if line_idx % 4 != 3 else 0.55))
                pygame.draw.rect(self.screen, (190, 195, 206), (margin_x, ly, lw, 7), border_radius=2)

            # 2. Animated Document Scanner Line moving vertically over the text
            scan_cycle = (elapsed_fraction * 15.0 / 2.5) % 1.0
            scan_y = canvas_rect.top + int(scan_cycle * canvas_rect.height)
            # Laser beam line
            pygame.draw.line(self.screen, COLOR_ACCENT_CYAN, (canvas_rect.left, scan_y), (canvas_rect.right, scan_y), 3)
            # Laser glow lines
            pygame.draw.line(self.screen, (160, 240, 255), (canvas_rect.left, scan_y - 1), (canvas_rect.right, scan_y - 1), 1)
            pygame.draw.line(self.screen, (160, 240, 255), (canvas_rect.left, scan_y + 1), (canvas_rect.right, scan_y + 1), 1)

            # 3. Central Analysis Engine Modal Card
            modal_w = 640
            modal_h = 190
            modal_rect = pygame.Rect(self.width // 2 - modal_w // 2, self.height // 2 - 75, modal_w, modal_h)
            self._draw_card(modal_rect, border_color=COLOR_ACCENT_CYAN, bg_color=(18, 22, 34))

            # 4. Slow Uncalibrated Spinning Progress Ring
            ring_cx = modal_rect.left + 55
            ring_cy = modal_rect.top + 65
            ring_r = 26
            pygame.draw.circle(self.screen, (36, 44, 64), (ring_cx, ring_cy), ring_r, width=3)
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

            self._draw_text("Please remain still during analysis.", self.font_small, (130, 140, 165), (self.width // 2, self.height - 40), center=True)
            return

        # Check if this is the fork_map delay wait animation (Scenario A)
        elif "synthesizing" in text.lower() or "projections" in text.lower() or "crossroads" in text.lower() or "selection" in text.lower():
            # 1. Render Fork Map scene in post-decision suspension
            cx = self.width // 2
            fork_node_y = 380
            trunk_bottom_y = 480

            # Background grid lines
            for gy in range(80, 680, 60):
                pygame.draw.line(self.screen, (16, 20, 30), (50, gy), (self.width - 50, gy), 1)

            # Stem
            stem_rect = pygame.Rect(cx - 18, fork_node_y, 36, trunk_bottom_y - fork_node_y)
            pygame.draw.rect(self.screen, (22, 26, 38), stem_rect)
            pygame.draw.line(self.screen, (50, 60, 85), (stem_rect.left, stem_rect.top), (stem_rect.left, stem_rect.bottom), 2)
            pygame.draw.line(self.screen, (50, 60, 85), (stem_rect.right, stem_rect.top), (stem_rect.right, stem_rect.bottom), 2)

            # Fork junction
            pygame.draw.circle(self.screen, (30, 36, 52), (cx, fork_node_y), 20)
            pygame.draw.circle(self.screen, (70, 85, 115), (cx, fork_node_y), 20, width=2)

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
                pygame.draw.lines(self.screen, (0, 90, 120), False, pts_a, 16)
                pygame.draw.lines(self.screen, COLOR_ACCENT_CYAN, False, pts_a, 6)
                pygame.draw.lines(self.screen, (40, 44, 52), False, pts_b, 4)
            else:
                # Path B illuminated, Path A dimmed
                pygame.draw.lines(self.screen, (40, 44, 52), False, pts_a, 4)
                pygame.draw.lines(self.screen, (90, 60, 15), False, pts_b, 16)
                for d_i in range(0, len(pts_b) - 1, 2):
                    pygame.draw.line(self.screen, COLOR_TIMER_AMBER, pts_b[d_i], pts_b[d_i + 1], 6)

            # Accelerated Compass Rose at top right
            comp_angle = (elapsed_fraction * 360.0 * 8.0) % 360.0
            self._draw_compass((self.width - 95, 114), 34, comp_angle)
            self._draw_text("[ COMPASS SPINNING ]", self.font_mono_small, COLOR_TIMER_RED, (self.width - 95, 162), center=True)

            # Central Post-Decision Suspension Modal Card
            modal_w = 740
            modal_h = 220
            modal_rect = pygame.Rect(self.width // 2 - modal_w // 2, self.height // 2 - 80, modal_w, modal_h)
            self._draw_card(modal_rect, border_color=COLOR_ACCENT_CYAN, bg_color=(16, 22, 34))

            # Spinning Synthesis Arc
            ring_cx = modal_rect.left + 60
            ring_cy = modal_rect.top + 70
            ring_r = 28
            pygame.draw.circle(self.screen, (35, 45, 68), (ring_cx, ring_cy), ring_r, width=3)
            arc_angle = (elapsed_fraction * 360.0 * 4.0) % 360.0
            arc_rect = pygame.Rect(ring_cx - ring_r, ring_cy - ring_r, ring_r * 2, ring_r * 2)
            pygame.draw.arc(self.screen, COLOR_ACCENT_CYAN, arc_rect, math.radians(arc_angle), math.radians(arc_angle + 120), 4)

            self._draw_text("Synthesizing outcome projections...", self.font_title, COLOR_TEXT_PRIMARY, (ring_cx + 46, ring_cy - 16))
            self._draw_text("Trajectory pathway locked • 12-second algorithmic projection in progress", self.font_small, COLOR_ACCENT_CYAN, (ring_cx + 46, ring_cy + 18))

            # Complete outcome ambiguity callout
            susp_box = pygame.Rect(modal_rect.left + 30, modal_rect.bottom - 65, modal_w - 60, 36)
            pygame.draw.rect(self.screen, (28, 22, 16), susp_box, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_TIMER_AMBER, susp_box, width=1, border_radius=6)
            self._draw_text("[ COMPLETE OUTCOME AMBIGUITY MAINTAINED: ZERO FEEDBACK GRANTED ]", self.font_small, COLOR_TIMER_AMBER, susp_box.center, center=True)

            self._draw_text("Please remain still during trajectory synthesis.", self.font_small, (130, 140, 165), (self.width // 2, self.height - 35), center=True)
            return

        # Check if this is the notification_stack delay wait animation (Scenario B)
        elif "recalculating" in text.lower() or "parameters" in text.lower() or "assessment" in text.lower():
            # 1. Render Lockscreen background
            cx = self.width // 2
            self._draw_text("23:42", self.font_title, (140, 150, 175), (cx, 84), center=True)
            self._draw_text("Friday, September 19 • Midterm Assessment Period", self.font_small, (90, 100, 120), (cx, 114), center=True)

            # Dimmed notification card in background
            card_w = 840
            card_h = 140
            notif_rect = pygame.Rect(cx - card_w // 2, 140, card_w, card_h)
            self._draw_card(notif_rect, border_color=(40, 48, 65), bg_color=(16, 18, 28))
            self._draw_text("ACADEMIC EVALUATOR / SUPERVISOR", self.font_body, (150, 160, 185), (notif_rect.left + 24, notif_rect.top + 16))
            self._draw_text("Your methodology throughout this term has been... [? atypical ?] compared to your peers.", self.font_small, (120, 130, 150), (notif_rect.left + 24, notif_rect.top + 46))
            self._draw_text("[Draft Response Dispatched • Pending Committee Review]", self.font_mono_small, (100, 115, 135), (notif_rect.left + 24, notif_rect.bottom - 28))

            # Central Recalculation Modal
            modal_w = 740
            modal_h = 220
            modal_rect = pygame.Rect(cx - modal_w // 2, self.height // 2 - 50, modal_w, modal_h)
            self._draw_card(modal_rect, border_color=COLOR_ACCENT_CYAN, bg_color=(18, 24, 36))

            # Progress Ring (10s progress ring)
            ring_cx = modal_rect.left + 60
            ring_cy = modal_rect.top + 70
            ring_r = 28
            pygame.draw.circle(self.screen, (35, 45, 68), (ring_cx, ring_cy), ring_r, width=3)
            ring_angle = (elapsed_fraction * 360.0 * 5.0) % 360.0
            arc_rect = pygame.Rect(ring_cx - ring_r, ring_cy - ring_r, ring_r * 2, ring_r * 2)
            pygame.draw.arc(self.screen, COLOR_ACCENT_CYAN, arc_rect, math.radians(ring_angle), math.radians(ring_angle + 140), 4)

            self._draw_text("Recalculating assessment parameters...", self.font_title, COLOR_TEXT_PRIMARY, (ring_cx + 46, ring_cy - 16))
            self._draw_text("Evaluation committee integrating response into cohort metric baseline", self.font_small, COLOR_ACCENT_CYAN, (ring_cx + 46, ring_cy + 18))

            # Outcome embargo callout (no feedback revealed)
            emb_box = pygame.Rect(modal_rect.left + 30, modal_rect.bottom - 65, modal_w - 60, 36)
            pygame.draw.rect(self.screen, (28, 20, 16), emb_box, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_TIMER_AMBER, emb_box, width=1, border_radius=6)
            self._draw_text("[ NO FEEDBACK REVEALED: ASSESSMENT PARAMETERS UNDER EMBARGO ]", self.font_small, COLOR_TIMER_AMBER, emb_box.center, center=True)

            self._draw_text("Please remain still during parameter recalculation.", self.font_small, (130, 140, 165), (self.width // 2, self.height - 35), center=True)
            return

        # Default fallback delay wait screen
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
        card_rect = pygame.Rect(self.width // 2 - 460, self.height // 2 - 165, 920, 330)
        self._draw_card(card_rect, COLOR_ACCENT_INDIGO)

        self._draw_text("CONSEQUENCE RECORDED", self.font_small, COLOR_ACCENT_CYAN, (self.width // 2, card_rect.top + 32), center=True)
        text_rect = pygame.Rect(card_rect.left + 50, card_rect.top + 70, card_rect.width - 100, 165)
        self._draw_wrapped_text(consequence_text, self.font_body, COLOR_TEXT_PRIMARY, text_rect, spacing=6)

        # Display account suspension warning badge if burst occurred
        if "suspended" in consequence_text.lower() or "failure" in consequence_text.lower():
            warn_badge = pygame.Rect(card_rect.left + 50, card_rect.bottom - 50, card_rect.width - 100, 34)
            pygame.draw.rect(self.screen, (48, 14, 20), warn_badge, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_TIMER_RED, warn_badge, width=1, border_radius=6)
            self._draw_text("ACCOUNT SUSPENDED — REACH RESET TO ZERO", self.font_small, COLOR_TIMER_RED, warn_badge.center, center=True)

        # Disperse shatter particles if active or if consequence was collapse
        if "collapsed" in consequence_text.lower() and not self.shatter_effect.particles:
            self.shatter_effect.trigger((self.width // 2, self.height // 2))
        if self.shatter_effect.is_active:
            self.shatter_effect.update(16)
            self.shatter_effect.draw(self.screen)

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
