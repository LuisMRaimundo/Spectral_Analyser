from __future__ import annotations

import numpy as np
import pandas as pd

from acoustic_density_core import compute_acoustic_density_descriptors


def test_strength_terms_are_dimensionless_and_comparable() -> None:
    # Build near-uniform occupancy in each alphabet:
    # - Harmonic orders: fill n=1..5 for f0=1000 Hz under 5 kHz ceiling.
    # - Inharmonic bins: one residual peak per 100-cent bin from 80 Hz to 5 kHz.
    # - Sub-bass particles: dense local-maxima candidates in 20-80 Hz.
    f0 = 1000.0
    harmonic_freqs = [1000.0, 2000.0, 3000.0, 4000.0, 5000.0]
    inharmonic_freqs = list(np.geomspace(80.0, 5000.0, 72).astype(float))
    subbass_freqs = [22.0, 33.0, 44.0, 55.0, 66.0, 77.0]
    freqs = harmonic_freqs + inharmonic_freqs + subbass_freqs
    powers = [1.0] * len(harmonic_freqs) + [1.0] * len(inharmonic_freqs) + [1.0] * len(subbass_freqs)
    peaks = pd.DataFrame({"frequency_hz": freqs, "power": powers})
    out = compute_acoustic_density_descriptors(
        peaks,
        f0_hz=f0,
        f0_fit_accepted=True,
        density_summation_mode="his_note_adaptive",
    )
    terms = [
        float(out["component_strength_h"]),
        float(out["component_strength_i"]),
        float(out["component_strength_s"]),
    ]
    for t in terms:
        assert 0.0 <= t <= 2.1
    assert max(terms) - min(terms) <= 0.6
