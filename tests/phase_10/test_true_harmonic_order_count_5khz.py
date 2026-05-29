from __future__ import annotations

import math

import numpy as np
import pandas as pd

from acoustic_density_core import compute_acoustic_density_descriptors


def _harmonic_table(f0_hz: float) -> pd.DataFrame:
    freqs = np.array([f0_hz * n for n in range(1, 28)], dtype=float)
    amps = np.array([1.0 / n for n in range(1, 28)], dtype=float)
    return pd.DataFrame({"Frequency (Hz)": freqs, "Amplitude": amps, "Power": amps**2})


def test_true_harmonic_order_count_body_ceiling_bounds() -> None:
    representative = {
        "B3": 246.94,
        "A4": 440.00,
        "D5": 587.33,
        "A5": 880.00,
        "A6": 1760.00,
    }
    for _, f0 in representative.items():
        out = compute_acoustic_density_descriptors(_harmonic_table(f0), f0_hz=f0)
        theoretical = int(math.floor(20000.0 / float(f0)))
        assert int(out["theoretical_harmonic_order_count_up_to_body_ceiling"]) == theoretical
        assert int(out["detected_salient_harmonic_order_count_up_to_body_ceiling"]) <= int(
            out["theoretical_harmonic_order_count_up_to_body_ceiling"]
        )
