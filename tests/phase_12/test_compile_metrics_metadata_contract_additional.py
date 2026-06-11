from __future__ import annotations

"""
Metadata / workbook / component-weight provenance contract tests for compile_metrics.py.

Layer 3 complement to test_compile_metrics_contract_additional.py and
test_compile_metrics_export_merge_additional.py. Exercises analysis-metadata
finalization, compile-guide construction, per-note workbook readers, schema
guards, and merge/enrich invariants without running the full compile pipeline.

No audio, GUI, plotting, or broad workbook integration.
"""

from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

import compile_metrics as cm


# ---------------------------------------------------------------------------
# Tiny workbook fixtures (Analysis_Metadata + optional spectrum sheets)
# ---------------------------------------------------------------------------

def _write_per_note_workbook(
    path: Path,
    meta_rows: list[dict[str, object]],
    *,
    harm_cols: list[str] | None = None,
    ih_cols: list[str] | None = None,
    sb_cols: list[str] | None = None,
    density_metrics_cols: list[str] | None = None,
) -> None:
    """Minimal xlsx scaffold for metadata reader / schema-assessment helpers."""
    harm_cols = harm_cols if harm_cols is not None else ["Amplitude_raw", "Power_raw"]
    ih_cols = ih_cols if ih_cols is not None else ["Amplitude_raw", "Power_raw"]
    sb_cols = sb_cols if sb_cols is not None else ["Amplitude_raw", "Power_raw"]
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(meta_rows).to_excel(writer, sheet_name="Analysis_Metadata", index=False)
        if harm_cols:
            pd.DataFrame({c: [1.0] for c in harm_cols}).to_excel(
                writer, sheet_name="Harmonic Spectrum", index=False
            )
        if ih_cols:
            pd.DataFrame({c: [1.0] for c in ih_cols}).to_excel(
                writer, sheet_name="Inharmonic Spectrum", index=False
            )
        if sb_cols:
            pd.DataFrame({c: [1.0] for c in sb_cols}).to_excel(
                writer, sheet_name="Sub-bass band", index=False
            )
        if density_metrics_cols is not None:
            pd.DataFrame({c: [1.0] for c in density_metrics_cols}).to_excel(
                writer, sheet_name="Density_Metrics", index=False
            )


def _canonical_integrated_meta_rows(**overrides: object) -> list[dict[str, object]]:
    defaults: dict[str, object] = {
        "analysis_schema_version": cm.EXPECTED_ANALYSIS_SCHEMA_VERSION,
        "model_weights_source": "current_analysis",
        "component_profile_source": "integrated_single_pass",
        "export_alignment_source": "disabled_integrated_single_pass",
        "export_alignment_factor": 1.0,
        "component_harmonic_energy_ratio": 0.50,
        "component_inharmonic_energy_ratio": 0.30,
        "component_subbass_energy_ratio": 0.20,
    }
    merged = {**defaults, **overrides}
    return [{"Parameter": key, "Value": value} for key, value in merged.items()]


# ---------------------------------------------------------------------------
# 1. Formal schema / version tokens
# ---------------------------------------------------------------------------

def test_expected_analysis_schema_version_token_is_stable() -> None:
    assert cm.EXPECTED_ANALYSIS_SCHEMA_VERSION == "single_pass_raw_export_v2"


def test_stale_pipeline_user_message_is_non_empty_stable_string() -> None:
    assert isinstance(cm.STALE_PIPELINE_USER_MESSAGE, str)
    assert "legacy" in cm.STALE_PIPELINE_USER_MESSAGE.lower()
    assert cm.STALE_PIPELINE_USER_MESSAGE == cm.STALE_PIPELINE_USER_MESSAGE.strip()


def test_legacy_ratio_alias_keys_match_batch_energy_ratio_pattern() -> None:
    assert cm._LEGACY_RATIO_ALIAS_KEYS == (
        "batch_harmonic_energy_ratio",
        "batch_inharmonic_energy_ratio",
        "batch_subbass_energy_ratio",
    )


# ---------------------------------------------------------------------------
# 2. _finalize_analysis_metadata_for_workbook
# ---------------------------------------------------------------------------

