"""Receiver and decode_file (Agent 2 interface stub).

These are stub implementations. Agent 2 should replace with the real
hardware/software receiver and JSON recording format support.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class Receiver:
    """Receives bit patterns from a channel (stub — reads from a buffer)."""

    def __init__(self) -> None:
        self._buffer: List[int] = []
        self._lock = threading.Lock()

    def feed_bits(self, bits: List[int]) -> None:
        """Feed received bits into the receiver buffer."""
        with self._lock:
            self._buffer.extend(list(bits))

    def receive_bits(self, count: int) -> List[int]:
        """Read up to `count` bits from the buffer."""
        with self._lock:
            result = self._buffer[:count]
            self._buffer = self._buffer[count:]
            return list(result)

    def available(self) -> int:
        """Return the number of bits available in the buffer."""
        with self._lock:
            return len(self._buffer)

    def clear(self) -> None:
        """Clear the receiver buffer."""
        with self._lock:
            self._buffer = []


def decode_file(file_path: str) -> Dict[str, Any]:
    """Decode a JSON recording file into a structured record.

    Expected JSON recording format:
    {
        "version": "1.0",
        "timestamp": "ISO-8601",
        "bits": [0, 1, 0, 1, ...],
        "gestures": ["wave", "tap", ...],
        "metadata": {}
    }

    Returns a dict with keys: version, timestamp, bits, gestures, metadata.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Recording file not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in recording file {file_path}: {exc}") from exc

    return {
        "version": data.get("version", "1.0"),
        "timestamp": data.get("timestamp", ""),
        "bits": [int(b) for b in data.get("bits", [])],
        "gestures": list(data.get("gestures", [])),
        "metadata": dict(data.get("metadata", {})),
    }
