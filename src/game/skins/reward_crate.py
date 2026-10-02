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

        vx, vy = effects.vibration_offset
        jx, jy = effects.jitter_offset
        ox = vx + jx
        oy = vy + jy

        current_val = reward_runner.get_current_value()
        instability = reward_runner.get_instability_fraction()
        is_collapsed = reward_runner.is_collapsed or reward_runner.has_collapsed()

        # Background vault chamber framing
        header_rect = pygame.Rect(50, 95, self.width - 100, 32)
        self._draw_text("CHAMBER: VAULT-03 // SECURE REWARD STORAGE", self.font_small, (140, 140, 140), (header_rect.left + 14, header_rect.centery), midleft=True)
        self._draw_text("EXPONENTIAL VALUE MULTIPLIER", self.font_small, COLOR_ACCENT_CYAN, (header_rect.right - 14, header_rect.centery), midright=True)
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (50, 130), (self.width - 50, 130), 1)

        # Ambient floor horizon line and perspective guide
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (0, 430), (self.width, 430), 1)

        # 1. Left Wall: Vertical Stability Gauge (positioned cleanly below chamber line y=130)
        card_w = 130
        card_left = 50 + ox
        card_top = 146 + oy
        card_h = 334
        gauge_card = pygame.Rect(card_left, card_top, card_w, card_h)
        self._draw_card(gauge_card, border_color=COLOR_HAIRLINE, bg_color=COLOR_CARD_BG)
        self._draw_text("CORE STABILITY", self.font_small, COLOR_TEXT_SECONDARY, (gauge_card.centerx, card_top + 18), center=True)

        # Gauge track centered in card
        gw = 36
        gh = 210
        gx = gauge_card.centerx - gw // 2
        gy = card_top + 38
        stability_frac = max(0.0, min(1.0, 1.0 - instability))

        pygame.draw.rect(self.screen, (32, 32, 32), (gx, gy, gw, gh), border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, (gx, gy, gw, gh), width=1, border_radius=0)

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
            pygame.draw.rect(self.screen, meter_col, fill_rect, border_radius=0)

        # Tick marks
        for tick_idx in range(1, 5):
            ty = gy + int(gh * (tick_idx / 5.0))
            pygame.draw.line(self.screen, (62, 62, 62), (gx + 3, ty), (gx + gw - 3, ty), 1)

        # Cracks on gauge frame when instability increases
        if instability > 0.35:
            crack_pts1 = [(gx - 3, gy + 55), (gx + 12, gy + 72), (gx + 7, gy + 88), (gx + 25, gy + 102)]
            pygame.draw.lines(self.screen, COLOR_TIMER_RED, False, crack_pts1, 2)
        if instability > 0.65:
            crack_pts2 = [(gx + gw + 3, gy + 135), (gx + 18, gy + 152), (gx + 22, gy + 168), (gx + 6, gy + 182)]
            pygame.draw.lines(self.screen, COLOR_TIMER_RED, False, crack_pts2, 2)

        pct_text = f"{int(stability_frac * 100)}%"
        self._draw_text(pct_text, self.font_body, meter_col, (gauge_card.centerx, gy + gh + 16), center=True)

        status_lbl = "CRITICAL" if instability > 0.75 else ("UNSTABLE" if instability > 0.4 else "SECURE")
        status_col = COLOR_TIMER_RED if instability > 0.75 else (COLOR_TIMER_AMBER if instability > 0.4 else COLOR_TIMER_GREEN)
        self._draw_text(status_lbl, self.font_small, status_col, (gauge_card.centerx, gy + gh + 38), center=True)

        # 2. Central Futuristic Supply Chest
        cx = self.width // 2 + ox
        cy = 348 + oy

        # Accent glow runs along the semantic tokens: info cyan -> caution yellow -> Rosso Corsa at collapse risk
        if instability < 0.8:
            glow_color = self._mix(COLOR_ACCENT_CYAN, COLOR_TIMER_AMBER, instability / 0.8)
        else:
            glow_color = self._mix(COLOR_TIMER_AMBER, COLOR_TIMER_RED, (instability - 0.8) / 0.2)
        glow_r, glow_g, glow_b = glow_color

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
            pygame.draw.ellipse(self.screen, (14, 14, 14), shadow_rect)

            # Outer glow aura
            aura_rect = chest_rect.inflate(16, 16)
            aura_color = (max(0, glow_r // 6), max(0, glow_g // 6), max(0, glow_b // 6))
            pygame.draw.rect(self.screen, aura_color, aura_rect, border_radius=0)

            # Chest chassis
            pygame.draw.rect(self.screen, (36, 36, 36), chest_rect, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE_SUBTLE, chest_rect, width=1, border_radius=0)

            # Corner reinforcement plates
            c_size = int(22 * scale)
            for c_x, c_y in [
                (chest_rect.left, chest_rect.top),
                (chest_rect.right - c_size, chest_rect.top),
                (chest_rect.left, chest_rect.bottom - c_size),
                (chest_rect.right - c_size, chest_rect.bottom - c_size),
            ]:
                pygame.draw.rect(self.screen, (48, 48, 48), (c_x, c_y, c_size, c_size), border_radius=0)
                pygame.draw.rect(self.screen, COLOR_HAIRLINE_SUBTLE, (c_x, c_y, c_size, c_size), width=1, border_radius=0)
                pygame.draw.circle(self.screen, (90, 90, 90), (c_x + c_size // 2, c_y + c_size // 2), 2)

            # Lid (upper 36%)
            lid_h = int(ch * 0.36)
            lid_rect = pygame.Rect(chest_rect.left, chest_rect.top, cw, lid_h)
            pygame.draw.rect(self.screen, (39, 39, 39), lid_rect, border_top_left_radius=0, border_top_right_radius=0)
            pygame.draw.rect(self.screen, (70, 70, 70), lid_rect, width=2, border_top_left_radius=0, border_top_right_radius=0)

            # Dividing seam line
            seam_y = chest_rect.top + lid_h
            pygame.draw.line(self.screen, (16, 16, 16), (chest_rect.left + 4, seam_y), (chest_rect.right - 4, seam_y), 4)
            pygame.draw.line(self.screen, glow_color, (chest_rect.left + 24, seam_y), (chest_rect.right - 24, seam_y), 2)

            # Central energy lock core
            lock_w = int(64 * scale)
            lock_h = int(46 * scale)
            lock_rect = pygame.Rect(cx - lock_w // 2, seam_y - lock_h // 2, lock_w, lock_h)
            pygame.draw.rect(self.screen, (24, 24, 24), lock_rect, border_radius=0)
            pygame.draw.rect(self.screen, glow_color, lock_rect, width=1, border_radius=0)

            core_r = max(4, int(10 * scale + math.sin(time_remaining_s * 6.0) * 2.5))
            pygame.draw.circle(self.screen, glow_color, lock_rect.center, core_r)
            pygame.draw.circle(self.screen, (255, 255, 255), lock_rect.center, max(2, core_r - 4))

            # Vertical energy cooling vents on lower chassis
            for vent_x in (cx - 85, cx - 42, cx + 42, cx + 85):
                pygame.draw.line(self.screen, (18, 18, 18), (vent_x, seam_y + 24), (vent_x, chest_rect.bottom - 18), 4)
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
                pygame.draw.lines(self.screen, COLOR_TIMER_RED, False, c3, 3)
            if instability > 0.85:
                c4 = [(cx + 20, seam_y - 10), (cx + 48, seam_y - 42), (cx + 82, seam_y - 32), (cx + 122, seam_y - 52)]
                pygame.draw.lines(self.screen, COLOR_TIMER_RED, False, c4, 3)

        else:
            # Shattered / collapsed chest graphic
            pygame.draw.rect(self.screen, (32, 32, 32), chest_rect, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_TIMER_RED, chest_rect, width=1, border_radius=0)
            pygame.draw.line(self.screen, COLOR_TIMER_RED, chest_rect.topleft, chest_rect.bottomright, 3)
            pygame.draw.line(self.screen, COLOR_TIMER_RED, chest_rect.topright, chest_rect.bottomleft, 3)
            self._draw_text("CHEST COLLAPSED", self.font_hero, COLOR_TIMER_RED, (cx, cy - 10), center=True, max_width=chest_rect.width - 24)
            self._draw_text("ALL ACCUMULATED VALUE LOST", self.font_body, COLOR_SEMANTIC_WARNING, (cx, cy + 30), center=True, max_width=chest_rect.width - 24)

        # 3. Multiplier Counter Floating Above Chest
        counter_h = 72
        counter_top = 152 + oy
        counter_card = pygame.Rect(cx - 160, counter_top, 320, counter_h)
        self._draw_card(counter_card, border_color=glow_color, bg_color=COLOR_CARD_BG)
        self._draw_text("ACCUMULATED MULTIPLIER", self.font_small, (160, 160, 160), (cx, counter_top + 16), center=True)
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
        b1 = COLOR_TIMER_GREEN if is_sel1 else (COLOR_TIMER_GREEN if selected_index is None else COLOR_HAIRLINE)
        bg1 = (43, 43, 43) if is_sel1 else COLOR_CARD_BG
        self._draw_card(r1, border_color=b1, bg_color=bg1)

        k1 = pygame.Rect(r1.left + 16, r1.centery - 18, 36, 36)
        self._draw_key_badge(k1, "1", selected=is_sel1)

        self._draw_text("CLAIM NOW", self.font_title, COLOR_TIMER_GREEN if is_sel1 else COLOR_TEXT_PRIMARY, (k1.right + 18, r1.top + 14))
        self._draw_text(f"Secure {current_val} units immediately", self.font_small, COLOR_TEXT_SECONDARY, (k1.right + 18, r1.top + 42))

        # Option 2: KEEP WAITING
        r2 = pygame.Rect(self.width // 2 + 20 + ox, card_y, card_w, card_h)
        is_sel2 = (selected_index == 1)
        b2 = COLOR_TIMER_AMBER if is_sel2 else (COLOR_TIMER_AMBER if selected_index is None else COLOR_HAIRLINE)
        bg2 = (42, 42, 42) if is_sel2 else COLOR_CARD_BG
        self._draw_card(r2, border_color=b2, bg_color=bg2)

        k2 = pygame.Rect(r2.left + 16, r2.centery - 18, 36, 36)
        self._draw_key_badge(k2, "2", selected=is_sel2)

        self._draw_text("KEEP WAITING", self.font_title, COLOR_TIMER_AMBER if is_sel2 else COLOR_TEXT_PRIMARY, (k2.right + 18, r2.top + 14))
        self._draw_text("Multiply value (Sudden collapse risk)", self.font_small, COLOR_TEXT_SECONDARY, (k2.right + 18, r2.top + 42))

        return True
