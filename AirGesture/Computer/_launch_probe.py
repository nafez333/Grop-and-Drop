import traceback, threading, time
try:
    from airgesture.app import AirGestureApp
    app = AirGestureApp()
    errors = []
    app.report_callback_exception = lambda *a: errors.append(a)
    def probe():
        try:
            print("pages:", list(getattr(app, "pages", {}).keys()))
            for name in list(getattr(app, "pages", {}).keys()):
                try:
                    app.show_page(name)
                    app.update()
                    print("  page ok:", name)
                except Exception as e:
                    print("  PAGE FAIL", name, type(e).__name__, e)
                    traceback.print_exc()
            time.sleep(1.5)
            app.update()
            pkt = app.engine.latest() if getattr(app, "engine", None) else None
            print("engine running:", getattr(getattr(app, "engine", None), "running", None))
            if pkt: print("frame:", None if pkt.frame is None else pkt.frame.shape, "gesture:", pkt.gesture, "err:", pkt.error)
            print("callback errors:", len(errors))
            for e in errors[:5]: print("  CB:", e[0], e[1])
        except Exception:
            traceback.print_exc()
        finally:
            try: app._on_close()
            except Exception: pass
            app.after(100, app.quit)
    app.after(1500, probe)
    app.mainloop()
    print("EXITED CLEANLY")
except Exception:
    traceback.print_exc()
