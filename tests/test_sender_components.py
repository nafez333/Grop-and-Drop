'''Unit tests for sender framing, CPU worker cleanup, and transmission.'''
from __future__ import annotations
import multiprocessing as mp
import unittest
from unittest.mock import Mock
from shared.constants import END_OF_MESSAGE, SYNC_HEADER
from shared.protocol import Protocol, ProtocolError
from sender.cpu_load import CPULoadController
from sender.transmitter import Transmitter
class ProtocolTests(unittest.TestCase):
    '''Test protocol round trips and integrity checks.'''
    def setUp(self) -> None:
        '''Create a protocol instance for this test.'''
        self.protocol = Protocol()
    def test_encode_decode_ascii_and_utf8(self) -> None:
        '''Round-trip ASCII, UTF-8 and empty messages.'''
        for message in ("test", "Hello, receiver!", "مرحبا 🌍", ""):
            bits = self.protocol.encode_message(message)
            self.assertEqual(bits[:len(SYNC_HEADER)], SYNC_HEADER)
            self.assertEqual(bits[-len(END_OF_MESSAGE):], END_OF_MESSAGE)
            self.assertTrue(self.protocol.validate_frame(bits))
            self.assertEqual(self.protocol.decode_bits(bits), message)
    def test_crc_corruption_rejected(self) -> None:
        '''Reject payload corruption.'''
        frame = self.protocol.encode_message("integrity")
        frame[len(SYNC_HEADER)] ^= 1
        self.assertFalse(self.protocol.validate_frame(frame))
        with self.assertRaises(ProtocolError):
            self.protocol.decode_bits(frame)
    def test_wrong_markers_and_invalid_bits(self) -> None:
        '''Reject malformed markers and bits.'''
        frame = self.protocol.encode_message("x")
        frame[0] ^= 1
        self.assertFalse(self.protocol.validate_frame(frame))
        with self.assertRaises(TypeError):
            self.protocol.encode_message(42)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            self.protocol.decode_bits([0, 2, 1])

class CPULoadControllerTests(unittest.TestCase):
    '''Test target validation and worker process cleanup.'''
    def test_target_range_validation(self) -> None:
        '''Reject out-of-range targets.'''
        with self.assertRaises(ValueError):
            CPULoadController(-1)
        with self.assertRaises(ValueError):
            CPULoadController(101)
    def test_start_and_cleanup_reaps_workers(self) -> None:
        '''Exercise brief real worker activity and cleanup.'''
        controller = CPULoadController(target_percent=1)
        try:
            controller.start_load(0.12)
            self.assertEqual(controller._workers, [])
            controller._spawn_workers()
            controller.stop_load()
            self.assertEqual(mp.active_children(), [])
        finally:
            controller.cleanup()
    def test_idle_and_cpu_reading(self) -> None:
        '''Check idle and CPU metrics.'''
        controller = CPULoadController(target_percent=1)
        try:
            controller.idle(0.01)
            self.assertGreaterEqual(controller.get_cpu_percent(), 0.0)
        finally:
            controller.cleanup()

class TransmitterTests(unittest.TestCase):
    '''Test bit/state mapping and transmission logs.'''
    def setUp(self) -> None:
        '''Inject a mock CPU controller to avoid actual wait intervals.'''
        self.controller = Mock()
        self.transmitter = Transmitter(self.controller, Protocol())
        self.transmitter._save_log = Mock(return_value="test.json")
    def test_send_bits_maps_zero_idle_and_one_load(self) -> None:
        '''Map logical bits to CPU states and record them.'''
        self.assertTrue(self.transmitter.send_bits([1, 0, 1], 0.01))
        self.assertEqual(self.controller.start_load.call_count, 2)
        self.assertEqual(self.controller.idle.call_count, 1)
        bits = [item["bit"] for item in self.transmitter.get_transmission_log()["transmissions"]]
        self.assertEqual(bits, [1, 0, 1])
    def test_send_message_and_reject_invalid_bits(self) -> None:
        '''Transmit protocol frame and reject invalid bits.'''
        self.assertTrue(self.transmitter.send_message("ok", 0.01))
        count = len(self.transmitter.get_transmission_log()["transmissions"])
        self.assertEqual(count, len(Protocol().encode_message("ok")))
        with self.assertRaises(ValueError):
            self.transmitter.send_bits([0, 2], 0.01)
    def test_send_bit_controller_failure_returns_false(self) -> None:
        '''Return failure and stop load when the CPU controller errors.'''
        self.controller.start_load.side_effect = OSError("worker failed")
        self.assertFalse(self.transmitter.send_bit(1, 0.01))
        self.controller.stop_load.assert_called_once()

if __name__ == "__main__":
    unittest.main()
