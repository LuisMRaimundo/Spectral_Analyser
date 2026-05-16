"""Formula validation Pass 13 — peak detection and f0 refinement (validation plan only)."""

from __future__ import annotations

import numpy as np
import numpy.testing as npt

import proc_audio


# Case PP-1
def test_parabolic_peak_symmetric_vertex() -> None:
    y = [1.0, 2.0, 1.0, 1.0]
    xv, yv = proc_audio._parabolic_peak(y, 1)
    npt.assert_allclose([xv, yv], [1.0, 2.0], rtol=0.0, atol=1e-15)


# Case PP-2
def test_parabolic_peak_nonzero_offset() -> None:
    y = [2.0, 3.0, 0.0]
    xv, yv = proc_audio._parabolic_peak(y, 1)
    npt.assert_allclose(xv, 0.75, rtol=0.0, atol=1e-15)
    npt.assert_allclose(yv, 3.125, rtol=0.0, atol=1e-15)


# Case PI-1
def test_parabolic_interpolation_log_magnitude_flat_triplet() -> None:
    mags = np.ones(5, dtype=float)
    freq, valid = proc_audio._parabolic_interpolation_log_magnitude(
        mags, 2, 10.0, 1000.0
    )
    npt.assert_allclose(freq, 1020.0, rtol=0.0, atol=1e-12)
    assert valid is True


# Case PI-2
def test_parabolic_interpolation_log_magnitude_symmetric_linear_peak() -> None:
    mags = np.array([0.1, 1.0, 0.1], dtype=float)
    freq, valid = proc_audio._parabolic_interpolation_log_magnitude(
        mags, 1, 1.0, 0.0
    )
    npt.assert_allclose(freq, 1.0, rtol=0.0, atol=1e-12)
    assert valid is True


# Case RI-1
def test_refine_peak_index_window_argmax() -> None:
    mags = np.array([0.0, 1.0, 0.0, 5.0, 4.0], dtype=float)
    out = proc_audio._refine_peak_index(mags, 2, refine_radius=2)
    assert out == 3


# Case IB-1
def test_infer_bin_spacing_uniform_grid() -> None:
    freqs = np.array([100.0, 110.0, 120.0], dtype=float)
    out = proc_audio._infer_bin_spacing_from_freqs(freqs)
    npt.assert_allclose(out, 10.0, rtol=0.0, atol=1e-15)


# Case IB-2
def test_infer_bin_spacing_odd_median() -> None:
    freqs = np.array([0.0, 10.0, 25.0, 40.0], dtype=float)
    out = proc_audio._infer_bin_spacing_from_freqs(freqs)
    npt.assert_allclose(out, 15.0, rtol=0.0, atol=1e-15)


# Case RC-1
def test_refine_candidate_to_interpolated_peak_nearest_and_db() -> None:
    freqs = np.linspace(440.0, 460.0, 11)
    mags = np.full(11, 1e-6, dtype=float)
    mags[5] = 2.0
    out = proc_audio._refine_candidate_to_interpolated_peak(
        candidate_freq_hz=451.0,
        complete_magnitudes=mags,
        complete_freqs=freqs,
        refine_radius=2,
    )
    assert out["peak_bin_index"] == 5
    npt.assert_allclose(out["bin_center_frequency_hz"], 450.0, rtol=0.0, atol=1e-12)
    npt.assert_allclose(
        out["peak_magnitude_db"], 20.0 * np.log10(2.0), rtol=0.0, atol=1e-12
    )
    npt.assert_allclose(
        out["interpolated_frequency_hz"],
        out["bin_center_frequency_hz"],
        rtol=0.0,
        atol=1e-9,
    )


# Case SP-1
def test_saddle_prominence_db_symmetric_shoulders() -> None:
    mags = np.ones(11, dtype=float)
    mags[5] = 100.0
    prom = proc_audio._saddle_prominence_db(mags, 5, saddle_window=3)
    npt.assert_allclose(prom, 40.0, rtol=0.0, atol=1e-9)


