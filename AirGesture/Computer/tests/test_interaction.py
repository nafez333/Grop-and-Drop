"""Unit tests for airgesture.runtime.interaction using a fake mouse."""
from __future__ import annotations

import sys
import os
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from airgesture.core.recognizer import OPEN_PALM, FIST, PINCH, TWO_FINGERS, UNKNOWN
from airgesture.core.settings import SettingsManager
from airgesture.runtime.interaction import InteractionController, InteractionState


class FakeMouse:
    def __init__(self):
        self.clicks = []
        self.dragging = False
        self.button_down = False
        self.released = False

    def click(self, button, double=False):
        self.clicks.append((button, double))
        return True

    def start_drag(self):
        self.dragging = True
        self.button_down = True
        return True

    def end_drag(self):
        self.dragging = False
        self.released = True
        return True

    def release_all(self):
        self.button_down = False
        self.released = True

    def move_to(self, nx, ny, now=None):
        return True

    def reset_position(self):
        pass

    @property
    def any_button_down(self):
        return self.button_down

    @property
    def dragging_prop(self):
        return self.dragging


class TestInteraction(unittest.TestCase):
    def setUp(self):
        # Use isolated temp settings to avoid loading user config
        self.temp_dir = tempfile.TemporaryDirectory()
        settings_path = os.path.join(self.temp_dir.name, "settings.json")
        self.settings = SettingsManager(path=settings_path, autosave=False)
        self.mouse = FakeMouse()
        self.ctl = InteractionController(self.mouse, self.settings)
        self.ctl.enable()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pinch_fires_once(self):
        now = 1000.0
        # first frame starts the hold timer
        self.ctl.update(PINCH, 0.9, now=now, palm_xy=(0.5, 0.5))
        self.assertEqual(len(self.mouse.clicks), 0)
        # after activation_delay (default 0.12s) it fires once
        self.ctl.update(PINCH, 0.9, now=now + 0.2, palm_xy=(0.5, 0.5))
        self.assertEqual(len(self.mouse.clicks), 1)
        # repeating same pose should not fire again (rising edge)
        self.ctl.update(PINCH, 0.9, now=now + 0.4, palm_xy=(0.5, 0.5))
        self.assertEqual(len(self.mouse.clicks), 1)

    def test_no_click_on_transition_from_other_pose(self):
        now = 1000.0
        self.ctl.update(OPEN_PALM, 0.9, now=now, palm_xy=(0.5, 0.5))
        self.ctl.update(PINCH, 0.9, now=now + 0.2, palm_xy=(0.5, 0.5))
        # activation delay not met yet -> no click
        self.assertEqual(len(self.mouse.clicks), 0)
        # after delay it should fire
        self.ctl.update(PINCH, 0.9, now=now + 0.5, palm_xy=(0.5, 0.5))
        self.assertEqual(len(self.mouse.clicks), 1)

    def test_drag_always_released_on_emergency(self):
        now = 1000.0
        self.ctl.update(TWO_FINGERS, 0.9, now=now, palm_xy=(0.5, 0.5))
        # force drag state
        self.ctl.state.dragging = True
        self.mouse.dragging = True
        self.ctl.emergency_stop()
        self.assertTrue(self.mouse.released)

    def test_hand_lost_releases(self):
        now = 1000.0
        self.ctl.mouse.dragging = True
        self.ctl.state.dragging = True
        self.ctl.update(None, 0.0, now=now, palm_xy=None)
        self.assertTrue(self.ctl.mouse.released)


    def test_drag_moves_cursor_with_palm(self):
        now = 1000.0
        self.settings.update_gesture(FIST, action="drag", enabled=True, activation_delay=0.1)
        # First frame: starts hold timer
        self.ctl.update(FIST, 0.9, now=now, palm_xy=(0.5, 0.5))
        self.assertFalse(self.mouse.dragging)
        # Second frame: exceeds activation delay, triggers drag
        self.ctl.update(FIST, 0.9, now=now + 0.15, palm_xy=(0.5, 0.5))
        self.assertTrue(self.mouse.dragging)
        self.assertTrue(self.ctl.state.dragging)
        # Third frame: palm moves while still in fist -> cursor moves while dragging
        self.ctl.update(FIST, 0.9, now=now + 0.2, palm_xy=(0.6, 0.7))
        self.assertTrue(self.mouse.dragging)
        self.assertEqual(self.ctl.state.action, "dragging")
        # Releasing fist releases the drag
        self.ctl.update(OPEN_PALM, 0.9, now=now + 0.3, palm_xy=(0.6, 0.7))
        self.assertFalse(self.ctl.state.dragging)
        self.assertTrue(self.mouse.released)


if __name__ == "__main__":
    unittest.main()
