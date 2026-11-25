'''Standalone fixed CPU-load pattern transmission test.'''
from __future__ import annotations
from shared.constants import RECORDINGS_DIR
from shared.logger import get_logger
from shared.utils import save_json, timestamp_now
from .cpu_load import CPULoadController
from .config import IDLE_DURATION, LOAD_DURATION, TEST_CYCLES
_LOG = get_logger(__name__)

def run_test() -> dict:
    '''Transmit the required repeated load/idle pattern and persist its log.'''
    _LOG.info("Receiver operator: start your recording now. Sending %d cycles of load then idle.", TEST_CYCLES)
    controller = CPULoadController()
    events = []
    try:
        for cycle in range(TEST_CYCLES):
            started = timestamp_now()
            _LOG.info("Cycle %d/%d: CPU load %.2fs", cycle + 1, TEST_CYCLES, LOAD_DURATION)
            controller.start_load(LOAD_DURATION)
            events.append({"timestamp": started, "cycle": cycle + 1, "state": "load", "duration_seconds": LOAD_DURATION})
            idle_start = timestamp_now()
            _LOG.info("Cycle %d/%d: idle %.2fs", cycle + 1, TEST_CYCLES, IDLE_DURATION)
            controller.idle(IDLE_DURATION)
            events.append({"timestamp": idle_start, "cycle": cycle + 1, "state": "idle", "duration_seconds": IDLE_DURATION})
        report = {"timestamp": timestamp_now(), "pattern": "load_idle", "cycles": TEST_CYCLES,
                  "load_duration_seconds": LOAD_DURATION, "idle_duration_seconds": IDLE_DURATION, "events": events}
        filepath = RECORDINGS_DIR / f"fixed_pattern_{report['timestamp'].replace(':', '-').replace('.', '-')}.json"
        save_json(report, str(filepath))
        _LOG.info("Fixed pattern test complete; log saved to %s", filepath)
        return report
    finally:
        controller.cleanup()

def main() -> int:
    '''Run the fixed-pattern exercise and log failures.'''
    try:
        run_test()
    except (OSError, RuntimeError, KeyboardInterrupt) as error:
        _LOG.exception("Fixed pattern test failed: %s", error)
        return 1
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
