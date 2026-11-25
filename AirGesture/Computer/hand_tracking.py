"""Legacy shim: re-exports HandTracker from airgesture.runtime.tracking."""
from __future__ import annotations

from airgesture.runtime.tracking import HandTracker  # noqa: F401

__all__ = ["HandTracker"]
