"""Simulation skin `fork_map` for scenario `future_uncertainty_a`, with its post-decision wait."""
from __future__ import annotations

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
    COMPASS_SPIN_MAX_RPM,
)
from src.game.scenario_logic import BARTRunner, MISTRunner, RewardAccumulator
from src.game.scenarios import Scenario
from src.game.ui_components import UIComponents
from src.game.ui_effects import UIEffectState

FORK_NODE_Y = 392
TRUNK_BOTTOM_Y = 498
# (direction, road label, destination line, descriptor, colour, dashed). The colour identifies the
# path on the map and on its option card; it is a legend, not a verdict.
ROUTES: tuple[tuple[int, str, str, str, tuple[int, int, int], bool], ...] = (
    (-1, "ESTABLISHED TRACK", "LONG-TERM GROWTH: [DATA UNAVAILABLE]", "Familiar track  •  predictable progression", COLOR_ACCENT_CYAN, False),
    (1, "NEW PATH", "SUPPORT STRUCTURE: [UNDER REVIEW]", "New path  •  unpredictable trajectory", COLOR_TIMER_AMBER, True),
)


class ForkMapSkin(UIComponents):
    """Renders the `fork_map` decision skin and its wait screen from one shared scene."""

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
        offset = (effects.vibration_offset[0] + effects.jitter_offset[0], effects.vibration_offset[1] + effects.jitter_offset[1])
        header = self._draw_fork_header(offset)
        if selected_index is None:
            self._draw_text("ROUTE PLANNER", self.font_body, COLOR_ACCENT_CYAN, (header.left + 20, header.top + 8))
            self._draw_text("Two routes lead on from your present location.", self.font_small, COLOR_TEXT_SECONDARY, (header.left + 20, header.top + 33))
        else:
            self._draw_text("ROUTE LOCKED IN", self.font_body, COLOR_TEXT_PRIMARY, (header.left + 20, header.top + 8))
            self._draw_text("Your route is held until the timer ends.", self.font_small, COLOR_TEXT_SECONDARY, (header.left + 20, header.top + 33))

        # The needle drifts continuously and never settles; the readout is its true bearing (RPM * 6 = deg/s)
        self._draw_fork_compass((time_remaining_s * COMPASS_SPIN_MAX_RPM * 6.0) % 360.0, offset)
        self._draw_fork_scene(selected_index, offset)

        for i, opt in enumerate(scenario.options[:2]):
            rect = pygame.Rect(self.width // 2 - 575 + i * 590 + offset[0], 592 + offset[1], 560, 92)
            action, detail = self._split_option(opt.text)
            self._draw_option_card(rect, opt.key, action, i, selected_index, detail=detail, accent=ROUTES[i][4], plate="LOCKED IN")
        self._draw_footer_prompt("PRESS 1 OR 2 TO COMMIT TO A ROUTE", selected_index is not None)
        return True

    def _draw_fork_header(self, offset: tuple[int, int]) -> pygame.Rect:
        """Draw the planner's header plate and return its rect."""
        header = pygame.Rect(self.MARGIN + offset[0], self.CONTENT_TOP + offset[1], self.width - 2 * self.MARGIN - 270, 60)
        self._draw_card(header, border_color=COLOR_HAIRLINE, bg_color=COLOR_CARD_BG)
        return header

    def _draw_fork_compass(self, angle_deg: float, offset: tuple[int, int]) -> None:
        """Draw the compass in the top-right corner with its live bearing underneath."""
        center = (self.width - self.MARGIN - 62 + offset[0], self.CONTENT_TOP + 28 + offset[1])
        # Cardinal letters are omitted: N would sit on the timer bar and S under the readout
        self._draw_compass(center, 28, angle_deg, show_cardinals=False)
        self._draw_text(f"BEARING {int(angle_deg):03d}°", self.font_mono_small, COLOR_TEXT_SECONDARY, (center[0] - 44, center[1]), midright=True)

    def _draw_fork_scene(self, chosen: int | None, offset: tuple[int, int]) -> None:
        """Draw the crossroads: the approach road, the junction, and both routes with their destinations."""
        cx = self.width // 2 + offset[0]
        node_y = FORK_NODE_Y + offset[1]
        trunk_y = TRUNK_BOTTOM_Y + offset[1]
        pygame.draw.rect(self.screen, (28, 28, 28), (cx - 18, node_y, 36, trunk_y - node_y))
        for edge_x in (cx - 18, cx + 18):
            pygame.draw.line(self.screen, (60, 60, 60), (edge_x, node_y), (edge_x, trunk_y), 2)
        for lane_y in range(node_y + 8, trunk_y - 8, 16):
            pygame.draw.line(self.screen, (114, 114, 114), (cx, lane_y), (cx, lane_y + 8), 2)
        pygame.draw.circle(self.screen, COLOR_TIMER_GREEN, (cx, trunk_y - 12), 6)
        pygame.draw.circle(self.screen, COLOR_TEXT_PRIMARY, (cx, trunk_y - 12), 3)
        self._draw_text("PRESENT LOCATION", self.font_small, COLOR_TIMER_GREEN, (cx, trunk_y + 12), center=True)

        for index in range(len(ROUTES)):
            self._draw_fork_route(index, chosen, (cx, node_y))
        pygame.draw.circle(self.screen, (36, 36, 36), (cx, node_y), 20)
        pygame.draw.circle(self.screen, (84, 84, 84), (cx, node_y), 20, width=2)

    def _draw_fork_route(self, index: int, chosen: int | None, node: tuple[int, int]) -> None:
        """Draw one route as a bezier road that fades into its destination card; the chosen one is lit."""
        direction, road_label, destination, descriptor, colour, dashed = ROUTES[index]
        cx, node_y = node
        active = chosen == index
        dimmed = chosen is not None and not active
        control = (cx + direction * 100, node_y - 90)
        end = (cx + direction * 310, node_y - 180)
        points: list[tuple[int, int]] = []
        for step in range(21):
            t = step / 20.0
            points.append((
                int((1 - t) ** 2 * cx + 2 * (1 - t) * t * control[0] + t ** 2 * end[0]),
                int((1 - t) ** 2 * node_y + 2 * (1 - t) * t * control[1] + t ** 2 * end[1]),
            ))

        road = (52, 52, 52) if dimmed else colour
        if not dimmed:
            # The halo under a route is the same token dimmed toward the canvas
            pygame.draw.lines(self.screen, self._mix(colour, COLOR_BG, 0.65 if active else 0.88), False, points, 16 if active else 12)
        road_w = 4 if dimmed else (6 if active else 5)
        if dashed:
            for seg in range(0, len(points) - 1, 2):
                pygame.draw.line(self.screen, road, points[seg], points[seg + 1], road_w)
        else:
            pygame.draw.lines(self.screen, road, False, points, road_w)
        self._draw_text(road_label, self.font_small, COLOR_TEXT_MUTED if dimmed else colour, (points[10][0] + direction * 96, points[10][1] + 34), center=True)

        # Destination card. The new path's destination also sits in fog: the participant cannot see where it leads
        box = pygame.Rect(0, node_y - 214, 400, 70)
        box.centerx = cx + direction * 350
        if dashed:
            fog = pygame.Surface((box.width + 60, box.height + 60), pygame.SRCALPHA)
            for inset, alpha in ((0, 90), (14, 130), (26, 170)):
                pygame.draw.ellipse(fog, (10, 10, 10, alpha), fog.get_rect().inflate(-inset * 2, -inset * 2))
            self.screen.blit(fog, (box.left - 30, box.top - 30))
        border = COLOR_HAIRLINE if dimmed else (colour if active else self._mix(colour, COLOR_BG, 0.5))
        self._draw_card(box, border_color=border, bg_color=(22, 22, 22) if dimmed else (32, 32, 32))
        self._draw_text(destination, self.font_small, COLOR_TEXT_MUTED if dimmed else COLOR_TEXT_PRIMARY, (box.centerx, box.top + 20), center=True)
        self._draw_text(descriptor, self.font_mono_small, COLOR_TEXT_MUTED if dimmed else (164, 164, 164), (box.centerx, box.top + 46), center=True)

    def _draw_post_wait_fork_map(self, text: str, elapsed_fraction: float) -> None:
        """Render the wait after a route is chosen: the same map, the same restless compass, and no information."""
        header = self._draw_fork_header((0, 0))
        self._draw_spinner((header.left + 34, header.centery), 14, elapsed_fraction * 6.0)
        self._draw_text(text, self.font_body, COLOR_TEXT_PRIMARY, (header.left + 64, header.top + 8))
        self._draw_text("This will finish on its own. No key is needed.", self.font_small, COLOR_TEXT_SECONDARY, (header.left + 64, header.top + 33))
        # 12 s at COMPASS_SPIN_MAX_RPM (4 RPM) is 0.8 of a revolution: the needle never speeds up
        self._draw_fork_compass((elapsed_fraction * 360.0 * COMPASS_SPIN_MAX_RPM * 0.2) % 360.0, (0, 0))
        self._draw_fork_scene(self._last_fork_choice, (0, 0))

        plate = pygame.Rect(self.width // 2 - 575, 592, 1150, 92)
        self._draw_card(plate, border_color=COLOR_HAIRLINE, bg_color=(28, 28, 28))
        self._draw_text("YOUR ROUTE IS LOCKED IN", self.font_body, COLOR_TEXT_PRIMARY, (plate.centerx, plate.top + 30), center=True)
        self._draw_text("Nothing further can be changed.", self.font_small, COLOR_TEXT_SECONDARY, (plate.centerx, plate.top + 60), center=True)
        self._draw_text("PLEASE REMAIN STILL", self.font_small, (140, 140, 140), (self.width // 2, self.FOOTER_Y), center=True)
