from __future__ import annotations

"""
Fourth Phase 12 workbook/export contract layer for compile_metrics.py.

Complements the three existing Phase 12 compile_metrics layers and phase_6–11
export suites with narrowly targeted checks on workbook validation, diagnostic
sheet builders, weighted-density attachment, canonical/diagnostic column
partitioning, publication path markers, and metadata/schema propagation.

No production code changes. No audio, GUI, plotting, or full compile pipeline.
"""

from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import compile_metrics as cm


def _write_minimal_workbook(
    path: Path,
    density_df: pd.DataFrame,
    *,
    meta_rows: list[dict[str, object]] | None = None,
    extra_sheets: dict[str, pd.DataFrame] | None = None,
) -> None:
    rows = meta_rows or [
        {"Parameter": "analysis_schema_version", "Value": cm.EXPECTED_ANALYSIS_SCHEMA_VERSION},
    ]
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        density_df.to_excel(writer, sheet_name="Density_Metrics", index=False)
        pd.DataFrame(rows).to_excel(writer, sheet_name="Analysis_Metadata", index=False)
        for sheet_name, frame in (extra_sheets or {}).items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)


def _minimal_density_row(**overrides: float | str) -> dict[str, object]:
    base: dict[str, object] = {
        "Note": "C4",
        "density_metric_raw": 1.25,
        "component_harmonic_energy_ratio": 0.70,
        "component_inharmonic_energy_ratio": 0.20,
        "component_subbass_energy_ratio": 0.10,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. validate_compiled_density_workbook
# ---------------------------------------------------------------------------


def test_validate_compiled_density_workbook_accepts_minimal_valid_structure(tmp_path: Path) -> None:
    path = tmp_path / "compiled.xlsx"
    _write_minimal_workbook(path, pd.DataFrame([_minimal_density_row()]))
    assert cm.validate_compiled_density_workbook(path) == []


def test_validate_compiled_density_workbook_reports_missing_file() -> None:
    errs = cm.validate_compiled_density_workbook(Path("/nonexistent/compiled.xlsx"))
    assert len(errs) == 1
    assert "File not found" in errs[0]


def test_validate_compiled_density_workbook_rejects_forbidden_density_metrics_column(
    tmp_path: Path,
) -> None:
    path = tmp_path / "compiled.xlsx"
    row = _minimal_density_row()
    row["Window"] = "hann"
    _write_minimal_workbook(path, pd.DataFrame([row]))
    errs = cm.validate_compiled_density_workbook(path)
    assert any("forbidden column" in e and "Window" in e for e in errs)


def test_validate_compiled_density_workbook_metadata_sheet_claim_without_debug_counts(
    tmp_path: Path,
) -> None:
    path = tmp_path / "compiled.xlsx"
    meta = [
        {"Parameter": "analysis_schema_version", "Value": cm.EXPECTED_ANALYSIS_SCHEMA_VERSION},
        {"Parameter": "debug_counts_export_status", "Value": "exported"},
    ]
    _write_minimal_workbook(path, pd.DataFrame([_minimal_density_row()]), meta_rows=meta)
    errs = cm.validate_compiled_density_workbook(path)
    assert any("Debug_Counts exported but sheet is missing" in e for e in errs)


def test_validate_compiled_density_workbook_density_metric_normalized_invariant(
    tmp_path: Path,
) -> None:
    path = tmp_path / "compiled.xlsx"
    df = pd.DataFrame(
        [
            {
                **_minimal_density_row(),
                "density_metric_raw": 2.0,
                "density_metric_normalized": 0.25,
            },
            {
                **_minimal_density_row(Note="D4"),
                "density_metric_raw": 4.0,
                "density_metric_normalized": 1.0,
            },
        ]
    )
    _write_minimal_workbook(path, df)
    errs = cm.validate_compiled_density_workbook(path)
    assert any("density_metric_normalized must equal density_metric_raw" in e for e in errs)


# ---------------------------------------------------------------------------
# 2. Diagnostic / validation / per-note satellite sheet builders
# ---------------------------------------------------------------------------


def test_build_debug_counts_sheet_maps_deprecated_legacy_alias_column() -> None:
    df = pd.DataFrame(
        {
            "Note": ["C4"],
            "inharmonic_bin_count_deprecated_legacy_alias": [42],
            "debug_counts_status": ["ok"],
        }
    )
    out = cm._build_debug_counts_sheet(df)
    assert out is not None
    assert out["inharmonic_bin_count"].iloc[0] == pytest.approx(42.0)
    assert "inharmonic_bin_count_deprecated_legacy_alias" in out.columns


def test_build_debug_counts_sheet_returns_none_when_only_note_column() -> None:
    assert cm._build_debug_counts_sheet(pd.DataFrame({"Note": ["C4"]})) is None


def test_build_debug_counts_sheet_does_not_mutate_input() -> None:
    df = pd.DataFrame(
        {
            "Note": ["C4"],
            "residual_spectral_row_count": [5],
            "debug_counts_status": ["ok"],
        }
    )
    snap = df.copy()
    cm._build_debug_counts_sheet(df)
    pd.testing.assert_frame_equal(df, snap)


def test_build_validation_metrics_sheet_selects_harmonic_alignment_subset() -> None:
    df = pd.DataFrame(
        {
            "Note": ["C4"],
            "harmonic_alignment_status": ["ok"],
            "harmonic_alignment_coverage_ratio": [0.95],
            "density_metric_raw": [1.2],
        }
    )
    out = cm._build_validation_metrics_sheet(df)
    assert out is not None
    assert "harmonic_alignment_status" in out.columns
    assert "density_metric_raw" not in out.columns


def test_build_per_note_processing_metadata_keeps_ratios_off_density_metrics() -> None:
    df = pd.DataFrame(
        {
            "Note": ["C4"],
            "n_fft": [8192],
            "window": ["hann"],
            "component_harmonic_energy_ratio": [0.7],
            "component_inharmonic_energy_ratio": [0.2],
            "component_subbass_energy_ratio": [0.1],
            "density_metric_raw": [1.25],
        }
    )
    out = cm._build_per_note_processing_metadata_sheet(df)
    assert out is not None
    assert out.columns[0] == "Note"
    assert "component_harmonic_energy_ratio" in out.columns
    assert "density_metric_raw" not in out.columns
    assert out["n_fft"].iloc[0] == 8192


def test_build_phase7_final_validation_summary_empty_frame_is_deterministic() -> None:
    a = cm._build_phase7_final_validation_summary_sheet(
        pd.DataFrame(), harmonic_weight=0.5, inharmonic_weight=0.3, subbass_weight=0.2
    )
    b = cm._build_phase7_final_validation_summary_sheet(
        pd.DataFrame(), harmonic_weight=0.5, inharmonic_weight=0.3, subbass_weight=0.2
    )
    pd.testing.assert_frame_equal(a, b)
    assert a["value"].iloc[0] == "empty_density_metrics_dataframe"


# ---------------------------------------------------------------------------
# 3. Weighted density attachment (canonical vs alias; no batch fallback)
# ---------------------------------------------------------------------------


def test_compute_weighted_density_prefers_component_ratios_over_strict_aliases() -> None:
    df = pd.DataFrame(
        {
            "Note": ["C4"],
            "Harmonic Partials sum": [2.0],
            "Inharmonic Partials sum": [1.0],
            "Sub-bass sum": [0.5],
            "component_harmonic_energy_ratio": [0.70],
            "component_inharmonic_energy_ratio": [0.20],
            "component_subbass_energy_ratio": [0.10],
            "harmonic_energy_ratio": [0.99],
            "batch_harmonic_energy_ratio": [0.05],
        }
    )
    out = cm._compute_weighted_density_columns_for_wide_df(df)
    expected = 2.0 * 0.70 + 1.0 * 0.20 + 0.5 * 0.10
    assert out["density_metric_raw"].iloc[0] == pytest.approx(expected)
    assert out["component_harmonic_energy_ratio"].iloc[0] == pytest.approx(0.70)
    assert out["density_weights_source"].iloc[0] == "per_note_energy_ratio"


def test_compute_weighted_density_phase2_profile_overrides_application_weights() -> None:
    df = pd.DataFrame(
        {
            "Note": ["C4"],
            "Harmonic Partials sum": [2.0],
            "Inharmonic Partials sum": [1.0],
            "Sub-bass sum": [0.5],
            "component_harmonic_energy_ratio": [0.70],
            "component_inharmonic_energy_ratio": [0.20],
            "component_subbass_energy_ratio": [0.10],
        }
    )
    out = cm._compute_weighted_density_columns_for_wide_df(
        df, harmonic_weight=0.6, inharmonic_weight=0.3, subbass_weight=0.1
    )
    assert out["density_weights_source"].iloc[0] == "phase2_corpus_profile"
    assert out["density_metric_raw"].iloc[0] == pytest.approx(2.0 * 0.6 + 1.0 * 0.3 + 0.5 * 0.1)
    assert out["density_metric_normalized"].iloc[0] == pytest.approx(1.0)


def test_compute_weighted_density_skips_when_partial_sums_missing() -> None:
    df = pd.DataFrame({"Note": ["C4"], "component_harmonic_energy_ratio": [0.7]})
    out = cm._compute_weighted_density_columns_for_wide_df(df)
    assert "density_metric_raw" not in out.columns


# ---------------------------------------------------------------------------
# 4. Canonical / diagnostic / legacy column partitioning
# ---------------------------------------------------------------------------


def test_slice_compiled_df_separates_canonical_diagnostic_and_legacy_columns() -> None:
    df = pd.DataFrame(
        {
            "Note": ["C4"],
            "effective_partial_density": [3.0],
            "component_harmonic_energy_ratio": [0.7],
            "density_metric_raw": [1.25],
            "harmonic_energy_ratio": [0.99],
            "harmonic_amplitude_sum": [2.0],
            "Density Metric": [5.0],
            "__source_file_path": [r"C:\secret\note.xlsx"],
        }
    )
    canonical = cm._slice_compiled_df_by_status(df, "canonical")
    diagnostic = cm._slice_compiled_df_by_status(df, "diagnostic")
    legacy = cm._slice_compiled_df_by_status(df, "legacy")

    assert "effective_partial_density" in canonical.columns
    assert "component_harmonic_energy_ratio" in canonical.columns
    assert "density_metric_raw" not in canonical.columns
    assert "harmonic_energy_ratio" not in canonical.columns

    assert "density_metric_raw" in diagnostic.columns
    assert "harmonic_energy_ratio" in diagnostic.columns
    assert "harmonic_amplitude_sum" in diagnostic.columns
    assert "effective_partial_density" not in diagnostic.columns

    assert "Density Metric" in legacy.columns
    assert "__source_file_path" not in legacy.columns


def test_slice_compiled_df_canonical_preserves_declared_column_order() -> None:
    df = pd.DataFrame(
        {
            "Note": ["C4"],
            "qc_status": ["validated_pipeline"],
            "effective_partial_density": [2.0],
            "component_harmonic_energy_ratio": [0.6],
            "spectral_entropy": [1.5],
        }
    )
    out = cm._slice_compiled_df_by_status(df, "canonical")
    ordered = [c for c in cm.CANONICAL_METRIC_COLUMNS if c in out.columns]
    assert list(out.columns[: len(ordered)]) == ordered


# ---------------------------------------------------------------------------
# 5. Publication safety and path-derived metadata helpers
# ---------------------------------------------------------------------------


def test_publication_safe_folder_path_marker_redacts_when_enabled() -> None:
    from metadata_sanitizer import REDACT_TOKEN, publication_redaction_enabled

    marker = cm._publication_safe_folder_path_marker(r"C:\Users\secret\results\C4")
    if publication_redaction_enabled():
        assert marker == REDACT_TOKEN
    else:
        assert marker == r"C:\Users\secret\results\C4"


def test_extract_dynamics_from_path_finds_marked_dynamics() -> None:
    assert cm.extract_dynamics_from_path("/corpus/clarinet_mf_A4/analysis_results") == "mf"
    assert cm.extract_dynamics_from_path("violin_pp_sustain.wav") == "pp"


def test_extract_dynamics_from_path_rejects_embedded_pp_in_appdata() -> None:
    assert cm.extract_dynamics_from_path(r"C:\Users\me\AppData\Local\results\note.wav") is None


# ---------------------------------------------------------------------------
# 6. Workbook write metadata propagation (helper-level, tmp_path only)
# ---------------------------------------------------------------------------


def test_merge_canonical_workbook_metadata_propagates_schema_and_formula_tokens() -> None:
    meta: dict[str, object] = {"analysis_schema_version": cm.EXPECTED_ANALYSIS_SCHEMA_VERSION}
    cm._merge_canonical_compiled_workbook_metadata(
        meta,
        file_pattern="results/*/spectral_analysis.xlsx",
        allow_legacy_super_json=False,
        input_schema_validation_status="validated",
    )
    assert meta["export_schema_version"] == cm.EXPORT_SCHEMA_VERSION
    assert meta["density_formula_version"] == cm.DENSITY_FORMULA_VERSION
    assert meta["input_schema_validation_status"] == "validated"
    assert meta["publication_output_allowed"] is True


def test_write_compiled_excel_preserves_canonical_density_scalar_on_minimal_frame(tmp_path: Path) -> None:
    """Uses the same slim synthetic frame pattern as phase_6 legacy-alias tests."""
    outp = tmp_path / "compiled.xlsx"
    raw_value = 1.23
    df = pd.DataFrame(
        {
            "Note": ["C4"],
            "effective_partial_density": [raw_value],
            "density_metric_raw": [raw_value],
            "harmonic_density_component": [1.0],
            "inharmonic_density_component": [0.2],
            "subbass_density_component": [0.03],
        }
    )
    cm._write_compiled_excel(outp, df, metadata={})
    with pd.ExcelFile(outp) as xf:
        assert "Analysis_Metadata" in xf.sheet_names
        if "Canonical_Metrics" in xf.sheet_names:
            canonical = xf.parse("Canonical_Metrics")
            assert canonical["effective_partial_density"].iloc[0] == pytest.approx(raw_value)
        else:
            main_sheet = "Density_Metrics" if "Density_Metrics" in xf.sheet_names else "Compiled Metrics"
            main = xf.parse(main_sheet)
            assert main["effective_partial_density"].iloc[0] == pytest.approx(raw_value)


# ---------------------------------------------------------------------------
# 7. Determinism / non-mutation
# ---------------------------------------------------------------------------


def test_compute_weighted_density_is_deterministic_and_non_mutating() -> None:
    df = pd.DataFrame(
        {
            "Note": ["C4"],
            "Harmonic Partials sum": [1.0],
            "Inharmonic Partials sum": [0.2],
            "Sub-bass sum": [0.05],
            "component_harmonic_energy_ratio": [0.7],
            "component_inharmonic_energy_ratio": [0.2],
            "component_subbass_energy_ratio": [0.1],
        }
    )
    snap = deepcopy(df)
    first = cm._compute_weighted_density_columns_for_wide_df(df)
    second = cm._compute_weighted_density_columns_for_wide_df(df)
    pd.testing.assert_frame_equal(first, second)
    pd.testing.assert_frame_equal(df, snap)
