"""Post-decision waiting screens for Pulse (delay-wait and future-uncertainty scenarios)."""
from __future__ import annotations

import pygame

from src.game.constants import (
    COLOR_BG,
    COLOR_HAIRLINE_SUBTLE,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
)
from src.game.skins.document_workspace import DocumentWorkspaceSkin
from src.game.skins.fork_map import ForkMapSkin
from src.game.skins.notification_stack import NotificationStackSkin

# Words in a scenario's post_wait_text that identify which skin's wait scene to draw
DOCUMENT_CUES = ("reviewing", "changes")
FORK_CUES = ("synthesizing", "projections", "crossroads", "selection")
NOTIFICATION_CUES = ("recalculating", "parameters", "assessment")


class UIPostWait(DocumentWorkspaceSkin, ForkMapSkin, NotificationStackSkin):
    """Renders the uninformative waiting phase between a committed choice and its consequence.

    Each wait redraws the scene the participant just left, so the world does not change under
    them. A wait screen never states how long it lasts or that information is being withheld.
    """

    def draw_post_wait(self, text: str, elapsed_fraction: float) -> None:
        """Render delay wait screen for Future Uncertainty and Impulsivity domains."""
        self.screen.fill(COLOR_BG)
        lowered = text.lower()
        if any(cue in lowered for cue in DOCUMENT_CUES):
            self._draw_post_wait_document_workspace(text, elapsed_fraction)
        elif any(cue in lowered for cue in FORK_CUES):
            self._draw_post_wait_fork_map(text, elapsed_fraction)
        elif any(cue in lowered for cue in NOTIFICATION_CUES):
            self._draw_post_wait_notification_stack(text, elapsed_fraction)
        else:
            self._draw_post_wait_default(text, elapsed_fraction)

    def _draw_post_wait_default(self, text: str, elapsed_fraction: float) -> None:
        """Render the plain wait card used when no skin owns the wait."""
        card = pygame.Rect(self.width // 2 - 300, self.height // 2 - 90, 600, 180)
        self._draw_card(card, COLOR_HAIRLINE_SUBTLE)
        self._draw_spinner((card.left + 60, card.centery), 20, elapsed_fraction * 5.0)
        self._draw_text(text, self.font_title, COLOR_TEXT_PRIMARY, (card.left + 108, card.centery - 32), max_width=card.width - 132)
        self._draw_text("This will finish on its own. No key is needed.", self.font_small, COLOR_TEXT_SECONDARY, (card.left + 108, card.centery + 14))
        self._draw_text("PLEASE REMAIN STILL", self.font_small, (140, 140, 140), (self.width // 2, self.FOOTER_Y), center=True)
