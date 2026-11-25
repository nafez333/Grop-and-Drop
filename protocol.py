"""Protocol constants and frame definitions (Agent 1 interface stub).

This is a stub implementation. Agent 1 should replace this with the real
Protocol class and constants.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from shared.constants import BIT_DURATION_DEFAULT, CRC_BITS, CRC_POLYNOMIAL, END_OF_MESSAGE, SYNC_HEADER

# Preserve legacy imports while using the shared frame format.
FRAME_END_MARKER = list(END_OF_MESSAGE)
MAX_PAYLOAD_BITS = 256
CRC_INITIAL = 0xFFFF


@dataclass
class Frame:
    """A single protocol frame."""

    sync_header: List[int]
    payload: List[int]
    crc: int
    end_marker: List[int]

    def to_bits(self) -> List[int]:
        """Serialize frame to a flat bit list."""
        bits = list(self.sync_header)
        bits.extend(self.payload)
        # CRC is serialized MSB first as a 16-bit field.
        crc_bits = [(self.crc >> shift) & 1 for shift in range(CRC_BITS - 1, -1, -1)]
        bits.extend(crc_bits)
        bits.extend(self.end_marker)
        return bits

    @classmethod
    def from_bits(cls, bits: List[int]) -> "Frame":
        """Deserialize a flat bit list into a Frame (best-effort).

        Frame layout: sync_header(4) + payload(N) + crc(8) + end_marker(4)
        """
        if any(bit not in (0, 1) for bit in bits):
            raise ValueError("frame bits must contain only 0 and 1")
        minimum = len(SYNC_HEADER) + CRC_BITS + len(FRAME_END_MARKER)
        if len(bits) < minimum:
            raise ValueError("frame is too short")
        sync_size = len(SYNC_HEADER)
        end_size = len(FRAME_END_MARKER)
        payload_end = len(bits) - CRC_BITS - end_size
        crc_end = len(bits) - end_size
        crc = 0
        for bit in bits[payload_end:crc_end]:
            crc = (crc << 1) | bit
        return cls(list(bits[:sync_size]), list(bits[sync_size:payload_end]), crc, list(bits[crc_end:]))


class Protocol:
    """Encode/decode messages to/from protocol frames."""

    def __init__(self, sync_header: Optional[List[int]] = None,
                 end_marker: Optional[List[int]] = None) -> None:
        self.sync_header = list(SYNC_HEADER if sync_header is None else sync_header)
        self.end_marker = list(FRAME_END_MARKER if end_marker is None else end_marker)
        if not self.sync_header or not self.end_marker:
            raise ValueError("frame markers must not be empty")
        if any(bit not in (0, 1) for bit in self.sync_header + self.end_marker):
            raise ValueError("frame markers must contain only 0 and 1")

    def encode(self, message: str) -> List[int]:
        """Encode a string message into a flat bit list with framing."""
        if not isinstance(message, str):
            raise TypeError("message must be a string")
        payload_bits: List[int] = []
        for byte in message.encode("utf-8"):
            for shift in range(7, -1, -1):
                payload_bits.append((byte >> shift) & 1)
        crc = self._compute_crc(payload_bits)
        frame = Frame(
            sync_header=list(self.sync_header),
            payload=payload_bits,
            crc=crc,
            end_marker=list(self.end_marker),
        )
        return frame.to_bits()

    def decode(self, bits: List[int]) -> Optional[str]:
        """Decode a flat bit list back into a string message."""
        if not self.validate_frame(bits):
            return None
        frame = Frame.from_bits(bits)
        payload = bytearray()
        for offset in range(0, len(frame.payload), 8):
            value = 0
            for bit in frame.payload[offset:offset + 8]:
                value = (value << 1) | bit
            payload.append(value)
        try:
            return bytes(payload).decode("utf-8")
        except UnicodeDecodeError:
            return None

    @staticmethod
    def _compute_crc(bits: List[int]) -> int:
        """Simple CRC-8 computation."""
        if any(bit not in (0, 1) for bit in bits):
            raise ValueError("CRC input must contain only 0 and 1")
        crc = 0xFFFF
        for bit in bits:
            feedback = ((crc >> (CRC_BITS - 1)) & 1) ^ bit
            crc = (crc << 1) & 0xFFFF
            if feedback:
                crc ^= CRC_POLYNOMIAL
        return crc

    def validate_frame(self, bits: List[int]) -> bool:
        """Validate that a bit list forms a well-formed frame."""
        minimum = len(self.sync_header) + CRC_BITS + len(self.end_marker)
        if len(bits) < minimum or any(bit not in (0, 1) for bit in bits):
            return False
        if bits[:len(self.sync_header)] != self.sync_header:
            return False
        if bits[-len(self.end_marker):] != self.end_marker:
            return False
        payload_end = len(bits) - CRC_BITS - len(self.end_marker)
        payload = bits[len(self.sync_header):payload_end]
        if len(payload) % 8:
            return False
        crc_end = len(bits) - len(self.end_marker)
        received_crc = 0
        for bit in bits[payload_end:crc_end]:
            received_crc = (received_crc << 1) | bit
        return received_crc == self._compute_crc(payload)
