# -*- coding: utf-8 -*-
"""Explicit energy-balance audit for harmonic / inharmonic / sub-bass components."""

from __future__ import annotations

import math
from typing import Any, Dict


def describe_component_energy_balance(
    harmonic_energy_sum: float,
    inharmonic_energy_sum: float,
    subbass_energy_sum: float,
    total_component_energy: float,
    harmonic_energy_ratio: float,
    inharmonic_energy_ratio: float,
    subbass_energy_ratio: float,
    *,
    eps: float = 1e-30,
) -> Dict[str, Any]:
    """
    Check internal consistency: reconstructed total from sums and ratio row sum ≈ 1.

    ``total_component_energy`` is expected to equal the sum of the three energy sums
    (same construction as ``proc_audio``).
    """
    h = float(harmonic_energy_sum) if math.isfinite(harmonic_energy_sum) else 0.0
    ih = float(inharmonic_energy_sum) if math.isfinite(inharmonic_energy_sum) else 0.0
    s = float(subbass_energy_sum) if math.isfinite(subbass_energy_sum) else 0.0
    tot = float(total_component_energy) if math.isfinite(total_component_energy) else 0.0
    den_parts = h + ih + s
    sum_err = abs(tot - den_parts) / max(abs(tot), abs(den_parts), eps)

    rh = float(harmonic_energy_ratio) if math.isfinite(harmonic_energy_ratio) else 0.0
    rih = float(inharmonic_energy_ratio) if math.isfinite(inharmonic_energy_ratio) else 0.0
    rs = float(subbass_energy_ratio) if math.isfinite(subbass_energy_ratio) else 0.0
    ratio_sum_err = abs(1.0 - (rh + rih + rs))

    status = "ok"
    if sum_err > 1e-6 or ratio_sum_err > 1e-5:
        status = "warning"

    return {
        "energy_denominator_description": (
            "total_component_energy := harmonic_energy_sum + inharmonic_energy_sum + subbass_energy_sum; "
            "ratios := each sum / total_component_energy"
        ),
        "energy_conservation_error": float(max(sum_err, ratio_sum_err)),
        "energy_conservation_status": status,
    }
