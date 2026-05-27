from __future__ import annotations

"""
Canonical sub-bass boundary policy.

The operational upper boundary for sub-bass is defined as:

    min(f0_hz * 0.5, 80.0)

This intersects a sub-fundamental guard (below half the fundamental) with the
perceptual sub-bass region near Bark bands 0-1.

Reference
---------
Zwicker, E., & Fastl, H. (1990). *Psychoacoustics: Facts and models*.
Springer.
"""

import math


class SubBassPolicy:
    @staticmethod
    def upper_bound_hz(f0_hz: float, sr_hz: float, n_fft: int) -> float:
        del sr_hz, n_fft  # reserved for future policy refinement
        try:
            f0 = float(f0_hz)
        except (TypeError, ValueError):
            return 80.0
        if not math.isfinite(f0) or f0 <= 0.0:
            return 80.0
        return float(min(f0 * 0.5, 80.0))
