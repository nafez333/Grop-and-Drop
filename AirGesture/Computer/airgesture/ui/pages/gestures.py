"""Gesture configuration: bind actions, enable/disable, tune timing, learn poses.

The "Learn" flow is real: the engine collects ~1.5 s of live hand poses for
the selected gesture, we analyse how consistently that pose is recognised,
show the measured confidence and only save it after the user confirms.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ...core.recognizer import ACTIONS, ACTION_LABELS, GESTURES, GESTURE_HINTS, GESTURE_LABELS
from ...core.recognizer import GestureRecognizer
from ..i18n import tr
from ..widgets import Card, GestureGlyph, SliderField, Switch, Toast, palette_font
from .base import Page


class GesturesPage(Page):
    title = tr("Gestures")
    subtitle = tr("Bind comfortable hand poses to actions and tune how easily they trigger.")

    def build(self):
        p = self.palette
        header = tk.Frame(self.body, bg=p.bg)
        header.pack(fill="x", pady=(0, 10))
        tk.Label(header, text=tr("Gesture profile"), bg=p.bg, fg=p.text_dim,
                 font=self.fonts["small"]).pack(side="left")
        self._button(header, tr("Restore defaults"), "settings", self._reset,
                     variant="surface").pack(side="right")
        self._button(header, tr("Learning guide"), "help",
                     lambda: self.app.show_page("help")).pack(side="right", padx=(0, 8))

        self.list_frame = self.scroll_page()
        self.toast = Toast(self)
        self._rows: dict[str, dict] = {}
        self._build_rows()

    # ---------------------------------------------------------------- helpers
    def _button(self, parent, text, icon, command, variant="ghost"):
        from ..icons import draw_icon

        p = self.palette
        bg = p.accent if variant == "accent" else p.surface_2
        fg = "#FFFFFF" if variant == "accent" else p.text
        f = tk.Frame(parent, bg=bg, cursor="hand2")
        cv = tk.Canvas(f, width=14, height=14, bg=bg, highlightthickness=0, bd=0)
        cv.pack(side="left", padx=(10, 6), pady=7)
        draw_icon(cv, icon, 7, 7, 11, fg)
        lbl = tk.Label(f, text=text, bg=bg, fg=fg, font=palette_font(self, "small_bold"))
        lbl.pack(side="left", padx=(0, 12), pady=6)
        for w in (f, cv, lbl):
            w.bind("<Button-1>", lambda _e: command())
        return f

    def _build_rows(self):
        p = self.palette
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._rows = {}
        gestures = self.app.settings.section("gestures")
        for gid in GESTURES:
            cfg = gestures.get(gid, {})
            self._build_row(gid, cfg)

    def _build_row(self, gid: str, cfg: dict):
        p = self.palette
        card = Card(self.list_frame, p, padding=14)
        card.pack(fill="x", pady=(0, 10))
        body = card.body

        head = tk.Frame(body, bg=p.surface)
        head.pack(fill="x")
        glyph = GestureGlyph(head, p, gid, size=64)
        glyph.pack(side="left")
        texts = tk.Frame(head, bg=p.surface)
        texts.pack(side="left", fill="x", expand=True, padx=(12, 0))
        tk.Label(texts, text=tr(GESTURE_LABELS[gid]), bg=p.surface, fg=p.text,
                 font=palette_font(self, "body_bold")).pack(anchor="w")
        tk.Label(texts, text=tr(GESTURE_HINTS.get(gid, "")), bg=p.surface, fg=p.text_mute,
                 font=palette_font(self, "tiny"), wraplength=560, justify="left").pack(anchor="w")

        enabled_var = tk.BooleanVar(value=bool(cfg.get("enabled", False)))
        Switch(head, p, enabled_var, command=lambda v: self._toggle(gid, v)).pack(
            side="right", padx=(10, 0))

        controls = tk.Frame(body, bg=p.surface)
        controls.pack(fill="x", pady=(12, 0))
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)

        action_var = tk.StringVar(value=cfg.get("action", "none"))
        left = tk.Frame(controls, bg=p.surface)
        left.grid(row=0, column=0, sticky="w")
        tk.Label(left, text=tr("Action"), bg=p.surface, fg=p.text_dim,
                 font=palette_font(self, "small_bold")).pack(anchor="w")
        combo = ttk.Combobox(left, state="readonly", width=22,
                             values=[tr(ACTION_LABELS[a]) for a in ACTIONS],
                             font=self.fonts["body"])
        combo.set(tr(ACTION_LABELS.get(cfg.get("action", "none"), "Do nothing")))
        combo.pack(anchor="w", pady=(4, 0))
        combo.bind("<<ComboboxSelected>>", lambda _e: self._set_action(gid, combo.get()))

        right = tk.Frame(controls, bg=p.surface)
        right.grid(row=0, column=1, sticky="e")
        btn_ok = tk.Frame(right, bg=p.accent, cursor="hand2")
        btn_ok.pack(side="left")
        lbl = tk.Label(btn_ok, text=tr("Learn comfortable pose"), bg=p.accent, fg="#FFFFFF",
                       font=palette_font(self, "small_bold"))
        lbl.pack(padx=12, pady=6)
        for w in (btn_ok, lbl):
            w.bind("<Button-1>", lambda _e: self._start_learning(gid))

        sliders = tk.Frame(body, bg=p.surface)
        sliders.pack(fill="x", pady=(10, 0))
        sliders.columnconfigure(0, weight=1)
        sliders.columnconfigure(1, weight=1)
        sliders.columnconfigure(2, weight=1)

        sens_var = tk.DoubleVar(value=float(cfg.get("sensitivity", 0.5)))
        delay_var = tk.DoubleVar(value=float(cfg.get("activation_delay", 0.12)))
        cool_var = tk.DoubleVar(value=float(cfg.get("cooldown", 0.45)))

        def commit():
            self.app.settings.update_gesture(
                gid, sensitivity=sens_var.get(), activation_delay=delay_var.get(),
                cooldown=cool_var.get(),
            )

        SliderField(sliders, p, tr("Sensitivity"), 0.0, 1.0, sens_var,
                    on_change=lambda v: self.app.settings.update_gesture(gid, sensitivity=v),
                    default=0.5).grid(row=0, column=0, sticky="ew", padx=(0, 10))
        SliderField(sliders, p, tr("Activation delay"), 0.0, 0.8, delay_var, unit=" s", decimals=2,
                    on_change=lambda v: self.app.settings.update_gesture(gid, activation_delay=v),
                    default=0.12).grid(row=0, column=1, sticky="ew", padx=(0, 10))
        SliderField(sliders, p, tr("Cooldown"), 0.05, 2.5, cool_var, unit=" s", decimals=2,
                    on_change=lambda v: self.app.settings.update_gesture(gid, cooldown=v),
                    default=0.45).grid(row=0, column=2, sticky="ew")

        self._rows[gid] = {"enabled": enabled_var}

    # ---------------------------------------------------------------- actions
    def _toggle(self, gid, value):
        self.app.settings.update_gesture(gid, enabled=value)
        self.app.refresh_pages("gestures", gid)
        self.toast.show(f"{GESTURE_LABELS[gid]} {'enabled' if value else 'disabled'}", "ok")

    def _set_action(self, gid, label):
        reverse = {tr(v): k for k, v in ACTION_LABELS.items()}
        reverse.update({v: k for k, v in ACTION_LABELS.items()})
        action = reverse.get(label, "none")
        self.app.settings.update_gesture(gid, action=action)
        self.app.refresh_pages("gestures", gid)
        self.toast.show(f"{tr(GESTURE_LABELS[gid])} → {label}", "info")

    def _reset(self):
        self.app.settings.reset_gestures()
        self._build_rows()
        self.app.refresh_pages("gestures", "*")
        self.toast.show("Gesture profile restored to defaults", "ok")

    # -------------------------------------------------------------- learning
    def _start_learning(self, gid):
        self.app.open_learning(gid, self._on_learned)

    def _on_learned(self, gid: str, confidence: float):
        if confidence is None:
            return
        current = self.app.settings.gesture(gid).get("learned_confidence", 1.0)
        blended = round(min(1.0, max(0.35, 0.6 * confidence + 0.4 * current)), 2)
        self.app.settings.update_gesture(gid, learned_confidence=blended)
        self.app.refresh_pages("gestures", gid)
        self.toast.show(
            f"{GESTURE_LABELS.get(gid, gid)} calibrated · recognition confidence {int(blended * 100)}%",
            "ok", 4000,
        )

    def on_show(self):
        self._build_rows()
