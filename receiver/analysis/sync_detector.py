"""Sync-header search with a configurable pattern and one-bit error tolerance."""
from __future__ import annotations
from typing import List, Sequence
try:
    from shared.constants import SYNC_HEADER as _SYNC_HEADER
except (ImportError, ModuleNotFoundError):
    _SYNC_HEADER = [1, 0, 1, 0, 1, 0, 1, 1]
SYNC_HEADER = list(_SYNC_HEADER)


def cross_correlate(signal: Sequence[int], pattern: Sequence[int]) -> List[float]:
    """Return normalized sliding binary agreement scores."""
    if not pattern:
        return []
    if len(signal) < len(pattern):
        return []
    pattern_bits = [1 if int(bit) else 0 for bit in pattern]
    return [sum(1.0 if (1 if int(bit) else 0) == expected else -1.0
                for bit, expected in zip(signal[start:start + len(pattern)], pattern_bits)) / len(pattern_bits)
            for start in range(len(signal) - len(pattern_bits) + 1)]


def find_sync_header(bits: List[int], sync_pattern: List[int] = None) -> int:
    """Return first matching sync start, accepting at most one mismatched bit."""
    pattern = list(SYNC_HEADER if sync_pattern is None else sync_pattern)
    if not pattern or len(bits) < len(pattern):
        return -1
    tolerance = 1 if len(pattern) > 1 else 0
    scores = cross_correlate(bits, pattern)
    for index, score in enumerate(scores):
        mismatches = int(round((1.0 - score) * len(pattern) / 2.0))
        if mismatches <= tolerance:
            return index
    return -1
