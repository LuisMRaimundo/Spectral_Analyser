"""Part B EWSD repairs: frozen F-048/F-049 values plus the eleven diagnostics."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tools.ewsd_core import (
    HISWeights,
    add_acoustic_alignment_columns,
    add_quality_columns,
    compute_ewsd,
)
from tools.ewsd_pure import (
    CompartmentInputs,
    compute_acoustic_balanced_score,
    compute_compartment_metrics,
    compute_note_ewsd,
    compute_strict_ewsd_total,
)
from tools.ewsd_research_integration import deterministic_ewsd_bootstrap_seed
from tools.ewsd_uncertainty import (
    bootstrap_ewsd_from_compartments,
    compartment_bootstrap_data_from_arrays,
)

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "phase_11" / "fixtures" / "ewsd_golden"
CORPUS_REF = Path(__file__).resolve().parents[1] / "phase_11" / "fixtures" / "ewsd_corpus_reference.json"


def test_b_frozen_golden_ewsd_unchanged() -> None:
    for path in sorted(GOLDEN_DIR.glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        comps = []
        for raw in case["compartments"]:
            comps.append(
                CompartmentInputs(
                    values=raw["values"],
                    analysis_ratio=raw["analysis_ratio"],
                    weight_function=raw.get("weight_function", "log"),
                    apply_anti_concentration=raw.get(
                        "apply_anti_concentration",
                        case.get("apply_anti_concentration", True),
                    ),
                    frequencies_hz=raw.get("frequencies_hz"),
                )
            )
        got = compute_note_ewsd(
            comps, acoustic_balance_alpha=case.get("acoustic_balance_alpha", 0.50)
        )
        expected = case["expected"]
        assert got["ewsd_score_total"] == pytest.approx(expected["ewsd_score_total"], abs=1e-12)
        assert got["ewsd_score_acoustic_balanced"] == pytest.approx(
            expected["ewsd_score_acoustic_balanced"], abs=1e-12
        )


def test_b_frozen_corpus_reference_unchanged() -> None:
    from tools.ewsd_pure import ACOUSTIC_BALANCE_ALPHA_DEFAULT, ewsd_from_compartment_summaries

    payload = json.loads(CORPUS_REF.read_text(encoding="utf-8"))
    for row in payload["notes"]:
        strict, balanced = ewsd_from_compartment_summaries(
            row["compartments"], alpha=ACOUSTIC_BALANCE_ALPHA_DEFAULT
        )
        assert strict == pytest.approx(row["EWSD_score_total"], abs=1e-10)
        assert balanced == pytest.approx(row["EWSD_score_acoustic_balanced"], abs=1e-10)


def test_b1_bootstrap_exports_companion_point() -> None:
    comps = [
        compartment_bootstrap_data_from_arrays([1.0, 0.4, 0.3], 0.820),
        compartment_bootstrap_data_from_arrays([0.05], 0.110),
        compartment_bootstrap_data_from_arrays([0.2], 0.070),
    ]
    res = bootstrap_ewsd_from_compartments(
        comps, n_boot=40, seed=1, propagate_ratio_uncertainty=True
    )
    excel_point = compute_strict_ewsd_total(
        [
            compute_compartment_metrics(
                CompartmentInputs(values=c.amplitudes, analysis_ratio=c.analysis_ratio)
            )
            for c in comps
        ]
    )
    assert res["ewsd_score_total"] == pytest.approx(excel_point, abs=1e-12)
    assert res["ewsd_ratio_definition_point"] == "excel_analysis_ratio"
    assert res["ewsd_ratio_definition_bootstrap"] == "resampled_energy_ratio"
    assert res["ewsd_score_total_point_under_bootstrap_ratios"] != pytest.approx(
        res["ewsd_score_total"], abs=1e-9
    )


def test_b2_bootstrap_bias_and_bca_exported() -> None:
    comps = [
        compartment_bootstrap_data_from_arrays([1.0, 0.8, 0.6, 0.4], 0.7),
        compartment_bootstrap_data_from_arrays([0.3, 0.2], 0.2),
        compartment_bootstrap_data_from_arrays([0.1], 0.1),
    ]
    res = bootstrap_ewsd_from_compartments(
        comps, n_boot=80, seed=2, propagate_ratio_uncertainty=False
    )
    assert np.isfinite(res["ewsd_bootstrap_bias_absolute"])
    assert np.isfinite(res["ewsd_score_total_ci_low_bca"])
    assert res["ewsd_score_total_ci_low"] <= res["ewsd_score_total"] <= res["ewsd_score_total_ci_high"]


def test_b3_label_is_sensitivity() -> None:
    comps = [
        compartment_bootstrap_data_from_arrays([1.0, 0.8, 0.6], 0.8),
        compartment_bootstrap_data_from_arrays([0.2, 0.15], 0.15),
        compartment_bootstrap_data_from_arrays([0.05], 0.05),
    ]
    res = bootstrap_ewsd_from_compartments(comps, n_boot=30, seed=0)
    assert res["uncertainty_sources"] == "partial_multiset_sensitivity"


def test_b4_seed_invariant_to_corpus_order() -> None:
    a = deterministic_ewsd_bootstrap_seed("abc123")
    b = deterministic_ewsd_bootstrap_seed("abc123")
    c = deterministic_ewsd_bootstrap_seed("zzz999")
    assert a == b
    assert a != c
    # adding an unrelated note does not change this note's seed
    _other = deterministic_ewsd_bootstrap_seed("unrelated")
    assert deterministic_ewsd_bootstrap_seed("abc123") == a


def test_b5_empty_row_family_fields_nan() -> None:
    from tools.ewsd_core import ComponentSet, _empty_row

    cset = ComponentSet(
        source_file="x",
        note="D3",
        components=pd.DataFrame(),
        weight_function="log",
        basis="amplitude",
        mode="individual_exact",
        his_weights=HISWeights(source="missing", warning="no ratios"),
    )
    row = _empty_row(cset, "no ratios", True)
    assert np.isnan(row["ewsd_score"])
    assert np.isnan(row["ewsd_score_harmonic"])
    assert np.isnan(row["ratio_weighted_metric_harmonic"])


def test_b6_balanced_requires_three_families() -> None:
    frame = pd.DataFrame(
        {
            "Note": ["D3", "E3"],
            "ewsd_score": [1.0, 1.0],
            "ratio_weighted_metric_harmonic": [1.0, 1.0],
            "concentration_penalty_harmonic": [1.0, 1.0],
            "ratio_weighted_metric_nonharmonic_residual": [0.2, np.nan],
            "concentration_penalty_nonharmonic_residual": [1.0, np.nan],
            "ratio_weighted_metric_noise_subbass": [0.1, np.nan],
            "concentration_penalty_noise_subbass": [1.0, np.nan],
        }
    )
    out = add_acoustic_alignment_columns(frame, None)
    assert out.loc[0, "ewsd_balanced_families_present"] == 3
    assert np.isfinite(out.loc[0, "ewsd_score_acoustic_balanced"])
    assert out.loc[1, "ewsd_balanced_families_present"] == 1
    assert np.isnan(out.loc[1, "ewsd_score_acoustic_balanced"])
    assert out.loc[0, "ewsd_score"] == 1.0


def test_b7_eligibility_uses_prenormalised_sum() -> None:
    frame = pd.DataFrame(
        {
            "mode": ["individual_exact", "individual_exact"],
            "warning": ["", ""],
            "analysis_ratio_weight_harmonic": [0.5, 0.8],
            "analysis_ratio_weight_nonharmonic_residual": [0.3, 0.15],
            "analysis_ratio_weight_noise_subbass": [0.2, 0.05],
            "his_ratio_input_sum": [1.5, 1.0],
            "ewsd_score": [1.0, 1.0],
            "component_count_salient": [4, 4],
            "Note_sort_warning": ["", ""],
            "weight_function_canonical": ["log", "log"],
        }
    )
    out = add_quality_columns(frame)
    assert bool(out.loc[0, "primary_analysis_eligible"]) is False
    assert bool(out.loc[1, "primary_analysis_eligible"]) is True


def test_b8_prefers_measured_f0() -> None:
    frame = pd.DataFrame(
        {
            "Note": ["A4"],
            "Note_midi_sort": [69],
            "ewsd_score": [1.0],
            "measured_f0_hz": [442.0],
            "ratio_weighted_metric_harmonic": [1.0],
            "concentration_penalty_harmonic": [1.0],
            "ratio_weighted_metric_nonharmonic_residual": [0.0],
            "concentration_penalty_nonharmonic_residual": [1.0],
            "ratio_weighted_metric_noise_subbass": [0.0],
            "concentration_penalty_noise_subbass": [1.0],
        }
    )
    out = add_acoustic_alignment_columns(frame, 20000.0)
    assert float(out.loc[0, "ewsd_estimated_f0_hz"]) == pytest.approx(442.0)
    assert out.loc[0, "ewsd_f0_source"] == "measured"
    frame2 = frame.copy()
    frame2["measured_f0_hz"] = [np.nan]
    out2 = add_acoustic_alignment_columns(frame2, 20000.0)
    assert float(out2.loc[0, "ewsd_estimated_f0_hz"]) == pytest.approx(440.0)
    assert out2.loc[0, "ewsd_f0_source"] == "nominal_12tet_a440"


def test_b11_weighted_mass_still_includes_ratio() -> None:
    comp = compute_compartment_metrics(
        CompartmentInputs(values=[1.0, 1.0], analysis_ratio=0.5, weight_function="log")
    )
    from tools.ewsd_pure import original_elementwise_weight

    phi = original_elementwise_weight([1.0, 1.0], "log")
    assert comp.weighted_mass == pytest.approx(float(np.sum(phi) * 0.5), abs=1e-12)
    assert comp.concentration_penalty == pytest.approx(1.0)
