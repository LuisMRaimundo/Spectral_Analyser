from __future__ import annotations

"""
Eighth Phase 12 harmonic-spectrum / candidate DataFrame export contract layer
for proc_audio.py.

Complements test_proc_audio_helper_contract_additional.py (candidate row
building) with export-schema validation, sub-bass harmonic protection
DataFrames, non-harmonic residual pipeline separation, and audit-canonical
Amplitude_raw / Power_raw column contracts.

No production code changes. No real audio, GUI, plotting, or batch pipeline.
"""

import math

import numpy as np
import pandas as pd
import pytest

import proc_audio as PA
from proc_audio import ANALYSIS_SCHEMA_VERSION, AudioProcessor


AUDIT_CANONICAL_CANDIDATE_KEYS = frozenset(
    {
        "Harmonic Number",
        "expected_frequency_hz",
        "extracted_frequency_hz",
        "frequency_deviation_hz",
        "bin_center_frequency_hz",
        "interpolated_frequency_hz",
        "subbin_offset_bins",
        "subbin_interpolation_valid",
        "peak_bin_index",
        "Frequency (Hz)",
        "Amplitude_raw",
        "Power_raw",
        "snr_db",
        "prominence_db",
        "local_peak_valid",
        "candidate_status",
        "include_for_density",
        "Note",
    }
)


def _raw_spectrum_df(freqs: list[float], amps: list[float]) -> pd.DataFrame:
    amps_arr = np.asarray(amps, dtype=float)
    return pd.DataFrame(
        {
            "Frequency (Hz)": freqs,
            "Amplitude_raw": amps_arr,
            "Power_raw": amps_arr**2,
        }
    )


def _valid_meta_rows(**overrides: object) -> list[tuple[str, object]]:
    rows: list[tuple[str, object]] = [
        ("analysis_schema_version", ANALYSIS_SCHEMA_VERSION),
        ("component_profile_source", "current_analysis"),
        ("model_weights_source", "current_analysis"),
        ("export_alignment_source", "disabled_integrated_single_pass"),
        ("export_alignment_factor", 1.0),
    ]
    for key, val in overrides.items():
        rows = [(k, val if k == key else v) for k, v in rows]
        if key not in {k for k, _ in rows}:
            rows.append((key, val))
    return rows


# ---------------------------------------------------------------------------
# 1. Harmonic candidate row export column contract
# ---------------------------------------------------------------------------


def test_build_harmonic_candidate_row_always_carries_audit_canonical_keys() -> None:
    ap = AudioProcessor()
    ap.note = "C4"
    row = ap._build_harmonic_candidate_row(
        hnum=1,
        expected_freq_hz=261.63,
        tol_hz=5.0,
        complete_magnitudes=None,
        complete_freqs=None,
    )
    assert AUDIT_CANONICAL_CANDIDATE_KEYS.issubset(row.keys())


def test_build_harmonic_candidate_row_power_raw_is_amplitude_squared_when_detected() -> None:
    ap = AudioProcessor()
    ap.sr = 44100
    ap.n_fft = 4096
    ap.filtered_list_df = pd.DataFrame({"Frequency (Hz)": [440.0], "Amplitude": [0.5]})
    row = ap._build_harmonic_candidate_row(
        hnum=1,
        expected_freq_hz=440.0,
        tol_hz=20.0,
        complete_magnitudes=None,
        complete_freqs=None,
    )
    assert row["Amplitude_raw"] == pytest.approx(0.5)
    assert row["Power_raw"] == pytest.approx(0.25)


def test_build_harmonic_candidate_row_missing_window_preserves_nan_raw_columns() -> None:
    ap = AudioProcessor()
    row = ap._build_harmonic_candidate_row(
        hnum=3,
        expected_freq_hz=880.0,
        tol_hz=5.0,
        complete_magnitudes=None,
        complete_freqs=None,
    )
    assert row["candidate_status"] == "missing_window"
    assert row["include_for_density"] is False
    assert math.isnan(row["Amplitude_raw"])
    assert math.isnan(row["Power_raw"])


# ---------------------------------------------------------------------------
# 2. Per-note export schema validation
# ---------------------------------------------------------------------------


def test_validate_per_note_export_schema_accepts_valid_raw_spectrum_sheets() -> None:
    ap = AudioProcessor()
    ap.auto_model_weights_from_analysis = True
    ap.export_alignment_source = "disabled_integrated_single_pass"
    ap.export_alignment_factor = 1.0
    harm = _raw_spectrum_df([440.0], [1.0])
    ih = _raw_spectrum_df([1500.0], [0.2])
    sb = pd.DataFrame()
    ap._validate_per_note_export_schema(
        harm_df=harm,
        ih_df=ih,
        sb_df=sb,
        meta_rows=_valid_meta_rows(),
        note="A4",
    )


