"""Transmitter and CPULoadController (Agent 1 interface stub).

These are stub implementations. Agent 1 should replace with the real
hardware/software transmitter.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import List, Optional

logger = logging.getLogger(__name__)


class CPULoadController:
    """Controls transmission rate to avoid CPU overload."""

    def __init__(self, max_cpu_percent: float = 70.0) -> None:
        self.max_cpu_percent = max_cpu_percent
        self._lock = threading.Lock()
        self._last_send_time: Optional[float] = None

    def throttle(self, bit_duration: float = 1.0) -> None:
        """Optionally throttle to respect CPU budget."""
        with self._lock:
            now = time.time()
            if self._last_send_time is not None:
                elapsed = now - self._last_send_time
                min_interval = bit_duration
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)
            self._last_send_time = time.time()


class Transmitter:
    """Sends bit patterns over a channel (stub — logs instead of hardware)."""

    def __init__(self, cpu_controller: Optional[CPULoadController] = None,
                 bit_duration: float = 1.0) -> None:
        self.cpu_controller = cpu_controller or CPULoadController()
        self.bit_duration = bit_duration
        self._lock = threading.Lock()
        self.sent_bits: List[int] = []

    def send_bits(self, bits: List[int]) -> bool:
        """Send a list of bits. Stub logs the transmission."""
        with self._lock:
            self.sent_bits.extend(list(bits))
        self.cpu_controller.throttle(self.bit_duration)
        logger.debug("Transmitted %d bits: %s", len(bits), "".join(str(b) for b in bits))
        return True

    def send_message(self, message: str, protocol) -> bool:
        """Encode and send a string message using the given Protocol."""
        bits = protocol.encode(message)
        return self.send_bits(bits)

    def clear(self) -> None:
        """Clear the sent-bits buffer."""
        with self._lock:
            self.sent_bits = []
