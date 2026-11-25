"""Hand pose analysis: turns 21 raw landmarks into a scale-invariant feature set.

Design goals
------------
* **No fixed pixel distances.** Every length is divided by the palm size.
* **No required hand orientation.** Finger state uses the *signed* projection of
  the tip along the finger's own axis plus joint angles, so a rotated or
  slightly turned hand produces the same features as a frontal one.
* **Partial training data only uses the camera's x/y/z in a normalised way**,
  which keeps it independent of resolution and camera distance.
* **Uncertainty is exposed.** The recogniser needs to know when a hand is
  ambiguous (in between poses) so it can be ignored instead of guessed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from . import geometry as geo

# Extension (base->tip reach / phalanx length) thresholds. 1.0 = perfectly
# straight. A relaxed but clearly-extended finger is >= ~0.90; a finger curled
# back over the palm falls to ~0.55-0.85 and its joint curvature becomes high.
# The band between is "Mid" (closing / opening) and is deliberately ambiguous.
OPEN_THRESHOLD = 0.88
STRONG_OPEN = 0.95
CLOSED_THRESHOLD = 0.80
CURL_CLOSED = 0.60


@dataclass
class HandPose:
    landmarks: object
    handedness: str  # "Left" / "Right" / "Unknown"
    confidence: float  # MediaPipe handedness score
    palm_center: tuple
    palm_size: float
    scale_cm: float  # rough estimate based on an average adult palm (~8.5cm)
    orientation_deg: float
    extension: Dict[str, float]  # thumb..pinky, signed & normalised
    curl: Dict[str, float]  # thumb..pinky, 0 straight .. 1 folded
    openness: float  # 0..1 overall
    thumb_index_ratio: float  # tip distance / palm size
    thumb_middle_ratio: float
    normalized_palm_pos: tuple  # palm centre in normalised image space

    def finger_state(self, finger: str) -> str:
        """Three-way state: Open / Closed / Mid.

        ``extension`` (base->tip reached / sum of phalanx lengths) measures
        *straightness*: it answers "is this finger out?" independent of
        rotation and scale. ``curl`` (joint bend) is only used to confirm.
        "Mid" = genuinely in transition and is treated as ambiguous by the
        recogniser instead of being counted as open or closed.
        """
        ext = self.extension[finger]
        curl = self.curl[finger]
        if ext >= OPEN_THRESHOLD and curl < CURL_CLOSED:
            return "Open"
        if ext <= CLOSED_THRESHOLD or curl >= CURL_CLOSED:
            return "Closed"
        return "Mid"

    def extended_fingers(self) -> list[str]:
        return [f for f in geo.FINGER_NAMES if self.finger_state(f) == "Open"]

    def as_dict(self) -> dict:
        return {
            "palm_center": self.palm_center,
            "palm_size": self.palm_size,
            "orientation_deg": self.orientation_deg,
            "extension": dict(self.extension),
            "curl": dict(self.curl),
            "openness": self.openness,
            "thumb_index_ratio": self.thumb_index_ratio,
            "thumb_middle_ratio": self.thumb_middle_ratio,
            "extended": self.extended_fingers(),
            "handedness": self.handedness,
        }


def analyze(
    landmarks, handedness: str = "Unknown", confidence: float = 0.0
) -> HandPose:
    """Build a :class:`HandPose` from raw landmarks."""
    size = geo.palm_size(landmarks)
    extension = {f: geo.finger_extension(landmarks, f) for f in geo.FINGER_NAMES}
    curl = {f: geo.finger_curvature(landmarks, f) for f in geo.FINGER_NAMES}
    openness = (
        sum(
            geo.clamp(extension[f] / OPEN_THRESHOLD, 0.0, 1.0) for f in geo.FINGER_NAMES
        )
        / 5.0
    )

    ti = geo.dist(landmarks[geo.THUMB_TIP], landmarks[geo.INDEX_TIP]) / size
    tm = geo.dist(landmarks[geo.THUMB_TIP], landmarks[geo.MIDDLE_TIP]) / size
    center = geo.palm_center(landmarks)

    return HandPose(
        landmarks=landmarks,
        handedness=handedness,
        confidence=confidence,
        palm_center=center,
        palm_size=size,
        scale_cm=size * 8.5,  # rough, only used to reason about camera distance
        orientation_deg=geo.hand_orientation(landmarks),
        extension=extension,
        curl=curl,
        openness=openness,
        thumb_index_ratio=ti,
        thumb_middle_ratio=tm,
        normalized_palm_pos=center,
    )
