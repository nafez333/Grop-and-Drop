# Handoff Prompt — Finish the AirGesture 2.0 Rebuild

You are a senior Windows desktop developer (Python, Tkinter/ttk, MediaPipe, OpenCV, PyAutoGUI).
A rebuild of the project **AirGesture** (hand-gesture mouse control) is already ~70% complete.
Your job is to finish it exactly as specified below. Work only inside:

```
c:\Users\CMC\Desktop\Grop and Drop\AirGesture\Computer\
```

Runtime: Windows, **Python 3.13.15** (Windows PowerShell 5.1 — no `&&`, no `||`, no ternary).
Installed and working: `mediapipe 1.2.3`, `opencv-contrib-python 5.1.0`, `numpy 2.5.3`,
`Pillow 12.3.0`, `PyAutoGUI 0.9.54`, `tkinter 8.6.15`. A camera on index 0 works (1280×720).
**Do NOT add dependencies. Do NOT use PySide/PyQt. Do NOT add cloud/Wi-Fi/Bluetooth/Android features.**
No fake buttons, no simulated recognition results, never claim something works without testing it.

---

## 1. Target architecture (already agreed — keep it)

```
AirGesture/Computer/
  hand_landmarker.task            # existing MediaPipe model (do not touch)
  main.py                         # ENTRY POINT -> launches airgesture.app (rewrite, thin)
  requirements.txt                # must be created
  airgesture/
    __init__.py                   # DONE (APP_NAME, __version__ = "2.0.0")
    core/                         # pure logic, no cv2/mediapipe/UI — unit testable
      __init__.py                 # DONE
      geometry.py                 # DONE
      pose.py                     # DONE  (HandPose feature set)
      recognizer.py               # DONE  (rule-based, scale/rotation invariant)
      stabilizer.py               # DONE  (hysteresis + confidence + dropout tolerance)
      settings.py                 # DONE  (JSON SettingsManager, validation, defaults)
    runtime/                      # hardware / OS services
      __init__.py                 # DONE
      camera_manager.py           # DONE
      tracking.py                 # DONE  (MediaPipe + One-Euro filter + draw_hand)
      mouse_controller.py         # DONE  (mapping, smoothing, jump guard, safe buttons)
      interaction.py              # DONE  (state machine: gesture -> safe mouse action)
      engine.py                   # DONE  (worker thread, frame packets, commands)
    ui/
      __init__.py                 # DONE
      theme.py                    # DONE  (Palette, StyleManager)  <- imports CHOOSE_FONTS from same file
      widgets.py                  # DONE  (Card, StatusPill, SliderField, ToggleRow, Switch,
                                  #        SegmentedControl, GestureGlyph, Toast, KeyValueRow)
      icons.py                    # DONE  (draw_icon, IconButton)
      camera_panel.py             # DONE  (Canvas video renderer + HUD)
      learning.py                 # DONE  (LearningDialog — live capture gesture learning)
      pages/
        __init__.py               # MISSING  -> create (empty docstring module)
        base.py                   # DONE  (Page base: header(), scroll_page(), hooks)
        dashboard.py              # DONE
        gestures.py               # DONE
        calibration.py            # TODO
        mouse_settings.py         # TODO
        camera_settings.py        # TODO
        appearance.py             # TODO
        help_page.py              # TODO
    app.py                        # TODO  (main window: sidebar, page router, engine lifecycle)
```

Legacy files that must be kept but made harmless (they are imported by nothing after `main.py` is rewritten;
MediPipe-style API only): `hand_tracking.py`, `gesture_classifier.py`, `mouse_controller.py`, `main.py`.
**Replace `hand_tracking.py` and `gesture_classifier.py` with thin re-export shims** so old scripts still
run, e.g. `from airgesture.runtime.tracking import HandTracker` etc. `mouse_controller.py` (root) -> shim
to `airgesture.runtime.mouse_controller.MouseController`.

---

## 2. What the existing modules already provide (API you must build on)

