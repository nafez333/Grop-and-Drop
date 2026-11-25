"End-to-end encoder, synthetic channel, Python and JavaScript decoder checks." ""
from __future__ import annotations
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from shared.constants import END_OF_MESSAGE, SYNC_HEADER
from shared.protocol import Protocol
from gestures import GestureEngine
from receiver.analysis.offline_pipeline import decode_recording
from tools.simulate_channel import simulate_channel

ROOT = Path(__file__).resolve().parents[1]


class TestEndToEnd(unittest.TestCase):
    def test_all_gestures_and_text_round_trip(self) -> None:
        engine = GestureEngine(config_path=str(ROOT / "gestures" / "gestures.json"))
        protocol = Protocol()
        cases = []
        for name, entry in engine.list_gestures().items():
            bits = list(SYNC_HEADER) + entry["bits"]
            checksum = protocol.calculate_crc(entry["bits"])
            bits += [(checksum >> shift) & 1 for shift in range(15, -1, -1)] + list(
                END_OF_MESSAGE
            )
            cases.append((name, bits, "gesture", name))
        for text in ("Hello", "Offline 42", "مرحبا بالعالم"):
            cases.append((text, protocol.encode_message(text), "message", text))
        for label, bits, kind, expected in cases:
            with self.subTest(case=label), tempfile.TemporaryDirectory() as folder:
                path = simulate_channel(
                    bits, Path(folder) / "record.json", delta_ut=8, snr_db=30, seed=15
                )
                recording = json.loads(path.read_text(encoding="utf-8"))
                py = decode_recording(recording, "otsu")
                self.assertTrue(
                    py["crc_valid"], f"Python CRC failure for {label}: {py}"
                )
                self.assertEqual(py[kind], expected)
                request = json.dumps(
                    {"recording": recording, "mode": "otsu", "options": {}},
                    ensure_ascii=False,
                )
                js = json.loads(
                    subprocess.check_output(
                        ["node", str(ROOT / "tests" / "js_runner.js")],
                        input=request,
                        text=True,
                        cwd=ROOT,
                    )
                )
                self.assertEqual(js["bits"], py["bits"])
                self.assertEqual(js["crc_valid"], py["crc_valid"])
                self.assertEqual(js["message"], py["message"])
                self.assertEqual(js["gesture"], py["gesture"])

    def test_detection_sweep(self) -> None:
        protocol = Protocol()
        bits = protocol.encode_message("S")
        results = []
        for snr in (20, 10, 3):
            minimum = None
            for delta in (1, 2, 4, 8, 12, 16, 24):
                with tempfile.TemporaryDirectory() as folder:
                    recording = json.loads(
                        simulate_channel(
                            bits,
                            Path(folder) / "r.json",
                            delta_ut=delta,
                            snr_db=snr,
                            seed=9,
                        ).read_text(encoding="utf-8")
                    )
                    decoded = decode_recording(recording, "otsu")
                    if decoded["crc_valid"] and decoded["message"] == "S":
                        minimum = delta
                        break
            results.append((snr, minimum))
        print("Detection sweep (synthetic, not hardware): SNR dB | minimum ΔµT")
        for snr, delta in results:
            print(f"{snr:>8} | {delta if delta is not None else 'not detected'}")
        self.assertTrue(any(delta is not None for _, delta in results), results)
        self.assertIsNone(dict(results)[3], "3 dB synthetic channel should expose its detection limit")


if __name__ == "__main__":
    unittest.main(verbosity=2)
