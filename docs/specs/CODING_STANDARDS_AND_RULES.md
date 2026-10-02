# CODING_STANDARDS_AND_RULES.md — Pulse Gamification Engine

> **Scope:** Establishes rigid boundaries for code generation behavior. Every generated file MUST conform to these rules. Violations are treated as bugs.

---

## 1. File-Level Requirements

### 1.1 Every `.py` file MUST begin with:

```python
"""<module docstring — one-line summary>."""
from __future__ import annotations
```

The `from __future__ import annotations` import enables PEP 604 union syntax (`X | None`) and forward references without quotes. No exceptions.

### 1.2 Import Order (enforced)

```python
# 1. __future__
from __future__ import annotations

# 2. Standard library (alphabetical)
import csv
import json
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

# 3. Third-party (alphabetical)
import numpy as np
import pygame

# 4. Local project imports (alphabetical)
from src.game.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from src.game.scenarios import Scenario, Domain
```

Blank line between each group. No wildcard imports (`from x import *`). No relative imports (always `from src.game.module import ...`).

---

## 2. Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Files | `snake_case.py` | `event_logger.py` |
| Classes | `PascalCase` | `GameEngine`, `MISTRunner` |
| Functions/methods | `snake_case` | `handle_keypress()` |
| Private methods | `_leading_underscore` | `_transition_to()` |
| Constants | `UPPER_SNAKE_CASE` | `SCREEN_WIDTH` |
| Enums | `PascalCase` class, `UPPER_SNAKE_CASE` members | `EngineState.BASELINE` |
| Dataclass fields | `snake_case` | `domain_id`, `priming_text` |
| Local variables | `snake_case` | `elapsed_ms`, `current_scenario` |
| Type aliases | `PascalCase` | `ColorTuple = tuple[int, int, int]` |

### Banned Names
- No single-letter variables except `i`, `j` in loops and `x`, `y` for coordinates.
- No abbreviations unless universally understood: `ms` (milliseconds), `s` (seconds), `hz` (hertz), `px` (pixels), `pct` (percent), `cfg` (config), `dt` (delta time).
- No Hungarian notation (`strName`, `iCount`).

---

## 3. Type Annotations

### 3.1 Mandatory

Every function signature (public AND private) MUST have complete type annotations on all parameters and return type.

```python
# ✅ Correct
def calculate_timer_color(fraction_remaining: float) -> tuple[int, int, int]:
    ...

# ❌ Rejected — missing return type
def calculate_timer_color(fraction_remaining: float):
    ...

# ❌ Rejected — missing parameter type
def calculate_timer_color(fraction_remaining) -> tuple[int, int, int]:
    ...
```

### 3.2 Union Syntax

Use PEP 604 pipe syntax, NOT `Optional` or `Union`:

```python
# ✅ Correct
def get_sample(self) -> SensorSample | None: ...

# ❌ Rejected
def get_sample(self) -> Optional[SensorSample]: ...
```

### 3.3 Collection Types

Use lowercase builtins (`list`, `dict`, `tuple`, `set`), NOT `typing.List` etc.:

```python
# ✅ Correct
options: list[Option]
metadata: dict[str, str | int | float | bool]

# ❌ Rejected
options: List[Option]
```

---

## 4. Docstrings

### 4.1 Every public class and public method MUST have a docstring.

```python
class GameEngine:
    """Master state machine and Pygame event loop for the Pulse scenario engine.

    Owns all subsystems (renderer, logger, audio, bridge) and drives the
    session from ID input through debrief.
    """

    def run(self) -> None:
        """Main Pygame event loop. Blocks until session completes or ESC pressed."""
```

### 4.2 Private methods SHOULD have a one-liner docstring if the name is not self-explanatory.

### 4.3 Format

- Single-line for trivial methods: `"""Return the current scenario."""`
- Multi-line for complex methods: summary line + blank line + details.
- No `Args:` / `Returns:` / `Raises:` sections in docstrings — the type annotations serve that purpose. Exception: document non-obvious `Raises` if the exception type isn't obvious from the signature.

