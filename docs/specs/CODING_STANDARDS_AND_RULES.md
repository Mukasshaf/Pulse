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

- `main.py` may use `print()` for CLI feedback (e.g., "Session complete, log saved to X").
- All other modules communicate through `EventLogger.log_event()`.

### 6.2 No Python `logging` module

The game engine has its own CSV event logger. Do not import or configure the stdlib `logging` module in any `src/game/` file. (The ML pipeline in WSL2 may use `logging` — that's a different codebase.)

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

# ✅ Required — hide cursor
pygame.mouse.set_visible(False)
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

Exception: The MIST accuracy percentage in the *consequence phase* (not during play) is permitted because it's a validated social-comparison manipulation, not a gamification score.

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

### 8.2 Maximum File Length: 500 Lines

If a file exceeds 500 lines, it MUST be split along logical boundaries. (This is why `ui.py` and `ui_effects.py` are separate files.)

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
- Use `pygame.font.SysFont("segoeui", size)` with fallback chain: `["segoeui", "arial", "helvetica", None]`.
- `None` as final fallback → Pygame default font (always available).
