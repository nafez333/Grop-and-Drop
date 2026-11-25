"""Mouse settings page: cursor mapping, smoothing, deadzone and live test."""
from __future__ import annotations

import tkinter as tk
from typing import Optional

from ...core.settings import defaults
from ..i18n import tr
from ..widgets import Card, SliderField, StatusPill, ToggleRow, Toast, palette_font
from .base import Page


class MouseSettingsPage(Page):
    title = tr("Mouse")
    subtitle = tr("Tune cursor movement, smoothing and safety guards. Test live with your own mouse.")

    def build(self) -> None:
        p = self.palette
        f = self.fonts
        s = self.app.settings

        self.toast = Toast(self, self.app.palette)

        card = Card(self.body, p, title=tr("Cursor movement"), subtitle=tr("Live-mapped settings."))
        card.pack(fill="x", pady=(0, 12))

        def commit(_v=None) -> None:
            self.app.engine.submit("reload")
            self.toast.show("Mouse settings updated", "info")

        def on_slider(section: str, key: str):
            def handler(value: float) -> None:
                s.set(section, key, value)
                self._schedule_commit()
            return handler

        def _schedule_commit(self_self=None) -> None:
            if self._commit_after is not None:
                try:
                    self.after_cancel(self._commit_after)
                except tk.TclError:
                    pass
            self._commit_after = self.after(400, lambda: self._do_commit())

        def _do_commit() -> None:
            self._commit_after = None
            self.app.engine.submit("reload")
            self.toast.show("Mouse settings applied", "info")

        self._commit_after: Optional[str] = None

        self.sens_var = tk.DoubleVar(value=float(s.get("mouse", "sensitivity", 1.35)))
        self.speed_var = tk.DoubleVar(value=float(s.get("mouse", "speed", 1.0)))
        self.smooth_var = tk.DoubleVar(value=float(s.get("mouse", "smoothing", 0.45)))
        self.accel_var = tk.DoubleVar(value=float(s.get("mouse", "acceleration", 0.35)))
        self.ax_var = tk.DoubleVar(value=float(s.get("mouse", "active_area_x", 0.62)))
        self.ay_var = tk.DoubleVar(value=float(s.get("mouse", "active_area_y", 0.58)))
        self.dz_var = tk.DoubleVar(value=float(s.get("mouse", "deadzone", 0.004)))
        self.jg_var = tk.DoubleVar(value=float(s.get("mouse", "jump_guard", 0.14)))
        self.scroll_var = tk.DoubleVar(value=float(s.get("mouse", "scroll_speed", 1.0)))

        self._slider(card.body, tr("Sensitivity"), 0.3, 3.5, self.sens_var, "",
                     on_slider("mouse", "sensitivity"), default=1.35)
        self._slider(card.body, tr("Speed"), 0.2, 3.0, self.speed_var, "",
                     on_slider("mouse", "speed"), default=1.0)
        self._slider(card.body, tr("Smoothing"), 0.0, 0.95, self.smooth_var, "",
                     on_slider("mouse", "smoothing"), default=0.45)
        self._slider(card.body, tr("Acceleration"), 0.0, 1.0, self.accel_var, "",
                     on_slider("mouse", "acceleration"), default=0.35)
        self._slider(card.body, tr("Active area width"), 0.2, 0.95, self.ax_var, "",
                     on_slider("mouse", "active_area_x"), default=0.62)
        self._slider(card.body, tr("Active area height"), 0.2, 0.95, self.ay_var, "",
                     on_slider("mouse", "active_area_y"), default=0.58)
        self._slider(card.body, tr("Deadzone"), 0.0, 0.03, self.dz_var, "%",
                     on_slider("mouse", "deadzone"), default=0.004)
        self._slider(card.body, tr("Jump guard"), 0.02, 0.4, self.jg_var, "",
                     on_slider("mouse", "jump_guard"), default=0.14)
        self._slider(card.body, tr("Scroll speed"), 0.2, 4.0, self.scroll_var, "",
                     on_slider("mouse", "scroll_speed"), default=1.0)

        self.nat_var = tk.BooleanVar(value=bool(s.get("mouse", "natural_scroll", True)))
        ToggleRow(card.body, p, tr("Natural scroll"), self.nat_var,
                  description=tr("Wheel moves content in the same direction as your hand."),
                  on_change=lambda v: self._toggle_bool("mouse", "natural_scroll")).pack(
            fill="x", pady=(10, 0)
        )

        pm_row = tk.Frame(card.body, bg=p.surface)
        pm_row.pack(fill="x", pady=(10, 0))
        tk.Label(pm_row, text=tr("Position mode"), bg=p.surface, fg=p.text_dim,
                 font=palette_font(self, "small_bold")).pack(side="left")
        self.pm_var = tk.StringVar(value=str(s.get("mouse", "position_mode", "absolute")))
        from ..widgets import SegmentedControl
        self.pm_ctrl = SegmentedControl(pm_row, p,
                                        [("absolute", tr("Absolute")), ("relative", tr("Relative"))],
                                        self.pm_var,
                                        on_change=lambda v: self._set_string("mouse", "position_mode", v))
        self.pm_ctrl.pack(side="left", padx=(10, 0))

        reset = tk.Frame(card.body, bg=p.surface_2, cursor="hand2")
        reset.pack(fill="x", pady=(12, 0))
        rlbl = tk.Label(reset, text=tr("Reset mouse settings"), bg=p.surface_2, fg=p.danger,
                        font=palette_font(self, "small_bold"), padx=14, pady=8)
        rlbl.pack()
        for w in (reset, rlbl):
            w.bind("<Button-1>", lambda _e: self._reset_mouse())

        # ------------------------------------------------------- live test card
        test = Card(self.body, p, title=tr("Live test"), subtitle=tr("Marker shows where your palm maps on screen."), padding=14)
        test.pack(fill="both", expand=True)

        self.test_canvas = tk.Canvas(test.body, bg=p.surface_2, highlightthickness=0, bd=0,
                                     width=340, height=260)
        self.test_canvas.pack(fill="both", expand=True, padx=2, pady=2)

        self.btn_click = tk.Frame(test.body, bg=p.accent, cursor="hand2")
        self.btn_click.pack(fill="x", pady=(10, 0))
        clbl = tk.Label(self.btn_click, text=tr("» Test centre click"), bg=p.accent, fg="#FFFFFF",
                        font=palette_font(self, "body_bold"), padx=14, pady=8)
        clbl.pack()
        for w in (self.btn_click, clbl):
            w.bind("<Button-1>", lambda _e: self._test_click())

        desc = tk.Label(test.body, text=tr("WARNING: this really clicks the left mouse button at the centre of your screen."),
                        bg=p.surface, fg=p.text_mute, font=palette_font(self, "tiny"),
                        wraplength=320, justify="center")
        desc.pack(pady=(6, 0))

        self.screen_info = tk.Label(test.body, text="", bg=p.surface, fg=p.text_dim,
                                    font=palette_font(self, "tiny"))
        self.screen_info.pack(pady=(4, 0))
        self._refresh_screen_info()

        self._last_palm = (0.5, 0.5)

    # -------------------------------------------------------------- helpers
    def _slider(self, parent, label, f, t, var, unit, on_change, default):
        SliderField(parent, self.palette, label, f, t, var, unit=unit, decimals=2,
                    on_change=on_change, default=default).pack(fill="x", pady=(0, 8))

    def _toggle_bool(self, section: str, key: str) -> None:
        var = getattr(self, f"{key}_var")
        self.app.settings.set(section, key, bool(var.get()))
        self._schedule_commit()

    def _set_string(self, section: str, key: str, value: str) -> None:
        self.app.settings.set(section, key, value)
        self._schedule_commit()

    def _refresh_screen_info(self) -> None:
        try:
            sw, sh = self.app.mouse.screen_w, self.app.mouse.screen_h
            self.screen_info.configure(
                text=f"Detected screen: {sw} × {sh}  (centre click will fire at {sw // 2}, {sh // 2})"
            )
        except Exception:
            self.screen_info.configure(text=tr("Screen size unavailable."))

    # -------------------------------------------------------------- actions
    def _schedule_commit(self) -> None:
        if self._commit_after is not None:
            try:
                self.after_cancel(self._commit_after)
            except tk.TclError:
                pass
        self._commit_after = self.after(400, self._do_commit)

    def _do_commit(self) -> None:
        self._commit_after = None
        self.app.engine.submit("reload")

    def _reset_mouse(self) -> None:
        d = defaults()["mouse"]
        for key, val in d.items():
            self.app.settings.set("mouse", key, val)
        self.sens_var.set(d["sensitivity"])
        self.speed_var.set(d["speed"])
        self.smooth_var.set(d["smoothing"])
        self.accel_var.set(d["acceleration"])
        self.ax_var.set(d["active_area_x"])
        self.ay_var.set(d["active_area_y"])
        self.dz_var.set(d["deadzone"])
        self.jg_var.set(d["jump_guard"])
        self.scroll_var.set(d["scroll_speed"])
        self.nat_var.set(d["natural_scroll"])
        self.pm_var.set(d["position_mode"])
        self.app.engine.submit("reload")
        self.toast.show("Mouse settings reset to defaults", "ok")

    def _test_click(self) -> None:
        try:
            self.app.mouse.click("left")
            self.toast.show("Centre click sent (left button)", "ok")
        except Exception as exc:  # pragma: no cover - defensive
            self.toast.show(f"Click failed: {exc}", "error")

    # -------------------------------------------------------------- lifecycle
    def on_frame(self, packet) -> None:
        if packet is None or packet.palm_xy is None:
            return
        nx, ny = packet.palm_xy
        self._last_palm = (nx, ny)
        self._redraw_marker()

    def _redraw_marker(self) -> None:
        c = self.test_canvas
        c.delete("marker")
        w = max(100, c.winfo_width())
        h = max(100, c.winfo_height())
        nx, ny = self._last_palm
        sx, sy = self.app.mouse.map_to_screen(nx, ny)
        cx = clamp(sx / max(1, self.app.mouse.screen_w), 0.0, 1.0)
        cy = clamp(sy / max(1, self.app.mouse.screen_h), 0.0, 1.0)
        px, py = cx * w, cy * h
        r = 9
        p = self.palette
        c.create_oval(px - r, py - r, px + r, py + r, fill=p.accent, outline="#FFFFFF",
                      width=2, tags="marker")
        c.create_text(px, py - r - 8, text="»", fill=p.accent, anchor="s",
                      font=palette_font(self, "tiny"), tags="marker")

    def on_show(self) -> None:
        self._refresh_screen_info()
        self._redraw_marker()


def clamp(value: float, low: float, high: float) -> float:
    return low if value < low else high if value > high else value
