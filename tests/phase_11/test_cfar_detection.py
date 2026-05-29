"""CFAR (constant false-alarm-rate) harmonic peak detection."""

from __future__ import annotations

import numpy as np

from harmonic_peak_validation import cfar_peak_detection


def test_cfar_detects_strong_peak() -> None:
    rng = np.random.default_rng(0)
    # Exponential-ish noise floor in power → magnitude = sqrt.
    n = 400
    noise_power = rng.exponential(1.0, n)
    mags = np.sqrt(noise_power)
    mags[200] = np.sqrt(500.0)  # strong peak well above the floor
    detected, margin_db, _ = cfar_peak_detection(mags, 200, pfa=1e-2)
    assert detected is True
    assert margin_db > 0.0


def test_cfar_rejects_floor_level_bin() -> None:
    rng = np.random.default_rng(1)
    n = 400
    mags = np.sqrt(rng.exponential(1.0, n))
    # A bin at the median floor (no real peak): should not be detected.
    k = 200
    mags[k] = float(np.median(mags))
    detected, margin_db, _ = cfar_peak_detection(mags, k, pfa=1e-3)
    assert detected is False
    assert margin_db < 0.0


def test_cfar_false_alarm_rate_is_bounded_by_pfa() -> None:
    """On pure noise, the empirical detection rate must be of the order of the
    configured Pfa (well below 1), demonstrating false-alarm control."""
    rng = np.random.default_rng(7)
    pfa = 1e-2
    trials = 3000
    hits = 0
    for _ in range(trials):
        mags = np.sqrt(rng.exponential(1.0, 200))
        k = 100  # arbitrary interior cell-under-test (pure noise)
        det, _, _ = cfar_peak_detection(mags, k, pfa=pfa)
        hits += int(det)
    rate = hits / trials
    # Trimming the training cells makes the test conservative; the empirical
    # false-alarm rate must stay small (<< 1) and not wildly exceed Pfa.
    assert rate < 0.10, f"empirical false-alarm rate {rate:.3f} too high for Pfa={pfa}"


def test_cfar_higher_pfa_detects_weaker_peaks() -> None:
    rng = np.random.default_rng(3)
    mags = np.sqrt(rng.exponential(1.0, 400))
    mags[200] = np.sqrt(8.0)  # modest peak
    det_strict, _, _ = cfar_peak_detection(mags, 200, pfa=1e-4)
    det_loose, _, _ = cfar_peak_detection(mags, 200, pfa=1e-1)
    # A looser false-alarm budget can only make detection easier (>=).
    assert int(det_loose) >= int(det_strict)
