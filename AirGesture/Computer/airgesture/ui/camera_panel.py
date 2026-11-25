"""Live camera panel: video + tracking overlay + HUD rendered on a Canvas."""

from __future__ import annotations

import tkinter as tk
from typing import Optional

from PIL import Image, ImageTk

from ..widgets import _round_rect


class CameraPanel(tk.Frame):
    """Renders the latest engine frame scaled to fit, with a professional HUD.

    Rendering work per update is small: the engine already drew the skeleton,
    this only resizes the image and draws text/badges on top. It never blocks.
    """

    def __init__(self, master, palette, fonts, on_resize=None):
        self.palette = palette
        self.fonts = fonts
        self.on_resize = on_resize
        super().__init__(master, bg=palette.bg, highlightthickness=0)
        self.canvas = tk.Canvas(self, bg=palette.surface, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self._photo: Optional[ImageTk.PhotoImage] = None
        self._last_frame_id = None
        self._packet = None
        self._size = (640, 400)
        self.canvas.bind("<Configure>", self._on_configure)
        self._placeholder = "Starting camera..."

    # ------------------------------------------------------------------ public
    def set_placeholder(self, text: str) -> None:
        self._placeholder = text
        if self._packet is None or self._packet.frame is None:
            self._draw_scene()

    def update_packet(self, packet) -> None:
        self._packet = packet
        self._draw_scene()

    # ------------------------------------------------------------------ drawing
    def _on_configure(self, event):
        self._size = (max(200, event.width), max(140, event.height))
        self._draw_scene()
        if self.on_resize:
            self.on_resize()
        self.canvas.delete("fp")
        w, h = self._size
        self.canvas.create_rectangle(
            0, 0, w, h, outline=self.palette.surface, tags="fp"
        )

    def _draw_scene(self) -> None:
        c = self.canvas
        p = self.palette
        w, h = self._size
        c.delete("all")
        c.create_rectangle(0, 0, w, h, fill="#0B0C10", outline="")
        pkt = self._packet

        if pkt is not None and getattr(pkt, "frame", None) is not None:
            frame = pkt.frame
            fh, fw = frame.shape[:2]
            scale = min(w / fw, h / fh)
            nw, nh = int(fw * scale), int(fh * scale)
            rgb = frame[:, :, ::-1]
            img = Image.fromarray(rgb)
            if (nw, nh) != (fw, fh):
                img = img.resize((nw, nh), Image.BILINEAR)
            self._photo = ImageTk.PhotoImage(img)
            self._last_frame_id = (id(frame), frame.shape, nw, nh, pkt.timestamp)
            c.create_image((w - nw) // 2, (h - nh) // 2, image=self._photo, anchor="nw")
            self._hud(pkt, w, h)
        else:
            self._empty_state(w, h)

    def _empty_state(self, w, h):
        c = self.canvas
        p = self.palette
        msg = self._placeholder
        if self._packet is not None and getattr(self._packet, "error", ""):
            msg = self._packet.error
        c.create_text(
            w / 2,
            h / 2 - 10,
            text="Camera preview",
            fill=p.text_mute,
            font=self.fonts["h2"],
        )
        c.create_text(
            w / 2,
            h / 2 + 14,
            text=msg,
            fill=p.text_dim,
            font=self.fonts["small"],
            width=max(200, w - 60),
        )

        # corner brackets for a "viewfinder" feel
        m, ln = 18, 22
        for x1, y1, x2, y2 in (
            (m, m, m + ln, m),
            (m, m, m, m + ln),
            (w - m, m, w - m - ln, m),
            (w - m, m, w - m, m + ln),
            (m, h - m, m + ln, h - m),
            (m, h - m, m, h - m - ln),
            (w - m, h - m, w - m - ln, h - m),
            (w - m, h - m, w - m, h - m - ln),
        ):
            c.create_line(x1, y1, x2, y2, fill=self.palette.surface_3, width=2)

    def _hud(self, pkt, w, h):
        c = self.canvas
        p = self.palette
        # top-left status
        active = getattr(pkt, "active", False)
        paused = getattr(pkt, "paused", False)
        tone = p.danger if paused else (p.success if active else p.text_dim)
        label = "PAUSED" if paused else ("LIVE CONTROL" if active else "STANDBY")
        _round_rect(
            c, 12, 12, 12 + 12 + len(label) * 7.2, 40, 14, fill="#111318", outline=""
        )
        c.create_oval(22, 22, 30, 30, fill=tone, outline="")
        c.create_text(
            36, 26, text=label, anchor="w", fill="#EEF0F4", font=self.fonts["tiny"]
        )
        if getattr(pkt, "dragging", False):
            _round_rect(c, 12, 48, 96, 74, 12, fill=p.danger, outline="")
            c.create_text(
                54, 61, text="DRAGGING", fill="#FFFFFF", font=self.fonts["tiny"]
            )

        # top-right gesture + confidence
        gtxt = getattr(pkt, "gesture_label", "No hand")
        conf = float(getattr(pkt, "confidence", 0.0))
        bw = max(150, 20 + len(gtxt) * 7.5)
        _round_rect(c, w - bw - 12, 12, w - 12, 46, 14, fill="#111318", outline="")
        c.create_text(
            w - bw - 4,
            24,
            text="GESTURE",
            anchor="nw",
            fill="#8A91A1",
            font=self.fonts["tiny"],
        )
        c.create_text(
            w - 22,
            25,
            text=gtxt,
            anchor="ne",
            fill="#F2F4F8",
            font=self.fonts["small_bold"],
        )
        # confidence bar
        bar_w = bw - 24
        c.create_rectangle(
            w - bw - 4, 38, w - bw - 4 + bar_w, 41, fill="#242832", outline=""
        )
        if pkt.gesture:
            c.create_rectangle(
                w - bw - 4,
                38,
                w - bw - 4 + bar_w * max(0.05, min(1.0, conf)),
                41,
                fill=p.accent,
                outline="",
            )

        # bottom-left FPS / handedness
        fps = getattr(pkt, "fps", 0.0)
        handed = getattr(pkt, "handedness", "Unknown")
        line1 = f"{fps:4.1f} fps   {getattr(pkt, 'frame_ms', 0.0):5.1f} ms"
        c.create_text(
            14, h - 26, text=line1, anchor="w", fill="#B9BFCC", font=self.fonts["mono"]
        )
        if pkt.gesture:
            c.create_text(
                14,
                h - 10,
                text=f"{handed} hand",
                anchor="w",
                fill="#7F8798",
                font=self.fonts["tiny"],
            )

        if getattr(pkt, "message", "") and not active:
            _round_rect(
                c,
                w / 2 - 150,
                h - 44,
                w / 2 + 150,
                h - 16,
                14,
                fill="#111318",
                outline="",
            )
            c.create_text(
                w / 2,
                h - 30,
                text=pkt.message,
                fill="#C7CBDA",
                font=self.fonts["tiny"],
                width=280,
            )

        # rounded frame border
        _round_rect(c, 1, 1, w - 1, h - 1, 14, fill="", outline=p.border)
