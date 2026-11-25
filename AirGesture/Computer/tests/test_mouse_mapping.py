"""Unit tests for airgesture.runtime.mouse_controller mapping (no camera, no real mouse)."""
from __future__ import annotations

import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from airgesture.runtime.mouse_controller import MouseController, MouseConfig


class TestMouseMapping(unittest.TestCase):
    def setUp(self):
        self.cfg = MouseConfig(active_area=(0.18, 0.15, 0.82, 0.85),
                               sensitivity=1.0, speed=1.0)
        self.cfg.screen_w = 1920
        self.cfg.screen_h = 1080
        self.mouse = MouseController(self.cfg)

    def test_map_to_screen_clamping(self):
        # center of active area -> center of screen
        x0, y0, x1, y1 = self.cfg.active_area
        mx = (x0 + x1) / 2
        my = (y0 + y1) / 2
        sx, sy = self.mouse.map_to_screen(mx, my)
        self.assertAlmostEqual(sx, 1920 / 2, delta=2)
        self.assertAlmostEqual(sy, 1080 / 2, delta=2)

        # out of range clamped
        sx, sy = self.mouse.map_to_screen(-1.0, 2.0)
        self.assertEqual(sx, 0)
        self.assertEqual(sy, 1079)

    def test_deadzone(self):
        # small moves below deadzone return False
        self.mouse._smooth_xy = (0.5, 0.5)
        self.mouse._last_time = 0.0
        import time
        result = self.mouse.move_to(0.5001, 0.5001, now=0.016)
        self.assertFalse(result)

    def test_jump_guard(self):
        # huge jump should be limited
        self.mouse._smooth_xy = (0.5, 0.5)
        self.mouse._last_time = 0.0
        import time
        self.mouse.move_to(0.9, 0.9, now=0.016)
        # should not teleport fully; jump guard caps displacement
        self.assertLess(abs(self.mouse._smooth_xy[0] - 0.5), 0.14)


if __name__ == "__main__":
    unittest.main()