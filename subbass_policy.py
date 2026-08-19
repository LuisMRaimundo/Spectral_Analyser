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
from typing import Any, Dict


SUBBASS_BOUND_FORMULA: str = "min(0.5*f0, 80)"
SUBBASS_BOUND_CAP_HZ: float = 80.0


class SubBassPolicy:
    @staticmethod
    def resolve_f020_bound(f0_hz: float) -> Dict[str, Any]:
        """Single F-020 bound used by every export sheet."""
        try:
            f0 = float(f0_hz)
        except (TypeError, ValueError):
            f0 = float("nan")
        if not math.isfinite(f0) or f0 <= 0.0:
            return {
                "subbass_upper_bound_hz": float(SUBBASS_BOUND_CAP_HZ),
                "subbass_bound_formula": SUBBASS_BOUND_FORMULA,
                "subbass_bound_f0_used_hz": float("nan"),
            }
        return {
            "subbass_upper_bound_hz": float(min(0.5 * f0, SUBBASS_BOUND_CAP_HZ)),
            "subbass_bound_formula": SUBBASS_BOUND_FORMULA,
            "subbass_bound_f0_used_hz": float(f0),
        }

    @staticmethod
    def upper_bound_hz(f0_hz: float, sr_hz: float = 0.0, n_fft: int = 0) -> float:
        del sr_hz, n_fft  # reserved for future policy refinement
        return float(SubBassPolicy.resolve_f020_bound(f0_hz)["subbass_upper_bound_hz"])
