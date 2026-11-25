"""Unit tests for airgesture.core.geometry."""
from __future__ import annotations

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from airgesture.core import geometry as geo


class FakeLm:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class TestGeometry(unittest.TestCase):
    def test_dist(self):
        a = FakeLm(0, 0)
        b = FakeLm(3, 4)
        self.assertAlmostEqual(geo.dist(a, b), 5.0)

    def test_centroid(self):
        pts = [FakeLm(0, 0), FakeLm(2, 0), FakeLm(0, 2)]
        cx, cy = geo.centroid(pts)
        self.assertAlmostEqual(cx, 2 / 3)
        self.assertAlmostEqual(cy, 2 / 3)

    def test_clamp(self):
        self.assertEqual(geo.clamp(0.5, 0, 1), 0.5)
        self.assertEqual(geo.clamp(-1, 0, 1), 0)
        self.assertEqual(geo.clamp(2, 0, 1), 1)

    def test_lerp(self):
        self.assertAlmostEqual(geo.lerp(0, 10, 0.5), 5.0)


if __name__ == "__main__":
    unittest.main()