"""Synthetic recovery: well-separated K-tone D2 == K; intra-ERB packing saturates."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tools.spectral_density_hill import (
    compute_density_compartment,
    erb_bandwidth_hz,
    hill_profile,
    merge_peaks_within_erb,
)

GOLDEN_PATH = Path(__file__).resolve().parent / "golden" / "acd_golden.json"
K_VALUES = (1, 2, 4, 8, 16, 32)


def _well_separated_partials(k: int) -> tuple[np.ndarray, np.ndarray]:
    # Place tones many ERBs apart so merge cannot collapse them.
    freqs = []
    f = 200.0
    for _ in range(k):
        freqs.append(f)
        f += 8.0 * float(erb_bandwidth_hz(np.asarray([f]))[0])
    amps = np.ones(k, dtype=float)
    return np.asarray(freqs, dtype=float), amps


@pytest.mark.parametrize("k", K_VALUES)
def test_well_separated_equal_amplitudes_recover_k(k: int) -> None:
    freqs, amps = _well_separated_partials(k)
    comp = compute_density_compartment(amps, freqs, merge_within_erb=True)
    assert comp.status == "ok"
    assert comp.d2 == pytest.approx(float(k), rel=0.01)


def test_intra_erb_packing_saturates() -> None:
    f0 = 1000.0
    erb = float(erb_bandwidth_hz(np.asarray([f0]))[0])
    k = 16
    freqs = f0 + np.linspace(0.0, 0.4 * erb, k)
    amps = np.ones(k, dtype=float)
    merged_f, merged_a, counts = merge_peaks_within_erb(freqs, amps, erb_fraction=1.0)
    assert merged_f.size < k
    assert int(counts.sum()) == k
    d2 = hill_profile(merged_a)["D2"]
    assert d2 < 3.0
    # saturation point recorded for the golden / theory memo
    assert merged_f.size == 1
    assert d2 == pytest.approx(1.0, abs=1e-12)


def test_golden_file_exists_and_covers_k() -> None:
    payload = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert payload["revision"] == "ACD v1.0"
    assert [c["k"] for c in payload["well_separated"]] == list(K_VALUES)
