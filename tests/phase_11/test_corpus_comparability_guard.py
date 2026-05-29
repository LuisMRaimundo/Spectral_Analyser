"""Phase 1 — cross-profile comparability guard.

Density metrics are comparable across notes only within a single
primary-comparable analysis profile. The compile path must surface a corpus
verdict and refuse to mark mixed/exploratory corpora as comparable.
"""

from __future__ import annotations

import pandas as pd

from compile_metrics import (
    _corpus_comparability_audit,
    _restrict_primary_subset_to_single_profile,
)


def _df(profile_ids, primary_flags):
    return pd.DataFrame(
        {
            "Note": [f"N{i}" for i in range(len(profile_ids))],
            "analysis_parameter_profile_id": profile_ids,
            "is_primary_comparable_profile": primary_flags,
            "density_metric_raw": [1.0] * len(profile_ids),
        }
    )


def test_single_primary_profile_is_comparable() -> None:
    pid = "wf=log|dst=-60.0|ceil=20000.0"
    audit = _corpus_comparability_audit(_df([pid, pid, pid], [True, True, True]))
    assert audit["corpus_comparability_status"] == "ok_single_primary_profile"
    assert audit["corpus_is_single_profile"] is True
    assert audit["corpus_all_primary_comparable"] is True
    assert audit["corpus_profile_count"] == 1


def test_mixed_profiles_flagged_not_comparable() -> None:
    audit = _corpus_comparability_audit(
        _df(
            ["wf=log|dst=-60.0|ceil=20000.0", "wf=linear|dst=-90.0|ceil=20000.0", "wf=log|dst=-60.0|ceil=20000.0"],
            [True, False, True],
        )
    )
    assert audit["corpus_comparability_status"] == "mixed_profiles_not_directly_comparable"
    assert audit["corpus_profile_count"] == 2
    assert audit["corpus_is_single_profile"] is False
    assert audit["corpus_all_primary_comparable"] is False
    assert audit["corpus_primary_comparable_row_count"] == 2


def test_single_exploratory_profile_flagged() -> None:
    pid = "wf=linear|dst=-90.0|ceil=20000.0"
    audit = _corpus_comparability_audit(_df([pid, pid], [False, False]))
    assert audit["corpus_comparability_status"] == "single_non_primary_profile_exploratory"
    assert audit["corpus_is_single_profile"] is True
    assert audit["corpus_all_primary_comparable"] is False


def test_empty_corpus() -> None:
    audit = _corpus_comparability_audit(pd.DataFrame())
    assert audit["corpus_comparability_status"] == "empty_corpus"
    assert audit["corpus_row_count"] == 0


def test_primary_subset_restricted_to_single_profile() -> None:
    pid_a = "wf=log|dst=-60.0|ceil=20000.0"
    pid_b = "wf=log|dst=-45.0|ceil=20000.0"
    df = pd.DataFrame(
        {
            "Note": ["A", "B", "C", "D"],
            "analysis_parameter_profile_id": [pid_a, pid_a, pid_a, pid_b],
            "x": [1.0, 2.0, 3.0, 99.0],
        }
    )
    out, restricted, kept = _restrict_primary_subset_to_single_profile(df)
    assert restricted is True
    assert kept == pid_a  # dominant (3 rows vs 1)
    assert len(out) == 3
    assert set(out["analysis_parameter_profile_id"]) == {pid_a}


def test_primary_subset_single_profile_unchanged() -> None:
    pid = "wf=log|dst=-60.0|ceil=20000.0"
    df = pd.DataFrame(
        {"Note": ["A", "B"], "analysis_parameter_profile_id": [pid, pid], "x": [1.0, 2.0]}
    )
    out, restricted, kept = _restrict_primary_subset_to_single_profile(df)
    assert restricted is False
    assert kept == pid
    assert len(out) == 2
