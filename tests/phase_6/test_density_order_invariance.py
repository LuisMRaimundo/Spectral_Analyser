from __future__ import annotations

import random

import pytest


def _weighted_raw(d_h: float, d_i: float, d_s: float, w_h: float, w_i: float, w_s: float) -> float:
    return float(d_h * w_h + d_i * w_i + d_s * w_s)


def test_density_metric_raw_invariant_to_iteration_order() -> None:
    rows = [
        (10.0, 3.0, 0.4, 0.65, 0.30, 0.05),
        (8.0, 2.5, 0.3, 0.62, 0.33, 0.05),
        (11.0, 2.0, 0.2, 0.68, 0.29, 0.03),
        (9.0, 2.8, 0.35, 0.60, 0.35, 0.05),
    ]
    baseline = [_weighted_raw(*r) for r in rows]
    shuffled = rows.copy()
    random.Random(20260526).shuffle(shuffled)
    shuffled_eval = [_weighted_raw(*r) for r in shuffled]

    assert sorted(baseline) == pytest.approx(sorted(shuffled_eval), rel=0.0, abs=1e-12)