---

## 5. Error Handling Strategy

### 5.1 Exception Hierarchy

All exceptions inherit from `PulseEngineError`. See DATA_MODELS_AND_CONTRACTS.md §6.

### 5.2 Rules

```python
# ✅ Correct — catch specific exception
try:
    self._transition_to(EngineState.DECISION)
except InvalidStateTransition as e:
    self.logger.log_event(GameEvent(..., metadata={"error": str(e)}))
    raise

# ❌ Rejected — bare except
try:
    ...
except:
    pass

# ❌ Rejected — catching Exception without re-raise
try:
    ...
except Exception:
    pass

# ❌ Rejected — swallowing the exception silently
try:
    self.audio.start_drone()
except AudioLoadError:
    pass  # BAD: silent failure masks missing asset
```

### 5.3 Exception Handling Locations

| Layer | Handling |
|---|---|
| `main.py` | Top-level `try/except` around `engine.run()`. Catches `PulseEngineError` → print error + clean shutdown. Catches `KeyboardInterrupt` → clean shutdown. |
| `engine.py` | Methods raise exceptions. The `run()` loop catches nothing — exceptions propagate to `main.py`. |
| `event_logger.py` | File I/O errors → raise `LoggerIOError`. Never swallow. |
| `audio.py` | Missing WAV → raise `AudioLoadError`. Pygame mixer errors → log and continue (audio is non-critical). |
| `scenarios.py` | Invalid domain lookup → raise `DomainNotFoundError`. |
| `sensor_bridge.py` | A port or recording failure on the reader thread is stored in `SerialBridge.error` and stops that thread; it never propagates into the frame loop. A bridge that was explicitly required (`--bridge serial`, `--bridge replay`) and cannot be established raises `BridgeUnavailableError`, which `main.py` turns into exit status 2 before the window opens. `--bridge auto` never raises for missing hardware. |

### 5.4 Never Use Assertions for Runtime Validation

```python
# ❌ Rejected — assert is stripped with -O flag
assert self.current_state == EngineState.DECISION

# ✅ Correct — explicit check
if self.current_state != EngineState.DECISION:
    raise InvalidStateTransition(self.current_state, EngineState.DECISION)
```

---

## 6. Logging & Output

### 6.1 No `print()` in any file except `main.py`

- `main.py` may use `print()` for CLI feedback (e.g., "Session complete, log saved to X", the sensor-bridge status line, and the no-telemetry warning on stderr).
- All other modules communicate through `EventLogger.log_event()`.

### 6.2 No Python `logging` module

The game engine has its own CSV event logger. Do not import or configure the stdlib `logging` module in any `src/game/` file. (The pipeline may use `logging`: `src/hardware/serial_reader.py` logs through a module logger, `logging.getLogger(__name__)`, never through the root logger.)

### 6.3 Debug Output

Temporary debug output during development: use `print(f"[DEBUG] {msg}")` guarded by an `if __debug__:` check. These MUST be removed before merge.

---

## 7. Architectural Anti-Patterns (Banned)

### 7.1 Banned: Mouse Events

```python
# ❌ BANNED — do not handle mouse events
if event.type == pygame.MOUSEBUTTONDOWN:
    ...

if event.type == pygame.MOUSEMOTION:
    ...

# ✅ Required — hide cursor and keep mouse events out of the queue
pygame.mouse.set_visible(False)
pygame.event.set_blocked([pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL])
pygame.event.set_grab(True)
```

**Rationale:** Mouse movement corrupts PPG/GSR biosignals. Locked decision.

### 7.2 Banned: Global Mutable State

```python
# ❌ BANNED
current_state = EngineState.INIT  # module-level mutable

# ✅ Required — state lives inside a class instance
class GameEngine:
    def __init__(self):
        self._current_state = EngineState.INIT
```

No module-level mutable variables. Constants (`UPPER_SNAKE_CASE`, frozen dataclasses) are fine.

### 7.3 Banned: Direct File Paths

