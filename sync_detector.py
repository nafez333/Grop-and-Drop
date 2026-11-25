"""Sync detector (Agent 1 / Agent 2 shared interface stub)."""

from __future__ import annotations

from typing import List, Optional

SYNC_PATTERN = [1, 1, 1, 1]


def detect_sync(bits: List[int], pattern: Optional[List[int]] = None,
                max_errors: int = 1) -> Optional[int]:
    """Detect a sync pattern in a bit stream.

    Returns the index where the sync pattern starts, or None if not found.

    Parameters
    ----------
    bits : List[int]
        The bit stream to search.
    pattern : Optional[List[int]]
        The sync pattern to detect. Defaults to [1, 1, 1, 1].
    max_errors : int
        Maximum number of bit errors tolerated (Hamming distance).

    Returns
    -------
    Optional[int]
        Start index of the sync pattern, or None.
    """
    if pattern is None:
        pattern = list(SYNC_PATTERN)

    plen = len(pattern)
    if len(bits) < plen:
        return None

    for i in range(len(bits) - plen + 1):
        window = bits[i : i + plen]
        errors = sum(1 for a, b in zip(window, pattern) if a != b)
        if errors <= max_errors:
            return i
    return None


def find_all_syncs(bits: List[int], pattern: Optional[List[int]] = None,
                   max_errors: int = 1) -> List[int]:
    """Find all sync pattern positions in a bit stream."""
    if pattern is None:
        pattern = list(SYNC_PATTERN)
    plen = len(pattern)
    positions: List[int] = []
    for i in range(len(bits) - plen + 1):
        window = bits[i : i + plen]
        errors = sum(1 for a, b in zip(window, pattern) if a != b)
        if errors <= max_errors:
            positions.append(i)
    return positions
