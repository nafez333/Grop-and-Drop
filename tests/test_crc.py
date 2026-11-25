"""Tests for CRC calculation and verification."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crc import compute_crc, verify_crc  # noqa: E402


class TestCRC(unittest.TestCase):
    """Comprehensive CRC tests."""

    def test_empty_bits(self):
        """CRC of empty bit sequence is 0."""
        self.assertEqual(compute_crc([]), 0)
        self.assertEqual(compute_crc(""), 0)

    def test_single_bit(self):
        """CRC of a single bit is in valid range."""
        crc = compute_crc([1])
        self.assertTrue(0 <= crc <= 255)

    def test_all_zeros(self):
        """CRC of all zeros is 0."""
        self.assertEqual(compute_crc([0, 0, 0, 0]), 0)
        self.assertEqual(compute_crc([0] * 64), 0)

    def test_crc_8bit_range(self):
        """CRC values are always in range 0-255."""
        for bits in ([1], [0, 1], [1, 0, 1, 0], [1] * 32):
            crc = compute_crc(bits)
            self.assertTrue(0 <= crc <= 255)

    def test_string_input(self):
        """compute_crc accepts both list and string input."""
        self.assertEqual(compute_crc([1, 0, 1, 0]), compute_crc("1010"))

    def test_verify_crc_true(self):
        """verify_crc returns True for matching CRC."""
        bits = [1, 0, 1, 0, 1, 1, 0, 0]
        crc = compute_crc(bits)
        self.assertTrue(verify_crc(bits, crc))

    def test_verify_crc_false(self):
        """verify_crc returns False for mismatched CRC."""
        bits = [1, 0, 1, 0, 1, 1, 0, 0]
        crc = compute_crc(bits)
        self.assertFalse(verify_crc(bits, (crc + 1) % 256))

    def test_bit_flip_changes_crc(self):
        """Flipping a bit changes the CRC (error detection)."""
        original = [1, 0, 1, 0, 1, 0, 1, 0]
        flipped = list(original)
        flipped[0] = 1 - flipped[0]
        self.assertNotEqual(compute_crc(original), compute_crc(flipped))

    def test_crc_failure_detection(self):
        """A corrupted bit stream fails CRC verification."""
        bits = [1, 1, 0, 0, 1, 1, 0, 0]
        crc = compute_crc(bits)
        # Corrupt one bit
        corrupted = list(bits)
        corrupted[3] = 1 - corrupted[3]
        self.assertFalse(verify_crc(corrupted, crc))


if __name__ == "__main__":
    unittest.main()