### `airgesture.core.settings`
`SettingsManager(path=None, autosave=True)`, persisted to `%APPDATA%\AirGesture\settings.json`, version 2.
- `get(section, key, default=None)`, `set(section, key, value, save=None)` (auto-clamps + validates), `section(name) -> dict` (deep copy), `snapshot()`
- `gesture(gid) -> dict`, `update_gesture(gid, action=..., enabled=..., sensitivity=..., activation_delay=..., cooldown=..., learned_confidence=...)`
- `reset_gestures()`, `reset_all()`, `subscribe(cb)` where `cb(section, key)`
- Sections: `general` (start_minimized, auto_start_control, show_overlay, appearance: dark|light|system, accent: violet|teal|amber|rose, ui_scale 0.85–1.25),
  `camera` (index, width, height, fps, mirror, detection_confidence, tracking_confidence),
  `tracking` (handedness: any|left|right, distance_filter, velocity_beta),
  `mouse` (sensitivity 0.3–3.5, speed, smoothing 0–0.95, active_area_x, active_area_y, acceleration, jump_guard, deadzone, scroll_speed, natural_scroll, position_mode: absolute|relative),
  `interaction` (mode: auto|active|always, tracking_lost_timeout, pause_grace, click_armed_timeout),
  `gestures` (per gesture: action, enabled, sensitivity, activation_delay, cooldown, learned_confidence),
  `calibration` (active_area {x0,y0,x1,y1}, screen_margin, completed, cursor_scale)

### `airgesture.core.recognizer`
`GESTURES = (open_palm, fist, index_only, pinch, two_fingers, three_fingers, four_fingers)`,
`GESTURE_LABELS`, `GESTURE_HINTS`, `ACTIONS = (move,left_click,right_click,double_click,drag,scroll,pause,none)`,
`ACTION_LABELS`, `UNKNOWN`, `GestureRecognizer(sensitivity).recognize(pose) -> Detection(gesture, score, candidates)`.
Default profile (in settings): open_palm→move, pinch→left_click, two_fingers→right_click,
three_fingers→double_click, fist→pause (disabled by default: `four_fingers`, `index_only`).

### `airgesture.runtime.engine.EngineThread`
```python
EngineThread(settings, mouse, on_frame: Callable[[FramePacket], None], on_status: Callable[[str, str], None])
engine.start(start_control: bool = False); engine.stop(timeout=3.0)
engine.set_control(bool); engine.emergency_stop(); engine.pause_tracking(bool); engine.set_mode("auto"|"active"|"always")
engine.submit("reload")   # MUST be called after any camera/tracking/mouse/gesture settings change
engine.request_capture(seconds)   # result delivered to engine.on_capture_done = cb(list[HandPose])
engine.latest() -> FramePacket
```
`FramePacket`: `frame` (BGR ndarray or None), `gesture`, `gesture_label`, `confidence`, `handedness`,
`action`, `active`, `dragging`, `paused`, `mode`, `fps`, `frame_ms`, `status`, `message`, `error`, `timestamp`.
`on_frame` / `on_status` are called **from the engine thread** — never touch Tk there.
The UI must marshal via `root.after(...)`.

### `airgesture.runtime.mouse_controller`
`MouseController(config: MouseConfig)`, `.map_to_screen(nx, ny)`, `.move_to(nx, ny)`, `.click(button, double)`,
`.start_drag()`, `.end_drag()`, `.scroll(amount)`, `.release_all()`, `.screen_w/.screen_h`, `.position()`.

### `airgesture.ui.theme`
`Palette(dark=True, accent="violet")` (attributes: bg, bg_alt, surface, surface_2, surface_3, border,
border_soft, text, text_dim, text_mute, success, warning, danger, info, track, accent, accent_hover,
accent_soft, dark), `choose_fonts(root, scale) -> dict` with keys display/h1/h2/body/body_bold/small/
small_bold/tiny/metric/mono, `StyleManager(root).apply(palette, fonts)`.

