"""Temporary diagnostic: reproduce engine resource opening step by step."""

import time
import traceback

import cv2
import mediapipe as mp
import tkinter as tk

from airgesture.core.settings import SettingsManager
from airgesture.runtime.mouse_controller import MouseController
from airgesture.runtime.engine import EngineThread
from airgesture.runtime.tracking import HandTracker

root = tk.Tk()
root.withdraw()
pkt = None
e = None


def run():
    global e
    s = SettingsManager()
    m = MouseController()
    e = EngineThread(
        s, m, lambda p: None, lambda st, msg: print("STATUS:", st, "|", msg)
    )
    print("--- plain open ---")
    print("open:", e.camera.open(0, 1280, 720, 30), e.camera.last_error)
    e.camera.close()
    print("--- tracker ---")
    try:
        t = HandTracker()
        print("tracker ok")
        t.close()
    except Exception:
        traceback.print_exc()
    print("--- engine._open_resources ---")
    try:
        e._open_resources()
        print(
            "camera_opened:",
            e._camera_opened,
            "tracker:",
            e.tracker,
            "held:",
            e.camera.is_open,
        )
    except Exception:
        traceback.print_exc()
    e.camera.close()
    if e.tracker:
        e.tracker.close()
    root.after(100, root.quit)


root.after(200, run)
root.mainloop()
root.destroy()
