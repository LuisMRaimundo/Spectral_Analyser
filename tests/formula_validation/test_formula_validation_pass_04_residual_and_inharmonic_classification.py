"""Formula validation Pass 4 — residual / inharmonic classification (docs/formula_validation/)."""

import numpy as np
import pandas as pd

import density


# Case 4-01
def test_identify_nonharmonic_residual_rows_relative_tolerance() -> None:
    harmonic_df = pd.DataFrame({"Frequency (Hz)": [100.0]})
    complete_df = pd.DataFrame({"Frequency (Hz)": [100.0, 103.0], "x": [1, 2]})
    out = density.identify_nonharmonic_residual_rows(
        harmonic_df,
        complete_df,
        tolerance=0.02,
        spectral_leakage_guard=True,
    )
    assert len(out) == 1
    assert float(out["Frequency (Hz)"].iloc[0]) == 103.0


# Case 4-02
def test_identify_nonharmonic_residual_rows_guard_off_same_membership() -> None:
    harmonic_df = pd.DataFrame({"Frequency (Hz)": [100.0]})
    complete_df = pd.DataFrame({"Frequency (Hz)": [100.0, 103.0], "x": [1, 2]})
    out = density.identify_nonharmonic_residual_rows(
        harmonic_df,
        complete_df,
        tolerance=0.02,
        spectral_leakage_guard=False,
    )
    assert len(out) == 1
    assert np.isclose(out["Frequency (Hz)"].to_numpy(), [103.0]).all()
