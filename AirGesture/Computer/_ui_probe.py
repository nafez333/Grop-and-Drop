import traceback
from airgesture.app import AirGestureApp, PAGE_ORDER
app = AirGestureApp()
print("PAGE_ORDER:", PAGE_ORDER)
def step():
    try:
        print("frames pending:", app._frame_pending, "last packet:", app._last_packet)
        for key, label, icon in PAGE_ORDER:
            cls_name = key
            try:
                page = app._pages.get(key)
                print("page", key, "exists?", page is not None)
            except Exception as e:
                print("LOOKUP FAIL", key, e)
    except Exception:
        traceback.print_exc()
    finally:
        app.after(200, app.quit)
app.after(1200, step)
app.mainloop()