```python
# ❌ BANNED — hardcoded path
f = open("C:/Users/AyushShetty/outputs/events.csv", "w")

# ✅ Required — Path objects, relative to project root
output_dir = Path("outputs/game_logs") / f"S{subject_id}_{session_ts}"
```

### 7.4 Banned: `time.sleep()` in the Main Thread

```python
# ❌ BANNED — blocks Pygame event loop, freezes UI
time.sleep(15)  # 15s rest

# ✅ Required — timer-based state transition
self._rest_timer_ms -= dt_ms
if self._rest_timer_ms <= 0:
    self._transition_to(EngineState.PRIMING)
```

### 7.5 Banned: Numerical Scores in UI

```python
# ❌ BANNED — locked decision
draw_text(f"Score: {score}")
draw_text(f"Points: {points}")

# ✅ Allowed — narrative consequence only
draw_text(consequence_text)  # "Your justification has been submitted..."
```

Exception: The MIST accuracy percentage in the *consequence phase* (not during play) is permitted because it's a validated social-comparison manipulation, not a gamification score. Any displayed percentage must be a possible value (the peer figure is capped at 100%).

Also banned: the words "score", "points" and "final score" in participant-facing text, even inside a diegetic skin.

### 7.8 Banned: Construct Labels in Participant-Facing Text

```python
# ❌ BANNED — tells the participant what is being manipulated or measured
draw_text(f"Paradigm: {scenario.paradigm}")          # "Digital Asch Conformity (Stoll et al., 2022)"
draw_text("[CONFORM]")                                # labels the response with the construct
draw_text("PANEL STATUS: UNRESPONSIVE (TSST PROTOCOL)")
draw_text("[ DIEGETIC TENSION DRONE ENGAGED ]")

# ✅ Required — in-world wording only
draw_text("PANEL IN SESSION • AWAITING YOUR RESPONSE")
```

**Rationale:** naming the paradigm, the manipulation or the target cohort creates demand characteristics and breaks the deception that MIST, Asch and TSST depend on. `Scenario.paradigm` exists for the registry, the logs and the documentation; no renderer may draw it.

### 7.9 Banned: Fabricated Sensor Readings

A UI element that claims to show live telemetry must show the real value or an explicit standby state. Hard-coded strings such as `"+1.5σ"` or `"NOMINAL (NO TREMOR)"` that do not come from the bridge are banned.

### 7.6 Banned: Random Without Seed Logging

```python
# ❌ BANNED — non-reproducible
random.shuffle(domains)

# ✅ Required — seed is logged
seed = int(time.time_ns() % (2**31))
rng = random.Random(seed)
rng.shuffle(domains)
self.logger.save_domain_order(domains, seed, start_ms)
```

### 7.7 Banned: Pygame `update()` Without Dirty-Rect OR Full Flip

```python
# ❌ Ambiguous
pygame.display.update()  # without args — which rects?

# ✅ Required — explicit full flip (simpler, fine at 60 FPS for our UI complexity)
pygame.display.flip()
```

---

## 8. Code Structure Rules

### 8.1 Maximum Function Length: 60 Lines

If a function exceeds 60 lines (excluding docstring and blank lines), it MUST be decomposed into private helper methods.

> **Known deviation (2026-10-02):** 19 functions in `src/game/` exceed this limit. 15 are the `_draw_skin_*` methods (134–304 lines each, one per simulation skin) and one is `draw_post_wait`. New code must comply; the existing skins are tracked in ARCHITECTURE_SPEC §7.3.

### 8.2 Maximum File Length: 500 Lines

If a file exceeds 500 lines, it MUST be split along logical boundaries. The rule is met across `src/` and `tests/` (largest: `tests/game/test_ui.py` 495, `src/game/scenarios.py` 428).

How the large modules were split (ADR-B6), and the pattern to follow when a module grows:

