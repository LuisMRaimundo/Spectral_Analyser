"""R1b — census-held attribution helpers and document claims."""

from __future__ import annotations

from pathlib import Path

from tools.r1b_census_held import _rel


def test_rel_delta() -> None:
    assert _rel(0.7878, 0.9222) == (abs(0.7878 - 0.9222) / 0.9222)
    assert _rel(0.9675, 0.9910) < 0.03


def test_r1b_section_records_held_numbers() -> None:
    text = Path("docs/validation/RESOLUTION_DEPENDENCE_DIAGNOSIS.md").read_text(
        encoding="utf-8"
    )
    assert "## R1b — Census-held G3" in text
    assert "0.9675" in text
    assert "0.9910" in text
    assert "70.65" in text
    assert "Partition residue" in text
    assert "**not** the B1 fail" in text
    assert "ci_basis_frame_count = 2.5625" in text
    assert "entire EWSD B1 fail" in text


def test_wp1_table_labelled_as_descriptor() -> None:
    text = Path("docs/validation/RESOLUTION_DEPENDENCE_DIAGNOSIS.md").read_text(
        encoding="utf-8"
    )
    assert "descriptor `harmonic_energy_ratio`" in text
    assert "Artefact (corrected R1b)" in text


def test_construct_validity_has_b1_and_b7() -> None:
    text = Path("docs/validation/EWSD_CONSTRUCT_VALIDITY.md").read_text(
        encoding="utf-8"
    )
    assert "## Declared analysis window" in text
    assert "91.31" in text
    assert "8.7668" in text
    assert "42.5820" in text


def test_version_rating_addendum_names_descriptor_artefact() -> None:
    text = Path("docs/validation/VERSION_RATING_V4_2_0.md").read_text(
        encoding="utf-8"
    )
    assert "Addendum — 20 August 2026 (R1b; scores not rewritten)" in text
    assert "descriptor" in text
    assert "0.9222 @8192 vs 0.7878" in text
