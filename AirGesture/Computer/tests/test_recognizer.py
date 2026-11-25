"""Unit tests for airgesture.core.recognizer using synthetic landmarks."""
from __future__ import annotations

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from airgesture.core.recognizer import GestureRecognizer, OPEN_PALM, FIST, PINCH, \
    INDEX_ONLY, TWO_FINGERS, THREE_FINGERS, FOUR_FINGERS, UNKNOWN
from airgesture.core.pose import analyze
from tests.synthetic import open_palm, fist, index_only, pinch, two_fingers, three_fingers, four_fingers


class TestRecognizer(unittest.TestCase):
    def setUp(self):
        self.rec = GestureRecognizer(sensitivity=0.5)

    def test_open_palm(self):
        det = self.rec.recognize(analyze(open_palm()))
        self.assertEqual(det.gesture, OPEN_PALM)

    def test_fist(self):
        det = self.rec.recognize(analyze(fist()))
        self.assertEqual(det.gesture, FIST)

    def test_pinch(self):
        det = self.rec.recognize(analyze(pinch()))
        self.assertEqual(det.gesture, PINCH)

    def test_index_only(self):
        det = self.rec.recognize(analyze(index_only()))
        self.assertEqual(det.gesture, INDEX_ONLY)

    def test_two_fingers(self):
        det = self.rec.recognize(analyze(two_fingers()))
        self.assertEqual(det.gesture, TWO_FINGERS)

    def test_three_fingers(self):
        det = self.rec.recognize(analyze(three_fingers()))
        self.assertEqual(det.gesture, THREE_FINGERS)

    def test_four_fingers(self):
        det = self.rec.recognize(analyze(four_fingers()))
        self.assertEqual(det.gesture, FOUR_FINGERS)

    def test_scale_invariant(self):
        """Same gesture at different scales must give the same label."""
        for pose_builder in (open_palm, fist, pinch, two_fingers):
            det_small = self.rec.recognize(analyze(pose_builder(scale=0.5)))
            det_large = self.rec.recognize(analyze(pose_builder(scale=1.5)))
            self.assertEqual(det_small.gesture, det_large.gesture)

    def test_rotation_invariant(self):
        """Rotated hands must give the same gesture."""
        for pose_builder in (open_palm, fist, pinch, two_fingers):
            det0 = self.rec.recognize(analyze(pose_builder(angle=0)))
            det45 = self.rec.recognize(analyze(pose_builder(angle=45)))
            det90 = self.rec.recognize(analyze(pose_builder(angle=90)))
            self.assertEqual(det0.gesture, det45.gesture)
            self.assertEqual(det0.gesture, det90.gesture)


if __name__ == "__main__":
    unittest.main()