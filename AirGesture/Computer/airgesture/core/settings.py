"""Persistent settings and gesture profile management.

Everything the user can tune lives in a single JSON document under
``%APPDATA%\\AirGesture\\settings.json`` (portable fallback: next to the
package). The schema is versioned and validated on load, so a corrupt or
outdated file never crashes the app - unknown keys are dropped, missing keys
fall back to defaults and bad values are clamped to safe ranges.
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

APP_DIR_NAME = "AirGesture"
SETTINGS_VERSION = 2


# ---------------------------------------------------------------- schema tool
@dataclass
class Field:
    default: Any
    low: Optional[float] = None
    high: Optional[float] = None
    kind: type = float

    def coerce(self, value: Any) -> Any:
        try:
            if self.kind is bool:
                return bool(value)
            if self.kind is int:
                ivalue = int(round(float(value)))
            elif self.kind is float:
                ivalue = float(value)
            else:
                return value
        except (TypeError, ValueError):
            return copy.deepcopy(self.default)
        if self.low is not None:
            ivalue = max(self.low, ivalue)
        if self.high is not None:
            ivalue = min(self.high, ivalue)
        return ivalue


def gesture_settings(default_action: str, enabled: bool = True, **overrides) -> dict:
    base = {
        "action": default_action,
        "enabled": enabled,
        "sensitivity": 0.5,  # 0..1, per-gesture forgiveness
        "activation_delay": 0.12,  # 0..1 s, how long the pose must be held
        "cooldown": 0.45,  # 0..3 s, minimum time between repeats
        "learned_confidence": 1.0,  # set by the gesture-learning workflow
    }
    base.update(overrides)
    return base


DEFAULT_GESTURES: dict[str, dict] = {
    "open_palm": gesture_settings("move", sensitivity=0.6),
    "fist": gesture_settings("drag", sensitivity=0.5),
    "index_only": gesture_settings("none", sensitivity=0.5),
    "pinch": gesture_settings(
        "left_click", sensitivity=0.6, activation_delay=0.05, cooldown=0.35
    ),
    "two_fingers": gesture_settings(
        "right_click", sensitivity=0.5, activation_delay=0.2, cooldown=0.8
    ),
    "three_fingers": gesture_settings(
        "double_click", sensitivity=0.5, activation_delay=0.25, cooldown=1.0
    ),
    "four_fingers": gesture_settings(
        "none", enabled=False, sensitivity=0.5, activation_delay=0.3
    ),
}


def defaults() -> dict:
    return copy.deepcopy(
        {
            "version": SETTINGS_VERSION,
            "general": {
                "start_minimized": False,
                "auto_start_control": False,
                "show_overlay": True,
                "appearance": "dark",
                "accent": "violet",
                "ui_scale": 1.0,
            },
            "camera": {
                "index": 0,
                "width": 1280,
                "height": 720,
                "fps": 30,
                "mirror": True,
                "detection_confidence": 0.6,
                "tracking_confidence": 0.6,
            },
            "tracking": {
                "handedness": "any",  # any | left | right
                "distance_filter": 0.35,  # One-Euro filter min cutoff (lower = smoother)
                "velocity_beta": 0.025,  # One-Euro beta (higher = more responsive)
            },
            "mouse": {
                "sensitivity": 1.35,  # cursor-to-hand multiplier (gain)
                "speed": 1.0,  # overall speed multiplier
                "smoothing": 0.45,  # 0 = raw, 1 = max smoothing
                "active_area_x": 0.62,  # fraction of frame width used for movement
                "active_area_y": 0.58,
                "acceleration": 0.35,  # 0..1, extra gain for fast movements
                "jump_guard": 0.14,  # max fraction of active area per frame
                "deadzone": 0.004,
                "scroll_speed": 1.0,
                "natural_scroll": True,
                "position_mode": "absolute",  # absolute | relative
            },
            "interaction": {
                "mode": "auto",  # auto | active (hold to control) | always
                "tracking_lost_timeout": 0.55,
                "pause_grace": 0.35,
                "click_armed_timeout": 0.9,
            },
            "gestures": DEFAULT_GESTURES,
            "calibration": {
                "active_area": {"x0": 0.18, "y0": 0.15, "x1": 0.82, "y1": 0.85},
                "screen_margin": 0.0,
                "completed": False,
                "cursor_scale": 1.0,
            },
        }
    )


NUMERIC_FIELDS: dict[str, dict[str, Field]] = {
    "general": {
        "start_minimized": Field(False, kind=bool),
        "auto_start_control": Field(False, kind=bool),
        "show_overlay": Field(True, kind=bool),
        "ui_scale": Field(1.0, 0.85, 1.25),
    },
    "camera": {
        "index": Field(0, 0, 15, int),
        "width": Field(1280, 320, 3840, int),
        "height": Field(720, 240, 2160, int),
        "fps": Field(30, 10, 60, int),
        "mirror": Field(True, kind=bool),
        "detection_confidence": Field(0.6, 0.2, 0.95),
        "tracking_confidence": Field(0.6, 0.2, 0.95),
    },
    "tracking": {
        "distance_filter": Field(0.35, 0.05, 1.2),
        "velocity_beta": Field(0.025, 0.0, 0.2),
    },
    "mouse": {
        "sensitivity": Field(1.35, 0.3, 3.5),
        "speed": Field(1.0, 0.2, 3.0),
        "smoothing": Field(0.45, 0.0, 0.95),
        "active_area_x": Field(0.62, 0.2, 0.95),
        "active_area_y": Field(0.58, 0.2, 0.95),
        "acceleration": Field(0.35, 0.0, 1.0),
        "jump_guard": Field(0.14, 0.02, 0.4),
        "deadzone": Field(0.004, 0.0, 0.03),
        "scroll_speed": Field(1.0, 0.2, 4.0),
        "natural_scroll": Field(True, kind=bool),
    },
    "interaction": {
        "tracking_lost_timeout": Field(0.55, 0.15, 2.0),
        "pause_grace": Field(0.35, 0.0, 1.5),
        "click_armed_timeout": Field(0.9, 0.2, 3.0),
    },
    "calibration": {
        "screen_margin": Field(0.0, 0.0, 0.15),
        "cursor_scale": Field(1.0, 0.5, 2.0),
    },
}

ENUMS = {
    ("general", "appearance"): ("dark", "light", "system"),
    ("general", "accent"): ("violet", "teal", "amber", "rose"),
    ("tracking", "handedness"): ("any", "left", "right"),
    ("mouse", "position_mode"): ("absolute", "relative"),
    ("interaction", "mode"): ("auto", "active", "always"),
}

GESTURE_ACTION_VALUES = (
    "move",
    "left_click",
    "right_click",
    "double_click",
    "drag",
    "scroll",
    "pause",
    "none",
)


# ------------------------------------------------------------------- manager
class SettingsManager:
    """Thread-safe settings store with lazy persistence."""

    def __init__(self, path: Optional[str] = None, autosave: bool = True):
        self.path = path or self.default_path()
        self.autosave = autosave
        self._lock = threading.RLock()
        self._data = defaults()
        self._listeners: list[Callable[[str, str], None]] = []
        self.load_error: Optional[str] = None
        self.load()

    # --------------------------------------------------------------- locations
    @staticmethod
    def default_path() -> str:
        appdata = os.environ.get("APPDATA")
        if appdata:
            folder = os.path.join(appdata, APP_DIR_NAME)
        else:
            folder = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "userdata"
            )
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, "settings.json")

    # --------------------------------------------------------------------- io
    def load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            with self._lock:
                self._data = self._validate(raw)
        except Exception as exc:  # corrupted settings must never break startup
            self.load_error = f"Could not read settings ({exc}). Defaults were used."
            with self._lock:
                self._data = defaults()

    def save(self) -> bool:
        with self._lock:
            payload = copy.deepcopy(self._data)
            payload["version"] = SETTINGS_VERSION
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
            os.replace(tmp, self.path)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ access
    def get(self, section: str, key: str, default: Any = None) -> Any:
        with self._lock:
            return copy.deepcopy(self._data.get(section, {}).get(key, default))

    def set(
        self, section: str, key: str, value: Any, save: Optional[bool] = None
    ) -> None:
        field = NUMERIC_FIELDS.get(section, {}).get(key)
        if field is not None:
            value = field.coerce(value)
        allowed = ENUMS.get((section, key))
        if allowed and value not in allowed:
            value = allowed[0]
        with self._lock:
            sec = self._data.setdefault(section, {})
            if sec.get(key) == value:
                return
            sec[key] = value
            if section == "gestures":
                pass
            should_save = self.autosave if save is None else save
        self._notify(section, key)
        if should_save:
            self.save()

    def section(self, name: str) -> dict:
        with self._lock:
            return copy.deepcopy(self._data.get(name, {}))

    def snapshot(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._data)

    # ---------------------------------------------------------------- gestures
    def gesture(self, gesture_id: str) -> dict:
        with self._lock:
            return copy.deepcopy(
                self._data["gestures"].get(gesture_id, gesture_settings("none"))
            )

    def update_gesture(self, gesture_id: str, **values) -> None:
        with self._lock:
            current = self._data.setdefault("gestures", {}).setdefault(
                gesture_id, gesture_settings("none")
            )
            for key, value in values.items():
                if key in ("sensitivity",):
                    value = max(0.0, min(1.0, float(value)))
                elif key in ("activation_delay",):
                    value = max(0.0, min(1.0, float(value)))
                elif key in ("cooldown",):
                    value = max(0.0, min(3.0, float(value)))
                elif key == "enabled":
                    value = bool(value)
                elif key == "action":
                    if value not in GESTURE_ACTION_VALUES:
                        continue
                current[key] = value
        self._notify("gestures", gesture_id)
        if self.autosave:
            self.save()

    def reset_gestures(self) -> None:
        with self._lock:
            self._data["gestures"] = copy.deepcopy(DEFAULT_GESTURES)
        self._notify("gestures", "*")
        if self.autosave:
            self.save()

    def reset_all(self) -> None:
        with self._lock:
            self._data = defaults()
        self._notify("*", "*")
        if self.autosave:
            self.save()

    # --------------------------------------------------------------- listeners
    def subscribe(self, callback: Callable[[str, str], None]) -> Callable[[], None]:
        self._listeners.append(callback)

        def unsubscribe() -> None:
            if callback in self._listeners:
                self._listeners.remove(callback)

        return unsubscribe

    def _notify(self, section: str, key: str) -> None:
        for cb in list(self._listeners):
            try:
                cb(section, key)
            except Exception:
                pass

    # -------------------------------------------------------------- validation
    def _validate(self, raw: dict) -> dict:
        data = defaults()
        if not isinstance(raw, dict):
            self.load_error = "Settings file is not an object; defaults were used."
            return data

        for section in ("general", "camera", "tracking", "mouse", "interaction"):
            incoming = raw.get(section) or {}
            if not isinstance(incoming, dict):
                continue
            for key, spec in NUMERIC_FIELDS.get(section, {}).items():
                if key in incoming:
                    data[section][key] = spec.coerce(incoming[key])
            for (sec, k), allowed in ENUMS.items():
                if sec == section and incoming.get(k) in allowed:
                    data[section][k] = incoming[k]
            if section == "mouse" and incoming.get("position_mode") in (
                "absolute",
                "relative",
            ):
                data["mouse"]["position_mode"] = incoming["position_mode"]

        gestures = raw.get("gestures")
        if isinstance(gestures, dict):
            for gid, values in gestures.items():
                if not isinstance(values, dict):
                    continue
                base = data["gestures"].get(gid) or gesture_settings("none")
                if values.get("action") in GESTURE_ACTION_VALUES:
                    base["action"] = values["action"]
                if "enabled" in values:
                    base["enabled"] = bool(values["enabled"])
                for key, lo, hi in (
                    ("sensitivity", 0.0, 1.0),
                    ("activation_delay", 0.0, 1.0),
                    ("cooldown", 0.0, 3.0),
                    ("learned_confidence", 0.35, 1.0),
                ):
                    if key in values:
                        try:
                            base[key] = max(lo, min(hi, float(values[key])))
                        except (TypeError, ValueError):
                            pass
                data["gestures"][gid] = base

        cal = raw.get("calibration")
        if isinstance(cal, dict):
            area = cal.get("active_area")
            if isinstance(area, dict):
                try:
                    x0, y0, x1, y1 = (
                        float(area["x0"]),
                        float(area["y0"]),
                        float(area["x1"]),
                        float(area["y1"]),
                    )
                    x0, x1 = max(0.0, min(x0, 0.45)), min(1.0, max(x1, 0.55))
                    y0, y1 = max(0.0, min(y0, 0.45)), min(1.0, max(y1, 0.55))
                    data["calibration"]["active_area"] = {
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1,
                    }
                except (KeyError, TypeError, ValueError):
                    pass
            data["calibration"]["completed"] = bool(cal.get("completed", False))
            for key, lo, hi in (
                ("screen_margin", 0.0, 0.15),
                ("cursor_scale", 0.5, 2.0),
            ):
                if key in cal:
                    try:
                        data["calibration"][key] = max(lo, min(hi, float(cal[key])))
                    except (TypeError, ValueError):
                        pass
        return data
