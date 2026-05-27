# -*- coding: utf-8 -*-
"""
Canonical low-frequency policy: subfundamental guard vs. fixed diagnostic band vs. DC.

This module does **not** implement density formulas or f0 estimation — only register-dependent
margins, optional leakage-aware lower bounds, and classification labels for audit exports.
"""

from __future__ import annotations

import math
import warnings
from typing import Any, Dict, Optional
from subbass_policy import SubBassPolicy

LOW_FREQUENCY_POLICY_VERSION = "dc_removed_adaptive_subfundamental_guard_v1"
_ADAPTIVE_SUBFUNDAMENTAL_SHIM_WARNED = False

SUBFUNDAMENTAL_CUTOFF_SELECTION_RULE: str = (
    "adaptive_subfundamental_cutoff_hz = min( max( min_floor_hz, "
    "percentage_subfundamental_cutoff_hz, optional_finite_leakage_guard_cutoff_hz ), "
    "f0_final_hz * max_fraction_of_f0 ); "
    "percentage_subfundamental_cutoff_hz = f0_final_hz * (1 - nominal_register_margin_percent/100); "
    "effective_subfundamental_margin_percent = 100 * (1 - adaptive_subfundamental_cutoff_hz / f0_final_hz)."
)


def _finite_positive(value: Any) -> bool:
    try:
        x = float(value)
    except Exception:
        return False
    return math.isfinite(x) and x > 0.0


def calculate_subfundamental_margin_percent(f0_hz: float) -> float:
    """
    Register-dependent safety margin below f0.

    This is not a physical sub-bass boundary. It is a note-dependent
    subfundamental guard to prevent low-frequency residual/DC/sub-f0
    artefacts from contaminating density-relevant metrics.
    """
    if not _finite_positive(f0_hz):
        return 10.0

    f0 = float(f0_hz)

    if f0 < 60.0:
        return 35.0
    if f0 < 120.0:
        return 25.0
    if f0 < 300.0:
        return 15.0
    return 10.0


def _nan_result() -> Dict[str, Any]:
    nan = float("nan")
    return {
        "low_frequency_policy_version": LOW_FREQUENCY_POLICY_VERSION,
        "f0_final_hz": nan,
        "subfundamental_margin_percent": nan,
        "percentage_subfundamental_cutoff_hz": nan,
        "leakage_guard_cutoff_hz": nan,
        "min_floor_hz": nan,
        "max_fraction_of_f0": nan,
        "adaptive_subfundamental_cutoff_hz": nan,
        "effective_subfundamental_margin_percent": nan,
        "subfundamental_guard_valid": False,
        "subfundamental_guard_policy": "invalid_f0",
        "subfundamental_cutoff_selection_rule": SUBFUNDAMENTAL_CUTOFF_SELECTION_RULE,
        "subfundamental_cutoff_selected_by": "none_invalid_f0",
    }


