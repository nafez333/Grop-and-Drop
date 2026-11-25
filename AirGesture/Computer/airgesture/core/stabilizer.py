"""Temporal stabilisation of gesture detections.

Raw per-frame classification is noisy. This module turns a stream of
:class:`~.recognizer.Detection` results into a stable, de-bounced gesture
stream with hysteresis, confidence scoring and drop-out tolerance:

* Each candidate gesture accumulates a weighted *score* per frame
  (score * learned confidence, decaying with time). The winner must clearly
  beat the current gesture before a switch happens (**hysteresis**), which
  removes flicker between neighbouring poses.
* A new gesture must be *held* for ``min_frames`` frames and the winning
  score must exceed ``switch_threshold`` before it is accepted.
* Short tracking drop-outs (``max_gap_s``) freeze the current gesture instead
  of resetting, so a momentary landmark loss does not stop cursor movement or
  release a drag.
* Sustained loss longer than ``max_gap_s`` reports ``None`` ("hand lost") so
  the interaction layer can apply its safety behaviour.
"""

from __future__ import annotations

from typing import Optional

from .recognizer import UNKNOWN, Detection


class GestureStabilizer:
    def __init__(
        self,
        window_s: float = 0.45,
        switch_threshold: float = 1.5,
        hold_advantage: float = 1.3,
        min_frames: int = 3,
        max_gap_s: float = 0.6,
        learned_confidence: Optional[dict[str, float]] = None,
    ):
        self.window_s = window_s
        self.switch_threshold = switch_threshold
        self.hold_advantage = hold_advantage
        self.min_frames = max(1, int(min_frames))
        self.max_gap_s = max_gap_s
        self.learned_confidence = dict(learned_confidence or {})

        self._history: list[tuple[float, Detection]] = []
        self.current: Optional[str] = None
        self.confidence: float = 0.0
        self.pending: Optional[str] = None
        self.pending_count: int = 0
        self.last_seen: float = -1e9
        self._accepted_at: float = 0.0

    # ------------------------------------------------------------------ API
    def reset(self) -> None:
        self._history.clear()
        self.current = None
        self.confidence = 0.0
        self.pending = None
        self.pending_count = 0
        self._accepted_at = 0.0

    def set_learned_confidence(self, mapping: dict[str, float]) -> None:
        self.learned_confidence = dict(mapping or {})

    def update(self, detection: Optional[Detection], now: float) -> Optional[str]:
        """Feed one frame. Returns the stabilised gesture (``None`` = hand lost)."""
        if detection is None:
            return self._no_hand(now)

        self.last_seen = now

        horizon = now - self.window_s
        self._history = [h for h in self._history if h[0] >= horizon]
        if detection.gesture != UNKNOWN and detection.score > 0.0:
            self._history.append((now, detection))

        votes: dict[str, float] = {}
        for ts, det in self._history:
            weight = max(0.0, 1.0 - (now - ts) / max(1e-3, self.window_s))
            factor = self.learned_confidence.get(det.gesture, 1.0)
            votes[det.gesture] = votes.get(det.gesture, 0.0) + weight * det.score * factor

        if not votes:
            # Unclear frames (in-between poses) keep the current gesture as long
            # as the hand itself is still visible, but confidence slowly decays.
            if self.current is not None:
                self.confidence *= 0.9
            return self.current

        best = max(votes, key=votes.get)
        best_score = votes[best]
        current_score = votes.get(self.current, 0.0) if self.current else 0.0

        if best == self.current:
            self.pending = None
            self.pending_count = 0
            self.confidence = _conf(best_score)
            return self.current

        # Hysteresis: the challenger must beat the incumbent by a clear margin.
        challenger_wins = best_score >= self.switch_threshold and (
            current_score <= 0.0 or best_score >= current_score * self.hold_advantage
        )
        if challenger_wins:
            if self.pending == best:
                self.pending_count += 1
            else:
                self.pending = best
                self.pending_count = 1
            if self.pending_count >= self.min_frames or self.current is None:
                self.current = best
                self.pending = None
                self.pending_count = 0
                self._accepted_at = now
                self.confidence = _conf(best_score)
        else:
            # Abort a pending switch when the incumbent is confirmed again.
            if self.current is not None and self._history and self._history[-1][1].gesture == self.current:
                self.pending = None
                self.pending_count = 0
            self.confidence = max(_conf(current_score), self.confidence * 0.85)

        return self.current

    def hold_seconds(self, now: float) -> float:
        """How long (s) the current stabilised gesture has been active."""
        if self.current is None:
            return 0.0
        return max(0.0, now - self._accepted_at)

    # -------------------------------------------------------------- internals
    def _no_hand(self, now: float) -> Optional[str]:
        if now - self.last_seen <= self.max_gap_s:
            return self.current  # tolerate brief landmark loss
        self.reset()
        return None


def _conf(raw: float) -> float:
    """Map accumulated window vote to a 0..1 confidence."""
    return max(0.0, min(1.0, raw / 2.6))
