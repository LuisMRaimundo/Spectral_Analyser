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


def test_pretag_archive_and_findings_exist() -> None:
    readme = Path("docs/validation/pretag_evidence/README.md").read_text(
        encoding="utf-8"
    )
    assert "non-citable" in readme
    assert "6b0e51a" in readme
    for name in (
        "trombone_pp_compiled_density_metrics_research.xlsx",
        "trombone_mf_compiled_density_metrics_research.xlsx",
        "trombone_ff_compiled_density_metrics_research.xlsx",
        "flute_pp_compiled_density_metrics_research.xlsx",
        "flute_mf_compiled_density_metrics_research.xlsx",
        "flute_ff_compiled_density_metrics_research.xlsx",
        "cordas/EWSD_acoustic_balanced_CORDAS_report.md",
        "cordas/ewsd_balanced_analysis.json",
        "cordas/ewsd_balanced_note_rows.csv",
    ):
        assert (Path("docs/validation/pretag_evidence") / name).is_file()
    findings = Path("docs/validation/PRETAG_FINDINGS_SUMMARY.md").read_text(
        encoding="utf-8"
    )
    assert "32 / 32" in findings
    assert "36 / 37" in findings
    assert "22 / 38" in findings
    assert "pre-tag; to be reproduced under the freeze tag" in findings
    assert "0.0076" in findings
    assert "−0.046" in findings or "-0.046" in findings


def test_as2_diff_has_post_fix_residual() -> None:
    text = Path("docs/validation/TROMBONE_AS2_DEFECT_FIX_DIFF.md").read_text(
        encoding="utf-8"
    )
    assert "core_residual_energy_ratio" in text
    assert "0.0959" in text
    assert "historical — not regenerated" in text
