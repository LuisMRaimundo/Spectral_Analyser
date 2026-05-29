from __future__ import annotations

from pathlib import Path

import pandas as pd

from tools import export_research_density_workbook as research_export


def _write_compiled(path: Path) -> None:
    density = pd.DataFrame(
        {
            "Note": ["A4"],
            "f0_final_hz": [440.0],
            "f0_source": ["nominal_guided"],
            "f0_final_source": ["nominal_guided"],
            "acoustic_f0_status": ["nominal_guided_acoustically_verified"],
            "f0_fit_accepted": [True],
            "density_metric_raw": [0.8],
            "density_component_body_weighted_sum_body_ceiling": [0.8],
            "density_body_weighted_sum_body_ceiling": [999.0],
            "density_full_spectrum_weighted_sum_20khz": [1.4],
            "harmonic_component_energy_sum_body_ceiling": [0.5],
            "inharmonic_component_energy_sum_body_ceiling": [0.2],
            "subbass_component_energy_sum": [0.1],
            "harmonic_body_energy_sum_body_ceiling": [0.5],
            "inharmonic_body_energy_sum_body_ceiling": [0.2],
            "subbass_rumble_energy_sum": [0.1],
            "harmonic_density_sum": [0.5],
            "inharmonic_density_sum": [0.2],
            "subbass_density_sum": [0.1],
            "component_harmonic_energy_ratio": [0.7],
            "component_inharmonic_energy_ratio": [0.2],
            "component_subbass_energy_ratio": [0.1],
            "expected_harmonic_order_count_up_to_body_ceiling": [11],
            "salient_harmonic_order_count_up_to_body_ceiling": [5],
            "salient_harmonic_coverage_up_to_body_ceiling": [5 / 11],
        }
    )
    meta = pd.DataFrame({"analysis_version": ["test"], "weight_function": ["log"]})
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        density.to_excel(writer, sheet_name="Density_Metrics", index=False)
        meta.to_excel(writer, sheet_name="Analysis_Metadata", index=False)


def test_research_export_primary_density_is_body_limited(tmp_path: Path) -> None:
    compiled = tmp_path / "compiled_density_metrics.xlsx"
    _write_compiled(compiled)
    output = tmp_path / "compiled_density_metrics_research.xlsx"
    research_export.export_research_workbook(compiled, output_path=output, overwrite=True, no_charts=True)
    sdm = pd.read_excel(output, sheet_name="Spectral_Density_Metrics")
    assert "density_component_body_weighted_sum_body_ceiling" in sdm.columns
    assert float(sdm.loc[0, "density_weighted_sum"]) == float(sdm.loc[0, "density_component_body_weighted_sum_body_ceiling"])
    assert float(sdm.loc[0, "density_weighted_sum"]) != float(sdm.loc[0, "density_body_weighted_sum_body_ceiling"])
