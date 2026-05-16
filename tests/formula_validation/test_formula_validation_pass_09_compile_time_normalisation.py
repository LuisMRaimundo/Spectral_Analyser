"""Formula validation Pass 9 — compile-time normalisation (docs/formula_validation/)."""

import numpy as np
import numpy.testing as npt
import pandas as pd

import compile_metrics


# Case 9-01
def test_canonical_density_fallback_from_density_metric() -> None:
    df = pd.DataFrame({"Density Metric": [50.0]})
    out = compile_metrics._add_canonical_and_global_density_columns(df)
    npt.assert_allclose(
        float(out["canonical_density_v5_adapted"].iloc[0]),
        5.0,
        rtol=0.0,
        atol=1e-12,
    )


# Case 9-02
def test_density_normalized_global_two_rows() -> None:
    df = pd.DataFrame(
        {
            "canonical_density_v5_adapted": [2.0, 8.0],
            "harmonic_order_count": [1, 1],
        }
    )
    out = compile_metrics._add_canonical_and_global_density_columns(df)
    npt.assert_allclose(out["density_normalized_global"].to_numpy(), [0.25, 1.0], rtol=0.0, atol=1e-12)
    assert float(out["density_normalization_denominator"].iloc[0]) == 8.0


# Case 9-03
def test_density_per_component_division() -> None:
    df = pd.DataFrame(
        {
            "canonical_density_v5_adapted": [6.0],
            "harmonic_order_count": [2],
        }
    )
    out = compile_metrics._add_canonical_and_global_density_columns(df)
    npt.assert_allclose(float(out["density_per_component"].iloc[0]), 3.0, rtol=0.0, atol=1e-12)


# Case 9-04
def test_weighted_density_metric_raw() -> None:
    df = pd.DataFrame(
        {
            "canonical_density_v5_adapted": [1.0],
            "harmonic_order_count": [1],
            "Harmonic Partials sum": [10.0],
            "Inharmonic Partials sum": [10.0],
            "Sub-bass sum": [10.0],
            "component_harmonic_energy_ratio": [0.2],
            "component_inharmonic_energy_ratio": [0.2],
            "component_subbass_energy_ratio": [0.2],
        }
    )
    out = compile_metrics._add_canonical_and_global_density_columns(df)
    npt.assert_allclose(float(out["density_metric_raw"].iloc[0]), 6.0, rtol=0.0, atol=1e-12)
