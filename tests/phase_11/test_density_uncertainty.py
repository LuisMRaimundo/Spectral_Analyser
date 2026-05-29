"""Phase 3 — uncertainty quantification for note_density_final."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from density_uncertainty import (
    bootstrap_density_ci,
    bootstrap_note_density_final,
    nfft_sensitivity,
)


def test_ratio_propagation_widens_or_matches_uncertainty() -> None:
    """Propagating ratio uncertainty adds a variance source, so the relative
    uncertainty must be >= the partials-only estimate on the same data."""
    rng = np.random.default_rng(11)
    amp_h = np.asarray(rng.uniform(0.5, 1.5, 30))
    amp_i = np.asarray(rng.uniform(0.1, 0.4, 12))
    amp_s = np.asarray(rng.uniform(0.05, 0.2, 6))
    # Ratios derived from the SAME band energies (as in the real pipeline), so
    # the fixed-ratio point estimate and the ratio-propagation bootstrap are
    # consistent and the CI brackets the point.
    e_h, e_i, e_s = float(np.sum(amp_h**2)), float(np.sum(amp_i**2)), float(np.sum(amp_s**2))
    tot = e_h + e_i + e_s
    bands = {
        "H": (list(amp_h), e_h / tot),
        "I": (list(amp_i), e_i / tot),
        "S": (list(amp_s), e_s / tot),
    }
    fixed = bootstrap_note_density_final(
        bands, weight_function="log", n_boot=3000, seed=7,
        propagate_ratio_uncertainty=False,
    )
    full = bootstrap_note_density_final(
        bands, weight_function="log", n_boot=3000, seed=7,
        propagate_ratio_uncertainty=True,
    )
    assert fixed["uncertainty_sources"] == "partials"
    assert full["uncertainty_sources"] == "partials+ratios"
    # Both bracket the same point estimate.
    assert fixed["point_estimate"] == pytest.approx(full["point_estimate"], rel=1e-12)
    assert full["ci_low"] <= full["point_estimate"] <= full["ci_high"]
    # Propagating ratios cannot reduce uncertainty below the partials-only floor
    # (allow tiny numerical slack).
    assert full["relative_uncertainty"] >= fixed["relative_uncertainty"] - 1e-9


def test_bootstrap_ci_brackets_point_estimate() -> None:
    rng = np.random.default_rng(0)
    h = list(rng.uniform(1.0, 2.0, 40))
    res = bootstrap_density_ci(
        {"H": (h, 0.9), "I": ([0.1, 0.2, 0.15], 0.07), "S": ([0.05], 0.03)},
        n_boot=3000,
        seed=1,
    )
    assert res["ci_low"] <= res["point_estimate"] <= res["ci_high"]
    assert res["ci_high"] > res["ci_low"]
    assert res["relative_uncertainty"] >= 0.0
    # bootstrap mean should be close to the point estimate
    assert abs(res["bootstrap_mean"] - res["point_estimate"]) / res["point_estimate"] < 0.1


def test_bootstrap_wider_spread_gives_wider_relative_uncertainty() -> None:
    rng = np.random.default_rng(2)
    tight = list(rng.normal(10.0, 0.1, 50))
    wide = list(rng.normal(10.0, 5.0, 50))
    r_tight = bootstrap_density_ci({"H": (tight, 1.0)}, n_boot=3000, seed=3)
    r_wide = bootstrap_density_ci({"H": (wide, 1.0)}, n_boot=3000, seed=3)
    assert r_wide["relative_uncertainty"] > r_tight["relative_uncertainty"]


def test_bootstrap_relative_uncertainty_shrinks_with_more_partials() -> None:
    # Consistency: for the same underlying distribution, more detected partials
    # give a smaller relative uncertainty (~1/sqrt(n) behaviour of the mean).
    rng = np.random.default_rng(4)
    small = list(rng.normal(10.0, 3.0, 20))
    large = list(rng.normal(10.0, 3.0, 200))
    r_small = bootstrap_density_ci({"H": (small, 1.0)}, n_boot=3000, seed=5)
    r_large = bootstrap_density_ci({"H": (large, 1.0)}, n_boot=3000, seed=5)
    assert r_large["relative_uncertainty"] < r_small["relative_uncertainty"]


def test_nfft_sensitivity_basic() -> None:
    s = nfft_sensitivity({4096: 100.0, 8192: 104.0, 16384: 102.0})
    assert s["n"] == 3
    assert s["min"] == 100.0 and s["max"] == 104.0
    assert s["mean"] == pytest.approx(102.0, abs=1e-9)
    assert 0.0 < s["coefficient_of_variation"] < 0.05
    assert s["relative_range"] == pytest.approx(4.0 / 102.0, rel=1e-6)


def test_nfft_sensitivity_degenerate_inputs() -> None:
    assert nfft_sensitivity({})["n"] == 0
    one = nfft_sensitivity({8192: 50.0})
    assert one["n"] == 1 and one["std"] == 0.0
    assert np.isnan(one["coefficient_of_variation"])


# ---------------------------------------------------------------------------
# End-to-end: demonstrate UQ on the REAL note_density_final across n_fft.
# ---------------------------------------------------------------------------

def _write_harmonic_wav(path: Path, *, f0_hz: float, n: int, sr: int = 44100, sec: float = 1.5) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(sr * sec), dtype=float) / sr
    y = np.zeros_like(t)
    for k in range(1, n + 1):
        fk = k * f0_hz
        if fk < 0.45 * sr:
            y += (1.0 / (k ** 0.25)) * np.sin(2.0 * np.pi * fk * t)
    y = 0.3 * y / float(np.max(np.abs(y)))
    pcm = np.asarray(np.clip(y, -1.0, 1.0) * 32767.0, dtype=np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


def _note_density_final_for_nfft(tmp_path: Path, n_fft: int) -> float:
    from proc_audio import AudioProcessor
    import compile_metrics as cm

    wav = _write_harmonic_wav(tmp_path / "audio" / f"A3_{n_fft}.wav", f0_hz=220.0, n=8)
    run = tmp_path / f"run_{n_fft}"
    ap = AudioProcessor()
    ap.load_audio_files([str(wav)])
    ap.apply_filters_and_generate_data(
        results_directory=run / "stage1",
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
    out_xlsx = run / "compiled_density_metrics.xlsx"
    cm.compile_density_metrics_with_pca(
        folder_path=run / "stage1",
        output_path=out_xlsx,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
        weight_function="log",
    )
    wb = next(run.rglob("compiled_density_metrics*.xlsx"))
    dm = pd.read_excel(wb, sheet_name="Density_Metrics")
    return float(pd.to_numeric(dm.iloc[0]["note_density_final"], errors="coerce"))


@pytest.mark.slow
def test_compiled_output_emits_note_density_final_ci_columns(tmp_path: Path) -> None:
    """The compiled Density_Metrics sheet must carry per-note bootstrap CI
    columns for note_density_final, and the CI must bracket the point estimate."""
    from proc_audio import AudioProcessor
    import compile_metrics as cm

    wav = _write_harmonic_wav(tmp_path / "audio" / "A3.wav", f0_hz=220.0, n=8)
    run = tmp_path / "run"
    ap = AudioProcessor()
    ap.load_audio_files([str(wav)])
    ap.apply_filters_and_generate_data(
        results_directory=run / "stage1",
        n_fft=8192,
        zero_padding=2,
        freq_max=20000.0,
        dissonance_enabled=False,
        dissonance_curve=False,
        dissonance_scale=False,
        compare_models=False,
        compile_per_call=False,
        parallel_processing=False,
    )
    out_xlsx = run / "compiled_density_metrics.xlsx"
    cm.compile_density_metrics_with_pca(
        folder_path=run / "stage1",
        output_path=out_xlsx,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
        weight_function="log",
    )
    wb = next(run.rglob("compiled_density_metrics*.xlsx"))
    dm = pd.read_excel(wb, sheet_name="Density_Metrics")
    for col in (
        "note_density_final",
        "note_density_final_ci_low",
        "note_density_final_ci_high",
        "note_density_final_rel_uncertainty",
        "note_density_final_uncertainty_sources",
    ):
        assert col in dm.columns, f"missing CI column: {col}"
    # The compiled pipeline must report the FULL uncertainty (partials+ratios).
    assert (
        str(dm.iloc[0]["note_density_final_uncertainty_sources"]).strip()
        == "partials+ratios"
    )
    r = dm.iloc[0]
    point = float(pd.to_numeric(r["note_density_final"], errors="coerce"))
    lo = float(pd.to_numeric(r["note_density_final_ci_low"], errors="coerce"))
    hi = float(pd.to_numeric(r["note_density_final_ci_high"], errors="coerce"))
    rel = float(pd.to_numeric(r["note_density_final_rel_uncertainty"], errors="coerce"))
    assert np.isfinite(point) and point > 0.0
    assert np.isfinite(lo) and np.isfinite(hi) and lo <= hi
    # CI should bracket the point estimate (within a small numerical tolerance).
    assert lo - 0.05 * abs(point) <= point <= hi + 0.05 * abs(point)
    assert np.isfinite(rel) and rel >= 0.0


@pytest.mark.slow
def test_note_density_final_nfft_sensitivity_is_bounded(tmp_path: Path) -> None:
    """note_density_final on a fixed signal must be reasonably stable across
    n_fft. We quantify (not just assert) the sensitivity and require it to stay
    within a sane band for an otherwise identical analysis profile."""
    vals = {}
    for n_fft in (8192, 16384):
        v = _note_density_final_for_nfft(tmp_path, n_fft)
        assert np.isfinite(v) and v > 0.0, f"note_density_final invalid at n_fft={n_fft}: {v}"
        vals[n_fft] = v
    sens = nfft_sensitivity(vals)
    assert sens["n"] == 2
    # The metric should not swing wildly with n_fft on the same signal/profile.
    assert sens["relative_range"] < 0.5, (
        f"note_density_final too n_fft-sensitive: {vals} (rel_range={sens['relative_range']:.3f})"
    )
