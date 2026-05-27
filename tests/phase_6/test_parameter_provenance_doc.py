from __future__ import annotations

from pathlib import Path


def test_parameter_provenance_doc_exists_and_has_required_fields() -> None:
    path = Path("docs/parameter_provenance.md")
    assert path.exists()
    txt = path.read_text(encoding="utf-8")
    assert "canonical_name" in txt
    assert "current_value" in txt
    assert "acoustic_meaning" in txt
    assert "source_or_status" in txt
    assert "qualitative_stability_range" in txt
    assert "stability_test_file" in txt
