from __future__ import annotations

import warnings

import pandas as pd

from acoustic_density_core import compute_acoustic_density_descriptors


def _synthetic_peaks(f0_hz: float) -> pd.DataFrame:
    freqs = [f0_hz, 2.0 * f0_hz, 3.0 * f0_hz, 0.4 * f0_hz, 1.41 * f0_hz]
    powers = [1.0, 0.4, 0.2, 0.03, 0.01]
    return pd.DataFrame({"frequency_hz": freqs, "power": powers})


def test_no_operational_subbass_deprecation_warning() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        _ = compute_acoustic_density_descriptors(
            _synthetic_peaks(220.0),
            f0_hz=220.0,
            f0_fit_accepted=True,
            density_summation_mode="his_note_adaptive",
        )

    offending = [
        str(w.message)
        for w in rec
        if issubclass(w.category, DeprecationWarning)
        and "SubBassPolicy.upper_bound_hz" in str(w.message)
    ]
    assert offending == []
