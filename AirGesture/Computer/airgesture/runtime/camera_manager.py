"""Camera discovery and lifecycle management.

Owns the ``cv2.VideoCapture`` object so that no other component has to worry
about resources. Handles open failures, read failures (USB glitch, camera in
use, unplugged) and provides a thread-safe :meth:`read_frame` suitable for a
background processing thread.
"""

from __future__ import annotations

import threading
import time
from typing import Optional, Tuple

import cv2
import numpy as np


class CameraError(RuntimeError):
    pass


#: Set if DirectShow ever fails to open in this process; the manager then
#: sticks to Media Foundation for the rest of the session.
_DSHOW_UNUSABLE = False


def _backend_priority(clear_first: bool = False) -> list[int]:
    """Video backends to try, best first.

    Measured on the target machine: DirectShow opens a 1280x720 stream in
    ~1.5-2.5 s, while Media Foundation takes ~14-18 s (it enumerates every
    format before the first frame arrives). DirectShow is therefore preferred,
    with Media Foundation as a fallback for machines where DirectShow is
    unavailable.
    """
    backends = []
    if not _DSHOW_UNUSABLE:
        backends.append(cv2.CAP_DSHOW)
    backends.extend([cv2.CAP_MSMF, cv2.CAP_ANY])
    return backends


class CameraManager:
    """Manages one camera device with automatic recovery.

    ``read_frame`` never raises for transient failures: it returns ``None`` and
    tracks consecutive failures, allowing the caller (tracking engine) to keep
    the UI responsive and report a meaningful status.
    """

    def __init__(self):
        self._cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.RLock()
        self.index: int = 0
        self.width: int = 0
        self.height: int = 0
        self.fps: float = 0.0
        self.is_open: bool = False
        self.last_error: Optional[str] = None
        self.consecutive_failures: int = 0
        self.opened_at: float = 0.0

    # ------------------------------------------------------------------ open
    def open(
        self, index: int = 0, width: int = 1280, height: int = 720, fps: int = 30,
        timeout: float = 20.0,
    ) -> bool:
        """Open a camera. Never blocks the caller longer than ``timeout`` seconds.

        The backend open call can hang indefinitely when the device is
        contended (observed with OpenCV: a C++ error is logged, then
        ``VideoCapture`` blocks forever). The open therefore runs on a helper
        thread; if it does not finish in time the user gets a clear, actionable
        error instead of a frozen application. The timeout is generous because
        Media Foundation legitimately needs ~15-18 s on some systems.
        """
        self.close()
        with self._lock:
            self.index = int(index)
            self.last_error = None
            self.consecutive_failures = 0

        result: dict = {"cap": None}
        done = threading.Event()

        def _worker():
            global _DSHOW_UNUSABLE
            cap = None
            try:
                for backend in _backend_priority(clear_first=True):
                    try:
                        candidate = cv2.VideoCapture(self.index, backend)
                    except cv2.error:
                        # DirectShow is the plugin that starts failing after
                        # MediaPipe initialised; remember it for this process.
                        if backend == cv2.CAP_DSHOW:
                            _DSHOW_UNUSABLE = True
                        continue
                    if candidate is not None and candidate.isOpened():
                        cap = candidate
                        break
                    if candidate is not None:
                        try:
                            candidate.release()
                        except cv2.error:
                            pass
            except Exception:  # never let the worker die silently
                pass
            result["cap"] = cap
            done.set()

        worker = threading.Thread(target=_worker, name="CameraOpen", daemon=True)
        worker.start()

        if not done.wait(timeout):
            self.is_open = False
            self.last_error = (
                f"Camera {self.index} did not respond within {int(timeout)}s. "
                "It is probably used by another application (Zoom, Teams, browser). "
                "Close that app, then press Restart camera."
            )
            return False

        cap = result["cap"]
        if cap is None:
            self.is_open = False
            self.last_error = (
                f"Camera {self.index} could not be opened. Check that it is connected "
                "and not used by another application, or choose another device "
                "on the Camera page."
            )
            return False

        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
            cap.set(cv2.CAP_PROP_FPS, int(fps))
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except cv2.error:
            pass

        # Warm-up: some drivers return black frames for the first reads, and a
        # few (DirectShow on this hardware) need the resolution hints re-applied
        # once the graph is running before they produce a frame at all.
        ok = False
        for attempt in range(30):
            try:
                ok, _frame = cap.read()
            except cv2.error:
                ok = False
            if ok:
                break
            if attempt == 10:
                try:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
                except cv2.error:
                    pass
            time.sleep(0.1)
        if not ok:
            try:
                cap.release()
            except cv2.error:
                pass
            self.is_open = False
            self.last_error = (
                "The camera opened but delivered no video frames. "
                "Unplug and replug it, or pick another device on the Camera page."
            )
            return False

        with self._lock:
            self._cap = cap
            self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or width)
            self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or height)
            self.fps = float(cap.get(cv2.CAP_PROP_FPS) or fps)
            self.is_open = True
            self.last_error = None
            self.consecutive_failures = 0
            self.opened_at = time.time()
            return True

    # ------------------------------------------------------------------ read
    def read_frame(self) -> Optional[np.ndarray]:
        """Return a BGR frame or ``None`` if the camera is unavailable.

        Grabs twice when the buffer is large to avoid processing an old frame.
        """
        with self._lock:
            if self._cap is None or not self.is_open:
                return None
            try:
                ok, frame = self._cap.read()
            except cv2.error as exc:
                ok, frame = False, None
                self.last_error = f"Camera read error: {exc}"
            if not ok or frame is None:
                self.consecutive_failures += 1
                return None
            self.consecutive_failures = 0
            return frame

    # ----------------------------------------------------------------- close
    def close(self) -> None:
        with self._lock:
            if self._cap is not None:
                try:
                    self._cap.release()
                except cv2.error:
                    pass
            self._cap = None
            self.is_open = False

    def info(self) -> Tuple[int, int, int]:
        return self.index, self.width, self.height

    @staticmethod
    def probe(max_index: int = 8) -> list[int]:
        """List camera indices that can be opened. Slow (~0.3s per device)."""
        found: list[int] = []
        for idx in range(max_index):
            cap = None
            try:
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if cap is not None and cap.isOpened():
                    found.append(idx)
            except cv2.error:
                pass
            finally:
                if cap is not None:
                    try:
                        cap.release()
                    except cv2.error:
                        pass
        return found

    @staticmethod
    def friendly_name(index: int, width: int, height: int) -> str:
        return f"Camera {index}" + (f"  ({width}x{height})" if width and height else "")
