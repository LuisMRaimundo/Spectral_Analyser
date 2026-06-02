from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tools.ewsd_pure import (
    CompartmentInputs,
    compute_acoustic_balanced_score,
    compute_compartment_metrics,
    compute_note_ewsd,
    compute_strict_ewsd_total,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "ewsd_golden"


def _independent_reference_compartment(
    values: list[float],
    analysis_ratio: float,
    weight_function: str,
    *,
    apply_anti_concentration: bool = True,
    frequencies_hz: list[float] | None = None,
) -> tuple[float, float, float]:
    """
    Independent EWSD compartment reference (no ewsd_core imports).

    Returns (ratio_weighted_metric, concentration_penalty, ewsd_score).
    """
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v) & (v >= 0.0)]
    ratio = float(analysis_ratio)
    if v.size == 0 or not np.isfinite(ratio) or ratio <= 0.0:
        return 0.0, 0.0, 0.0

    wf = (weight_function or "linear").strip().lower()
    if wf in {"log", "d3", "d10", "d24"}:
        strengths = np.log1p(v)
        original = float(np.sum(np.log1p(v)))
    elif wf == "sqrt":
        strengths = np.sqrt(v)
        original = float(np.sum(strengths))
    elif wf == "linear":
        strengths = v
        original = float(np.sum(v))
    else:
        raise AssertionError(f"independent reference does not cover weight {weight_function}")

    if wf == "d24" and frequencies_hz is not None:
        f = np.asarray(frequencies_hz, dtype=float)
        if f.size == v.size:
            m = (f <= 12000.0) & (v >= 0.01 * float(np.max(v)))
            strengths = np.where(m, strengths, 0.0)
            original = float(np.sum(np.log1p(v[m]))) if np.any(m) else 0.0

    strengths = strengths * ratio
    strengths = strengths[np.isfinite(strengths) & (strengths > 0.0)]
    n = int(strengths.size)
    if n == 0:
        return 0.0, 0.0, 0.0

    total = float(np.sum(strengths))
    p = strengths / total
    neff = float(1.0 / np.sum(p ** 2))
    penalty = float(neff / n)
    mass = float(original * ratio)
    score = float(mass * penalty) if apply_anti_concentration else mass
    return mass, penalty, score


def _load_golden_cases() -> list[dict]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(FIXTURES_DIR.glob("*.json"))]


@pytest.mark.parametrize("case", _load_golden_cases(), ids=lambda c: c["id"])
def test_golden_vectors_match_ewsd_pure(case: dict) -> None:
    compartments = [
        CompartmentInputs(
            values=c["values"],
            analysis_ratio=c["analysis_ratio"],
            frequencies_hz=np.asarray(c["frequencies_hz"], dtype=float)
            if c.get("frequencies_hz") is not None
            else None,
            weight_function=c.get("weight_function", "log"),
            apply_anti_concentration=c.get("apply_anti_concentration", True),
        )
        for c in case["compartments"]
    ]
    result = compute_note_ewsd(
        compartments,
        acoustic_balance_alpha=case.get("acoustic_balance_alpha", 0.5),
    )
    expected = case["expected"]

    assert result["ewsd_score_total"] == pytest.approx(expected["ewsd_score_total"], rel=0.0, abs=1e-12)
    assert result["ewsd_score_acoustic_balanced"] == pytest.approx(
        expected["ewsd_score_acoustic_balanced"], rel=0.0, abs=1e-12
    )

    for got, exp in zip(result["compartments"], expected["compartments"], strict=True):
        assert got.count == exp["count"]
        assert got.original_sum_metric == pytest.approx(exp["original_sum_metric"], abs=1e-12)
        assert got.ratio_weighted_metric == pytest.approx(exp["ratio_weighted_metric"], abs=1e-12)
        assert got.concentration_penalty == pytest.approx(exp["concentration_penalty"], abs=1e-12)
        assert got.ewsd_score == pytest.approx(exp["ewsd_score"], abs=1e-12)


@pytest.mark.parametrize("case", _load_golden_cases(), ids=lambda c: c["id"])
def test_golden_vectors_match_independent_reference(case: dict) -> None:
    metrics = []
    for comp in case["compartments"]:
        mass, penalty, score = _independent_reference_compartment(
            comp["values"],
            comp["analysis_ratio"],
            comp.get("weight_function", "log"),
            apply_anti_concentration=comp.get("apply_anti_concentration", True),
            frequencies_hz=comp.get("frequencies_hz"),
        )
        pure = compute_compartment_metrics(
            CompartmentInputs(
                values=comp["values"],
                analysis_ratio=comp["analysis_ratio"],
                frequencies_hz=comp.get("frequencies_hz"),
                weight_function=comp.get("weight_function", "log"),
                apply_anti_concentration=comp.get("apply_anti_concentration", True),
            )
        )
        assert pure.ratio_weighted_metric == pytest.approx(mass, abs=1e-12)
        assert pure.concentration_penalty == pytest.approx(penalty, abs=1e-12)
        assert pure.ewsd_score == pytest.approx(score, abs=1e-12)
        metrics.append(pure)

    alpha = case.get("acoustic_balance_alpha", 0.5)
    assert compute_strict_ewsd_total(metrics) == pytest.approx(
        case["expected"]["ewsd_score_total"], abs=1e-12
    )
    assert compute_acoustic_balanced_score(metrics, alpha=alpha) == pytest.approx(
        case["expected"]["ewsd_score_acoustic_balanced"], abs=1e-12
    )
