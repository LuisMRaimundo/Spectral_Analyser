from __future__ import annotations

from pathlib import Path

import pandas as pd

from tools import export_research_density_workbook as research_export


def _write_compiled_workbook(path: Path) -> None:
    density = pd.DataFrame(
        {
            "Note": ["B3", "A4", "C6"],
            "f0_final_hz": [247.0, 440.0, 1047.0],
            "f0_source": ["nominal_guided", "nominal_guided", "nominal_guided"],
            "f0_final_source": ["nominal_guided", "nominal_guided", "nominal_guided"],
            "acoustic_f0_status": [
                "nominal_guided_acoustically_verified",
                "nominal_guided_acoustically_verified",
                "nominal_guided_acoustically_verified",
            ],
            "f0_fit_accepted": [True, True, True],
            "density_metric_raw": [1.0, 1.1, 1.2],
            "density_metric_normalized": [0.8, 0.9, 1.0],
            "harmonic_density_sum": [1.0, 1.0, 1.0],
            "inharmonic_density_sum": [0.1, 0.1, 0.1],
            "subbass_density_sum": [0.05, 0.05, 0.05],
            "component_harmonic_energy_ratio": [0.8, 0.8, 0.8],
            "component_inharmonic_energy_ratio": [0.15, 0.15, 0.15],
            "component_subbass_energy_ratio": [0.05, 0.05, 0.05],
            "expected_harmonic_order_count_up_to_body_ceiling": [20, 11, 4],
            "salient_harmonic_order_count_up_to_body_ceiling": [6, 5, 3],
            "salient_harmonic_coverage_up_to_body_ceiling": [0.3, 5 / 11, 0.75],
            "harmonic_bin_count": [210, 387, 198],
            "harmonic_peak_candidate_count": [75, 40, 17],
            "harmonic_occupancy_detected_order_count": [10, 9, 7],
            "Harmonic Count": [81, 46, 20],
            "Harmonic Count (N)": [81, 46, 20],
        }
    )
    meta = pd.DataFrame(
        {
            "analysis_version": ["test"],
            "weight_function": ["log"],
            "density_salience_threshold_db": [-60.0],
            "density_frequency_ceiling_hz": [20000.0],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        density.to_excel(writer, sheet_name="Density_Metrics", index=False)
        meta.to_excel(writer, sheet_name="Analysis_Metadata", index=False)


def test_research_export_harmonic_semantics(tmp_path: Path) -> None:
    compiled = tmp_path / "compiled_density_metrics.xlsx"
    _write_compiled_workbook(compiled)
    output = tmp_path / "compiled_density_metrics_research.xlsx"
    research_export.export_research_workbook(
        input_path=compiled,
        output_path=output,
        overwrite=True,
        no_charts=True,
    )

    sdm = pd.read_excel(output, sheet_name="Spectral_Density_Metrics")
    for col in (
        "expected_harmonic_order_count_up_to_body_ceiling",
        "salient_harmonic_order_count_up_to_body_ceiling",
        "salient_harmonic_coverage_up_to_body_ceiling",
        "theoretical_harmonic_order_count_up_to_body_ceiling",
        "detected_salient_harmonic_order_count_up_to_body_ceiling",
        "salient_harmonic_coverage_ratio_up_to_body_ceiling",
    ):
        assert col in sdm.columns

    assert "harmonic_bin_count" not in sdm.columns
    assert "harmonic_peak_candidate_count" not in sdm.columns
    assert "Harmonic Count" not in sdm.columns
    assert "Harmonic Count (N)" not in sdm.columns
    if "legacy_high_ceiling_harmonic_slot_index_count" in sdm.columns:
        assert pd.to_numeric(
            sdm["legacy_high_ceiling_harmonic_slot_index_count"], errors="coerce"
        ).notna().all()
