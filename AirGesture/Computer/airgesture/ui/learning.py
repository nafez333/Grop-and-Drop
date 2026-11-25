"""Interactive gesture learning dialog.

Flow (honest, no simulated recognition):
  1. Show the target gesture and its illustration.
  2. Ask the user to hold the pose; the engine captures ~1.6 s of live poses.
  3. We run the real recogniser over those captured poses and measure how often
     the *target* gesture is recognised and how clear the margin is.
  4. Show the measured result. Only recognisable, unambiguous poses may be
     confirmed - otherwise we explain why and offer to retry.
  5. On confirm the caller stores a learned confidence factor.
"""

from __future__ import annotations

import tkinter as tk
from collections import Counter
from typing import Callable, Optional

from ...core.recognizer import UNKNOWN, GESTURE_HINTS, GESTURE_LABELS, GestureRecognizer
from ..i18n import tr
from ..theme import Palette
from ..widgets import GestureGlyph, palette_font


class LearningDialog(tk.Toplevel):
    def __init__(
        self,
        master,
        app,
        gesture_id: str,
        on_done: Callable[[str, Optional[float]], None],
    ):
        super().__init__(master)
        self.app = app
        self.gesture_id = gesture_id
        self.on_done = on_done
        self.palette: Palette = app.palette
        self.fonts = app.fonts
        self.configure(bg=self.palette.bg)
        self.title(f"Learn · {GESTURE_LABELS.get(gesture_id, gesture_id)}")
        self.resizable(False, False)
        self.transient(master)
        self._samples = []
        self._result: Optional[float] = None
        self._state = "intro"
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self._build()
        self.update_idletasks()
        self._center()

    def _center(self):
        m = self.master
        try:
            x = m.winfo_rootx() + (m.winfo_width() - self.winfo_width()) // 2
            y = m.winfo_rooty() + (m.winfo_height() - self.winfo_height()) // 3
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except tk.TclError:
            pass

    def _build(self):
        p = self.palette
        wrap = tk.Frame(self, bg=p.bg, padx=26, pady=22)
        wrap.pack(fill="both", expand=True)
        self.wrap = wrap

        top = tk.Frame(wrap, bg=p.bg)
        top.pack(fill="x")
        GestureGlyph(top, p, self.gesture_id, size=92, bg=p.surface).pack(side="left")
        txt = tk.Frame(top, bg=p.bg)
        txt.pack(side="left", padx=(16, 0), fill="x", expand=True)
        tk.Label(
            txt,
            text=f"Teaching: {GESTURE_LABELS.get(self.gesture_id, '')}",
            bg=p.bg,
            fg=p.text,
            font=self.fonts["h1"],
        ).pack(anchor="w")
        tk.Label(
            txt,
            text=GESTURE_HINTS.get(self.gesture_id, ""),
            bg=p.bg,
            fg=p.text_dim,
            font=self.fonts["small"],
            wraplength=380,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        self.status = tk.Label(
            wrap,
            text=tr("Hold this pose in front of the camera, comfortably."),
            bg=p.bg,
            fg=p.text,
            font=self.fonts["body"],
            wraplength=460,
            justify="left",
        )
        self.status.pack(anchor="w", pady=(18, 4))
        self.detail = tk.Label(
            wrap,
            text="",
            bg=p.bg,
            fg=p.text_mute,
            font=self.fonts["tiny"],
            wraplength=460,
            justify="left",
        )
        self.detail.pack(anchor="w")

        self.bar = tk.Canvas(wrap, height=8, bg=p.bg, highlightthickness=0, bd=0)
        self.bar.pack(fill="x", pady=(16, 0))
        self.bar.bind("<Configure>", lambda e: self._draw_bar(0.0))

        buttons = tk.Frame(wrap, bg=p.bg)
        buttons.pack(fill="x", pady=(20, 0))
        self.btn_cancel = self._btn(buttons, "Cancel", self._cancel, "ghost")
        self.btn_cancel.pack(side="right")
        self.btn_confirm = self._btn(buttons, "Start capture", self._capture, "accent")
        self.btn_confirm.pack(side="right", padx=(0, 8))

    def _btn(self, parent, text, cmd, variant):
        p = self.palette
        bg = p.accent if variant == "accent" else p.surface_2
        fg = "#FFFFFF" if variant == "accent" else p.text
        b = tk.Label(
            parent,
            text=text,
            bg=bg,
            fg=fg,
            font=palette_font(self, "body_bold"),
            padx=16,
            pady=8,
            cursor="hand2",
        )
        b.bind("<Button-1>", lambda _e: cmd())
        return b

    def _draw_bar(self, fraction: float):
        p = self.palette
        self.bar.delete("all")
        w = self.bar.winfo_width()
        h = 8
        from ..widgets import _round_rect

        _round_rect(self.bar, 0, 0, w, h, h / 2, fill=p.track, outline="")
        if fraction > 0:
            _round_rect(
                self.bar,
                0,
                0,
                max(h, w * min(1.0, fraction)),
                h,
                h / 2,
                fill=p.accent,
                outline="",
            )

    # ----------------------------------------------------------------- flow
    def _capture(self):
        self._state = "capturing"
        self._samples = []
        self.btn_confirm.configure(
            text=tr("Capturing..."), state="disabled", bg=self.palette.surface_3
        )
        self.status.configure(
            text=tr("Hold the pose naturally - keep it comfortable."), fg=self.palette.text
        )
        self.detail.configure(text=tr("Collecting live hand poses for 1.6 seconds."))
        engine = self.app.engine
        engine.on_capture_done = lambda samples: self._finish(samples)
        engine.request_capture(1.6)
        self._progress_start = self.winfo_toplevel().tk.call("clock", "milliseconds")
        self.after(50, self._tick)

    def _tick(self):
        if self._state != "capturing":
            return
        try:
            now = float(self.winfo_toplevel().tk.call("clock", "milliseconds"))
        except tk.TclError:
            return
        elapsed = (now - float(self._progress_start)) / 1000.0
        self._draw_bar(elapsed / 1.6)
        if elapsed < 1.8:
            self.after(50, self._tick)

    def _finish(self, samples):
        self.app.engine.on_capture_done = None
        if self._state != "capturing":
            return
        self._state = "result"
        self._draw_bar(1.0)
        if not samples or len(samples) < 8:
            self._result = None
            self.status.configure(text=tr("No hand was detected."), fg=self.palette.danger)
            self.detail.configure(
                text=tr("Make sure your hand is clearly visible in the camera preview, then try again.")
            )
            self.btn_confirm.configure(
                text=tr("Try again"), state="normal", bg=self.palette.accent
            )
            return

        recognizer = GestureRecognizer(sensitivity=0.6)
        detected = [recognizer.recognize(pose).gesture for pose in samples]
        counts = Counter(detected)
        total = len(detected)
        target_hits = counts.get(self.gesture_id, 0)
        other_hits = total - target_hits - counts.get(UNKNOWN, 0)
        rate = target_hits / total
        clarity = 1.0 - (other_hits / total)
        confidence = max(0.0, min(1.0, rate * 0.75 + clarity * 0.25))

        if rate >= 0.6 and other_hits / total <= 0.2:
            self._result = confidence
            self.status.configure(
                text=f"Pose recognised - {int(confidence * 100)}% consistency.",
                fg=self.palette.success,
            )
            self.detail.configure(
                text="This pose is distinct enough to use reliably. Confirm to save the calibration."
            )
            self.btn_confirm.configure(
                text="Save calibration", state="normal", bg=self.palette.accent
            )
            self.btn_confirm.bind("<Button-1>", lambda _e: self._confirm())
        else:
            self._result = None
            top_other = next(
                (
                    (g, n)
                    for g, n in counts.most_common()
                    if g not in (self.gesture_id, UNKNOWN)
                ),
                None,
            )
            reason = "The pose was only recognised some of the time."
            if top_other:
                reason = (
                    f"It looked more like {GESTURE_LABELS.get(top_other[0], top_other[0])} "
                    f"for {int(top_other[1] / total * 100)}% of the capture."
                )
            self.status.configure(
                text="This pose cannot be distinguished reliably.",
                fg=self.palette.warning,
            )
            self.detail.configure(
                text=f"{reason} Adjust the fingers to match the illustration and try again. "
                "We only save poses that are genuinely reliable."
            )
            self.btn_confirm.configure(
                text="Try again", state="normal", bg=self.palette.accent
            )
            self.btn_confirm.bind("<Button-1>", lambda _e: self._capture())

    def _confirm(self):
        self.on_done(self.gesture_id, self._result)
        self.destroy()

    def _cancel(self):
        if self._state == "capturing":
            self.app.engine.on_capture_done = None
            self.app.engine.submit("capture_stop")
        self.on_done(self.gesture_id, None)
        self.destroy()
