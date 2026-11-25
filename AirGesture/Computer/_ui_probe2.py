import traceback
from airgesture.app import AirGestureApp
app = AirGestureApp()
def step():
    try:
        for name in ("gestures","calibration","mouse","camera","appearance","help","dashboard"):
            try:
                app.show_page(name); app.update()
                print("page ok:", name)
            except Exception as e:
                print("PAGE FAIL:", name, type(e).__name__, e)
                traceback.print_exc()
    except Exception:
        traceback.print_exc()
    finally:
        app.after(300, app.quit)
app.after(1200, step)
app.mainloop()
