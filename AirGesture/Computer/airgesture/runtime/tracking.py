"""MediaPipe hand tracking engine (the only MediaPipe-aware component).

Responsibilities
----------------
* Load the ``hand_landmarker.task`` model once and reuse it.
* Accept a BGR frame, return at most one :class:`~airgesture.core.pose.HandPose`
  plus the raw landmarks for drawing.
* Apply a One-Euro filter to the palm centre so the cursor is smooth without
  adding perceivable latency.
* Frame-rate independent: uses timestamps, no fixed sleeps.

Threading: a ``HandTracker`` instance must only be used from the processing
thread that created it (MediaPipe landmarkers are not documented as thread
safe).
"""

from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core import base_options

from ..core.pose import HandPose, analyze

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "hand_landmarker.task"
)


class TrackingError(RuntimeError):
    pass


@dataclass
class TrackResult:
    landmarks: object  # list[landmark] or None
    pose: Optional[HandPose]
    palm_xy: Optional[tuple]  # filtered palm centre, normalised (0..1)
    raw_palm_xy: Optional[tuple]
    handedness: str
    handedness_confidence: float
    timestamp: float


class OneEuroFilter:
    """Low-latency adaptive low-pass filter (Casiez et al. 2012).

    Smooth when the hand is still, responsive when it moves quickly - exactly
    what a cursor needs. ``min_cutoff`` controls jitter, ``beta`` controls how
    much speed increases responsiveness.
    """

    def __init__(
        self, min_cutoff: float = 0.35, beta: float = 0.025, d_cutoff: float = 1.0
    ):
        self.min_cutoff_db = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x: Optional[float] = None
        self._dx = 0.0
        self._t_prev: Optional[float] = None

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * max(1e-6, cutoff))
        return 1.0 / (1.0 + tau / max(1e-6, dt))

    def reset(self) -> None:
        self._x = None
        self._dx = 0.0
        self._t_prev = None

    def __call__(self, value: float, t: float) -> float:
        if self._x is None or self._t_prev is None:
            self._x = value
            self._t_prev = t
            self._dx = 0.0
            return value
        dt = max(1e-3, t - self._t_prev)
        self._t_prev = t
        dx = (value - self._x) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        self._dx = a_d * dx + (1 - a_d) * self._dx
        cutoff = self.min_cutoff_db + self.beta * abs(self._dx)
        a = self._alpha(cutoff, dt)
        self._x = a * value + (1 - a) * self._x
        return self._x


class HandTracker:
    def __init__(
        self,
        num_hands: int = 1,
        detection_confidence: float = 0.6,
        tracking_confidence: float = 0.6,
        model_path: str = MODEL_PATH,
    ):
        if not os.path.exists(model_path):
            raise TrackingError(
                f"Hand tracking model not found at {model_path}. "
                "Make sure hand_landmarker.task is next to main.py."
            )
        options = vision.HandLandmarkerOptions(
            base_options=base_options.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=detection_confidence,
            min_hand_presence_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._t0 = time.perf_counter()
        self._last_ts_ms = -1
        self._fx = OneEuroFilter()
        self._fy = OneEuroFilter()
        self.filter_min_cutoff = 0.35
        self.filter_beta = 0.025
        self.closed = False
        self.last_result: Optional[TrackResult] = None
        self.handedness_filter = "any"

    # ------------------------------------------------------------------ config
    def configure_filter(self, min_cutoff: float, beta: float) -> None:
        if min_cutoff != self.filter_min_cutoff or beta != self.filter_beta:
            self.filter_min_cutoff = min_cutoff
            self.filter_beta = beta
            self._fx = OneEuroFilter(min_cutoff, beta)
            self._fy = OneEuroFilter(min_cutoff, beta)

    # --------------------------------------------------------------- processing
    def process(self, frame_bgr, timestamp: Optional[float] = None) -> TrackResult:
        """Detect the primary hand in ``frame_bgr`` (BGR, mirrored as desired)."""
        if self.closed:
            raise TrackingError("Hand tracker was closed.")
        now = time.perf_counter() if timestamp is None else timestamp
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        ts_ms = int((now - self._t0) * 1000)
        if ts_ms <= self._last_ts_ms:
            ts_ms = self._last_ts_ms + 1
        self._last_ts_ms = ts_ms

        try:
            result = self._landmarker.detect_for_video(mp_image, ts_ms)
        except Exception as exc:  # MediaPipe can raise on bad frames
            return TrackResult(None, None, None, None, "Unknown", 0.0, now)

        if not result.hand_landmarks:
            return TrackResult(None, None, None, None, "Unknown", 0.0, now)

        best = 0
        if len(result.hand_landmarks) > 1 and result.handedness:
            scores = [h[0].score if h else 0.0 for h in result.handedness]
            best = int(max(range(len(scores)), key=scores.__getitem__))

        landmarks = result.hand_landmarks[best]
        label, score = "Unknown", 0.0
        if (
            result.handedness
            and best < len(result.handedness)
            and result.handedness[best]
        ):
            cat = result.handedness[best][0]
            label = cat.category_name or "Unknown"
            score = float(cat.score)

        # MediaPipe reports handedness of the image as given. The app shows a
        # mirrored preview, so the label matches what the user sees; we keep it
        # informational only - recognition is handedness agnostic.
        pose = analyze(landmarks, label, score)
        raw_xy = pose.palm_center

        accepted = (
            self.handedness_filter == "any"
            or self.handedness_filter.lower() == label.lower()
        )
        if not accepted:
            return TrackResult(landmarks, pose, None, raw_xy, label, score, now)

        # Filter only when the hand did not jump absurdly (re-acquisition)
        if (
            self._fx._x is not None
            and self.last_result
            and self.last_result.pose is not None
        ):
            jump = math.hypot(raw_xy[0] - self._fx._x, raw_xy[1] - self._fy._x)
            if jump > 0.35:
                self._fx.reset()
                self._fy.reset()
        fx = self._fx(raw_xy[0], now)
        fy = self._fy(raw_xy[1], now)

        res = TrackResult(landmarks, pose, (fx, fy), raw_xy, label, score, now)
        self.last_result = res
        return res

    # ----------------------------------------------------------------- drawing
    def reset(self) -> None:
        self._fx.reset()
        self._fy.reset()
        self.last_result = None

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            self._landmarker.close()
        except Exception:
            pass


def draw_hand(frame, landmarks, palm_xy=None, accent=(139, 108, 255)) -> None:
    """Draw a light, modern hand skeleton on ``frame`` (BGR, in place)."""
    if landmarks is None:
        return
    h, w = frame.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    overlay = frame.copy()
    for conn in vision.HandLandmarksConnections.HAND_CONNECTIONS:
        a, b = pts[conn.start], pts[conn.end]
        cv2.line(overlay, a, b, accent, 2, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    for i, p in enumerate(pts):
        r = 4 if i in (0, 4, 8, 12, 16, 20) else 3
        cv2.circle(frame, p, r, (245, 245, 245), -1, cv2.LINE_AA)
        cv2.circle(frame, p, r, accent, 1, cv2.LINE_AA)
    if palm_xy is not None:
        px, py = int(palm_xy[0] * w), int(palm_xy[1] * h)
        cv2.circle(frame, (px, py), 12, accent, 2, cv2.LINE_AA)
        cv2.circle(frame, (px, py), 3, (255, 255, 255), -1, cv2.LINE_AA)
