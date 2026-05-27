from __future__ import annotations

import warnings

import numpy as np

from density import aggregate_subbass_noise_peak_power


def test_aggregate_subbass_wrapper_emits_deprecation_warning() -> None:
    freq = np.array([30.0, 40.0, 60.0], dtype=float)
    amp = np.array([1.0, 0.8, 0.4], dtype=float)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        _ = aggregate_subbass_noise_peak_power(
            freqs_hz=freq,
            amplitudes=amp,
            subbass_hz=80.0,
        )
    assert any(issubclass(w.category, DeprecationWarning) for w in rec)
