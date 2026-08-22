"""Reproduce the D1-promotion saturation and dynamic-range tables.

Committed source for the numbers in ``docs/validation/ACD_THEORY.md``.
A 1/n amplitude series has energy shares 1/n^2; D2 converges to
(pi^2/6)^2 / (pi^4/90) = 2.500.
"""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np

from tools.spectral_density_hill import hill_profile

SATURATION_N = (4, 12, 40, 60)
DYNAMIC_N = range(8, 41)
DYNAMIC_SLOPES = (0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0)
D2_ANALYTIC_LIMIT = (math.pi**2 / 6.0) ** 2 / (math.pi**4 / 90.0)


def power_law_profile(n: int, slope: float = 1.0) -> dict[str, float]:
    idx = np.arange(1, int(n) + 1, dtype=float)
    return hill_profile(idx ** (-float(slope)))


def saturation_rows(ns: Iterable[int] = SATURATION_N) -> list[dict[str, float]]:
    rows = []
    for n in ns:
        p = power_law_profile(int(n), 1.0)
        rows.append(
            {
                "N": float(n),
                "D0": float(p["D0"]),
                "D1": float(p["D1"]),
                "D2": float(p["D2"]),
                "Dinf": float(p["Dinf"]),
            }
        )
    return rows


def dynamic_ranges(
    ns: Iterable[int] = DYNAMIC_N,
    slopes: Iterable[float] = DYNAMIC_SLOPES,
) -> dict[str, float]:
    d0: list[float] = []
    d1: list[float] = []
    d2: list[float] = []
    for n in ns:
        for slope in slopes:
            p = power_law_profile(int(n), float(slope))
            d0.append(float(p["D0"]))
            d1.append(float(p["D1"]))
            d2.append(float(p["D2"]))
    return {
        "D0": max(d0) / min(d0),
        "D1": max(d1) / min(d1),
        "D2": max(d2) / min(d2),
    }


def markdown_tables() -> str:
    sat = saturation_rows()
    dyn = dynamic_ranges()
    lines = [
        "## Why the headline count is D1, not D2",
        "",
        "D2 is a dominance statistic, not a count. For a 1/n rolloff —",
        "approximately what a bowed string produces — energy shares go as",
        "1/n^2 and D2 converges to the analytic limit",
        "",
        "```",
        "lim N→∞ D2 = (ζ(2))^2 / ζ(4)",
        "           = (π²/6)² / (π⁴/90)",
        f"           = {D2_ANALYTIC_LIMIT:.3f}",
        "```",
        "",
        "Derivation: p_n = n^{-2} / H_N^{(2)}, so",
        "D2 = (H_N^{(2)})^2 / H_N^{(4)}. The p-series limits are the",
        "Riemann zeta values ζ(2) = π²/6 and ζ(4) = π⁴/90.",
        "",
        "Numbers below are produced by `tests/phase_32/acd_d1_promotion_tables.py`",
        "on an unmerged 1/n amplitude series (A_n = 1/n).",
        "",
        "| N partials | D0 | D1 | D2 | Dinf |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in sat:
        lines.append(
            f"| {row['N']:.0f} | {row['D0']:.3f} | {row['D1']:.3f} | "
            f"{row['D2']:.3f} | {row['Dinf']:.3f} |"
        )
    lines += [
        "",
        "A fifteen-fold change in partial count moves D2 by "
        f"{100.0 * (sat[2]['D2'] / sat[0]['D2'] - 1.0):.0f}%. "
        "Jost (2006) argues that D1 = exp(H) is uniquely justified when no "
        "weighting of components is preferred a priori: each component is "
        "weighted by its share exactly once.",
        "",
        "Across N ∈ {8,…,40} and spectral slope ∈ {0.5,…,2.0} "
        "(A_n = n^{-slope}) the measured dynamic ranges are:",
        "",
        "| order | max/min |",
        "|---|---:|",
        f"| D0 | {dyn['D0']:.1f}× |",
        f"| D1 | {dyn['D1']:.1f}× |",
        f"| D2 | {dyn['D2']:.1f}× |",
        "",
        "Headline `ACD_score` is therefore `sum_k r_k D1_k`. The previous",
        "D2-based value is retained as `ACD_score_D2_dominance`.",
        " `ACD_D0_minus_D1` is the count of components present but not",
        "carrying effective weight — a texture descriptor, not a diagnostic.",
        "",
    ]
    return "\n".join(lines)
