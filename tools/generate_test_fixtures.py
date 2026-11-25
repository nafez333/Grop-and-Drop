"Generate deterministic synthetic recordings for receiver parity tests." ""
from __future__ import annotations
import json
import logging
import math
import random
import sys
from pathlib import Path
from typing import Any, Sequence
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shared.protocol import Protocol
from shared.constants import SAMPLE_RATE

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures"


def _recording(
    name: str,
    bits: Sequence[int],
    duration: float = 1.0,
    *,
    noise: float = 0.0,
    drift: bool = False,
    jitter: bool = False,
    seed: int = 23,
    empty: bool = False,
    one_sample: bool = False
) -> dict[str, Any]:
    rng = random.Random(seed)
    rate = float(SAMPLE_RATE)
    samples: list[dict[str, float]] = []
    if not empty:
        # One idle bit is intentionally prefixed to provide the calibration segment.
        all_bits = [0] + list(bits)
        count = int(round(rate * duration * len(all_bits)))
        for i in range(count):
            nominal_t = i / rate
            t = nominal_t + (rng.uniform(-0.006, 0.006) if jitter else 0.0)
            bit = all_bits[min(len(all_bits) - 1, int(nominal_t / duration))]
            baseline = (
                48.0
                + (0.02 * i if drift else 0.0)
                + (0.35 * math.sin(i / 110) if drift else 0.0)
            )
            noise_value = rng.gauss(0, noise)
            level = baseline + (8.0 if bit else 0.0) + noise_value
            samples.append(
                {
                    "t": round(t, 6),
                    "x": level,
                    "y": baseline + rng.gauss(0, noise * 0.1),
                    "z": baseline + rng.gauss(0, noise * 0.1),
                }
            )
        if one_sample:
            samples = samples[:1]
    return {
        "metadata": {
            "name": name,
            "timestamp": "2026-01-01T00:00:00Z",
            "sample_rate_hz": rate,
            "bit_duration_seconds": duration,
            "sensor_type": "magnetometer",
            "idle_start_index": 0,
            "idle_end_index": max(2, int(rate * duration)),
            "threshold_percentile": 75,
        },
        "samples": samples,
    }


def generate() -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    protocol = Protocol()
    gesture_table = json.loads(
        (ROOT / "gestures" / "gestures.json").read_text(encoding="utf-8")
    )["gestures"]
    clean = protocol.encode_message("A")
    no_sync = [0] * 32 + [1, 1, 0, 0, 1, 0, 0, 1] * 4
    corrupted = list(clean)
    corrupted[len(protocol.sync_header) + 2] ^= 1
    entries = {
        "clean_square_wave.json": _recording("clean_square_wave", clean),
        "noisy_low_snr.json": _recording("noisy_low_snr", clean, noise=4.0),
        "baseline_drift.json": _recording("baseline_drift", clean, drift=True),
        "missing_sync.json": _recording("missing_sync", no_sync),
        "corrupted_crc.json": _recording("corrupted_crc", corrupted),
        "short_bit_duration.json": _recording(
            "short_bit_duration", protocol.encode_message("S"), duration=0.25
        ),
        "long_bit_duration.json": _recording(
            "long_bit_duration", protocol.encode_message("L"), duration=2.0
        ),
        "variable_sample_rate.json": _recording(
            "variable_sample_rate", clean, jitter=True
        ),
        "empty_recording.json": _recording("empty_recording", [], empty=True),
        "single_sample.json": _recording("single_sample", [0], one_sample=True),
        "gesture_frame.json": _recording(
            "gesture_frame",
            protocol.sync_header
            + gesture_table["wave"]["bits"]
            + _crc_bits(protocol, gesture_table["wave"]["bits"])
            + protocol.end_marker,
        ),
        "text_frame.json": _recording(
            "text_frame", protocol.encode_message("Hi مرحبا")
        ),
    }
    result = []
    for name, data in entries.items():
        path = OUT / name
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        result.append(path)
    LOGGER.info("Generated %d recording fixtures", len(result))
    return result


def _crc_bits(protocol: Protocol, bits: Sequence[int]) -> list[int]:
    value = protocol.calculate_crc(list(bits))
    return [(value >> shift) & 1 for shift in range(15, -1, -1)]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    generate()
