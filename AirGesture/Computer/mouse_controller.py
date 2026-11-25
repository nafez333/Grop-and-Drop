"""Legacy shim: re-exports MouseController from airgesture.runtime.mouse_controller."""
from __future__ import annotations

from airgesture.runtime.mouse_controller import MouseController  # noqa: F401

__all__ = ["MouseController"]
