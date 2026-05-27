from __future__ import annotations

import math

from acoustic_density_core import deprecated_subbass_upper_bound_hz_from_ratio
from constants import deprecated_subbass_aggregate_cutoff_hz
from low_frequency_policy import calculate_adaptive_subfundamental_cutoff_hz


def test_legacy_callers_resolve_single_subbass_upper_bound() -> None:
    f0_hz = 220.0
    sr_hz = 48000.0
    n_fft = 4096

    bound_from_constant_shim = deprecated_subbass_aggregate_cutoff_hz(
        f0_hz=f0_hz,
        sr_hz=sr_hz,
        n_fft=n_fft,
    )
    bound_from_ratio_shim = deprecated_subbass_upper_bound_hz_from_ratio(
        f0_hz=f0_hz,
        sr_hz=sr_hz,
        n_fft=n_fft,
        subbass_upper_ratio=0.75,
    )
    guard = calculate_adaptive_subfundamental_cutoff_hz(
        f0_hz=f0_hz,
        sr_hz=sr_hz,
        n_fft=n_fft,
    )
    bound_from_low_frequency_policy = float(guard["adaptive_subfundamental_cutoff_hz"])

    assert math.isfinite(bound_from_constant_shim)
    assert bound_from_constant_shim == bound_from_ratio_shim
    assert bound_from_constant_shim == bound_from_low_frequency_policy
