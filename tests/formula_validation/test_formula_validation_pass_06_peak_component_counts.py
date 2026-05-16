"""Formula validation Pass 6 — peak component counts (docs/formula_validation/)."""

import numpy as np
import numpy.testing as npt
import pandas as pd

import peak_component_counts


# Case 6-01
def test_linear_amp_from_row_db_to_linear() -> None:
    df = pd.DataFrame({"Magnitude (dB)": [20.0]})
    row = df.iloc[0]
    out = peak_component_counts._linear_amp_from_row(row, df)
    npt.assert_allclose(out, 10.0, rtol=0.0, atol=1e-12)


# Case 6-02
def test_hz_tolerance_from_cents_matches_classify_formula() -> None:
    expected_freq = 200.0
    tolerance_cents = 18.0
    tol_hz = expected_freq * (2.0 ** (tolerance_cents / 1200.0) - 1.0)
    npt.assert_allclose(tol_hz, 2.0902892973527543, rtol=1e-12, atol=1e-12)


# Case 6-03
def test_classify_peaks_subbass_and_harmonic() -> None:
    df = pd.DataFrame(
        {
            "Frequency (Hz)": [50.0, 300.0],
            "Magnitude (dB)": [0.0, 0.0],
        }
    )
    out = peak_component_counts.classify_peaks_harmonic_inharmonic_subbass_from_df(
        df,
        100.0,
        subbass_cutoff_hz=200.0,
        tolerance_cents=18.0,
    )
    assert out["peaklist_low_frequency_window_candidate_count"] >= 1
    assert out["peaklist_harmonic_window_candidate_count"] >= 1
    assert out["classification_valid"] is True
