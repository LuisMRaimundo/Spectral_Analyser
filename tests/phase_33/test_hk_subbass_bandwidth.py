"""Hutchinson–Knopoff low-frequency bandwidth option (default unchanged)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from dissonance_models import HutchinsonKnopoffDissonance
from mir_descriptors import critical_bandwidth_zwicker_hz

DOC_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "validation"
    / "HK_SUBBASS_BANDWIDTH.md"
)


def test_default_cbw_is_hk1978_power_law() -> None:
    for f in (20.0, 50.0, 110.0, 200.0, 500.0):
        expected = 1.72 * (f ** 0.65)
        assert HutchinsonKnopoffDissonance.cbw(f) == pytest.approx(expected)
        model = HutchinsonKnopoffDissonance()
        assert model.low_frequency_basis == "hk1978"
        assert model.cbw(f, low_frequency_basis=model.low_frequency_basis) == (
            pytest.approx(expected)
        )


def test_hybrid_uses_zwicker_below_200_and_hk_at_or_above() -> None:
    zw_50 = float(critical_bandwidth_zwicker_hz(np.asarray([50.0]))[0])
    assert HutchinsonKnopoffDissonance.cbw(
        50.0, low_frequency_basis="zwicker_below_200hz"
    ) == pytest.approx(zw_50)
    hk_200 = 1.72 * (200.0 ** 0.65)
    assert HutchinsonKnopoffDissonance.cbw(
        200.0, low_frequency_basis="zwicker_below_200hz"
    ) == pytest.approx(hk_200)
    hk_400 = 1.72 * (400.0 ** 0.65)
    assert HutchinsonKnopoffDissonance.cbw(
        400.0, low_frequency_basis="zwicker_below_200hz"
    ) == pytest.approx(hk_400)


def test_default_total_dissonance_unchanged_by_optional_argument() -> None:
    partials = [(40.0, 1.0), (55.0, 0.7), (70.0, 0.4), (400.0, 0.2)]
    a = HutchinsonKnopoffDissonance().total_dissonance(partials, [])
    b = HutchinsonKnopoffDissonance(
        low_frequency_basis="hk1978"
    ).total_dissonance(partials, [])
    assert a == pytest.approx(b, rel=0.0, abs=0.0)
    hybrid = HutchinsonKnopoffDissonance(
        low_frequency_basis="zwicker_below_200hz"
    ).total_dissonance(partials, [])
    assert hybrid != pytest.approx(a, rel=0.0, abs=1e-15)


def test_hk_subbass_doc_exists_and_leaves_default_open() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "1.72" in text
    assert "zwicker_below_200hz" in text
    assert "Default arithmetic is unchanged" in text.replace("\n", " ")
    assert "f0 < 200 Hz" in text
    assert "C2" in text
    assert "author decision" in text.lower()