- **One skin, one module.** Each simulation skin is a class in `src/game/skins/<skin>.py` with a single `_draw_skin_<skin>` method. A new skin is a new file plus one base-class entry in `UIDomainSkins`.
- **Mixins over a shared typed base.** `UIRendererCore → UIComponents → {skins, UIScreens, UIPostWait} → UIDomainSkins → UIRenderer`, and `EngineBase → {EngineInputMixin, EngineTimerMixin} → GameEngine`. Every mixin inherits the base that declares the attributes it uses, so `mypy --strict` checks each module on its own. No `Protocol` shims, no `# type: ignore`.
- **Facade modules keep the import site stable.** `ui.py`, `engine.py` and `sensor_bridge.py` re-export the public names (`__all__`), so `from src.game.ui import UIRenderer` and `from src.game.engine import GameEngine, SessionConfig` never change.
- **A split moves code, it does not edit it.** A decomposition is verified by rendering before and after and comparing every frame (the UI split was pixel-identical on 248 frames).

### 8.3 No Nested Functions Deeper Than 2 Levels

```python
# ❌ Rejected
def outer():
    def middle():
        def inner():  # Too deep
            ...
```

### 8.4 Dataclasses: Prefer `frozen=True`

All configuration/data-transfer dataclasses MUST be `frozen=True`. Only `GameEvent` and mutable runner classes (MISTRunner, BARTRunner, etc.) are mutable.

### 8.5 String Formatting: f-strings Only

```python
# ❌ Rejected
"Hello %s" % name
"Hello {}".format(name)

# ✅ Required
f"Hello {name}"
```

---

## 9. Pygame-Specific Rules

### 9.1 Surface Management

- The main `screen` Surface is created in `main.py` and passed to `GameEngine.__init__()`.
- No module may call `pygame.display.set_mode()` except `main.py`.
- All rendering goes through `UIRenderer` methods — no direct `screen.blit()` calls in `engine.py`.

### 9.2 Event Loop

- Single `for event in pygame.event.get()` per frame, inside `engine.run()`.
- `pygame.QUIT` → immediate clean shutdown (close logger, quit pygame).
- `pygame.KEYDOWN` with `K_ESCAPE` → same as QUIT.
- All other key events → routed to `_handle_input()`.

### 9.3 Clock

- `pygame.time.Clock()` created once in `engine.run()`.
- `dt_ms = clock.tick(FPS)` called once per frame.
- `dt_ms` passed to `_update()` for all timer decrements.

### 9.4 Font Loading

- Load fonts ONCE in `UIRenderer.__init__()`.
- Resolve **exact font files** first (`segoeui.ttf` for body, `seguisb.ttf` for display, `consola.ttf` for mono) from the Windows Fonts directory, then fall back to `pygame.font.match_font()` over the chain `["segoeui", "arial", "helvetica", None]`.
- Do NOT rely on `pygame.font.SysFont(name, size)` for fallback: it never raises on an unknown name, so a `try/except` chain around it cannot advance, and `"segoeui"` resolves to Segoe UI **Light**.
- Display weight is semibold, never synthetic bold.
- `None` as final fallback → Pygame default font (always available).

### 9.5 Text Fit

- A single line drawn into a bounded container (tag, nameplate, badge, banner, card) MUST pass `max_width=` to `_draw_text()`. The renderer steps down the same-family font ladder and ellipsizes only as a last resort.
- `_draw_wrapped_text()` downscales within the same font family (sans stays sans) and marks truncation with an ellipsis. Silent truncation is a bug.
- Ink on an accent fill is chosen with `_ink_for(fill)` (WCAG luminance), not hard-coded white.

### 9.6 Corners

All rectangles use `border_radius=0`. Circles are reserved for avatars and dials.

### 9.7 Colour (ADR-B5)

The palette is `DESIGN-ferrari.md`, defined once in `constants.py` (ARCHITECTURE_SPEC §6.1).

