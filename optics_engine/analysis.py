from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .tracing import TraceResult


@dataclass(frozen=True)
class SpotResult:
    arrived_count: int
    blocked_count: int
    failed_count: int
    centroid_y_mm: float | None
    centroid_z_mm: float | None
    rms_radius_mm: float | None


def analyze_spot(trace_result: TraceResult) -> SpotResult:
    mask = trace_result.arrived_mask
    arrived = int(np.sum(mask))
    blocked = int(np.sum(trace_result.status == "blocked"))
    failed = int(trace_result.status.size - arrived - blocked)
    if arrived == 0:
        return SpotResult(arrived, blocked, failed, None, None, None)

    y = trace_result.sensor_y_mm[mask]
    z = trace_result.sensor_z_mm[mask]
    cy = float(np.mean(y))
    cz = float(np.mean(z))
    rms = float(np.sqrt(np.mean((y - cy) ** 2 + (z - cz) ** 2)))
    return SpotResult(arrived, blocked, failed, cy, cz, rms)
