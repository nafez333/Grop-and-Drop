"""Base class for pages and shared page helpers (scrollable body, headers)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ..i18n import tr


class Page(tk.Frame):
    """A page owns its widgets and receives context (app) and refresh calls."""

    title = tr("Page")
    subtitle = tr("")

    def __init__(self, master, app):
        self.app = app
        self.palette = app.palette
        self.fonts = app.fonts
        super().__init__(master, bg=self.palette.bg)
        self.root_frame = tk.Frame(self, bg=self.palette.bg)
        self.root_frame.pack(fill="both", expand=True, padx=26, pady=(20, 18))
        self.header()
        self.body = tk.Frame(self.root_frame, bg=self.palette.bg)
        self.body.pack(fill="both", expand=True, pady=(14, 0))
        self.build()

    # -------------------------------------------------------------- overridable
    def build(self) -> None:  # pragma: no cover - abstract
        pass

    def on_show(self) -> None:
        pass

    def on_hide(self) -> None:
        pass

    def on_frame(self, packet) -> None:
        pass

    def on_settings(self, section: str, key: str) -> None:
        pass

    def on_engine_status(self, status: str, message: str) -> None:
        pass

    # ------------------------------------------------------------------ helpers
    def header(self, title: Optional[str] = None, subtitle: Optional[str] = None):
        p = self.palette
        row = tk.Frame(self.root_frame, bg=p.bg)
        row.pack(fill="x")
        left = tk.Frame(row, bg=p.bg)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(
            left,
            text=title or self.title,
            bg=p.bg,
            fg=p.text,
            font=(
                self.fonts["display"]
                if hasattr(self.fonts, "get")
                else self.fonts["h1"]
            ),
        ).pack(anchor="w")
        tk.Label(
            left,
            text=subtitle if subtitle is not None else self.subtitle,
            bg=p.bg,
            fg=p.text_dim,
            font=self.fonts["small"],
        ).pack(anchor="w", pady=(3, 0))
        self.header_right = tk.Frame(row, bg=p.bg)
        self.header_right.pack(side="right")
        return row

    def scroll_page(self) -> tk.Frame:
        """Create a vertically scrollable container inside ``body``. Returns content frame."""
        p = self.palette
        outer = tk.Frame(self.body, bg=p.bg)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=p.bg, highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=p.bg)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _resize(_e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(window, width=canvas.winfo_width())

        inner.bind("<Configure>", _resize)
        canvas.bind("<Configure>", _resize)

        def _wheel(event):
            if event.delta:
                canvas.yview_scroll(int(-event.delta / 120) * 2, "units")

        def _enter(_e=None):
            self.winfo_toplevel().bind_all("<MouseWheel>", _wheel)

        def _leave(_e=None):
            self.winfo_toplevel().unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _enter)
        canvas.bind("<Leave>", _leave)
        return inner
