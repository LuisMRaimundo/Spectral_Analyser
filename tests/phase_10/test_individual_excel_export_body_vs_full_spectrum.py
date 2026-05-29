from __future__ import annotations

from pathlib import Path

import pandas as pd

from tests.phase_7_1b.helpers import run_stage1_synthetic_notes


def test_individual_excel_export_body_vs_full_spectrum(tmp_path: Path) -> None:
    workbooks = run_stage1_synthetic_notes(tmp_path, notes=[("A4", 440.0)])
    metrics = pd.read_excel(workbooks[0], sheet_name="Metrics")
    row = metrics.iloc[0]

    assert "density_body_weighted_sum_body_ceiling" in metrics.columns
    assert "density_full_spectrum_weighted_sum_20khz" in metrics.columns
    assert "body_density_frequency_ceiling_hz" in metrics.columns
    assert "full_spectrum_frequency_ceiling_hz" in metrics.columns
    assert float(row["body_density_frequency_ceiling_hz"]) > 0.0
    assert float(row["full_spectrum_frequency_ceiling_hz"]) >= float(row["body_density_frequency_ceiling_hz"])
