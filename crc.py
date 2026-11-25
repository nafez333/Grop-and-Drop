"""CRC utilities (Agent 1 / Agent 2 shared interface stub)."""

from __future__ import annotations

POLYNOMIAL = 0x07  # CRC-8 polynomial


def compute_crc(bits) -> int:
    """Compute CRC-8 over a sequence of bits (list of 0/1 ints or a string)."""
    crc = 0
    if isinstance(bits, str):
        bit_list = [int(c) for c in bits]
    else:
        bit_list = list(bits)
    for bit in bit_list:
        crc ^= (int(bit) << 7)
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ POLYNOMIAL) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def verify_crc(bits, expected_crc: int) -> bool:
    """Verify that CRC of bits matches expected_crc."""
    return compute_crc(bits) == expected_crc
