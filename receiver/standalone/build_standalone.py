# Build the offline receiver with source-generated constants, gestures and parity data.
from __future__ import annotations
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
JS_DIR = HERE / "js"
TEMPLATE = HERE / "template_receiver.html"
OUTPUT = HERE / "standalone_receiver.html"
MODULES = (
    "gestures_embedded.js",
    "crc16.js",
    "decoder.js",
    "chart_lite.js",
    "sensor_hub.js",
    "storage.js",
    "network_guard.js",
    "ui_release.js",
)


def load_protocol() -> dict[str, Any]:
    try:
        sys.path.insert(0, str(ROOT))
        from shared.constants import (
            BIT_DURATION_DEFAULT,
            CRC_POLYNOMIAL,
            SAMPLE_RATE,
            SYNC_HEADER,
            END_OF_MESSAGE,
        )
        from shared.protocol import CRC_INITIAL

        return {
            "SYNC_HEADER": list(SYNC_HEADER),
            "END_OF_MESSAGE": list(END_OF_MESSAGE),
            "CRC_POLYNOMIAL": int(CRC_POLYNOMIAL),
            "CRC_INIT": int(CRC_INITIAL),
            "SAMPLE_RATE": float(SAMPLE_RATE),
            "BIT_DURATION_DEFAULT": float(BIT_DURATION_DEFAULT),
        }
    except (ImportError, AttributeError, TypeError, ValueError) as error:
        raise RuntimeError(f"Could not load protocol constants: {error}") from error


def _sync_index(bits: list[int], pattern: list[int]) -> int:
    from receiver.analysis.sync_detector import find_sync_header

    return find_sync_header(bits, pattern)


def create_parity_fixture() -> dict[str, Any]:
    try:
        sys.path.insert(0, str(ROOT))
        from receiver.analysis.receiver import Receiver

        path = ROOT / "data" / "recordings" / "example_recording.json"
        return {
            "recording": json.loads(path.read_text(encoding="utf-8")),
            "expected": {"bits": Receiver().decode_file(str(path)).get("bits", [])},
        }
    except (
        OSError,
        json.JSONDecodeError,
        ImportError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise RuntimeError(
            f"Cannot generate embedded Python fixture: {error}"
        ) from error


def build() -> Path:
    try:
        template = TEMPLATE.read_text(encoding="utf-8")
        protocol = load_protocol()
        gesture_source = json.loads(
            (ROOT / "gestures" / "gestures.json").read_text(encoding="utf-8")
        )
        exported = re.search(
            r"const GESTURE_DATA = Object\.freeze\((.*)\);",
            (JS_DIR / "gestures_embedded.js").read_text(encoding="utf-8"),
            re.S,
        )
        if not exported or json.loads(exported.group(1)) != gesture_source:
            raise RuntimeError(
                "Gesture export drift; run tools/export_gestures_to_js.py"
            )
        source_constants = (ROOT / "shared" / "constants.py").read_text(
            encoding="utf-8"
        )
        if "CRC_POLYNOMIAL = 0x1021" not in source_constants:
            raise RuntimeError(
                "Protocol constant source changed; update generated decoder constants contract"
            )
        constants = "<!-- BUILD_CONSTANTS_START --><script>const APP_PROTOCOL={};const PARITY_FIXTURE=null;</script><!-- BUILD_CONSTANTS_END -->"
        if constants not in template:
            raise RuntimeError("Constants marker missing from template")
        fixture = create_parity_fixture()
        constant_js = (
            "<script>globalThis.APP_PROTOCOL="
            + json.dumps(protocol, ensure_ascii=False)
            + ";globalThis.PARITY_FIXTURE="
            + json.dumps(fixture, ensure_ascii=False)
            + ";</script>"
        )
        template = template.replace(constants, constant_js)
        marker = "<!-- BUILD_MODULES_START --><!-- BUILD_MODULES_END -->"
        if marker not in template:
            raise RuntimeError("Module marker missing from template")
        modules = "\n".join(
            (JS_DIR / name).read_text(encoding="utf-8") for name in MODULES
        )
        network = (JS_DIR / "network_guard.js").read_text(encoding="utf-8")
        # Install the network blocker synchronously in the head, before application modules.
        template = template.replace(
            "<title>Offline Receiver — مستقبل مستقل</title>",
            "<title>Offline Receiver — مستقبل مستقل</title><script>"
            + network
            + "</script>",
        )
        template = template.replace(marker, "<script>" + modules + "</script>")
        csp = re.search(
            r"<meta http-equiv=\"Content-Security-Policy\"[^>]*>", template, re.I
        )
        if not csp or "connect-src 'none'" not in csp.group(0):
            raise RuntimeError("Restrictive CSP missing")
        cleaned = re.sub(
            r"<meta http-equiv=\"Content-Security-Policy\"[^>]*>",
            "",
            template,
            flags=re.I,
        )
        cleaned = re.sub(r"<!--.*?-->", "", cleaned, flags=re.S)
        cleaned = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", cleaned, flags=re.I)
        if re.search(r"https?://|(?<!:)//[A-Za-z0-9.-]+", cleaned, re.I):
            raise RuntimeError("External/protocol-relative URL found in HTML")
        scripts = "\n".join((JS_DIR / name).read_text(encoding="utf-8") for name in MODULES) + (JS_DIR / "network_guard.js").read_text(encoding="utf-8")
        scripts = scripts.replace("http://127.0.0.1", "LOCALHOST_URL")
        if re.search(r"https?://|(?<!:)//[A-Za-z0-9.-]+", scripts, re.I):
            raise RuntimeError("External URL found in inline JavaScript")
        if re.search(r"<script[^>]+src=|<link[^>]+href=", cleaned, re.I):
            raise RuntimeError("External script/style reference found")
        if len(template.encode("utf-8")) >= 500 * 1024:
            raise RuntimeError("Standalone HTML must be <500 KB")
        OUTPUT.write_text(template, encoding="utf-8")
        LOGGER.info("Built %s (%d bytes)", OUTPUT, OUTPUT.stat().st_size)
        return OUTPUT
    except (OSError, json.JSONDecodeError, RuntimeError, re.error) as error:
        LOGGER.error("Build failed: %s", error)
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    build()
