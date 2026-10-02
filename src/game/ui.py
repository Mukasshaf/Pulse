"""UI rendering facade for Pulse: composes the core, components, screens, and simulation skins."""
from __future__ import annotations

from src.game.ui_domains import UIDomainSkins
from src.game.ui_post_wait import UIPostWait
from src.game.ui_screens import UIScreens

__all__ = ["UIRenderer"]


class UIRenderer(UIDomainSkins, UIScreens, UIPostWait):
    """Master rendering subsystem responsible for frame composition and presentation."""
