"""General-purpose bit/byte/text conversion and persistence helpers."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import List


def bits_to_bytes(bits: List[int]) -> bytes:
    """Convert a list of 0/1 bits (MSB first, length a multiple of 8) to bytes."""
    if len(bits) % 8 != 0:
        raise ValueError(f"bit length {len(bits)} is not a multiple of 8")
    if any(bit not in (0, 1) for bit in bits):
        raise ValueError("bits may contain only 0 and 1")
    result = bytearray()
    for offset in range(0, len(bits), 8):
        byte = 0
        for bit in bits[offset : offset + 8]:
            byte = (byte << 1) | bit
        result.append(byte)
    return bytes(result)


def bytes_to_bits(data: bytes) -> List[int]:
    """Convert bytes to a list of 0/1 bits (MSB first)."""
    bits: List[int] = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append(1 if (byte >> shift) & 1 else 0)
    return bits


def text_to_bits(text: str) -> List[int]:
    """Encode a UTF-8 string to a list of 0/1 bits (MSB first)."""
    return bytes_to_bits(text.encode("utf-8"))


def bits_to_text(bits: List[int]) -> str:
    """Decode a list of 0/1 bits (MSB first, length a multiple of 8) to a UTF-8 string."""
    return bits_to_bytes(bits).decode("utf-8")


def timestamp_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def save_json(data: dict, filepath: str) -> None:
    """Serialize ``data`` to JSON and write it to ``filepath`` (creating dirs)."""
    directory = os.path.dirname(os.path.abspath(filepath))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)


def load_json(filepath: str) -> dict:
    """Load and return a JSON object from ``filepath``."""
    with open(filepath, "r", encoding="utf-8") as handle:
        return json.load(handle)
