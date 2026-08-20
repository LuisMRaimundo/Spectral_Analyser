"""R6 — re-export dossier exists; original scores not rewritten."""

from pathlib import Path


def test_r6_diff_summary_and_addendum() -> None:
    summary = Path("docs/validation/REEXPORT_DIFF_SUMMARY.md").read_text(
        encoding="utf-8"
    )
    assert "1db94e1" in summary
    assert "v4.2.3" in summary
    assert "0.00756" in summary or "0.0076" in summary
    assert "−0.046" in summary or "-0.046" in summary
    report = Path("docs/validation/MEASUREMENT_PERFORMANCE_REPORT.md").read_text(
        encoding="utf-8"
    )
    assert "## Addendum — 20 August 2026 (R6; scores not rewritten)" in report
    assert "**76.6**" in report
    assert "62.7" in report
    status = Path("docs/validation/UPGRADE_PROGRAMME_STATUS.md").read_text(
        encoding="utf-8"
    )
    assert "R2–R6" in status
    assert "R6" in status
