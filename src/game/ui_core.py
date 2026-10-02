"""Rendering core for Pulse: surface, fonts, text fitting, wrapping, and card primitives."""
from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar

import pygame

from src.game.constants import (
    COLOR_BG,
    COLOR_CARD_BG,
    COLOR_TEXT_PRIMARY,
)
from src.game.ui_effects import RadialShatterEffect


class UIRendererCore:
    """Owns the target surface and the shared text and panel primitives every screen builds on."""

    FONT_FALLBACKS: ClassVar[list[str | None]] = ["segoeui", "arial", "helvetica", None]
    MONO_FONT_FALLBACKS: ClassVar[list[str | None]] = ["consolas", "couriernew", "lucidaconsole", "monospace", None]

    # Shared layout grid (1280x720): every screen keeps its content inside the same side margins,
    # starts it below the timer bar, and puts its one-line instruction on the same footer line
    MARGIN: ClassVar[int] = 50
    CONTENT_TOP: ClassVar[int] = 96
    FOOTER_Y: ClassVar[int] = 704

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

        font_dir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"

        def resolve(files: tuple[str, ...], names: list[str | None], size: int, bold: bool = False) -> pygame.font.Font:
            # Exact files first: SysFont never raises on an unknown name, and 'segoeui' matches the Light cut
            for file_name in files:
                candidate = font_dir / file_name
                if candidate.is_file():
                    return pygame.font.Font(str(candidate), size)
            for name in names:
                path = pygame.font.match_font(name, bold=bold) if name is not None else None
                if path:
                    return pygame.font.Font(path, size)
            return pygame.font.Font(None, size)

        sans = ("segoeui.ttf", "arial.ttf")
        sans_display = ("seguisb.ttf", "segoeuib.ttf", "arialbd.ttf")
        mono = ("consola.ttf", "cour.ttf")
        self.font_hero: pygame.font.Font = resolve(sans_display, self.FONT_FALLBACKS, 44, bold=True)
        self.font_title: pygame.font.Font = resolve(sans_display, self.FONT_FALLBACKS, 28, bold=True)
        self.font_lead: pygame.font.Font = resolve(sans, self.FONT_FALLBACKS, 24)
        self.font_body: pygame.font.Font = resolve(sans, self.FONT_FALLBACKS, 20)
        self.font_small: pygame.font.Font = resolve(sans, self.FONT_FALLBACKS, 16)
        self.font_caption: pygame.font.Font = resolve(sans, self.FONT_FALLBACKS, 13)
        self.font_mono: pygame.font.Font = resolve(mono, self.MONO_FONT_FALLBACKS, 17)
        self.font_mono_small: pygame.font.Font = resolve(mono, self.MONO_FONT_FALLBACKS, 14)
        self.font_mono_caption: pygame.font.Font = resolve(mono, self.MONO_FONT_FALLBACKS, 12)

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
        max_width: int | None = None,
    ) -> pygame.Rect:
        """Render a single line of text with optional alignment and a shrink-to-fit width guard."""
        if max_width is not None and font.size(text)[0] > max_width:
            font, text = self._fit_line(text, font, max_width)
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

    def _ladder(self, font: pygame.font.Font) -> list[pygame.font.Font]:
        """Return fonts of the same family no larger than the given one, largest first."""
        mono = [self.font_mono, self.font_mono_small, self.font_mono_caption]
        sans = [self.font_hero, self.font_title, self.font_lead, self.font_body, self.font_small, self.font_caption]
        family = mono if any(font is f for f in mono) else sans
        return [f for f in family if f.get_linesize() <= font.get_linesize()]

    def _ellipsize(self, text: str, font: pygame.font.Font, max_width: int) -> str:
        """Trim text and append an ASCII ellipsis so it fits max_width."""
        if font.size(text)[0] <= max_width:
            return text
        trimmed = text
        while trimmed and font.size(f"{trimmed}...")[0] > max_width:
            trimmed = trimmed[:-1]
        return f"{trimmed.rstrip()}..."

    def _fit_line(self, text: str, font: pygame.font.Font, max_width: int) -> tuple[pygame.font.Font, str]:
        """Step down the family ladder until the line fits; ellipsize only as a last resort."""
        chosen = font
        for candidate in self._ladder(font):
            chosen = candidate
            if candidate.size(text)[0] <= max_width:
                return (candidate, text)
        return (chosen, self._ellipsize(text, chosen, max_width))

    @staticmethod
    def _ink_for(fill: tuple[int, int, int]) -> tuple[int, int, int]:
        """Return near-black or white ink, whichever contrasts more with the given fill (WCAG luminance)."""
        def lin(v: int) -> float:
            ch = v / 255.0
            return ch / 12.92 if ch <= 0.03928 else ((ch + 0.055) / 1.055) ** 2.4

        lum = 0.2126 * lin(fill[0]) + 0.7152 * lin(fill[1]) + 0.0722 * lin(fill[2])
        return COLOR_BG if lum > 0.179 else COLOR_TEXT_PRIMARY

    @staticmethod
    def _mix(color: tuple[int, int, int], toward: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
        """Blend a palette token toward a neutral. The hue is unchanged, so the result stays on-palette."""
        t = max(0.0, min(1.0, amount))
        return (
            int(color[0] + (toward[0] - color[0]) * t),
            int(color[1] + (toward[1] - color[1]) * t),
            int(color[2] + (toward[2] - color[2]) * t),
        )

    def set_last_choice(self, option_index: int) -> None:
        """Record the committed option so post-decision screens reflect what was actually chosen."""
        self._last_fork_choice = option_index

    @staticmethod
    def _wrap_lines(text: str, font: pygame.font.Font, width: int) -> list[str]:
        """Break text into lines no wider than width; an empty string marks a paragraph break."""
        lines: list[str] = []
        for paragraph in text.split("\n"):
            words = paragraph.strip().split(" ") if paragraph.strip() else []
            if not words:
                lines.append("")
                continue
            current = ""
            for word in words:
                candidate = f"{current} {word}".strip()
                if font.size(candidate)[0] <= width:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)
        return lines

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

        def _wrap_lines(f: pygame.font.Font) -> list[str]:
            return self._wrap_lines(text, f, rect.width)

        active_font = font
        lines = _wrap_lines(active_font)
        line_h = active_font.get_linesize()
        total_h = len(lines) * (line_h + spacing) - spacing
        # Auto downscale font if lines exceed container height
        if rect.height > 0 and total_h > rect.height:
            for fallback_font in self._ladder(font):
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

        for idx, line in enumerate(lines):
            if not line:
                y += line_h // 2 + spacing
                continue
            # Clamping overflow: do not draw outside the container bottom
            if rect.height > 0 and y + line_h > rect.bottom + 6:
                break
            # Never truncate silently: mark the last line that fits when more text follows
            next_overflows = rect.height > 0 and y + 2 * line_h + spacing > rect.bottom + 6
            shown = self._ellipsize(f"{line} ...", active_font, rect.width) if next_overflows and idx < len(lines) - 1 else line
            surf = active_font.render(shown, True, color)
            line_x = rect.centerx - surf.get_width() // 2 if center_h else rect.left
            self.screen.blit(surf, (line_x, y))
            y += surf.get_height() + spacing
        return y

    def _draw_card(
        self,
        rect: pygame.Rect,
        border_color: tuple[int, int, int] | None = None,
        bg_color: tuple[int, int, int] = COLOR_CARD_BG,
        border_radius: int = 0,
        border_width: int = 1,
    ) -> None:
        """Draw a precision panel card with optional accent border (Ferrari design system)."""
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=border_radius)
        if border_color is not None:
            pygame.draw.rect(self.screen, border_color, rect, width=border_width, border_radius=border_radius)