def test_finalize_analysis_metadata_sets_policy_keys_and_sample_counts() -> None:
    meta: dict[str, object] = {"weight_function": "log", "smoothing_enabled": None}
    base_df = pd.DataFrame(
        {
            "Note": ["C4", "C4", "D4"],
            "MIDI": [60, 60, 62],
            "component_energy_denominator": ["harmonic_plus_inharmonic_plus_subbass"] * 3,
        }
    )
    cm._finalize_analysis_metadata_for_workbook(meta, base_df)

    assert meta["component_ratio_sum_policy"].startswith("component_harmonic_energy_ratio")
    assert meta["model_weight_policy"] == "current_analysis_component_HIS_projected_to_HI_model_weights"
    assert meta["sample_row_count"] == 3
    assert meta["unique_note_label_count"] == 2
    assert meta["duplicate_note_label_count"] == 2
    assert meta["component_energy_denominator"] == "harmonic_plus_inharmonic_plus_subbass"
    assert meta["smoothing_enabled"] == "not_available_at_compile_stage"
    assert meta["harmonic_tolerance"] == "not_available_at_compile_stage"
    assert meta["weight_function_ui_label"] == "Logarithmic"


def test_finalize_analysis_metadata_empty_base_df_uses_documented_fallbacks() -> None:
    meta: dict[str, object] = {"weight_function": ""}
    cm._finalize_analysis_metadata_for_workbook(meta, pd.DataFrame())

    assert meta["component_energy_denominator"] == "harmonic_plus_inharmonic_plus_subbass"
    assert meta["dissonance_partial_cap"] == "not_available_at_compile_stage"
    assert meta["pca_export_status"] == "not_available_at_compile_stage"
    assert meta["weight_function_ui_label"] == "not_available_at_compile_stage"
    assert "sample_row_count" not in meta


def test_finalize_analysis_metadata_preserves_existing_analysis_date() -> None:
    meta: dict[str, object] = {"analysis_date": "2020-01-01T00:00:00"}
    cm._finalize_analysis_metadata_for_workbook(meta, pd.DataFrame({"Note": ["C4"]}))
    assert meta["analysis_date"] == "2020-01-01T00:00:00"


def test_finalize_analysis_metadata_multiple_component_denominators_marked_mixed() -> None:
    meta: dict[str, object] = {}
    base_df = pd.DataFrame(
        {
            "Note": ["C4", "D4"],
            "component_energy_denominator": ["harmonic_plus_inharmonic", "harmonic_plus_inharmonic_plus_subbass"],
        }
    )
    cm._finalize_analysis_metadata_for_workbook(meta, base_df)
    assert meta["component_energy_denominator"] == "multiple"


def test_finalize_analysis_metadata_is_deterministic_for_same_inputs() -> None:
    base_df = pd.DataFrame({"Note": ["C4"], "MIDI": [60]})
    meta_a: dict[str, object] = {"weight_function": "linear"}
    meta_b: dict[str, object] = {"weight_function": "linear", "analysis_date": "fixed-date"}
    cm._finalize_analysis_metadata_for_workbook(meta_a, base_df, pca_include_dissonance=True)
    cm._finalize_analysis_metadata_for_workbook(meta_b, base_df, pca_include_dissonance=True)
    meta_a.pop("analysis_date", None)
    meta_b.pop("analysis_date", None)
    assert meta_a == meta_b


# ---------------------------------------------------------------------------
# 3. _attach_weight_function_ui_label
# ---------------------------------------------------------------------------

def test_attach_weight_function_ui_label_maps_known_key() -> None:
    meta: dict[str, object] = {"weight_function": "cubic"}
    cm._attach_weight_function_ui_label(meta)
    assert meta["weight_function_ui_label"] != "not_available_at_compile_stage"
    assert isinstance(meta["weight_function_ui_label"], str)


def test_attach_weight_function_ui_label_missing_key_uses_fallback() -> None:
    meta: dict[str, object] = {}
    cm._attach_weight_function_ui_label(meta)
    assert meta["weight_function_ui_label"] == "not_available_at_compile_stage"


