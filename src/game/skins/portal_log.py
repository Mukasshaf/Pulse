"""Simulation skin `portal_log` for scenario `rule_ambiguity_a`."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_ACCENT_CYAN,
    COLOR_HAIRLINE,
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

# The tag carries the severity colour, the detail stays in white ink
LOG_ENTRIES: tuple[tuple[str, str, tuple[int, int, int]], ...] = (
    ("[AUTH_DAEMON]", " USER: friend_account_id", COLOR_ACCENT_CYAN),
    ("[STATUS]", " LOCKED — OUTSTANDING SYSTEM GLITCH", COLOR_TIMER_AMBER),
    ("[TICKET_STATUS]", " PENDING ADMIN REVIEW: 21 DAYS", COLOR_TIMER_AMBER),
    ("[DEADLINE_ALERT]", " ASSIGNMENT CLOSES IN: 00:42:15", COLOR_SEMANTIC_WARNING),
    ("[STORED_SESSION]", " ACTIVE TOKEN DETECTED FROM YOUR IP", COLOR_ACCENT_CYAN),
)
# Written to the log for the last 15 s of the window, whether or not a choice has been made
IDLE_ENTRY: tuple[str, str, tuple[int, int, int]] = ("[SESSION]", " INACTIVITY DETECTED — DECISION REQUIRED", COLOR_SEMANTIC_WARNING)
IDLE_NOTICE_S = 15.0


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
        # The panels carry the engine jitter; no second jitter source is added (3 px / 2 Hz limits)
        ox = effects.vibration_offset[0] + effects.jitter_offset[0]
        oy = effects.vibration_offset[1] + effects.jitter_offset[1]
        total_w = self.width - 2 * self.MARGIN
        left_w = int((total_w - 20) * 0.45)
        left = pygame.Rect(self.MARGIN + ox, self.CONTENT_TOP + oy, left_w, 584)
        right = pygame.Rect(left.right + 20, left.top, total_w - 20 - left_w, left.height)

        self._draw_portal_terminal(left, time_remaining_s)
        self._draw_portal_decisions(right, scenario, selected_index)
        self._draw_footer_prompt("PRESS 1, 2 OR 3 TO COMMIT YOUR DECISION TO THE AUDIT LOG", selected_index is not None)
        return True

    def _draw_portal_terminal(self, panel: pygame.Rect, time_remaining_s: float) -> None:
        """Draw the audit log: the lockout, the deadline, the stored session, and the policy clause."""
        pygame.draw.rect(self.screen, (20, 20, 20), panel, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, panel, width=1, border_radius=0)
        self._draw_window_chrome(panel, "root@campus-it-gateway: /var/log/audit.log", mono=True)

        critical = time_remaining_s <= IDLE_NOTICE_S
        stamp = f"SYS_TIME: 2026-09-19 23:17:{int(time_remaining_s):02d}.{int((time_remaining_s * 1000) % 1000):03d} UTC"
        self._draw_text(stamp, self.font_mono_small, COLOR_SEMANTIC_WARNING if critical else COLOR_ACCENT_CYAN, (panel.left + 20, panel.top + 50))
        self._draw_text("auth_daemon --inspect --target friend_account_id", self.font_mono_small, COLOR_TIMER_GREEN, (panel.left + 20, panel.top + 76))
        pygame.draw.line(self.screen, (34, 34, 34), (panel.left + 20, panel.top + 100), (panel.right - 20, panel.top + 100), 1)

        entries = LOG_ENTRIES + ((IDLE_ENTRY,) if critical else ())
        for row, (tag, detail, tag_colour) in enumerate(entries):
            box = pygame.Rect(panel.left + 16, panel.top + 110 + row * 44, panel.width - 32, 38)
            pygame.draw.rect(self.screen, (32, 32, 32), box, border_radius=0)
            pygame.draw.rect(self.screen, COLOR_HAIRLINE, box, width=1, border_radius=0)
            tag_rect = self._draw_text(tag, self.font_mono_small, tag_colour, (box.left + 12, box.centery), midleft=True)
            self._draw_text(detail, self.font_mono_small, COLOR_TEXT_PRIMARY, (tag_rect.right, box.centery), midleft=True)

        for row, line in enumerate((">> ORIGIN_HOST: 192.168.4.120 [TRUSTED_WORKSTATION]", ">> CREDENTIAL_CACHE: VALID OAUTH_2.0 REFRESH TOKEN")):
            self._draw_text(line, self.font_mono_small, COLOR_TEXT_MUTED, (panel.left + 20, panel.top + 388 + row * 20))

        clause = pygame.Rect(panel.left + 16, panel.bottom - 96, panel.width - 32, 80)
        pygame.draw.rect(self.screen, (24, 24, 24), clause, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_TIMER_RED, clause, width=1, border_radius=0)
        self._draw_text("CAMPUS IT POLICY — SECTION 4.2.1", self.font_small, COLOR_SEMANTIC_WARNING, (clause.left + 14, clause.top + 10))
        policy = "Accessing another user's portal credentials constitutes unauthorized authentication and carries disciplinary suspension."
        self._draw_wrapped_text(policy, self.font_small, (179, 179, 179), pygame.Rect(clause.left + 14, clause.top + 32, clause.width - 28, 44), spacing=2)

    def _draw_portal_decisions(self, panel: pygame.Rect, scenario: Scenario, selected_index: int | None) -> None:
        """Draw the decision terminal: each option shows its action and its trade-off as logged, with no verdict."""
        pygame.draw.rect(self.screen, (24, 24, 24), panel, border_radius=0)
        pygame.draw.rect(self.screen, COLOR_HAIRLINE, panel, width=1, border_radius=0)
        header = pygame.Rect(panel.left, panel.top, panel.width, 36)
        pygame.draw.rect(self.screen, (36, 36, 36), header, border_radius=0)
        self._draw_text("DECISION TERMINAL", self.font_small, COLOR_ACCENT_CYAN, (header.left + 20, header.centery), midleft=True)
        self._draw_text("RECORDED EVENT", self.font_small, (139, 139, 139), (header.right - 20, header.centery), midright=True)
        self._draw_text("Choose how to proceed:", self.font_body, COLOR_TEXT_SECONDARY, (panel.left + 20, panel.top + 50))

        card_h, gap = 148, 14
        for i, opt in enumerate(scenario.options):
            action, trade_off = self._split_option(opt.text)
            rect = pygame.Rect(panel.left + 20, panel.top + 88 + i * (card_h + gap), panel.width - 40, card_h)
            self._draw_option_card(rect, opt.key, action, i, selected_index, detail=trade_off, plate="COMMITTED")
