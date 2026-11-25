"""Temporary visual QA: screenshot each page of the real running app."""

import os

from PIL import ImageGrab

from airgesture.app import AirGestureApp

OUT = os.path.join(os.path.dirname(__file__), "_shots")
os.makedirs(OUT, exist_ok=True)

app = AirGestureApp()
app.geometry("1280x800+40+40")
app.lift()
pages = [
    "dashboard",
    "gestures",
    "calibration",
    "mouse",
    "camera",
    "appearance",
    "help",
]
state = {"i": 0}


def grab():
    i = state["i"]
    if i >= len(pages):
        app.after(100, app.quit)
        return
    name = pages[i]
    app.show_page(name)
    app.update()
    app.after(900, lambda: shot(name))


def shot(name):
    app.update()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    path = os.path.join(OUT, f"{name}.png")
    img.save(path)
    print("saved", path, img.size)
    state["i"] += 1
    grab()


app.after(6000, grab)
app.mainloop()
print("done; frames delivered:", app._last_delivered is not None)
