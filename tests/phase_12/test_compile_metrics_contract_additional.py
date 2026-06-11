from __future__ import annotations

"""
Narrow contract/regression coverage for compile_metrics.py helpers.

Focus: schema tokens, column classification, alias separation, publication
forbidden columns, dead-column pruning, sheet/column pickers, weight-function
normalisation, optional export text coercion, and deterministic utilities.

Does not run the full audio pipeline, GUI, plotting, or broad Excel
integration (those live in phase_6–phase_11 suites).
"""

import json

import numpy as np
import pandas as pd
import pytest

import compile_metrics as cm


_REQUIRED_MINIMAL_DISPLAY = (
    "Note",
    "density_metric_raw",
    "component_harmonic_energy_ratio",
    "acoustic_f0_status",
)

_REQUIRED_PHASE7 = (
    "inharmonicity_coefficient_B",
    "inharmonicity_fit_status",
    "inharmonicity_fit_method",
)

_LEGACY_DISPLAY_NAMES = (
    "Density Metric",
    "Spectral Density Metric",
    "Combined Density Metric",
)


# ---------------------------------------------------------------------------
# 1. Schema invariants
# ---------------------------------------------------------------------------

def test_schema_column_lists_have_no_duplicates() -> None:
    for name, seq in (
        ("DENSITY_METRICS_MAIN_COLUMNS", cm.DENSITY_METRICS_MAIN_COLUMNS),
        ("CANONICAL_METRIC_COLUMNS", cm.CANONICAL_METRIC_COLUMNS),
        ("PHASE7_INHARMONICITY_COMPILED_COLUMNS", cm.PHASE7_INHARMONICITY_COMPILED_COLUMNS),
        ("PHASE7_OBSERVATION_EXPOSURE_COLUMNS", cm.PHASE7_OBSERVATION_EXPOSURE_COLUMNS),
    ):
        assert len(seq) == len(set(seq)), f"duplicate entries in {name}"


def test_minimal_display_list_pins_note_first_and_has_known_duplicate_body_sums() -> None:
    # The minimal display list intentionally repeats some body-ceiling columns
    # for export layout; pin that contract rather than requiring uniqueness.
    assert cm.DENSITY_METRICS_MINIMAL_DISPLAY_COLUMNS[0] == "Note"
    assert cm.DENSITY_METRICS_MINIMAL_DISPLAY_COLUMNS[1] == "density_metric_raw"
    assert (
        cm.DENSITY_METRICS_MINIMAL_DISPLAY_COLUMNS.count(
            "harmonic_component_energy_sum_body_ceiling"
        )
        >= 2
    )


def test_metric_columns_is_non_empty_and_includes_density_metric_label() -> None:
    assert cm.METRIC_COLUMNS
    assert "Density Metric" in cm.METRIC_COLUMNS
    # Historical duplicate entries exist for body-ceiling sums; pin that they remain stable.
    assert cm.METRIC_COLUMNS.count("harmonic_component_energy_sum_body_ceiling") >= 1


def test_minimal_display_and_weighted_columns_include_canonical_tokens() -> None:
    minimal = set(cm.DENSITY_METRICS_MINIMAL_DISPLAY_COLUMNS)
    for col in _REQUIRED_MINIMAL_DISPLAY:
        assert col in minimal
    weighted = cm.DENSITY_METRICS_WEIGHTED_DENSITY_COLUMNS
    assert "density_weighted_sum" in weighted
    assert "density_log_weighted" in weighted
    assert cm.DENSITY_METRICS_MINIMAL_DISPLAY_COLUMNS[0] == "Note"
    assert cm.DENSITY_METRICS_MINIMAL_DISPLAY_COLUMNS[1] == "density_metric_raw"


def test_phase7_and_legacy_display_contracts() -> None:
    main = set(cm.DENSITY_METRICS_MAIN_COLUMNS)
    for col in _REQUIRED_PHASE7:
        assert col in main
    legacy_exact = cm.LEGACY_COLUMN_EXACT_NAMES
    for col in _LEGACY_DISPLAY_NAMES:
        assert col in legacy_exact
    omitted = cm._OMIT_FROM_COMPILED_METRICS_EXPORT
    assert "Total Metric" in omitted
    assert cm.CANONICAL_PIPELINE_ROLE == "canonical_stage2_compilation"
    assert cm.EXPECTED_ANALYSIS_SCHEMA_VERSION == "single_pass_raw_export_v2"
    assert cm.PUBLICATION_OUTPUT_ALLOWED is True


