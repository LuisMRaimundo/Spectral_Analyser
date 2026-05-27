from __future__ import annotations

import pandas as pd

from acoustic_density_core import compute_acoustic_density_descriptors


def test_obs_w_s_stays_below_005_on_harmonic_like_note() -> None:
    peaks = pd.DataFrame(
        {
            "frequency_hz": [220.0, 440.0, 660.0, 880.0, 1100.0],
            "power": [10.0, 5.0, 3.0, 2.0, 1.5],
        }
    )
    out = compute_acoustic_density_descriptors(
        peaks,
        f0_hz=220.0,
        f0_fit_accepted=True,
    )
    assert float(out["pure_observation_w_s"]) < 0.05