# Case SP-2
def test_saddle_prominence_db_edge_returns_neg_inf() -> None:
    mags = np.ones(3, dtype=float)
    prom = proc_audio._saddle_prominence_db(mags, 0)
    assert prom == float("-inf")


# Case LV-1
def test_is_local_peak_valid_synthetic_pass() -> None:
    mags = np.full(21, 0.01, dtype=float)
    mags[10] = 100.0
    is_valid, snr_db = proc_audio._is_local_peak_valid(
        mags,
        10,
        threshold_db=3.0,
        noise_floor_percentile=15.0,
        window_size=5,
        saddle_window=3,
    )
    assert bool(is_valid) is True
    assert snr_db > 3.0


# Case LM-1
def test_local_peak_metrics_matches_saddle_delegate() -> None:
    mags = np.full(21, 0.01, dtype=float)
    mags[10] = 100.0
    is_lp, snr_db, prom = proc_audio._local_peak_metrics(mags, 10)
    assert bool(is_lp) is True
    assert snr_db > 0.0
    ref = proc_audio._saddle_prominence_db(mags, 10, saddle_window=10)
    npt.assert_allclose(prom, ref, rtol=0.0, atol=1e-12)


# Case CF-1
def test_correct_f0_candidate_octave_drop() -> None:
    out = proc_audio._correct_f0_candidate_against_prior(880.0, 440.0)
    assert bool(out["valid"]) is True
    npt.assert_allclose(out["corrected_hz"], 440.0, rtol=0.0, atol=1e-12)
    npt.assert_allclose(out["cents_error"], 0.0, rtol=0.0, atol=1e-9)


# Case CF-2
def test_correct_f0_candidate_identity() -> None:
    c4 = 440.0 * 2.0 ** ((60.0 - 69.0) / 12.0)
    out = proc_audio._correct_f0_candidate_against_prior(c4, c4)
    assert bool(out["valid"]) is True
    npt.assert_allclose(out["corrected_hz"], c4, rtol=0.0, atol=1e-9)
    npt.assert_allclose(out["cents_error"], 0.0, rtol=0.0, atol=1e-9)


# Case BS-1
def test_calculate_bin_spacing() -> None:
    out = proc_audio._calculate_bin_spacing(48000.0, 4096, 2)
    npt.assert_allclose(out, 48000.0 / (4096.0 * 2.0), rtol=1e-15, atol=0.0)


# Case FN-1
def test_frequency_to_note_name_a4() -> None:
    s = proc_audio.frequency_to_note_name(440.0, 440.0)
    assert "A4" in s
    assert ("+0.00" in s) or ("-0.00" in s)


# Case FN-2
def test_frequency_to_note_name_one_semitone_up() -> None:
    f = 440.0 * 2.0 ** (1.0 / 12.0)
    s = proc_audio.frequency_to_note_name(f, 440.0)
    assert "A#4" in s


# Case CF0-1
def test_calculate_fundamental_frequency_numeric_string() -> None:
    proc = proc_audio.AudioProcessor()
    npt.assert_allclose(proc.calculate_fundamental_frequency("440"), 440.0, rtol=0.0, atol=1e-12)


# Case CF0-2
def test_calculate_fundamental_frequency_a4() -> None:
    proc = proc_audio.AudioProcessor()
    npt.assert_allclose(proc.calculate_fundamental_frequency("A4"), 440.0, rtol=1e-9, atol=0.0)


# Case CF0-3
def test_calculate_fundamental_frequency_c4() -> None:
    proc = proc_audio.AudioProcessor()
    expected = 440.0 * 2.0 ** ((60.0 - 69.0) / 12.0)
    npt.assert_allclose(
        proc.calculate_fundamental_frequency("C4"), expected, rtol=1e-9, atol=0.0
    )