```python
# ❌ BANNED — a chromatic literal (navy panel, purple accent, off-token red)
pygame.draw.rect(self.screen, (22, 28, 44), panel)
self._draw_text(tag, self.font_small, (180, 120, 255), pos)
self._draw_text("ERROR", self.font_small, (255, 80, 80), pos)

# ✅ Required — a token, or a neutral grey literal (r == g == b)
pygame.draw.rect(self.screen, (28, 28, 28), panel)
self._draw_text(tag, self.font_small, COLOR_TEXT_PRIMARY, pos)
self._draw_text("ERROR", self.font_small, COLOR_SEMANTIC_WARNING, pos)

# ✅ A dimmer or lighter shade of a token: blend toward a neutral, never invent a new hex
halo = self._mix(COLOR_ACCENT_CYAN, COLOR_BG, 0.65)
```

- **Six chromatic tokens, nothing else:** `COLOR_PRIMARY_ROSSO`, `COLOR_PRIMARY_ACTIVE`, `COLOR_SEMANTIC_WARNING`, `COLOR_ACCENT_CYAN`, `COLOR_ACCENT_YELLOW` (= `COLOR_TIMER_AMBER`), `COLOR_TIMER_GREEN`.
- **Rosso Corsa is for stress triggers, danger states and timer expiry.** It never fills a key prompt and never marks the participant's own selection.
- **Key prompts** are drawn with `_draw_key_badge(rect, label, selected=, enabled=)`: canvas plate, white label, Grigio border; inverted once chosen; muted while inert. Do not hand-draw a badge.
- **Selection** on a plain multiple-choice skin is a white border. A risk-coded skin may keep the option's own semantic accent (green / yellow / Rosso) on its border.
- **Blends between two tokens** are allowed only for the three continuous indicators: timer bar, composure bar, reward-chest glow.
- **Small alert text on a dark surface** uses `COLOR_SEMANTIC_WARNING` (contrast 4.5:1 on the canvas); Rosso Corsa is for strokes, fills and large type.
- `tests/game/test_palette.py` enforces all of this, down to the hue of every rendered pixel.

### 9.8 Sensor Bridge

- The engine never imports `serial` at module load. `sensor_bridge.py` imports pyserial lazily, so a machine without it still runs (on `StubBridge`).
- **Auto-detection may open only a port whose USB vendor ID is in `KNOWN_USB_SERIAL_VIDS`.** Opening an arbitrary COM port can reset or disturb another device.
- **Whoever owns the serial port records the stream.** `SerialBridge` always writes `sensor_stream.csv` in `serial_reader.py`'s column order; a session must never consume telemetry that is not also on disk.
- **Never show telemetry that is not live.** A bridge returns `None` for stale data; the UI then shows STANDBY (§7.9).
- Reader threads are daemon threads, own no engine state, and communicate only through the lock-protected `StreamBridge` buffer.
- Tests inject the port, the port lister and the clock. No test opens a real port or sleeps.

---

## 10. Quality Gates

A change is complete only when all three commands are clean, run from the repository root:

```powershell
uv run pytest -v                      # every test passes, no warnings
uv run mypy src/ tests/ --strict      # zero errors
uv run ruff check .                   # zero findings, whole repository
```

- **Zero-warning policy.** No finding is left "for later". There is no ruff configuration file: the rule set is the default of the ruff version pinned in `uv.lock`.
- **`# noqa` is a last resort and must explain itself:** name the rule and give the reason on the same line, e.g. `except Exception as e:  # noqa: BLE001 - one failed subject must not abort the batch`. A bare `# noqa` is rejected.
- **`# type: ignore` is not used in `src/`.** Tests may use it, with the error code, where they deliberately pass a wrong type or replace a method.
- **Lint- and type-only edits to `src/pipeline/`, `src/hardware/` and `validation/` must be shown to preserve behaviour** before they are accepted: same outputs on fixed inputs, or a structural comparison against the previous version. A real defect found on the way (for example a call with a missing argument) is fixed, named in the change description, and reported to the pipeline owner.
- **Pytest warnings.** One upstream deprecation (pygame importing `pkg_resources`) is filtered in `pyproject.toml`. Any other warning is a defect to fix, not to filter.
