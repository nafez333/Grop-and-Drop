"""Design system: colour tokens, ttk theme, fonts and reusable widgets.

Tkinter/ttk is used instead of Qt so the app keeps its zero-extra-dependency
footprint (ttk ships with Python). ttk is a native-theme renderer, so a full
dark UI has to be built from explicitly styled elements - the styles registered
here are the single source of truth for the application's look.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

FONT_FAMILY = "Segoe UI"
FONT_MONO = "Consolas"


class Palette:
    """Semantic colour tokens for one appearance mode."""

    def __init__(self, dark: bool = True, accent: str = "violet"):
        accents = {
            "violet": "#7C5CFF",
            "teal": "#22D3B6",
            "amber": "#F5A524",
            "rose": "#FF6B8A",
        }
        accents_hover = {
            "violet": "#9478FF",
            "teal": "#38E6C8",
            "amber": "#FFB84D",
            "rose": "#FF8CA5",
        }
        accents_soft_dark = {
            "violet": "#2A2350",
            "teal": "#0F3B38",
            "amber": "#3D2E10",
            "rose": "#3D1D28",
        }
        accents_soft_light = {
            "violet": "#EEE9FF",
            "teal": "#D9FAF4",
            "amber": "#FFF2DB",
            "rose": "#FFE6EC",
        }
        self.accent_name = accent if accent in accents else "violet"
        self.accent = accents[self.accent_name]
        self.accent_hover = accents_hover[self.accent_name]
        self.accent_soft = (accents_soft_dark if dark else accents_soft_light)[
            self.accent_name
        ]
        self.dark = dark

        if dark:
            self.bg = "#0E0F13"  # app background
            self.bg_alt = "#13151B"  # sidebar / deep panels
            self.surface = "#181B22"  # cards
            self.surface_2 = "#1F232C"  # raised / hover
            self.surface_3 = "#272C37"  # pressed / inputs
            self.border = "#2A2F3A"
            self.border_soft = "#222630"
            self.text = "#F2F4F8"
            self.text_dim = "#A3A9B8"
            self.text_mute = "#6E7585"
            self.success = "#3DDC97"
            self.warning = "#F5A524"
            self.danger = "#FF5C6C"
            self.info = "#5AA9FF"
            self.track = "#262B35"
            self.overlay = "#000000"
        else:
            self.bg = "#F4F5F8"
            self.bg_alt = "#ECEEF3"
            self.surface = "#FFFFFF"
            self.surface_2 = "#F7F8FB"
            self.surface_3 = "#EEF0F5"
            self.border = "#DDE1E9"
            self.border_soft = "#E8EBF1"
            self.text = "#16181D"
            self.text_dim = "#565D6C"
            self.text_mute = "#8A91A1"
            self.success = "#18A86B"
            self.warning = "#D98A00"
            self.danger = "#E04355"
            self.info = "#2F7FE0"
            self.track = "#E4E7EE"
            self.overlay = "#FFFFFF"


def choose_fonts(root: tk.Misc, scale: float = 1.0) -> dict:
    """Register the named fonts used across the app."""

    def s(px: int) -> int:
        return max(8, int(round(px * scale)))

    fonts = {
        "display": tkfont.Font(
            root=root, family=FONT_FAMILY, size=s(22), weight="bold"
        ),
        "h1": tkfont.Font(root=root, family=FONT_FAMILY, size=s(16), weight="bold"),
        "h2": tkfont.Font(root=root, family=FONT_FAMILY, size=s(12), weight="bold"),
        "body": tkfont.Font(root=root, family=FONT_FAMILY, size=s(10)),
        "body_bold": tkfont.Font(
            root=root, family=FONT_FAMILY, size=s(10), weight="bold"
        ),
        "small": tkfont.Font(root=root, family=FONT_FAMILY, size=s(9)),
        "small_bold": tkfont.Font(
            root=root, family=FONT_FAMILY, size=s(9), weight="bold"
        ),
        "tiny": tkfont.Font(root=root, family=FONT_FAMILY, size=s(8)),
        "metric": tkfont.Font(root=root, family=FONT_FAMILY, size=s(20), weight="bold"),
        "mono": tkfont.Font(root=root, family=FONT_MONO, size=s(9)),
    }
    return fonts


class StyleManager:
    """Registers every ttk style the app uses. Re-runnable for theme switches."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.style = ttk.Style(root)
        self.style.theme_use("clam")
        self.palette = Palette()
        self.fonts = choose_fonts(root)

    def apply(self, palette: Palette, fonts: dict) -> None:
        self.palette = palette
        self.fonts = fonts
        p, s, f = palette, self.style, fonts

        self.root.configure(bg=p.bg)

        # ---------------------------------------------------------- containers
        s.configure(".", background=p.bg, foreground=p.text, font=f["body"])
        s.configure("TFrame", background=p.bg)
        s.configure("Alt.TFrame", background=p.bg_alt)
        s.configure("Card.TFrame", background=p.surface, relief="flat")
        s.configure("Card2.TFrame", background=p.surface_2, relief="flat")
        s.configure("Sidebar.TFrame", background=p.bg_alt)
        s.configure("Rail.TFrame", background=p.surface)

        s.configure("TLabel", background=p.bg, foreground=p.text, font=f["body"])
        s.configure("Card.TLabel", background=p.surface, foreground=p.text)
        s.configure(
            "CardDim.TLabel",
            background=p.surface,
            foreground=p.text_dim,
            font=f["small"],
        )
        s.configure(
            "CardMute.TLabel",
            background=p.surface,
            foreground=p.text_mute,
            font=f["small"],
        )
        s.configure(
            "CardTitle.TLabel", background=p.surface, foreground=p.text, font=f["h2"]
        )
        s.configure(
            "Display.TLabel", background=p.surface, foreground=p.text, font=f["display"]
        )
        s.configure(
            "Metric.TLabel", background=p.surface, foreground=p.text, font=f["metric"]
        )
        s.configure("Section.TLabel", background=p.bg, foreground=p.text, font=f["h1"])
        s.configure(
            "SectionDim.TLabel", background=p.bg, foreground=p.text_dim, font=f["small"]
        )
        s.configure(
            "Field.TLabel",
            background=p.surface,
            foreground=p.text_dim,
            font=f["small_bold"],
        )
        s.configure(
            "Help.TLabel", background=p.surface, foreground=p.text_mute, font=f["tiny"]
        )
        s.configure(
            "Error.TLabel", background=p.surface, foreground=p.danger, font=f["small"]
        )
        s.configure(
            "Accent.TLabel",
            background=p.surface,
            foreground=p.accent,
            font=f["small_bold"],
        )

        # ------------------------------------------------------------- buttons
        base = dict(
            font=f["body_bold"], borderwidth=0, focuscolor=p.bg, padding=(14, 8)
        )
        s.configure("TButton", background=p.surface_2, foreground=p.text, **base)
        s.map(
            "TButton",
            background=[
                ("disabled", p.surface_2),
                ("pressed", p.surface_3),
                ("active", p.surface_3),
            ],
            foreground=[("disabled", p.text_mute)],
        )

        s.configure("Accent.TButton", background=p.accent, foreground="#FFFFFF", **base)
        s.map(
            "Accent.TButton",
            background=[
                ("disabled", p.surface_2),
                ("pressed", p.accent_soft),
                ("active", p.accent_hover),
            ],
            foreground=[("disabled", p.text_mute)],
        )

        s.configure("Danger.TButton", background=p.danger, foreground="#FFFFFF", **base)
        s.map(
            "Danger.TButton", background=[("pressed", "#C93A48"), ("active", "#FF7080")]
        )

        s.configure(
            "Ghost.TButton",
            background=p.surface,
            foreground=p.text_dim,
            font=f["body_bold"],
            borderwidth=0,
            padding=(10, 6),
        )
        s.map(
            "Ghost.TButton",
            background=[("pressed", p.surface_3), ("active", p.surface_2)],
            foreground=[("active", p.text)],
        )

        s.configure(
            "Sidebar.TButton",
            background=p.bg_alt,
            foreground=p.text_dim,
            font=f["body_bold"],
            borderwidth=0,
            padding=(14, 10),
            anchor="w",
        )
        s.map(
            "Sidebar.TButton",
            background=[("active", p.surface_2), ("pressed", p.surface)],
            foreground=[("active", p.text)],
        )

        s.configure(
            "Chip.TButton",
            background=p.surface_3,
            foreground=p.text,
            font=f["small"],
            borderwidth=0,
            padding=(8, 5),
        )
        s.map("Chip.TButton", background=[("active", p.border)])

        # -------------------------------------------------------------- inputs
        s.configure(
            "TEntry",
            fieldbackground=p.surface_3,
            foreground=p.text,
            insertcolor=p.text,
            bordercolor=p.border,
            lightcolor=p.border,
            darkcolor=p.border,
            padding=(8, 6),
            borderwidth=1,
        )
        s.map(
            "TEntry",
            fieldbackground=[("focus", p.surface_3)],
            bordercolor=[("focus", p.accent)],
        )

        s.configure(
            "TCombobox",
            fieldbackground=p.surface_3,
            background=p.surface_3,
            foreground=p.text,
            arrowcolor=p.text_dim,
            bordercolor=p.border,
            lightcolor=p.border,
            darkcolor=p.border,
            padding=(8, 5),
        )
        self.root.option_add("*TCombobox*Listbox.background", p.surface_2)
        self.root.option_add("*TCombobox*Listbox.foreground", p.text)
        self.root.option_add("*TCombobox*Listbox.selectBackground", p.accent)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")
        self.root.option_add("*TCombobox*Listbox.font", f["body"])
        s.map(
            "TCombobox",
            fieldbackground=[("readonly", p.surface_3), ("disabled", p.surface_2)],
            foreground=[("disabled", p.text_mute)],
            bordercolor=[("focus", p.accent)],
        )

        s.configure(
            "TCheckbutton",
            background=p.surface,
            foreground=p.text,
            font=f["body"],
            focuscolor=p.surface,
            indicatorcolor=p.surface_3,
        )
        s.map(
            "TCheckbutton",
            background=[("active", p.surface)],
            indicatorcolor=[("selected", p.accent), ("active", p.surface_2)],
        )
        s.configure(
            "TSwitch.TCheckbutton",
            background=p.surface,
            foreground=p.text,
            font=f["body"],
        )

        # ------------------------------------------------------------ sliders
        s.configure(
            "Horizontal.TScale",
            background=p.surface,
            troughcolor=p.track,
            bordercolor=p.surface,
            lightcolor=p.surface,
            darkcolor=p.surface,
        )
        s.map("Horizontal.TScale", background=[("active", p.surface)])

        # ------------------------------------------------------------- scroll
        s.configure(
            "Vertical.TScrollbar",
            background=p.surface_2,
            troughcolor=p.bg,
            bordercolor=p.bg,
            arrowcolor=p.text_mute,
            arrowsize=12,
            lightcolor=p.surface_2,
            darkcolor=p.surface_2,
        )
        s.map("Vertical.TScrollbar", background=[("active", p.surface_3)])

        s.configure("TSeparator", background=p.border_soft)

        # ----------------------------------------------------------- notebook
        s.configure("TNotebook", background=p.bg, borderwidth=0)
        s.configure(
            "TNotebook.Tab",
            background=p.bg,
            foreground=p.text_dim,
            padding=(12, 8),
            font=f["small_bold"],
            borderwidth=0,
        )
        s.map(
            "TNotebook.Tab",
            background=[("selected", p.surface)],
            foreground=[("selected", p.text)],
        )

        # ------------------------------------------------------------- progress
        s.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor=p.track,
            background=p.accent,
            bordercolor=p.surface,
            lightcolor=p.accent,
            darkcolor=p.accent,
            thickness=6,
        )
        s.configure(
            "Success.Horizontal.TProgressbar",
            troughcolor=p.track,
            background=p.success,
            bordercolor=p.surface,
            lightcolor=p.success,
            darkcolor=p.success,
            thickness=6,
        )
