"""Post-rating remediation — P1/P3 document consistency."""

from __future__ import annotations

from pathlib import Path


def test_p1_three_documents_cite_the_same_live_fail() -> None:
    diagnosis = Path("docs/validation/RESOLUTION_DEPENDENCE_DIAGNOSIS.md").read_text(
        encoding="utf-8"
    )
    backlog = Path("docs/POST_FREEZE_BACKLOG.md").read_text(encoding="utf-8")
    status = Path("docs/validation/UPGRADE_PROGRAMME_STATUS.md").read_text(
        encoding="utf-8"
    )
    for text in (diagnosis, backlog, status):
        assert "0.9222" in text
        assert "0.7878" in text
        assert "aa24de8" in text
    assert "P1 — Live G3 swap" in diagnosis
    assert "**FAIL**" in diagnosis
    assert "FAILED live" in status
    assert "3 % tolerance: **FAIL**" in backlog


def test_sethares_is_in_references() -> None:
    refs = Path("REFERENCES.md").read_text(encoding="utf-8")
    assert "Sethares, W. A. (2005)" in refs
    assert "dissonance_models.py" in refs
    index = Path("docs/METRIC_FORMULA_INDEX.md").read_text(encoding="utf-8")
    assert "Sethares (2005)" in index


def test_as2_diff_has_post_fix_residual() -> None:
    text = Path("docs/validation/TROMBONE_AS2_DEFECT_FIX_DIFF.md").read_text(
        encoding="utf-8"
    )
    assert "core_residual_energy_ratio" in text
    assert "0.0959" in text
    assert "historical — not regenerated" in text
