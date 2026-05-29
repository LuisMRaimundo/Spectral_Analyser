from __future__ import annotations

from pathlib import Path

import pandas as pd

from constants import COUNT_SEMANTICS_NOTE_DOC
from tools import export_research_density_workbook as research_export


def _write_compiled_workbook(path: Path) -> None:
    density = pd.DataFrame(
        {
            "Note": ["A4"],
            "density_metric_raw": [1.0],
            "density_metric_normalized": [1.0],
            "harmonic_density_sum": [1.0],
            "inharmonic_density_sum": [0.1],
            "subbass_density_sum": [0.05],
            "component_harmonic_energy_ratio": [0.8],
            "component_inharmonic_energy_ratio": [0.15],
            "component_subbass_energy_ratio": [0.05],
            "f0_final_hz": [440.0],
            "f0_source": ["nominal_guided"],
            "f0_final_source": ["nominal_guided"],
            "acoustic_f0_status": ["nominal_guided_acoustically_verified"],
            "f0_fit_accepted": [True],
            "harmonic_bin_count": [321],
            "harmonic_peak_candidate_count": [47],
            "harmonic_occupancy_detected_order_count": [9],
            "expected_harmonic_order_count_up_to_body_ceiling": [11],
            "salient_harmonic_order_count_up_to_body_ceiling": [6],
            "salient_harmonic_coverage_up_to_body_ceiling": [6 / 11],
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


def test_non_literal_count_semantics_are_explicit() -> None:
    note_doc = str(COUNT_SEMANTICS_NOTE_DOC).lower()
    assert "harmonic_bin_count" in note_doc
    assert "debug_counts" in note_doc
    assert "not synonymous with harmonic_order_count" in note_doc


def test_occupancy_metadata_marks_non_physical_semantics(tmp_path: Path) -> None:
    compiled = tmp_path / "compiled_density_metrics.xlsx"
    _write_compiled_workbook(compiled)
    output = tmp_path / "compiled_density_metrics_research.xlsx"
    research_export.export_research_workbook(
        input_path=compiled,
        output_path=output,
        overwrite=True,
        no_charts=True,
    )

    metadata = pd.read_excel(output, sheet_name="Metadata")
    key_col = str(metadata.columns[0])
    val_col = str(metadata.columns[1]) if len(metadata.columns) > 1 else str(metadata.columns[0])
    mapping = {str(k): str(v) for k, v in zip(metadata[key_col], metadata[val_col], strict=False)}

    desc = mapping.get("harmonic_region_occupancy_count_definition", "").lower()
    assert "occupancy/slot-derived descriptor" in desc
    assert "not a strict count of detected harmonic partial orders" in desc