# ---------------------------------------------------------------------------
# 4. _build_compile_guide_dataframe
# ---------------------------------------------------------------------------

def test_build_compile_guide_dataframe_schema_and_column_presence_rows() -> None:
    cols = ["Note", "weight_function", "Harmonic Partials sum", "Total sum"]
    guide = cm._build_compile_guide_dataframe({"weight_function": "log"}, cols)

    assert list(guide.columns) == ["Category", "Item", "Value"]
    assert len(guide) >= 10
    presence = guide[guide["Category"] == "Density_Metrics — column present?"]
    assert set(presence["Item"]) >= {
        "weight_function",
        "Harmonic Partials sum",
        "Inharmonic Partials sum",
        "Sub-bass sum",
        "Total sum",
    }
    yes_items = set(presence.loc[presence["Value"] == "yes", "Item"])
    assert yes_items == {"weight_function", "Harmonic Partials sum", "Total sum"}
    assert presence.loc[presence["Item"] == "Sub-bass sum", "Value"].iloc[0] == "no"


def test_build_compile_guide_dataframe_is_deterministic_and_independent() -> None:
    meta = {"weight_function": "linear"}
    cols = ["Note"]
    first = cm._build_compile_guide_dataframe(meta, cols)
    second = cm._build_compile_guide_dataframe(meta, cols)
    pd.testing.assert_frame_equal(first, second)
    meta["weight_function"] = "mutated"
    third = cm._build_compile_guide_dataframe({"weight_function": "linear"}, cols)
    pd.testing.assert_frame_equal(first, third)


# ---------------------------------------------------------------------------
# 5. Component weights / provenance readers
# ---------------------------------------------------------------------------

def test_read_component_weights_reads_canonical_h_i_s_separately(tmp_path: Path) -> None:
    path = tmp_path / "spectral_analysis.xlsx"
    _write_per_note_workbook(path, _canonical_integrated_meta_rows())
    w_h, w_i, w_s, legacy_only = cm._read_component_weights_from_analysis_metadata(path)
    assert w_h == pytest.approx(0.50)
    assert w_i == pytest.approx(0.30)
    assert w_s == pytest.approx(0.20)
    assert legacy_only is False


def test_read_component_weights_legacy_aliases_only_flag_without_canonical(tmp_path: Path) -> None:
    path = tmp_path / "legacy.xlsx"
    rows = [
        {"Parameter": "batch_harmonic_energy_ratio", "Value": 0.6},
        {"Parameter": "batch_inharmonic_energy_ratio", "Value": 0.3},
        {"Parameter": "batch_subbass_energy_ratio", "Value": 0.1},
    ]
    _write_per_note_workbook(path, rows)
    w_h, w_i, w_s, legacy_only = cm._read_component_weights_from_analysis_metadata(path)
    assert w_h is None and w_i is None and w_s is None
    assert legacy_only is True


def test_read_component_weights_first_canonical_row_wins(tmp_path: Path) -> None:
    path = tmp_path / "dup.xlsx"
    rows = [
        {"Parameter": "component_harmonic_energy_ratio", "Value": 0.10},
        {"Parameter": "component_harmonic_energy_ratio", "Value": 0.90},
    ]
    _write_per_note_workbook(path, rows)
    w_h, _, _, _ = cm._read_component_weights_from_analysis_metadata(path)
    assert w_h == pytest.approx(0.10)


def test_read_component_weights_missing_sheet_returns_none_tuple(tmp_path: Path) -> None:
    path = tmp_path / "no_meta.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame({"x": [1]}).to_excel(writer, sheet_name="Metrics", index=False)
    assert cm._read_component_weights_from_analysis_metadata(path) == (None, None, None, False)


def test_read_analysis_schema_version_from_workbook(tmp_path: Path) -> None:
    path = tmp_path / "schema.xlsx"
    _write_per_note_workbook(
        path,
        [{"Parameter": "analysis_schema_version", "Value": cm.EXPECTED_ANALYSIS_SCHEMA_VERSION}],
    )
    assert (
        cm._read_analysis_schema_version_from_workbook(path)
        == cm.EXPECTED_ANALYSIS_SCHEMA_VERSION
    )


