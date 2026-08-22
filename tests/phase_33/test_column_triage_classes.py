"""Four-branch class assignments for the 202 COL: metric residue."""
from __future__ import annotations

from collections import Counter

from metric_formula_versions import (
    TRIAGE_COL_METRIC_202,
    TRIAGE_DECISION_PENDING,
    classify_export_column,
    column_stamp,
)


def test_triage_residue_has_exactly_202_unique_names() -> None:
    assert len(TRIAGE_COL_METRIC_202) == 202
    assert len(set(TRIAGE_COL_METRIC_202)) == 202


def test_triage_branch_counts_sum_to_202() -> None:
    classes = Counter(
        classify_export_column(name, column_stamp(name)[0])
        for name in TRIAGE_COL_METRIC_202
    )
    assert sum(classes.values()) == 202
    assert classes["provenance"] == 16
    assert classes["deprecated"] == 21
    assert classes["diagnostic"] == 13 + 79
    assert classes["metric"] == 66 + 7


def test_decision_pending_still_metric_with_col_stamp() -> None:
    for name in TRIAGE_DECISION_PENDING:
        fid, _ver = column_stamp(name)
        assert classify_export_column(name, fid) == "metric"
        assert fid.startswith("COL:")


def test_remaining_metric_col_stamps_are_only_decision_pending() -> None:
    leftover = [
        name
        for name in TRIAGE_COL_METRIC_202
        if classify_export_column(name, column_stamp(name)[0]) == "metric"
        and column_stamp(name)[0].startswith("COL:")
    ]
    assert set(leftover) == set(TRIAGE_DECISION_PENDING)


def test_citable_residue_has_real_f_ids() -> None:
    for name in (
        "sethares_dissonance",
        "hutchinson_knopoff_dissonance",
        "vassilakis_dissonance",
        "selected_dissonance_value",
        "spectral_centroid_hz_on_attack",
        "erb_weighted_spectral_density_on_sustain",
        "roughness_parncutt_kernel_on_release",
        "spectral_entropy",
        "odd_even_harmonic_energy_ratio",
        "low_mid_energy_ratio",
        "inharmonicity_coefficient_B",
        "pure_observation_w_h",
        "harmonic_density_weight",
    ):
        fid, _ver = column_stamp(name)
        assert fid.startswith("F-"), name
        assert classify_export_column(name, fid) == "metric"
