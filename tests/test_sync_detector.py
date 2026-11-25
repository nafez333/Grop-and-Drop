"""Tests for sync detector."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sync_detector import detect_sync, find_all_syncs  # noqa: E402


class TestSyncDetector(unittest.TestCase):
    """Sync pattern detection tests."""

    def test_clean_signal_at_start(self):
        """Sync detected at position 0 in a clean signal."""
        bits = [1, 1, 1, 1, 0, 1, 0, 1]
        pos = detect_sync(bits)
        self.assertEqual(pos, 0)

    def test_clean_signal_not_at_start(self):
        """Sync detected at a non-zero position (exact match)."""
        bits = [0, 0, 1, 1, 1, 1, 0, 0]
        pos = detect_sync(bits, max_errors=0)
        self.assertEqual(pos, 2)

    def test_one_bit_error(self):
        """Sync detected with 1 bit error within tolerance."""
        bits = [1, 1, 0, 1, 0, 0, 1, 0]  # bit 2 flipped
        pos = detect_sync(bits, max_errors=1)
        self.assertEqual(pos, 0)

    def test_two_bit_errors_exceed_tolerance(self):
        """Sync NOT detected when 2 errors exceed max_errors=1."""
        bits = [1, 0, 0, 1, 0, 0, 1, 0]  # bits 1 and 2 flipped
        pos = detect_sync(bits, max_errors=1)
        self.assertIsNone(pos)

    def test_no_sync_present(self):
        """Returns None when no sync pattern exists."""
        bits = [0, 0, 0, 0, 0, 0, 0, 0]
        pos = detect_sync(bits, max_errors=1)
        self.assertIsNone(pos)

    def test_empty_bits(self):
        """Returns None for empty bit stream."""
        self.assertIsNone(detect_sync([]))

    def test_find_all_syncs(self):
        """find_all_syncs returns all matching positions (exact match)."""
        bits = [1, 1, 1, 1, 0, 0, 1, 1, 1, 1]
        positions = find_all_syncs(bits, max_errors=0)
        self.assertEqual(positions, [0, 6])

    def test_short_stream(self):
        """Returns None when stream is shorter than pattern."""
        self.assertIsNone(detect_sync([1, 1, 1]))


if __name__ == "__main__":
    unittest.main()