def test_validate_per_note_export_schema_rejects_missing_raw_columns_on_nonempty_harmonic() -> None:
    ap = AudioProcessor()
    ap.auto_model_weights_from_analysis = True
    ap.export_alignment_source = "disabled_integrated_single_pass"
    ap.export_alignment_factor = 1.0
    bad = pd.DataFrame({"Frequency (Hz)": [440.0], "Amplitude": [1.0]})
    with pytest.raises(RuntimeError, match="Amplitude_raw / Power_raw"):
        ap._validate_per_note_export_schema(
            harm_df=bad,
            ih_df=pd.DataFrame(),
            sb_df=pd.DataFrame(),
            meta_rows=_valid_meta_rows(),
            note="A4",
        )


def test_validate_per_note_export_schema_rejects_stale_analysis_schema_version() -> None:
    ap = AudioProcessor()
    ap.auto_model_weights_from_analysis = True
    ap.export_alignment_source = "disabled_integrated_single_pass"
    ap.export_alignment_factor = 1.0
    with pytest.raises(RuntimeError, match="analysis_schema_version"):
        ap._validate_per_note_export_schema(
            harm_df=_raw_spectrum_df([440.0], [1.0]),
            ih_df=pd.DataFrame(),
            sb_df=pd.DataFrame(),
            meta_rows=_valid_meta_rows(analysis_schema_version="legacy_v0"),
            note="A4",
        )


def test_validate_per_note_export_schema_rejects_batch_columns_on_inharmonic_sheet() -> None:
    ap = AudioProcessor()
    ap.auto_model_weights_from_analysis = True
    ap.export_alignment_source = "disabled_integrated_single_pass"
    ap.export_alignment_factor = 1.0
    ih = _raw_spectrum_df([1500.0], [0.2])
    ih["batch_alignment_factor"] = 0.8
    with pytest.raises(RuntimeError, match="batch_"):
        ap._validate_per_note_export_schema(
            harm_df=_raw_spectrum_df([440.0], [1.0]),
            ih_df=ih,
            sb_df=pd.DataFrame(),
            meta_rows=_valid_meta_rows(),
            note="A4",
        )


def test_validate_per_note_export_schema_raises_on_legacy_export_alignment_active() -> None:
    ap = AudioProcessor()
    ap.auto_model_weights_from_analysis = True
    ap.export_alignment_source = "batch_handoff"
    ap.export_alignment_factor = 0.5
    with pytest.raises(RuntimeError, match="legacy export alignment active"):
        ap._validate_per_note_export_schema(
            harm_df=_raw_spectrum_df([440.0], [1.0]),
            ih_df=pd.DataFrame(),
            sb_df=pd.DataFrame(),
            meta_rows=_valid_meta_rows(),
            note="A4",
        )


# ---------------------------------------------------------------------------
# 3. Sub-bass harmonic protection DataFrame
# ---------------------------------------------------------------------------


def test_build_subbass_harmonic_protection_merges_strict_and_included_candidates() -> None:
    ap = AudioProcessor()
    ap.harmonic_list_df = pd.DataFrame({"Frequency (Hz)": [110.0, 220.0]})
    ap.harmonic_spectrum_candidates_df = pd.DataFrame(
        {
            "Frequency (Hz)": [110.0, 330.0, 440.0],
            "include_for_density": [True, False, True],
        }
    )
    out = ap._build_subbass_harmonic_protection_df()
    freqs = sorted(out["Frequency (Hz)"].tolist())
    assert freqs == pytest.approx([110.0, 220.0, 440.0])


def test_build_subbass_harmonic_protection_excludes_non_included_candidate_frequencies() -> None:
    ap = AudioProcessor()
    ap.harmonic_spectrum_candidates_df = pd.DataFrame(
        {
            "Frequency (Hz)": [100.0, 200.0],
            "include_for_density": [True, False],
        }
    )
    out = ap._build_subbass_harmonic_protection_df()
    assert out["Frequency (Hz)"].tolist() == [pytest.approx(100.0)]


def test_build_subbass_harmonic_protection_empty_when_no_sources() -> None:
    ap = AudioProcessor()
    out = ap._build_subbass_harmonic_protection_df()
    assert list(out.columns) == ["Frequency (Hz)"]
    assert out.empty


