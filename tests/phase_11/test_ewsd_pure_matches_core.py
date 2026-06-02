from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tools.ewsd_core import (
    ComponentSet,
    HISWeights,
    SCRIPT_VERSION,
    compute_ewsd,
)
from tools.ewsd_pure import EWSD_PURE_REVISION, CompartmentInputs, compute_note_ewsd

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "ewsd_golden"


def _component_set_from_golden(case: dict) -> ComponentSet:
    rows: list[dict[str, object]] = []
    family_map = {
        0: "harmonic",
        1: "nonharmonic_residual",
        2: "noise_subbass",
    }
    for idx, comp in enumerate(case["compartments"]):
        ftype = family_map.get(idx, "harmonic")
        freqs = comp.get("frequencies_hz") or [1000.0 + 100.0 * i for i in range(len(comp["values"]))]
        for val, freq in zip(comp["values"], freqs, strict=False):
            rows.append(
                {
                    "component_type": ftype if ftype != "noise_subbass" else "subbass_aggregated_band",
                    "frequency_hz": float(freq),
                    "magnitude_db": 0.0,
                    "basis_value": float(val),
                }
            )
    components = pd.DataFrame(rows)
    ratios = case["compartments"]
    if len(ratios) == 1:
        h, i, s = float(ratios[0]["analysis_ratio"]), 0.0, 0.0
    elif len(ratios) == 2:
        h, i, s = float(ratios[0]["analysis_ratio"]), float(ratios[1]["analysis_ratio"]), 0.0
    else:
        h = float(ratios[0]["analysis_ratio"])
        i = float(ratios[1]["analysis_ratio"])
        s = float(ratios[2]["analysis_ratio"])

    wf = case["compartments"][0].get("weight_function", "log")
    his = HISWeights(harmonic=h, nonharmonic_residual=i, noise_subbass=s, source="golden")
    return ComponentSet(
        source_file="golden.json",
        note="D3",
        components=components,
        weight_function=wf,
        basis="amplitude",
        mode="individual_exact",
        his_weights=his,
    )


@pytest.mark.parametrize(
    "case",
    [json.loads(p.read_text(encoding="utf-8")) for p in sorted(FIXTURES_DIR.glob("*.json"))],
    ids=lambda c: c["id"],
)
def test_ewsd_core_compute_matches_ewsd_pure(case: dict) -> None:
    cset = _component_set_from_golden(case)
    apply_anti = case["compartments"][0].get("apply_anti_concentration", True)
    core_row = compute_ewsd(cset, threshold_db_relative=None, apply_anti_concentration=apply_anti)

    pure_inputs = [
        CompartmentInputs(
            values=comp["values"],
            analysis_ratio=comp["analysis_ratio"],
            frequencies_hz=comp.get("frequencies_hz"),
            weight_function=comp.get("weight_function", "log"),
            apply_anti_concentration=comp.get("apply_anti_concentration", True),
        )
        for comp in case["compartments"]
    ]
    pure = compute_note_ewsd(
        pure_inputs,
        acoustic_balance_alpha=case.get("acoustic_balance_alpha", 0.5),
    )

    assert float(core_row["ewsd_score"]) == pytest.approx(pure["ewsd_score_total"], abs=1e-12)
    assert float(core_row["ewsd_score"]) == pytest.approx(case["expected"]["ewsd_score_total"], abs=1e-12)


def test_script_version_declares_pure_revision() -> None:
    assert SCRIPT_VERSION.startswith("EWSD-R v18")
    assert "pure" in EWSD_PURE_REVISION.lower()
