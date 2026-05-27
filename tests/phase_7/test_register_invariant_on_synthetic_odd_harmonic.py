from __future__ import annotations

import numpy as np
import pandas as pd

from acoustic_density_core import compute_acoustic_density_descriptors


def _odd_harmonic_peaks(f0_hz: float, ceiling_hz: float = 5000.0) -> pd.DataFrame:
    amps = [1.0, 0.5, 0.3, 0.2, 0.1]
    odd_orders = [1, 3, 5, 7, 9]
    freqs = []
    powers = []
    for n, a in zip(odd_orders, amps, strict=False):
        f = float(n) * float(f0_hz)
        if f <= ceiling_hz:
            freqs.append(f)
            powers.append(float(a * a))

    rng = np.random.default_rng(20260526)
    noise_freqs = rng.uniform(low=max(25.0, f0_hz * 0.8), high=ceiling_hz * 0.95, size=5)
    for f in noise_freqs.tolist():
        if min(abs(f - hf) for hf in freqs) > max(8.0, 0.03 * f0_hz):
            freqs.append(float(f))
            powers.append(float((0.06 ** 2)))
    return pd.DataFrame({"frequency_hz": freqs, "power": powers})


def test_register_invariant_odd_harmonic_low_and_high_register() -> None:
    low = compute_acoustic_density_descriptors(
        _odd_harmonic_peaks(147.0),
        f0_hz=147.0,
        f0_fit_accepted=True,
        density_summation_mode="his_note_adaptive",
    )
    high = compute_acoustic_density_descriptors(
        _odd_harmonic_peaks(2093.0),
        f0_hz=2093.0,
        f0_fit_accepted=True,
        density_summation_mode="his_note_adaptive",
    )
    assert float(low["pure_observation_w_h"]) >= 0.65
    assert float(high["pure_observation_w_h"]) >= 0.50
