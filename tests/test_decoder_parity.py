"Python versus JavaScript recording decoder parity tests."""
from __future__ import annotations
import json
import shutil
import subprocess
import unittest
from pathlib import Path
from receiver.analysis.receiver import Receiver
ROOT = Path(__file__).resolve().parents[1]
JS_DECODER = ROOT / "receiver" / "standalone" / "js" / "decoder.js"
FIXTURES = ROOT / "tests" / "fixtures"
RECORDINGS = [ROOT / "data" / "recordings" / "example_recording.json"]

class TestDecoderParity(unittest.TestCase):
    def test_recording_pipeline_matches_python(self) -> None:
        node = shutil.which("node")
        expected_cases = []
        for path in RECORDINGS:
            with self.subTest(recording=path.name):
                expected = Receiver().decode_file(str(path))
                expected_cases.append({"recording": json.loads(path.read_text(encoding="utf-8")), "expected": expected, "source": str(path.relative_to(ROOT))})
                if node:
                    script = "const d=require(process.argv[1]);const r=require(process.argv[2]);process.stdout.write(JSON.stringify(d.decodeRecording(r)))"
                    actual = json.loads(subprocess.check_output([node, "-e", script, str(JS_DECODER), str(path)], text=True))
                    self.assertEqual(actual["bits"], expected["bits"])
                    self.assertEqual(actual["crc_valid"], expected["crc_valid"])
                    self.assertEqual(actual["sync_index"], _sync_index(expected["bits"]))
                    self.assertEqual(actual["message"], expected["message"])
        fixture = {"cases": expected_cases}
        FIXTURES.mkdir(parents=True, exist_ok=True)
        (FIXTURES / "parity_expected.json").write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")
        if not node:
            self.skipTest("Node.js unavailable; Python expected fixture generated for in-page/manual browser verification")

def _sync_index(bits: list[int]) -> int:
    from shared.constants import SYNC_HEADER
    for start in range(max(0, len(bits) - len(SYNC_HEADER) + 1)):
        if sum(int(a) != int(b) for a, b in zip(bits[start:start + len(SYNC_HEADER)], SYNC_HEADER)) <= 1:
            return start
    return -1
if __name__ == "__main__":
    unittest.main()
