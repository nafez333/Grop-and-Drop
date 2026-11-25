"""Project-wide constants.

This module is the single source of truth for all named numeric and
configuration values. No magic numbers should appear anywhere else in the
project; import from this module instead.
"""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Frame format
# ---------------------------------------------------------------------------
SYNC_HEADER = [1, 0, 1, 0, 1, 0, 1, 0]
"""Preamble that marks the start of every transmitted frame (8 bits)."""
END_OF_MESSAGE = [1, 1, 1, 1]
"""Trailer that marks the end of every transmitted frame (4 bits)."""
CRC_POLYNOMIAL = 0x1021
"""CRC-16/CCITT polynomial used for frame integrity checking."""
CRC_BITS = 16
"""Width of the CRC field in bits."""

# ---------------------------------------------------------------------------
# Timing and CPU-load modulation
# ---------------------------------------------------------------------------
BIT_DURATION_DEFAULT = 1.0
"""Default number of seconds used to transmit a single bit."""
SAMPLE_RATE = 20
"""Samples per second used when observing the received CPU-load signal."""
LOAD_PERCENT = 100
"""CPU-load target percent used to represent a logical 1 bit."""
IDLE_PERCENT = 0
"""CPU-load target percent used to represent a logical 0 bit (idle)."""

# ---------------------------------------------------------------------------
# Distance test
# ---------------------------------------------------------------------------
DISTANCES = [5, 10, 15, 20, 25, 30]
"""Distances (cm) used during the receiver distance test."""

# ---------------------------------------------------------------------------
# Filesystem paths (resolved relative to this package's project root)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
"""Project root directory (parent of the ``shared`` package)."""
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = DATA_DIR / "logs"
RECORDINGS_DIR = DATA_DIR / "recordings"
# Sender scheduling, validation and optional configuration values.
CPU_TARGET_MIN = 0
"Minimum load percentage and fallback worker count."""
CPU_TARGET_MAX = 100
"Maximum target load percentage."""
CPU_LOAD_PERIOD_SECONDS = 0.05
"Duty-cycle worker scheduling period in seconds."""
PROCESS_JOIN_TIMEOUT_SECONDS = 1.0
"Grace period before terminating an unresponsive worker."""
LOAD_DURATION_DEFAULT = 2.0
"Default continuous load segment duration."""
IDLE_DURATION_DEFAULT = 2.0
"Default idle segment duration."""
TEST_CYCLE_COUNT = 10
"Default number of fixed-pattern load/idle cycles."""
SETUP_WAIT_SECONDS = 5.0
"Delay used to position/settle the receiver during a distance test."""
TRANSMISSION_LOG_FIELDS = {"extension": "json", "timestamp": "timestamp", "entries": "transmissions"}
"Named keys and filename extension for transmission log persistence."""
TEST_PATTERN = [1, 0, 1, 1, 0, 0, 1, 0]
"Known test payload following sync marker in distance validation."""

CONFIG_FILE = PROJECT_ROOT / "sender_config.json"
"Optional sender configuration JSON path."""
