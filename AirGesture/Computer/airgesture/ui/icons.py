"""Vector icons drawn on a Canvas (crisp at any DPI, no image assets needed)."""

from __future__ import annotations

import tkinter as tk


def draw_icon(
    canvas: tk.Canvas,
    name: str,
    x: float,
    y: float,
    size: float,
    color: str,
    width: float = 1.7,
) -> None:
    """Draw a stroked line icon centred on (x, y)."""
    s = size / 2.0
    w = max(1, int(round(width)))
    kw = dict(fill=color, width=w, capstyle="round", joinstyle="round")

    def line(*pts):
        canvas.create_line(*pts, **kw)

    def rect(x1, y1, x2, y2, r=0):
        if r:
            canvas.create_polygon(
                x1 + r,
                y1,
                x2 - r,
                y1,
                x2,
                y1,
                x2,
                y1 + r,
                x2,
                y2 - r,
                x2,
                y2,
                x2 - r,
                y2,
                x1 + r,
                y2,
                x1,
                y2,
                x1,
                y2 - r,
                x1,
                y1 + r,
                x1,
                y1,
                smooth=True,
                outline=color,
                fill="",
                width=w,
            )
        else:
            canvas.create_rectangle(x1, y1, x2, y2, outline=color, fill="", width=w)

    def circle(cx, cy, r, fill=""):
        canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r, outline=color, fill=fill, width=w
        )

    if name == "dashboard":
        rect(x - s, y - s, x - s * 0.15, y - s * 0.15, s * 0.2)
        rect(x + s * 0.15, y - s, x + s, y - s * 0.2, s * 0.2)
        rect(x - s, y + s * 0.15, x - s * 0.15, y + s, s * 0.2)
        rect(x + s * 0.15, y + s * 0.2, x + s, y + s, s * 0.2)
    elif name == "gestures":
        circle(x - s * 0.45, y - s * 0.1, s * 0.32)
        circle(x + s * 0.45, y + s * 0.1, s * 0.32)
        line(x - s * 0.9, y + s * 0.75, x + s * 0.9, y + s * 0.75)
    elif name == "calibration":
        circle(x, y, s * 0.78)
        circle(x, y, s * 0.18)
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            line(
                x + dx * s * 0.78,
                y + dy * s * 0.78,
                x + dx * s * 1.05,
                y + dy * s * 1.05,
            )
    elif name == "mouse":
        rect(x - s * 0.5, y - s * 0.9, x + s * 0.5, y + s * 0.9, s * 0.45)
        line(x, y - s * 0.55, x, y - s * 0.15)
    elif name == "camera":
        rect(x - s * 0.95, y - s * 0.6, x + s * 0.35, y + s * 0.65, s * 0.2)
        line(x + s * 0.35, y - s * 0.15, x + s * 0.95, y - s * 0.55)
        line(x + s * 0.35, y + s * 0.2, x + s * 0.95, y + s * 0.6)
    elif name == "appearance":
        circle(x, y, s * 0.72)
        circle(x - s * 0.05, y - s * 0.1, s * 0.42)
    elif name == "help":
        circle(x, y, s * 0.85)
        canvas.create_text(
            x,
            y - s * 0.1,
            text="?",
            fill=color,
            font=("Segoe UI", max(7, int(s * 0.9)), "bold"),
        )
    elif name == "play":
        canvas.create_polygon(
            x - s * 0.55,
            y - s * 0.75,
            x + s * 0.8,
            y,
            x - s * 0.55,
            y + s * 0.75,
            fill=color,
            outline="",
        )
    elif name == "pause":
        canvas.create_rectangle(
            x - s * 0.55, y - s * 0.7, x - s * 0.15, y + s * 0.7, fill=color, outline=""
        )
        canvas.create_rectangle(
            x + s * 0.15, y - s * 0.7, x + s * 0.55, y + s * 0.7, fill=color, outline=""
        )
    elif name == "stop":
        canvas.create_rectangle(
            x - s * 0.65,
            y - s * 0.65,
            x + s * 0.65,
            y + s * 0.65,
            fill=color,
            outline="",
        )
    elif name == "alert":
        canvas.create_polygon(
            x,
            y - s * 0.9,
            x + s * 0.95,
            y + s * 0.75,
            x - s * 0.95,
            y + s * 0.75,
            outline=color,
            fill="",
            width=w,
            joinstyle="round",
        )
        line(x, y - s * 0.25, x, y + s * 0.2)
        circle(x, y + s * 0.46, max(1, s * 0.06), fill=color)
    elif name == "hand":
        rect(x - s * 0.6, y - s * 0.15, x + s * 0.6, y + s * 0.9, s * 0.25)
        for i, dx in enumerate((-0.42, -0.14, 0.14, 0.42)):
            line(
                x + dx * s,
                y - s * 0.1,
                x + dx * s,
                y - s * (0.75 - abs(i - 1.5) * 0.12),
            )
    else:
        circle(x, y, s * 0.75)


class IconButton(tk.Frame):
    """Icon + label button that highlights on hover; used in the sidebar and quick actions."""

    def __init__(
        self,
        master,
        palette,
        icon: str,
        text: str,
        command=None,
        variant: str = "ghost",
        compact: bool = False,
    ):
        self.palette = palette
        self.variant = variant
        self.command = command
        self.active = False
        bg = self._base_bg()
        super().__init__(master, bg=bg, cursor="hand2")
        self.canvas = tk.Canvas(
            self,
            width=20 if compact else 22,
            height=20 if compact else 22,
            bg=bg,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(
            side="left", padx=(0 if compact else 6, 8 if not compact else 6)
        )
        self.label = tk.Label(
            self,
            text=text,
            bg=bg,
            fg=self._fg(),
            font=("Segoe UI", 10, "bold" if variant != "ghost" else "normal"),
        )
        if not compact:
            self.label.pack(side="left")
        self._icon = icon
        self._draw()
        for widget in (self, self.canvas, self.label):
            widget.bind("<Button-1>", self._click)
            widget.bind("<Enter>", self._hover)
            widget.bind("<Leave>", self._leave)

    def _base_bg(self):
        p = self.palette
        return {"accent": p.accent, "danger": p.danger, "surface": p.surface_2}.get(
            self.variant, p.bg_alt
        )

    def _fg(self):
        p = self.palette
        return {"accent": "#FFFFFF", "danger": "#FFFFFF"}.get(self.variant, p.text_dim)

    def _draw(self):
        self.canvas.delete("all")
        fg = "#FFFFFF" if self.active else self._fg()
        if self.active:
            fg = self.palette.accent
        draw_icon(self.canvas, self._icon, 11, 11, 15, fg)

    def _click(self, _e=None):
        if self.command:
            self.command()

    def _hover(self, _e=None):
        if self.variant == "ghost":
            self._paint(self.palette.surface_2, self.palette.text)

    def _leave(self, _e=None):
        if self.variant == "ghost":
            self._paint(self.palette.bg_alt, self.palette.text_dim)

    def _paint(self, bg, fg):
        self.configure(bg=bg)
        self.canvas.configure(bg=bg)
        self.label.configure(bg=bg, fg=fg)
        self.canvas.delete("all")
        draw_icon(
            self.canvas,
            self._icon,
            11,
            11,
            15,
            self.palette.accent if self.active else fg,
        )

    def set_active(self, active: bool):
        self.active = active
        p = self.palette
        if active:
            self._paint(p.surface_2, p.text)
        else:
            self._paint(p.bg_alt, p.text_dim)

    def set_enabled(self, enabled: bool):
        fg = self.palette.text_dim if enabled else self.palette.text_mute
        self._paint(self._base_bg(), fg)