def test_canonical_alias_columns_map_to_component_ratios() -> None:
    assert cm.CANONICAL_ALIAS_COLUMNS == {
        "harmonic_energy_ratio": "component_harmonic_energy_ratio",
        "inharmonic_energy_ratio": "component_inharmonic_energy_ratio",
        "subbass_energy_ratio": "component_subbass_energy_ratio",
    }


# ---------------------------------------------------------------------------
# 2. Forbidden / alias / classification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name, forbidden",
    [
        ("Window", True),
        ("n_fft", True),
        ("density_metric_raw", False),
        ("component_harmonic_energy_ratio", False),
        ("Spectral Density Metric", False),  # legacy display, not forbidden on DM
    ],
)
def test_density_metric_column_is_forbidden(name: str, forbidden: bool) -> None:
    assert cm.density_metric_column_is_forbidden(name) is forbidden


def test_classify_compiled_column_buckets() -> None:
    assert cm._classify_compiled_column("canonical_density") == "canonical"
    assert cm._classify_compiled_column("Density Metric") == "legacy"
    assert cm._classify_compiled_column("legacy_batch_ratio") == "legacy"
    assert cm._classify_compiled_column("pure_observation_w_h") == "diagnostic"
    assert cm._classify_compiled_column("compilation_error") == "diagnostic"
    assert cm._classify_compiled_column("qc_status") == "canonical"


def test_split_strict_alias_columns_preserves_canonical_and_copies_input() -> None:
    df = pd.DataFrame(
        {
            "Note": ["C4", "D4"],
            "density_metric_raw": [1.0, 2.0],
            "component_harmonic_energy_ratio": [0.7, 0.6],
            "harmonic_energy_ratio": [0.7, 0.6],
            "inharmonic_peak_count_deprecated_legacy_alias": [3, 4],
            "qc_status": ["ok", "ok"],
        }
    )
    snapshot = df.copy()
    main, aliases = cm._split_strict_alias_columns(df)
    assert list(main.columns) == [
        "Note",
        "density_metric_raw",
        "component_harmonic_energy_ratio",
        "qc_status",
    ]
    assert "harmonic_energy_ratio" in aliases.columns
    assert "inharmonic_peak_count_deprecated_legacy_alias" in aliases.columns
    assert "component_harmonic_energy_ratio" in main.columns
    pd.testing.assert_frame_equal(df, snapshot)


def test_split_strict_alias_columns_empty_passthrough() -> None:
    empty = pd.DataFrame()
    main, aliases = cm._split_strict_alias_columns(empty)
    assert main is empty
    assert aliases.empty


# ---------------------------------------------------------------------------
# 3. Export text / weight-function normalization
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, None),
        ("", None),
        ("  ", None),
        ("NaN", None),
        ("none", None),
        ("<NA>", None),
        ("validated_pipeline", "validated_pipeline"),
        ("  ok  ", "ok"),
    ],
)
def test_normalize_optional_export_text(raw: object, expected: object) -> None:
    assert cm._normalize_optional_export_text(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, "linear"),
        ("", "linear"),
        ("sum", "linear"),
        ("LOG", "log"),
        ("power", "power"),
        ("unknown", "linear"),
    ],
)
def test_normalise_density_weight_function(raw: object, expected: str) -> None:
    assert cm._normalise_density_weight_function(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("sum", "linear"),
        ("d2", "linear"),
        ("d8", "d17"),
        ("sqrt", "sqrt"),
        ("", "linear"),
    ],
)
def test_compile_operator_weight_function_key_preserves_discrete_keys(
    raw: str, expected: str
) -> None:
    assert cm._compile_operator_weight_function_key(raw) == expected


# ---------------------------------------------------------------------------
# 4. Merge / export helpers (DataFrame-level)
# ---------------------------------------------------------------------------

