"""Mouse control: coordinate mapping, smoothing, jump guard and safe buttons.

The controller deliberately knows nothing about hands or gestures. It receives
normalised screen targets (0..1) and exposes intent-level operations
(move, click, drag, right click, double click, scroll). This separation keeps
the mapping maths independently testable - ``test_mouse_mapping.py`` checks
0..1 -> screen pixels, clamping, deadzone, jump guard and button safety
without any camera or gesture involved.

Hard-won details
----------------
* All PyAutoGUI calls use ``_pause=False`` (the default global pause would add
  100ms latency per call).
* ``pyautogui.FAILSAFE`` stays enabled: moving the physical mouse to a screen
  corner raises ``FailSafeException`` which the caller treats as an emergency
  stop - a second, OS-level kill switch that always works.
* Every operation is serialized with a lock; a click can never be issued while
  a drag is being released.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple

try:
    import pyautogui
except Exception as exc:  # pragma: no cover - only when not installed
    pyautogui = None
    _IMPORT_ERROR = str(exc)
else:
    _IMPORT_ERROR = ""

from ..core.geometry import clamp


class MouseError(RuntimeError):
    pass


@dataclass
class MouseConfig:
    sensitivity: float = 1.35
    speed: float = 1.0
    smoothing: float = 0.45
    area_x: float = 0.62
    area_y: float = 0.58
    acceleration: float = 0.35
    jump_guard: float = 0.14
    deadzone: float = 0.004
    scroll_speed: float = 1.0
    natural_scroll: bool = True
    relative_mode: bool = False
    active_area: Tuple[float, float, float, float] = (0.18, 0.15, 0.82, 0.85)


class MouseController:
    def __init__(self, config: Optional[MouseConfig] = None):
        if pyautogui is None:
            raise MouseError(
                f"PyAutoGUI is required for mouse control ({_IMPORT_ERROR})."
            )
        self._lock = threading.RLock()
        self.config = config or MouseConfig()
        self.screen_w, self.screen_h = pyautogui.size()
        self._smooth_xy: Optional[Tuple[float, float]] = (
            None  # normalised smooth target
        )
        self._last_time: Optional[float] = None
        self._last_move_px: Optional[Tuple[int, int]] = None
        self._dragging = False
        self._button_down_any = False
        self.last_action: str = "idle"
        self.last_action_time: float = 0.0
        self.failsafe_action: str = ""

    # ------------------------------------------------------------------ config
    def update_config(self, config: MouseConfig) -> None:
        with self._lock:
            self.config = config

    @property
    def dragging(self) -> bool:
        return self._dragging

    @property
    def any_button_down(self) -> bool:
        return self._button_down_any

    def position(self) -> Tuple[int, int]:
        try:
            x, y = pyautogui.position()
            return int(x), int(y)
        except Exception:
            return self._last_move_px or (0, 0)

    # ------------------------------------------------------------------ mapping
    def map_to_screen(self, nx: float, ny: float) -> Tuple[int, int]:
        """Map normalised hand coordinates to screen pixels.

        ``nx``/``ny`` are 0..1 within the configured *active area* of the camera
        (so the user can rest their hand without reaching the frame border).
        Output is clamped to the screen.
        """
        cfg = self.config
        x0, y0, x1, y1 = cfg.active_area
        ax = clamp((nx - x0) / max(1e-6, (x1 - x0)), 0.0, 1.0)
        ay = clamp((ny - y0) / max(1e-6, (y1 - y0)), 0.0, 1.0)
        # Screen coordinate: (0,0) top-left
        sx = ax * self.screen_w
        sy = ay * self.screen_h
        return int(clamp(sx, 0, self.screen_w - 1)), int(
            clamp(sy, 0, self.screen_h - 1)
        )

    def _normalised_from_area(self, nx: float, ny: float) -> Tuple[float, float]:
        x0, y0, x1, y1 = self.config.active_area
        nx = clamp(nx, 0.0, 1.0)
        ny = clamp(ny, 0.0, 1.0)
        return (
            clamp((nx - x0) / max(1e-6, x1 - x0), 0.0, 1.0),
            clamp((ny - y0) / max(1e-6, y1 - y0), 0.0, 1.0),
        )

    # ------------------------------------------------------------------- motion
    def move_to(self, nx: float, ny: float, now: Optional[float] = None) -> bool:
        """Move the cursor towards normalised target ``(nx, ny)``.

        Applies exponential smoothing, a deadzone (ignore sub-pixel jitter) and
        the jump guard (large teleports are split/blocked). Returns ``True`` if
        the cursor moved.
        """
        now = time.time() if now is None else now
        with self._lock:
            cfg = self.config
            if self._last_time is None:
                self._last_time = now
            dt = clamp(now - self._last_time, 0.0, 0.5) or 1.0 / 60.0
            self._last_time = now

            tx, ty = self._normalised_from_area(nx, ny)

            if self._smooth_xy is None:
                self._smooth_xy = (tx, ty)
                return self._commit(tx, ty)

            px, py = self._smooth_xy
            dx, dy = tx - px, ty - py
            if abs(dx) < cfg.deadzone * 0.5 and abs(dy) < cfg.deadzone * 0.5:
                return False

            # Jump guard: cap the per-update displacement in active-area units.
            dist = (dx * dx + dy * dy) ** 0.5
            max_step = cfg.jump_guard
            if dist > max_step:
                scale = max_step / dist
                dx, dy = dx * scale, dy * scale

            # Smoothing: higher value = smoother (more inertia)
            smooth = clamp(cfg.smoothing, 0.0, 0.95)
            base_alpha = 1.0 - smooth * 0.82

            # Acceleration: fast movements respond faster, fine moves stay stable
            speed = (dx * dx + dy * dy) ** 0.5
            accel = cfg.acceleration * min(1.0, speed * 24.0)
            alpha = clamp((base_alpha + accel) * (dt * 60.0) ** 0.5, 0.05, 0.95)

            px += dx * alpha
            py += dy * alpha
            self._smooth_xy = (px, py)
            return self._commit(px, py)

    def _commit(self, px: float, py: float) -> bool:
        cfg = self.config
        # Sensitivity stretches the target away from the centre.
        cx = 0.5 + (px - 0.5) * cfg.sensitivity * cfg.speed
        cy = 0.5 + (py - 0.5) * cfg.sensitivity * cfg.speed
        sx = int(clamp(cx * self.screen_w, 0, self.screen_w - 1))
        sy = int(clamp(cy * self.screen_h, 0, self.screen_h - 1))
        try:
            pyautogui.moveTo(sx, sy, _pause=False)
        except pyautogui.FailSafeException:
            self.failsafe_action = "emergency_stop"
            return False
        self._last_move_px = (sx, sy)
        return True

    def reset_position(self) -> None:
        with self._lock:
            self._smooth_xy = None
            self._last_time = None

    # ------------------------------------------------------------------ buttons
    def click(self, button: str = "left", double: bool = False) -> bool:
        with self._lock:
            if self._dragging:
                return False  # never click while dragging
            try:
                if double:
                    pyautogui.doubleClick(button=button, _pause=False)
                    self.last_action = "double_click"
                else:
                    pyautogui.click(button=button, _pause=False)
                    self.last_action = f"{button}_click"
                self.last_action_time = time.time()
                return True
            except pyautogui.FailSafeException:
                self.failsafe_action = "emergency_stop"
                return False

    def start_drag(self) -> bool:
        with self._lock:
            if self._dragging:
                return False
            try:
                pyautogui.mouseDown(_pause=False)
            except pyautogui.FailSafeException:
                self.failsafe_action = "emergency_stop"
                return False
            self._dragging = True
            self._button_down_any = True
            self.last_action = "drag_start"
            self.last_action_time = time.time()
            return True

    def end_drag(self) -> bool:
        with self._lock:
            if not self._dragging:
                return False
            try:
                pyautogui.mouseUp(_pause=False)
            except Exception:
                pass
            self._dragging = False
            self._button_down_any = False
            self.last_action = "drag_end"
            self.last_action_time = time.time()
            return True

    def scroll(self, amount: int) -> bool:
        """Scroll ``amount`` wheel clicks. Positive = content moves down."""
        if amount == 0:
            return False
        with self._lock:
            clicks = int(clamp(amount * self.config.scroll_speed, -20, 20))
            if clicks == 0:
                return False
            if not self.config.natural_scroll:
                clicks = -clicks
            try:
                pyautogui.scroll(clicks, _pause=False)
            except pyautogui.FailSafeException:
                self.failsafe_action = "emergency_stop"
                return False
            self.last_action = "scroll"
            self.last_action_time = time.time()
            return True

    def release_all(self) -> None:
        """Safety net: guarantee no mouse button remains pressed."""
        with self._lock:
            if self._dragging:
                try:
                    pyautogui.mouseUp(_pause=False)
                except Exception:
                    pass
                self._dragging = False
            self._button_down_any = False

    def check_failsafe(self) -> bool:
        """Returns ``True`` if PyAutoGUI's corner failsafe was triggered."""
        if self.failsafe_action:
            self.failsafe_action = ""
            return True
        return False

    # -------------------------------------------------------------- diagnostics
    def consume_action(self) -> Optional[str]:
        if not self.last_action or time.time() - self.last_action_time > 1.6:
            return None
        action = self.last_action
        self.last_action = ""
        return action
