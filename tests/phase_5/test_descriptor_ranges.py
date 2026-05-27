from __future__ import annotations

import math

import numpy as np

from mir_descriptors import compute_mir_descriptors_from_spectrum


def test_descriptor_ranges_on_synthetic_signal() -> None:
    freqs = np.array([110.0, 220.0, 330.0, 440.0, 550.0, 770.0], dtype=float)
    amps = np.array([1.0, 0.7, 0.45, 0.35, 0.20, 0.10], dtype=float)
    desc = compute_mir_descriptors_from_spectrum(
        frequencies_hz=freqs,
        amplitudes=amps,
        f0_hz=110.0,
    )

    assert math.isfinite(desc["spectral_centroid_hz"])
    assert desc["spectral_centroid_hz"] >= 0.0
    assert math.isfinite(desc["spectral_spread_hz"])
    assert desc["spectral_spread_hz"] >= 0.0
    assert math.isfinite(desc["spectral_skewness"])
    assert math.isfinite(desc["spectral_kurtosis"])
    assert math.isfinite(desc["spectral_irregularity"])
    assert 0.0 <= desc["spectral_irregularity"] <= 1.0

    t1 = desc["tristimulus_1_fundamental"]
    t2 = desc["tristimulus_2_low_harmonics_2_to_4"]
    t3 = desc["tristimulus_3_high_harmonics_5_plus"]
    assert 0.0 <= t1 <= 1.0
    assert 0.0 <= t2 <= 1.0
    assert 0.0 <= t3 <= 1.0
    assert abs((t1 + t2 + t3) - 1.0) <= 1e-9

    assert 0.0 <= desc["spectral_flatness"] <= 1.0
    assert desc["spectral_rolloff_hz_85"] >= 0.0
    assert desc["spectral_rolloff_hz_95"] >= desc["spectral_rolloff_hz_85"]
    assert desc["roughness_aures_1985"] >= 0.0
    assert desc["erb_weighted_spectral_density"] >= 0.0
