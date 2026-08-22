"""F-056 balanced component density (Hill q=1)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from compile_metrics import _energy_distribution_density
from metric_contract import get_metric_definition
from tools.balanced_density import (
    BALANCED_DENSITY_COLUMN,
    BALANCED_DENSITY_FORMULA_ID,
    BALANCED_DENSITY_POOL_COUNT_COLUMN,
    BALANCED_DENSITY_POOL_DEFINITION,
    BALANCED_DENSITY_PROVENANCE,
    DIAGNOSTIC_LOW_FREQUENCY_RESIDUAL_NOT_PARTIAL,
    EWSD_ACOUSTIC_BALANCED_COLUMN,
    balanced_component_density,
    balanced_density_from_component_tables,
    balanced_density_is_primary_valid,
    place_balanced_density_left_of_ewsd,
)


def _participation_ratio(amplitudes: np.ndarray) -> float:
    amps = np.asarray(amplitudes, dtype=np.float64)
    amps = amps[np.isfinite(amps)]
    power = np.square(amps)
    power = power[power > 0.0]
    total = float(np.sum(power))
    ss = float(np.sum(power * power))
    if total <= 0.0 or ss <= 0.0:
        return float("nan")
    return float((total * total) / ss)


def test_a_equal_amplitudes_d1_equals_n() -> None:
    for n in (1, 2, 8, 50):
        amps = np.ones(n, dtype=np.float64)
        assert balanced_component_density(amps) == pytest.approx(float(n), abs=1e-9)


def test_b_scale_invariance() -> None:
    rng = np.random.default_rng(0)
    base = rng.uniform(0.1, 4.0, size=12).astype(np.float64)
    ref = balanced_component_density(base)
    for g in (1e-3, 1.0, 1e3):
        assert balanced_component_density(g * base) == pytest.approx(ref, abs=1e-9)


def test_c_specified_energy_shares() -> None:
    shares = np.asarray([0.5, 0.25, 0.125, 0.125], dtype=np.float64)
    amps = np.sqrt(shares)
    expected = float(np.exp(-np.sum(shares * np.log(shares))))
    assert expected == pytest.approx(3.363586, abs=1e-4)
    assert balanced_component_density(amps) == pytest.approx(expected, abs=1e-9)
    assert balanced_component_density(amps) == pytest.approx(np.exp(1.213007565), abs=1e-6)


def test_d_ordering_and_bounds() -> None:
    n = 8
    flat = np.ones(n, dtype=np.float64)
    sloped = np.asarray([2.0 ** (-k) for k in range(n)], dtype=np.float64)
    peaked = np.asarray([10.0] + [0.05] * (n - 1), dtype=np.float64)
    d_flat = balanced_component_density(flat)
    d_slope = balanced_component_density(sloped)
    d_peak = balanced_component_density(peaked)
    assert d_flat > d_slope > d_peak
    for d1 in (d_flat, d_slope, d_peak):
        assert 1.0 <= d1 <= float(n)


def test_e_hill_consistency_d1_ge_participation_ratio() -> None:
    rng = np.random.default_rng(1)
    for _ in range(20):
        amps = rng.uniform(0.05, 3.0, size=15).astype(np.float64)
        d1 = balanced_component_density(amps)
        d2 = _participation_ratio(amps)
        assert d1 >= d2 - 1e-12


def test_f_zero_amplitude_component_leaves_d1_unchanged() -> None:
    amps = np.asarray([1.2, 0.4, 0.8], dtype=np.float64)
    ref = balanced_component_density(amps)
    with_zero = np.concatenate([amps, np.asarray([0.0], dtype=np.float64)])
    assert balanced_component_density(with_zero) == pytest.approx(ref, abs=1e-9)


def test_g_empty_pool_is_nan_and_not_primary_valid() -> None:
    d1 = balanced_component_density([])
    assert np.isnan(d1)
    assert balanced_density_is_primary_valid(d1) is False
    assert balanced_density_is_primary_valid(0.0) is False
    zeros = balanced_component_density(np.zeros(4, dtype=np.float64))
    assert np.isnan(zeros)
    assert balanced_density_is_primary_valid(zeros) is False


def test_h_diagnostic_residual_row_excluded_from_pool() -> None:
    harmonic = pd.DataFrame(
        {
            "Amplitude_raw": [1.0, 0.5],
            "include_for_density": [True, True],
        }
    )
    residual = pd.DataFrame(
        {
            "Amplitude_raw": [4.0],
            "include_for_density": [True],
            "Acoustic_Interpretation_Status": [
                DIAGNOSTIC_LOW_FREQUENCY_RESIDUAL_NOT_PARTIAL
            ],
        }
    )
    with_residual = pd.concat([harmonic, residual], ignore_index=True)
    d1_clean, n_clean = balanced_density_from_component_tables(harmonic_df=harmonic)
    d1_dirty, n_dirty = balanced_density_from_component_tables(
        harmonic_df=with_residual
    )
    assert n_clean == 2
    assert n_dirty == 2
    assert d1_dirty == pytest.approx(d1_clean, abs=1e-12)


def test_compile_energy_distribution_writes_d1_without_changing_f047(
    tmp_path: Path,
) -> None:
    path = tmp_path / "note" / "spectral_analysis.xlsx"
    path.parent.mkdir(parents=True, exist_ok=True)
    harmonic = pd.DataFrame(
        {
            "Harmonic Number": [1, 2, 3],
            "Frequency (Hz)": [110.0, 220.0, 330.0],
            "Amplitude_raw": [2.0, 1.0, 0.5],
            "include_for_density": [True, True, True],
        }
    )
    inharmonic = pd.DataFrame(
        {
            "Frequency (Hz)": [250.0],
            "Amplitude_raw": [0.8],
            "inharmonic_status": ["candidate_not_confirmed_partial"],
            "Acoustic_Interpretation_Status": ["candidate_not_confirmed_partial"],
        }
    )
    residual = pd.DataFrame(
        {
            "Frequency (Hz)": [40.0],
            "Amplitude_raw": [3.0],
            "subbass_membership": ["subbass_member"],
            "Acoustic_Interpretation_Status": [
                DIAGNOSTIC_LOW_FREQUENCY_RESIDUAL_NOT_PARTIAL
            ],
        }
    )
    meta = pd.DataFrame({"sustain_frame_count_independent": [20]})
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        harmonic.to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
        inharmonic.to_excel(writer, sheet_name="Inharmonic Spectrum", index=False)
        residual.to_excel(writer, sheet_name="Sub-bass band", index=False)
        meta.to_excel(writer, sheet_name="Per_Note_Processing_Metadata", index=False)

    out = _energy_distribution_density(path)
    # F-047 still pools unconfirmed I + member S (existing algebra).
    f047_amps = np.asarray([2.0, 1.0, 0.5, 0.8, 3.0], dtype=np.float64)
    p = np.square(f047_amps)
    expected_f047 = float((np.sum(p) ** 2) / np.sum(p * p))
    assert out["note_effective_component_density"] == pytest.approx(
        expected_f047, abs=1e-9
    )
    d1, n_d1 = balanced_density_from_component_tables(harmonic_df=harmonic)
    assert int(out["note_balanced_component_density_pool_count"]) == n_d1 == 3
    assert out["note_balanced_component_density"] == pytest.approx(d1, abs=1e-12)
    assert balanced_density_is_primary_valid(out["note_balanced_component_density"])


def test_empty_compile_pool_is_nan(tmp_path: Path) -> None:
    path = tmp_path / "empty" / "spectral_analysis.xlsx"
    path.parent.mkdir(parents=True, exist_ok=True)
    harmonic = pd.DataFrame(
        {
            "Harmonic Number": [1],
            "Frequency (Hz)": [110.0],
            "Amplitude_raw": [1.0],
            "include_for_density": [False],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        harmonic.to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
        pd.DataFrame({"Frequency (Hz)": [], "Amplitude_raw": []}).to_excel(
            writer, sheet_name="Inharmonic Spectrum", index=False
        )
        pd.DataFrame({"Frequency (Hz)": [], "Amplitude_raw": []}).to_excel(
            writer, sheet_name="Sub-bass band", index=False
        )
    out = _energy_distribution_density(path)
    assert np.isnan(out["note_balanced_component_density"])
    assert int(out["note_balanced_component_density_pool_count"]) == 0
    assert balanced_density_is_primary_valid(out["note_balanced_component_density"]) is False


def test_column_sits_immediately_left_of_ewsd() -> None:
    df = pd.DataFrame(
        {
            "Note": ["A2"],
            "EWSD_score_total": [1.0],
            EWSD_ACOUSTIC_BALANCED_COLUMN: [2.0],
            BALANCED_DENSITY_COLUMN: [3.0],
            BALANCED_DENSITY_POOL_COUNT_COLUMN: [4],
            "other": [0],
        }
    )
    placed = place_balanced_density_left_of_ewsd(df)
    cols = list(placed.columns)
    ewsd_i = cols.index(EWSD_ACOUSTIC_BALANCED_COLUMN)
    assert cols[ewsd_i - 1] == BALANCED_DENSITY_COLUMN
    assert cols[ewsd_i - 2] == BALANCED_DENSITY_POOL_COUNT_COLUMN


def test_package_and_citation_are_4_3_0() -> None:
    from analysis_provenance import resolve_package_version

    pkg, source = resolve_package_version()
    assert source.startswith("pyproject.toml")
    assert pkg == "4.6.0"
    citation = Path("CITATION.cff").read_text(encoding="utf-8")
    assert citation.count('version: "4.6.0"') >= 2


def test_registry_f056_defined_and_ewsd_deprecated() -> None:
    d1 = get_metric_definition("note_balanced_component_density")
    assert d1 is not None
    assert BALANCED_DENSITY_FORMULA_ID in d1.formula
    assert BALANCED_DENSITY_PROVENANCE in d1.formula
    assert BALANCED_DENSITY_POOL_DEFINITION in d1.formula
    ewsd = get_metric_definition("EWSD_score_acoustic_balanced")
    assert ewsd is not None
    assert "diagnostic only; level-dependent; not for cross-note comparison" in (
        ewsd.formula + " " + ewsd.physical_interpretation
    )
