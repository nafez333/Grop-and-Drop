'''Sender-specific settings with environment and optional JSON overrides.'''
from __future__ import annotations
import math
import os
from typing import Any, Dict
from shared.constants import BIT_DURATION_DEFAULT, CONFIG_FILE, IDLE_DURATION_DEFAULT, LOAD_DURATION_DEFAULT, TEST_CYCLE_COUNT
from shared.utils import load_json

def _positive_float(value: Any, name: str) -> float:
    '''Convert and validate a positive finite duration value.'''
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a number") from error
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return result

def _read_config() -> Dict[str, Any]:
    '''Read optional project sender JSON settings if available.'''
    if not CONFIG_FILE.is_file():
        return {}
    data = load_json(str(CONFIG_FILE))
    if not isinstance(data, dict):
        raise ValueError("sender config JSON must contain an object")
    return data
_FILE_CONFIG = _read_config()
BIT_DURATION = _positive_float(os.environ.get("SENDER_BIT_DURATION", _FILE_CONFIG.get("bit_duration", BIT_DURATION_DEFAULT)), "BIT_DURATION")
LOAD_DURATION = _positive_float(os.environ.get("SENDER_LOAD_DURATION", _FILE_CONFIG.get("load_duration", LOAD_DURATION_DEFAULT)), "LOAD_DURATION")
IDLE_DURATION = _positive_float(os.environ.get("SENDER_IDLE_DURATION", _FILE_CONFIG.get("idle_duration", IDLE_DURATION_DEFAULT)), "IDLE_DURATION")
try:
    TEST_CYCLES = int(os.environ.get("SENDER_TEST_CYCLES", _FILE_CONFIG.get("test_cycles", TEST_CYCLE_COUNT)))
except (TypeError, ValueError) as error:
    raise ValueError("TEST_CYCLES must be an integer") from error
if TEST_CYCLES <= 0:
    raise ValueError("TEST_CYCLES must be positive")
