"""Phase 2 — end-to-end ground-truth accuracy.

These tests synthesise signals with KNOWN harmonic content (frequencies,
relative amplitudes) and KNOWN inharmonicity, run the full per-note pipeline,
and assert the pipeline RECOVERS those quantities within tolerance — i.e. they
test accuracy, not merely plausibility (which the acoustic-validity tests
already cover) and not just the isolated fit math (which the phase_4 unit tests
cover). The point is to prove the whole `proc_audio` path is quantitatively
faithful.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from proc_audio import AudioProcessor


def _write_partials_wav(
    path: Path,
    *,
    partials_hz,
    amplitudes,
    sr_hz: int = 44100,
    seconds: float = 1.5,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(sr_hz * seconds), dtype=float) / float(sr_hz)
    y = np.zeros_like(t)
    for f, a in zip(partials_hz, amplitudes):
        if 0.0 < f < 0.45 * sr_hz:
            y += float(a) * np.sin(2.0 * np.pi * float(f) * t)
    y = 0.30 * y / float(np.max(np.abs(y)))
    pcm = np.asarray(np.clip(y, -1.0, 1.0) * 32767.0, dtype=np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr_hz))
        wf.writeframes(pcm.tobytes())
    return path


def _run(tmp_path: Path, name: str, partials_hz, amplitudes, *, n_fft: int = 8192):
    wav = _write_partials_wav(
        tmp_path / "audio" / f"{name}.wav",
        partials_hz=partials_hz,
        amplitudes=amplitudes,
    )
    out = tmp_path / f"run_{name}"
    ap = AudioProcessor()
    ap.load_audio_files([str(wav)])
    ap.apply_filters_and_generate_data(
        results_directory=out,
        n_fft=n_fft,
        zero_padding=2,
        freq_max=20000.0,
        dissonance_enabled=False,
        dissonance_curve=False,
        dissonance_scale=False,
        compare_models=False,
        compile_per_call=False,
        parallel_processing=False,
    )
    return next(out.rglob("spectral_analysis.xlsx"))


def _cents(f_meas: float, f_ref: float) -> float:
    return 1200.0 * np.log2(float(f_meas) / float(f_ref))


@pytest.mark.slow
def test_harmonic_frequencies_recovered_within_cents(tmp_path: Path) -> None:
    f0 = 220.0  # A3
    n_max = 8
    partials = [n * f0 for n in range(1, n_max + 1)]
    amps = [1.0 / n for n in range(1, n_max + 1)]
    wb = _run(tmp_path, "A3", partials, amps)
    harm = pd.read_excel(wb, sheet_name="Harmonic Spectrum")
    inc = harm.loc[harm["include_for_density"].astype(bool)].copy()
    inc["n"] = pd.to_numeric(inc["Harmonic Number"], errors="coerce")
    inc["fx"] = pd.to_numeric(inc["extracted_frequency_hz"], errors="coerce")
    checked = 0
    for _, r in inc.iterrows():
        n = int(r["n"]) if np.isfinite(r["n"]) else 0
        if 1 <= n <= n_max and np.isfinite(r["fx"]):
            dev = abs(_cents(r["fx"], n * f0))
            assert dev < 25.0, f"H{n}: {dev:.1f} cents off (f={r['fx']:.2f}, expected {n*f0:.2f})"
            checked += 1
    assert checked >= 5, f"too few harmonics validated for frequency accuracy ({checked})"


@pytest.mark.slow
def test_harmonic_amplitude_ratios_recovered(tmp_path: Path) -> None:
    """Synthesised 1/n rolloff → recovered Amplitude_raw ratios track 1/n.

    RMS normalisation and coherent gain are global scalars that cancel in
    intra-note ratios, so H_n/H_1 must approximate a_n/a_1 = 1/n.
    """
    f0 = 220.0  # A3
    n_max = 6
    partials = [n * f0 for n in range(1, n_max + 1)]
    amps = [1.0 / n for n in range(1, n_max + 1)]
    wb = _run(tmp_path, "A3", partials, amps)
    harm = pd.read_excel(wb, sheet_name="Harmonic Spectrum")
    inc = harm.loc[harm["include_for_density"].astype(bool)].copy()
    by_n = {}
    for _, r in inc.iterrows():
        n = pd.to_numeric(r["Harmonic Number"], errors="coerce")
        a = pd.to_numeric(r["Amplitude_raw"], errors="coerce")
        if np.isfinite(n) and np.isfinite(a) and int(n) >= 1:
            by_n[int(n)] = float(a)
    assert 1 in by_n, "fundamental not recovered"
    a1 = by_n[1]
    assert a1 > 0
    # Check the low-order partials that were recovered: ratio within 35%.
    checked = 0
    for n in (2, 3, 4):
        if n in by_n:
            ratio = by_n[n] / a1
            expected = 1.0 / n
            assert abs(ratio - expected) / expected < 0.35, (
                f"H{n}/H1={ratio:.3f}, expected ~{expected:.3f}"
            )
            checked += 1
    assert checked >= 2, "too few harmonic amplitude ratios recovered"
    # Monotonic decay (1/n is strictly decreasing).
    if 2 in by_n and 4 in by_n:
        assert by_n[4] < by_n[2] < a1


@pytest.mark.slow
def test_no_false_inharmonicity_on_pure_harmonic(tmp_path: Path) -> None:
    """A perfectly harmonic signal must NOT be reported as inharmonic (B ≈ 0)."""
    f0 = 110.0  # A2, perfectly harmonic
    n_max = 14
    partials = [n * f0 for n in range(1, n_max + 1)]
    amps = [1.0 / (n ** 0.25) for n in range(1, n_max + 1)]
    wb = _run(tmp_path, "A2", partials, amps, n_fft=16384)
    xls = pd.ExcelFile(wb)
    assert "Inharmonicity_Fit" in xls.sheet_names, "Inharmonicity_Fit sheet missing"
    fit = xls.parse("Inharmonicity_Fit").iloc[0]
    status = str(fit.get("inharmonicity_fit_status", fit.get("fit_status", "")))
    b_est = float(pd.to_numeric(fit.get("inharmonicity_coefficient_B"), errors="coerce"))
    assert status == "ok", f"fit_status={status!r}"
    assert np.isfinite(b_est)
    assert abs(b_est) < 5.0e-5, f"false inharmonicity on pure-harmonic signal: B_est={b_est:.2e}"


@pytest.mark.slow
def test_inharmonicity_B_recovered_end_to_end(tmp_path: Path) -> None:
    """Stiff-string synthetic with known B, recovered through the full pipeline
    via the joint (f0, B) fit. Complements the phase_4 isolated-fit unit test."""
    f0 = 110.0  # A2
    b_true = 3.0e-4
    n_max = 14
    orders = np.arange(1, n_max + 1, dtype=float)
    partials = (orders * f0 * np.sqrt(1.0 + b_true * orders**2)).tolist()
    amps = [1.0 / (n ** 0.25) for n in range(1, n_max + 1)]
    wb = _run(tmp_path, "A2", partials, amps, n_fft=16384)
    xls = pd.ExcelFile(wb)
    assert "Inharmonicity_Fit" in xls.sheet_names, "Inharmonicity_Fit sheet missing"
    fit = xls.parse("Inharmonicity_Fit").iloc[0]
    status = str(fit.get("inharmonicity_fit_status", fit.get("fit_status", "")))
    b_est = float(pd.to_numeric(fit.get("inharmonicity_coefficient_B"), errors="coerce"))
    assert status == "ok", f"fit_status={status!r}"
    assert np.isfinite(b_est)
    # Joint fit recovers the magnitude end-to-end: within [0.4x, 2.5x] of true B.
    assert 0.4 * b_true <= b_est <= 2.5 * b_true, (
        f"B_est={b_est:.2e} not within [0.4x, 2.5x] of B_true={b_true:.2e}"
    )