def calculate_adaptive_subfundamental_cutoff_hz(
    f0_hz: float,
    *,
    min_floor_hz: float = 20.0,
    max_fraction_of_f0: float = 0.95,
    leakage_guard_cutoff_hz: Optional[float] = None,
    sr_hz: Optional[float] = None,
    n_fft: Optional[int] = None,
) -> Dict[str, Any]:
    """
    deprecated, see SubBassPolicy.upper_bound_hz

    Legacy API retained for compatibility while unifying operational sub-bass
    boundary semantics across the codebase.
    """
    global _ADAPTIVE_SUBFUNDAMENTAL_SHIM_WARNED
    if not _ADAPTIVE_SUBFUNDAMENTAL_SHIM_WARNED:
        warnings.warn(
            "deprecated, see SubBassPolicy.upper_bound_hz",
            DeprecationWarning,
            stacklevel=2,
        )
        _ADAPTIVE_SUBFUNDAMENTAL_SHIM_WARNED = True

    result = _nan_result()
    if not _finite_positive(f0_hz):
        return result

    f0 = float(f0_hz)
    margin = calculate_subfundamental_margin_percent(f0)
    percentage_cut = f0 * (1.0 - margin / 100.0)

    floor = float(min_floor_hz)
    if not math.isfinite(floor) or floor < 0.0:
        floor = 20.0

    max_frac = float(max_fraction_of_f0)
    if not math.isfinite(max_frac) or max_frac <= 0.0:
        max_frac = 0.95
    cap_hz = f0 * max_frac

    leak_raw: float = float("nan")
    if leakage_guard_cutoff_hz is not None:
        try:
            lg_try = float(leakage_guard_cutoff_hz)
        except (TypeError, ValueError):
            lg_try = float("nan")
        if math.isfinite(lg_try) and lg_try > 0.0:
            leak_raw = float(lg_try)

    # Max stage: floor, nominal percentage line, optional leakage (all finite candidates).
    parts: list[tuple[float, str]] = [(floor, "min_floor_hz"), (percentage_cut, "percentage_subfundamental_cutoff_hz")]
    if math.isfinite(leak_raw) and leak_raw > 0.0:
        parts.append((leak_raw, "leakage_guard_cutoff_hz"))

    raw_max = max(p[0] for p in parts)
    eps = 1e-6 * max(1.0, f0)
    # Prefer leakage > percentage > min_floor when reporting ties at raw_max.
    _prio = {"leakage_guard_cutoff_hz": 3, "percentage_subfundamental_cutoff_hz": 2, "min_floor_hz": 1}
    at_raw = [p for p in parts if abs(p[0] - raw_max) <= eps]
    selected_raw = max(at_raw, key=lambda p: _prio.get(p[1], 0))[1]

    sr_eff = float(sr_hz) if _finite_positive(sr_hz) else 44100.0
    n_fft_eff = int(n_fft) if n_fft is not None else 0
    if n_fft_eff < 0:
        n_fft_eff = 0
    policy_bound = float(
        SubBassPolicy.upper_bound_hz(
            f0_hz=f0,
            sr_hz=sr_eff,
            n_fft=n_fft_eff,
        )
    )
    adaptive = min(policy_bound, cap_hz)
    if adaptive + eps < raw_max:
        selected_final = "max_fraction_of_f0_cap"
    else:
        selected_final = selected_raw

    eff_margin = 100.0 * (1.0 - adaptive / f0)

    result.update(
        {
            "f0_final_hz": float(f0),
            "subfundamental_margin_percent": float(margin),
            "percentage_subfundamental_cutoff_hz": float(percentage_cut),
            "leakage_guard_cutoff_hz": float(leak_raw) if math.isfinite(leak_raw) else float("nan"),
            "min_floor_hz": float(floor),
            "max_fraction_of_f0": float(max_frac),
            "adaptive_subfundamental_cutoff_hz": float(adaptive),
            "effective_subfundamental_margin_percent": float(eff_margin),
            "subfundamental_guard_valid": True,
            "subfundamental_guard_policy": "f0_adaptive_register_margin",
            "subfundamental_cutoff_selection_rule": SUBFUNDAMENTAL_CUTOFF_SELECTION_RULE,
            "subfundamental_cutoff_selected_by": str(selected_final),
        }
    )
    return result


def classify_low_frequency_row(
    f_hz: float,
    *,
    dc_floor_hz: float,
    physical_low_band_upper_hz: float,
    adaptive_subfundamental_cutoff_hz: float,
) -> str:
    """
    Label one spectral row inside the fixed diagnostic low-frequency band.

    ``dc_floor_hz`` is the upper edge of the DC / sub-audible bucket (Hz, inclusive boundary
    on the low side in the sense f <= dc_floor_hz → dc bucket — see callers).
    """
    try:
        f = float(f_hz)
    except (TypeError, ValueError):
        return "not_low_frequency_residual"
    if not math.isfinite(f):
        return "not_low_frequency_residual"
    try:
        ad = float(adaptive_subfundamental_cutoff_hz)
    except (TypeError, ValueError):
        ad = float("nan")
    if not math.isfinite(ad):
        ad = float("inf")
    if f <= float(dc_floor_hz):
        return "dc_or_subaudible_residual"
    if f < float(ad):
        return "subfundamental_residual"
    if f <= float(physical_low_band_upper_hz):
        return "physical_low_frequency_residual"
    return "not_low_frequency_residual"
