"""WP3 — production policy as code (FFT defaults, segment pair, eligibility)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from constants import (
    ELIGIBILITY_POLICY_VERSION,
    FFT_POLICY_DEFAULT,
    FIXED_HOP_LENGTH_DEFAULT,
    FIXED_N_FFT_DEFAULT,
    MIN_INDEPENDENT_FRAMES,
    SEGMENT_POLICY_DEFAULT,
    STABLE_CENTROID_MAX_RATIO,
    STABLE_REPRESENTATIVENESS_MAX_RATIO,
)
from metric_contract import get_metric_definition
from production_policy import (
    apply_degenerate_ci_nan,
    build_analysis_parameter_profile_id,
    classify_segment_role,
    default_parameter_profile_id,
    evaluate_eligibility,
    evaluate_segment_diagnostics,
    find_segment_sibling,
    is_primary_comparable_profile,
    missing_metric_nan,
    mixed_profile_ids,
)
from run_manifest import default_parameter_profile_id as manifest_profile_id
from tools.ewsd_core import add_quality_columns
from tools.ewsd_stage3_contract import build_stage3_diagnostics
from tools.ewsd_uncertainty import (
    compartment_bootstrap_data_from_arrays,
    bootstrap_ewsd_from_compartments,
)


# Case-study numbers from the G2 segmentation pair (full vs stable).
CELLO_G2_FULL_EWSD = 50.2
CELLO_G2_STABLE_EWSD = 12.3
CELLO_G2_FULL_CENTROID_HZ = 551.0
CELLO_G2_STABLE_CENTROID_HZ = 140.0
CELLO_G2_STABLE_FRAMES = 1.75
CELLO_G2_STABLE_HARMONICS = 16
CELLO_G2_FULL_HARMONICS = 43

TROMBONE_AS2_EWSD = 87.41
TROMBONE_AS2_FRAMES = 12.0
TROMBONE_AS2_HARMONICS = 92


def test_fft_defaults_are_fixed_8192_1024() -> None:
    assert FFT_POLICY_DEFAULT == "fixed"
    assert FIXED_N_FFT_DEFAULT == 8192
    assert FIXED_HOP_LENGTH_DEFAULT == 1024
    assert MIN_INDEPENDENT_FRAMES == 8
    assert STABLE_REPRESENTATIVENESS_MAX_RATIO == pytest.approx(1.3)
    assert STABLE_CENTROID_MAX_RATIO == pytest.approx(2.0)
    assert SEGMENT_POLICY_DEFAULT == "sustain_primary_stable_diagnostic"
    assert ELIGIBILITY_POLICY_VERSION == "1"


def test_adaptive_tier_is_not_primary_comparable() -> None:
    assert is_primary_comparable_profile("log", "fixed") is True
    assert is_primary_comparable_profile("log", "adaptive_tier") is False
    assert is_primary_comparable_profile("linear", "fixed") is False


def test_profile_id_carries_fft_seg_elig() -> None:
    pid = build_analysis_parameter_profile_id("log", -40.0, 5000.0, "fixed")
    assert pid == (
        "wf=log|dst=-40.0|ceil=5000.0|fft=fixed|"
        "seg=sustain_primary_stable_diagnostic|elig=1"
    )
    assert manifest_profile_id("log") == default_parameter_profile_id("log")
    assert "|fft=fixed|" in default_parameter_profile_id("log")
    assert "|seg=sustain_primary_stable_diagnostic|" in default_parameter_profile_id("log")
    assert default_parameter_profile_id("log").endswith("|elig=1")


def test_cello_g2_stable_is_ineligible_and_unrepresentative() -> None:
    gate = evaluate_eligibility(CELLO_G2_STABLE_FRAMES, CELLO_G2_STABLE_HARMONICS)
    assert gate["ewsd_primary_analysis_eligible"] is False
    assert gate["frames_below_min_independent"] is True
    assert gate["degenerate_partial_set"] is False

    diag = evaluate_segment_diagnostics(
        primary_ewsd=CELLO_G2_STABLE_EWSD,
        primary_centroid_hz=CELLO_G2_STABLE_CENTROID_HZ,
        primary_frames_independent=CELLO_G2_STABLE_FRAMES,
        sibling_ewsd=CELLO_G2_FULL_EWSD,
        sibling_centroid_hz=CELLO_G2_FULL_CENTROID_HZ,
        sibling_frames_independent=20.0,
        primary_role="stable",
        sibling_found=True,
    )
    assert diag["segment_policy"] == SEGMENT_POLICY_DEFAULT
    assert diag["stable_segment_ewsd"] == pytest.approx(CELLO_G2_STABLE_EWSD)
    assert diag["full_stable_ewsd_ratio"] == pytest.approx(
        CELLO_G2_FULL_EWSD / CELLO_G2_STABLE_EWSD
    )
    assert diag["full_stable_ewsd_ratio"] == pytest.approx(4.0813, abs=1e-3)
    assert diag["stable_segment_unrepresentative"] is True


def test_trombone_as2_is_eligible_and_representative() -> None:
    gate = evaluate_eligibility(TROMBONE_AS2_FRAMES, TROMBONE_AS2_HARMONICS)
    assert gate["ewsd_primary_analysis_eligible"] is True
    assert gate["degenerate_partial_set"] is False

    diag = evaluate_segment_diagnostics(
        primary_ewsd=TROMBONE_AS2_EWSD,
        primary_centroid_hz=400.0,
        primary_frames_independent=TROMBONE_AS2_FRAMES,
        sibling_ewsd=TROMBONE_AS2_EWSD,
        sibling_centroid_hz=401.0,
        sibling_frames_independent=TROMBONE_AS2_FRAMES,
        primary_role="stable",
        sibling_found=True,
    )
    assert diag["full_stable_ewsd_ratio"] == pytest.approx(1.0)
    assert diag["stable_segment_unrepresentative"] is False
    assert diag["stable_segment_frames_independent"] == pytest.approx(TROMBONE_AS2_FRAMES)


def test_missing_sibling_diagnostics_are_nan_not_zero() -> None:
    diag = evaluate_segment_diagnostics(sibling_found=False)
    assert diag["segment_policy"] == SEGMENT_POLICY_DEFAULT
    assert np.isnan(diag["stable_segment_ewsd"])
    assert np.isnan(diag["full_stable_ewsd_ratio"])
    assert np.isnan(diag["stable_segment_frames_independent"])
    assert diag["stable_segment_unrepresentative"] is False
    assert missing_metric_nan() != 0.0


def test_degenerate_ci_is_nan_never_zero() -> None:
    gate = evaluate_eligibility(20.0, 2)
    assert gate["ewsd_primary_analysis_eligible"] is False
    assert gate["degenerate_partial_set"] is True
    patched = apply_degenerate_ci_nan(
        {"EWSD_score_acoustic_balanced_rel_uncertainty": 0.0, "score": 12.0},
        degenerate=True,
    )
    assert np.isnan(patched["EWSD_score_acoustic_balanced_rel_uncertainty"])
    assert patched["score"] == pytest.approx(12.0)

    boot = bootstrap_ewsd_from_compartments(
        [
            compartment_bootstrap_data_from_arrays([1.0, 0.5], 1.0),
        ]
    )
    assert np.isnan(boot["ewsd_score_total_rel_uncertainty"])
    assert np.isnan(boot["ewsd_score_acoustic_balanced_rel_uncertainty"])


def test_add_quality_columns_applies_wp3_gates() -> None:
    frame = pd.DataFrame(
        {
            "Note": ["G2", "A#2"],
            "mode": ["individual_exact", "individual_exact"],
            "warning": ["", ""],
            "Note_sort_warning": ["", ""],
            "weight_function_canonical": ["log", "log"],
            "analysis_ratio_weight_harmonic": [0.8, 0.8],
            "analysis_ratio_weight_nonharmonic_residual": [0.15, 0.15],
            "analysis_ratio_weight_noise_subbass": [0.05, 0.05],
            "ewsd_score": [12.3, 87.41],
            "component_count_salient": [16, 92],
            "harmonic_validated_count": [16, 92],
            "sustain_frame_count_independent": [1.75, 12.0],
            "EWSD_score_acoustic_balanced_rel_uncertainty": [0.0, 0.12],
        }
    )
    out = add_quality_columns(frame)
    g2 = out.loc[out["Note"] == "G2"].iloc[0]
    as2 = out.loc[out["Note"] == "A#2"].iloc[0]
    assert bool(g2["ewsd_primary_analysis_eligible"]) is False
    assert bool(as2["ewsd_primary_analysis_eligible"]) is True
    flute = pd.DataFrame(
        {
            "Note": ["B6"],
            "mode": ["individual_exact"],
            "warning": [""],
            "Note_sort_warning": [""],
            "weight_function_canonical": ["log"],
            "analysis_ratio_weight_harmonic": [1.0],
            "analysis_ratio_weight_nonharmonic_residual": [0.0],
            "analysis_ratio_weight_noise_subbass": [0.0],
            "ewsd_score": [2.0],
            "component_count_salient": [2],
            "harmonic_validated_count": [2],
            "sustain_frame_count_independent": [20.0],
            "EWSD_score_acoustic_balanced_rel_uncertainty": [0.0],
        }
    )
    flute_out = add_quality_columns(flute).iloc[0]
    assert bool(flute_out["degenerate_partial_set"]) is True
    assert bool(flute_out["ewsd_primary_analysis_eligible"]) is False
    assert np.isnan(float(flute_out["EWSD_score_acoustic_balanced_rel_uncertainty"]))


def test_mixed_profile_ids_emit_stage3_issue() -> None:
    pid_a = default_parameter_profile_id("log")
    pid_b = build_analysis_parameter_profile_id("log", -40.0, 5000.0, "adaptive_tier")
    assert len(mixed_profile_ids([pid_a, pid_b])) == 2
    sd = pd.DataFrame(
        {
            "Note": ["A2", "B2"],
            "ewsd_merge_status": ["merged_individual_exact", "merged_individual_exact"],
            "ewsd_primary_analysis_eligible": [True, True],
            "analysis_parameter_profile_id": [pid_a, pid_b],
        }
    )
    summary, _meta = build_stage3_diagnostics(
        sd, analysis_root="/tmp", frequency_ceiling_hz=20000.0, n_workbooks=2
    )
    assert any(
        "mixed analysis_parameter_profile_id" in str(v)
        for v in summary["stage3_issue"].tolist()
    )


def test_sibling_path_and_adsr_sidecar(tmp_path: Path) -> None:
    full_dir = tmp_path / "_Sustains"
    stable_dir = tmp_path / "_Sustains_Stable"
    full_dir.mkdir()
    stable_dir.mkdir()
    full = full_dir / "IOWA_Vlc.sG_arco_ff.G2_Sustains.aif"
    stable = stable_dir / "IOWA_Vlc.sG_arco_ff.G2_SustainStable.aif"
    full.write_bytes(b"x")
    stable.write_bytes(b"x")
    assert classify_segment_role(stable) == "stable"
    assert classify_segment_role(full) == "full_sustain"
    assert find_segment_sibling(full) == stable
    assert find_segment_sibling(stable) == full

    take = tmp_path / "solo_note.wav"
    take.write_bytes(b"x")
    sidecar = tmp_path / "solo_note.json"
    named = tmp_path / "solo_note_SustainStable.wav"
    named.write_bytes(b"x")
    sidecar.write_text('{"stable_path": "solo_note_SustainStable.wav"}', encoding="utf-8")
    assert find_segment_sibling(take) == named


def test_export_row_includes_wp3_columns() -> None:
    from proc_audio import AudioProcessor

    ap = AudioProcessor()
    ap.weight_function = "log"
    ap.density_salience_threshold_db = -40.0
    ap.density_frequency_ceiling_hz = 5000.0
    ap.fft_policy = "fixed"
    ap.sustain_frame_count_independent = CELLO_G2_STABLE_FRAMES
    ap.harmonic_validated_count = CELLO_G2_STABLE_HARMONICS
    ap.energy_weighted_component_density_diagnostic = CELLO_G2_STABLE_EWSD
    ap.spectral_centroid_hz = CELLO_G2_STABLE_CENTROID_HZ
    ap.source_file_name = "IOWA_Vlc.sG_arco_ff.G2_SustainStable.aif"
    ap.stable_sibling_metrics = {
        "ewsd": CELLO_G2_FULL_EWSD,
        "centroid_hz": CELLO_G2_FULL_CENTROID_HZ,
        "frames_independent": 20.0,
    }
    row = ap._build_main_metrics_export_row(
        "G2", h_psum=1.0, i_psum=0.0, s_psum=0.0, t_psum=1.0
    )
    assert row["segment_policy"] == SEGMENT_POLICY_DEFAULT
    assert row["ewsd_primary_analysis_eligible"] is False
    assert row["stable_segment_unrepresentative"] is True
    assert row["full_stable_ewsd_ratio"] == pytest.approx(
        CELLO_G2_FULL_EWSD / CELLO_G2_STABLE_EWSD
    )
    assert "|fft=fixed|" in str(row["analysis_parameter_profile_id"])
    assert "|seg=" in str(row["analysis_parameter_profile_id"])
    assert str(row["analysis_parameter_profile_id"]).endswith("|elig=1")
    assert row["is_primary_comparable_profile"] is True

    ap2 = AudioProcessor()
    ap2.weight_function = "log"
    ap2.fft_policy = "adaptive_tier"
    ap2.density_salience_threshold_db = -40.0
    ap2.density_frequency_ceiling_hz = 5000.0
    row2 = ap2._build_main_metrics_export_row(
        "A2", h_psum=1.0, i_psum=0.0, s_psum=0.0, t_psum=1.0
    )
    assert row2["is_primary_comparable_profile"] is False
    assert "|fft=adaptive_tier|" in str(row2["analysis_parameter_profile_id"])


def test_new_columns_are_in_metric_contract() -> None:
    for name in (
        "segment_policy",
        "stable_segment_ewsd",
        "full_stable_ewsd_ratio",
        "stable_segment_frames_independent",
        "stable_segment_unrepresentative",
        "ewsd_primary_analysis_eligible",
        "degenerate_partial_set",
    ):
        assert get_metric_definition(name) is not None
