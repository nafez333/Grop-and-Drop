"""Engine bridge: runs camera + vision on a worker thread, feeds the UI.

Threading contract
------------------
* One ``EngineThread`` owns the camera and the MediaPipe tracker. It never
  touches Tk widgets.
* UI threads call :meth:`submit` with small command objects; commands are
  executed *on the engine thread* so settings that MediaPipe or OpenCV depend
  on are applied where they are used (no cross-thread mutation races).
* The engine publishes immutable-ish ``FramePacket`` objects to a callback.
  The UI side copies whatever it needs under a lock and renders at ~30 fps.
* Shutdown is cooperative: ``stop()`` sets a flag, joins with a timeout and
  always releases the camera, the tracker and any pressed mouse button.

Performance
-----------
* Vision runs at the camera's rate but is throttled to ``max_fps``.
* Only the newest frame matters; stale frames are simply not read twice.
* Optional recognition of every other frame when the CPU is slow (adaptive).
"""
from __future__ import annotations

import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Callable, Optional

import cv2
import numpy as np

from ..core.recognizer import ACTION_LABELS, GESTURE_LABELS, GestureRecognizer
from ..core.settings import SettingsManager
from ..core.stabilizer import GestureStabilizer
from .camera_manager import CameraManager
from .interaction import InteractionController
from .mouse_controller import MouseConfig, MouseController
from .tracking import HandTracker, TrackingError, draw_hand


@dataclass
class FramePacket:
    """Everything the UI needs for one rendered frame."""
    frame: Optional[np.ndarray] = None       # BGR copy with overlay drawn
    landmarks: object = None
    palm_px: Optional[tuple] = None
    palm_xy: Optional[tuple] = None
    gesture: Optional[str] = None
    gesture_label: str = "No hand"
    confidence: float = 0.0
    handedness: str = "Unknown"
    action: str = "idle"
    active: bool = False
    dragging: bool = False
    paused: bool = False
    mode: str = "auto"
    fps: float = 0.0
    frame_ms: float = 0.0
    status: str = "idle"
    message: str = ""
    timestamp: float = 0.0
    error: str = ""

    def copy(self) -> "FramePacket":
        return FramePacket(
            frame=None if self.frame is None else self.frame.copy(),
            landmarks=self.landmarks,
            palm_px=self.palm_px,
            palm_xy=self.palm_xy,
            gesture=self.gesture,
            gesture_label=self.gesture_label,
            confidence=self.confidence,
            handedness=self.handedness,
            action=self.action,
            active=self.active,
            dragging=self.dragging,
            paused=self.paused,
            mode=self.mode,
            fps=self.fps,
            frame_ms=self.frame_ms,
            status=self.status,
            message=self.message,
            timestamp=self.timestamp,
            error=self.error,
        )


