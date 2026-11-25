import traceback
from airgesture.app import AirGestureApp
app = AirGestureApp()
def step():
    try:
        pkt = app.engine.latest()
        print("engine running:", app.engine.running)
        print("camera open:", app.engine.camera.is_open, "err:", app.engine.camera.last_error)
        print("tracker:", app.engine.tracker)
        print("packet frame:", None if pkt.frame is None else pkt.frame.shape)
        print("frame_pending:", app._frame_pending, "last packet:", None if app._last_packet is None else "set")
        print("_drain_frames exists:", hasattr(app, "_drain_frames"))
    except Exception:
        traceback.print_exc()
    finally:
        app.after(300, app.quit)
app.after(3000, step)
app.mainloop()
