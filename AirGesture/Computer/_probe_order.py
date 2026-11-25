"""Temporary diagnostic: isolate what blocks the camera open."""

import time
import traceback

from airgesture.runtime.camera_manager import CameraManager, _backend_priority

print("backends:", _backend_priority(clear_first=True))

cam = CameraManager()
print("--- open BEFORE mediapipe ---")
t = time.time()
print(
    "opened:",
    cam.open(0, 1280, 720, 30, timeout=10),
    "in %.1fs" % (time.time() - t),
    cam.last_error,
)
cam.close()

print("--- import + create tracker ---")
try:
    from airgesture.runtime.tracking import HandTracker

    tr = HandTracker()
    print("tracker created")
except Exception:
    traceback.print_exc()
    tr = None

print("--- open AFTER mediapipe ---")
t = time.time()
ok = cam.open(0, 1280, 720, 30, timeout=10)
print("opened:", ok, "in %.1fs" % (time.time() - t), cam.last_error)
print("frame:", None if cam.read_frame() is None else "ok")
cam.close()
if tr:
    tr.close()
