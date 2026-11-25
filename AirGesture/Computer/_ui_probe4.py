import time, traceback
from airgesture.app import AirGestureApp
app = AirGestureApp()
seen = {"n": 0}
orig = app._start_frame_pump
def step():
    try:
        dash = app._pages["dashboard"]
        pkt = dash.cam_panel._packet
        print("delivered packets:", app._last_delivered is not None)
        print("cam panel packet frame:", None if pkt is None or pkt.frame is None else pkt.frame.shape)
        print("photo rendered:", dash.cam_panel._photo is not None)
        print("canvas items:", len(dash.cam_panel.canvas.find_all()))
        print("fps:", round(getattr(pkt, "fps", 0), 1) if pkt else None)
        print("camera pill text:", dash.pill_camera._text)
    except Exception:
        traceback.print_exc()
    finally:
        app.after(300, app.quit)
app.after(4000, step)
app.mainloop()
print("closed ok")
