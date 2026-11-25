import time, traceback, threading
from airgesture.core.settings import SettingsManager
from airgesture.runtime.mouse_controller import MouseController
from airgesture.runtime.engine import EngineThread
s = SettingsManager()
print("camera cfg:", s.section("camera"))
m = MouseController()
frames = []
e = EngineThread(s, m, lambda p: frames.append(p), lambda st, msg: print("STATUS:", st, "|", msg))
e.start()
time.sleep(6)
print("running:", e.running, "frames:", len(frames))
print("camera is_open:", e.camera.is_open, "failures:", e.camera.consecutive_failures, "err:", e.camera.last_error)
print("tracker:", e.tracker)
threads = [t.name for t in threading.enumerate()]
print("threads:", threads)
e.stop()
