"""CI gate: frozen ACD golden vectors from the §7.3 synthetic set."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tools.spectral_density_hill import (
    ACD_FORMULA_IDS,
    MODULE_REVISION,
    compute_density_compartment,
    erb_bandwidth_hz,
    hill_profile,
    merge_peaks_within_erb,
)

GOLDEN_PATH = Path(__file__).resolve().parent / "golden" / "acd_golden.json"


def _well_separated(k: int) -> tuple[np.ndarray, np.ndarray]:
    freqs = []
    f = 200.0
    for _ in range(k):
        freqs.append(f)
        f += 8.0 * float(erb_bandwidth_hz(np.asarray([f]))[0])
    return np.asarray(freqs, dtype=float), np.ones(k, dtype=float)


def test_golden_well_separated_match() -> None:
    payload = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert payload["revision"] == MODULE_REVISION
    assert payload["formula_ids"] == ACD_FORMULA_IDS
    for row in payload["well_separated"]:
        freqs, amps = _well_separated(int(row["k"]))
        comp = compute_density_compartment(amps, freqs)
        assert comp.status == row["status"]
        assert comp.d2 == pytest.approx(row["D2"], abs=1e-12)
        assert comp.d1 == pytest.approx(row["D1"], abs=1e-12)
        assert comp.d0 == pytest.approx(row["D0"], abs=1e-12)
        assert comp.count_merged == int(row["count_merged"])


def test_golden_saturation_match() -> None:
    payload = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    sat = payload["intra_erb_saturation"]
    f0 = 1000.0
    erb = float(erb_bandwidth_hz(np.asarray([f0]))[0])
    freqs = f0 + np.linspace(0.0, 0.4 * erb, int(sat["k"]))
    amps = np.ones(int(sat["k"]), dtype=float)
    mf, ma, _mc = merge_peaks_within_erb(freqs, amps)
    assert int(mf.size) == int(sat["merged_count"])
    assert hill_profile(ma)["D2"] == pytest.approx(sat["D2"], abs=1e-12)
