"""Camera settings page: device, resolution, FPS, mirror, confidence and handedness."""
from __future__ import annotations

import tkinter as tk
import threading
from typing import Optional

from ..i18n import tr
from ..widgets import Card, SliderField, StatusPill, ToggleRow, Toast, palette_font
from .base import Page


class CameraSettingsPage(Page):
    title = tr("Camera")
    subtitle = tr("Choose your webcam, resolution and detection sensitivity.")

    def build(self) -> None:
        p = self.palette
        f = self.fonts
        s = self.app.settings

        self.toast = Toast(self, self.app.palette)
        self._probe_job: Optional[str] = None

        # ------------------------------------------------------ device card
        dev = Card(self.body, p, title=tr("Device & resolution"), subtitle=tr("Pick the camera and frame size."))
        dev.pack(fill="x", pady=(0, 12))

        row1 = tk.Frame(dev.body, bg=p.surface)
        row1.pack(fill="x", pady=(0, 8))
        tk.Label(row1, text=tr("Camera"), bg=p.surface, fg=p.text_dim,
                 font=palette_font(self, "small_bold")).pack(side="left")
        self.cam_var = tk.StringVar(value=str(s.get("camera", "index", 0)))
        self.cam_combo = tk.OptionMenu(row1, self.cam_var, "Camera 0")
        self.cam_combo.configure(bg=p.surface_3, fg=p.text, highlightthickness=0, bd=0,
                                 font=f["body"])
        self.cam_combo.pack(side="left", padx=(10, 0))

        btn_probe = tk.Frame(dev.body, bg=p.accent, cursor="hand2")
        btn_probe.pack(fill="x", pady=(0, 8))
        plbl = tk.Label(btn_probe, text=tr("Refresh camera list"), bg=p.accent, fg="#FFFFFF",
                        font=palette_font(self, "small_bold"), padx=12, pady=6)
        plbl.pack()
        for w in (btn_probe, plbl):
            w.bind("<Button-1>", lambda _e: self._probe_cameras())

        row2 = tk.Frame(dev.body, bg=p.surface)
        row2.pack(fill="x", pady=(0, 8))
        tk.Label(row2, text=tr("Resolution"), bg=p.surface, fg=p.text_dim,
                 font=palette_font(self, "small_bold")).pack(side="left")
        self.res_var = tk.StringVar(value=f"{s.get('camera','width',1280)}x{s.get('camera','height',720)}")
        self.res_combo = tk.OptionMenu(row2, self.res_var,
                                       "640x480", "1280x720", "1920x1080")
        self.res_combo.configure(bg=p.surface_3, fg=p.text, highlightthickness=0, bd=0,
                                 font=f["body"])
        self.res_combo.pack(side="left", padx=(10, 0))

        row3 = tk.Frame(dev.body, bg=p.surface)
        row3.pack(fill="x")
        tk.Label(row3, text=tr("FPS"), bg=p.surface, fg=p.text_dim,
                 font=palette_font(self, "small_bold")).pack(side="left")
        self.fps_var = tk.DoubleVar(value=float(s.get("camera", "fps", 30)))
        SliderField(dev.body, p, tr("FPS"), 10, 60, self.fps_var, "",
                    on_change=lambda v: self._set_num("camera", "fps", int(v)),
                    default=30).pack(fill="x", pady=(6, 0))

        # ------------------------------------------------------ detection card
        det = Card(self.body, p, title=tr("Detection & handedness"), subtitle=tr("MediaPipe confidence and hand filter."))
        det.pack(fill="x", pady=(0, 12))

        self.det_var = tk.DoubleVar(value=float(s.get("camera", "detection_confidence", 0.6)))
        self.trk_var = tk.DoubleVar(value=float(s.get("camera", "tracking_confidence", 0.6)))
        SliderField(det.body, p, tr("Detection confidence"), 0.2, 0.95, self.det_var, "",
                    on_change=lambda v: self._set_num("camera", "detection_confidence", v),
                    default=0.6).pack(fill="x", pady=(0, 8))
        SliderField(det.body, p, tr("Tracking confidence"), 0.2, 0.95, self.trk_var, "",
                    on_change=lambda v: self._set_num("camera", "tracking_confidence", v),
                    default=0.6).pack(fill="x", pady=(0, 8))

        self.mirror_var = tk.BooleanVar(value=bool(s.get("camera", "mirror", True)))
        ToggleRow(det.body, p, tr("Mirror preview"), self.mirror_var,
                  description=tr("Flip the camera image horizontally (matches a mirror)."),
                  on_change=lambda v: self._set_bool("camera", "mirror")).pack(fill="x", pady=(10, 0))

        hand_row = tk.Frame(det.body, bg=p.surface)
        hand_row.pack(fill="x", pady=(10, 0))
        tk.Label(hand_row, text=tr("Handedness"), bg=p.surface, fg=p.text_dim,
                 font=palette_font(self, "small_bold")).pack(side="left")
        self.hand_var = tk.StringVar(value=str(s.get("tracking", "handedness", "any")))
        from ..widgets import SegmentedControl
        self.hand_ctrl = SegmentedControl(hand_row, p,
                                          [("any", tr("Any")), ("left", tr("Left")), ("right", tr("Right"))],
                                          self.hand_var,
                                          on_change=lambda v: self._set_string("tracking", "handedness", v))
        self.hand_ctrl.pack(side="left", padx=(10, 0))

        # ------------------------------------------------------ actions
        act = Card(self.body, p, title=tr("Apply & test"), subtitle=tr("Changes take effect after Apply."))
        act.pack(fill="x", pady=(0, 12))

        btn_apply = tk.Frame(act.body, bg=p.accent, cursor="hand2")
        btn_apply.pack(fill="x", pady=(0, 8))
        albl = tk.Label(btn_apply, text=tr("Apply & restart camera"), bg=p.accent, fg="#FFFFFF",
                        font=palette_font(self, "body_bold"), padx=14, pady=8)
        albl.pack()
        for w in (btn_apply, albl):
            w.bind("<Button-1>", lambda _e: self._apply())

        btn_test = tk.Frame(act.body, bg=p.surface_2, cursor="hand2")
        btn_test.pack(fill="x")
        tlbl = tk.Label(btn_test, text=tr("Test camera (1 s preview)"), bg=p.surface_2, fg=p.text,
                        font=palette_font(self, "body_bold"), padx=14, pady=8)
        tlbl.pack()
        for w in (btn_test, tlbl):
            w.bind("<Button-1>", lambda _e: self._test_camera())

        self.status_lbl = tk.Label(act.body, text="", bg=p.surface, fg=p.text_dim,
                                   font=palette_font(self, "tiny"), wraplength=560,
                                   justify="left")
        self.status_lbl.pack(pady=(8, 0))

        self._probe_cameras()

    # -------------------------------------------------------------- helpers
    def _set_num(self, section: str, key: str, value) -> None:
        self.app.settings.set(section, key, value)

    def _set_bool(self, section: str, key: str) -> None:
        var = getattr(self, f"{key}_var")
        self.app.settings.set(section, key, bool(var.get()))

    def _set_string(self, section: str, key: str, value: str) -> None:
        self.app.settings.set(section, key, value)

    def _probe_cameras(self) -> None:
        if self._probe_job is not None:
            try:
                self.after_cancel(self._probe_job)
            except tk.TclError:
                pass
        self.status_lbl.configure(text="Scanning cameras…", fg=self.palette.text_dim)

        def work() -> None:
            found = []
            try:
                from ...runtime.camera_manager import CameraManager
                found = CameraManager.probe()
            except Exception as exc:  # pragma: no cover
                found = [0]

            def update_ui():
                try:
                    menu = self.cam_combo["menu"]
                    menu.delete(0, "end")
                    for idx in found:
                        label = f"Camera {idx}"
                        menu.add_command(label=label,
                                         command=lambda i=idx: self.cam_var.set(str(i)))
                    if found:
                        self.cam_var.set(str(found[0]))
                    self.status_lbl.configure(
                        text=f"Found {len(found)} camera(s).", fg=self.palette.text_mute)
                except Exception:
                    pass

            self.after(0, update_ui)

        self._probe_job = self.after(50, lambda: threading.Thread(target=work, daemon=True).start())

    def _apply(self) -> None:
        try:
            w, h = self.res_var.get().split("x")
            self.app.settings.set("camera", "index", int(self.cam_var.get()))
            self.app.settings.set("camera", "width", int(w))
            self.app.settings.set("camera", "height", int(h))
            self.app.settings.set("camera", "fps", int(self.fps_var.get()))
            self.app.settings.set("tracking", "handedness", self.hand_var.get())
            self.app.settings.set("camera", "detection_confidence", self.det_var.get())
            self.app.settings.set("camera", "tracking_confidence", self.trk_var.get())
            self.app.settings.set("camera", "mirror", bool(self.mirror_var.get()))
        except Exception as exc:  # pragma: no cover - defensive
            self.toast.show(f"Apply failed: {exc}", "error")
            return
        self.app.restart_engine()
        self.toast.show("Camera restarted with new settings", "ok")

    def _test_camera(self) -> None:
        from ...runtime.camera_manager import CameraManager
        cam = CameraManager()
        ok = cam.open(
            int(self.cam_var.get()),
            int(self.res_var.get().split("x")[0]),
            int(self.res_var.get().split("x")[1]),
            int(self.fps_var.get()),
        )
        if not ok:
            self.toast.show(f"Camera test failed: {cam.last_error}", "error")
            return
        import time as _t
        frame = cam.read_frame()
        cam.close()
        if frame is None:
            self.toast.show("Camera opened but no frame received.", "error")
        else:
            self.toast.show("Camera test OK — frame received.", "ok")

    def on_show(self) -> None:
        if self.app.camera.last_error:
            self.status_lbl.configure(text=self.app.camera.last_error, fg=self.palette.danger)
        else:
            self.status_lbl.configure(text="", fg=self.palette.text_mute)
