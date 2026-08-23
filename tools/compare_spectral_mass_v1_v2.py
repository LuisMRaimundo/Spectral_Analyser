#!/usr/bin/env python3
"""Compare F-061 v1 vs v2 on a research workbook that already has ACD.

Requires pooled v1 inputs (ACD_D0, ACD_score, ACD_magnitude_per_component)
and v2 per-compartment columns. Prints Spearman, median |delta|, and notes
that move more than 3 ranks.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.spectral_mass import (
    REQUIRED_D0_COLUMNS,
    REQUIRED_D1_COLUMNS,
    REQUIRED_R_COLUMNS,
    add_spectral_mass_column,
    compute_spectral_mass_v1,
)


def compare_workbook(path: Path) -> dict:
    frame = pd.read_excel(path, sheet_name="Spectral_Density_Metrics")
    missing = [
        col
        for col in ("ACD_D0", "ACD_score", "ACD_magnitude_per_component", "ACD_status")
        + REQUIRED_D0_COLUMNS
        + REQUIRED_D1_COLUMNS
        + REQUIRED_R_COLUMNS
        if col not in frame.columns
    ]
    if missing:
        raise ValueError(f"workbook lacks columns for a v1↔v2 compare: {missing}")
    v2 = add_spectral_mass_column(frame)
    v1_mass = []
    for _, row in frame.iterrows():
        mass, _ = compute_spectral_mass_v1(
            row["ACD_D0"],
            row["ACD_score"],
            row["ACD_magnitude_per_component"],
            status=str(row.get("ACD_status", "")),
        )
        v1_mass.append(mass)
    v2["spectral_mass_v1"] = v1_mass
    paired = v2[["Note", "spectral_mass_v1", "spectral_mass"]].copy()
    paired = paired.replace([np.inf, -np.inf], np.nan).dropna()
    if paired.empty:
        return {"n": 0, "spearman": float("nan"), "median_abs_delta": float("nan"), "rank_movers": []}
    from scipy.stats import spearmanr

    rho, _ = spearmanr(paired["spectral_mass_v1"], paired["spectral_mass"])
    delta = (paired["spectral_mass"] - paired["spectral_mass_v1"]).abs()
    paired["rank_v1"] = paired["spectral_mass_v1"].rank(ascending=False, method="average")
    paired["rank_v2"] = paired["spectral_mass"].rank(ascending=False, method="average")
    movers = paired.loc[(paired["rank_v1"] - paired["rank_v2"]).abs() > 3, "Note"].astype(str).tolist()
    return {
        "n": int(len(paired)),
        "spearman": float(rho),
        "median_abs_delta": float(delta.median()),
        "rank_movers": movers,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook")
    args = parser.parse_args()
    report = compare_workbook(Path(args.workbook))
    print(report)


if __name__ == "__main__":
    main()
