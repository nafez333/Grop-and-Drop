"""Integration tests for the full gesture pipeline."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gestures import GestureEngine  # noqa: E402
from protocol import Protocol  # noqa: E402
from transmitter import Transmitter, CPULoadController  # noqa: E402
from receiver import Receiver, decode_file  # noqa: E402
from crc import compute_crc  # noqa: E402


class TestFullPipeline(unittest.TestCase):
    """Full pipeline: encode message -> transmit -> receive -> decode -> verify."""

    def test_message_pipeline(self):
        """Encode a message, simulate transmission, decode, and verify."""
        engine = GestureEngine(config_path="gestures/gestures.json")
        protocol = Protocol()
        cpu_controller = CPULoadController()
        transmitter = Transmitter(cpu_controller=cpu_controller, bit_duration=0.01)
        receiver = Receiver()

        message = "hello"
        bits = protocol.encode(message)

        # Transmit
        ok = transmitter.send_bits(bits)
        self.assertTrue(ok)

        # Receive (simulate channel)
        receiver.feed_bits(transmitter.sent_bits)
        received = receiver.receive_bits(len(transmitter.sent_bits))

        # Decode
        decoded = protocol.decode(received)
        self.assertEqual(decoded, message)

    def test_gesture_pipeline(self):
        """Gesture name -> bits -> transmit -> receive -> gesture name."""
        engine = GestureEngine(config_path="gestures/gestures.json")
        transmitter = Transmitter(bit_duration=0.01)
        receiver = Receiver()

        gesture_name = "wave"
        bits = engine.get_bits(gesture_name)

        # Transmit
        transmitter.send_bits(bits)

        # Receive
        receiver.feed_bits(transmitter.sent_bits)
        received = receiver.receive_bits(len(transmitter.sent_bits))

        # Reverse lookup
        recognized = engine.get_gesture(received)
        self.assertEqual(recognized, gesture_name)

    def test_crc_in_pipeline(self):
        """CRC verification detects corrupted transmissions."""
        engine = GestureEngine(config_path="gestures/gestures.json")
        protocol = Protocol()
        transmitter = Transmitter(bit_duration=0.01)

        bits = protocol.encode("test")
        crc = compute_crc(bits[: -12])  # CRC over payload portion

        # Transmit clean
        transmitter.send_bits(bits)
        clean = list(transmitter.sent_bits)

        # Corrupt a bit
        corrupted = list(clean)
        corrupted[5] = 1 - corrupted[5]

        # Clean passes frame validation
        self.assertTrue(protocol.validate_frame(clean))
        # Corrupted may still pass structural validation but CRC will differ
        self.assertNotEqual(compute_crc(clean), compute_crc(corrupted))


class TestRecordingFile(unittest.TestCase):
    """Test decode_file with a temporary recording JSON."""

    def test_decode_file(self):
        """decode_file parses a recording JSON correctly."""
        record = {
            "version": "1.0",
            "timestamp": "2026-01-01T00:00:00Z",
            "bits": [1, 1, 1, 1, 0, 0, 0, 1],
            "gestures": ["wave"],
            "metadata": {"source": "test"},
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            import json as _json
            _json.dump(record, f)
            tmp_path = f.name
        try:
            result = decode_file(tmp_path)
            self.assertEqual(result["version"], "1.0")
            self.assertEqual(result["bits"], [1, 1, 1, 1, 0, 0, 0, 1])
            self.assertEqual(result["gestures"], ["wave"])
            self.assertEqual(result["metadata"]["source"], "test")
        finally:
            os.unlink(tmp_path)

    def test_decode_file_missing(self):
        """decode_file raises FileNotFoundError for missing file."""
        with self.assertRaises(FileNotFoundError):
            decode_file("/nonexistent/path/recording.json")


if __name__ == "__main__":
    unittest.main()
