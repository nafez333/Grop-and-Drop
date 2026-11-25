"""Dashboard: live preview, control status, quick controls and gesture guide."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ...core.recognizer import ACTION_LABELS, GESTURES, GESTURE_LABELS
from ..camera_panel import CameraPanel
from ..i18n import tr
from ..icons import draw_icon
from ..widgets import Card, GestureGlyph, KeyValueRow, StatusPill, Toast, palette_font
from .base import Page


class DashboardPage(Page):
    title = tr("Dashboard")
    subtitle = tr("Live control, status and everything you need at a glance.")

    def build(self):
        p = self.palette
        f = self.fonts

        # toolbar in header
        self.mode_var = tk.StringVar(value=self.app.settings.get("interaction", "mode", "auto"))
        self.mode_choice = ttk.Combobox(
            self.header_right, textvariable=self.mode_var, state="readonly",
            values=[tr("auto - always active"), tr("active - hold palm to control")],
            width=30, font=f["small"],
        )
        self._refresh_mode_text()
        self.mode_choice.pack(side="right", padx=(10, 0))
        tk.Label(self.header_right, text=tr("Mode"), bg=p.bg, fg=p.text_dim,
                 font=f["small"]).pack(side="right")
        self.mode_choice.bind("<<ComboboxSelected>>", self._mode_changed)

        main = tk.Frame(self.body, bg=p.bg)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=4, uniform="cols")
        main.columnconfigure(1, weight=2, uniform="cols")
        main.rowconfigure(0, weight=1)

        # ------------------------------------------------------- preview card
        left = tk.Frame(main, bg=p.bg)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        preview = Card(left, p, title=tr("Live preview"),
                       subtitle=tr("Mirrored webcam with tracking overlay"), padding=14)
        preview.pack(fill="both", expand=True)

        bottom_bar = tk.Frame(preview.body, bg=p.surface)
        self.cam_panel = CameraPanel(preview.body, p, f)
        self.cam_panel.pack(fill="both", expand=True)
        bottom_bar.pack(fill="x", pady=(12, 0))

        # quick controls row
        self.btn_start = self._button(bottom_bar, tr("Start control"), "play", self._start, "accent")
        self.btn_start.pack(side="left")
        self.btn_stop = self._button(bottom_bar, tr("Stop control"), "stop", self._stop)
        self.btn_stop.pack(side="left", padx=(8, 0))
        self.btn_pause = self._button(bottom_bar, tr("Pause"), "pause", self._pause)
        self.btn_pause.pack(side="left", padx=(8, 0))
        self.btn_recal = self._button(bottom_bar, tr("Recalibrate"), "calibration",
                                      lambda: self.app.show_page("calibration"))
        self.btn_recal.pack(side="left", padx=(8, 0))
        self.btn_estop = self._button(bottom_bar, tr("Emergency stop"), "alert",
                                      self._emergency, "danger")
        self.btn_estop.pack(side="right")

        # ------------------------------------------------------- right column
        right = tk.Frame(main, bg=p.bg)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        status_card = Card(right, p, title=tr("Control status"), padding=16)
        status_card.grid(row=0, column=0, sticky="ew")
        sb = status_card.body
        self.pill_camera = StatusPill(sb, p, tr("Camera"), "muted", width=150)
        self.pill_camera.pack(fill="x", pady=3)
        self.pill_tracking = StatusPill(sb, p, tr("Tracking"), "muted", width=150)
        self.pill_tracking.pack(fill="x", pady=3)
        self.pill_gesture = StatusPill(sb, p, tr("Recognition"), "muted", width=150)
        self.pill_gesture.pack(fill="x", pady=3)
        self.pill_mouse = StatusPill(sb, p, tr("Mouse control"), "muted", width=150)
        self.pill_mouse.pack(fill="x", pady=3)

        sep = tk.Frame(sb, bg=p.border_soft, height=1)
        sep.pack(fill="x", pady=10)
        self.kv_gesture = KeyValueRow(sb, p, tr("Current gesture"), tr("No hand"))
        self.kv_gesture.pack(fill="x", pady=2)
        self.kv_action = KeyValueRow(sb, p, tr("Action"), "-")
        self.kv_action.pack(fill="x", pady=2)
        self.kv_conf = KeyValueRow(sb, p, tr("Confidence"), "-")
        self.kv_conf.pack(fill="x", pady=2)
        self.kv_fps = KeyValueRow(sb, p, tr("Performance"), "-")
        self.kv_fps.pack(fill="x", pady=2)

        # ------------------------------------------------------ gesture guide
        guide = Card(right, p, title=tr("Gesture guide"),
                     subtitle=f"{self.app.active_gesture_count()} active", padding=16)
        guide.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        self.guide_body = guide.body
        self._build_guide()

        self.toast = Toast(self)
        self._mode_label = {v: k for k, v in self._mode_options().items()}
        self._update_buttons(False)

    # ---------------------------------------------------------------- helpers
    def _mode_options(self):
        return {"auto": tr("auto - always active"), "active": tr("active - hold palm to control")}

    def _refresh_mode_text(self):
        opts = self._mode_options()
        self.mode_choice.configure(values=list(opts.values()))
        self.mode_var.set(opts.get(self.mode_var.get(), opts["auto"]))

    def _mode_changed(self, _e=None):
        mapping = {v: k for k, v in self._mode_options().items()}
        mode = mapping.get(self.mode_var.get(), "auto")
        self.app.settings.set("interaction", "mode", mode)
        self.app.engine.set_mode(mode)
        self.toast.show(f"Interaction mode: {mode}", "info")

    def _button(self, parent, text, icon, command, variant="ghost"):
        pal = self.palette
        bg = {"accent": pal.accent, "danger": pal.danger}.get(variant, pal.surface_2)
        fg = "#FFFFFF" if variant in ("accent", "danger") else pal.text
        b = tk.Frame(parent, bg=bg, cursor="hand2")
        cv = tk.Canvas(b, width=16, height=16, bg=bg, highlightthickness=0, bd=0)
        cv.pack(side="left", padx=(12, 7), pady=9)
        draw_icon(cv, icon, 8, 8, 12, fg, width=1.6)
        lbl = tk.Label(b, text=text, bg=bg, fg=fg, font=palette_font(self, "small_bold"))
        lbl.pack(side="left", padx=(0, 14), pady=8)
        for widget in (b, cv, lbl):
            widget.bind("<Button-1>", lambda _e: command())
        return b

    def _build_guide(self):
        p = self.palette
        for child in self.guide_body.winfo_children():
            child.destroy()
        gestures = self.app.settings.section("gestures")
        shown = 0
        for gid in GESTURES:
            cfg = gestures.get(gid, {})
            if not cfg.get("enabled", False):
                continue
            shown += 1
            row = tk.Frame(self.guide_body, bg=p.surface)
            row.pack(fill="x", pady=4)
            glyph = GestureGlyph(row, p, gid, size=58)
            glyph.pack(side="left")
            info = tk.Frame(row, bg=p.surface)
            info.pack(side="left", fill="x", expand=True, padx=(10, 0))
            tk.Label(info, text=tr(GESTURE_LABELS[gid]), bg=p.surface, fg=p.text,
                     font=palette_font(self, "small_bold")).pack(anchor="w")
            action = tr(ACTION_LABELS.get(cfg.get("action", "none"), "-"))
            tk.Label(info, text=action, bg=p.surface, fg=p.accent,
                     font=palette_font(self, "tiny")).pack(anchor="w")
            tk.Label(info, text=self._hint(gid), bg=p.surface, fg=p.text_mute,
                     font=palette_font(self, "tiny"), wraplength=250,
                     justify="left").pack(anchor="w", pady=(2, 0))
        if shown == 0:
            tk.Label(self.guide_body, text="No gestures are enabled.\nEnable some in the Gestures page.",
                     bg=p.surface, fg=p.text_dim, font=palette_font(self, "small"),
                     justify="left").pack(anchor="w")

    def _hint(self, gid):
        return {
            "open_palm": tr("Relaxed open hand - move your palm to move the cursor."),
            "fist": tr("All fingers curled - grab and drag the item with the cursor."),
            "index_only": tr("Index finger up, others relaxed. Pinch the thumb to it to click."),
            "pinch": tr("Touch thumb and index finger tips together - a pinch click."),
            "two_fingers": tr("Index and middle up, like a relaxed peace sign."),
            "three_fingers": tr("Index, middle and ring up. Keep the pinky relaxed."),
            "four_fingers": tr("Four fingers up, thumb relaxed."),
        }.get(gid, "")

    # -------------------------------------------------------------- lifecycle
    def _start(self):
        self.app.start_control()

    def _stop(self):
        self.app.stop_control()
        self.toast.show("Mouse control stopped", "info")

    def _pause(self):
        self.app.pause_tracking()
        self.toast.show("Paused - show an open palm to resume", "warn")

    def _emergency(self):
        self.app.emergency_stop()
        self.toast.show("Emergency stop - all mouse buttons released", "error")

    def _update_buttons(self, active: bool):
        self._set_visual(self.btn_start, "accent" if not active else "muted")
        self._set_visual(self.btn_stop, "normal" if active else "muted")

    def _set_visual(self, frame, state):
        p = self.palette
        bg = p.surface_3 if state == "muted" else frame.cget("bg")
        if state == "normal":
            bg = p.surface_2
        for child in frame.winfo_children():
            try:
                child.configure(bg=bg)
            except tk.TclError:
                pass

    def on_frame(self, packet):
        if packet is None:
            return
        self.cam_panel.update_packet(packet)
        p = self.palette

        # camera pill
        if packet.error:
            self.pill_camera.set(tr("Camera error"), "error")
        elif getattr(packet, "frame", None) is not None:
            self.pill_camera.set(tr("Camera streaming"), "ok")
        else:
            self.pill_camera.set(tr("Camera starting"), "warn")

        if packet.gesture:
            self.pill_tracking.set(f"{tr('Hand detected')} ({packet.handedness})", "ok")
            self.pill_gesture.set(f"{tr('Recognition')} · {int(packet.confidence * 100)}%",
                                  "accent" if packet.confidence > 0.5 else "warn")
        elif getattr(packet, "frame", None) is not None:
            self.pill_tracking.set(tr("No hand in view"), "warn")
            self.pill_gesture.set(tr("Waiting for hand"), "muted")

        if packet.paused:
            self.pill_mouse.set(tr("Control paused"), "warn")
        elif packet.active:
            self.pill_mouse.set(tr("Mouse control ON"), "ok")
        else:
            self.pill_mouse.set(tr("Mouse control OFF"), "muted")

        self.kv_gesture.set(tr(packet.gesture_label), p.accent if packet.gesture else None)
        self.kv_action.set(tr(packet.action))
        self.kv_conf.set(f"{int(packet.confidence * 100)}%" if packet.gesture else "-",
                         p.success if packet.confidence > 0.6 else p.warning if packet.gesture else None)
        self.kv_fps.set(f"{packet.fps:.0f} fps · {packet.frame_ms:.0f} ms")
        self._update_buttons(packet.active)
        if packet.error:
            self.toast.show(packet.error, "error", 4000)

    def on_engine_status(self, status, message):
        if status in ("error", "warning"):
            self.toast.show(message, "error" if status == "error" else "warn", 5000)
            if status == "error":
                self.pill_camera.set("Camera error", "error")
                self.cam_panel.set_placeholder(message)

    def on_settings(self, section, key):
        if section == "gestures":
            self._build_guide()
        if section == "interaction" and key == "mode":
            mode = self.app.settings.get("interaction", "mode", "auto")
            self.mode_var.set(self._mode_options().get(mode, "auto - always active"))

    def on_show(self):
        pkt = self.app.engine.latest()
        if pkt is not None:
            self.on_frame(pkt)
