from __future__ import annotations

import math

import numpy as np
import pandas as pd

from acoustic_density_core import compute_acoustic_density_descriptors


def _synthetic_peak_table(f0_hz: float) -> pd.DataFrame:
    freqs = np.array([f0_hz * n for n in range(1, 16)], dtype=float)
    amps = np.array([1.0 / n for n in range(1, 16)], dtype=float)
    return pd.DataFrame(
        {
            "Frequency (Hz)": freqs,
            "Amplitude": amps,
            "Power": np.square(amps),
        }
    )


def test_true_harmonic_order_bounds_hold_for_20000hz_family() -> None:
    for f0_hz in (247.0, 440.0, 1047.0, 1760.0, 2349.0):
        desc = compute_acoustic_density_descriptors(_synthetic_peak_table(f0_hz), f0_hz=f0_hz)
        expected = int(desc.get("expected_harmonic_order_count_up_to_body_ceiling", 0) or 0)
        salient = int(desc.get("salient_harmonic_order_count_up_to_body_ceiling", 0) or 0)
        theoretical = int(math.floor(20000.0 / float(f0_hz)))

        assert expected <= theoretical
        assert salient <= expected
