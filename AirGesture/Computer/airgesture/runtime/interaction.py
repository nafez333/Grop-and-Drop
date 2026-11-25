"""Interaction state machine: gesture stream -> safe mouse actions.

This is the "brain" of the runtime and the component that fixes the original
design's biggest usability flaws. The old code triggered a click every time
*any* gesture followed a thumb-up, so scratching your nose clicked the window
under the cursor, and drags only worked while a fist was held.

New model (kept deliberately simple):

* Every gesture maps to an action in settings; the default profile is
  comfortable:
  ``Open palm -> move``, ``Pinch -> left click``, ``Two fingers -> right click``,
  ``Three fingers -> double click``, ``Fist -> pause``.
* Every action needs
  * the pose to be *stably held* for its ``activation_delay`` (anti-accident),
  * to respect its ``cooldown`` (anti double-fire),
  * and either the pose or its transition (rising edge) to be intentional.
* Gestures fire on **rising edge** (one action per pose), never on "whatever
  follows". Only continuous actions (move/scroll) are level-triggered.
* A *click ready* concept: while a click action is enabled and the hand is
  tracking, clicks may fire. Transitioning through a click pose -> `drag`
  action can turn the click into a drag (release on leaving the pose).
* Leaving every click pose and the cursor being idle guarantees released
  buttons; ``fail()``/``suspend()`` always release the button first.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from ..core.recognizer import FIST, OPEN_PALM
from ..core.settings import SettingsManager
from .mouse_controller import MouseController

CONTINUOUS_ACTIONS = ("move", "scroll")
CLICK_ACTIONS = ("left_click", "right_click", "double_click", "drag")


@dataclass
class InteractionState:
    active: bool = False
    mode: str = "auto"
    mode_unlocked: bool = False
    current_gesture: Optional[str] = None
    action: str = "idle"
    dragging: bool = False
    click_ready: bool = False
    last_message: str = ""
    last_error: str = ""
    paused: bool = False
    hand_present: bool = False
    gestures_suppressed: bool = False


class InteractionController:
    """Consumes stabilized gestures and drives the :class:`MouseController`."""

    def __init__(self, mouse: MouseController, settings: SettingsManager):
        self.mouse = mouse
        self.settings = settings
        self.state = InteractionState()
        self.mode = "auto"
        self._gesture_since: Optional[float] = None
        self._prev_gesture: Optional[str] = None
        self._fired_for_gesture: Optional[str] = None
        self._last_fire: dict[str, float] = {}
        self._scroll_last_y: Optional[float] = None
        self._drag_gesture: Optional[str] = None

    # ------------------------------------------------------------- lifecycle
    def set_mode(self, mode: str) -> None:
        self.mode = mode if mode in ("auto", "active", "always") else "auto"
        self.state.mode = self.mode

    def enable(self) -> None:
        """Start controlling the real mouse."""
        if self.state.active:
            return
        self.state.active = True
        self.state.mode_unlocked = self.mode != "active"
        self.state.paused = False
        self.state.last_message = (
            "Control started" if self.mode != "active" else "Show an open palm to start"
        )

    def disable(self, reason: str = "Control stopped") -> None:
        self.state.active = False
        self.state.mode_unlocked = False
        self.state.click_ready = False
        self.state.action = "idle"
        self._release("disable")
        self.state.last_message = reason
        self.mouse.reset_position()

    def suspend(self, reason: str) -> None:
        """Temporarily stop acting (tracking lost, window hidden based opt-out)."""
        self.state.gestures_suppressed = True
        self.state.click_ready = False
        if self.state.active:
            self._release(reason)
        self.state.last_message = reason

    def resume(self) -> None:
        self.state.gestures_suppressed = False
        self.state.last_message = "Resumed"

    def emergency_stop(self) -> None:
        self._release("emergency stop")
        self.state.active = False
        self.state.paused = True
        self.state.action = "idle"
        self.state.click_ready = False
        self.state.last_message = "Emergency stop - all mouse actions are off"
        self.mouse.reset_position()

    # ---------------------------------------------------------------- per-frame
    def update(
        self,
        gesture: Optional[str],
        confidence: float,
        now: Optional[float] = None,
        palm_xy: Optional[tuple] = None,
    ) -> None:
        """Called once per processed frame with the stabilised gesture."""
        now = time.time() if now is None else now
        st = self.state
        st.current_gesture = gesture
        st.hand_present = gesture is not None

        if not st.active:
            return

        if gesture is None:
            # Hand lost: release immediately, perform nothing.
            self._release("hand lost")
            st.action = "tracking_lost"
            st.click_ready = False
            st.dragging = False
            self._gesture_since = None
            self._prev_gesture = None
            self._fired_for_gesture = None
            return

        prev = self._prev_gesture
        if gesture != prev:
            self._gesture_since = now
            self._fired_for_gesture = None

        # Paused: nothing moves until the user shows the open palm again.
        # Showing the pause pose again while paused does nothing, so a stray
        # fist can never trap the user.
        if st.paused:
            st.action = "paused"
            if gesture == OPEN_PALM and self._gesture_since is not None and now - self._gesture_since >= 0.25:
                st.paused = False
                st.last_message = "Control resumed"
            self._prev_gesture = gesture
            return

        if st.gestures_suppressed:
            self._prev_gesture = gesture
            return

        # "Active" mode = hold-to-control. Only an open palm unlocks output;
        # leaving it re-locks. This makes the safest mode the default option.
        if self.mode == "active":
            if gesture == OPEN_PALM:
                if not st.mode_unlocked:
                    st.mode_unlocked = True
                    st.last_message = "Control active"
            elif not st.mode_unlocked:
                st.action = "waiting"
                st.click_ready = False
                self._prev_gesture = gesture
                return
        else:
            st.mode_unlocked = True

        cfg = self.settings.gesture(gesture)
        action = cfg.get("action", "none")
        enabled = cfg.get("enabled", False)
        delay = float(cfg.get("activation_delay", 0.12))
        cooldown = float(cfg.get("cooldown", 0.45))
        held = 0.0 if self._gesture_since is None else now - self._gesture_since

        # Switching to any other pose releases a drag started by a drag gesture.
        if st.dragging and self._drag_gesture and gesture != self._drag_gesture:
            self._release("drag pose released")
            st.dragging = False

        if not enabled or action in ("none", "pause"):
            # Rest pose / unbound pose: hold still, guarantee released buttons.
            self._release("rest")
            st.action = "paused_pose" if gesture == FIST else "idle"
            st.click_ready = False
            self._prev_gesture = gesture
            return

        st.click_ready = action in CLICK_ACTIONS

        if action == "move":
            st.action = "moving"
            if palm_xy is not None:
                try:
                    self.mouse.move_to(palm_xy[0], palm_xy[1], now)
                except Exception as exc:  # pragma: no cover - defensive
                    st.last_error = f"Cursor move failed: {exc}"
            self._scroll_last_y = None
            self._prev_gesture = gesture
            return

        if action == "scroll":
            st.action = "scrolling"
            self._handle_scroll(palm_xy)
            self._prev_gesture = gesture
            return

        # One-shot actions: fire once per pose (rising edge) after the hold delay.
        if st.dragging:
            st.action = "dragging"
            if palm_xy is not None:
                try:
                    self.mouse.move_to(palm_xy[0], palm_xy[1], now)
                except Exception as exc:  # pragma: no cover - defensive
                    st.last_error = f"Cursor move during drag failed: {exc}"
            self._prev_gesture = gesture
            return

        if self._fired_for_gesture == gesture:
            self._prev_gesture = gesture
            return
        if held < delay:
            self._prev_gesture = gesture
            return
        last = self._last_fire.get(gesture, -1e9)
        if now - last < cooldown:
            self._prev_gesture = gesture
            return

        fired = False
        if action == "left_click":
            fired = self.mouse.click("left")
            st.action = "click" if fired else st.action
        elif action == "right_click":
            fired = self.mouse.click("right")
            st.action = "right_click" if fired else st.action
        elif action == "double_click":
            fired = self.mouse.click("left", double=True)
            st.action = "double_click" if fired else st.action
        elif action == "drag":
            fired = self.mouse.start_drag()
            if fired:
                st.dragging = True
                self._drag_gesture = gesture
                st.action = "dragging"

        if fired:
            self._last_fire[gesture] = now
            self._fired_for_gesture = gesture
        self._prev_gesture = gesture

    # ------------------------------------------------------------ remote cmds
    def pause(self) -> None:
        """Explicit pause (toolbar button): release everything and freeze."""
        self._release("paused")
        self.state.paused = True
        self.state.dragging = False
        self.state.action = "paused"
        self.state.last_message = "Paused - show an open palm to resume"

    def toggle_pause(self) -> None:
        if self.state.paused:
            self.state.paused = False
            self.state.last_message = "Resumed"
        else:
            self.pause()

    # -------------------------------------------------------------- internals
    def _handle_scroll(self, palm_xy) -> None:
        if palm_xy is None:
            return
        y = palm_xy[1]
        if self._scroll_last_y is None:
            self._scroll_last_y = y
            return
        dy = y - self._scroll_last_y
        self._scroll_last_y = y
        if abs(dy) < 0.006:
            return
        self.mouse.scroll(int(round(dy * 120)))

    def _release(self, reason: str) -> None:
        try:
            if self.mouse.dragging:
                self.mouse.end_drag()
            elif self.mouse.any_button_down:
                self.mouse.release_all()
        except Exception:
            pass
        self._drag_gesture = None
        self._scroll_last_y = None
