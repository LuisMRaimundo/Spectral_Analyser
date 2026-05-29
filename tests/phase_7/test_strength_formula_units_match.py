from __future__ import annotations

import numpy as np
import pandas as pd

from acoustic_density_core import compute_acoustic_density_descriptors


def test_strength_terms_are_dimensionless_and_comparable() -> None:
    # Build near-uniform occupancy in each alphabet:
    # - Harmonic orders: fill n=1..5 for f0=800 Hz under body ceiling.
    # - Inharmonic bins: one residual peak per 100-cent bin from 80 Hz to body ceiling.
    # - Sub-bass particles: dense local-maxima candidates in 20-80 Hz.
    body_ceiling_hz = 4800.0
    f0 = 800.0
    harmonic_freqs = [800.0, 1600.0, 2400.0, 3200.0, 4000.0]
    inharmonic_freqs = list(np.geomspace(80.0, body_ceiling_hz, 72).astype(float))
    subbass_freqs = [22.0, 33.0, 44.0, 55.0, 66.0, 77.0]
    freqs = harmonic_freqs + inharmonic_freqs + subbass_freqs
    powers = [1.0] * len(harmonic_freqs) + [1.0] * len(inharmonic_freqs) + [1.0] * len(subbass_freqs)
    peaks = pd.DataFrame({"frequency_hz": freqs, "power": powers})
    out = compute_acoustic_density_descriptors(
        peaks,
        f0_hz=f0,
        f0_fit_accepted=True,
        density_summation_mode="his_note_adaptive",
        body_freq_max_hz=body_ceiling_hz,
        density_frequency_ceiling_hz=body_ceiling_hz,
    )
    terms = [
        float(out["component_strength_h"]),
        float(out["component_strength_i"]),
        float(out["component_strength_s"]),
    ]
    for t in terms:
        assert 0.0 <= t <= 2.1
    assert max(terms) - min(terms) <= 0.6
