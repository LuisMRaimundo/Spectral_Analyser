from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tools.ewsd_pure import ACOUSTIC_BALANCE_ALPHA_DEFAULT
from tools.ewsd_uncertainty import (
    bootstrap_ewsd_from_compartments,
    compartment_bootstrap_data_from_arrays,
)
from tools.ewsd_sensitivity_report import (
    alpha_rank_stability,
    balanced_score_from_row,
    construct_checks,
)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "ewsd_corpus_reference.json"


def test_bootstrap_ewsd_ci_brackets_point_estimate() -> None:
    comps = [
        compartment_bootstrap_data_from_arrays([1.0, 0.8, 0.6], 0.80, weight_function="log"),
        compartment_bootstrap_data_from_arrays([0.2, 0.15], 0.15, weight_function="log"),
        compartment_bootstrap_data_from_arrays([0.05], 0.05, weight_function="log"),
    ]
    res = bootstrap_ewsd_from_compartments(
        comps,
        n_boot=1200,
        seed=3,
        propagate_ratio_uncertainty=True,
    )
    assert res["ewsd_score_acoustic_balanced_ci_low"] <= res["ewsd_score_acoustic_balanced"]
    assert res["ewsd_score_acoustic_balanced"] <= res["ewsd_score_acoustic_balanced_ci_high"]
    assert res["ewsd_score_total_ci_low"] <= res["ewsd_score_total"] <= res["ewsd_score_total_ci_high"]
    assert res["uncertainty_sources"] == "partials+ratios"
    assert res["ewsd_score_acoustic_balanced_rel_uncertainty"] >= 0.0


def test_ratio_propagation_widens_or_matches_ewsd_uncertainty() -> None:
    comps = [
        compartment_bootstrap_data_from_arrays(list(np.linspace(0.2, 1.0, 25)), 0.75),
        compartment_bootstrap_data_from_arrays(list(np.linspace(0.05, 0.4, 12)), 0.20),
        compartment_bootstrap_data_from_arrays([0.08, 0.06], 0.05),
    ]
    partials_only = bootstrap_ewsd_from_compartments(
        comps, n_boot=800, seed=11, propagate_ratio_uncertainty=False
    )
    full = bootstrap_ewsd_from_compartments(
        comps, n_boot=800, seed=11, propagate_ratio_uncertainty=True
    )
    assert partials_only["uncertainty_sources"] == "partials"
    assert full["uncertainty_sources"] == "partials+ratios"
    assert full["ewsd_score_acoustic_balanced_rel_uncertainty"] >= (
        partials_only["ewsd_score_acoustic_balanced_rel_uncertainty"] - 1e-9
    )


@pytest.fixture(scope="module")
def corpus_reference() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_alpha_rank_stability_on_corpus_reference(corpus_reference: dict) -> None:
    rows = []
    for note in corpus_reference["notes"]:
        parts = note["compartments"]
        row = {"Note": note["Note"]}
        mapping = {
            "H": "harmonic",
            "I": "nonharmonic_residual",
            "S_noise": "noise_subbass",
        }
        for part in parts:
            fam = mapping[part["family"]]
            row[f"ratio_weighted_metric_{fam}"] = part["ratio_weighted_metric"]
            row[f"concentration_penalty_{fam}"] = part["concentration_penalty"]
        row["ewsd_score"] = note["EWSD_score_total"]
        row["ewsd_score_acoustic_balanced"] = note["EWSD_score_acoustic_balanced"]
        rows.append(row)
    frame = __import__("pandas").DataFrame(rows)
    stability = alpha_rank_stability(frame, alphas=(0.5, 1.0))
    assert len(stability) == 1
    assert float(stability.iloc[0]["spearman_rho"]) >= 0.90


def test_construct_checks_on_corpus_reference(corpus_reference: dict) -> None:
    import pandas as pd

    rows = [
        {
            "Note": n["Note"],
            "ewsd_score": n["EWSD_score_total"],
            "ewsd_score_acoustic_balanced": n["EWSD_score_acoustic_balanced"],
            "concentration_penalty_harmonic": next(
                p["concentration_penalty"] for p in n["compartments"] if p["family"] == "H"
            ),
            "concentration_penalty_nonharmonic_residual": next(
                p["concentration_penalty"] for p in n["compartments"] if p["family"] == "I"
            ),
            "concentration_penalty_noise_subbass": next(
                p["concentration_penalty"] for p in n["compartments"] if p["family"] == "S_noise"
            ),
        }
        for n in corpus_reference["notes"]
    ]
    checks = construct_checks(pd.DataFrame(rows))
    assert checks["n_finite_scores"] == 49
    assert checks["strict_balanced_not_identical"] is True
    assert 0.5 <= checks["spearman_strict_vs_balanced"] <= 1.0


def test_balanced_score_from_row_matches_alpha_default() -> None:
    row = {
        "ratio_weighted_metric_harmonic": 10.0,
        "concentration_penalty_harmonic": 0.5,
        "ratio_weighted_metric_nonharmonic_residual": 2.0,
        "concentration_penalty_nonharmonic_residual": 0.8,
        "ratio_weighted_metric_noise_subbass": 0.5,
        "concentration_penalty_noise_subbass": 1.0,
    }
    expected = 10.0 * (0.5 ** 0.5) + 2.0 * (0.8 ** 0.5) + 0.5 * 1.0
    assert balanced_score_from_row(row, ACOUSTIC_BALANCE_ALPHA_DEFAULT) == pytest.approx(expected)
