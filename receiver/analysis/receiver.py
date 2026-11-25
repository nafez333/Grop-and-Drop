"""Load a receiver JSON recording and decode its framed digital signal."""
from __future__ import annotations
import argparse
import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np
try:
    from .signal_processing import baseline_correction, low_pass_filter
    from .threshold import ThresholdCalculator, compute_threshold as _compute_threshold
    from .sync_detector import SYNC_HEADER, find_sync_header
    from .crc import CRC_POLYNOMIAL, calculate_crc, verify_crc
except ImportError:  # Allow `python receiver/analysis/receiver.py --file ...`
    from signal_processing import baseline_correction, low_pass_filter
    from threshold import ThresholdCalculator, compute_threshold as _compute_threshold
    from sync_detector import SYNC_HEADER, find_sync_header
    from crc import CRC_POLYNOMIAL, calculate_crc, verify_crc
LOGGER = logging.getLogger(__name__)
try:
    from shared.constants import BIT_DURATION_DEFAULT as _BIT_DURATION_DEFAULT, SAMPLE_RATE as _SAMPLE_RATE
except (ImportError, ModuleNotFoundError):
    _BIT_DURATION_DEFAULT, _SAMPLE_RATE = 0.1, 20.0
BIT_DURATION_DEFAULT = float(_BIT_DURATION_DEFAULT)
SAMPLE_RATE = float(_SAMPLE_RATE)


def compute_threshold(data: list, idle_segments: list) -> float:
    """Agent-facing threshold API."""
    return _compute_threshold(data, idle_segments)


def _sample_value(sample: Any, axis: str = "x") -> float:
    if isinstance(sample, dict):
        return float(sample.get(axis, sample.get("z", 0.0)))
    return float(sample)


def samples_to_bits(data: list, threshold: Union[float, Sequence[float]], bit_duration: float,
                    sample_rate: Optional[float] = None) -> List[int]:
    """Convert samples to one bit per bit interval using interval means."""
    if bit_duration <= 0:
        raise ValueError("bit_duration must be positive")
    if not data:
        return []
    if isinstance(data[0], dict) and "t" in data[0]:
        times = [float(item["t"]) for item in data]
        values = [_sample_value(item) for item in data]
        origin = times[0]
        end = times[-1] - origin
        count = max(1, int(math.ceil((end + 1e-9) / bit_duration)))
        result: List[int] = []
        for index in range(count):
            start, stop = origin + index * bit_duration, origin + (index + 1) * bit_duration
            interval = [value for time, value in zip(times, values) if start <= time < stop]
            indices = [j for j, time in enumerate(times) if start <= time < stop]
            if not interval:
                nearest = min(range(len(times)), key=lambda sample_index: abs(times[sample_index] - (start + stop) / 2.0))
                interval = [values[nearest]]
                indices = [nearest]
            threshold_value = float(threshold) if np.isscalar(threshold) else float(np.mean(np.asarray(threshold)[indices]))
            result.append(int(float(np.mean(interval)) > threshold_value))
        return result
    values = [_sample_value(item) for item in data]
    effective_rate = float(sample_rate if sample_rate is not None else SAMPLE_RATE) or 20.0
    samples_per_bit = max(1, int(round(bit_duration * effective_rate)))
    result = []
    for start in range(0, len(values), samples_per_bit):
        section = values[start:start + samples_per_bit]
        if not section:
            continue
        level = float(threshold) if np.isscalar(threshold) else float(np.mean(np.asarray(threshold)[start:start + len(section)]))
        result.append(int(float(np.mean(section)) > level))
    return result

