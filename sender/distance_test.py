'''Interactive CPU-load transmission distance test.'''
from __future__ import annotations
from typing import List
from shared.constants import DISTANCES, IDLE_PERCENT, LOAD_PERCENT, RECORDINGS_DIR, SETUP_WAIT_SECONDS, SYNC_HEADER, TEST_PATTERN
from shared.logger import get_logger
from shared.protocol import Protocol
from shared.utils import save_json, timestamp_now
from .config import BIT_DURATION
from .cpu_load import CPULoadController
_LOG = get_logger(__name__)

def run_distance_test() -> dict:
    '''Prompt for receiver placement and transmit sync plus a known bit pattern.'''
    controller = CPULoadController()
    results: List[dict] = []
    test_bits = list(SYNC_HEADER) + list(TEST_PATTERN)
    try:
        for distance in DISTANCES:
            input(f"Place phone at {distance} cm, then press Enter to continue: ")
            _LOG.info("Distance test at %d cm: settling for %.1f seconds", distance, SETUP_WAIT_SECONDS)
            controller.idle(SETUP_WAIT_SECONDS)
            entries = []
            begin = timestamp_now()
            for bit in test_bits:
                state = "load" if bit == 1 else "idle"
                if bit == 1:
                    controller.start_load(BIT_DURATION)
                else:
                    controller.idle(BIT_DURATION)
                entries.append({"bit": bit, "cpu_state": state, "target_percent": LOAD_PERCENT if bit else IDLE_PERCENT,
                                "duration_seconds": BIT_DURATION})
            controller.idle(SETUP_WAIT_SECONDS)
            result = {"distance_cm": distance, "timestamp": begin, "bits": test_bits, "events": entries}
            results.append(result)
            _LOG.info("Distance test at %d cm complete", distance)
        report = {"timestamp": timestamp_now(), "sync_header": SYNC_HEADER, "test_pattern": TEST_PATTERN,
                  "bit_duration_seconds": BIT_DURATION, "distance_tests": results}
        filepath = RECORDINGS_DIR / f"distance_test_{report['timestamp'].replace(':', '-').replace('.', '-')}.json"
        save_json(report, str(filepath))
        _LOG.info("Distance test log saved to %s", filepath)
        return report
    finally:
        controller.cleanup()

def main() -> int:
    '''Run the operator-guided distance test.'''
    try:
        run_distance_test()
    except (EOFError, KeyboardInterrupt):
        _LOG.warning("Distance test cancelled by operator")
        return 130
    except (OSError, RuntimeError, ValueError) as error:
        _LOG.exception("Distance test failed: %s", error)
        return 1
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
