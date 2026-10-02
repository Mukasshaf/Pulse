"""Simulation skin `fork_map` for scenario `future_uncertainty_a`."""
from __future__ import annotations

import math

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_BG,
    COLOR_CARD_BG,
    COLOR_HAIRLINE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TIMER_AMBER,
    COLOR_TIMER_GREEN,
    COLOR_TIMER_RED,
    COMPASS_SPIN_MAX_RPM,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState


class ForkMapSkin(UIComponents):
    """Renders the `fork_map` decision skin."""

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
        self._draw_card(hdr_rect, border_color=COLOR_HAIRLINE, bg_color=COLOR_CARD_BG)

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
            syn_col = self._mix(COLOR_ACCENT_CYAN, COLOR_TEXT_PRIMARY, 0.35 * pulse_syn)
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
        # Continuous drift that never settles on North, capped at COMPASS_SPIN_MAX_RPM (RPM * 6 = deg/s)
        compass_angle = (time_remaining_s * COMPASS_SPIN_MAX_RPM * 6.0) % 360.0

        # Cardinal letters are omitted here: N sat on the timer bar and S under the status label
        self._draw_compass(compass_center, 28, compass_angle, show_cardinals=False)
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
        pygame.draw.rect(self.screen, (24, 24, 24), stem_rect)
        pygame.draw.line(self.screen, (60, 60, 60), (stem_rect.left, stem_rect.top), (stem_rect.left, stem_rect.bottom), 2)
        pygame.draw.line(self.screen, (60, 60, 60), (stem_rect.right, stem_rect.top), (stem_rect.right, stem_rect.bottom), 2)

        # Dashed center lane on approach road
        for sy in range(fork_node_y + 8, trunk_bottom_y - 8, 16):
            pygame.draw.line(self.screen, (114, 114, 114), (cx, sy), (cx, sy + 8), 2)

        # Start/Present position indicator
        pygame.draw.circle(self.screen, COLOR_TIMER_GREEN, (cx, trunk_bottom_y - 12), 6)
        pygame.draw.circle(self.screen, (255, 255, 255), (cx, trunk_bottom_y - 12), 3)
        self._draw_text("PRESENT LOCATION", self.font_small, COLOR_TIMER_GREEN, (cx, trunk_bottom_y + 8), center=True)

        # Fork junction circle
        pygame.draw.circle(self.screen, (36, 36, 36), (cx, fork_node_y), 20)
        pygame.draw.circle(self.screen, (84, 84, 84), (cx, fork_node_y), 20, width=2)

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
            a_col = (48, 48, 48)
            a_w = 4
        elif is_a_active:
            # Glowing illuminated branch
            pygame.draw.lines(self.screen, self._mix(COLOR_ACCENT_CYAN, COLOR_BG, 0.65), False, pts_a, 16)
            a_col = COLOR_ACCENT_CYAN
            a_w = 6
        else:
            pygame.draw.lines(self.screen, self._mix(COLOR_ACCENT_CYAN, COLOR_BG, 0.88), False, pts_a, 12)
            a_col = COLOR_ACCENT_CYAN
            a_w = 5

        pygame.draw.lines(self.screen, a_col, False, pts_a, a_w)

        # Path A Label along roadway
        mid_a = pts_a[10]
        self._draw_text(
            "ESTABLISHED TRACK",
            self.font_small,
            COLOR_TEXT_MUTED if is_a_dimmed else COLOR_ACCENT_CYAN,
            (mid_a[0] - 20, mid_a[1] + 16),
            center=True,
        )

        # Terminal Box A: Opaque Gray Box (expanded to 380px to contain subtitle cleanly)
        box_a = pygame.Rect(cx - 550, fork_node_y - 215, 380, 68)
        box_a_border = (58, 58, 58) if is_a_dimmed else (COLOR_ACCENT_CYAN if is_a_active else (94, 94, 94))
        box_a_bg = (24, 24, 24) if is_a_dimmed else ((33, 33, 33) if is_a_active else (30, 30, 30))
        self._draw_card(box_a, border_color=box_a_border, bg_color=box_a_bg)

        self._draw_text(
            "[ LONG-TERM OUTCOMES: DATA UNAVAILABLE ]",
            self.font_small,
            (129, 129, 129) if is_a_dimmed else COLOR_TEXT_PRIMARY,
            (box_a.centerx, box_a.top + 18),
            center=True,
        )
        self._draw_text(
            "Familiar Track • Predictable • Fixed Ceiling",
            self.font_mono_small,
            COLOR_TEXT_MUTED if is_a_dimmed else (164, 164, 164),
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
            b_col = (48, 48, 48)
            b_w = 4
        elif is_b_active:
            # Glowing illuminated branch
            pygame.draw.lines(self.screen, self._mix(COLOR_TIMER_AMBER, COLOR_BG, 0.65), False, pts_b, 16)
            b_col = COLOR_TIMER_AMBER
            b_w = 6
        else:
            pygame.draw.lines(self.screen, self._mix(COLOR_TIMER_AMBER, COLOR_BG, 0.88), False, pts_b, 12)
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
            (91, 91, 91) if is_b_dimmed else COLOR_TIMER_AMBER,
            (mid_b[0] + 20, mid_b[1] + 16),
            center=True,
        )

        # Dark Fog / Gradient Overlay around Path B destination
        fog_w = 380
        fog_h = 110
        fog_surf = pygame.Surface((fog_w, fog_h), pygame.SRCALPHA)
        # Concentric dark fog clouds
        for fog_r, fog_alpha in [(160, 160), (120, 190), (80, 220), (40, 240)]:
            pygame.draw.ellipse(fog_surf, (10, 10, 10, fog_alpha), (fog_w // 2 - fog_r, fog_h // 2 - fog_r // 2, fog_r * 2, fog_r))
        self.screen.blit(fog_surf, (cx + 150, fork_node_y - 235))

        # Terminal Box B inside fog (expanded to 380px to contain subtitle cleanly)
        box_b = pygame.Rect(cx + 170, fork_node_y - 215, 380, 68)
        box_b_border = (48, 48, 48) if is_b_dimmed else (COLOR_TIMER_AMBER if is_b_active else self._mix(COLOR_TIMER_AMBER, COLOR_BG, 0.45))
        box_b_bg = (16, 16, 16) if is_b_dimmed else COLOR_BG
        self._draw_card(box_b, border_color=box_b_border, bg_color=box_b_bg)

        self._draw_text(
            "[ SUPPORT STRUCTURE: UNDER REVIEW ]",
            self.font_small,
            (111, 111, 111) if is_b_dimmed else COLOR_TIMER_AMBER,
            (box_b.centerx, box_b.top + 18),
            center=True,
        )
        self._draw_text(
            "Uncharted • High Volatility • Zero Guarantees",
            self.font_mono_small,
            (86, 86, 86) if is_b_dimmed else (173, 173, 173),
            (box_b.centerx, box_b.top + 42),
            center=True,
        )

        # 4. Decision Options Cards at Bottom
        card_y = self.height - 130 + oy
        card_h = 95
        card_w = 560

        # Option 1: Established Track
        r1 = pygame.Rect(cx - card_w - 15, card_y, card_w, card_h)
        b1_col = COLOR_TIMER_GREEN if selected_index == 0 else (COLOR_ACCENT_CYAN if selected_index is None else COLOR_HAIRLINE)
        bg1_col = (35, 35, 35) if selected_index == 0 else COLOR_CARD_BG
        self._draw_card(r1, border_color=b1_col, bg_color=bg1_col)

        k1_badge = pygame.Rect(r1.left + 16, r1.centery - 18, 36, 36)
        self._draw_key_badge(k1_badge, "1", selected=selected_index == 0)

        self._draw_text(
            "Path A: Familiar, Established Track",
            self.font_body,
            COLOR_ACCENT_CYAN if selected_index == 0 else COLOR_TEXT_PRIMARY,
            (k1_badge.right + 14, r1.top + 14),
        )
        sub1_rect = pygame.Rect(k1_badge.right + 14, r1.top + 38, r1.width - 85, 26)
        self._draw_wrapped_text(
            "Predictable progression. Long-term growth potential: [DATA UNAVAILABLE]",
            self.font_small,
            COLOR_TEXT_SECONDARY,
            sub1_rect,
            spacing=2,
            center_v=True,
        )
        tag1 = pygame.Rect(k1_badge.right + 14, r1.bottom - 28, 270, 20)
        pygame.draw.rect(self.screen, (32, 32, 32), tag1, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_ACCENT_CYAN, tag1, width=1, border_radius=0)
        self._draw_text("[ PREDICTABLE // UNKNOWN HORIZON ]", self.font_mono_small, COLOR_ACCENT_CYAN, tag1.center, center=True, max_width=tag1.width - 10)

        # Option 2: Uncharted Trajectory
        r2 = pygame.Rect(cx + 15, card_y, card_w, card_h)
        b2_col = COLOR_TIMER_GREEN if selected_index == 1 else (COLOR_TIMER_AMBER if selected_index is None else COLOR_HAIRLINE)
        bg2_col = (33, 33, 33) if selected_index == 1 else COLOR_CARD_BG
        self._draw_card(r2, border_color=b2_col, bg_color=bg2_col)

        k2_badge = pygame.Rect(r2.left + 16, r2.centery - 18, 36, 36)
        self._draw_key_badge(k2_badge, "2", selected=selected_index == 1)

        self._draw_text(
            "Path B: New, Challenging Path",
            self.font_body,
            COLOR_TIMER_AMBER if selected_index == 1 else COLOR_TEXT_PRIMARY,
            (k2_badge.right + 14, r2.top + 14),
        )
        sub2_rect = pygame.Rect(k2_badge.right + 14, r2.top + 38, r2.width - 85, 26)
        self._draw_wrapped_text(
            "Unpredictable trajectory. Support structure: [UNDER REVIEW]",
            self.font_small,
            COLOR_TEXT_SECONDARY,
            sub2_rect,
            spacing=2,
            center_v=True,
        )
        tag2 = pygame.Rect(k2_badge.right + 14, r2.bottom - 28, 270, 20)
        pygame.draw.rect(self.screen, (32, 32, 32), tag2, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TIMER_AMBER, tag2, width=1, border_radius=0)
        self._draw_text("[ HIGH VOLATILITY // ZERO GUARANTEE ]", self.font_mono_small, COLOR_TIMER_AMBER, tag2.center, center=True, max_width=tag2.width - 10)

        # Bottom Prompt
        self._draw_text(
            "PRESS KEY [1] OR [2] TO COMMIT TO TRAJECTORY PATHWAY",
            self.font_small,
            (140, 140, 140),
            (self.width // 2, self.height - 20),
            center=True,
        )

        return True
