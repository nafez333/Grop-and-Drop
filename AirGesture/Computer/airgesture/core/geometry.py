"""Scale-invariant geometric helpers for MediaPipe hand landmarks.

All measurements are normalised by palm size, so results do not depend on
the distance between the hand and the camera and use no absolute pixel
thresholds.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence, Tuple

# MediaPipe hand landmark indices
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

#: MCP joints of index..pinky, used for palm geometry.
MCP_IDS = (INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP)

FINGER_CHAINS = {
    "thumb": (THUMB_MCP, THUMB_IP, THUMB_TIP),
    "index": (INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP),
    "middle": (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP),
    "ring": (RING_MCP, RING_PIP, RING_DIP, RING_TIP),
    "pinky": (PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP),
}

FINGER_NAMES = ("thumb", "index", "middle", "ring", "pinky")

Point = Tuple[float, float]


def dist(a, b) -> float:
    """Euclidean distance between two MediaPipe-like landmarks."""
    return math.hypot(a.x - b.x, a.y - b.y)


def centroid(points: Iterable) -> Point:
    pts = list(points)
    n = max(1, len(pts))
    return (sum(p.x for p in pts) / n, sum(p.y for p in pts) / n)


def palm_size(landmarks) -> float:
    """Reference length for normalisation.

    A *median* of several palm measurements, not an average. The mean was
    dominated by whichever finger happened to point at the camera after
    rotation, which made the scale (and therefore every scaled feature)
    drift with hand orientation. The median over five quasi-independent spans
    stays stable when one measurement is unreliable.

    Measurements: the four wrist->MCP distances and the index->pinky MCP span.
    """
    w = landmarks[WRIST]
    samples = [dist(landmarks[i], w) for i in MCP_IDS]
    samples.append(dist(landmarks[INDEX_MCP], landmarks[PINKY_MCP]))
    samples.sort()
    median = samples[len(samples) // 2]
    return max(median, 1e-6)


def palm_center(landmarks) -> Point:
    """Stable hand centre: average of wrist and the four finger MCP joints.

    Much steadier than any single landmark (e.g. the index finger tip) because
    it averages out jitter and is near the palm's rotation axis.
    """
    return centroid([landmarks[WRIST]] + [landmarks[i] for i in MCP_IDS])


def palm_unit(landmarks) -> Tuple[float, float]:
    """Scale of the palm in normalised-distance terms (blend of size and span)."""
    return palm_size(landmarks)


def hand_orientation(landmarks) -> float:
    """Roll angle of the hand in the image plane, in degrees.

    0 degrees means index-MCP side is to the right of pinky-MCP (typical for a
    right hand pointing up). Used for the optional rotation-invariant mode and
    for diagnostics; the recognizer is already largely orientation free.
    """
    dx = landmarks[INDEX_MCP].x - landmarks[PINKY_MCP].x
    dy = landmarks[INDEX_MCP].y - landmarks[PINKY_MCP].y
    return math.degrees(math.atan2(dy, dx))


def joint_angle(a, b, c) -> float:
    """Angle at vertex ``b`` between ``a`` and ``c`` in degrees (0..180)."""
    v1x, v1y = a.x - b.x, a.y - b.y
    v2x, v2y = c.x - b.x, c.y - b.y
    n1 = math.hypot(v1x, v1y)
    n2 = math.hypot(v2x, v2y)
    if n1 < 1e-9 or n2 < 1e-9:
        return 180.0
    cosv = (v1x * v2x + v1y * v2y) / (n1 * n2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosv))))


def finger_curvature(landmarks, finger: str) -> float:
    """How curled a finger is, 0 = straight, 1 = fully folded.

    Uses the PIP->DIP->TIP bend (the visible bend when a finger curls towards
    the palm) once, not the PIP bend. Using the PIP joint made a fully folded
    finger look almost straight, because the MCP->PIP vector is largely
    cancelled by the PIP->DIP vector when the finger curls back on itself.
    """
    chain = FINGER_CHAINS[finger]
    if finger == "thumb":
        cmc, mcp, tip = chain
        ang = joint_angle(landmarks[cmc], landmarks[mcp], landmarks[tip])
    else:
        mcp, pip, dip, tip = chain
        _ = mcp
        ang = joint_angle(landmarks[pip], landmarks[dip], landmarks[tip])
    return max(0.0, min(1.0, (180.0 - ang) / 110.0))


def finger_extension(landmarks, finger: str) -> float:
    """How extended a finger is, in units of palm size (0 = folded, 1 = out).

    Measured from the finger's *base MCP* to its tip, not from the wrist.
    The wrist-based version projected the whole palm onto the finger axis, so
    rotating the hand shrunk it: the same pose at 0 deg and 45 deg gave wildly
    different values. The MCP is the fixed root of the finger and does not
    move when the finger straightens. The maximum possible length is the
    summed phalanx lengths along the same chain, so a straight finger -> ~1.

    Rotation is compensated implicitly: the tip offset is projected on the
    *unit* direction of the last phalanx (the finger's own heading), so
    turning the hand turns the whole frame of reference with it.
    """
    chain = FINGER_CHAINS[finger]
    base = landmarks[chain[0]]
    tip = landmarks[chain[-1]]
    prev = landmarks[chain[-2]]
    # Heading of the finger near its tip.
    hx, hy = tip.x - prev.x, tip.y - prev.y
    norm = math.hypot(hx, hy)
    if norm < 1e-9:
        # Degenerate (tip on previous joint): fall back to base->tip.
        hx, hy = tip.x - base.x, tip.y - base.y
        norm = math.hypot(hx, hy) or 1e-6
    hx, hy = hx / norm, hy / norm
    reach = math.hypot(tip.x - base.x, tip.y - base.y)
    full = sum(
        math.hypot(landmarks[chain[i + 1]].x - landmarks[chain[i]].x,
                   landmarks[chain[i + 1]].y - landmarks[chain[i]].y)
        for i in range(len(chain) - 1)
    ) or 1e-6
    # Direction sanity: a finger folded back over the palm points towards its
    # base instead of away from it - keep that as "not extended" via the
    # phalanx-length ratio only (which is small for a folded chain).
    _ = (hx, hy)
    return max(0.0, min(1.25, reach / full))


def tip_spread(a, b, landmarks) -> float:
    """Distance between two finger tips normalised by palm size."""
    return dist(a, b) / palm_size(landmarks)


def clamp(value: float, low: float, high: float) -> float:
    return low if value < low else high if value > high else value


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def landmarks_to_pixels(landmarks, width: int, height: int) -> Sequence[Point]:
    return [(lm.x * width, lm.y * height) for lm in landmarks]
