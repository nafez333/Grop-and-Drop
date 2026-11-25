"""Temporary diagnostic: DirectShow timing after MediaPipe init (app-like order)."""

import time

import cv2

from airgesture.runtime.tracking import HandTracker

tr = HandTracker()  # create MediaPipe first, like the app does
for label, be in (("DSHOW", cv2.CAP_DSHOW), ("MSMF", cv2.CAP_MSMF)):
    t = time.time()
    cap = cv2.VideoCapture(0, be)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    ok, frame = cap.read()
    print(
        label,
        "ok",
        bool(ok),
        "%.1fs" % (time.time() - t),
        None if frame is None else frame.shape,
    )
    cap.release()
tr.close()