class EngineThread:
    def __init__(
        self,
        settings: SettingsManager,
        mouse: MouseController,
        on_frame: Callable[[FramePacket], None],
        on_status: Callable[[str, str], None],
    ):
        self.settings = settings
        self.mouse = mouse
        self.interaction = InteractionController(mouse, settings)
        self.on_frame = on_frame
        self.on_status = on_status

        self.camera = CameraManager()
        self.tracker: Optional[HandTracker] = None
        self.recognizer = GestureRecognizer()
        self.stabilizer = GestureStabilizer(
            min_frames=3, max_gap_s=settings.get("interaction", "tracking_lost_timeout", 0.55)
        )
        self.stabilizer.set_learned_confidence(self._learned_confidence())

        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._commands: list[tuple[str, dict]] = []
        self._cmd_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._packet = FramePacket()
        self._running = False
        self._camera_opened = False
        self._tracking_paused = False

        self._fps_ema = 0.0
        self._frame_ms_ema = 0.0
        self._last_status_push = 0.0
        self._last_frame_push = 0.0
        self._target_fps = 30
        self._max_fps = 60
        self._show_overlay = True
        self._camera_error_reported = False

        # Calibration / learning helpers that need live frames.
        self._capture_request: Optional[dict] = None
        self._capture_samples: list = []
        self.on_capture_done: Optional[Callable[[list], None]] = None

    # ------------------------------------------------------------ public API
    @property
    def running(self) -> bool:
        return self._running

    def latest(self) -> FramePacket:
        with self._state_lock:
            return self._packet.copy()

    def submit(self, name: str, **payload) -> None:
        """Queue a command for the engine thread (thread safe)."""
        with self._cmd_lock:
            self._commands.append((name, payload))

    def start(self, start_control: bool = False) -> bool:
        if self._running:
            if start_control:
                self.interaction.enable()
            return True
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="AirGestureEngine", daemon=True)
        self._running = True
        self._autostart_control = start_control
        self._thread.start()
        return True

    def stop(self, timeout: float = 3.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)
        # Safety net independent of the thread state.
        try:
            self.interaction.emergency_stop()
            self.mouse.release_all()
        except Exception:
            pass
        self._running = False

    def set_control(self, on: bool) -> None:
        self.submit("control", on=on)

    def emergency_stop(self) -> None:
        self.submit("emergency")

    def pause_tracking(self, paused: bool) -> None:
        self.submit("pause_tracking", paused=paused)

    def request_capture(self, seconds: float = 1.6) -> None:
        """Collect landmark samples for gesture learning (handled on engine)."""
        self.submit("capture_start", seconds=seconds)

    def start_calibration(self) -> None:
        self.submit("calibration_start")

    # ------------------------------------------------------------- engine loop
    def _run(self) -> None:
        try:
            self._open_resources()
            if not self._camera_opened:
                self._push_status("error", self.camera.last_error or "Camera unavailable")
                return
            if self._autostart_control:
                self.interaction.enable()
            self._loop()
        except Exception as exc:  # unexpected engine failure
            self._push_status("error", f"Engine stopped: {exc}")
            traceback.print_exc()
        finally:
            self._shutdown_resources()
            self._push_status("stopped", "Camera released")
            self._running = False

    def _open_resources(self) -> None:
        cam = self.settings.section("camera")

        # Load the hand model FIRST. MediaPipe initialises its own capture
        # machinery at import/first-use; doing it while no camera is open keeps
        # the OpenCV capture thread free, which is what prevented the device
        # from ever opening when the order was reversed.
        self._push_status("starting", "Loading hand tracking model...")
        try:
            self.tracker = HandTracker(
                num_hands=1,
                detection_confidence=float(cam.get("detection_confidence", 0.6)),
                tracking_confidence=float(cam.get("tracking_confidence", 0.6)),
            )
        except Exception as exc:
            self._push_status("error", f"Hand tracking model failed to load: {exc}")
            self._camera_opened = False
            return

        self._push_status("starting", "Opening camera...")
        try:
            self._camera_opened = self.camera.open(
                cam.get("index", 0), cam.get("width", 1280),
                cam.get("height", 720), cam.get("fps", 30),
            )
        except Exception as exc:
            self.camera.last_error = f"Camera error: {exc}"
            self._camera_opened = False
        if not self._camera_opened:
            self._push_status("error", self.camera.last_error or "Camera unavailable")
            with self._state_lock:
                self._packet.error = self.camera.last_error or "Camera unavailable"
            return

        self._target_fps = max(10, int(cam.get("fps", 30)))
        self._max_fps = self._target_fps
        self._show_overlay = bool(self.settings.get("general", "show_overlay", True))
        track_cfg = self.settings.section("tracking")
        self.tracker.configure_filter(
            float(track_cfg.get("distance_filter", 0.35)), float(track_cfg.get("velocity_beta", 0.025))
        )
        self.tracker.handedness_filter = track_cfg.get("handedness", "any")
        self._apply_mouse_config()
        self.interaction.set_mode(self.settings.get("interaction", "mode", "auto"))
        self._push_status("running", "Tracking ready")
        self._camera_opened = True

    def _loop(self) -> None:
        frame_interval = 1.0 / max(10, self._max_fps)
        reconnect_at = 0.0
        while not self._stop.is_set():
            t_start = time.perf_counter()
            self._drain_commands()
            self._tick_capture()
            if self._stop.is_set():
                break

            frame = self.camera.read_frame()
            if frame is None:
                # Report the failure once, visibly, instead of spinning silently.
                if not self._camera_error_reported:
                    self._camera_error_reported = True
                    self._push_status(
                        "error",
                        "Camera is not delivering frames. Close other apps using the "
                        "webcam, then press 'Restart camera' on the Camera page.",
                    )
                    with self._state_lock:
                        self._packet.error = "Camera is not delivering frames"
                # Retry the device every few seconds (USB hiccup) without spinning hot.
                now = time.time()
                if now >= reconnect_at:
                    reconnect_at = now + 3.0
                    self._reconnect_camera()
                time.sleep(0.05)
                continue

            self._camera_error_reported = False

            cam_cfg = self.settings.section("camera")
            if cam_cfg.get("mirror", True):
                frame = cv2.flip(frame, 1)

            self._process_frame(frame)

            # Throttle from the *end* of processing, so frame time is not
            # double-counted: loop cost = processing + remaining interval.
            elapsed = time.perf_counter() - t_start
            if elapsed < frame_interval:
                time.sleep(min(frame_interval - elapsed, 0.02))

        self._push_status("stopping", "Stopping engine...")

    def _process_frame(self, frame: np.ndarray) -> None:
        t0 = time.perf_counter()
        h, w = frame.shape[:2]
        packet = FramePacket(timestamp=time.time(), mode=self.interaction.mode)
        gesture = None
        conf = 0.0

        if self.tracker is not None and not self._tracking_paused:
            try:
                result = self.tracker.process(frame)
            except TrackingError as exc:
                self._push_status("error", str(exc))
                self._stop.set()
                return
            except Exception as exc:  # never let one bad frame kill the engine
                self._push_status("warning", f"Tracking error: {exc}")
                result = None

            if result is not None and result.landmarks is not None:
                packet.landmarks = result.landmarks
                packet.handedness = result.handedness
                if result.pose is not None:
                    self.recognizer.sensitivity = self._global_sensitivity()
                    try:
                        detection = self.recognizer.recognize(result.pose)
                    except Exception as exc:
                        self._push_status("warning", f"Recognition error: {exc}")
                        detection = None
                    gesture = self.stabilizer.update(detection, result.timestamp)
                    conf = self.stabilizer.confidence
                if result.palm_xy is not None:
                    packet.palm_xy = result.palm_xy
                    packet.palm_px = (int(result.palm_xy[0] * w), int(result.palm_xy[1] * h))
                # live capture for the gesture learner
                if self._capture_request is not None and result.pose is not None:
                    self._capture_samples.append(result.pose)
            else:
                gesture = self.stabilizer.update(None, time.perf_counter())
                conf = 0.0
        else:
            gesture = None

        self.interaction.update(gesture, conf, palm_xy=packet.palm_xy)
        pkt = self._build_packet(frame, packet, gesture, conf)
        cost_ms = (time.perf_counter() - t0) * 1000.0
        self._frame_ms_ema = (
            cost_ms if self._frame_ms_ema == 0.0
            else self._frame_ms_ema * 0.85 + cost_ms * 0.15
        )
        pkt.frame_ms = self._frame_ms_ema
        self._publish(pkt)

    def _build_packet(self, frame, packet: FramePacket, gesture, conf) -> FramePacket:
        st = self.interaction.state
        if self._show_overlay and frame is not None:
            frame = self._draw_overlay(frame, packet, gesture, st)
        packet.frame = frame
        packet.gesture = gesture
        packet.gesture_label = GESTURE_LABELS.get(gesture, "No hand")
        packet.confidence = float(conf)
        packet.action = ACTION_LABELS.get(st.action, st.action.replace("_", " ").title())
        packet.active = st.active
        packet.dragging = st.dragging
        packet.paused = st.paused
        packet.mode = self.interaction.mode
        packet.message = st.last_message
        packet.error = st.last_error
        packet.frame_ms = self._frame_ms_ema
        packet.fps = self._fps_ema
        return packet

    def _draw_overlay(self, frame, packet: FramePacket, gesture, st) -> np.ndarray:
        p = (139, 108, 255)  # BGR violet
        h, w = frame.shape[:2]
        if packet.landmarks is not None:
            draw_hand(frame, packet.landmarks, packet.palm_xy, accent=p)

        # active-area rectangle from calibration
        cal = self.settings.section("calibration").get("active_area", {})
        x0, y0 = int(float(cal.get("x0", 0.18)) * w), int(float(cal.get("y0", 0.15)) * h)
        x1, y1 = int(float(cal.get("x1", 0.82)) * w), int(float(cal.get("y1", 0.85)) * h)
        overlay = frame.copy()
        cv2.rectangle(overlay, (x0, y0), (x1, y1), (255, 255, 255), 1)
        cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)

        if packet.palm_px is not None:
            cx, cy = packet.palm_px
            col = (151, 220, 61) if packet.active else (210, 210, 210)
            cv2.circle(frame, (cx, cy), 22, col, 2, cv2.LINE_AA)

        status = "CONTROL ON" if st.active else "STANDBY"
        if st.paused:
            status = "PAUSED"
        cv2.rectangle(frame, (0, 0), (w, 34), (16, 18, 24), -1)
        cv2.putText(frame, status, (12, 23), cv2.FONT_HERSHEY_DUPLEX, 0.55,
                    (151, 220, 61) if st.active else (190, 190, 200), 1, cv2.LINE_AA)
        cv2.putText(frame, GESTURE_LABELS.get(gesture, "No hand"), (w - 210, 23),
                    cv2.FONT_HERSHEY_DUPLEX, 0.58, (240, 240, 245), 1, cv2.LINE_AA)
        return frame

    def _publish(self, packet: FramePacket) -> None:
        now = time.perf_counter()
        with self._state_lock:
            prev_ts = self._packet.timestamp
            self._packet = packet
            if now - self._last_frame_push < 1 / 30:
                self._packet.frame = packet.frame
            self._last_frame_push = now
        if prev_ts:
            dt = max(1e-3, packet.timestamp - prev_ts)
            fps = 1.0 / dt
            self._fps_ema = fps if self._fps_ema == 0 else self._fps_ema * 0.9 + fps * 0.1
        try:
            self.on_frame(packet)
        except Exception:
            pass

    # --------------------------------------------------------------- commands
    def _drain_commands(self) -> None:
        with self._cmd_lock:
            commands, self._commands = self._commands, []
        for name, payload in commands:
            try:
                self._handle_command(name, payload)
            except Exception as exc:
                self._push_status("warning", f"Command {name} failed: {exc}")

    def _handle_command(self, name: str, payload: dict) -> None:
        if name == "control":
            if payload.get("on"):
                self.interaction.enable()
                self._push_status("control", "Mouse control ON")
            else:
                self.interaction.disable()
                self._push_status("control", "Mouse control OFF")
        elif name == "emergency":
            self.interaction.emergency_stop()
            self.mouse.release_all()
            self._push_status("error", "EMERGENCY STOP - mouse released")
        elif name == "pause_tracking":
            self._tracking_paused = bool(payload.get("paused"))
            if self._tracking_paused:
                self.interaction.suspend("Tracking paused")
            else:
                self.interaction.resume()
                if self.tracker is not None:
                    self.tracker.reset()
                self.stabilizer.reset()
        elif name == "reload":
            self._apply_mouse_config()
            self.recognizer.sensitivity = self._global_sensitivity()
            self.stabilizer.set_learned_confidence(self._learned_confidence())
            self.stabilizer.max_gap_s = float(
                self.settings.get("interaction", "tracking_lost_timeout", 0.55)
            )
            self.interaction.set_mode(self.settings.get("interaction", "mode", "auto"))
            self._show_overlay = bool(self.settings.get("general", "show_overlay", True))
            if self.tracker is not None:
                track_cfg = self.settings.section("tracking")
                self.tracker.configure_filter(
                    float(track_cfg.get("distance_filter", 0.35)),
                    float(track_cfg.get("velocity_beta", 0.025)),
                )
                self.tracker.handedness_filter = track_cfg.get("handedness", "any")
        elif name == "capture_start":
            self._capture_samples = []
            self._capture_request = {"seconds": float(payload.get("seconds", 1.6)), "since": time.time()}
        elif name == "capture_stop":
            if self._capture_request is not None:
                samples = self._capture_samples
                self._capture_request = None
                self._capture_samples = []
                if self.on_capture_done is not None:
                    try:
                        self.on_capture_done(samples)
                    except Exception:
                        pass
        elif name == "calibration_start":
            self._push_status("calibration", "Calibration mode active")

    def _tick_capture(self) -> None:
        req = self._capture_request
        if req is None:
            return
        if time.time() - req["since"] >= req["seconds"]:
            samples = self._capture_samples
            self._capture_request = None
            self._capture_samples = []
            if self.on_capture_done is not None:
                try:
                    self.on_capture_done(samples)
                except Exception:
                    pass

    def _apply_mouse_config(self) -> None:
        m = self.settings.section("mouse")
        cal = self.settings.section("calibration")
        area = cal.get("active_area", {})
        cfg = MouseConfig(
            sensitivity=float(m.get("sensitivity", 1.35)),
            speed=float(m.get("speed", 1.0)),
            smoothing=float(m.get("smoothing", 0.45)),
            area_x=float(m.get("active_area_x", 0.62)),
            area_y=float(m.get("active_area_y", 0.58)),
            acceleration=float(m.get("acceleration", 0.35)),
            jump_guard=float(m.get("jump_guard", 0.14)),
            deadzone=float(m.get("deadzone", 0.004)),
            scroll_speed=float(m.get("scroll_speed", 1.0)),
            natural_scroll=bool(m.get("natural_scroll", True)),
            relative_mode=m.get("position_mode") == "relative",
            active_area=(
                float(area.get("x0", 0.18)), float(area.get("y0", 0.15)),
                float(area.get("x1", 0.82)), float(area.get("y1", 0.85)),
            ),
        )
        self.mouse.update_config(cfg)

    def _global_sensitivity(self) -> float:
        gestures = self.settings.section("gestures")
        values = [g.get("sensitivity", 0.5) for g in gestures.values() if g.get("enabled")]
        return sum(values) / len(values) if values else 0.5

    def _learned_confidence(self) -> dict[str, float]:
        gestures = self.settings.section("gestures")
        return {gid: float(cfg.get("learned_confidence", 1.0)) for gid, cfg in gestures.items()}

    # -------------------------------------------------------------- resources
    def _reconnect_camera(self) -> None:
        """Reopen the configured camera after a read failure (engine thread)."""
        cam = self.settings.section("camera")
        self.camera.close()
        ok = self.camera.open(cam.get("index", 0), cam.get("width", 1280),
                              cam.get("height", 720), cam.get("fps", 30))
        if ok:
            self._camera_error_reported = False
            self._push_status("running", "Camera reconnected")
        else:
            self._push_status("error", self.camera.last_error or "Camera unavailable")

    def _push_status(self, status: str, message: str) -> None:
        try:
            self.on_status(status, message)
        except Exception:
            pass

    def _shutdown_resources(self) -> None:
        if self.interaction.state.active or self.mouse.any_button_down:
            self.interaction.emergency_stop()
        self.mouse.release_all()
        if self.tracker is not None:
            try:
                self.tracker.close()
            except Exception:
                pass
            self.tracker = None
        self.camera.close()
        self._camera_opened = False
