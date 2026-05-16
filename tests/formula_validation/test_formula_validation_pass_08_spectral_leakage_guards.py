"""Formula validation Pass 8 — spectral leakage guards (docs/formula_validation/)."""

import numpy as np
import numpy.testing as npt

import spectral_leakage_guards


# Case 8-01
def test_leakage_halfwidth_hz_default_main_lobe() -> None:
    out = spectral_leakage_guards.leakage_halfwidth_hz(sr=44100.0, n_fft=4096)
    expected = 0.5 * 4.0 * (44100.0 / 4096.0)
    npt.assert_allclose(out, expected, rtol=0.0, atol=1e-3)


# Case 8-02
def test_filter_inharmonic_peak_candidates_drops_near_harmonic() -> None:
    out = spectral_leakage_guards.filter_inharmonic_peak_candidates(
        [(100.5, 1.0)],
        [100.0],
        leakage_halfwidth_hz=2.0,
    )
    assert len(out) == 0
