"""Tests for Protocol encode/decode, frame validation, and sync header detection."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocol import Protocol, SYNC_HEADER, FRAME_END_MARKER  # noqa: E402
from sync_detector import detect_sync  # noqa: E402
from crc import compute_crc, verify_crc  # noqa: E402


class TestProtocol(unittest.TestCase):
    """Test Protocol encode/decode round trips and frame validation."""

    def setUp(self) -> None:
        self.protocol = Protocol()

    def test_encode_decode_round_trip(self):
        """Encode a message then decode it back — should match."""
        messages = ["hello", "wave", "A", "", "12345", "hi there!"]
        for msg in messages:
            with self.subTest(message=msg):
                bits = self.protocol.encode(msg)
                decoded = self.protocol.decode(bits)
                self.assertEqual(decoded, msg)

    def test_frame_validation(self):
        """validate_frame accepts well-formed frames and rejects malformed ones."""
        bits = self.protocol.encode("test")
        self.assertTrue(self.protocol.validate_frame(bits))

        # Truncated frame
        self.assertFalse(self.protocol.validate_frame(bits[:4]))
        # Wrong sync header
        bad = [0, 0, 0, 0] + bits[4:]
        self.assertFalse(self.protocol.validate_frame(bad))

    def test_sync_header_constant(self):
        """SYNC_HEADER matches the expected pattern."""
        self.assertEqual(SYNC_HEADER, [1, 1, 1, 1])

    def test_end_marker_constant(self):
        """FRAME_END_MARKER matches the expected pattern."""
        self.assertEqual(FRAME_END_MARKER, [1, 1, 1, 0])


class TestCRC(unittest.TestCase):
    """Test CRC calculation and verification."""

    def test_crc_deterministic(self):
        """CRC of the same bits is always the same."""
        bits = [1, 0, 1, 0, 1, 0, 1, 0]
        self.assertEqual(compute_crc(bits), compute_crc(bits))

    def test_crc_different_bits_different(self):
        """Different bit sequences produce different CRCs (usually)."""
        c1 = compute_crc([0, 0, 0, 0])
        c2 = compute_crc([1, 1, 1, 1])
        self.assertNotEqual(c1, c2)

    def test_verify_crc(self):
        """verify_crc returns True when CRC matches, False otherwise."""
        bits = [1, 0, 1, 0, 1, 0, 1, 0]
        crc = compute_crc(bits)
        self.assertTrue(verify_crc(bits, crc))
        self.assertFalse(verify_crc(bits, (crc + 1) % 256))


class TestSyncDetector(unittest.TestCase):
    """Test sync header detection."""

    def test_clean_signal(self):
        """Sync is detected at the start of a clean signal."""
        bits = [1, 1, 1, 1, 0, 0, 1, 0]
        pos = detect_sync(bits)
        self.assertEqual(pos, 0)

    def test_sync_with_one_bit_error(self):
        """Sync is detected with up to 1 bit error."""
        bits = [1, 1, 0, 1, 0, 0, 1, 0]  # third bit flipped
        pos = detect_sync(bits, max_errors=1)
        self.assertEqual(pos, 0)

    def test_sync_detection_failure(self):
        """Sync is not found when errors exceed tolerance."""
        bits = [0, 0, 0, 0, 0, 0, 1, 0]  # 4 errors vs sync pattern
        pos = detect_sync(bits, max_errors=1)
        self.assertIsNone(pos)

    def test_sync_not_at_start(self):
        """Sync is found even when not at position 0 (exact match)."""
        bits = [0, 0, 1, 1, 1, 1, 0, 0]
        pos = detect_sync(bits, max_errors=0)
        self.assertEqual(pos, 2)


if __name__ == "__main__":
    unittest.main()
