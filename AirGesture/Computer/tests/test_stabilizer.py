"""Unit tests for airgesture.core.stabilizer."""
from __future__ import annotations

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from airgesture.core.recognizer import Detection, OPEN_PALM, FIST, UNKNOWN
from airgesture.core.stabilizer import GestureStabilizer


class TestStabilizer(unittest.TestCase):
    def test_flicker_suppressed(self):
        st = GestureStabilizer(min_frames=3, switch_threshold=0.5, hold_advantage=1.3, max_gap_s=0.6)
        now = 1000.0
        # Establish open_palm as current
        for i in range(5):
            st.update(Detection(OPEN_PALM, 0.9, {}), now + i * 0.1)
        self.assertEqual(st.current, OPEN_PALM)
        # Send fist for just 1 frame - should not switch yet (min_frames=3)
        st.update(Detection(FIST, 0.9, {}), now + 0.6)
        self.assertEqual(st.current, OPEN_PALM)
        # Send fist for 3 frames - should switch
        for i in range(3):
            st.update(Detection(FIST, 0.9, {}), now + 0.7 + i * 0.1)
        self.assertEqual(st.current, FIST)

    def test_rising_edge_accepted(self):
        st = GestureStabilizer(min_frames=1, switch_threshold=0.3, hold_advantage=1.0, max_gap_s=0.6)
        now = 1000.0
        st.update(Detection(FIST, 0.9, {}), now)
        self.assertEqual(st.current, FIST)

    def test_brief_dropout_tolerated(self):
        st = GestureStabilizer(min_frames=1, switch_threshold=0.3, hold_advantage=1.0, max_gap_s=0.6)
        now = 1000.0
        st.update(Detection(OPEN_PALM, 0.9, {}), now)
        self.assertEqual(st.current, OPEN_PALM)
        # brief gap shorter than max_gap_s
        st.update(None, now + 0.2)
        self.assertEqual(st.current, OPEN_PALM)

    def test_long_dropout_none(self):
        st = GestureStabilizer(min_frames=1, switch_threshold=0.3, hold_advantage=1.0, max_gap_s=0.3)
        now = 1000.0
        st.update(Detection(OPEN_PALM, 0.9, {}), now)
        self.assertEqual(st.current, OPEN_PALM)
        # gap longer than max_gap_s
        result = st.update(None, now + 1.0)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()