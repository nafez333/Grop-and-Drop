# Deterministic offline decoder aligned to standalone JavaScript.
from __future__ import annotations
import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Union
import numpy as np
from shared.constants import CRC_BITS, CRC_POLYNOMIAL, END_OF_MESSAGE, SAMPLE_RATE, SYNC_HEADER
from .crc import calculate_crc
from .signal_processing import low_pass_filter
from .sync_detector import find_sync_header
from .threshold import ThresholdCalculator
LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]

def decode_recording(recording: Dict[str, Any], mode: str = "otsu", options: Dict[str, Any] | None = None) -> Dict[str, Any]:
    options = options or {}
    try:
        samples = recording.get("samples")
        if not isinstance(samples, list):
            raise ValueError("recording.samples must be an array")
        if not samples:
            return {"threshold": None, "bits": [], "sync_index": -1, "crc": None, "crc_valid": False, "message": "", "gesture": None, "error": None}
        metadata = recording.get("metadata", {})
        rate = float(metadata.get("sample_rate_hz", SAMPLE_RATE))
        duration = float(metadata.get("bit_duration_seconds", 1.0))
        if rate <= 0 or duration <= 0:
            raise ValueError("sample rate and bit duration must be positive")
        axes = {axis: np.asarray([float(sample.get(axis, 0.0)) for sample in samples], dtype=np.float64) for axis in "xyz"}
        sensor = str(metadata.get("sensor_type", "magnetometer"))
        axis = "x" if sensor == "device_orientation" else max("xyz", key=lambda name: float(np.var(axes[name])))
        raw = axes[axis]
        baseline_count = max(1, min(len(raw), int(rate * .5)))
        baseline = float(np.median(raw[:baseline_count]))
        conditioned = np.asarray(low_pass_filter(np.abs(raw - baseline), min(8.0, rate * .45), rate), dtype=np.float64)
        idle_start = int(options.get("idle_start", metadata.get("idle_start_index", 0)))
        idle_end = int(options.get("idle_end", metadata.get("idle_end_index", max(1, int(rate * .5)))))
        calc = ThresholdCalculator()
        if mode == "otsu": threshold: Union[float, List[float]] = calc.compute_otsu(conditioned)
        elif mode == "idle": threshold = calc.compute_from_idle(conditioned, idle_start, idle_end)
        elif mode == "adaptive": threshold = calc.compute_adaptive(conditioned, int(options.get("window", 50)))
        elif mode == "percentile": threshold = calc.compute_percentile(conditioned, float(options.get("percentile", 75)))
        elif mode == "manual": threshold = float(options.get("manual", 0.0))
        else: raise ValueError(f"unknown threshold mode: {mode}")
        times = [float(sample.get("t", index / rate)) for index, sample in enumerate(samples)]
        origin = times[0]
        count = max(1, int(math.ceil(((times[-1] - origin) + 1e-9) / duration)))
        bits: List[int] = []
        for index in range(count):
            start, stop = origin + index * duration, origin + (index + 1) * duration
            indices = [i for i, value in enumerate(times) if start <= value < stop]
            if not indices:
                indices = [min(range(len(times)), key=lambda i: abs(times[i] - (start + stop) / 2))]
            avg = float(np.mean(conditioned[indices]))
            effective = float(threshold) if np.isscalar(threshold) else float(np.mean(np.asarray(threshold)[indices]))
            bits.append(int(avg > effective))
        sync = find_sync_header(bits, list(SYNC_HEADER))
        crc: int | None = None; valid = False; message = ""; gesture = None
        if sync >= 0:
            frame = bits[sync + len(SYNC_HEADER):]
            marker_len = len(END_OF_MESSAGE)
            if len(frame) >= CRC_BITS + marker_len and frame[-marker_len:] == list(END_OF_MESSAGE):
                crc_start = len(frame) - marker_len - CRC_BITS
                payload, check_bits = frame[:crc_start], frame[crc_start:crc_start + CRC_BITS]
                crc = 0
                for bit in check_bits: crc = (crc << 1) | bit
                valid = calculate_crc(payload) == crc
                if valid: message = _bits_to_text(payload)
                gesture = _gesture(payload)
            else:
                gesture = _gesture(frame)
        scalar_threshold: Any = float(threshold) if np.isscalar(threshold) else [float(value) for value in threshold]
        return {"threshold": scalar_threshold, "bits": bits, "sync_index": int(sync), "crc": crc,
                "crc_valid": bool(valid), "message": message, "gesture": gesture, "error": None}
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        LOGGER.debug("Offline decoding failed", exc_info=True)
        return {"threshold": None, "bits": [], "sync_index": -1, "crc": None, "crc_valid": False,
                "message": "", "gesture": None, "error": str(error)}

def _bits_to_text(bits: List[int]) -> str:
    raw = bytes(sum(bits[offset + bit] << (7 - bit) for bit in range(8)) for offset in range(0, len(bits) - 7, 8))
    return raw.decode("utf-8", errors="replace").rstrip("\x00")

def _gesture(bits: List[int]) -> str | None:
    try:
        table = json.loads((ROOT / "gestures" / "gestures.json").read_text(encoding="utf-8"))["gestures"]
        key = "".join(str(bit) for bit in bits)
        return next((name for name, entry in table.items() if "".join(str(bit) for bit in entry["bits"]) == key), None)
    except (OSError, KeyError, json.JSONDecodeError, TypeError):
        return None