class Receiver:
    """Signal receiver. Protocol is optional for standalone recordings/tests."""
    def __init__(self, protocol: Any = None) -> None:
        self.protocol = protocol
        self.logger = logging.getLogger(f"{__name__}.Receiver")

    def decode_bits(self, bits: List[int]) -> str:
        """Decode complete MSB-first bytes to UTF-8 text."""
        valid_bits = [int(bit) for bit in bits]
        if any(bit not in (0, 1) for bit in valid_bits):
            raise ValueError("bits must contain only 0 and 1")
        byte_count = len(valid_bits) // 8
        raw = bytes(sum(valid_bits[offset + bit] << (7 - bit) for bit in range(8))
                    for offset in range(0, byte_count * 8, 8))
        return raw.decode("utf-8", errors="replace").rstrip("\x00")

    def _decode_payload(self, payload_bits: List[int]) -> str:
        if self.protocol is not None:
            validator = getattr(self.protocol, "validate_frame", None) or getattr(self.protocol, "validate", None)
            if callable(validator):
                try:
                    result = validator(payload_bits)
                    if isinstance(result, str):
                        return result
                    if isinstance(result, dict):
                        return str(result.get("message", result.get("payload", "")))
                except (ValueError, TypeError, AttributeError):
                    self.logger.debug("Shared protocol validation rejected payload", exc_info=True)
        return self.decode_bits(payload_bits)

    def decode_file(self, json_path: str) -> dict:
        """Load a JSON recording and run conditioning, bit extraction and frame decoding."""
        result: Dict[str, Any] = {"message": "", "gesture": None, "bits": [], "confidence": 0.0,
                                  "crc_valid": False, "sync_found": False}
        try:
            with open(json_path, "r", encoding="utf-8") as recording_file:
                recording = json.load(recording_file)
            samples = recording["samples"]
            metadata = recording.get("metadata", {})
            if not isinstance(samples, list) or not samples:
                raise ValueError("recording samples must be a non-empty list")
            sample_rate = float(metadata.get("sample_rate_hz", SAMPLE_RATE))
            bit_duration = float(metadata.get("bit_duration_seconds", BIT_DURATION_DEFAULT))
            if sample_rate <= 0 or bit_duration <= 0:
                raise ValueError("sample rate and bit duration must be positive")
            axes = {axis: np.asarray([float(item.get(axis, 0.0)) for item in samples], dtype=float)
                    for axis in ("x", "y", "z")}
            sensor_type = str(metadata.get("sensor_type", "magnetometer"))
            axis = "x" if sensor_type == "device_orientation" else max(axes, key=lambda name: float(np.var(axes[name])))
            values = axes[axis]
            baseline_count = max(1, min(len(values), int(sample_rate * 0.5)))
            baseline = float(np.median(values[:baseline_count]))
            conditioned = np.abs(values - baseline)
            conditioned = np.asarray(low_pass_filter(conditioned, min(8.0, sample_rate * 0.45), sample_rate))
            threshold = ThresholdCalculator().compute_otsu(conditioned.tolist())
            transformed = [dict(sample, x=float(value), y=float(value), z=float(value))
                           for sample, value in zip(samples, conditioned.tolist())]
            bits = samples_to_bits(transformed, threshold, bit_duration)
            result["bits"] = bits
            sync_index = find_sync_header(bits, list(SYNC_HEADER))
            result["sync_found"] = sync_index >= 0
            if sync_index < 0:
                result["confidence"] = min(0.49, float(np.mean(conditioned > threshold)))
                return result
            payload_start = sync_index + len(SYNC_HEADER)
            frame_bits = bits[payload_start:]
            if len(frame_bits) >= 16:
                payload_bits, checksum_bits = frame_bits[:-16], frame_bits[-16:]
                received_crc = 0
                for bit in checksum_bits:
                    received_crc = (received_crc << 1) | int(bit)
                result["crc_valid"] = verify_crc(payload_bits, received_crc)
                if result["crc_valid"]:
                    result["message"] = self._decode_payload(payload_bits)
                else:
                    result["message"] = self._decode_payload(frame_bits) if self.protocol is not None else ""
            else:
                result["message"] = self._decode_payload(frame_bits)
            result["confidence"] = min(1.0, max(0.0, 0.5 + (1.0 - abs(float(np.mean(conditioned > threshold)) - 0.5)) * 0.5))
            try:
                from gesture_engine import GestureEngine
                gesture_engine = GestureEngine()
                gesture = gesture_engine.decode(bits[payload_start:])
                result["gesture"] = getattr(gesture, "name", str(gesture)) if gesture else None
            except (ImportError, AttributeError, TypeError):
                result["gesture"] = None
            return result
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            self.logger.exception("Could not decode recording %s", json_path)
            result["error"] = str(error)
            return result

def decode_file(json_path: str) -> dict:
    """Module-level interface expected by other agents."""
    return Receiver().decode_file(json_path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Decode a magnetometer receiver JSON recording")
    parser.add_argument("--file", required=True, help="Path to recording JSON")
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    result = Receiver().decode_file(arguments.file)
    LOGGER.info("Decoded result: %s", json.dumps(result, ensure_ascii=False))
    return 0 if "error" not in result else 1
if __name__ == "__main__":
    raise SystemExit(main())
