from __future__ import annotations

import math


def test_theoretical_harmonic_order_decreases_with_higher_f0() -> None:
    # Representative flute notes under fixed analysis ceiling.
    f0s = [247.0, 440.0, 1047.0, 1760.0, 2349.0]  # B3, A4, C6, A6, D7
    counts = [int(math.floor(20000.0 / f0)) for f0 in f0s]

    # Non-increasing with register rise.
    assert counts == sorted(counts, reverse=True)
