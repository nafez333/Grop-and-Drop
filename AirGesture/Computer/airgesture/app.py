"""Main application window: sidebar, page router, engine lifecycle, thread marshalling."""
from __future__ import annotations

import os
import sys
import time
import tkinter as tk
import tkinter.messagebox as mbox
import traceback
from typing import Optional

from .core.settings import SettingsManager
from .core.recognizer import GESTURES
from .runtime.engine import EngineThread
from .runtime.mouse_controller import MouseController, MouseConfig, MouseError
from .ui.i18n import tr, get_language, set_language, ARABIC, ENGLISH
from .ui.theme import Palette, StyleManager, choose_fonts
from .ui.widgets import Toast, StatusPill, palette_font
from .ui.icons import draw_icon
from .ui.pages.base import Page
from .ui.pages.dashboard import DashboardPage
from .ui.pages.gestures import GesturesPage
from .ui.pages.calibration import CalibrationPage
from .ui.pages.mouse_settings import MouseSettingsPage
from .ui.pages.camera_settings import CameraSettingsPage
from .ui.pages.appearance import AppearancePage
from .ui.pages.help_page import HelpPage

PAGE_ORDER = [
    ("dashboard", tr("Dashboard"), "dashboard"),
    ("gestures", tr("Gestures"), "gestures"),
    ("calibration", tr("Calibration"), "calibration"),
    ("mouse", tr("Mouse"), "mouse"),
    ("camera", tr("Camera"), "camera"),
    ("appearance", tr("Appearance"), "appearance"),
    ("help", tr("Help"), "help"),
]


class AirGestureApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # ------------------------------------------------------- window frame
        self.title(tr("AirGesture"))
        self.geometry("1280x800")
        self.minsize(1080, 680)
        self.configure(bg="#0E0F13")

        # window icon: 16×16 hand glyph on a Canvas, then set as iconphoto
        self._icon_canvas = tk.Canvas(self, width=16, height=16, bg="#0E0F13",
                                      highlightthickness=0, bd=0)
        self._icon_canvas.update_idletasks()
        draw_icon(self._icon_canvas, "hand", 8, 8, 12, "#7C5CFF")

        # ------------------------------------------------------ palette / fonts
        self.palette = Palette(dark=True, accent="violet")
        self.fonts = choose_fonts(self, 1.0)
        self.ag_fonts = self.fonts
        self.style = StyleManager(self)
        self.style.apply(self.palette, self.fonts)

        # ------------------------------------------------------ services
        self.settings = SettingsManager()
        try:
            self.mouse = MouseController(MouseConfig())
        except MouseError as exc:
            mbox.showerror("AirGesture — fatal error",
                           f"PyAutoGUI is required for mouse control:\n{exc}")
            self.destroy()
            raise

        self.engine = EngineThread(
            self.settings, self.mouse,
            self._on_frame, self._on_status,
        )

        self._pages: dict[str, Page] = {}
        self._current_page: Optional[str] = None
        self._last_packet = None
        self._last_delivered = None
        self._closing = False
        self._pending_settings: list[tuple[str, str]] = []
        self._status_text = ""
        self._delivered_status = ""
        self._engine_error_shown = False
        self._toast: Optional[Toast] = None
        self._last_status = "idle"

        self._build_layout()
        self._bind_keys()

        # settings subscription (marshalled to Tk thread)
        self.settings.subscribe(self._on_settings_changed)

        # ------------------------------------------------------ startup
        self.engine.start(start_control=False)
        if self.settings.get("general", "auto_start_control", False):
            self.start_control()
        if self.settings.get("general", "start_minimized", False):
            self.after(200, self.iconify)

        # Both pumps run on the Tk thread only (see _on_frame).
        self._start_frame_pump()
        self._drain_status()
        self._drain_settings()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -------------------------------------------------------------- layout
    def _build_layout(self) -> None:
        p = self.palette

        # top bar
        self.top_bar = tk.Frame(self, bg=p.bg_alt, height=52)
        self.top_bar.pack(side="top", fill="x")
        self.top_bar.pack_propagate(False)

        self.breadcrumb = tk.Label(self.top_bar, text=tr("Dashboard"), bg=p.bg_alt,
                                   fg=p.text, font=palette_font(self, "h2"))
        self.breadcrumb.pack(side="left", padx=(18, 0), pady=14)

        # Language selector
        self.lang_var = tk.StringVar(value=get_language())
        lang_menu = tk.OptionMenu(self.top_bar, self.lang_var, ARABIC, ENGLISH,
                                  command=self._set_language)
        lang_menu.pack(side="right", padx=(0, 14))

        right = tk.Frame(self.top_bar, bg=p.bg_alt)
        right.pack(side="right", padx=(0, 14))

        self.btn_estop = tk.Frame(right, bg=p.danger, cursor="hand2")
        self.btn_estop.pack(side="right", padx=(8, 0), pady=8)
        elbl = tk.Label(self.btn_estop, text=tr("Emergency stop"), bg=p.danger, fg="#FFFFFF",
                        font=palette_font(self, "body_bold"), padx=12, pady=6)
        elbl.pack()
        for w in (self.btn_estop, elbl):
            w.bind("<Button-1>", lambda _e: self.emergency_stop())

        self.btn_folder = tk.Frame(right, bg=p.surface_2, cursor="hand2")
        self.btn_folder.pack(side="right", padx=(8, 0), pady=8)
        flbl = tk.Label(self.btn_folder, text=tr("Settings folder"), bg=p.surface_2, fg=p.text,
                        font=palette_font(self, "body_bold"), padx=10, pady=6)
        flbl.pack()
        for w in (self.btn_folder, flbl):
            w.bind("<Button-1>", lambda _e: self._open_settings_folder())

        self.btn_min = tk.Frame(right, bg=p.surface_2, cursor="hand2")
        self.btn_min.pack(side="right", padx=(0, 0), pady=8)
        mlbl = tk.Label(self.btn_min, text=tr("−"), bg=p.surface_2, fg=p.text_dim,
                        font=palette_font(self, "body_bold"), padx=10, pady=6)
        mlbl.pack()
        for w in (self.btn_min, mlbl):
            w.bind("<Button-1>", lambda _e: self.iconify())

        # main container: sidebar + page area
        main = tk.Frame(self, bg=p.bg)
        main.pack(side="top", fill="both", expand=True)

        # sidebar
        self.sidebar = tk.Frame(main, bg=p.bg_alt, width=232)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # logo + title
        logo = tk.Frame(self.sidebar, bg=p.bg_alt)
        logo.pack(fill="x", padx=16, pady=(20, 10))
        self.logo_canvas = tk.Canvas(logo, width=22, height=22, bg=p.bg_alt,
                                     highlightthickness=0, bd=0)
        self.logo_canvas.pack(side="left", padx=(0, 8))
        draw_icon(self.logo_canvas, "hand", 11, 11, 16, p.accent)
        ttl = tk.Label(logo, text="AirGesture", bg=p.bg_alt, fg=p.text,
                       font=("Segoe UI", 13, "bold"))
        ttl.pack(side="left")
        ver = tk.Label(logo, text="v2.0.0", bg=p.bg_alt, fg=p.text_mute,
                       font=("Segoe UI", 8))
        ver.pack(side="left", padx=(6, 0))

        # page buttons
        self.page_buttons: dict[str, tk.Frame] = {}
        for key, label, icon_name in PAGE_ORDER:
            btn = tk.Frame(self.sidebar, bg=p.bg_alt, cursor="hand2")
            btn.pack(fill="x", padx=10, pady=2)
            cv = tk.Canvas(btn, width=18, height=18, bg=p.bg_alt,
                           highlightthickness=0, bd=0)
            cv.pack(side="left", padx=(12, 8), pady=8)
            draw_icon(cv, icon_name, 9, 9, 14, p.text_dim)
            lbl = tk.Label(btn, text=label, bg=p.bg_alt, fg=p.text_dim,
                           font=("Segoe UI", 10, "bold"))
            lbl.pack(side="left")
            for w in (btn, cv, lbl):
                w.bind("<Button-1>", lambda _e, k=key: self.show_page(k))
            self.page_buttons[key] = btn

        # sidebar bottom: status pill + start control
        self.sidebar_bottom = tk.Frame(self.sidebar, bg=p.bg_alt)
        self.sidebar_bottom.pack(side="bottom", fill="x", padx=10, pady=(0, 16))

        self.status_pill = StatusPill(self.sidebar_bottom, p, "Engine", "muted",
                                      width=190, height=26)
        self.status_pill.pack(fill="x", pady=(0, 8))

        self.btn_start_ctrl = tk.Frame(self.sidebar_bottom, bg=p.accent, cursor="hand2")
        self.btn_start_ctrl.pack(fill="x", pady=(0, 2))
        slbl = tk.Label(self.btn_start_ctrl, text=tr("Start control"), bg=p.accent, fg="#FFFFFF",
                        font=palette_font(self, "body_bold"), padx=14, pady=8)
        slbl.pack()
        for w in (self.btn_start_ctrl, slbl):
            w.bind("<Button-1>", lambda _e: self.start_control())

        # page area
        self.page_area = tk.Frame(main, bg=p.bg)
        self.page_area.pack(side="left", fill="both", expand=True)

        # create all pages eagerly, gridded in same cell
        page_classes = {
            "dashboard": DashboardPage,
            "gestures": GesturesPage,
            "calibration": CalibrationPage,
            "mouse": MouseSettingsPage,
            "camera": CameraSettingsPage,
            "appearance": AppearancePage,
            "help": HelpPage,
        }
        for key, label, _icon in PAGE_ORDER:
            cls = page_classes[key]
            page = cls(self.page_area, self)
            page.place(x=0, y=0, relwidth=1, relheight=1)
            self._pages[key] = page

        self.show_page("dashboard")

        # toast
        self._toast = Toast(self, p)
        self._toast.place(relx=1.0, rely=1.0, anchor="se", x=-18, y=-18)
        self._toast.place_forget()

    # -------------------------------------------------------------- page router
    def show_page(self, name: str) -> None:
        if name not in self._pages:
            return
        if self._current_page is not None:
            old = self._pages[self._current_page]
            try:
                old.on_hide()
            except Exception:
                pass
        self._current_page = name
        new = self._pages[name]
        new.tkraise()
        # update sidebar highlights
        for key, btn in self.page_buttons.items():
            active = key == name
            p = self.palette
            for child in btn.winfo_children():
                try:
                    if isinstance(child, tk.Canvas):
                        draw_icon(child, _icon_for(key), 9, 9, 14,
                                  p.accent if active else p.text_dim)
                    elif isinstance(child, tk.Label):
                        child.configure(fg=p.text if active else p.text_dim,
                                        bg=p.surface_2 if active else p.bg_alt)
                except tk.TclError:
                    pass
            btn.configure(bg=p.surface_2 if active else p.bg_alt)
        self.breadcrumb.configure(text=_label_for(name))
        try:
            new.on_show()
        except Exception:
            pass

    def refresh_pages(self, section: str, key: str) -> None:
        for page in self._pages.values():
            try:
                page.on_settings(section, key)
            except Exception:
                pass

    # -------------------------------------------------------------- engine bridge
    def _on_frame(self, packet) -> None:
        """Called from the engine thread — never touch Tk here."""
        # NOTE: ``self.after`` is NOT thread-safe in Tkinter. Calling it from
        # the engine thread could raise silently, which left the UI showing a
        # frozen first frame (or nothing) forever. The engine only stores the
        # newest packet; a single periodic poller on the Tk thread reads it.
        self._last_packet = packet

    def _start_frame_pump(self) -> None:
        """Single ~30 fps poller that renders on the Tk thread."""
        if self._closing:
            return
        pkt = self._last_packet
        if pkt is not None and pkt is not self._last_delivered:
            self._last_delivered = pkt
            if self._current_page is not None:
                page = self._pages.get(self._current_page)
                if page is not None:
                    try:
                        page.on_frame(pkt)
                    except Exception:
                        traceback.print_exc()
        # A camera/engine error is fatal for the preview but not for the app:
        # show it instead of leaving the panel on "Starting camera...".
        elif pkt is None and self.engine and not self.engine.running and not self._engine_error_shown:
            self._engine_error_shown = True
            page = self._pages.get("dashboard")
            if page is not None and hasattr(page, "cam_panel"):
                page.cam_panel.set_placeholder(
                    "Camera unavailable. Open the Camera page to select a device "
                    "or press Restart camera."
                )
        self.after(33, self._start_frame_pump)

    def _on_status(self, status: str, message: str) -> None:
        """Called from the engine thread — only store, never touch Tk."""
        self._last_status = status
        self._status_text = message

    def _drain_status(self) -> None:
        """Tk thread: refresh the sidebar pill from the last engine status."""
        if self._closing:
            return
        self.status_pill.set(self._status_text or "Idle", self._status_tone())
        if self._status_text and self._status_text != self._delivered_status:
            self._delivered_status = self._status_text
            if self._current_page is not None:
                page = self._pages.get(self._current_page)
                if page is not None:
                    try:
                        page.on_engine_status(self._last_status, self._status_text)
                    except Exception:
                        traceback.print_exc()
        self.after(400, self._drain_status)

    def _status_tone(self) -> str:
        txt = self._status_text.lower()
        if "error" in txt or "emergency" in txt:
            return "error"
        if "warn" in txt:
            return "warn"
        if "on" in txt or "ready" in txt or "streaming" in txt:
            return "ok"
        return "muted"

    def _set_language(self, *args) -> None:
        """Handle language selection change from the UI menu."""
        lang = self.lang_var.get()
        set_language(lang)
        # Refresh all visible text
        self.breadcrumb.configure(text=tr("Dashboard"))

    def _refresh_all_text(self) -> None:
        """Refresh all UI text when language changes.

        This iterates through known widgets and updates their displayed text
        using the current language translation function.
        """
        try:
            self.breadcrumb.configure(text=tr("Dashboard"))
        except Exception:
            pass

    # -------------------------------------------------------------- settings
    def _on_settings_changed(self, section: str, key: str) -> None:
        """May be called from any thread. Tk is not touched here."""
        self._pending_settings.append((section, key))

    def _drain_settings(self) -> None:
        """Tk thread: apply queued settings changes to pages and the engine."""
        if self._closing:
            return
        pending, self._pending_settings = self._pending_settings, []
        for section, key in pending:
            for page in self._pages.values():
                try:
                    page.on_settings(section, key)
                except Exception:
                    traceback.print_exc()
            self.engine.submit("reload")
        self.after(120, self._drain_settings)

    # -------------------------------------------------------------- control
    def start_control(self) -> None:
        if not self.engine.running:
            # First attempt may be recovering from a camera failure.
            self.engine.start(start_control=False)
        self.engine.set_control(True)
        self.toast.show("Mouse control ON", "ok")

    def stop_control(self) -> None:
        self.engine.set_control(False)
        self.toast.show("Mouse control OFF", "info")

    def pause_tracking(self) -> None:
        self.engine.pause_tracking(not self._is_paused())
        self.toast.show("Tracking paused", "warn")

    def _is_paused(self) -> bool:
        pkt = self.engine.latest()
        return bool(getattr(pkt, "paused", False))

    def emergency_stop(self) -> None:
        self.engine.emergency_stop()
        self.mouse.release_all()
        self.toast.show("Emergency stop — all mouse buttons released", "error")

    def restart_engine(self) -> None:
        self.engine.stop(timeout=3.0)
        self.engine.start(start_control=False)

    def open_learning(self, gesture_id: str, cb) -> None:
        from .ui.learning import LearningDialog
        LearningDialog(self, self, gesture_id, cb)

    def active_gesture_count(self) -> int:
        gestures = self.settings.section("gestures")
        return sum(1 for gid in GESTURES if gestures.get(gid, {}).get("enabled", False))

    def apply_theme(self) -> None:
        dark = self.settings.get("general", "appearance", "dark") == "dark"
        accent = self.settings.get("general", "accent", "violet")
        scale = float(self.settings.get("general", "ui_scale", 1.0))
        self.palette = Palette(dark=dark, accent=accent)
        self.fonts = choose_fonts(self, scale)
        self.ag_fonts = self.fonts
        self.style.apply(self.palette, self.fonts)
        # rebuild sidebar + pages
        self._rebuild_ui()

    def _rebuild_ui(self) -> None:
        # simplest reliable way in Tk: destroy and recreate sidebar + pages
        for page in self._pages.values():
            page.destroy()
        self._pages.clear()
        self.sidebar.destroy()
        self.top_bar.destroy()
        self.page_area.destroy()
        self._build_layout()

    # -------------------------------------------------------------- toast
    def toast(self, message: str, tone: str = "info") -> None:
        if self._toast is not None:
            self._toast.show(message, tone)

    # -------------------------------------------------------------- keyboard
    def _bind_keys(self) -> None:
        self.bind("<F9>", lambda _e: self.start_control())
        self.bind("<F10>", lambda _e: self.stop_control())
        self.bind("<Escape>", lambda _e: self.emergency_stop())
        self.bind("<Control-t>", lambda _e: self.pause_tracking())
        self.bind("<Control-1>", lambda _e: self.show_page("dashboard"))
        self.bind("<Control-2>", lambda _e: self.show_page("gestures"))
        self.bind("<Control-3>", lambda _e: self.show_page("calibration"))
        self.bind("<Control-4>", lambda _e: self.show_page("mouse"))
        self.bind("<Control-5>", lambda _e: self.show_page("camera"))
        self.bind("<Control-6>", lambda _e: self.show_page("appearance"))
        self.bind("<Control-7>", lambda _e: self.show_page("help"))

    # -------------------------------------------------------------- close
    def _on_close(self) -> None:
        if self._closing:
            return
        self._closing = True
        try:
            self.engine.stop(timeout=2.0)
            self.mouse.release_all()
            self.settings.save()
        finally:
            self.destroy()

    # -------------------------------------------------------------- misc
    def _open_settings_folder(self) -> None:
        try:
            os.startfile(os.path.dirname(self.settings.path))
        except Exception:
            pass


def main() -> int:
    try:
        app = AirGestureApp()
        app.mainloop()
        return 0
    except Exception as exc:  # pragma: no cover - top-level safety net
        try:
            mbox.showerror("AirGesture — fatal error", str(exc))
        except Exception:
            print(f"Fatal error: {exc}", file=sys.stderr)
        return 1


# -------------------------------------------------------------- helpers
def _icon_for(key: str) -> str:
    return {
        "dashboard": "dashboard",
        "gestures": "gestures",
        "calibration": "calibration",
        "mouse": "mouse",
        "camera": "camera",
        "appearance": "appearance",
        "help": "help",
    }[key]


def _label_for(key: str) -> str:
    return {
        "dashboard": tr("Dashboard"),
        "gestures": tr("Gestures"),
        "calibration": tr("Calibration"),
        "mouse": tr("Mouse"),
        "camera": tr("Camera"),
        "appearance": tr("Appearance"),
        "help": tr("Help"),
    }[key]