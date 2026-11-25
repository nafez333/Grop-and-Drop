"""Legacy shim: re-exports GestureRecognizer from airgesture.core.recognizer."""
from __future__ import annotations

from airgesture.core.recognizer import GestureRecognizer  # noqa: F401

__all__ = ["GestureRecognizer"]