def test_read_analysis_metadata_scalar_preserves_provenance_text(tmp_path: Path) -> None:
    path = tmp_path / "provenance.xlsx"
    _write_per_note_workbook(
        path,
        [{"Parameter": "model_weights_source", "Value": "current_analysis"}],
    )
    assert cm._read_analysis_metadata_scalar(path, "model_weights_source") == "current_analysis"
    assert cm._read_analysis_metadata_scalar(path, "missing_parameter") is None


# ---------------------------------------------------------------------------
# 6. assess_per_note_workbook_schema / scan / assert guards
# ---------------------------------------------------------------------------

def test_assess_per_note_workbook_schema_valid_integrated_single_pass(tmp_path: Path) -> None:
    path = tmp_path / "valid.xlsx"
    _write_per_note_workbook(path, _canonical_integrated_meta_rows())
    result = cm.assess_per_note_workbook_schema(path)

    assert result["schema_ok"] is True
    assert result["schema_version"] == cm.EXPECTED_ANALYSIS_SCHEMA_VERSION
    assert result["has_amplitude_raw"] is True
    assert result["has_power_raw"] is True
    assert result["model_weights_source"] == "current_analysis"
    assert result["component_profile_source"] == "integrated_single_pass"
    assert result["export_alignment_source"] == "disabled_integrated_single_pass"
    assert result["export_alignment_factor"] == pytest.approx(1.0)
    assert result["problems"] == []
    assert result["looks_like_per_note_proc_audio_export"] is True


def test_assess_per_note_workbook_schema_stale_version_reports_problem(tmp_path: Path) -> None:
    path = tmp_path / "stale.xlsx"
    rows = _canonical_integrated_meta_rows(
        analysis_schema_version="legacy_export_v0",
    )
    _write_per_note_workbook(path, rows)
    result = cm.assess_per_note_workbook_schema(path)
    assert result["schema_ok"] is False
    assert any("analysis_schema_version" in p for p in result["problems"])


def test_assess_per_note_workbook_schema_integrated_single_pass_batch_leak(tmp_path: Path) -> None:
    path = tmp_path / "batch_leak.xlsx"
    _write_per_note_workbook(
        path,
        _canonical_integrated_meta_rows(),
        ih_cols=["Amplitude_raw", "Power_raw", "batch_inharmonic_energy_ratio"],
    )
    result = cm.assess_per_note_workbook_schema(path)
    assert any("batch_" in p for p in result["problems"])


def test_assess_per_note_workbook_schema_non_per_note_scaffold_not_stale(tmp_path: Path) -> None:
    path = tmp_path / "scalar_only.xlsx"
    _write_per_note_workbook(path, _canonical_integrated_meta_rows(), harm_cols=[], ih_cols=[], sb_cols=[])
    result = cm.assess_per_note_workbook_schema(path)
    assert result["looks_like_per_note_proc_audio_export"] is False
    assert result["problems"] == []


