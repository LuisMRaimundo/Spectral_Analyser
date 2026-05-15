"""Formula validation Pass 10 — selected proc_audio formulas (docs/formula_validation/)."""

import math

import numpy as np
import numpy.testing as npt
import pytest

import proc_audio


# Case 10-01
def test_normalize_level_rms_unity_gain() -> None:
    y = np.ones(4, dtype=float)
    y_out = proc_audio._normalize_level(y, target_rms_db=0.0)
    rms_out = float(np.sqrt(np.mean(np.square(y_out))))
    npt.assert_allclose(rms_out, 1.0, rtol=0.0, atol=1e-9)


# Case 10-02
def test_normalize_level_gain_from_minus_20_db_rms() -> None:
    y = np.full(64, 0.1, dtype=float)
    y_out = proc_audio._normalize_level(y, target_rms_db=0.0)
    npt.assert_allclose(float(np.max(np.abs(y_out))), 1.0, rtol=0.0, atol=1e-9)


# Case 10-03
def test_coherent_gain_hann_matches_window_average() -> None:
    n_fft = 4096
    g = proc_audio._coherent_gain("hann", n_fft)
    try:
        from scipy.signal import windows as _win

        w = _win.hann(n_fft, sym=False)
        ref = float(np.sum(w) / float(n_fft))
    except Exception:
        w = np.hanning(n_fft)
        ref = float(np.sum(w) / float(n_fft))
    npt.assert_allclose(g, ref, rtol=0.0, atol=1e-10)


# Case 10-04
def test_physical_peak_amplitude_one_sided() -> None:
    mag = np.array([1.0])
    n_fft = 4096
    sw = proc_audio._window_sum("hann", n_fft)
    expected = 2.0 * 1.0 / sw
    out = proc_audio.physical_peak_amplitude(mag, "hann", n_fft, is_one_sided=True)
    npt.assert_allclose(out, np.array([expected]), rtol=0.0, atol=1e-9)


# Case 10-05 — environment-sensitive (librosa STFT)
def test_verify_energy_conservation_ratio_near_one() -> None:
    pytest.importorskip("librosa")
    import librosa

    sr = 8000
    n_fft = 1024
    hop = n_fft // 4
    duration = 0.5
    t = np.linspace(0.0, duration, int(sr * duration), endpoint=False)
    y = 0.3 * np.sin(2.0 * math.pi * 440.0 * t).astype(float)
    y_norm = proc_audio._normalize_level(y, target_rms_db=-20.0)
    S = librosa.stft(
        y_norm,
        n_fft=n_fft,
        hop_length=hop,
        window="hann",
        center=True,
    )
    win_arg = "hann"
    res = proc_audio._verify_energy_conservation(
        y_norm,
        S,
        n_fft,
        hop,
        win_arg,
        tolerance=0.15,
        window_array=None,
    )
    npt.assert_allclose(res["energy_ratio"], 1.0, rtol=0.0, atol=0.15)


# Case 10-06
def test_estimate_f0_global_robust_two_partials() -> None:
    detected_freqs = np.array([200.0, 400.0])
    detected_amplitudes = np.array([1.0, 1.0])
    out = proc_audio._estimate_f0_global_robust(
        detected_freqs,
        detected_amplitudes,
        initial_f0=100.0,
        max_n=10,
    )
    npt.assert_allclose(out["f0_estimated"], 100.0, rtol=0.0, atol=1e-9)
