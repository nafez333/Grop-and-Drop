"""Temporary diagnostic: why does the standalone engine produce no frames?"""

import threading
import time

from airgesture.core.settings import SettingsManager
from airgesture.runtime.engine import EngineThread
from airgesture.runtime.mouse_controller import MouseController

s = SettingsManager()
e = EngineThread(
    s, MouseController(), lambda p: None, lambda st, msg: print("STATUS:", st, "|", msg)
)
e.start()
for i in range(6):
    time.sleep(1)
    print(
        i,
        "running",
        e.running,
        "camera_open",
        e.camera.is_open,
        "failures",
        e.camera.consecutive_failures,
        "tracker",
        e.tracker is not None,
        "threads",
        [t.name for t in threading.enumerate() if t.name != "MainThread"],
    )
print("last_error:", e.camera.last_error)
e.stop()
