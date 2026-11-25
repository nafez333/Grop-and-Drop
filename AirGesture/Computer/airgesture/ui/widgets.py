"""Reusable Tk widgets that give the app its consistent visual language."""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from tkinter import ttk

from .i18n import tr
from .theme import Palette


def _round_rect(canvas: tk.Canvas, x1, y1, x2, y2, r, **kwargs):
    points = [
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
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class Card(tk.Frame):
    """A rounded panel with an optional title and subtitle.

    Implemented as a Frame with a Canvas-drawn rounded background; children are
    placed inside ``self.body`` so layout code stays simple.
    """

    def __init__(
        self,
        master,
        palette: Palette,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        padding: int = 16,
        radius: int = 14,
        bg_key: str = "surface",
        **kwargs,
    ):
        super().__init__(master, bg=palette.bg, highlightthickness=0, **kwargs)
        self.palette = palette
        self.radius = radius
        self.bg_color = getattr(palette, bg_key)
        self.padding = padding
        self._canvas = tk.Canvas(self, bg=palette.bg, highlightthickness=0, bd=0)
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.body = tk.Frame(self, bg=self.bg_color)
        self.body.pack(fill="both", expand=True, padx=padding, pady=padding)
        self.bind("<Configure>", self._redraw)

        if title:
            head = tk.Frame(self.body, bg=self.bg_color)
            head.pack(fill="x", pady=(0, 10))
            tk.Label(
                head,
                text=title,
                bg=self.bg_color,
                fg=palette.text,
                font=(palette_font(self, "h2")),
            ).pack(side="left")
            if subtitle:
                tk.Label(
                    head,
                    text=subtitle,
                    bg=self.bg_color,
                    fg=palette.text_mute,
                    font=palette_font(self, "small"),
                ).pack(side="left", padx=(10, 0))

    def _redraw(self, _event=None):
        w = self.winfo_width()
        h = self.winfo_height()
        self._canvas.delete("bg")
        if w > 2 and h > 2:
            _round_rect(
                self._canvas,
                0,
                0,
                w,
                h,
                self.radius,
                fill=self.bg_color,
                outline=self.palette.border_soft,
                tags="bg",
            )
            self._canvas.tag_lower("bg")


def palette_font(widget, name: str):
    root = widget.winfo_toplevel()
    fonts = getattr(root, "ag_fonts", None)
    if fonts and name in fonts:
        return fonts[name]
    return ("Segoe UI", 10)


class StatusPill(tk.Canvas):
    """Small coloured status chip: dot + label."""

    def __init__(
        self,
        master,
        palette: Palette,
        text: str = "",
        tone: str = "muted",
        width: int = 110,
        bg: Optional[str] = None,
        height: int = 26,
    ):
        self.palette = palette
        self.bg = bg or palette.surface
        super().__init__(
            master, bg=self.bg, height=height, width=width, highlightthickness=0, bd=0
        )
        self._text = text
        self._tone = tone
        self._width = width
        self._h = height
        self.bind("<Configure>", lambda e: self._draw())
        self._draw()

    def set(self, text: str, tone: str) -> None:
        if text == self._text and tone == self._tone:
            return
        self._text = text
        self._tone = tone
        self._draw()

    def _tone_color(self) -> str:
        p = self.palette
        return {
            "ok": p.success,
            "warn": p.warning,
            "error": p.danger,
            "info": p.info,
            "accent": p.accent,
            "muted": p.text_mute,
        }.get(self._tone, p.text_mute)

    def _draw(self):
        self.delete("all")
        p = self.palette
        h = int(self.winfo_height() or self._h)
        r = h / 2
        w = max(self.winfo_width(), self._width)
        fill = p.surface_2
        _round_rect(self, 0, 0, w, h, r, fill=fill, outline=p.border_soft)
        col = self._tone_color()
        cy = h / 2
        self.create_oval(10, cy - 4, 18, cy + 4, fill=col, outline=col)
        self.create_text(
            25,
            cy,
            text=self._text,
            anchor="w",
            fill=p.text,
            font=palette_font(self, "small_bold"),
        )


class SliderField(tk.Frame):
    """Labelled slider + numeric value + optional reset. Emits on release only."""

    def __init__(
        self,
        master,
        palette: Palette,
        label: str,
        from_: float,
        to: float,
        variable: tk.DoubleVar,
        unit: str = "",
        decimals: int = 2,
        on_change: Optional[Callable[[float], None]] = None,
        on_commit: Optional[Callable[[], None]] = None,
        live: bool = True,
        default: Optional[float] = None,
    ):
        super().__init__(master, bg=palette.surface)
        self.palette = palette
        self.variable = variable
        self.unit = unit
        self.decimals = decimals
        self.on_change = on_change
        self.on_commit = on_commit
        self.default = default

        row = tk.Frame(self, bg=palette.surface)
        row.pack(fill="x")
        tk.Label(
            row,
            text=label,
            bg=palette.surface,
            fg=palette.text,
            font=palette_font(self, "body"),
        ).pack(side="left")
        self.value_lbl = tk.Label(
            row,
            text=self._fmt(variable.get()),
            bg=palette.surface,
            fg=palette.accent,
            font=palette_font(self, "small_bold"),
        )
        self.value_lbl.pack(side="right")
        if default is not None:
            tk.Button(
                row,
                text=tr("reset"),
                relief="flat",
                bd=0,
                bg=palette.surface,
                fg=palette.text_mute,
                activebackground=palette.surface_2,
                activeforeground=palette.text,
                cursor="hand2",
                font=palette_font(self, "tiny"),
                command=lambda: self._reset(),
            ).pack(side="right", padx=(0, 8))

        self.scale = ttk.Scale(
            self,
            from_=from_,
            to=to,
            variable=variable,
            orient="horizontal",
            style="Horizontal.TScale",
            command=self._changed,
        )
        self.scale.pack(fill="x", pady=(4, 0))
        self.scale.bind("<ButtonRelease-1>", self._released)
        self.scale.bind("<MouseWheel>", lambda e: self.scale.event_generate("<Right>"))

    def _fmt(self, v) -> str:
        try:
            return f"{float(v):.{self.decimals}f}{self.unit}"
        except (TypeError, ValueError):
            return str(v)

    def _changed(self, _v=None):
        self.value_lbl.configure(text=self._fmt(self.variable.get()))
        if self.on_change:
            self.on_change(self.variable.get())

    def _released(self, _e=None):
        if self.on_commit:
            self.on_commit()

    def _reset(self):
        if self.default is not None:
            self.variable.set(self.default)
            self._changed()


class ToggleRow(tk.Frame):
    """Label + description on the left, switch on the right."""

    def __init__(
        self,
        master,
        palette: Palette,
        label: str,
        variable: tk.BooleanVar,
        description: str = "",
        on_change: Optional[Callable[[bool], None]] = None,
    ):
        super().__init__(master, bg=palette.surface)
        self.variable = variable
        self.on_change = on_change
        text = tk.Frame(self, bg=palette.surface)
        text.pack(side="left", fill="x", expand=True)
        tk.Label(
            text,
            text=label,
            bg=palette.surface,
            fg=palette.text,
            font=palette_font(self, "body"),
        ).pack(anchor="w")
        if description:
            tk.Label(
                text,
                text=description,
                bg=palette.surface,
                fg=palette.text_mute,
                font=palette_font(self, "tiny"),
                wraplength=520,
                justify="left",
            ).pack(anchor="w")
        self.switch = Switch(self, palette, variable, command=self._toggled)
        self.switch.pack(side="right", padx=(12, 0))

    def _toggled(self, value: bool):
        if self.on_change:
            self.on_change(value)


class Switch(tk.Canvas):
    """A drawn on/off switch (Tk checkbuttons cannot be fully themed)."""

    def __init__(
        self,
        master,
        palette: Palette,
        variable: tk.BooleanVar,
        command: Optional[Callable[[bool], None]] = None,
        width: int = 46,
        height: int = 24,
        bg: Optional[str] = None,
    ):
        self.palette = palette
        self.variable = variable
        self.on_command = command
        self._width, self._h = width, height
        super().__init__(
            master, width=width, height=height, bg=bg or palette.surface,
            highlightthickness=0, bd=0, cursor="hand2",
        )
        self.bind("<Button-1>", self._click)
        variable.trace_add("write", lambda *_: self._draw())
        self._draw()

    def _click(self, _e=None):
        self.variable.set(not bool(self.variable.get()))
        if self.on_command:
            self.on_command(bool(self.variable.get()))

    def _draw(self):
        self.delete("all")
        p = self.palette
        on = bool(self.variable.get())
        w, h = self._width, self._h
        r = h / 2
        _round_rect(self, 1, 1, w - 1, h - 1, r - 1,
                    fill=p.accent if on else p.surface_3,
                    outline=p.accent if on else p.border)
        knob = 9
        kx = (w - knob - 3) if on else knob + 3
        self.create_oval(kx - knob, h / 2 - knob, kx + knob, h / 2 + knob,
                         fill="#FFFFFF" if on else p.text_mute, outline="")


class SegmentedControl(tk.Frame):
    """A row of mutually exclusive buttons (used for modes)."""

    def __init__(
        self,
        master,
        palette: Palette,
        options: list[tuple[str, str]],
        variable: tk.StringVar,
        on_change: Optional[Callable[[str], None]] = None,
        bg: Optional[str] = None,
    ):
        super().__init__(master, bg=bg or palette.surface)
        self.palette = palette
        self.variable = variable
        self.on_change = on_change
        self._buttons: dict[str, tk.Button] = {}
        self._bg = bg or palette.surface
        for value, label in options:
            b = tk.Button(
                self,
                text=label,
                relief="flat",
                bd=0,
                cursor="hand2",
                font=palette_font(self, "small_bold"),
                command=lambda v=value: self._select(v),
            )
            b.pack(side="left", padx=(0, 6))
            self._buttons[value] = b
        variable.trace_add("write", lambda *_: self._sync())
        self._sync()

    def _select(self, value: str):
        self.variable.set(value)
        if self.on_change:
            self.on_change(value)

    def _sync(self):
        p = self.palette
        current = self.variable.get()
        for value, b in self._buttons.items():
            if value == current:
                b.configure(
                    bg=p.accent,
                    fg="#FFFFFF",
                    activebackground=p.accent_hover,
                    activeforeground="#FFFFFF",
                    padx=12,
                    pady=6,
                )
            else:
                b.configure(
                    bg=self._bg,
                    fg=p.text_dim,
                    activebackground=p.surface_2,
                    activeforeground=p.text,
                    padx=12,
                    pady=6,
                )


class GestureGlyph(tk.Canvas):
    """Schematic hand illustration for each gesture (drawn vector-style).

    These are honest, stylised diagrams of the hand poses the recogniser
    expects - not photos - so they stay legible on every theme and scale.
    """

    # finger lines: (x_base, y_base, x_tip, y_tip, finger_key)
    def __init__(
        self,
        master,
        palette: Palette,
        gesture: str,
        size: int = 74,
        bg: Optional[str] = None,
    ):
        self.palette = palette
        self.bg = bg or palette.surface_2
        super().__init__(
            master,
            width=size,
            height=size,
            bg=bg or palette.surface_2,
            highlightthickness=0,
            bd=0,
        )
        self.gesture = gesture
        self.size = size
        self._draw()

    def set_gesture(self, gesture: str, palette: Optional[Palette] = None):
        self.gesture = gesture
        if palette:
            self.palette = palette
        self._draw()

    def _draw(self):
        self.delete("all")
        p = self.palette
        s = self.size
        cx, cy = s * 0.5, s * 0.62

        def L(x):  # scale helper
            return x * s

        # palm
        _round_rect(
            self,
            L(0.26),
            L(0.42),
            L(0.74),
            L(0.80),
            L(0.10),
            fill=p.surface_3,
            outline=p.border,
        )

        g = self.gesture
        # finger geometry: x positions and extended lengths
        fingers = {
            "index": (0.33, 0.30),
            "middle": (0.46, 0.20),
            "ring": (0.59, 0.30),
            "pinky": (0.70, 0.40),
        }
        extended = {
            "open_palm": {"index", "middle", "ring", "pinky"},
            "index_only": {"index"},
            "pinch": {"index"},
            "two_fingers": {"index", "middle"},
            "three_fingers": {"index", "middle", "ring"},
            "four_fingers": {"index", "middle", "ring", "pinky"},
            "fist": set(),
        }.get(g, {"index", "middle", "ring", "pinky"})

        for name, (fx, ext_y) in fingers.items():
            x = L(fx)
            base_y = L(0.46)
            if name in extended:
                tip_y = L(ext_y * 0.95)
                self._round_line(x, base_y, x, tip_y, L(0.065), p.accent)
            else:
                # curled: short stub
                self._round_line(x, base_y, x, base_y - L(0.05), L(0.065), p.surface_3)

        # thumb
        if g == "fist":
            self._round_line(L(0.28), L(0.58), L(0.22), L(0.68), L(0.075), p.surface_3)
        elif g == "pinch":
            # thumb meets index tip
            tip_y = L(0.30 * 0.95)
            self._round_line(
                L(0.24), L(0.62), L(0.31), tip_y + L(0.02), L(0.07), p.accent
            )
            self.create_oval(
                L(0.27),
                tip_y - L(0.03),
                L(0.37),
                tip_y + L(0.07),
                fill=p.success,
                outline="",
            )
        else:
            self._round_line(L(0.27), L(0.60), L(0.16), L(0.40), L(0.075), p.accent)

    def _round_line(self, x1, y1, x2, y2, width, color):
        self.create_line(
            x1, y1, x2, y2, width=width, fill=color, capstyle="round", joinstyle="round"
        )


class Toast(tk.Frame):
    """Transient notification inside a parent container (not an OS popup)."""

    def __init__(self, master, palette: Optional[Palette] = None):
        if palette is None:
            palette = getattr(master, "palette", None)
            if palette is None and hasattr(master, "app"):
                palette = getattr(master.app, "palette", None)
            if palette is None:
                palette = Palette()
        super().__init__(
            master,
            bg=palette.surface_2,
            highlightthickness=1,
            highlightbackground=palette.border,
        )
        self.palette = palette
        self._label = tk.Label(
            self,
            text="",
            bg=palette.surface_2,
            fg=palette.text,
            font=palette_font(self, "small"),
            padx=14,
            pady=8,
        )
        self._label.pack()
        self._after_id = None

    def show(self, message: str, tone: str = "info", duration: int = 2600):
        p = self.palette
        color = {
            "ok": p.success,
            "warn": p.warning,
            "error": p.danger,
            "info": p.info,
        }.get(tone, p.text)
        self._label.configure(text=message, fg=color)
        self.lift()
        self.place(relx=1.0, rely=1.0, anchor="se", x=-18, y=-18)
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self.after(duration, self.hide)

    def hide(self):
        self.place_forget()


class KeyValueRow(tk.Frame):
    """A compact label/value line used in status cards."""

    def __init__(
        self,
        master,
        palette: Palette,
        label: str,
        value: str = "-",
        value_color: Optional[str] = None,
        bg: Optional[str] = None,
    ):
        bg = bg or palette.surface
        super().__init__(master, bg=bg)
        tk.Label(
            self,
            text=label,
            bg=bg,
            fg=palette.text_dim,
            font=palette_font(self, "small"),
        ).pack(side="left")
        self.value = tk.Label(
            self,
            text=value,
            bg=bg,
            fg=value_color or palette.text,
            font=palette_font(self, "small_bold"),
        )
        self.value.pack(side="right")

    def set(self, text: str, color: Optional[str] = None):
        self.value.configure(text=text)
        if color:
            self.value.configure(fg=color)
