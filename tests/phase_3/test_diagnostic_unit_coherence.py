from __future__ import annotations

import math

import pandas as pd

from acoustic_density_core import compute_acoustic_density_descriptors


def _synthetic_peaks() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "frequency_hz": [
                50.0,    # subbass
                110.0,   # harmonic 1
                220.0,   # harmonic 2
                330.0,   # harmonic 3
                470.0,   # residual/inharmonic
                690.0,   # residual/inharmonic
            ],
            "power": [
                0.2,
                10.0,
                5.5,
                3.0,
                1.2,
                0.8,
            ],
        }
    )


def test_diagnostic_terms_are_finite_nonnegative_effective_counts() -> None:
    out = compute_acoustic_density_descriptors(
        _synthetic_peaks(),
        f0_hz=110.0,
        f0_fit_accepted=True,
    )

    for key in (
        "diagnostic_effective_components_h",
        "diagnostic_effective_components_r",
        "diagnostic_effective_components_s",
        "effective_components_weighted_diagnostic",
    ):
        value = out[key]
        assert isinstance(value, float)
        assert math.isfinite(value)
        assert value >= 0.0