# ---------------------------------------------------------------------------
# 4. Non-harmonic residual pipeline / debug counts
# ---------------------------------------------------------------------------


def test_nonharmonic_residual_pipeline_returns_empty_when_harmonic_list_missing() -> None:
    ap = AudioProcessor()
    ap.filtered_list_df = pd.DataFrame({"Frequency (Hz)": [1500.0], "Amplitude": [0.5]})
    ih_full, ih_sel = ap._nonharmonic_residual_pipeline_dataframes()
    assert ih_full.empty
    assert ih_sel.empty


def test_nonharmonic_residual_pipeline_keeps_inharmonic_peaks_separate_from_harmonic_list() -> None:
    ap = AudioProcessor()
    ap.freq_min = 20.0
    ap.subfundamental_guard_valid = False
    ap.harmonic_list_df = pd.DataFrame({"Frequency (Hz)": [440.0], "Amplitude": [1.0]})
    ap.filtered_list_df = pd.DataFrame(
        {"Frequency (Hz)": [440.0, 1500.0], "Amplitude": [1.0, 0.4]}
    )
    ih_full, ih_sel = ap._nonharmonic_residual_pipeline_dataframes()
    assert not ih_full.empty
    assert 1500.0 in ih_full["Frequency (Hz)"].tolist()
    assert 440.0 not in ih_full["Frequency (Hz)"].tolist()
    assert len(ih_sel) <= len(ih_full)


def test_assign_hierarchical_residual_debug_counts_sets_export_counters() -> None:
    ap = AudioProcessor()
    ih_full = pd.DataFrame({"Frequency (Hz)": [1500.0, 1600.0], "Amplitude": [0.3, 0.2]})
    ih_sel = pd.DataFrame({"Frequency (Hz)": [1500.0], "Amplitude": [0.3]})
    ap._assign_hierarchical_residual_debug_counts(ih_full, ih_sel)
    assert ap.residual_spectral_row_count == 2
    assert ap.nonharmonic_candidate_row_count == 2
    assert ap.retained_nonharmonic_peak_candidate_count == 1
    assert ap.exported_nonharmonic_peak_candidate_count == 1


# ---------------------------------------------------------------------------
# 5. Spectral sheet helper / determinism
# ---------------------------------------------------------------------------


def test_spectral_sheet_has_raw_columns_rejects_amplitude_only_nonempty_sheet() -> None:
    df = pd.DataFrame({"Frequency (Hz)": [440.0], "Amplitude": [1.0]})
    assert PA._spectral_sheet_has_raw_columns(df) is False
    assert PA._spectral_sheet_has_raw_columns(_raw_spectrum_df([440.0], [1.0])) is True


def test_harmonic_candidate_row_builder_is_deterministic_and_does_not_mutate_peak_df() -> None:
    ap = AudioProcessor()
    ap.sr = 44100
    ap.n_fft = 4096
    src = pd.DataFrame({"Frequency (Hz)": [440.0], "Amplitude": [0.6]})
    snap = src.copy()
    kwargs = dict(
        hnum=1,
        expected_freq_hz=440.0,
        tol_hz=20.0,
        complete_magnitudes=None,
        complete_freqs=None,
    )
    ap.filtered_list_df = src
    first = ap._build_harmonic_candidate_row(**kwargs)
    second = ap._build_harmonic_candidate_row(**kwargs)
    assert first.keys() == second.keys()
    for key in first:
        if isinstance(first[key], float) and math.isnan(first[key]):
            assert isinstance(second[key], float) and math.isnan(second[key])
        else:
            assert first[key] == second[key]
    pd.testing.assert_frame_equal(src, snap)


def test_rebuild_harmonic_candidate_rows_list_maps_to_dataframe_with_stable_columns() -> None:
    ap = AudioProcessor()
    ap.sr = 44100
    ap.n_fft = 4096
    ap.note = "A4"
    ap.filtered_list_df = pd.DataFrame({"Frequency (Hz)": [440.0], "Amplitude": [1.0]})
    rows = ap._rebuild_harmonic_candidate_rows(
        f0_hz=440.0,
        freq_max=2000.0,
        tolerance=30.0,
        use_adaptive_tolerance=False,
        bin_spacing=10.766,
        has_sub_bin_interpolation=False,
        complete_magnitudes=None,
        complete_freqs=None,
    )
    df = pd.DataFrame(rows)
    assert not df.empty
    assert AUDIT_CANONICAL_CANDIDATE_KEYS.issubset(set(df.columns))
    assert df["Note"].iloc[0] == "A4"