def test_drop_dead_columns_preserves_protected_phase7_and_zero_numeric() -> None:
    df = pd.DataFrame(
        {
            "Note": ["C4"],
            "sample_id": [None],
            "inharmonicity_fit_status": [None],
            "zeros": [0.0],
            "blank_text": [""],
            "metric": [1.0],
        }
    )
    out = cm._drop_dead_columns(df)
    assert list(out.columns) == [
        "Note",
        "sample_id",
        "inharmonicity_fit_status",
        "zeros",
        "metric",
    ]
    assert list(df.columns) == [
        "Note",
        "sample_id",
        "inharmonicity_fit_status",
        "zeros",
        "blank_text",
        "metric",
    ]


def test_slice_compiled_df_by_status_keeps_note_and_orders_canonical() -> None:
    df = pd.DataFrame(
        {
            "Note": ["C4"],
            "qc_status": ["ok"],
            "canonical_density": [0.5],
            "component_harmonic_energy_ratio": [0.7],
            "Density Metric": [0.4],
            "harmonic_energy_ratio": [0.7],
            "pure_observation_w_h": [0.8],
            "__source_file_path": ["/secret/path"],
        }
    )
    canonical = cm._slice_compiled_df_by_status(df, "canonical")
    legacy = cm._slice_compiled_df_by_status(df, "legacy")
    diagnostic = cm._slice_compiled_df_by_status(df, "diagnostic")

    assert list(canonical.columns)[0] == "Note"
    assert "canonical_density" in canonical.columns
    assert "qc_status" in canonical.columns
    assert "component_harmonic_energy_ratio" in canonical.columns
    assert canonical.columns.get_loc("component_harmonic_energy_ratio") < canonical.columns.get_loc(
        "canonical_density"
    )
    assert "__source_file_path" not in canonical.columns
    assert "Density Metric" in legacy.columns
    assert "harmonic_energy_ratio" in diagnostic.columns
    assert "pure_observation_w_h" in diagnostic.columns


def test_pick_sheet_case_insensitive_skips_metadata_sheets() -> None:
    sheets = ["Analysis_Metadata", "Harmonic Spectrum", "Metrics"]
    picked = cm._pick_sheet_case_insensitive(sheets, cm.HARMONIC_SPECTRUM_SHEET_PREFERENCES)
    assert picked == "Harmonic Spectrum"
    # Metadata sheet names must never win even when they substring-match preferences.
    only_meta = ["Analysis_Metadata", "Debug_Counts"]
    assert cm._pick_sheet_case_insensitive(only_meta, cm.HARMONIC_SPECTRUM_SHEET_PREFERENCES) is None


def test_pick_column_case_insensitive_returns_first_preference_match() -> None:
    cols = ["Frequency (Hz)", "Amplitude_raw", "Magnitude (dB)"]
    assert cm._pick_column_case_insensitive(cols, ("missing", "amplitude_raw")) == "Amplitude_raw"


def test_resolve_include_for_density_mask_honours_formal_tokens() -> None:
    df = pd.DataFrame(
        {
            "include_for_density": [True, 1, "yes", "YES", "false", 0, None, "", np.nan],
        }
    )
    cols_lower = {c.lower(): c for c in df.columns}
    mask, excluded = cm._resolve_include_for_density_mask(df, cols_lower)
    assert mask is not None
    assert excluded == 5
    assert mask.tolist() == [True, True, True, True, False, False, False, False, False]


def test_resolve_include_for_density_mask_absent_column() -> None:
    df = pd.DataFrame({"Note": ["C4"]})
    cols_lower = {c.lower(): c for c in df.columns}
    mask, excluded = cm._resolve_include_for_density_mask(df, cols_lower)
    assert mask is None
    assert excluded == 0


# ---------------------------------------------------------------------------
# 5. Numeric helpers / sheet preferences / note ordering
# ---------------------------------------------------------------------------

def test_sum_finite_numeric_ignores_nan_and_inf() -> None:
    series = pd.Series([1.0, np.nan, np.inf, 2.0, "3"])
    total, count = cm._sum_finite_numeric(series)
    assert total == pytest.approx(6.0)
    assert count == 3


def test_density_sheet_preferences_for_canonical_component_sheets() -> None:
    assert cm._density_sheet_preferences_for("Harmonic Spectrum") == cm.HARMONIC_SPECTRUM_SHEET_PREFERENCES
    assert cm._density_sheet_preferences_for("sub_bass_band") == cm.SUBBASS_SPECTRUM_SHEET_PREFERENCES


