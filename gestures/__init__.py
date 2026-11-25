"""Gesture system package.

Exposes the GestureEngine class for flexible, prefix-free gesture bit-pattern
management. All gestures are defined in JSON configuration — zero code changes
required to add new gestures.
"""

from .gesture_engine import (
    GestureEngine,
    GestureNotFoundError,
    GestureEngineError,
    PrefixFreeViolationError,
    DuplicateBitsError,
)

__all__ = [
    "GestureEngine",
    "GestureNotFoundError",
    "GestureEngineError",
    "PrefixFreeViolationError",
    "DuplicateBitsError",
]
