"""Hurley & Rickard (2009) axiomatic checks for ACD Hill numbers (F-057)."""
from __future__ import annotations

import math

import numpy as np
import pytest

from tools.ewsd_pure import CompartmentInputs, compute_compartment_metrics
from tools.spectral_density_hill import hill_number, hill_profile, energy_shares

Q_VALUES = (0.0, 1.0, 2.0, math.inf)
BASE = np.asarray([2.0, 0.2, 0.2], dtype=float)


def _dq(amps: np.ndarray, q: float) -> float:
    return hill_number(energy_shares(amps), q)


@pytest.mark.parametrize("q", Q_VALUES)
@pytest.mark.parametrize("c", (1e-6, 1e-3, 1.0, 1e3, 1e6))
def test_scaling_invariance(q: float, c: float) -> None:
    left = _dq(c * BASE, q)
    right = _dq(BASE, q)
    assert np.isfinite(left) and np.isfinite(right)
    assert left == pytest.approx(right, rel=0.0, abs=1e-12)


def test_babies_acd_d2_stable_ewsd_not() -> None:
    strong = np.asarray([1.0, 1.0, 1.0], dtype=float)
    babies = np.full(50, float(10.0 ** (-80.0 / 20.0)), dtype=float)
    d2_0 = hill_profile(strong)["D2"]
    d2_1 = hill_profile(np.concatenate([strong, babies]))["D2"]
    assert abs(d2_1 - d2_0) / d2_0 < 0.01

    h0 = compute_compartment_metrics(
        CompartmentInputs(values=strong, analysis_ratio=1.0, weight_function="log")
    )
    one_m60 = np.concatenate([strong, [10.0 ** (-60.0 / 20.0)]])
    fifty_m60 = np.concatenate([strong, np.full(50, 10.0 ** (-60.0 / 20.0))])
    h1 = compute_compartment_metrics(
        CompartmentInputs(values=one_m60, analysis_ratio=1.0, weight_function="log")
    )
    h50 = compute_compartment_metrics(
        CompartmentInputs(values=fifty_m60, analysis_ratio=1.0, weight_function="log")
    )
    drop1 = (h0.ewsd_score - h1.ewsd_score) / h0.ewsd_score
    drop50 = (h0.ewsd_score - h50.ewsd_score) / h0.ewsd_score
    assert drop1 == pytest.approx(0.249, abs=0.01)
    assert drop50 == pytest.approx(0.939, abs=0.01)


@pytest.mark.parametrize("q", Q_VALUES)
def test_cloning_replication_principle(q: float) -> None:
    left = np.asarray([1.0, 0.6, 0.4], dtype=float)
    cloned = np.concatenate([left, left])
    d0 = _dq(left, q)
    d1 = _dq(cloned, q)
    assert d1 == pytest.approx(2.0 * d0, abs=1e-9)


def test_dalton_robin_hood_increases_d2() -> None:
    rich = np.asarray([4.0, 1.0, 0.5], dtype=float)
    # move energy from the strongest to the weakest in A^2 space
    pwr = np.square(rich)
    transfer = 0.4
    pwr[0] -= transfer
    pwr[2] += transfer
    after = np.sqrt(pwr)
    assert hill_profile(after)["D2"] > hill_profile(rich)["D2"]


def test_rising_tide_increases_hill_d2() -> None:
    """Hurley & Rickard rising tide decreases *sparsity*; Hill D2 is diversity.

    Adding a positive constant to unequal amplitudes equalises energy shares,
    so D2 increases. The dual sparsity statement is not applied to D2.
    """
    unequal = np.asarray([3.0, 1.0, 0.4], dtype=float)
    tide = unequal + 2.5
    assert hill_profile(tide)["D2"] > hill_profile(unequal)["D2"]


def test_bill_gates_d2_to_one() -> None:
    base = np.asarray([1.0, 0.8, 0.6], dtype=float)
    huge = base.copy()
    huge[0] = 1.0e8
    assert hill_profile(huge)["D2"] == pytest.approx(1.0, abs=1e-6)
