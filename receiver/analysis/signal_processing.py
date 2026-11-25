"""Small, dependency-light signal conditioning helpers for receiver recordings."""
from __future__ import annotations
from typing import List, Sequence, Union
import numpy as np
NumericSequence = Union[Sequence[float], np.ndarray]


def moving_average(data: NumericSequence, window: int) -> List[float]:
    """Return a centered moving average, preserving the input length."""
    values = np.asarray(data, dtype=float).reshape(-1)
    if window <= 0:
        raise ValueError("window must be positive")
    if values.size == 0:
        return []
    width = min(int(window), int(values.size))
    kernel = np.ones(width, dtype=float) / width
    left = (width - 1) // 2
    right = width - 1 - left
    padded = np.pad(values, (left, right), mode="edge")
    return np.convolve(padded, kernel, mode="valid").astype(float).tolist()


def low_pass_filter(data: NumericSequence, cutoff_hz: float, sample_rate: float) -> List[float]:
    """Apply a first-order Butterworth-style low-pass using a stable RC filter."""
    values = np.asarray(data, dtype=float).reshape(-1)
    if sample_rate <= 0 or cutoff_hz <= 0:
        raise ValueError("sample_rate and cutoff_hz must be positive")
    if values.size == 0:
        return []
    cutoff = min(float(cutoff_hz), float(sample_rate) * 0.499)
    dt = 1.0 / float(sample_rate)
    rc = 1.0 / (2.0 * np.pi * cutoff)
    alpha = dt / (rc + dt)
    result = np.empty_like(values)
    result[0] = values[0]
    for index in range(1, values.size):
        result[index] = result[index - 1] + alpha * (values[index] - result[index - 1])
    return result.tolist()


def baseline_correction(data: NumericSequence, baseline_segment: NumericSequence) -> List[float]:
    """Subtract the median baseline level from each sample."""
    values = np.asarray(data, dtype=float).reshape(-1)
    baseline = np.asarray(baseline_segment, dtype=float).reshape(-1)
    if baseline.size == 0:
        raise ValueError("baseline_segment must not be empty")
    if not np.all(np.isfinite(baseline)):
        raise ValueError("baseline_segment contains non-finite values")
    return (values - float(np.median(baseline))).astype(float).tolist()


def compute_magnitude(x: float, y: float, z: float) -> float:
    """Compute the Euclidean magnitude of a three-axis vector."""
    return float(np.sqrt(float(x) ** 2 + float(y) ** 2 + float(z) ** 2))


def normalize(data: NumericSequence) -> List[float]:
    """Min-max normalize values to [0, 1]; constant arrays become zeros."""
    values = np.asarray(data, dtype=float).reshape(-1)
    if values.size == 0:
        return []
    low = float(np.min(values))
    span = float(np.max(values) - low)
    if span <= np.finfo(float).eps:
        return np.zeros_like(values).tolist()
    return ((values - low) / span).tolist()
