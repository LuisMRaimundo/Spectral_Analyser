from __future__ import annotations

from pathlib import Path

import pandas as pd

from tools import export_research_density_workbook as research_export


def _write_compiled(path: Path) -> None:
    density = pd.DataFrame(
        {
            "Note": ["C5"],
            "density_metric_raw": [1.0],
            "density_body_weighted_sum_body_ceiling": [1.0],
            "harmonic_density_sum": [0.6],
            "inharmonic_density_sum": [0.3],
            "subbass_density_sum": [0.1],
            "component_harmonic_energy_ratio": [0.6],
            "component_inharmonic_energy_ratio": [0.3],
            "component_subbass_energy_ratio": [0.1],
            "Harmonic Count": [77],
            "Harmonic Count (N)": [77],
            "Harmonic Count (relative)": [0.9],
            "Harmonic Ceiling (relative)": [1.0],
            "harmonic_bin_count": [800],
            "harmonic_peak_candidate_count": [120],
            "harmonic_occupancy_detected_order_count": [9],
            "harmonic_order_count": [9],
        }
    )
    meta = pd.DataFrame({"analysis_version": ["test"], "weight_function": ["log"]})
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        density.to_excel(writer, sheet_name="Density_Metrics", index=False)
        meta.to_excel(writer, sheet_name="Analysis_Metadata", index=False)


def test_no_ambiguous_harmonic_count_names_in_research_main(tmp_path: Path) -> None:
    compiled = tmp_path / "compiled_density_metrics.xlsx"
    _write_compiled(compiled)
    output = tmp_path / "compiled_density_metrics_research.xlsx"
    research_export.export_research_workbook(compiled, output_path=output, overwrite=True, no_charts=True)
    sdm = pd.read_excel(output, sheet_name="Spectral_Density_Metrics")
    forbidden = {
        "Harmonic Count",
        "Harmonic Count (N)",
        "Harmonic Count (relative)",
        "Harmonic Ceiling (relative)",
        "harmonic_bin_count",
        "harmonic_peak_candidate_count",
        "harmonic_occupancy_detected_order_count",
        "harmonic_order_count",
    }
    assert forbidden.isdisjoint(set(map(str, sdm.columns)))
