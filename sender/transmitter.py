'''Frame and transmit digital data by modulating CPU load.'''
from __future__ import annotations
import math
import threading
from typing import Any, Dict, List, Optional
from shared.constants import BIT_DURATION_DEFAULT, IDLE_PERCENT, LOAD_PERCENT, RECORDINGS_DIR, TRANSMISSION_LOG_FIELDS
from shared.logger import get_logger
from shared.protocol import Protocol
from shared.utils import save_json, timestamp_now
from .cpu_load import CPULoadController
_LOG = get_logger(__name__)
class Transmitter:
    '''Transmit framed bits and retain a JSON-serializable operation log.'''
    def __init__(self, cpu_controller: CPULoadController, protocol: Protocol) -> None:
        '''Create transmitter using the injected CPU controller and frame protocol.'''
        self.cpu_controller = cpu_controller
        self.protocol = protocol
        self._log: Dict[str, Any] = {"timestamp": timestamp_now(), "transmissions": []}
        self._lock = threading.RLock()
        self._gesture_engine: Optional[Any] = None
    def _state(self, bit: int, duration: float) -> str:
        '''Transmit one validated logical bit at the configured duration.'''
        cpu_state = "load" if bit else "idle"
        started = timestamp_now()
        try:
            if bit == 1:
                self.cpu_controller.start_load(duration)
            else:
                self.cpu_controller.idle(duration)
            return cpu_state
        finally:
            entry = {"timestamp": started, "bit": bit, "cpu_state": cpu_state,
                     "duration_seconds": float(duration), "target_percent": LOAD_PERCENT if bit else IDLE_PERCENT}
            with self._lock:
                self._log["transmissions"].append(entry)
            _LOG.info("Transmitted bit=%d state=%s duration=%.3fs", bit, cpu_state, duration)

    def send_bit(self, bit: int, duration: float) -> bool:
        '''Transmit one binary bit, returning False for validation/runtime errors.'''
        if not isinstance(bit, int):
            raise TypeError("bit must be an integer")
        if bit not in (0, 1):
            raise ValueError("bit must be 0 or 1")
        if not math.isfinite(float(duration)) or duration <= 0:
            raise ValueError("duration must be positive and finite")
        try:
            self._state(int(bit), float(duration))
            return True
        except (OSError, RuntimeError, KeyboardInterrupt):
            _LOG.exception("Bit transmission failed")
            self.cpu_controller.stop_load()
            return False
    def send_bits(self, bits: List[int], duration: float) -> bool:
        '''Transmit each bit in order, stopping safely on the first failure.'''
        if not math.isfinite(float(duration)) or duration <= 0:
            raise ValueError("duration must be positive and finite")
        if any(not isinstance(bit, int) or bit not in (0, 1) for bit in bits):
            raise ValueError("bits must contain only 0 and 1")
        for bit in bits:
            if not self.send_bit(bit, duration):
                return False
        try:
            self._save_log()
        except OSError:
            _LOG.exception("Could not persist transmission log")
            return False
        return True
    def send_message(self, message: str, bit_duration: float = BIT_DURATION_DEFAULT) -> bool:
        '''Encode and transmit one framed UTF-8 message.'''
        if not math.isfinite(float(bit_duration)) or bit_duration <= 0:
            raise ValueError("bit_duration must be positive and finite")
        try:
            bits = self.protocol.encode_message(message)
        except (TypeError, ValueError):
            _LOG.exception("Message could not be encoded")
            return False
        return self.send_bits(bits, bit_duration)

    def _get_gesture_engine(self) -> Any:
        '''Lazily import the other agent's GestureEngine interface.'''
        if self._gesture_engine is None:
            try:
                from gestures.gesture_engine import GestureEngine
            except ImportError as error:
                raise RuntimeError("gestures.gesture_engine.GestureEngine is unavailable") from error
            self._gesture_engine = GestureEngine()
        return self._gesture_engine
    def send_gesture(self, gesture_name: str) -> bool:
        '''Resolve a gesture name and transmit its bit pattern.'''
        if not isinstance(gesture_name, str) or not gesture_name.strip():
            raise ValueError("gesture_name must be a non-empty string")
        try:
            bits = self._get_gesture_engine().get_bits(gesture_name)
            if any(bit not in (0, 1) for bit in bits):
                raise ValueError("gesture engine returned non-binary bits")
            return self.send_bits(list(bits), BIT_DURATION_DEFAULT)
        except (ImportError, RuntimeError, ValueError, LookupError):
            _LOG.exception("Unable to send gesture %s", gesture_name)
            return False
    def get_transmission_log(self) -> dict:
        '''Return a deep-enough copy of transmission metadata and entries.'''
        with self._lock:
            return {"timestamp": self._log["timestamp"], "transmissions": [dict(entry) for entry in self._log["transmissions"]]}

    def _save_log(self) -> str:
        '''Persist transmission history to a timestamped JSON recording.'''
        with self._lock:
            snapshot = self.get_transmission_log()
        safe_stamp = snapshot["timestamp"].replace(":", "-").replace(".", "-")
        extension = TRANSMISSION_LOG_FIELDS["extension"]
        filepath = RECORDINGS_DIR / f"transmit_log_{safe_stamp}.{extension}"
        save_json(snapshot, str(filepath))
        _LOG.info("Transmission log saved: %s", filepath)
        return str(filepath)

# Module-level convenience functions use an explicit configured singleton.
_DEFAULT_TRANSMITTER: Optional[Transmitter] = None

def configure_transmitter(cpu_controller: CPULoadController, protocol: Protocol) -> Transmitter:
    '''Configure the singleton used by the Agent-facing module functions.'''
    global _DEFAULT_TRANSMITTER
    _DEFAULT_TRANSMITTER = Transmitter(cpu_controller, protocol)
    return _DEFAULT_TRANSMITTER

def _default() -> Transmitter:
    '''Return the configured module-level transmitter or raise clearly.'''
    if _DEFAULT_TRANSMITTER is None:
        raise RuntimeError("call configure_transmitter(cpu_controller, protocol) first")
    return _DEFAULT_TRANSMITTER

def send_bits(bit_list: List[int], bit_duration: float) -> bool:
    '''Module-level send_bits interface.'''
    return _default().send_bits(bit_list, bit_duration)
def send_message(message: str, bit_duration: float = BIT_DURATION_DEFAULT) -> bool:
    '''Module-level send_message interface.'''
    return _default().send_message(message, bit_duration)
def send_gesture(gesture_name: str) -> bool:
    '''Module-level send_gesture interface.'''
    return _default().send_gesture(gesture_name)
def get_transmission_log() -> dict:
    '''Module-level transmission log interface.'''
    return _default().get_transmission_log()
