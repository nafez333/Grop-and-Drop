import traceback
from airgesture.app import AirGestureApp
app = AirGestureApp()
counts = {"pump": 0}
def pump():
    counts["pump"] += 1
    pkt = app._last_packet
    try:
        app._pages["dashboard"].on_frame(pkt)
    except Exception:
        traceback.print_exc()
    if counts["pump"] < 400:
        app.after(33, pump)
app.after(500, pump)
def step():
    dash = app._pages["dashboard"]
    print("pump calls:", counts["pump"])
    print("last_packet:", type(app._last_packet).__name__)
    print("engine.latest frame:", None if app.engine is None or app.engine.latest().frame is None else "ok")
    print("cam packet frame:", None if dash.cam_panel._packet is None or dash.cam_panel._packet.frame is None else dash.cam_panel._packet.frame.shape)
    app.after(200, app.quit)
app.after(4000, step)
app.mainloop()