### `airgesture.ui.pages.base.Page`
Subclass, set `title`/`subtitle`, implement `build()`. Optional hooks: `on_show`, `on_hide`,
`on_frame(packet)`, `on_settings(section, key)`, `on_engine_status(status, message)`.
Helpers: `self.header()`, `self.header_right`, `self.body`, `self.scroll_page() -> tk.Frame`.
`self.app` gives: `app.palette`, `app.fonts`, `app.settings`, `app.engine`, `app.mouse`,
`app.show_page(name)`, `app.refresh_pages(section, key)`, `app.start_control()`, `app.stop_control()`,
`app.pause_tracking()`, `app.emergency_stop()`, `app.open_learning(gesture_id, callback)`,
`app.active_gesture_count()`, `app.apply_theme()`, `app.toast(message, tone)`.

---

## 3. Remaining tasks (do them in this order)

### T1 — `airgesture/ui/pages/__init__.py`
Empty module docstring (`"""Pages."""`).

### T2 — `airgesture/ui/pages/mouse_settings.py` (`MouseSettingsPage`)
Card "Cursor movement" with `SliderField`s bound to `settings.get("mouse", ...)` and on change
`settings.set("mouse", key, value)` + `engine.submit("reload")`:
sensitivity (0.3–3.5), speed (0.2–3.0), smoothing (0–0.95), acceleration (0–1),
active_area_x / active_area_y (0.2–0.95; label them "Active area width/height"),
deadzone (0–0.03, show as %), jump_guard (0.02–0.4, show as %), scroll_speed (0.2–4),
`ToggleRow` natural_scroll, `SegmentedControl` position_mode (absolute / relative).
Card "Live test": big centered target area + a "»" marker showing `mouse.map_to_screen(latest palm_xy)`
normalised into the card; a **"Test centre click"** button calling `app.mouse.click("left")` — it must
really click, so warn in the description. Read-only line with detected screen size.
Add a "Reset mouse settings" button -> `settings.reset_all()` is NOT allowed (wipes gestures); instead
write the default values back one by one from `airgesture.core.settings.defaults()`.

### T3 — `airgesture/ui/pages/camera_settings.py` (`CameraSettingsPage`)
- Device combo populated by `CameraManager.probe()` run **in a background thread** (results via
  `root.after`), fallback `Camera 0`.
- Resolution combo (640×480, 1280×720, 1920×1080), FPS slider (10–60), mirror `ToggleRow`,
  detection/tracking confidence sliders, handedness `SegmentedControl` (any / left / right).
- Buttons: **"Apply & restart camera"** -> save `camera`+`tracking` settings then
  `app.restart_engine()` (implement in app.py: `engine.stop(); engine.start(...)`), **"Test camera"**
  that opens via `CameraManager` directly for 1 s and reports success/failure (no engine interference).
- Show `camera.last_error` when present.

### T4 — `airgesture/ui/pages/calibration.py` (`CalibrationPage`)
A **real** guided wizard, 5 steps, no fake data:
1. **Camera check** — engine running + frame arriving + no `packet.error`.
2. **Position** — user holds an open palm; require 25 consecutive frames with `packet.gesture`
   == open_palm and `palm_xy` inside 0.2–0.8 in x and y; show a live `<progress>` bar.
3. **Active area** — user moves their hand to the 4 corners of their comfortable range in order
   (top-left, top-right, bottom-right, bottom-left). For each corner collect the `palm_xy` for 0.7 s
   (min 10 frames), average it. Compute `active_area = {x0=min(xs), y0=min(ys), x1=max(xs), y1=max(ys)}`,
   enforce min span 0.25, clamp inside 0..1, then `settings.set("calibration","active_area", area)` +
   `engine.submit("reload")`.
4. **Cursor sensitivity** — slider (0.5–2.5) mapped into `mouse.sensitivity`, applied live so the user
   can try it immediately.
5. **Practice** — checkbox checklist ("I moved the cursor", "I left-clicked with a pinch",
   "I right-clicked with two fingers") -> on "Finish", `settings.set("calibration","completed", True)`,
   write `mouse` sensitivity, `engine.submit("reload")`, show a completion card.
