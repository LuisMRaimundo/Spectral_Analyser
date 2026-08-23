"""Structural ACD contracts: energy conservation, ratios, fail-closed, EWSD identity."""
from __future__ import annotations

import math

import numpy as np
import pytest

from tools.ewsd_pure import (
    CompartmentInputs,
    compute_compartment_metrics,
    original_elementwise_weight,
    original_sum_metric,
)
from tools.spectral_density_hill import (
    ENERGY_EPS,
    compute_density_compartment,
    compute_density_from_excitation_pattern,
    compute_note_density,
    merge_peaks_fixed_erb_grid,
    merge_peaks_roex_overlap,
    merge_peaks_within_erb,
)


def test_merge_conserves_energy() -> None:
    rng = np.random.default_rng(0)
    f = np.sort(rng.uniform(80.0, 4000.0, 40))
    a = rng.uniform(0.01, 2.0, 40)
    _mf, ma, _mn = merge_peaks_within_erb(f, a, erb_fraction=1.0)
    assert abs(float(np.sum(np.square(ma))) - float(np.sum(np.square(a)))) <= 1e-12
    _ff, fa, _fn = merge_peaks_fixed_erb_grid(f, a, erb_fraction=1.0)
    assert abs(float(np.sum(np.square(fa))) - float(np.sum(np.square(a)))) <= 1e-12


def test_ratios_sum_to_one_when_energy_present() -> None:
    h = compute_density_compartment(
        np.asarray([1.0, 0.7, 0.5]),
        np.asarray([146.8, 293.7, 440.5]),
    )
    i = compute_density_compartment(
        np.asarray([0.2]),
        np.asarray([220.0]),
    )
    s = compute_density_compartment(
        np.asarray([0.05]),
        np.asarray([55.0]),
    )
    note = compute_note_density({"harmonic": h, "inharmonic": i, "subbass": s})
    rsum = note["r_harmonic"] + note["r_inharmonic"] + note["r_subbass"]
    assert rsum == pytest.approx(1.0, abs=1e-15)
    assert note["ACD_status"].startswith("ok")
    assert note["energy_total"] == pytest.approx(
        note["ACD_score"] * note["ACD_magnitude_per_component"], abs=1e-12
    )
    assert note["ACD_score"] == pytest.approx(note["ACD_D1"], abs=1e-12)


def test_empty_compartment_nan_not_silent_zero() -> None:
    empty = compute_density_compartment(np.asarray([]), np.asarray([]))
    assert empty.status == "empty"
    assert math.isnan(empty.d2)
    filled = compute_density_compartment(
        np.asarray([1.0, 1.0]),
        np.asarray([200.0, 800.0]),
    )
    note = compute_note_density({"harmonic": filled, "inharmonic": empty, "subbass": empty})
    assert note["r_inharmonic"] == 0.0
    assert note["r_subbass"] == 0.0
    assert math.isnan(note["D2_inharmonic"])
    assert note["ACD_score"] == pytest.approx(filled.d1)
    assert note["ACD_score_D2_dominance"] == pytest.approx(filled.d2)
    assert note["ACD_D0_minus_D1"] == pytest.approx(filled.d0 - filled.d1)
    assert not math.isnan(note["ACD_score"])
    assert note["energy_total"] == pytest.approx(
        note["ACD_score"] * note["ACD_magnitude_per_component"], abs=1e-12
    )


def test_all_empty_note_is_nan() -> None:
    empty = compute_density_compartment(np.asarray([]), None, merge_within_erb=False)
    note = compute_note_density({"harmonic": empty})
    assert math.isnan(note["ACD_score"])
    assert note["ACD_status"] == "empty"


def test_ewsd_identity_r_mean_phi_neff() -> None:
    values = np.asarray([1.2, 0.8, 0.5, 0.3], dtype=float)
    ratio = 0.7
    comp = compute_compartment_metrics(
        CompartmentInputs(values=values, analysis_ratio=ratio, weight_function="log")
    )
    phi = original_elementwise_weight(values, "log")
    phi = phi[np.isfinite(phi) & (phi > 0.0)]
    mean_phi = float(np.mean(phi))
    d_k = original_sum_metric(values, "log")
    left = float(comp.ewsd_score)
    right = float(ratio * mean_phi * comp.effective_component_count)
    assert left == pytest.approx(d_k * ratio * comp.concentration_penalty, abs=1e-12)
    assert left == pytest.approx(right, abs=1e-12)


def test_excitation_pattern_scaffold_raises() -> None:
    with pytest.raises(NotImplementedError):
        compute_density_from_excitation_pattern()
    with pytest.raises(NotImplementedError):
        merge_peaks_roex_overlap()


def test_per_compartment_d1_matches_density_compartment() -> None:
    h = compute_density_compartment(
        np.asarray([1.0, 0.7, 0.5]),
        np.asarray([146.8, 293.7, 440.5]),
    )
    i = compute_density_compartment(np.asarray([0.2]), np.asarray([220.0]))
    s = compute_density_compartment(np.asarray([0.05]), np.asarray([55.0]))
    note = compute_note_density({"harmonic": h, "inharmonic": i, "subbass": s})
    assert note["D1_harmonic"] == pytest.approx(h.d1, abs=1e-12)
    assert note["D1_inharmonic"] == pytest.approx(i.d1, abs=1e-12)
    assert note["D1_subbass"] == pytest.approx(s.d1, abs=1e-12)
    assert note["D0_harmonic"] == pytest.approx(h.d0, abs=1e-12)
    assert note["ACD_score"] == pytest.approx(note["ACD_D1"], abs=1e-12)


def test_missing_frequency_fail_closed() -> None:
    c = compute_density_compartment(np.asarray([1.0, 0.5]), None, merge_within_erb=True)
    assert c.status == "missing_frequency"
    assert math.isnan(c.d2)
    assert c.d2 != 0.0
