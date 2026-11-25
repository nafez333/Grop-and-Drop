"""Calibration wizard: camera check, palm position, active area, sensitivity, practice."""
from __future__ import annotations

import tkinter as tk
from typing import Optional

from ...core.recognizer import OPEN_PALM, GESTURE_LABELS
from ..i18n import tr
from ..widgets import Card, SliderField, ToggleRow, Toast, palette_font
from .base import Page


class CalibrationPage(Page):
    title = tr("Calibration")
    subtitle = tr("Guided setup: camera, hand position, active area and cursor sensitivity.")

    STEPS = ("camera", "position", "area", "sensitivity", "practice")

    def build(self) -> None:
        p = self.palette
        f = self.fonts
        s = self.app.settings

        self.toast = Toast(self, self.app.palette)
        self._step_idx = 0
        self._step = self.STEPS[0]
        self._after_id: Optional[str] = None

        # progress + step label
        top = tk.Frame(self.body, bg=p.bg)
        top.pack(fill="x", pady=(0, 10))
        self.step_lbl = tk.Label(top, text="", bg=p.bg, fg=p.text,
                                 font=palette_font(self, "h2"))
        self.step_lbl.pack(side="left")
        self.sub_lbl = tk.Label(top, text="", bg=p.bg, fg=p.text_dim,
                                font=palette_font(self, "small"))
        self.sub_lbl.pack(side="left", padx=(12, 0), anchor="w")

        # content area
        self.content = tk.Frame(self.body, bg=p.bg)
        self.content.pack(fill="both", expand=True)

        # footer buttons
        self.footer = tk.Frame(self.body, bg=p.bg)
        self.footer.pack(fill="x", pady=(12, 0))

        self.btn_back = tk.Frame(self.footer, bg=p.surface_2, cursor="hand2")
        self.lbl_back = tk.Label(self.btn_back, text=tr("Back"), bg=p.surface_2, fg=p.text_dim,
                                 font=palette_font(self, "body_bold"), padx=14, pady=8)
        self.lbl_back.pack()
        for w in (self.btn_back, self.lbl_back):
            w.bind("<Button-1>", lambda _e: self._prev())

        self.btn_skip = tk.Frame(self.footer, bg=p.surface_2, cursor="hand2")
        self.lbl_skip = tk.Label(self.btn_skip, text=tr("Skip step"), bg=p.surface_2, fg=p.text_dim,
                                 font=palette_font(self, "body_bold"), padx=14, pady=8)
        self.lbl_skip.pack()
        for w in (self.btn_skip, self.lbl_skip):
            w.bind("<Button-1>", lambda _e: self._next())

        self.btn_next = tk.Frame(self.footer, bg=p.accent, cursor="hand2")
        self.lbl_next = tk.Label(self.btn_next, text=tr("Next"), bg=p.accent, fg="#FFFFFF",
                                 font=palette_font(self, "body_bold"), padx=14, pady=8)
        self.lbl_next.pack()
        for w in (self.btn_next, self.lbl_next):
            w.bind("<Button-1>", lambda _e: self._next())

        self._render_step()

    # -------------------------------------------------------------- step render
    def _render_step(self) -> None:
        for c in self.content.winfo_children():
            c.destroy()
        step = self._step
        if step == "camera":
            self._build_camera_step()
        elif step == "position":
            self._build_position_step()
        elif step == "area":
            self._build_area_step()
        elif step == "sensitivity":
            self._build_sensitivity_step()
        elif step == "practice":
            self._build_practice_step()
        self._update_footer()
        self._update_labels()

    def _update_labels(self) -> None:
        i = self.STEPS.index(self._step)
        total = len(self.STEPS)
        names = {
            "camera": tr("Camera check"),
            "position": tr("Hand position"),
            "area": tr("Active area (4 corners)"),
            "sensitivity": tr("Cursor sensitivity"),
            "practice": tr("Practice & finish"),
        }
        self.step_lbl.configure(text=f"{tr('Step')} {i + 1} / {total} — {names[self._step]}")
        hints = {
            "camera": "Checking that the camera is delivering frames…",
            "position": "Hold an open palm in the centre of the view.",
            "area": "Move your hand to each corner, hold for 0.7 s.",
            "sensitivity": "Try the slider and move the cursor.",
            "practice": "Tick the boxes when you can do each action.",
        }
        self.sub_lbl.configure(text=hints[self._step])

    def _update_footer(self) -> None:
        i = self.STEPS.index(self._step)
        self.btn_back.pack_forget()
        self.btn_skip.pack_forget()
        self.btn_next.pack_forget()
        if i > 0:
            self.btn_back.pack(side="left")
        self.btn_skip.pack(side="left", padx=(10, 0))
        last = i == len(self.STEPS) - 1
        self.lbl_next.configure(text=tr("Finish") if last else tr("Next"))
        self.btn_next.pack(side="right")

    # -------------------------------------------------------------- step: camera
    def _build_camera_step(self) -> None:
        p = self.palette
        card = Card(self.content, p, title=tr("Camera check"), padding=20)
        card.pack(fill="x")
        self.cam_status = tk.Label(card.body, text=tr("Waiting for frames…"), bg=p.surface,
                                   fg=p.text, font=palette_font(self, "body"))
        self.cam_status.pack(pady=(0, 8))
        self.cam_ok = tk.Label(card.body, text="", bg=p.surface, fg=p.text_dim,
                               font=palette_font(self, "tiny"))
        self.cam_ok.pack()
        self._check_camera()

    def _check_camera(self) -> None:
        pkt = self.app.engine.latest()
        ok = pkt is not None and pkt.frame is not None and not pkt.error
        if ok:
            self.cam_status.configure(text="Camera is delivering frames.", fg=self.palette.success)
            self.cam_ok.configure(text=f"Gesture: {pkt.gesture_label}  ·  Hand: {pkt.handedness}")
            self._schedule_next(400)
        elif pkt is not None and pkt.error:
            self.cam_status.configure(text=f"Camera error: {pkt.error}", fg=self.palette.danger)
            self._schedule_next(1000)
        else:
            self.cam_status.configure(text="Waiting for camera…", fg=self.palette.warning)
            self._schedule_next(300)

    # -------------------------------------------------------------- step: position
    def _build_position_step(self) -> None:
        p = self.palette
        card = Card(self.content, p, title="Hand position", padding=20)
        card.pack(fill="x")
        tk.Label(card.body, text="Hold your open palm steady in the centre of the camera view.",
                 bg=p.surface, fg=p.text, font=palette_font(self, "body"),
                 wraplength=560, justify="left").pack(anchor="w", pady=(0, 10))
        self.pos_bar = tk.Canvas(card.body, height=10, bg=p.surface_3,
                                 highlightthickness=0, bd=0)
        self.pos_bar.pack(fill="x", pady=(0, 6))
        self.pos_bar.bind("<Configure>", lambda e: self._draw_pos_bar(0.0))
        self.pos_status = tk.Label(card.body, text="Open palm not detected yet.", bg=p.surface,
                                   fg=p.text_dim, font=palette_font(self, "small"))
        self.pos_status.pack()
        self._pos_count = 0
        self._check_position()

    def _draw_pos_bar(self, frac: float) -> None:
        c = self.pos_bar
        c.delete("all")
        w = max(50, c.winfo_width())
        h = 10
        p = self.palette
        from ..widgets import _round_rect
        _round_rect(c, 0, 0, w, h, h / 2, fill=p.track, outline="")
        if frac > 0:
            _round_rect(c, 0, 0, max(h, w * min(1.0, frac)), h, h / 2,
                        fill=p.accent, outline="")

    def _check_position(self) -> None:
        pkt = self.app.engine.latest()
        good = (
            pkt is not None
            and pkt.gesture == OPEN_PALM
            and pkt.palm_xy is not None
            and 0.2 <= pkt.palm_xy[0] <= 0.8
            and 0.2 <= pkt.palm_xy[1] <= 0.8
        )
        if good:
            self._pos_count += 1
        else:
            self._pos_count = max(0, self._pos_count - 1)
        frac = min(1.0, self._pos_count / 25.0)
        self._draw_pos_bar(frac)
        if self._pos_count >= 25:
            self.pos_status.configure(text="Position held — ready to continue.", fg=self.palette.success)
            self._schedule_next(400)
        else:
            self.pos_status.configure(
                text=f"Hold open palm in centre: {self._pos_count}/25 frames",
                fg=self.palette.text_dim,
            )
            self._schedule_next(40)

    # -------------------------------------------------------------- step: area
    def _build_area_step(self) -> None:
        p = self.palette
        card = Card(self.content, p, title="Active area — 4 corners", padding=20)
        card.pack(fill="x")
        tk.Label(card.body, text="Move your hand to each corner, in order. Hold each for 0.7 s.",
                 bg=p.surface, fg=p.text, font=palette_font(self, "body"),
                 wraplength=560, justify="left").pack(anchor="w", pady=(0, 10))
        self.area_idx = 0
        self.area_samples = []
        self.area_corners = [
            ("top-left", 0.20, 0.20),
            ("top-right", 0.80, 0.20),
            ("bottom-right", 0.80, 0.80),
            ("bottom-left", 0.20, 0.80),
        ]
        self.area_status = tk.Label(card.body, text="", bg=p.surface, fg=p.text,
                                    font=palette_font(self, "body_bold"))
        self.area_status.pack(pady=(0, 6))
        self.area_bar = tk.Canvas(card.body, height=10, bg=p.surface_3,
                                  highlightthickness=0, bd=0)
        self.area_bar.pack(fill="x", pady=(0, 6))
        self.area_bar.bind("<Configure>", lambda e: self._draw_area_bar(0.0))
        self.area_captured = tk.Label(card.body, text="", bg=p.surface, fg=p.text_dim,
                                      font=palette_font(self, "tiny"))
        self.area_captured.pack()
        self._area_collecting = False
        self._area_start_t = 0.0
        self._render_area_corner()
        self._tick_area()

    def _render_area_corner(self) -> None:
        name, tx, ty = self.area_corners[self.area_idx]
        self.area_status.configure(
            text=f"Corner {self.area_idx + 1} of 4 — {name}  (target ~{int(tx*100)},{int(ty*100)})"
        )
        self._draw_area_bar(0.0)
        self.area_captured.configure(text="")

    def _draw_area_bar(self, frac: float) -> None:
        c = self.area_bar
        c.delete("all")
        w = max(50, c.winfo_width())
        h = 10
        p = self.palette
        from ..widgets import _round_rect
        _round_rect(c, 0, 0, w, h, h / 2, fill=p.track, outline="")
        if frac > 0:
            _round_rect(c, 0, 0, max(h, w * min(1.0, frac)), h, h / 2,
                        fill=p.accent, outline="")

    def _tick_area(self) -> None:
        pkt = self.app.engine.latest()
        now = __import__("time").time()
        name, tx, ty = self.area_corners[self.area_idx]

        if pkt is not None and pkt.gesture == OPEN_PALM and pkt.palm_xy is not None:
            px, py = pkt.palm_xy
            near = abs(px - tx) < 0.12 and abs(py - ty) < 0.12
            if near and not self._area_collecting:
                self._area_collecting = True
                self._area_start_t = now
                self.area_samples = []
            if self._area_collecting:
                self.area_samples.append((px, py))
                elapsed = now - self._area_start_t
                frac = min(1.0, elapsed / 0.7)
                self._draw_area_bar(frac)
                if elapsed >= 0.7 and len(self.area_samples) >= 10:
                    xs = [p[0] for p in self.area_samples]
                    ys = [p[1] for p in self.area_samples]
                    captured = getattr(self, "area_corners_captured", [])
                    captured.append((sum(xs) / len(xs), sum(ys) / len(ys)))
                    self.area_corners_captured = captured
                    self.area_captured.configure(
                        text=f"{name} captured: avg ({sum(xs)/len(xs):.2f}, {sum(ys)/len(ys):.2f})",
                        fg=self.palette.success,
                    )
                    self._area_collecting = False
                    self._schedule_advance_area(700)
        else:
            self._draw_area_bar(0.0)
            self._area_collecting = False

        self._schedule_next(40)

    def _schedule_advance_area(self, ms: int) -> None:
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
        self._after_id = self.after(ms, self._advance_area)

    def _advance_area(self) -> None:
        captured = getattr(self, "area_corners_captured", [])
        if self.area_idx < 3 and len(captured) > self.area_idx:
            self.area_idx += 1
            self._render_area_corner()
            self._tick_area()
        elif self.area_idx == 3 and len(captured) >= 4:
            self._finish_area()

    def _finish_area(self) -> None:
        captured = self.area_corners_captured
        xs = [c[0] for c in captured]
        ys = [c[1] for c in captured]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        # enforce min span 0.25
        if x1 - x0 < 0.25:
            x1 = min(1.0, x0 + 0.25)
        if y1 - y0 < 0.25:
            y1 = min(1.0, y0 + 0.25)
        # clamp 0..1
        x0 = max(0.0, min(0.45, x0)); x1 = max(0.55, min(1.0, x1))
        y0 = max(0.0, min(0.45, y0)); y1 = max(0.55, min(1.0, y1))
        area = {"x0": round(x0, 3), "y0": round(y0, 3), "x1": round(x1, 3), "y1": round(y1, 3)}
        self.app.settings.set("calibration", "active_area", area)
        self.app.engine.submit("reload")
        self.toast.show(f"Active area saved: {area}", "ok")
        self._schedule_next(400)

    def _restore_default_area(self) -> None:
        area = {"x0": 0.18, "y0": 0.15, "x1": 0.82, "y1": 0.85}
        self.app.settings.set("calibration", "active_area", area)
        self.app.engine.submit("reload")
        self.toast.show("Active area restored to default", "ok")

    # -------------------------------------------------------------- step: sensitivity
    def _build_sensitivity_step(self) -> None:
        p = self.palette
        card = Card(self.content, p, title="Cursor sensitivity", padding=20)
        card.pack(fill="x")
        tk.Label(card.body, text="Slide to try the cursor gain. Higher = farther cursor movement per hand move.",
                 bg=p.surface, fg=p.text, font=palette_font(self, "body"),
                 wraplength=560, justify="left").pack(anchor="w", pady=(0, 12))
        self.sens_var = tk.DoubleVar(value=float(self.app.settings.get("mouse", "sensitivity", 1.35)))
        SliderField(card.body, p, "Sensitivity", 0.5, 2.5, self.sens_var, "",
                    on_change=self._apply_sens_live, default=1.35).pack(fill="x")

    def _apply_sens_live(self, value: float) -> None:
        self.app.settings.set("mouse", "sensitivity", value)
        self.app.engine.submit("reload")

    # -------------------------------------------------------------- step: practice
    def _build_practice_step(self) -> None:
        p = self.palette
        card = Card(self.content, p, title="Practice & finish", padding=20)
        card.pack(fill="x")
        tk.Label(card.body, text="Try each action with your hand, then tick the box.",
                 bg=p.surface, fg=p.text, font=palette_font(self, "body"),
                 wraplength=560, justify="left").pack(anchor="w", pady=(0, 12))

        self.practice_vars = {}
        items = [
            ("moved", "I moved the cursor with an open palm."),
            ("clicked", "I left-clicked with a pinch."),
            ("right_clicked", "I right-clicked with two fingers."),
        ]
        for key, text in items:
            var = tk.BooleanVar(value=False)
            self.practice_vars[key] = var
            ToggleRow(card.body, p, text, var,
                      on_change=lambda v, k=key: self._practice_ticked(k))

        btn_restore = tk.Frame(card.body, bg=p.surface_2, cursor="hand2")
        btn_restore.pack(fill="x", pady=(12, 0))
        rlbl = tk.Label(btn_restore, text="Restore default active area", bg=p.surface_2, fg=p.text_dim,
                        font=palette_font(self, "small_bold"), padx=14, pady=8)
        rlbl.pack()
        for w in (btn_restore, rlbl):
            w.bind("<Button-1>", lambda _e: self._restore_default_area())

    def _practice_ticked(self, key: str) -> None:
        pass  # state is in the vars; finish reads them

    # -------------------------------------------------------------- navigation
    def _schedule_next(self, ms: int) -> None:
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
        self._after_id = self.after(ms, self._tick_current)

    def _tick_current(self) -> None:
        self._after_id = None
        step = self._step
        if step == "camera":
            self._check_camera()
        elif step == "position":
            self._check_position()
        elif step == "area":
            self._tick_area()

    def _next(self) -> None:
        i = self.STEPS.index(self._step)
        if i < len(self.STEPS) - 1:
            self._step = self.STEPS[i + 1]
            self._render_step()
        else:
            self._finish()

    def _prev(self) -> None:
        i = self.STEPS.index(self._step)
        if i > 0:
            self._step = self.STEPS[i - 1]
            self._render_step()

    def _finish(self) -> None:
        all_ok = all(var.get() for var in self.practice_vars.values())
        if not all_ok:
            self.toast.show("Please complete all practice items before finishing.", "warn")
            return
        self.app.settings.set("calibration", "completed", True)
        self.app.engine.submit("reload")
        self.toast.show("Calibration completed and saved.", "ok")
        # show completion card
        for c in self.content.winfo_children():
            c.destroy()
        p = self.palette
        card = Card(self.content, p, title="Calibration complete", padding=24)
        card.pack(fill="both", expand=True)
        tk.Label(card.body, text="Your active area and sensitivity are saved.",
                 bg=p.surface, fg=p.success, font=palette_font(self, "h2")).pack(pady=(0, 8))
        tk.Label(card.body, text="You can now use hand gestures to control the mouse.",
                 bg=p.surface, fg=p.text_dim, font=palette_font(self, "body")).pack()
        self._update_footer()

    def on_show(self) -> None:
        self._render_step()
