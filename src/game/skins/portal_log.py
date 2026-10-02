"""Simulation skin `portal_log` for scenario `rule_ambiguity_a`."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_CARD_BG,
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


class PortalLogSkin(UIComponents):
    """Renders the `portal_log` decision skin."""

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
        # The panel already carries the engine jitter (ox, oy); a second source would exceed the 3 px / 2 Hz limits
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
        pygame.draw.rect(self.screen, (20, 20, 20), left_rect, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, left_rect, width=1, border_radius=0)

        # Terminal Header Bar
        hdr_h = 36
        term_hdr = pygame.Rect(left_rect.left, left_rect.top, w_left, hdr_h)
        pygame.draw.rect(self.screen, (36, 36, 36), term_hdr, border_top_left_radius=0, border_top_right_radius=0)
        pygame.draw.line(self.screen, COLOR_HAIRLINE, (left_rect.left, term_hdr.bottom), (left_rect.right, term_hdr.bottom), 1)

        # Window controls: neutral square outlines (no OS-specific traffic-light colours)
        for ctl_x in (left_rect.left + 18, left_rect.left + 34, left_rect.left + 50):
            pygame.draw.rect(self.screen, COLOR_HAIRLINE_SUBTLE, (ctl_x - 4, term_hdr.centery - 4, 9, 9), width=1, border_radius=0)

        self._draw_text(
            "root@campus-it-gateway: /var/log/audit.log",
            self.font_mono_small,
            (159, 159, 159),
            (left_rect.left + 68, term_hdr.centery),
            midleft=True,
        )

        # Timestamp line with diegetic jitter
        ms_part = int((time_remaining_s * 1000) % 1000)
        ts_text = f"SYS_TIME: 2026-09-19 23:17:{int(time_remaining_s):02d}.{ms_part:03d} UTC"
        self._draw_text(
            ts_text,
            self.font_mono_small,
            COLOR_ACCENT_CYAN if time_remaining_s > 15.0 else COLOR_SEMANTIC_WARNING,
            (left_rect.left + 20 + tjx, left_rect.top + 50 + tjy),
        )

        # Terminal prompt
        prompt_y = left_rect.top + 76
        self._draw_text("auth_daemon --inspect --target friend_account_id", self.font_mono_small, COLOR_TIMER_GREEN, (left_rect.left + 20, prompt_y))
        pygame.draw.line(self.screen, (34, 34, 34), (left_rect.left + 20, prompt_y + 24), (left_rect.right - 20, prompt_y + 24), 1)

        # Core Log lines: the tag carries the severity colour, the detail stays in white ink
        log_entries = [
            ("[AUTH_DAEMON]", " USER: friend_account_id", COLOR_ACCENT_CYAN),
            ("[STATUS]", " LOCKED — OUTSTANDING SYSTEM GLITCH", COLOR_TIMER_AMBER),
            ("[TICKET_STATUS]", " PENDING ADMIN REVIEW: 21 DAYS", COLOR_TIMER_AMBER),
            ("[DEADLINE_ALERT]", " ASSIGNMENT CLOSES IN: 00:42:15", COLOR_SEMANTIC_WARNING),
            ("[STORED_SESSION]", " ACTIVE TOKEN DETECTED FROM YOUR IP", COLOR_ACCENT_CYAN),
        ]

        log_start_y = prompt_y + 36
        entry_h = 44
        for idx, (tag, detail, tag_col) in enumerate(log_entries):
            ey = log_start_y + idx * entry_h
            entry_box = pygame.Rect(left_rect.left + 16, ey - 4, w_left - 32, 38)
            pygame.draw.rect(self.screen, (32, 32, 32), entry_box, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE, entry_box, width=1, border_radius=0)

            self._draw_text(tag, self.font_mono_small, tag_col, (entry_box.left + 12, ey + 4))
            tag_w = self.font_mono_small.size(tag)[0]
            self._draw_text(detail, self.font_mono_small, COLOR_TEXT_PRIMARY, (entry_box.left + 12 + tag_w, ey + 4))

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
            self._draw_text(d_line, self.font_mono_small, COLOR_TEXT_MUTED, (left_rect.left + 20, extra_y + d_idx * 18))

        # Institutional Policy Callout Box at bottom of left panel
        clause_box = pygame.Rect(left_rect.left + 16, left_rect.bottom - 92, w_left - 32, 76)
        pygame.draw.rect(self.screen, (24, 24, 24), clause_box, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TIMER_RED, clause_box, width=1, border_radius=0)

        self._draw_text("CAMPUS IT POLICY — SECTION 4.2.1", self.font_small, COLOR_SEMANTIC_WARNING, (clause_box.left + 14, clause_box.top + 10))
        self._draw_text(
            "Accessing another user's portal credentials constitutes",
            self.font_small,
            (179, 179, 179),
            (clause_box.left + 14, clause_box.top + 30),
        )
        self._draw_text(
            "unauthorized authentication and carries disciplinary suspension.",
            self.font_small,
            (179, 179, 179),
            (clause_box.left + 14, clause_box.top + 50),
        )

        # =============================================================
        # Right Panel (Decision Terminal, 55% width): 3 Dilemma Cards
        # =============================================================
        pygame.draw.rect(self.screen, (24, 24, 24), right_rect, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, right_rect, width=1, border_radius=0)

        # Right Header
        r_hdr = pygame.Rect(right_rect.left, right_rect.top, w_right, hdr_h)
        pygame.draw.rect(self.screen, (28, 28, 28), r_hdr, border_top_left_radius=0, border_top_right_radius=0)
        pygame.draw.line(self.screen, (48, 48, 48), (right_rect.left, r_hdr.bottom), (right_rect.right, r_hdr.bottom), 1)

        self._draw_text(
            "DECISION TERMINAL // AUTHORIZATION PROTOCOL",
            self.font_small,
            COLOR_ACCENT_CYAN,
            (right_rect.left + 20, r_hdr.centery),
            midleft=True,
        )
        self._draw_text("RECORDED EVENT", self.font_small, (139, 139, 139), (right_rect.right - 20, r_hdr.centery), midright=True)

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
                (35, 35, 35),
            ),
            (
                2,
                "Direct to Official Appeal",
                "Strict compliance with campus procedures (Compliance)",
                "Follows rules strictly; friend misses deadline & incurs 20% penalty.",
                "[ STRICTLY COMPLIANT // FRIEND FAILS ]",
                COLOR_TIMER_GREEN,
                (34, 34, 34),
            ),
            (
                3,
                "Exploit Guest Access Loophole",
                "Use unpatched portal guest feature (Grey Area)",
                "Circumvents login with guest bypass; risks investigation if audited.",
                "[ GREY AREA // UNPATCHED EXPLOIT ]",
                COLOR_TEXT_PRIMARY,
                (27, 27, 27),
            ),
        ]

        for i, (key, title, subtitle, trade_off, tag, accent_col, bg_col) in enumerate(opts_data):
            cy = cards_start_y + i * (card_h + card_gap)
            c_rect = pygame.Rect(right_rect.left + 20, cy, w_right - 40, card_h)

            is_sel = (selected_index == i)
            border_col = accent_col if is_sel else COLOR_HAIRLINE
            card_bg = bg_col if is_sel else COLOR_CARD_BG
            self._draw_card(c_rect, border_color=border_col, bg_color=card_bg)

            # Key Badge
            k_badge = pygame.Rect(c_rect.left + 16, c_rect.top + 16, 36, 36)
            self._draw_key_badge(k_badge, str(key), selected=is_sel)

            # Title & Subtitle (font_body prevents overlap with subtitle at top + 42)
            self._draw_text(title, self.font_body, accent_col if is_sel else COLOR_TEXT_PRIMARY, (k_badge.right + 16, c_rect.top + 14))
            self._draw_text(subtitle, self.font_small, (160, 160, 160), (k_badge.right + 16, c_rect.top + 42))

            # Trade-off text
            trade_rect = pygame.Rect(c_rect.left + 16, c_rect.top + 70, c_rect.width - 32, 38)
            self._draw_wrapped_text(trade_off, self.font_small, COLOR_TEXT_SECONDARY, trade_rect, spacing=2, center_v=True)

            # Bottom pill tag
            tag_rect = pygame.Rect(c_rect.left + 16, c_rect.bottom - 34, c_rect.width - 32, 24)
            pygame.draw.rect(self.screen, (32, 32, 32), tag_rect, border_radius=0)
            pygame.draw.rect(self.screen, accent_col, tag_rect, width=1, border_radius=0)
            self._draw_text(tag, self.font_small, accent_col, tag_rect.center, center=True)

        # Bottom Prompt
        self._draw_text(
            "PRESS KEY [1], [2], OR [3] TO COMMIT DECISION TO AUDIT LOG",
            self.font_small,
            (140, 140, 140),
            (self.width // 2, self.height - 35),
            center=True,
        )

        return True
