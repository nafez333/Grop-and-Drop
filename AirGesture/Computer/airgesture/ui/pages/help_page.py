"""Help page: getting started, gesture table, safety, troubleshooting."""
from __future__ import annotations

import os
import tkinter as tk
from typing import Optional

from ...core.recognizer import ACTIONS, ACTION_LABELS, GESTURES, GESTURE_HINTS, GESTURE_LABELS
from ..i18n import tr
from ..widgets import Card, GestureGlyph, Toast, palette_font
from .base import Page


class HelpPage(Page):
    title = tr("Help")
    subtitle = tr("Getting started, gesture reference, safety and troubleshooting.")

    def build(self) -> None:
        p = self.palette
        f = self.fonts
        s = self.app.settings

        self.toast = Toast(self, self.app.palette)

        # Getting started
        gs = Card(self.body, p, title=tr("Getting started"), padding=16)
        gs.pack(fill="x", pady=(0, 10))
        steps = [
            tr("Launch AirGesture: open the Computer folder and run `python main.py`."),
            tr("Complete the Calibration wizard (open palm → corners → sensitivity)."),
            tr("Go to Dashboard and click Start control (or press F9)."),
            tr("Show an open palm to move the cursor; pinch to left-click."),
            tr("Press Esc at any time for emergency stop."),
        ]
        for i, step in enumerate(steps, 1):
            row = tk.Frame(gs.body, bg=p.surface)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=str(i), bg=p.surface, fg=p.accent,
                     font=palette_font(self, "body_bold"), width=2).pack(side="left")
            tk.Label(row, text=step, bg=p.surface, fg=p.text,
                     font=palette_font(self, "body"), wraplength=620,
                     justify="left").pack(side="left", padx=(8, 0))

        # Your gestures table
        gt = Card(self.body, p, title=tr("Your gestures"), padding=16)
        gt.pack(fill="x", pady=(0, 10))
        tk.Label(gt.body, text=tr("Enabled gestures and their bound actions (from current settings):"),
                 bg=p.surface, fg=p.text_dim, font=palette_font(self, "small")).pack(anchor="w", pady=(0, 8))
        gestures = s.section("gestures")
        for gid in GESTURES:
            cfg = gestures.get(gid, {})
            if not cfg.get("enabled", False):
                continue
            row = tk.Frame(gt.body, bg=p.surface_2)
            row.pack(fill="x", pady=2)
            glyph = GestureGlyph(row, p, gid, size=44, bg=p.surface_2)
            glyph.pack(side="left", padx=(0, 10))
            info = tk.Frame(row, bg=p.surface_2)
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=tr(GESTURE_LABELS[gid]), bg=p.surface_2, fg=p.text,
                     font=palette_font(self, "small_bold")).pack(anchor="w")
            action = tr(ACTION_LABELS.get(cfg.get("action", "none"), "—"))
            hint = tr(GESTURE_HINTS.get(gid, ""))
            tk.Label(info, text=f"→ {action}   |   delay {cfg.get('activation_delay', 0):.2f}s  cooldown {cfg.get('cooldown', 0):.2f}s",
                     bg=p.surface_2, fg=p.accent, font=palette_font(self, "tiny")).pack(anchor="w")
            tk.Label(info, text=hint, bg=p.surface_2, fg=p.text_mute,
                     font=palette_font(self, "tiny"), wraplength=500,
                     justify="left").pack(anchor="w")

        # Safety
        sf = Card(self.body, p, title=tr("Safety"), padding=16)
        sf.pack(fill="x", pady=(0, 10))
        items = [
            (tr("Emergency stop (Esc):"), tr("Releases all mouse buttons and turns control off immediately.")),
            (tr("PyAutoGUI corner failsafe:"), tr("Moving the physical mouse to a screen corner raises FailSafe — treated as an emergency stop.")),
            (tr("Automatic button release:"), tr("Any drag or held button is released on stop, hand lost, pause, or window close.")),
            (tr("Pause behaviour:"), tr("A fist pauses control; show an open palm to resume. No action can fire while paused.")),
        ]
        for label, text in items:
            row = tk.Frame(sf.body, bg=p.surface)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, bg=p.surface, fg=p.text,
                     font=palette_font(self, "body_bold")).pack(side="left")
            tk.Label(row, text=text, bg=p.surface, fg=p.text_dim,
                     font=palette_font(self, "small"), wraplength=620,
                     justify="left").pack(side="left", padx=(8, 0))

        # Keyboard shortcuts
        kb = Card(self.body, p, title=tr("Keyboard shortcuts"), padding=16)
        kb.pack(fill="x", pady=(0, 10))
        shortcuts = [
            ("F9", tr("Start mouse control")),
            ("F10", tr("Stop mouse control")),
            ("Esc", tr("Emergency stop — release all buttons")),
            ("Ctrl+T", tr("Pause / resume tracking")),
            ("Ctrl+1", tr("Dashboard")),
            ("Ctrl+2", tr("Gestures")),
            ("Ctrl+3", tr("Calibration")),
            ("Ctrl+4", tr("Mouse")),
            ("Ctrl+5", tr("Camera")),
            ("Ctrl+6", tr("Appearance")),
            ("Ctrl+7", tr("Help")),
        ]
        for key, desc in shortcuts:
            row = tk.Frame(kb.body, bg=p.surface)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=key, bg=p.surface_3, fg=p.accent,
                     font=palette_font(self, "small_bold"), padx=8, pady=4,
                     relief="solid", bd=1).pack(side="left")
            tk.Label(row, text=desc, bg=p.surface, fg=p.text_dim,
                     font=palette_font(self, "small")).pack(side="left", padx=(8, 0))

        # Troubleshooting
        ts = Card(self.body, p, title=tr("Troubleshooting"), padding=16)
        ts.pack(fill="x", pady=(0, 10))
        issues = [
            (tr("Camera not found:"), tr("Close other apps using the webcam, then click Refresh camera list on the Camera page.")),
            (tr("Hand not detected:"), tr("Improve lighting, keep the hand fully in frame, or lower Detection confidence on the Camera page.")),
            (tr("Cursor jittery:"), tr("Lower Sensitivity or increase Smoothing on the Mouse page.")),
            (tr("Accidental clicks:"), tr("Increase Activation delay for the gesture on the Gestures page.")),
            (tr("Light background:"), tr("Switch to Dark theme on the Appearance page for better contrast.")),
        ]
        for label, text in issues:
            row = tk.Frame(ts.body, bg=p.surface)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, bg=p.surface, fg=p.danger,
                     font=palette_font(self, "body_bold")).pack(side="left")
            tk.Label(row, text=text, bg=p.surface, fg=p.text_dim,
                     font=palette_font(self, "small"), wraplength=620,
                     justify="left").pack(side="left", padx=(8, 0))

        # Open settings folder
        btn = tk.Frame(self.body, bg=p.accent, cursor="hand2")
        btn.pack(fill="x", pady=(8, 0))
        lbl = tk.Label(btn, text=tr("Open settings folder (%APPDATA%\\AirGesture)"), bg=p.accent,
                       fg="#FFFFFF", font=palette_font(self, "body_bold"), padx=14, pady=8)
        lbl.pack()
        for w in (btn, lbl):
            w.bind("<Button-1>", lambda _e: self._open_settings_folder())

    def _open_settings_folder(self) -> None:
        try:
            folder = self.app.settings.path
            folder = os.path.dirname(folder)
            os.startfile(folder)
        except Exception as exc:  # pragma: no cover - defensive
            self.toast.show(f"Could not open folder: {exc}", "error")

    def on_show(self) -> None:
        pass
