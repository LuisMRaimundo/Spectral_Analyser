"""Formula validation Pass 14 — compile extraction and batch mass (validation plan only)."""

from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path

import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest

import compile_metrics


def _load_finalize_batch_power_mass_summary():
    root = Path(__file__).resolve().parents[2]
    path = root / "audio_analysis" / "super_audio_analyzer.py"
    spec = importlib.util.spec_from_file_location("super_audio_analyzer_pass14", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.finalize_batch_power_mass_summary


def _write_minimal_density_xlsx(
    path: Path,
    *,
    harmonic_amps: list[float],
    inharmonic_amps: list[float],
    subbass_amps: list[float],
    power_raw: bool = False,
) -> None:
    harm = pd.DataFrame({"Amplitude_raw": harmonic_amps})
    if power_raw:
        harm["Power_raw"] = [1.0, 4.0][: len(harmonic_amps)]
        if len(harmonic_amps) != 2:
            raise ValueError("power_raw fixture expects two harmonic rows")
    inh = pd.DataFrame({"Amplitude_raw": inharmonic_amps})
    sub = pd.DataFrame({"Amplitude_raw": subbass_amps})
    meta = pd.DataFrame(
        {
            "Parameter": [
                "analysis_schema_version",
                "component_harmonic_energy_ratio",
                "component_inharmonic_energy_ratio",
                "component_subbass_energy_ratio",
            ],
            "Value": [
                compile_metrics.EXPECTED_ANALYSIS_SCHEMA_VERSION,
                0.5,
                0.25,
                0.25,
            ],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        harm.to_excel(w, sheet_name="Harmonic Spectrum", index=False)
        inh.to_excel(w, sheet_name="Inharmonic Spectrum", index=False)
        sub.to_excel(w, sheet_name="Sub-bass band", index=False)
        meta.to_excel(w, sheet_name="Analysis_Metadata", index=False)


# Case SN-1
def test_sum_finite_numeric() -> None:
    s = pd.Series([1.0, np.nan, 3.0, float("inf")])
    total, n = compile_metrics._sum_finite_numeric(s)
    npt.assert_allclose(total, 4.0, rtol=0.0, atol=0.0)
    assert int(n) == 2


# Case ED-LIN-1
def test_extract_density_component_sum_linear(tmp_path: Path) -> None:
    p = tmp_path / "ed_lin.xlsx"
    _write_minimal_density_xlsx(p, harmonic_amps=[1.0, 2.0, 3.0], inharmonic_amps=[0.0], subbass_amps=[0.0])
    out = compile_metrics.extract_density_component_sum(p, "Harmonic Spectrum", "linear")
    assert out.get("status") == "ok"
    npt.assert_allclose(float(out["D"]), 6.0, rtol=0.0, atol=1e-12)


# Case ED-LOG-1
def test_extract_density_component_sum_log(tmp_path: Path) -> None:
    p = tmp_path / "ed_log.xlsx"
    _write_minimal_density_xlsx(p, harmonic_amps=[1.0, 2.0, 3.0], inharmonic_amps=[0.0], subbass_amps=[0.0])
    out = compile_metrics.extract_density_component_sum(p, "Harmonic Spectrum", "log")
    assert out.get("status") == "ok"
    npt.assert_allclose(float(out["D"]), np.log10(7.0), rtol=1e-12, atol=0.0)


# Case ED-POW-1
def test_extract_density_component_sum_power_raw(tmp_path: Path) -> None:
    p = tmp_path / "ed_pow.xlsx"
    harm = pd.DataFrame({"Amplitude_raw": [9.0, 9.0], "Power_raw": [1.0, 4.0]})
    inh = pd.DataFrame({"Amplitude_raw": [0.0]})
    sub = pd.DataFrame({"Amplitude_raw": [0.0]})
    meta = pd.DataFrame(
        {
            "Parameter": ["analysis_schema_version"],
            "Value": [compile_metrics.EXPECTED_ANALYSIS_SCHEMA_VERSION],
        }
    )
    with pd.ExcelWriter(p, engine="openpyxl") as w:
        harm.to_excel(w, sheet_name="Harmonic Spectrum", index=False)
        inh.to_excel(w, sheet_name="Inharmonic Spectrum", index=False)
        sub.to_excel(w, sheet_name="Sub-bass band", index=False)
        meta.to_excel(w, sheet_name="Analysis_Metadata", index=False)
    out = compile_metrics.extract_density_component_sum(p, "Harmonic Spectrum", "power")
    assert out.get("status") == "ok"
    npt.assert_allclose(float(out["D"]), 5.0, rtol=0.0, atol=1e-12)


# Case ED-POW-2
def test_extract_density_component_sum_power_amp_squared_fallback(tmp_path: Path) -> None:
    p = tmp_path / "ed_pow2.xlsx"
    harm = pd.DataFrame({"Amplitude_raw": [2.0, 3.0]})
    inh = pd.DataFrame({"Amplitude_raw": [0.0]})
    sub = pd.DataFrame({"Amplitude_raw": [0.0]})
    meta = pd.DataFrame(
        {
            "Parameter": ["analysis_schema_version"],
            "Value": [compile_metrics.EXPECTED_ANALYSIS_SCHEMA_VERSION],
        }
    )
    with pd.ExcelWriter(p, engine="openpyxl") as w:
        harm.to_excel(w, sheet_name="Harmonic Spectrum", index=False)
        inh.to_excel(w, sheet_name="Inharmonic Spectrum", index=False)
        sub.to_excel(w, sheet_name="Sub-bass band", index=False)
        meta.to_excel(w, sheet_name="Analysis_Metadata", index=False)
    out = compile_metrics.extract_density_component_sum(p, "Harmonic Spectrum", "power")
    assert out.get("status") == "ok"
    npt.assert_allclose(float(out["D"]), 13.0, rtol=0.0, atol=1e-12)


# Case DC-MINI-1
def test_extract_density_components_mini_workbook(tmp_path: Path) -> None:
    p = tmp_path / "dc_mini.xlsx"
    _write_minimal_density_xlsx(p, harmonic_amps=[2.0], inharmonic_amps=[2.0], subbass_amps=[2.0])
    out = compile_metrics.extract_density_components_from_per_note_workbook(
        p, weight_function="linear"
    )
    assert out.get("density_extraction_status") == "ok"
    npt.assert_allclose(float(out["D_H"]), 2.0, rtol=0.0, atol=1e-12)
    npt.assert_allclose(float(out["D_I"]), 2.0, rtol=0.0, atol=1e-12)
    npt.assert_allclose(float(out["D_S"]), 2.0, rtol=0.0, atol=1e-12)
    npt.assert_allclose(float(out["harmonic_amplitude_sum"]), 2.0, rtol=0.0, atol=1e-12)
    npt.assert_allclose(float(out["harmonic_log_amplitude_density"]), np.log10(3.0), rtol=1e-12, atol=0.0)
    npt.assert_allclose(float(out["density_weighted_sum"]), 2.0, rtol=0.0, atol=1e-12)
    npt.assert_allclose(float(out["density_log_weighted"]), np.log10(3.0), rtol=1e-12, atol=0.0)
    assert bool(out.get("component_energy_ratio_sum_ok")) is True
    npt.assert_allclose(float(out["component_energy_ratio_sum"]), 1.0, rtol=0.0, atol=1e-12)


# Case FDN-1
def test_apply_frequency_dependent_normalization_alpha_gt_one() -> None:
    density = pd.Series([1.5], index=[0])
    freq = pd.Series([100.0], index=[0])
    nhar = pd.Series([4], index=[0])
    out = compile_metrics.apply_frequency_dependent_normalization(
        density, freq, nhar, alpha=2.0, use_frequency_dependent_alpha=False
    )
    npt.assert_allclose(float(out.iloc[0]), 2.0, rtol=1e-9, atol=0.0)


# Case FDN-2
def test_apply_frequency_dependent_normalization_guards() -> None:
    density = pd.Series([0.0, -1.0], index=[0, 1])
    freq = pd.Series([100.0, 100.0], index=[0, 1])
    nhar = pd.Series([4, 4], index=[0, 1])
    out = compile_metrics.apply_frequency_dependent_normalization(
        density, freq, nhar, alpha=2.0, use_frequency_dependent_alpha=False
    )
    npt.assert_allclose(out.to_numpy(dtype=float), density.to_numpy(dtype=float), rtol=0.0, atol=0.0)

    density2 = pd.Series([5.0], index=[0])
    freq2 = pd.Series([100.0], index=[0])
    nhar2 = pd.Series([0], index=[0])
    out2 = compile_metrics.apply_frequency_dependent_normalization(
        density2, freq2, nhar2, alpha=2.0, use_frequency_dependent_alpha=False
    )
    npt.assert_allclose(float(out2.iloc[0]), 5.0, rtol=0.0, atol=0.0)


# Case FDA-1
def test_get_frequency_dependent_alpha_piecewise() -> None:
    assert compile_metrics.get_frequency_dependent_alpha(50.0) == 1.2
    assert compile_metrics.get_frequency_dependent_alpha(150.0) == 1.3
    assert compile_metrics.get_frequency_dependent_alpha(300.0) == 1.4
    assert compile_metrics.get_frequency_dependent_alpha(500.0) == 1.6


# Case MM-1
def test_minmax_spread() -> None:
    s = pd.Series([1.0, 5.0, 9.0])
    z = compile_metrics._minmax(s)
    npt.assert_allclose(z.to_numpy(dtype=float), [0.0, 0.5, 1.0], rtol=0.0, atol=1e-15)


# Case MM-2
def test_minmax_degenerate_all_equal() -> None:
    s = pd.Series([7.0, 7.0, 7.0])
    z = compile_metrics._minmax(s)
    assert z.shape == s.shape
    npt.assert_allclose(z.to_numpy(dtype=float), np.zeros(3), rtol=0.0, atol=0.0)


# Case RD-FB-1
def test_robust_normalize_series_import_error_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "data_integrity":
            raise ImportError("forced for pass14 test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    s = pd.Series([0.0, 5.0, 10.0])
    out = compile_metrics._robust_normalize_series(s, method="percentile")
    ref = compile_metrics._minmax(s)
    npt.assert_allclose(out.to_numpy(dtype=float), ref.to_numpy(dtype=float), rtol=0.0, atol=1e-12)


# Case NM-1
def test_note_to_midi_a4() -> None:
    assert compile_metrics.note_to_midi("A4") == 69


# Case NM-2
def test_note_to_midi_invalid_sentinel() -> None:
    assert compile_metrics.note_to_midi("X99") == 10**9


# Case NF-1
def test_note_to_fundamental_freq_a4() -> None:
    f = compile_metrics.note_to_fundamental_freq("A4")
    assert f is not None
    npt.assert_allclose(float(f), 440.0, rtol=0.0, atol=1e-12)


# Case AI-OLS-1
def test_apply_weighted_index_log_log_slope_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    def _identity_robust(s: pd.Series, method: str = "percentile", **_kwargs) -> pd.Series:
        return pd.to_numeric(s, errors="coerce").astype(float)

    monkeypatch.setattr(compile_metrics, "_robust_normalize_series", _identity_robust)

    notes = ["C3", "C4", "C5"]
    freqs = np.array(
        [float(compile_metrics.note_to_fundamental_freq(n)) for n in notes],
        dtype=float,
    )
    dens = np.exp(-0.9 * np.log(freqs))
    df = pd.DataFrame(
        {
            "Note": notes,
            "Harmonic Count": [4, 5, 6],
            "Density Metric": dens,
            "D_agn": [0.5, 0.5, 0.5],
            "P_norm": [0.5, 0.5, 0.5],
            "Weighted Combined Metric_Norm": [0.5, 0.5, 0.5],
        }
    )
    out = compile_metrics.apply_weighted_index(df.copy(), scheme="pdf")
    assert str(out["frequency_dependent_normalization_status"].iloc[0]) == "applied"

    log_density = np.log(pd.to_numeric(df["Density Metric"], errors="coerce").astype(float))
    log_freq = np.log(freqs)
    beta_hat = float(np.cov(log_density, log_freq, bias=True)[0, 1] / np.var(log_freq))
    beta_used = max(-1.5, min(-0.3, beta_hat))
    npt.assert_allclose(beta_hat, -0.9, rtol=1e-6, atol=1e-6)
    npt.assert_allclose(beta_used, -0.9, rtol=0.0, atol=1e-9)


# Case AI-CLP-1
def test_apply_weighted_index_clip_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    def _identity_robust(s: pd.Series, method: str = "percentile", **_kwargs) -> pd.Series:
        return pd.to_numeric(s, errors="coerce").astype(float)

    monkeypatch.setattr(compile_metrics, "_robust_normalize_series", _identity_robust)
    df = pd.DataFrame(
        {
            "Density Metric": [1.0, 1.0],
            "Harmonic Count": [5, 5],
            "D_agn": [0.5, 0.5],
            "P_norm": [0.5, 0.5],
            "Weighted Combined Metric_Norm": [0.5, 0.5],
        }
    )
    out = compile_metrics.apply_weighted_index(df, scheme="pdf")
    idx = pd.to_numeric(out["Index_Weighted"], errors="coerce").dropna()
    assert bool((idx >= -1e-15).all()) is True
    assert bool((idx <= 1.0 + 1e-15).all()) is True


# Case AI-AV-1
def test_apply_weighted_index_pdf_available_terms_renorm(monkeypatch: pytest.MonkeyPatch) -> None:
    def _identity_robust(s: pd.Series, method: str = "percentile", **_kwargs) -> pd.Series:
        return pd.to_numeric(s, errors="coerce").astype(float)

    monkeypatch.setattr(compile_metrics, "_robust_normalize_series", _identity_robust)
    df = pd.DataFrame(
        {
            "Density Metric": [1.0],
            "D_agn": [0.4],
            "P_norm": [0.6],
        }
    )
    out = compile_metrics.apply_weighted_index(df, scheme="pdf")
    npt.assert_allclose(float(out["Index_Weighted"].iloc[0]), 0.29 / 0.55, rtol=1e-9, atol=0.0)


# Case AI-PDF-1
def test_apply_weighted_index_pdf_weights_sum_to_one(monkeypatch: pytest.MonkeyPatch) -> None:
    def _identity_robust(s: pd.Series, method: str = "percentile", **_kwargs) -> pd.Series:
        return pd.to_numeric(s, errors="coerce").astype(float)

    monkeypatch.setattr(compile_metrics, "_robust_normalize_series", _identity_robust)
    df = pd.DataFrame(
        {
            "Density Metric": [1.0, 1.0],
            "Harmonic Count": [5, 5],
            "D_agn": [1.0, 1.0],
            "P_norm": [1.0, 1.0],
            "Weighted Combined Metric_Norm": [1.0, 1.0],
        }
    )
    out = compile_metrics.apply_weighted_index(df, scheme="pdf")
    npt.assert_allclose(float(out["Index_Weighted"].iloc[0]), 1.0, rtol=1e-9, atol=0.0)
    npt.assert_allclose(float(out["Index_Weighted"].max()), 1.0, rtol=0.0, atol=1e-9)


# Case AI-CUR-1
def test_apply_weighted_index_current_scheme_halves(monkeypatch: pytest.MonkeyPatch) -> None:
    def _half_robust(s: pd.Series, method: str = "percentile", **_kwargs) -> pd.Series:
        return pd.Series(0.5, index=s.index, dtype=float)

    monkeypatch.setattr(compile_metrics, "_robust_normalize_series", _half_robust)
    df = pd.DataFrame(
        {
            "Harmonic Count": [5],
            "Density Metric": [1.0],
            "D_agn": [0.5],
            "P_norm": [0.5],
        }
    )
    out = compile_metrics.apply_weighted_index(df, scheme="current")
    npt.assert_allclose(float(out["Index_Weighted"].iloc[0]), 0.5, rtol=1e-9, atol=0.0)


# Case DIS-1
def test_extract_dissonance_metrics_first_finite_row() -> None:
    dfs = {"S1": pd.DataFrame({"X Dissonance Y": [np.nan, 2.5, 3.0]})}
    out = compile_metrics.extract_dissonance_metrics(dfs)
    assert out["X Dissonance Y"] == 2.5


# Case BPM-1
def test_finalize_batch_power_mass_summary_positive() -> None:
    finalize = _load_finalize_batch_power_mass_summary()
    out = finalize(3.0, 1.0, 1.0)
    npt.assert_allclose(float(out["harmonic_power_percent"]), 60.0, rtol=0.0, atol=1e-9)
    npt.assert_allclose(float(out["total_inharmonic_power_percent"]), 40.0, rtol=0.0, atol=1e-9)
    trio = (
        float(out["harmonic_power_percent"])
        + float(out["inharmonic_residual_power_percent"])
        + float(out["subbass_noise_power_percent"])
    )
    npt.assert_allclose(trio, 100.0, rtol=0.0, atol=1e-9)


# Case BPM-2
def test_finalize_batch_power_mass_summary_renorm_sum_100() -> None:
    finalize = _load_finalize_batch_power_mass_summary()
    out = finalize(1.0, 1.0, 1.0)
    trio = (
        float(out["harmonic_power_percent"])
        + float(out["inharmonic_residual_power_percent"])
        + float(out["subbass_noise_power_percent"])
    )
    npt.assert_allclose(trio, 100.0, rtol=0.0, atol=1e-9)


# Case BPM-3
def test_finalize_batch_power_mass_summary_zero_total() -> None:
    finalize = _load_finalize_batch_power_mass_summary()
    out = finalize(0.0, 0.0, 0.0)
    assert float(out["harmonic_power_percent"]) == 0.0
    assert float(out["inharmonic_residual_power_percent"]) == 0.0
    assert float(out["subbass_noise_power_percent"]) == 0.0
    assert float(out["total_inharmonic_power_percent"]) == 0.0


# Case BPM-4
def test_finalize_batch_power_mass_summary_negative_clamped() -> None:
    finalize = _load_finalize_batch_power_mass_summary()
    out = finalize(-5.0, 1.0, 1.0)
    npt.assert_allclose(float(out["harmonic_power_percent"]), 0.0, rtol=0.0, atol=0.0)
    trio = (
        float(out["harmonic_power_percent"])
        + float(out["inharmonic_residual_power_percent"])
        + float(out["subbass_noise_power_percent"])
    )
    npt.assert_allclose(trio, 100.0, rtol=0.0, atol=1e-9)
