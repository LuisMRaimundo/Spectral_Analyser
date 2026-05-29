from __future__ import annotations

from pathlib import Path

import pandas as pd

from tools import export_research_density_workbook as research_export


def _write_compiled(path: Path) -> None:
    density = pd.DataFrame(
        {
            "Note": ["B4"],
            "density_metric_raw": [0.7],
            "density_body_weighted_sum_body_ceiling": [0.7],
            "rolloff_compensated_harmonic_density": [4.2],
            "harmonic_density_sum": [0.45],
            "inharmonic_density_sum": [0.20],
            "subbass_density_sum": [0.05],
            "component_harmonic_energy_ratio": [0.65],
            "component_inharmonic_energy_ratio": [0.25],
            "component_subbass_energy_ratio": [0.10],
        }
    )
    meta = pd.DataFrame({"analysis_version": ["test"], "weight_function": ["log"]})
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        density.to_excel(writer, sheet_name="Density_Metrics", index=False)
        meta.to_excel(writer, sheet_name="Analysis_Metadata", index=False)


def test_rolloff_compensation_not_default_body_density(tmp_path: Path) -> None:
    compiled = tmp_path / "compiled_density_metrics.xlsx"
    _write_compiled(compiled)
    output = tmp_path / "compiled_density_metrics_research.xlsx"
    research_export.export_research_workbook(compiled, output_path=output, overwrite=True, no_charts=True)
    sdm = pd.read_excel(output, sheet_name="Spectral_Density_Metrics")
    assert float(sdm.loc[0, "density_weighted_sum"]) == float(sdm.loc[0, "density_body_weighted_sum_body_ceiling"])
    if "rolloff_compensated_harmonic_density" in sdm.columns:
        assert float(sdm.loc[0, "rolloff_compensated_harmonic_density"]) != float(
            sdm.loc[0, "density_body_weighted_sum_body_ceiling"]
        )
