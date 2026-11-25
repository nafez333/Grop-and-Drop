"""Rule-based gesture recognition over :class:`~.pose.HandPose` features.

The gesture set was deliberately kept small and *comfortable*. Instead of
requiring unusual finger shapes (shaka, victory, upside-down fists...) the
recogniser uses:

===============  ==========================================  ==================
Gesture          Pose                                        Default action
===============  ==========================================  ==================
``OPEN_PALM``    All five fingers relaxed and extended       Move cursor
``FIST``         All fingers curled                          Pause (idle)
``INDEX_ONLY``   Only the index finger extended              Left click (pinch)
``PINCH``        Thumb touching index/middle tip             Left click
``TWO_FINGERS``  Index + middle extended                     Right click
``THREE_FINGERS``Index + middle + ring extended              Double click
``FOUR_FINGERS`` Index..pinky extended                       *Free* (user can assign)
===============  ==========================================  ==================

Any of these can additionally be mapped to *drag*, *scroll*, *enter*, etc. in
the Gesture page. Handedness does not change the mapping: left and right hands
produce identical features, so both work out of the box.

Recognition returns a *score* (0..1) that reflects how cleanly the pose matched
a rule. Poses that sit between two gestures get low scores and are stabilised
away by the temporal filter rather than being reported.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .pose import HandPose
from . import geometry as geo

#: Largest palm size that is physically plausible. All coordinates are
#: normalised to image width (0..1), so a palm spanning more than ~half the
#: frame means the hand is at the lens. Beyond this the landmarks are zoomed
#: synthetic input rather than a real hand.
MAX_PALM_SIZE = 0.62

# Canonical gesture identifiers
OPEN_PALM = "open_palm"
FIST = "fist"
INDEX_ONLY = "index_only"
PINCH = "pinch"
TWO_FINGERS = "two_fingers"
THREE_FINGERS = "three_fingers"
FOUR_FINGERS = "four_fingers"
UNKNOWN = "unknown"

#: Gestures the user can bind to actions (in the order shown in the UI).
GESTURES = (
    OPEN_PALM,
    FIST,
    INDEX_ONLY,
    PINCH,
    TWO_FINGERS,
    THREE_FINGERS,
    FOUR_FINGERS,
)

GESTURE_LABELS = {
    OPEN_PALM: "Open Palm",
    FIST: "Fist",
    INDEX_ONLY: "Point (index)",
    PINCH: "Pinch",
    TWO_FINGERS: "Two fingers",
    THREE_FINGERS: "Three fingers",
    FOUR_FINGERS: "Four fingers",
    UNKNOWN: "No gesture",
}

GESTURE_HINTS = {
    OPEN_PALM: "Relaxed open hand - move your palm to move the cursor.",
    FIST: "All fingers curled - grab and drag the item with the cursor.",
    INDEX_ONLY: "Index finger up, others relaxed. Pinch the thumb to it to click.",
    PINCH: "Touch thumb and index finger tips together - a pinch click.",
    TWO_FINGERS: "Index and middle up, like a relaxed peace sign.",
    THREE_FINGERS: "Index, middle and ring up. Keep the pinky relaxed.",
    FOUR_FINGERS: "Four fingers up, thumb relaxed.",
}

#: Actions a gesture can be mapped to.
ACTIONS = (
    "move",
    "left_click",
    "right_click",
    "double_click",
    "drag",
    "scroll",
    "pause",
    "none",
)

ACTION_LABELS = {
    "move": "Move cursor",
    "left_click": "Left click",
    "right_click": "Right click",
    "double_click": "Double click",
    "drag": "Click and drag",
    "scroll": "Scroll",
    "pause": "Pause control",
    "none": "Do nothing",
}


@dataclass
class Detection:
    gesture: str
    score: float
    candidates: dict[str, float]


class GestureRecognizer:
    """Stateless per-frame classifier for one hand."""

    def __init__(self, sensitivity: float = 0.5):
        self.sensitivity = sensitivity  # 0..1, higher = more forgiving

    def _t(self, tolerant: float, strict: float) -> float:
        """Interpolate a threshold between strict (sensitivity 0) and tolerant (1)."""
        return strict + (tolerant - strict) * max(0.0, min(1.0, self.sensitivity))

    def recognize(self, pose: HandPose) -> Detection:
        st = pose.finger_state
        index, middle, ring, pinky, thumb = (
            st(f) for f in ("index", "middle", "ring", "pinky", "thumb")
        )

        # Pinch / click: thumb tip close to index tip. Geometrically sound, but
        # require the index to be roughly straight - a fist has the thumb near
        # the index knuckles too, and must never read as a pinch.
        # Tip separation is measured in palm units. A relaxed open hand keeps
        # thumb and index tips ~0.4-0.6 palm units apart, so the "touched"
        # threshold must sit clearly *below* that or every open palm would read
        # as a pinch.
        pinch_on = 0.30
        pinch_off = 0.44
        index_straight = st("index") == "Open" and pose.extension["index"] >= 0.85
        scores: dict[str, float] = {}

        # ---- scrolling: index+middle extended and held parallel apart, i.e.
        # the "two finger" pose also used for right click. Scroll is a *gesture
        # transition* action handled by the interaction controller, not a
        # separate pose. Here we only classify poses.
        scores[PINCH] = _ramp_down(pose.thumb_index_ratio, pinch_off, pinch_on) * (
            1.0 if index_straight else 0.0
        )

        # A "Mid" finger is genuinely ambiguous (mid-transition). It must not
        # count as open for one gesture and closed for another, otherwise
        # neighbouring poses (two vs three fingers) fire together. We therefore
        # evaluate the count of clearly-open fingers and the count of clearly
        # closed ones separately.
        four = ("index", "middle", "ring", "pinky")
        open_cnt = sum(1 for f in four if st(f) == "Open")
        closed_cnt = sum(1 for f in four if st(f) == "Closed")
        mid_cnt = 4 - open_cnt - closed_cnt
        thumb_curled = st("thumb") == "Closed"

        # Pinch means the thumb and index tips meet. In that pose the thumb is
        # necessarily curled, so "index_only" (a relaxed pointing hand with the
        # thumb out of the way) must not also claim it, otherwise a clean pinch
        # is a permanent 50/50 tie and never becomes a :class:`Detection`.
        pinching = (
            scores.get(PINCH, 0.0) >= 0.6
            and thumb == "Closed"
            and open_cnt <= 1
        )

        if index == "Open" and not pinching:
            if open_cnt == 1 and closed_cnt >= 2:
                # Only the index clearly up, the rest tucked -> point
                scores[INDEX_ONLY] = 0.70 + 0.30 * (closed_cnt / 3.0)
            elif open_cnt == 2 and middle == "Open" and ring != "Open" and pinky != "Open":
                scores[TWO_FINGERS] = 0.70 + 0.30 * (closed_cnt / 2.0)
            elif open_cnt == 3 and middle == "Open" and ring == "Open" and pinky != "Open":
                scores[THREE_FINGERS] = 0.70 + 0.30 * (1.0 if pinky == "Closed" else 0.5)

        # Open palm vs four fingers: both have four fingers up, so the only
        # unambiguous, comfortable difference is whether the thumb is tucked
        # against the palm. Exactly one of the two is scored - never both - so
        # they cannot tie and swallow each other in the margin calculation.
        if open_cnt == 4:
            if thumb_curled:
                scores[FOUR_FINGERS] = 0.72 + 0.25 * pose.openness
                scores.pop(OPEN_PALM, None)
            else:
                scores[OPEN_PALM] = 0.80 + 0.20 * (1.0 - pose.curl["thumb"])
                scores.pop(FOUR_FINGERS, None)

        # Fist: all four fingers clearly closed. A relaxed thumb is still a fist.
        if closed_cnt == 4:
            scores[FIST] = 0.80 + 0.20 * (1.0 if thumb != "Open" else 0.0)
        elif mid_cnt == 0 and closed_cnt == 3 and open_cnt == 0:
            scores[FIST] = 0.70

        # Require a physically plausible palm scale. Very small palms (hand far
        # away) give unreliable landmarks; very large ones mean the hand is
        # touching the lens (or the frame is synthetic). Both are refused rather
        # than guessed, because the stabiliser will simply hold the last pose.
        plausible = 0.035 <= pose.palm_size <= MAX_PALM_SIZE
        if not plausible:
            return Detection(UNKNOWN, 0.0, scores)

        if not scores:
            return Detection(UNKNOWN, 0.0, {})

        best, best_score = max(scores.items(), key=lambda kv: kv[1])
        second = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0.0
        margin = best_score - second

        if best_score < 0.5:
            return Detection(UNKNOWN, best_score, scores)

        # Ambiguous frames (two near-equal rules) are reported with low confidence
        ambiguity_penalty = 1.0 if margin > 0.15 else 0.55 + margin
        return Detection(
            best, max(0.0, min(1.0, best_score * ambiguity_penalty)), scores
        )


def _ramp_down(value: float, high: float, low: float) -> float:
    """1 when value <= low, 0 when value >= high, linear in between."""
    if value <= low:
        return 1.0
    if value >= high:
        return 0.0
    return (high - value) / max(1e-6, high - low)


def score_to_hint(gesture: Optional[str]) -> str:
    return GESTURE_HINTS.get(gesture or UNKNOWN, "")