def test_density_sheet_preferences_unknown_sheet_raises() -> None:
    with pytest.raises(ValueError, match="unknown sheet_name"):
        cm._density_sheet_preferences_for("Metrics")


@pytest.mark.parametrize(
    "note, midi",
    [
        ("C4", 60),
        ("A4", 69),
        ("Bb3", 58),
        ("H2", 47),  # German B
        ("invalid", 10**9),
    ],
)
def test_note_to_midi_ordering(note: str, midi: int) -> None:
    assert cm.note_to_midi(note) == midi


def test_text_fields_protect_documented_status_columns() -> None:
    documented = {
        "harmonic_validation_status",
        "energy_conservation_status",
        "weight_function",
        "selected_dissonance_model",
        "f0_final_method",
    }
    assert documented.issubset(cm.TEXT_FIELDS)


def test_canonical_metric_columns_include_qc_and_f0_status_tokens() -> None:
    canonical = set(cm.CANONICAL_METRIC_COLUMNS)
    for col in ("qc_status", "acoustic_f0_status", "f0_epistemic_status"):
        assert col in canonical


# ---------------------------------------------------------------------------
# 6. Determinism / density-core probe
# ---------------------------------------------------------------------------

def test_stable_hash_is_deterministic_under_key_reordering() -> None:
    payload_a = {"b": 2, "a": 1, "status": "ok"}
    payload_b = {"a": 1, "status": "ok", "b": 2}
    assert cm._stable_hash(payload_a) == cm._stable_hash(payload_b)
    assert len(cm._stable_hash(payload_a)) == 64


@pytest.mark.parametrize(
    "df, expected",
    [
        (pd.DataFrame({"Note": ["C4"], "Harmonic Partials sum": [1.0]}), True),
        (pd.DataFrame({"Note": ["C4"], "__source_file_path": ["/x"]}), True),
        (pd.DataFrame({"Note": ["C4"], "effective_partial_density": [0.5]}), True),
        (pd.DataFrame({"Note": ["C4"], "density_metric_raw": [0.5]}), False),
        (pd.DataFrame(), False),
    ],
)
def test_compiled_df_has_density_core(df: pd.DataFrame, expected: bool) -> None:
    assert cm._compiled_df_has_density_core(df) is expected


def test_attach_sample_id_from_density_delegates_without_mutation() -> None:
    density = pd.DataFrame({"Note": ["C4"], "sample_id": ["c4__000000000001"]})
    satellite = pd.DataFrame({"Note": ["C4"], "metric": [1.0]})
    snapshot = satellite.copy()
    out = cm._attach_sample_id_from_density(satellite, density)
    assert out["sample_id"].tolist() == ["c4__000000000001"]
    pd.testing.assert_frame_equal(satellite, snapshot)


def test_corpus_comparability_audit_exposes_stable_metadata_keys() -> None:
    audit = cm._corpus_comparability_audit(pd.DataFrame())
    for key in (
        "corpus_comparability_status",
        "corpus_profile_count",
        "corpus_is_single_profile",
        "corpus_comparability_policy",
    ):
        assert key in audit
    assert audit["corpus_comparability_status"] == "empty_corpus"


def test_omit_from_compiled_metrics_export_excludes_legacy_norm_columns() -> None:
    omitted = cm._OMIT_FROM_COMPILED_METRICS_EXPORT
    for col in (
        "Spectral Density Metric",
        "Combined Density Metric",
        "Total Metric",
        "__source_file_path",
    ):
        assert col in omitted
    assert "density_metric_raw" not in omitted


def test_density_component_basis_valid_tokens() -> None:
    assert cm.DENSITY_COMPONENT_BASIS_DEFAULT == "amplitude_sum"
    assert set(cm.DENSITY_COMPONENT_BASIS_VALID) == {"amplitude_sum", "power_sum"}


def test_stable_hash_serializes_nested_payload_deterministically() -> None:
    payload = {"rows": [{"note": "C4", "status": "ok"}], "version": 2}
    again = json.loads(json.dumps(payload))
    assert cm._stable_hash(payload) == cm._stable_hash(again)
