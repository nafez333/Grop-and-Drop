"""Automatic signal threshold estimators."""
from __future__ import annotations
from typing import List, Sequence, Union
import numpy as np
NumericSequence = Union[Sequence[float], np.ndarray]

class ThresholdCalculator:
    """Compute fixed and adaptive thresholds from numeric signal samples."""
    def compute_from_idle(self, data: NumericSequence, idle_start: float, idle_end: float) -> float:
        values = np.asarray(data, dtype=float).reshape(-1)
        if idle_start < 0 or idle_end < idle_start:
            raise ValueError("idle bounds must satisfy 0 <= idle_start <= idle_end")
        segment = values[int(idle_start):int(idle_end)]
        if segment.size == 0 or not np.all(np.isfinite(segment)):
            raise ValueError("idle segment is empty or contains non-finite values")
        return float(np.mean(segment) + 2.0 * np.std(segment, ddof=0))

    def compute_adaptive(self, data: NumericSequence, window: int = 50) -> List[float]:
        values = np.asarray(data, dtype=float).reshape(-1)
        if window <= 0:
            raise ValueError("window must be positive")
        half = max(1, int(window) // 2)
        result: List[float] = []
        for index in range(values.size):
            section = values[max(0, index - half):min(values.size, index + half + 1)]
            result.append(float(np.mean(section) + 1.5 * np.std(section, ddof=0)))
        return result
    def compute_otsu(self, data: NumericSequence) -> float:
        values = np.asarray(data, dtype=float).reshape(-1)
        if values.size == 0:
            raise ValueError("data must not be empty")
        if not np.all(np.isfinite(values)):
            raise ValueError("data must contain only finite values")
        low, high = float(np.min(values)), float(np.max(values))
        if low == high:
            return low
        histogram, edges = np.histogram(values, bins=100, range=(low, high))
        probabilities = histogram.astype(float) / values.size
        centers = (edges[:-1] + edges[1:]) / 2.0
        omega = np.cumsum(probabilities)
        mean = np.cumsum(probabilities * centers)
        total_mean = mean[-1]
        denominator = omega * (1.0 - omega)
        variance = np.zeros_like(denominator)
        valid = denominator > 0
        variance[valid] = ((total_mean * omega[valid] - mean[valid]) ** 2) / denominator[valid]
        return float(centers[int(np.argmax(variance))])

    def compute_percentile(self, data: NumericSequence, percentile: float = 75.0) -> float:
        values = np.asarray(data, dtype=float).reshape(-1)
        if values.size == 0:
            raise ValueError("data must not be empty")
        if not 0 <= percentile <= 100:
            raise ValueError("percentile must be between 0 and 100")
        return float(np.percentile(values, percentile))


def compute_threshold(data: list, idle_segments: list) -> float:
    """Shared interface: threshold separating idle noise from signal amplitudes."""
    values = np.asarray(data, dtype=float).reshape(-1)
    if values.size == 0:
        raise ValueError("data must not be empty")
    idle_values: List[float] = []
    for segment in idle_segments:
        if isinstance(segment, (tuple, list)) and len(segment) == 2:
            start, end = max(0, int(segment[0])), min(values.size, int(segment[1]))
            idle_values.extend(values[start:end].tolist())
        elif isinstance(segment, (tuple, list, np.ndarray)):
            idle_values.extend(np.asarray(segment, dtype=float).reshape(-1).tolist())
    if not idle_values:
        return ThresholdCalculator().compute_otsu(values)
    idle = np.asarray(idle_values, dtype=float)
    median = float(np.median(idle))
    spread = float(np.median(np.abs(idle - median))) * 1.4826
    return median + max(3.0 * spread, np.finfo(float).eps)
