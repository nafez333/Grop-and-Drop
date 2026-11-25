"Bit-level parity tests for the browser and Python CRC implementations."""
from __future__ import annotations
import json
import shutil
import subprocess
import unittest
from pathlib import Path
from receiver.analysis.crc import calculate_crc
ROOT = Path(__file__).resolve().parents[1]
JS_CRC = ROOT / "receiver" / "standalone" / "js" / "crc16.js"

class TestCRC16Parity(unittest.TestCase):
    def test_crc_vectors_match_python(self) -> None:
        vectors = [[], [0], [1], [1, 0, 1, 0], [1, 0, 1, 0, 1, 0, 1, 0], [1, 0] * 32]
        expected = [calculate_crc(bits) for bits in vectors]
        node = shutil.which("node")
        if node:
            script = "const c=require(process.argv[1]);const v=JSON.parse(process.argv[2]);process.stdout.write(JSON.stringify(v.map(x=>c.crc16ccitt(x))))"
            output = subprocess.check_output([node, "-e", script, str(JS_CRC), json.dumps(vectors)], text=True)
            self.assertEqual(json.loads(output), expected)
        else:
            fixture = ROOT / "tests" / "fixtures" / "crc16_expected.json"
            fixture.parent.mkdir(parents=True, exist_ok=True)
            fixture.write_text(json.dumps({"vectors": vectors, "expected": expected}, indent=2), encoding="utf-8")
            self.skipTest("Node.js is unavailable; static vectors generated for browser/manual verification")

if __name__ == "__main__":
    unittest.main()
