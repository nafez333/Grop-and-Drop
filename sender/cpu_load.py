'''Cross-platform CPU-load modulation with managed multiprocessing workers.'''
from __future__ import annotations
import atexit
import math
import multiprocessing as mp
import signal
import threading
import time
from typing import List, Optional, Tuple
import psutil
from shared.constants import CPU_LOAD_PERIOD_SECONDS, CPU_TARGET_MAX, CPU_TARGET_MIN, PROCESS_JOIN_TIMEOUT_SECONDS
from shared.logger import get_logger
_LOG = get_logger(__name__)

def _load_worker(stop_event: mp.synchronize.Event, duty_cycle: float, period: float) -> None:
    '''Consume CPU for the requested fraction of each period until stopped.'''
    while not stop_event.is_set():
        cycle_start = time.perf_counter()
        work_until = cycle_start + period * duty_cycle
        while time.perf_counter() < work_until:
            if stop_event.is_set():
                return
        remaining = period - (time.perf_counter() - cycle_start)
        if remaining > 0:
            stop_event.wait(remaining)

class CPULoadController:
    '''Start, stop and measure isolated CPU load worker processes.'''
    def __init__(self, target_percent: int = CPU_TARGET_MAX) -> None:
        '''Initialize process tracking and register best-effort global cleanup.'''
        if isinstance(target_percent, bool) or not isinstance(target_percent, int):
            raise TypeError("target_percent must be an integer")
        if not CPU_TARGET_MIN <= target_percent <= CPU_TARGET_MAX:
            raise ValueError(f"target_percent must be between {CPU_TARGET_MIN} and {CPU_TARGET_MAX}")
        self.target_percent = int(target_percent)
        self._workers: List[Tuple[mp.Process, object]] = []
        self._lock = threading.RLock()
        self._closed = False
        self._previous_handlers = {}
        self._atexit_callback = self.cleanup
        atexit.register(self._atexit_callback)
        if threading.current_thread() is threading.main_thread():
            for signum in (signal.SIGINT, signal.SIGTERM):
                try:
                    self._previous_handlers[signum] = signal.getsignal(signum)
                    signal.signal(signum, self._handle_signal)
                except (ValueError, OSError):
                    _LOG.debug("Could not register signal handler for %s", signum, exc_info=True)

    def _handle_signal(self, signum: int, frame: object) -> None:
        '''Stop child processes before delegating or terminating on a signal.'''
        previous = self._previous_handlers.get(signum, signal.SIG_DFL)
        self.cleanup()
        if callable(previous):
            previous(signum, frame)
        elif previous == signal.SIG_DFL:
            raise KeyboardInterrupt(f"received signal {signum}")

    def _spawn_workers(self) -> None:
        '''Start enough worker processes to approximate machine-wide target load.'''
        if self._closed:
            raise RuntimeError("controller has already been cleaned up")
        core_count = max(1, psutil.cpu_count(logical=True) or 1)
        desired_cores = core_count * self.target_percent / CPU_TARGET_MAX
        process_count = max(CPU_TARGET_MIN, int(math.ceil(desired_cores)))
        try:
            for index in range(process_count):
                duty = min(1.0, max(0.0, desired_cores - index))
                if duty <= 0:
                    continue
                event = mp.Event()
                process = mp.Process(target=_load_worker, args=(event, duty, CPU_LOAD_PERIOD_SECONDS),
                                     name=f"cpu-load-worker-{index}", daemon=False)
                try:
                    process.start()
                except (OSError, RuntimeError):
                    event.set()
                    process.close()
                    raise
                self._workers.append((process, event))
        except (OSError, RuntimeError):
            self.stop_load()
            _LOG.exception("Failed starting one or more CPU workers; existing workers stopped")
            raise
        if not self._workers and self.target_percent > CPU_TARGET_MIN:
            raise RuntimeError("no CPU load worker process could be started")
        _LOG.info("CPU load active: target=%d%%, workers=%d", self.target_percent, len(self._workers))

    def start_load(self, duration_seconds: float) -> None:
        '''Run target CPU load for the specified duration, then stop all workers.'''
        if not isinstance(duration_seconds, (int, float)) or not math.isfinite(float(duration_seconds)) or duration_seconds < 0:
            raise ValueError("duration_seconds must be a finite non-negative number")
        with self._lock:
            self.stop_load()
            if duration_seconds == 0:
                _LOG.info("CPU load duration is zero; no workers started")
                return
            self._spawn_workers()
        try:
            deadline = time.monotonic() + duration_seconds
            while time.monotonic() < deadline:
                time.sleep(min(CPU_LOAD_PERIOD_SECONDS, deadline - time.monotonic()))
        except (KeyboardInterrupt, OSError):
            _LOG.warning("CPU load interrupted; stopping workers", exc_info=True)
            raise
        finally:
            self.stop_load()

    def stop_load(self) -> None:
        '''Signal and join all running load processes without leaving orphans.'''
        with self._lock:
            workers, self._workers = self._workers, []
            if not workers:
                return
            for process, event in workers:
                event.set()
            for process, _event in workers:
                process.join(timeout=PROCESS_JOIN_TIMEOUT_SECONDS)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=PROCESS_JOIN_TIMEOUT_SECONDS)
                if process.is_alive() and hasattr(process, "kill"):
                    process.kill()
                    process.join(timeout=PROCESS_JOIN_TIMEOUT_SECONDS)
                if process.is_alive():
                    _LOG.error("Worker process %s did not exit after terminate/kill", process.name)
                else:
                    _LOG.debug("CPU worker %s stopped", process.name)
                    process.close()
            _LOG.info("CPU load stopped")

    def idle(self, duration_seconds: float) -> None:
        '''Keep CPU modulation idle for the specified duration.'''
        if not isinstance(duration_seconds, (int, float)) or not math.isfinite(float(duration_seconds)) or duration_seconds < 0:
            raise ValueError("duration_seconds must be a finite non-negative number")
        self.stop_load()
        _LOG.info("CPU state idle for %.3f seconds", duration_seconds)
        if duration_seconds:
            time.sleep(duration_seconds)

    def get_cpu_percent(self) -> float:
        '''Return measured total-system CPU utilization as a percentage.'''
        try:
            return float(psutil.cpu_percent(interval=None))
        except (psutil.Error, OSError):
            _LOG.exception("Unable to measure CPU utilization")
            return 0.0
    def cleanup(self) -> None:
        '''Idempotently stop all workers and restore previously installed handlers.'''
        with self._lock:
            if self._closed:
                return
            self.stop_load()
            for signum, previous in self._previous_handlers.items():
                try:
                    if threading.current_thread() is threading.main_thread():
                        signal.signal(signum, previous)
                except (ValueError, OSError):
                    _LOG.debug("Could not restore signal handler %s", signum, exc_info=True)
            self._previous_handlers.clear()
            self._closed = True
            try:
                atexit.unregister(self._atexit_callback)
            except (AttributeError, RuntimeError):
                _LOG.debug("Could not unregister controller cleanup callback", exc_info=True)
            _LOG.info("CPU load controller cleaned up")