def test_assess_per_note_workbook_schema_density_metrics_layout_heuristic(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit_dm.xlsx"
    _write_per_note_workbook(
        audit_path,
        _canonical_integrated_meta_rows(),
        density_metrics_cols=["density_metric_raw", "density_metric_normalized", "Note"],
    )
    assert cm.assess_per_note_workbook_schema(audit_path)["density_metrics_layout"] == "audit_canonical"

    legacy_path = tmp_path / "legacy_dm.xlsx"
    _write_per_note_workbook(
        legacy_path,
        _canonical_integrated_meta_rows(),
        density_metrics_cols=[
            "Note",
            "weight_function",
            "Harmonic Partials sum",
            "Inharmonic Partials sum",
            "Sub-bass sum",
            "Total sum",
        ],
    )
    assert cm.assess_per_note_workbook_schema(legacy_path)["density_metrics_layout"] == "legacy_six_columns"


def test_scan_results_dir_for_stale_per_note_workbooks_counts_valid_and_stale(tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    valid = results_dir / "note_a" / "spectral_analysis.xlsx"
    valid.parent.mkdir()
    stale = results_dir / "note_b" / "spectral_analysis.xlsx"
    stale.parent.mkdir()
    _write_per_note_workbook(valid, _canonical_integrated_meta_rows())
    _write_per_note_workbook(
        stale,
        _canonical_integrated_meta_rows(analysis_schema_version="old_schema"),
    )
    summary = cm.scan_results_dir_for_stale_per_note_workbooks(results_dir)
    assert summary["expected_schema"] == cm.EXPECTED_ANALYSIS_SCHEMA_VERSION
    assert summary["total"] == 2
    assert summary["valid"] == 1
    assert summary["stale"] == 1
    assert summary["first_failing_path"] is not None


def test_assert_results_dir_schema_or_raise_passes_for_valid_dir(tmp_path: Path) -> None:
    results_dir = tmp_path / "ok"
    results_dir.mkdir()
    path = results_dir / "spectral_analysis.xlsx"
    _write_per_note_workbook(path, _canonical_integrated_meta_rows())
    summary = cm.assert_results_dir_schema_or_raise(results_dir)
    assert summary["stale"] == 0


def test_assert_results_dir_schema_or_raise_raises_with_stale_message(tmp_path: Path) -> None:
    results_dir = tmp_path / "bad"
    results_dir.mkdir()
    path = results_dir / "spectral_analysis.xlsx"
    _write_per_note_workbook(
        path,
        _canonical_integrated_meta_rows(analysis_schema_version="stale_v1"),
    )
    with pytest.raises(RuntimeError, match=cm.STALE_PIPELINE_USER_MESSAGE.split()[0]):
        cm.assert_results_dir_schema_or_raise(results_dir)


# ---------------------------------------------------------------------------
# 7. Metadata merge / enrich invariants (metadata-specific angles)
# ---------------------------------------------------------------------------

def test_merge_canonical_metadata_setdefault_preserves_preexisting_version_tokens() -> None:
    meta: dict[str, object] = {
        "export_schema_version": "pinned_export_v1",
        "density_formula_version": "pinned_density_v1",
        "input_schema_validation_status": "custom_status",
        "pipeline_contract_version": "pinned_contract",
    }
    snapshot = deepcopy(meta)
    cm._merge_canonical_compiled_workbook_metadata(
        meta,
        file_pattern="results/*/spectral_analysis.xlsx",
        allow_legacy_super_json=False,
        input_schema_validation_status="ignored_if_preexisting",
    )
    assert meta["export_schema_version"] == snapshot["export_schema_version"]
    assert meta["density_formula_version"] == snapshot["density_formula_version"]
    assert meta["input_schema_validation_status"] == snapshot["input_schema_validation_status"]
    assert meta["pipeline_contract_version"] == snapshot["pipeline_contract_version"]
    assert meta["compiled_by"] == "compile_metrics.compile_density_metrics_with_pca"


def test_enrich_compiled_metadata_prefers_existing_canonical_over_row_zero() -> None:
    df = pd.DataFrame({"window": ["hann_from_row"], "N FFT": [4096]})
    enriched = cm._enrich_compiled_metadata_from_df({"window": "pinned_window"}, df)
    assert enriched["window"] == "pinned_window"
    assert enriched["window_type"] == "pinned_window"
    assert enriched["n_fft"] == 4096


def test_enrich_compiled_metadata_does_not_mutate_input_metadata_dict() -> None:
    original: dict[str, object] = {"density_formula": "keep_me"}
    snapshot = deepcopy(original)
    df = pd.DataFrame({"window": ["hann"]})
    enriched = cm._enrich_compiled_metadata_from_df(original, df)
    assert original == snapshot
    assert enriched is not original
    assert enriched["window"] == "hann"


def test_enrich_compiled_metadata_empty_df_returns_copy_without_row_keys() -> None:
    original: dict[str, object] = {"run_id": "abc"}
    enriched = cm._enrich_compiled_metadata_from_df(original, pd.DataFrame())
    assert enriched == original
    assert enriched is not original
