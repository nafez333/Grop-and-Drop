"""Temporary diagnostic: open the real app, then dump every thread's stack."""

import faulthandler
import sys
import threading

from airgesture.app import AirGestureApp

app = AirGestureApp()
faulthandler.dump_traceback_later(5.0, exit=False)
_threads = []


def snap():
    for t in threading.enumerate():
        print("THREAD", t.name, "alive", t.is_alive())


app.after(6000, lambda: (snap(), app.after(100, app.quit)))
app.mainloop()
print(
    "after mainloop; engine running:",
    app.engine.running,
    "frames:",
    app._last_delivered is not None,
)
sys.stdout.flush()
