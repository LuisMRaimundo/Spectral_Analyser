"""Formula validation Pass 5 — harmonic alignment (docs/formula_validation/)."""

import math

import numpy as np
import numpy.testing as npt
import pandas as pd

import harmonic_alignment


# Case 5-01
def test_cents_unison() -> None:
    out = harmonic_alignment._cents(440.0, 440.0)
    npt.assert_allclose(out, 0.0, rtol=0.0, atol=1e-12)


# Case 5-02
def test_cents_octave() -> None:
    out = harmonic_alignment._cents(880.0, 440.0)
    npt.assert_allclose(out, 1200.0, rtol=0.0, atol=1e-9)


# Case 5-03
def test_adaptive_tolerance_cents_floor() -> None:
    out = harmonic_alignment._adaptive_tolerance_cents(1000.0, None, None)
    assert out == 18.0


# Case 5-04
def test_adaptive_tolerance_cents_numeric() -> None:
    expected_hz = 100.0
    sr = 44100.0
    n_fft = 4096.0
    out = harmonic_alignment._adaptive_tolerance_cents(expected_hz, sr, int(n_fft))
    bin_w = sr / n_fft
    hi = expected_hz + bin_w / 2.0
    bw_cents = 1200.0 * math.log2(hi / expected_hz)
    manual = float(max(18.0, 2.0 * bw_cents))
    npt.assert_allclose(out, manual, rtol=0.0, atol=1e-6)


# Case 5-05
def test_harmonic_alignment_expected_slot_count() -> None:
    peaks = pd.DataFrame(
        {
            "Frequency (Hz)": [200.0],
            "Amplitude": [1.0],
        }
    )
    result = harmonic_alignment.compute_harmonic_alignment_metrics(
        100.0,
        peaks,
        max_frequency_hz=500.0,
        subbass_cutoff_hz=-1.0,
    )
    assert int(result["total_expected_harmonic_orders"]) == 5
