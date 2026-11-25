"""Temporary diagnostic: measure real engine throughput and per-frame cost."""

import time

from airgesture.core.settings import SettingsManager
from airgesture.runtime.engine import EngineThread
from airgesture.runtime.mouse_controller import MouseController

stamps = []
s = SettingsManager()
e = EngineThread(
    s, MouseController(), lambda p: stamps.append(p.timestamp), lambda st, msg: None
)
e.start()
time.sleep(12)
n = len(stamps)
span = (stamps[-1] - stamps[0]) if n > 1 else 0
print("frames:", n, "span %.1fs" % span, "fps %.1f" % (n / span if span else 0))
print("frame_ms ema:", round(e._frame_ms_ema, 1))
print("camera fps prop:", e.camera.fps, "size:", e.camera.width, e.camera.height)
last = e.latest()
print("packet fps:", round(last.fps, 1), "frame_ms:", round(last.frame_ms, 1))
e.stop()
