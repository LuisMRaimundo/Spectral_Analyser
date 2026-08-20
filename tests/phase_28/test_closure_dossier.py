"""WP6 — closure dossier and freeze declaration."""

from __future__ import annotations

from pathlib import Path


def test_construct_validation_table_is_the_phase_i_record() -> None:
    text = Path("docs/validation/CONSTRUCT_VALIDATION_SYNTHETIC.md").read_text(
        encoding="utf-8"
    )
    for token in (
        "harmonic_snr10_white",
        "stiff_snr40_white",
        "bell_snr20_white",
        "N ±1",
        "Phase I / WP6 freeze evidence",
    ):
        assert token in text


def test_upgrade_status_supersedes_one_to_hundred_ratings() -> None:
    status = Path("docs/validation/UPGRADE_PROGRAMME_STATUS.md").read_text(
        encoding="utf-8"
    )
    for phase in (
        "| A |",
        "| I |",
        "| D1 |",
        "| D6.6 |",
        "| WP1 |",
        "| WP5 |",
        "| WP6 |",
    ):
        assert phase in status
    assert "supersedes" in status.lower()
    assert "VERSION_RATING_IOWA_TUBA.md" in status
    assert "SEGMENTATION_CASE_STUDY_G2.md" in status
    assert "POST_FREEZE_BACKLOG.md" in status


def test_version_rating_is_deprecated() -> None:
    rating = Path("docs/validation/VERSION_RATING_IOWA_TUBA.md").read_text(
        encoding="utf-8"
    )
    assert "DEPRECATED" in rating
    assert "UPGRADE_PROGRAMME_STATUS.md" in rating
    assert "1–100" in rating or "1-100" in rating


def test_g2_case_study_records_full_versus_stable() -> None:
    study = Path("docs/validation/SEGMENTATION_CASE_STUDY_G2.md").read_text(
        encoding="utf-8"
    )
    assert "43" in study
    assert "16" in study
    assert "551" in study
    assert "140" in study
    assert "50.2" in study
    assert "12.3" in study
    assert "1.75" in study
    assert "sustain_primary_stable_diagnostic" in study


def test_post_freeze_backlog_records_g3_core_h() -> None:
    backlog = Path("docs/POST_FREEZE_BACKLOG.md").read_text(encoding="utf-8")
    assert "core_H" in backlog
    assert "n_fft" in backlog
    assert "G3" in backlog
    assert "perceptual" in backlog.lower() or "listener" in backlog.lower()


def test_readme_declares_freeze() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "Frozen at v4.2.0" in readme
    assert "POST_FREEZE_BACKLOG.md" in readme
    assert "SEGMENTATION_CASE_STUDY_G2.md" in readme
    assert "UPGRADE_PROGRAMME_STATUS.md" in readme
    changes = Path("CHANGES.md").read_text(encoding="utf-8")
    assert "WP6 — Closure dossier" in changes