Every step must be skippable (`Skip step`), and `Back`/`Next` must work. Bind a derived
`interaction` helper `app.calibration` is NOT required — keep state inside the page.
Also a "Restore default active area" button (0.18, 0.15, 0.82, 0.85).

### T5 — `airgesture/ui/pages/appearance.py` (`AppearancePage`)
- Theme: `SegmentedControl` dark / light / system (`general.appearance`) — "system" resolves to dark on
  Windows (state this in the description; do not pretend to read the OS theme).
- Accent: 4 swatch buttons (violet/teal/amber/rose) writing `general.accent`.
- UI scale slider 0.85–1.25 writing `general.ui_scale`.
- Toggle "Show tracking overlay in preview" (`general.show_overlay`) and "Start with Windows control
  active" (`general.auto_start_control`) and "Start minimized" (`general.start_minimized`).
- Any change calls `app.apply_theme()`. A "Reset appearance" button restores defaults for `general` only.

### T6 — `airgesture/ui/pages/help_page.py` (`HelpPage`)
Real content, generated from the current settings (not hard-coded duplicates that can drift):
- "Getting started" 5 numbered steps.
- "Your gestures" table: for each **enabled** gesture -> `GestureGlyph`, name, bound action, hint,
  activation delay + cooldown.
- "Safety": emergency stop button, PyAutoGUI corner failsafe, automatic button release on stop /
  hand lost, pause behaviour.
- "Troubleshooting" sections: camera not found, hand not detected, cursor jittery (lower sensitivity /
  increase smoothing), accidental clicks (increase activation delay), light background.
- A button "Open settings folder" that opens `%APPDATA%\AirGesture` via `os.startfile`.
- Keyboard shortcuts of the app (see T7).

### T7 — `airgesture/app.py` (main window) — the biggest remaining piece
```python
class AirGestureApp(tk.Tk)
```
Requirements:
- 1280×800 default, min 1080×680, dark background, title "AirGesture", window icon drawn on a Canvas →
  `iconphoto` (16×16 hand glyph).
- `self.palette`, `self.fonts` set **before** creating anything; expose them on the Tk root
  (`self.ag_fonts = self.fonts`) because `widgets.palette_font()` looks them up there.
- `self.settings = SettingsManager()`, `self.mouse = MouseController(...)` (catch `MouseError` and show a
  fatal dialog instead of crashing), `self.engine = EngineThread(self.settings, self.mouse, self._on_frame,
  self._on_status)`.
- **Left sidebar (width 232):** app logo (Canvas glyph) + "AirGesture" + version, then page buttons with
  `icons.draw_icon` + label, highlight the active one; bottom block: status pill (Engine status) and
  "Start control" accent button. Pages, in order: Dashboard, Gestures, Calibration, Mouse, Camera,
  Appearance, Help.
- **Top bar** (`height 52`): breadcrumb = page title, right side: emergency-stop button (always visible,
  danger), settings folder button, minimize. Keep it minimal.
- **Page router:** create all pages eagerly in a dict, `grid` them all in the same cell, `tkraise()` the
  active one. `show_page(name)` calls `on_hide` on the old page and `on_show` on the new one.
- **Thread marshalling:** `_on_frame(pkt)` (engine thread) must only store `self._last_packet = pkt` and
  schedule a single pending `self.after(0, self._drain_frames)` (guard with a flag so at most one
  callback is queued). `_drain_frames` delivers the latest packet to the current page's `on_frame` and
  is scheduled again with `after(33, ...)` (≈30 fps UI). Same for `_on_status` -> marshal via `after`.
- **Settings subscription:** `self.settings.subscribe(self._on_settings_changed)` — must marshal into the
  Tk thread with `after(0, ...)`, then call each page's `on_settings(section, key)` and
  `self.engine.submit("reload")` for hardware-related sections (camera, tracking, mouse, interaction,
  gestures, calibration).
