'''Canonical message framing for CPU-load transmission and receiver decoding.'''
from __future__ import annotations
from typing import List, Optional
from .constants import CRC_BITS, CRC_POLYNOMIAL, END_OF_MESSAGE, SYNC_HEADER
from .utils import bits_to_text, text_to_bits
CRC_INITIAL = 0xFFFF
class ProtocolError(ValueError):
    '''Raised when an encoded frame or payload is malformed.'''

class Protocol:
    '''Encode/decode framed UTF-8 messages using CRC-16/CCITT.

    Frame layout: sync header, UTF-8 payload bits, CRC-16, end marker.
    CRC is calculated over payload bits only and serialized MSB first.
    '''

    def __init__(self, sync_header: Optional[List[int]] = None,
                 end_marker: Optional[List[int]] = None,
                 polynomial: int = CRC_POLYNOMIAL) -> None:
        '''Initialize protocol constants, allowing validated frame-marker overrides.'''
        self.sync_header = list(SYNC_HEADER if sync_header is None else sync_header)
        self.end_marker = list(END_OF_MESSAGE if end_marker is None else end_marker)
        self.polynomial = int(polynomial)
        if not self.sync_header or not self.end_marker:
            raise ValueError("frame markers must not be empty")
        self._validate_bits(self.sync_header)
        self._validate_bits(self.end_marker)
        if not 0 <= self.polynomial <= 0xFFFF:
            raise ValueError("polynomial must fit in 16 bits")

    @staticmethod
    def _validate_bits(bits: List[int]) -> None:
        '''Raise ValueError unless every entry is binary.'''
        if any(bit not in (0, 1) for bit in bits):
            raise ValueError("bit sequences may contain only 0 and 1")

    def calculate_crc(self, payload_bits: List[int]) -> int:
        '''Compute CRC-16/CCITT-FALSE over payload bits (init FFFF, xorout 0000).'''
        self._validate_bits(payload_bits)
        crc = CRC_INITIAL
        for bit in payload_bits:
            feedback = ((crc >> 15) & 1) ^ bit
            crc = (crc << 1) & 0xFFFF
            if feedback:
                crc ^= self.polynomial
        return crc
    def encode_message(self, message: str) -> List[int]:
        '''Encode UTF-8 text as sync + payload + CRC-16 + end marker.'''
        if not isinstance(message, str):
            raise TypeError("message must be a string")
        payload_bits = text_to_bits(message)
        crc_value = self.calculate_crc(payload_bits)
        crc_bits = [(crc_value >> shift) & 1 for shift in range(CRC_BITS - 1, -1, -1)]
        return list(self.sync_header) + payload_bits + crc_bits + list(self.end_marker)

    def _frame_parts(self, bits: List[int]) -> tuple[List[int], int]:
        '''Validate frame shape and return payload bits and received CRC.'''
        self._validate_bits(bits)
        minimum = len(self.sync_header) + CRC_BITS + len(self.end_marker)
        if len(bits) < minimum:
            raise ProtocolError("frame is shorter than the minimum frame length")
        if bits[:len(self.sync_header)] != self.sync_header:
            raise ProtocolError("sync header does not match")
        end_start = len(bits) - len(self.end_marker)
        if bits[end_start:] != self.end_marker:
            raise ProtocolError("end marker does not match")
        crc_start = end_start - CRC_BITS
        payload_bits = bits[len(self.sync_header):crc_start]
        if len(payload_bits) % 8:
            raise ProtocolError("payload length is not a whole number of UTF-8 bytes")
        received_crc = 0
        for bit in bits[crc_start:end_start]:
            received_crc = (received_crc << 1) | bit
        return payload_bits, received_crc
    def validate_frame(self, bits: List[int]) -> bool:
        '''Return whether sync, end marker, payload length and CRC are valid.'''
        try:
            payload_bits, received_crc = self._frame_parts(bits)
        except (ProtocolError, ValueError, TypeError):
            return False
        return self.calculate_crc(payload_bits) == received_crc
    def decode_bits(self, bits: List[int]) -> str:
        '''Validate a complete frame and decode its payload as UTF-8 text.'''
        payload_bits, received_crc = self._frame_parts(bits)
        if self.calculate_crc(payload_bits) != received_crc:
            raise ProtocolError("CRC check failed")
        try:
            return bits_to_text(payload_bits)
        except UnicodeDecodeError as error:
            raise ProtocolError("payload is not valid UTF-8") from error
