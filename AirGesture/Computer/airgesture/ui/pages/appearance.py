"""Appearance page: theme, accent colour, UI scale and start-up options."""
from __future__ import annotations

import tkinter as tk

from ..i18n import tr
from ..widgets import Card, SliderField, ToggleRow, Toast, palette_font
from .base import Page


class AppearancePage(Page):
    title = tr("Appearance")
    subtitle = tr("Choose dark/light/system theme, accent colour and UI scale.")

    def build(self) -> None:
        p = self.palette
        f = self.fonts
        s = self.app.settings

        self.toast = Toast(self, self.app.palette)

        # ------------------------------------------------------ theme
        th = Card(self.body, p, title=tr("Theme"), subtitle=tr("Windows system resolves to dark."), padding=16)
        th.pack(fill="x", pady=(0, 12))
        self.theme_var = tk.StringVar(value=str(s.get("general", "appearance", "dark")))
        row = tk.Frame(th.body, bg=p.surface)
        row.pack(fill="x")
        tk.Label(row, text=tr("Appearance"), bg=p.surface, fg=p.text_dim,
                 font=palette_font(self, "small_bold")).pack(side="left")
        from ..widgets import SegmentedControl
        self.theme_ctrl = SegmentedControl(row, p,
            [("dark", tr("Dark")), ("light", tr("Light")), ("system", tr("System"))],
            self.theme_var,
            on_change=self._on_theme)
        self.theme_ctrl.pack(side="left", padx=(10, 0))

        # ------------------------------------------------------ accent
        ac = Card(self.body, p, title=tr("Accent colour"), padding=16)
        ac.pack(fill="x", pady=(0, 12))
        tk.Label(ac.body, text=tr("Pick your accent colour."), bg=p.surface, fg=p.text_dim,
                 font=palette_font(self, "small")).pack(anchor="w", pady=(0, 8))
        self.accent_var = tk.StringVar(value=str(s.get("general", "accent", "violet")))
        swatches = tk.Frame(ac.body, bg=p.surface)
        swatches.pack(fill="x")
        for name in ("violet", "teal", "amber", "rose"):
            sw = tk.Frame(swatches, bg=p.surface_3, cursor="hand2", width=34, height=34)
            sw.pack(side="left", padx=(0, 8))
            sw.pack_propagate(False)
            canvas = tk.Canvas(sw, bg=p.surface_3, highlightthickness=0, bd=0,
                               width=34, height=34)
            canvas.pack()
            canvas.create_oval(4, 4, 30, 30, fill=self._accent_hex(name), outline="")
            canvas.bind("<Button-1>", lambda _e, n=name: self._pick_accent(n))
            sw.bind("<Button-1>", lambda _e, n=name: self._pick_accent(n))

        # ------------------------------------------------------ scale
        sc = Card(self.body, p, title=tr("UI scale"), padding=16)
        sc.pack(fill="x", pady=(0, 12))
        self.scale_var = tk.DoubleVar(value=float(s.get("general", "ui_scale", 1.0)))
        SliderField(sc.body, p, tr("UI scale"), 0.85, 1.25, self.scale_var, "",
                    on_change=lambda v: self._set_num("general", "ui_scale", v),
                    default=1.0).pack(fill="x")

        # ------------------------------------------------------ toggles
        tg = Card(self.body, p, title=tr("Start-up & overlay"), padding=16)
        tg.pack(fill="x", pady=(0, 12))
        self.overlay_var = tk.BooleanVar(value=bool(s.get("general", "show_overlay", True)))
        ToggleRow(tg.body, p, tr("Show tracking overlay in preview"), self.overlay_var,
                  description=tr("Draws the skeleton and active-area rectangle on the camera preview."),
                  on_change=lambda v: self._set_bool("general", "show_overlay")).pack(fill="x", pady=(0, 8))
        self.autostart_var = tk.BooleanVar(value=bool(s.get("general", "auto_start_control", False)))
        ToggleRow(tg.body, p, tr("Start with Windows control active"), self.autostart_var,
                  description=tr("Mouse control turns on automatically when the app launches."),
                  on_change=lambda v: self._set_bool("general", "auto_start_control")).pack(fill="x", pady=(0, 8))
        self.minimized_var = tk.BooleanVar(value=bool(s.get("general", "start_minimized", False)))
        ToggleRow(tg.body, p, tr("Start minimized"), self.minimized_var,
                  description=tr("The window opens iconified on launch."),
                  on_change=lambda v: self._set_bool("general", "start_minimized")).pack(fill="x")

        # ------------------------------------------------------ reset
        rst = tk.Frame(self.body, bg=p.surface_2, cursor="hand2")
        rst.pack(fill="x", pady=(8, 0))
        rlbl = tk.Label(rst, text=tr("Reset appearance"), bg=p.surface_2, fg=p.danger,
                        font=palette_font(self, "small_bold"), padx=14, pady=8)
        rlbl.pack()
        for w in (rst, rlbl):
            w.bind("<Button-1>", lambda _e: self._reset_appearance())

    # -------------------------------------------------------------- helpers
    def _accent_hex(self, name: str) -> str:
        return {"violet": "#7C5CFF", "teal": "#22D3B6", "amber": "#F5A524", "rose": "#FF6B8A"}.get(name, "#7C5CFF")

    def _on_theme(self, value: str) -> None:
        self.app.settings.set("general", "appearance", value)
        self.app.apply_theme()

    def _pick_accent(self, name: str) -> None:
        self.app.settings.set("general", "accent", name)
        self.app.apply_theme()

    def _set_num(self, section: str, key: str, value) -> None:
        self.app.settings.set(section, key, value)
        self.app.apply_theme()

    def _set_bool(self, section: str, key: str) -> None:
        var = getattr(self, f"{key}_var")
        self.app.settings.set(section, key, bool(var.get()))
        self.app.apply_theme()

    def _reset_appearance(self) -> None:
        from ...core.settings import defaults
        d = defaults()["general"]
        self.app.settings.set("general", "appearance", d["appearance"])
        self.app.settings.set("general", "accent", d["accent"])
        self.app.settings.set("general", "ui_scale", d["ui_scale"])
        self.app.settings.set("general", "show_overlay", d["show_overlay"])
        self.app.settings.set("general", "auto_start_control", d["auto_start_control"])
        self.app.settings.set("general", "start_minimized", d["start_minimized"])
        self.theme_var.set(d["appearance"])
        self.accent_var.set(d["accent"])
        self.scale_var.set(d["ui_scale"])
        self.overlay_var.set(d["show_overlay"])
        self.autostart_var.set(d["auto_start_control"])
        self.minimized_var.set(d["start_minimized"])
        self.app.apply_theme()
        self.toast.show("Appearance reset to defaults", "ok")

    def on_show(self) -> None:
        pass
