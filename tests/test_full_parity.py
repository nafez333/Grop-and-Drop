"Full fixture-by-threshold-mode parity tests for Python and JavaScript." ""
from __future__ import annotations
import json
import math
import subprocess
import unittest
from pathlib import Path
from typing import Any
from receiver.analysis.offline_pipeline import decode_recording

ROOT = Path(__file__).resolve().parents[1]
MODES = ("otsu", "idle", "adaptive", "percentile", "manual")
FIXTURE_NAMES = ("clean_square_wave.json", "noisy_low_snr.json", "baseline_drift.json", "missing_sync.json", "corrupted_crc.json", "short_bit_duration.json", "long_bit_duration.json", "variable_sample_rate.json", "empty_recording.json", "single_sample.json", "gesture_frame.json", "text_frame.json")
FIXTURES = [ROOT / "tests" / "fixtures" / name for name in FIXTURE_NAMES]


class TestFullParity(unittest.TestCase):
    def test_fixture_mode_matrix(self) -> None:
        cases = 0
        failures = []
        for path in FIXTURES:
            recording = json.loads(path.read_text(encoding="utf-8"))
            for mode in MODES:
                options = {
                    "idle_start": 0,
                    "idle_end": max(
                        1, int(recording.get("metadata", {}).get("idle_end_index", 10))
                    ),
                    "percentile": 75,
                    "manual": 4.0,
                    "window": 50,
                }
                expected = decode_recording(recording, mode, options)
                request = json.dumps(
                    {"recording": recording, "mode": mode, "options": options},
                    ensure_ascii=False,
                )
                proc = subprocess.run(
                    ["node", str(ROOT / "tests" / "js_runner.js")],
                    input=request,
                    text=True,
                    capture_output=True,
                    cwd=ROOT,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, msg=proc.stderr)
                actual = json.loads(proc.stdout)
                ok = _equal(expected, actual)
                cases += 1
                print(f"{path.name:30} {mode:10} {'PASS' if ok else 'FAIL'}")
                if not ok:
                    failures.append((path.name, mode, expected, actual))
        self.assertEqual(cases, len(FIXTURES) * len(MODES))
        self.assertFalse(
            failures,
            msg="Parity mismatches: " + json.dumps(failures[:2], ensure_ascii=False),
        )


def _equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
    for key in (
        "bits",
        "sync_index",
        "crc",
        "crc_valid",
        "message",
        "gesture",
        "error",
    ):
        if a.get(key) != b.get(key):
            return False
    x, y = a.get("threshold"), b.get("threshold")
    if isinstance(x, list) and isinstance(y, list):
        return len(x) == len(y) and all(
            math.isclose(float(i), float(j), rel_tol=0, abs_tol=1e-9)
            for i, j in zip(x, y)
        )
    if x is None or y is None:
        return x is y
    return math.isclose(float(x), float(y), rel_tol=0, abs_tol=1e-9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
