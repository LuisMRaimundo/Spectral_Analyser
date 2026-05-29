from __future__ import annotations

import numpy as np
import pandas as pd

from acoustic_density_core import compute_acoustic_density_descriptors


def _harmonic_dominant_peaks(f0_hz: float) -> pd.DataFrame:
    orders = [1, 2, 3, 4, 5, 6]
    amps = [1.0, 0.7, 0.45, 0.3, 0.2, 0.12]
    freqs = [float(n) * float(f0_hz) for n in orders if float(n) * float(f0_hz) <= 20000.0]
    powers = [float(a * a) for n, a in zip(orders, amps, strict=False) if float(n) * float(f0_hz) <= 20000.0]
    # Small deterministic off-harmonic bed.
    freqs.extend([float(f0_hz * 1.37), float(f0_hz * 2.63)])
    powers.extend([0.0036, 0.0025])
    return pd.DataFrame({"frequency_hz": freqs, "power": powers})


def test_obs_wh_is_register_invariant_across_f0_grid() -> None:
    f0s = [150.0, 300.0, 600.0, 1200.0, 2400.0]
    wh = []
    for f0 in f0s:
        out = compute_acoustic_density_descriptors(
            _harmonic_dominant_peaks(f0),
            f0_hz=f0,
            f0_fit_accepted=True,
            density_summation_mode="his_note_adaptive",
        )
        wh.append(float(out["pure_observation_w_h"]))
    mean_wh = float(np.mean(wh))
    for value in wh:
        assert abs(value - mean_wh) <= 0.15
