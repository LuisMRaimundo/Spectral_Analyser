"""Zwicker-CB roughness kernel (F-037 bandwidth basis)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from mir_descriptors import (
    _roughness_aures_1985,
    critical_bandwidth_zwicker_hz,
    roughness_parncutt_kernel,
)

GOLDEN_PATH = Path(__file__).resolve().parent / "golden" / "roughness_zwicker.json"
DOC_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "validation"
    / "ROUGHNESS_BANDWIDTH_BASIS.md"
)
ZWICKER_CHECK_HZ = (100.0, 500.0, 1000.0, 2000.0, 5000.0)
# Zwicker & Fastl (2007) CB(f) = 25 + 75*(1 + 1.4*(f/1000)^2)^0.69
ZWICKER_PUBLISHED_HZ = {
    100.0: 100.72,
    500.0: 117.26,
    1000.0: 162.22,
    2000.0: 300.77,
    5000.0: 914.02,
}


def _two_tone_peak_df(f0: float, basis: str) -> float:
    dfs = np.linspace(0.5, max(400.0, 2.0 * f0), 400)
    vals = np.array(
        [
            roughness_parncutt_kernel(
                np.asarray([f0, f0 + df], dtype=float),
                np.asarray([1.0, 1.0], dtype=float),
                bandwidth_basis=basis,
            )
            for df in dfs
        ]
    )
    return float(dfs[int(np.argmax(vals))])


def test_zwicker_cb_matches_formula_at_published_frequencies() -> None:
    payload = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    for f, expected in zip(ZWICKER_CHECK_HZ, payload["zwicker_cb_hz"]):
        got = float(critical_bandwidth_zwicker_hz(np.asarray([f]))[0])
        assert got == pytest.approx(expected, rel=0.01)
        assert got == pytest.approx(ZWICKER_PUBLISHED_HZ[f], rel=0.01)


def test_validation_doc_signs_off_on_provenance_not_circular_table() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "unit mismatch with the source" in text
    assert "provenance-consistent" in text
    assert "identity check (grid resolution)" in text
    assert "PL ref (0.25·Zwicker CB)" not in text
    assert "non-blocking" in text
    assert "Fig. 10" in text


def test_zwicker_kernel_peak_locations() -> None:
    z_1k = _two_tone_peak_df(1000.0, "zwicker_cb")
    z_147 = _two_tone_peak_df(146.83, "zwicker_cb")
    assert 25.0 <= z_1k <= 45.0
    assert 20.0 <= z_147 <= 30.0
    erb_147 = _two_tone_peak_df(146.83, "erb")
    assert not (20.0 <= erb_147 <= 30.0)


def test_amplitude_scale_invariance_c_squared() -> None:
    rng = np.random.default_rng(3)
    f = np.sort(rng.uniform(80.0, 2000.0, 12))
    a = rng.uniform(0.1, 1.5, 12)
    base = roughness_parncutt_kernel(f, a)
    for c in (1e-3, 0.5, 7.0, 1e2):
        got = roughness_parncutt_kernel(f, c * a)
        assert got == pytest.approx(c * c * base, rel=0.0, abs=1e-10)


def test_zwicker_goldens_frozen() -> None:
    payload = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert payload["bandwidth_basis"] == "zwicker_cb"
    freqs, amps = 146.83 * np.arange(1, 21, dtype=float), 1.0 / np.arange(1, 21, dtype=float)
    got = roughness_parncutt_kernel(freqs, amps, bandwidth_basis="zwicker_cb")
    assert got == pytest.approx(payload["harmonic_20_partial_d3"], rel=0.0, abs=1e-12)
    for row in payload["two_tone_peaks_hz"]:
        got_df = _two_tone_peak_df(float(row["f0"]), "zwicker_cb")
        assert got_df == pytest.approx(row["df_peak"], abs=1.0)


def test_retired_aures_alias_raises() -> None:
    with pytest.raises(NotImplementedError, match="mis-specified bandwidth"):
        _roughness_aures_1985(np.array([440.0, 445.0]), np.array([1.0, 1.0]))
