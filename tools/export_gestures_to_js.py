# Generate the browser gesture table from canonical JSON.
from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any
LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "gestures" / "gestures.json"
TARGET = ROOT / "receiver" / "standalone" / "js" / "gestures_embedded.js"


def export_gestures(source: Path = SOURCE, target: Path = TARGET) -> None:
    try:
        data: dict[str, Any] = json.loads(source.read_text(encoding="utf-8"))
        encoded = json.dumps(data, ensure_ascii=False)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "/* Generated from gestures/gestures.json; do not edit by hand. */\n"
            f"const GESTURE_DATA = Object.freeze({encoded});\n"
            "if (typeof globalThis !== 'undefined') globalThis.GESTURE_DATA = GESTURE_DATA;\n"
            "if (typeof module !== 'undefined' && module.exports) module.exports = GESTURE_DATA;\n",
            encoding="utf-8",
        )
        LOGGER.info("Exported %d gestures to %s", len(data.get("gestures", {})), target)
    except (OSError, json.JSONDecodeError, TypeError) as error:
        raise RuntimeError(f"Could not export gestures: {error}") from error
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    export_gestures()
