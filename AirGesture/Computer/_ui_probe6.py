"""Temporary diagnostic: inspect engine state inside the running app."""

import threading

from airgesture.app import AirGestureApp

app = AirGestureApp()


def step():
    e = app.engine
    print("running:", e.running)
    print("packets delivered:", app._last_delivered is not None)
    pkt = e._packet
    print(
        "engine._packet frame:",
        None if pkt is None or pkt.frame is None else pkt.frame.shape,
    )
    print("engine._packet.error:", getattr(pkt, "error", None))
    print(
        "camera open:",
        e.camera.is_open,
        "failures:",
        e.camera.consecutive_failures,
        "err:",
        e.camera.last_error,
    )
    print("status text:", app._status_text, "| last status:", app._last_status)
    print("threads:", [t.name for t in threading.enumerate()])
    app.after(200, app.quit)


app.after(5000, step)
app.mainloop()
