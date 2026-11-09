"""Simulation skin `reward_crate` for scenario `impulsivity_gratification_a`."""
from __future__ import annotations

import math

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_CARD_BG,
    COLOR_HAIRLINE,
    COLOR_HAIRLINE_SUBTLE,
    COLOR_SEMANTIC_WARNING,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_GREEN,
    COLOR_TIMER_RED,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState

CHEST_BASE = (380, 224)
CHEST_CENTER_Y = 392
Colour = tuple[int, int, int]


class RewardCrateSkin(UIComponents):
    """Renders the `reward_crate` decision skin."""

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
        ox = effects.vibration_offset[0] + effects.jitter_offset[0]
        oy = effects.vibration_offset[1] + effects.jitter_offset[1]
        value = reward_runner.get_current_value()
        instability = reward_runner.get_instability_fraction()
        collapsed = reward_runner.is_collapsed or reward_runner.has_collapsed()
        claimed = reward_runner.is_claimed and not collapsed

        self._draw_text("VAULT 03  •  SECURE REWARD STORAGE", self.font_mono_small, COLOR_TEXT_SECONDARY, (self.MARGIN, self.CONTENT_TOP + 10), midleft=True)
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (self.MARGIN, self.CONTENT_TOP + 24), (self.width - self.MARGIN, self.CONTENT_TOP + 24), 1)
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (0, 478), (self.width, 478), 1)

        # Accent glow runs along the semantic tokens: info cyan -> caution yellow -> Rosso Corsa at collapse risk
        if claimed:
            glow: Colour = COLOR_TIMER_GREEN
        elif instability < 0.8:
            glow = self._mix(COLOR_ACCENT_CYAN, COLOR_TIMER_AMBER, instability / 0.8)
        else:
            glow = self._mix(COLOR_TIMER_AMBER, COLOR_TIMER_RED, (instability - 0.8) / 0.2)

        self._draw_crate_gauge(instability, collapsed, (ox, oy))
        center = (self.width // 2 + ox, CHEST_CENTER_Y + oy)
        if collapsed:
            self._draw_crate_debris(center)
        else:
            pulse = 0.0 if claimed else 0.02 * math.sin(time_remaining_s * 5.0)
            scale = 1.0 + 0.15 * min(1.0, value / 600.0) + pulse
            self._draw_crate_chest(center, scale, instability, glow, 0.0 if claimed else time_remaining_s)
        self._draw_crate_counter(center[0], 140 + oy, value, glow, claimed, collapsed)
        self._update_crate_shatter(center, collapsed)
        self._draw_crate_actions(scenario, value, selected_index, collapsed, (ox, oy))
        self._draw_footer_prompt("PRESS 1 TO CLAIM  •  WAITING NEEDS NO KEY", claimed or collapsed, "THE CHEST HAS COLLAPSED" if collapsed else "RESPONSE RECORDED")
        return True

    def _draw_crate_gauge(self, instability: float, collapsed: bool, offset: tuple[int, int]) -> None:
        """Draw the stability gauge on the left wall: it drains and cracks as the chest becomes unstable."""
        card = pygame.Rect(self.MARGIN + offset[0], 140 + offset[1], 130, 400)
        self._draw_card(card, border_color=COLOR_HAIRLINE, bg_color=COLOR_CARD_BG)
        self._draw_text("CORE STABILITY", self.font_small, COLOR_TEXT_SECONDARY, (card.centerx, card.top + 18), center=True)
        track = pygame.Rect(card.centerx - 18, card.top + 40, 36, 276)
        stability = 0.0 if collapsed else max(0.0, min(1.0, 1.0 - instability))
        colour = COLOR_TIMER_GREEN if stability > 0.6 else (COLOR_TIMER_AMBER if stability > 0.3 else COLOR_TIMER_RED)
        pygame.draw.rect(self.screen, (32, 32, 32), track, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, track, width=1, border_radius=0)
        fill_h = int(track.height * stability)
        if fill_h > 4:
            pygame.draw.rect(self.screen, colour, (track.left + 2, track.bottom - fill_h + 2, track.width - 4, fill_h - 4), border_radius=0)
        for tick in range(1, 5):
            tick_y = track.top + int(track.height * (tick / 5.0))
            pygame.draw.line(self.screen, (62, 62, 62), (track.left + 3, tick_y), (track.right - 3, tick_y), 1)
        if instability > 0.35:
            pygame.draw.lines(self.screen, COLOR_TIMER_RED, False, [(track.left - 3, track.top + 70), (track.left + 12, track.top + 92), (track.left + 7, track.top + 112), (track.left + 25, track.top + 130)], 2)
        if instability > 0.65:
            pygame.draw.lines(self.screen, COLOR_TIMER_RED, False, [(track.right + 3, track.top + 176), (track.left + 18, track.top + 198), (track.left + 22, track.top + 218), (track.left + 6, track.top + 238)], 2)

        if collapsed:
            label = "COLLAPSED"
        else:
            label = "CRITICAL" if instability > 0.75 else ("UNSTABLE" if instability > 0.4 else "SECURE")
        self._draw_text(f"{int(stability * 100)}%", self.font_body, colour, (card.centerx, track.bottom + 22), center=True)
        self._draw_text(label, self.font_small, colour, (card.centerx, track.bottom + 46), center=True)

    def _draw_crate_chest(self, center: tuple[int, int], scale: float, instability: float, glow: Colour, phase_s: float) -> None:
        """Draw the intact chest from scaled rects: it grows with its value and cracks as it destabilises."""
        cx, cy = center
        cw, ch = int(CHEST_BASE[0] * scale), int(CHEST_BASE[1] * scale)
        chest = pygame.Rect(cx - cw // 2, cy - ch // 2, cw, ch)
        pygame.draw.ellipse(self.screen, (14, 14, 14), (chest.left - 15, chest.bottom - 8, cw + 30, 24))
        pygame.draw.rect(self.screen, self._mix(glow, (0, 0, 0), 0.84), chest.inflate(16, 16), border_radius=0)
        pygame.draw.rect(self.screen, (36, 36, 36), chest, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE_SUBTLE, chest, width=1, border_radius=0)

        plate = int(24 * scale)
        for plate_x, plate_y in ((chest.left, chest.top), (chest.right - plate, chest.top), (chest.left, chest.bottom - plate), (chest.right - plate, chest.bottom - plate)):
            pygame.draw.rect(self.screen, (48, 48, 48), (plate_x, plate_y, plate, plate), border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE_SUBTLE, (plate_x, plate_y, plate, plate), width=1, border_radius=0)
            pygame.draw.circle(self.screen, (90, 90, 90), (plate_x + plate // 2, plate_y + plate // 2), 2)

        lid = pygame.Rect(chest.left, chest.top, cw, int(ch * 0.36))
        pygame.draw.rect(self.screen, (40, 40, 40), lid, border_radius=0)
        pygame.draw.rect(self.screen, (70, 70, 70), lid, width=2, border_radius=0)
        seam_y = lid.bottom
        pygame.draw.line(self.screen, (16, 16, 16), (chest.left + 4, seam_y), (chest.right - 4, seam_y), 4)
        pygame.draw.line(self.screen, glow, (chest.left + 26, seam_y), (chest.right - 26, seam_y), 2)

        lock = pygame.Rect(0, 0, int(72 * scale), int(52 * scale))
        lock.center = (cx, seam_y)
        pygame.draw.rect(self.screen, (24, 24, 24), lock, border_radius=0)
        pygame.draw.rect(self.screen, glow, lock, width=1, border_radius=0)
        core_r = max(4, int(11 * scale + math.sin(phase_s * 6.0) * 2.5))
        pygame.draw.circle(self.screen, glow, lock.center, core_r)
        pygame.draw.circle(self.screen, (255, 255, 255), lock.center, max(2, core_r - 4))
        for vent in (-0.27, -0.14, 0.14, 0.27):
            vent_x = cx + int(cw * vent)
            pygame.draw.line(self.screen, (18, 18, 18), (vent_x, seam_y + 28), (vent_x, chest.bottom - 20), 4)
            pygame.draw.line(self.screen, glow, (vent_x, seam_y + 30), (vent_x, chest.bottom - 22), 1)
        self._draw_crate_cracks(cx, seam_y, scale, instability, glow)

    def _draw_crate_cracks(self, cx: int, seam_y: int, scale: float, instability: float, glow: Colour) -> None:
        """Draw the surface cracks that appear one after another as instability passes each threshold."""
        cracks: tuple[tuple[float, tuple[tuple[int, int], ...], bool], ...] = (
            (0.20, ((-28, -8), (-56, -34), (-88, -24), (-124, -52)), False),
            (0.45, ((32, 12), (62, 40), (90, 26), (128, 60)), False),
            (0.70, ((-20, 18), (-46, 50), (-36, 74), (-76, 90)), True),
            (0.85, ((24, -10), (54, -46), (92, -34), (136, -58)), True),
        )
        for threshold, points, severe in cracks:
            if instability > threshold:
                scaled = [(cx + int(px * scale), seam_y + int(py * scale)) for px, py in points]
                pygame.draw.lines(self.screen, COLOR_TIMER_RED if severe else glow, False, scaled, 3 if severe else 2)

    def _draw_crate_debris(self, center: tuple[int, int]) -> None:
        """Draw the collapsed chest as broken halves, with the headline set clear of the wreck so it stays legible."""
        cx, cy = center
        pieces = (
            [(cx - 176, cy + 72), (cx - 22, cy + 72), (cx - 38, cy - 12), (cx - 154, cy - 34)],
            [(cx + 16, cy + 72), (cx + 180, cy + 72), (cx + 164, cy - 26), (cx + 42, cy + 2)],
            [(cx - 126, cy - 78), (cx + 72, cy - 110), (cx + 84, cy - 70), (cx - 114, cy - 38)],
        )
        pygame.draw.ellipse(self.screen, (14, 14, 14), (cx - 200, cy + 62, 400, 26))
        for piece in pieces:
            pygame.draw.polygon(self.screen, (36, 36, 36), piece)
            pygame.draw.polygon(self.screen, COLOR_TIMER_RED, piece, width=1)
        pygame.draw.lines(self.screen, COLOR_TIMER_RED, False, [(cx - 20, cy + 72), (cx - 2, cy + 34), (cx - 14, cy + 10), (cx + 8, cy - 22)], 3)
        self._draw_text("CHEST COLLAPSED", self.font_hero, COLOR_TIMER_RED, (cx, cy + 122), center=True)
        self._draw_text("ALL ACCUMULATED VALUE LOST", self.font_body, COLOR_SEMANTIC_WARNING, (cx, cy + 158), center=True)

    def _draw_crate_counter(self, cx: int, top: int, value: int, glow: Colour, claimed: bool, collapsed: bool) -> None:
        """Draw the value readout above the chest."""
        card = pygame.Rect(cx - 170, top, 340, 76)
        colour = COLOR_TIMER_RED if collapsed else glow
        self._draw_card(card, border_color=colour, bg_color=COLOR_CARD_BG)
        self._draw_text("VALUE SECURED" if claimed else "CHEST VALUE", self.font_small, (160, 160, 160), (cx, card.top + 16), center=True)
        self._draw_text("0" if collapsed else f"{value:,}", self.font_hero, colour, (cx, card.top + 48), center=True)

    def _update_crate_shatter(self, center: tuple[int, int], collapsed: bool) -> None:
        """Fire the radial shatter once on collapse and clear it again for the next run."""
        if collapsed:
            if not self.shatter_effect.is_active and not self.shatter_effect.particles:
                self.shatter_effect.trigger(center)
        elif not self.shatter_effect.is_active and self.shatter_effect.particles:
            self.shatter_effect.particles = []
        if self.shatter_effect.is_active:
            self.shatter_effect.update(16)
            self.shatter_effect.draw(self.screen)

    def _draw_crate_actions(self, scenario: Scenario, value: int, selected_index: int | None, collapsed: bool, offset: tuple[int, int]) -> None:
        """Draw the claim key and the waiting status. Waiting is passive, so it carries no key prompt."""
        labels = [opt.text for opt in scenario.options] + ["CLAIM NOW", "KEEP WAITING"]
        top = 600 + offset[1]
        claim = pygame.Rect(self.width // 2 - 440 + offset[0], top, 430, 78)
        detail = "Nothing is left to claim." if collapsed else f"Secure the current value: {value:,}"
        self._draw_option_card(claim, 1, labels[0], 0, selected_index, detail=detail, accent=COLOR_TIMER_GREEN, plate="CLAIMED", dimmed=collapsed)
        wait = pygame.Rect(self.width // 2 + 10 + offset[0], top, 430, 78)
        style = self._draw_option_frame(wait, 1, selected_index, COLOR_TIMER_AMBER, dimmed=collapsed)
        self._draw_text(labels[1], self.font_body, style.ink, (wait.left + 24, wait.top + 14))
        self._draw_text("The value keeps multiplying. The chest may collapse.", self.font_small, style.sub_ink, (wait.left + 24, wait.top + 44), max_width=wait.width - 40)
