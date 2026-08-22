"""ACD_THEORY.md saturation / dynamic-range tables match the committed script."""
from __future__ import annotations

from pathlib import Path

from tests.phase_32.acd_d1_promotion_tables import (
    D2_ANALYTIC_LIMIT,
    dynamic_ranges,
    saturation_rows,
)

THEORY = Path(__file__).resolve().parents[2] / "docs" / "validation" / "ACD_THEORY.md"


def test_analytic_d2_limit_is_exactly_2_5() -> None:
    assert abs(D2_ANALYTIC_LIMIT - 2.5) < 1e-12


def test_theory_memo_reproduces_script_tables() -> None:
    text = THEORY.read_text(encoding="utf-8")
    assert "(π²/6)² / (π⁴/90)" in text or "(pi^2/6)^2 / (pi^4/90)" in text
    assert "2.500" in text
    for row in saturation_rows():
        assert f"{row['D1']:.3f}" in text
        assert f"{row['D2']:.3f}" in text
    dyn = dynamic_ranges()
    assert f"{dyn['D0']:.1f}" in text
    assert f"{dyn['D1']:.1f}" in text
    assert f"{dyn['D2']:.1f}" in text
