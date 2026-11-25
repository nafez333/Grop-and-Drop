"Unit tests for the receiver's numerical helpers and protocol primitives." ""
import unittest
import numpy as np
from receiver.analysis.crc import calculate_crc, verify_crc
from receiver.analysis.sync_detector import cross_correlate, find_sync_header
from receiver.analysis.threshold import ThresholdCalculator, compute_threshold
from receiver.analysis.receiver import Receiver, samples_to_bits
from receiver.analysis.signal_processing import (
    baseline_correction,
    compute_magnitude,
    low_pass_filter,
    moving_average,
    normalize,
)


class ThresholdCalculatorTests(unittest.TestCase):
    def setUp(self):
        self.calculator = ThresholdCalculator()

    def test_idle_threshold_uses_noise_spread(self):
        threshold = self.calculator.compute_from_idle([1, 1, 1, 2, 2, 9], 0, 5)
        self.assertGreaterEqual(threshold, 1.0)
        self.assertLess(threshold, 3.0)

    def test_adaptive_threshold_preserves_length(self):
        result = self.calculator.compute_adaptive([0, 0, 10, 10, 0], 3)
        self.assertEqual(len(result), 5)
        self.assertTrue(all(np.isfinite(result)))

    def test_otsu_separates_two_clusters(self):
        threshold = self.calculator.compute_otsu([0, 0.1, 0.2, 8, 9, 10])
        self.assertGreater(threshold, 0.2)
        self.assertLess(threshold, 8)

    def test_percentile_and_shared_threshold(self):
        self.assertEqual(self.calculator.compute_percentile([0, 10], 50), 5)
        self.assertGreater(compute_threshold([0, 0, 0, 10], [(0, 3)]), 0)


class SyncDetectorTests(unittest.TestCase):
    def test_exact_pattern_and_one_bit_tolerance(self):
        pattern = [1, 0, 1, 1, 0]
        self.assertEqual(find_sync_header([0, 0] + pattern + [1], pattern), 2)
        self.assertEqual(find_sync_header([0, 0, 1, 0, 1, 0, 0, 1], pattern), 2)

    def test_rejects_too_many_errors(self):
        self.assertEqual(find_sync_header([0, 0, 0, 0, 0], [1, 1, 1, 1, 1]), -1)

    def test_cross_correlation_scores(self):
        self.assertEqual(cross_correlate([1, 0, 1], [1, 0]), [1.0, -1.0])


class CrcTests(unittest.TestCase):
    def test_standard_crc16_ccitt_check_vector(self):
        bits = [int(bit) for byte in b"123456789" for bit in f"{byte:08b}"]
        self.assertEqual(calculate_crc(bits), 0x29B1)
        self.assertTrue(verify_crc(bits, 0x29B1))
        self.assertFalse(verify_crc(bits, 0x29B0))

    def test_rejects_non_binary_data(self):
        with self.assertRaises(ValueError):
            calculate_crc([0, 2, 1])


class SignalProcessingTests(unittest.TestCase):
    def test_timed_samples_make_full_bit_count_and_decode_bytes(self):
        samples = [{"t": index * 0.05, "x": bit} for index, bit in enumerate([1, 1, 0, 0, 1, 1, 0, 0])]
        self.assertEqual(samples_to_bits(samples, 0.5, 0.1), [1, 0, 1, 0])
        self.assertEqual(Receiver().decode_bits([0, 1, 0, 0, 0, 0, 0, 1]), "A")
    def test_moving_average_and_numpy_input(self):
        result = moving_average(np.array([1.0, 2.0, 3.0]), 2)
        self.assertEqual(len(result), 3)
        self.assertAlmostEqual(result[1], 2.5)

    def test_low_pass_reduces_step(self):
        filtered = low_pass_filter([0, 0, 10, 10], 1, 20)
        self.assertGreater(filtered[2], 0)
        self.assertLess(filtered[2], 10)

    def test_baseline_magnitude_and_normalization(self):
        self.assertEqual(baseline_correction([10, 12], [10, 10]), [0.0, 2.0])
        self.assertAlmostEqual(compute_magnitude(2, 3, 6), 7.0)
        self.assertEqual(normalize([4, 4]), [0.0, 0.0])
        self.assertEqual(normalize([2, 4]), [0.0, 1.0])


if __name__ == "__main__":
    unittest.main()