- **Methods:** `start_control()` (starts engine if stopped, then `set_control(True)`), `stop_control()`,
  `pause_tracking()` (toggles `pause_tracking`), `emergency_stop()` (engine.emergency_stop(); must always
  release buttons; also `self.mouse.release_all()` on the UI thread as a second net; show a toast),
  `restart_engine()`, `open_learning(gid, cb)` -> `LearningDialog(self, self, gid, cb)`,
  `refresh_pages(section, key)`, `active_gesture_count()`, `apply_theme()` (rebuild `Palette` +
  `choose_fonts` from settings, `StyleManager.apply`, then rebuild the sidebar/pages by destroying and
  recreating them — the simplest reliable way in Tk; keep the engine untouched).
- **Keyboard shortcuts:** `F9` start control, `F10` stop control, `Esc` emergency stop, `Ctrl+T` pause
  tracking, `Ctrl+1..7` navigate pages. Bind on the root only (no global hooks).
- **Safety on close:** `WM_DELETE_WINDOW` -> `_on_close()`: `engine.stop(timeout=2.0)`,
  `mouse.release_all()`, `settings.save()`, `destroy()`. Wrap in try/finally so the window always closes.
- **Toast:** a single `widgets.Toast(self)` used by `app.toast(message, tone)`.
- Auto-start engine on launch (control OFF) unless `general.auto_start_control` is true, and honour
  `general.start_minimized` (call `iconify()` after 200 ms).
- `main.py` becomes:
```python
import sys
from airgesture.app import main

if __name__ == "__main__":
    sys.exit(main())
```
with `def main()` in `app.py` handling a friendly fatal-error dialog if `pyautogui`/`mediapipe`/camera
model are missing.

### T8 — `requirements.txt`
`mediapipe>=0.10`, `opencv-python>=4.8`, `numpy>=1.24`, `Pillow>=10.0`, `PyAutoGUI>=0.9.54`

### T9 — Tests
Create `tests/` (plain `unittest`, run with `python -m unittest discover -s tests -v`):
- `test_geometry.py`, `test_recognizer.py` (synthetic landmark builders for open palm, fist, point,
  pinch, two/three fingers; also a **rotated** hand and a **scaled** hand must give the same gesture),
  `test_stabilizer.py` (flicker is suppressed, rising edge accepted, brief dropout tolerated, long dropout
  → None), `test_mouse_mapping.py` (0..1 → screen, clamping, deadzone, jump guard),
  `test_interaction.py` (fake mouse object; pinch fires exactly one click; no click on transition from
  another pose; drag started and always released on `disable`/`emergency_stop`/hand lost).
Write the synthetic-landmark helper once in `tests/synthetic.py` and reuse it.

### T10 — README.md (at `AirGesture/` level)
Install, run (`cd Computer; python main.py`), first run & calibration, gesture table, settings file
location, safety, troubleshooting, **"Tested / Partially tested / Not tested / Known limitations"**.

---

## 4. Non-negotiable rules

1. Read every existing module before editing it. Preserve the documented APIs above.
2. Never block the Tk main thread; never call Tk from the engine thread.
3. Never leave a mouse button down: `stop()`, `emergency_stop()`, hand-loss, window close.
4. No fixed-pixel gesture thresholds; keep recognition scale-invariant and handedness-agnostic.
5. No placeholder/simulated data, no dead buttons.
6. Every "apply" must persist via `settings.set/update_gesture` **and** notify the engine with `reload`.
7. Verify each page renders: launch the app, screenshot it (see the `browser-automation` /
   screenshot approach you have), check for Tk errors in the console, click through all 7 pages.
8. Report honestly: for each feature say Tested / Partially tested (and why) / Not tested.

## 5. Definition of done
- `python -m py_compile` clean for all modules; `python -m unittest discover -s tests -v` passes.
- App launches, camera streams, skeleton overlay visible, all 7 pages open without exceptions,
  theme switch (dark/light + accents) works, calibration wizard completes and persists an active area,
  gesture learning dialog saves a learned confidence, emergency stop releases buttons.
- README + final report with modified/added files and real test results.
