"""CRC-16-CCITT implementation over MSB-first bits."""
from __future__ import annotations
from typing import List, Sequence
try:
    from shared.constants import CRC_POLYNOMIAL as _CRC_POLYNOMIAL
except (ImportError, ModuleNotFoundError):
    _CRC_POLYNOMIAL = 0x1021
CRC_POLYNOMIAL = int(_CRC_POLYNOMIAL)
CRC_INITIAL = 0xFFFF

def calculate_crc(data_bits: List[int], polynomial: int = CRC_POLYNOMIAL) -> int:
    """Calculate CRC-16-CCITT (initial value 0xFFFF, no final XOR)."""
    if polynomial < 0 or polynomial > 0xFFFF:
        raise ValueError("polynomial must be a 16-bit value")
    crc = CRC_INITIAL
    for bit in data_bits:
        value = int(bit)
        if value not in (0, 1):
            raise ValueError("data_bits must contain only 0 and 1")
        feedback = ((crc >> 15) & 1) ^ value
        crc = (crc << 1) & 0xFFFF
        if feedback:
            crc ^= polynomial
    return crc

def verify_crc(data_bits: List[int], received_crc: int) -> bool:
    """Return whether the supplied 16-bit checksum matches the payload."""
    if not 0 <= int(received_crc) <= 0xFFFF:
        return False
    return calculate_crc(data_bits) == int(received_crc)
