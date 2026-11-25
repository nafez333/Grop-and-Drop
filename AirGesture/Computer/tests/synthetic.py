"""Synthetic landmark builders for unit tests.

Builds fake MediaPipe-style landmark objects (with .x, .y, .z attributes) that
represent canonical hand poses. All poses are normalised (palm size ~1.0) so
they are scale-invariant. Rotation helpers produce the same pose turned by an
angle in the image plane.

Coordinate convention: y increases downward (image coordinates). All fingers
radiate from the middle MCP at (0.50, 0.50) which is the reference centre used
by ``finger_extension``. Extended tips lie further along the same radial vector
from the centre through the MCP; curled tips collapse back to the MCP so
extension ≈ 0 and curl > 0.8.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List


@dataclass
class _Lm:
    x: float
    y: float
    z: float = 0.0


# MediaPipe indices
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20


def _rotate_point(x: float, y: float, angle_deg: float, cx: float, cy: float):
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    dx, dy = x - cx, y - cy
    return cx + dx * ca - dy * sa, cy + dx * sa + dy * ca


def _build_palm(open_fingers: list, scale: float = 1.0) -> List[_Lm]:
    """Build a canonical hand with the given fingers extended.

    Fingers radiate from the middle MCP at (0.50, 0.50). Extended tips lie
    further along the same radial vector from the centre through the MCP;
    curled tips collapse back to the MCP.
    """
    extended = set(open_fingers)
    # idx: (mcp_xy, tip_extended_xy, tip_curled_xy)
    layout = {
        THUMB_CMC:   ((0.44, 0.60), None, None),
        THUMB_MCP:   ((0.40, 0.62), None, None),
        THUMB_IP:    ((0.36, 0.64), None, None),
        THUMB_TIP:   ((0.32, 0.66), (0.24, 0.70), (0.36, 0.62)),
        INDEX_MCP:   ((0.43, 0.43), None, None),
        INDEX_PIP:   ((0.40, 0.36), None, None),
        INDEX_DIP:   ((0.37, 0.29), None, None),
        INDEX_TIP:   ((0.34, 0.22), (0.26, 0.14), (0.38, 0.30)),
        MIDDLE_MCP:  ((0.50, 0.50), None, None),
        MIDDLE_PIP:  ((0.50, 0.42), None, None),
        MIDDLE_DIP:  ((0.50, 0.34), None, None),
        MIDDLE_TIP:  ((0.50, 0.26), (0.50, 0.18), (0.50, 0.38)),
        RING_MCP:    ((0.57, 0.43), None, None),
        RING_PIP:    ((0.60, 0.36), None, None),
        RING_DIP:    ((0.63, 0.29), None, None),
        RING_TIP:    ((0.66, 0.22), (0.74, 0.14), (0.60, 0.30)),
        PINKY_MCP:   ((0.70, 0.50), None, None),
        PINKY_PIP:   ((0.74, 0.55), None, None),
        PINKY_DIP:   ((0.76, 0.60), None, None),
        PINKY_TIP:   ((0.78, 0.66), (0.86, 0.72), (0.72, 0.60)),
    }
    pts: dict[int, _Lm] = {WRIST: _Lm(0.50, 0.75)}
    for idx in range(1, 21):
        mcp_xy, tip_ext, tip_curled = layout[idx]
        x, y = mcp_xy
        name = None
        if idx == THUMB_TIP:
            name = "thumb"
        elif idx == INDEX_TIP:
            name = "index"
        elif idx == MIDDLE_TIP:
            name = "middle"
        elif idx == RING_TIP:
            name = "ring"
        elif idx == PINKY_TIP:
            name = "pinky"
        if name:
            if name in extended:
                x, y = tip_ext
            else:
                x, y = tip_curled
        pts[idx] = _Lm(x * scale + 0.0, y * scale + 0.0)
    return [pts[i] for i in range(21)]


def open_palm(scale: float = 1.0, angle: float = 0.0, cx: float = 0.5, cy: float = 0.5) -> List[_Lm]:
    pts = _build_palm(["thumb", "index", "middle", "ring", "pinky"], scale)
    return _apply_transform(pts, angle, cx, cy)


def fist(scale: float = 1.0, angle: float = 0.0, cx: float = 0.5, cy: float = 0.5) -> List[_Lm]:
    pts = _build_palm([], scale)
    return _apply_transform(pts, angle, cx, cy)


def index_only(scale: float = 1.0, angle: float = 0.0, cx: float = 0.5, cy: float = 0.5) -> List[_Lm]:
    pts = _build_palm(["index"], scale)
    return _apply_transform(pts, angle, cx, cy)


def pinch(scale: float = 1.0, angle: float = 0.0, cx: float = 0.5, cy: float = 0.5) -> List[_Lm]:
    pts = _build_palm(["index"], scale)
    # thumb tip touches index tip
    pts[THUMB_TIP] = _Lm(pts[INDEX_TIP].x - 0.015 * scale, pts[INDEX_TIP].y, 0.0)
    return _apply_transform(pts, angle, cx, cy)


def two_fingers(scale: float = 1.0, angle: float = 0.0, cx: float = 0.5, cy: float = 0.5) -> List[_Lm]:
    pts = _build_palm(["index", "middle"], scale)
    return _apply_transform(pts, angle, cx, cy)


def three_fingers(scale: float = 1.0, angle: float = 0.0, cx: float = 0.5, cy: float = 0.5) -> List[_Lm]:
    pts = _build_palm(["index", "middle", "ring"], scale)
    return _apply_transform(pts, angle, cx, cy)


def four_fingers(scale: float = 1.0, angle: float = 0.0, cx: float = 0.5, cy: float = 0.5) -> List[_Lm]:
    pts = _build_palm(["index", "middle", "ring", "pinky"], scale)
    return _apply_transform(pts, angle, cx, cy)


def _apply_transform(pts: List[_Lm], angle: float, cx: float, cy: float) -> List[_Lm]:
    if angle == 0.0 and cx == 0.5 and cy == 0.5:
        return pts
    out = []
    for lm in pts:
        nx, ny = _rotate_point(lm.x, lm.y, angle, cx, cy)
        out.append(_Lm(nx, ny, lm.z))
    return out


def pose_list(*poses: List[_Lm]) -> List[_Lm]:
    """Concatenate multiple pose lists (for multi-frame sequences)."""
    return list(poses)