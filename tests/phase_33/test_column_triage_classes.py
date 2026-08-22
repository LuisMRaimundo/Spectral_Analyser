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
