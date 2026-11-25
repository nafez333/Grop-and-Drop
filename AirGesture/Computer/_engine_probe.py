import time
from airgesture.core.settings import SettingsManager
from airgesture.runtime.mouse_controller import MouseController
from airgesture.runtime.engine import EngineThread
s = SettingsManager()
m = MouseController()
e = EngineThread(s, m, lambda p: None, lambda st, msg: print("STATUS", st, "|", msg))
print("settings camera:", s.section("camera"))
print("open:", e.camera.open(0, 1280, 720, 30), e.camera.last_error)
print("read:", None if e.camera.read_frame() is None else "ok")
e.camera.close()
e.start()
for i in range(40):
    time.sleep(0.25)
    p = e.latest()
    print(i, "running", e.running, "frame", None if p.frame is None else p.frame.shape, "err", p.error, "msg", p.message)
    if p.frame is not None: break
e.stop()
print("done")
