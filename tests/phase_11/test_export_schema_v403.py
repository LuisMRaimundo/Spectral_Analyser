"""Regression tests for export schema fixes in v4.0.3."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from export_row_identity import attach_sample_id_from_density, sample_id_fully_populated
from tools import export_research_density_workbook as research_export


def test_sample_id_fully_populated_rejects_nan_placeholders() -> None:
    df = pd.DataFrame({"Note": ["D3"], "sample_id": [float("nan")]})
    assert not sample_id_fully_populated(df)


def test_attach_sample_id_from_density_fills_nan_column() -> None:
    diag = pd.DataFrame({"Note": ["D3", "G4"], "sample_id": [None, None]})
    density = pd.DataFrame(
        {
            "Note": ["D3", "G4"],
            "sample_id": ["d3__abc", "g4__def"],
        }
    )
    out = attach_sample_id_from_density(diag, density)
    assert sample_id_fully_populated(out)
    assert out.loc[0, "sample_id"] == "d3__abc"


def test_metadata_exports_distinct_phase2_weights(tmp_path: Path) -> None:
    density = pd.DataFrame(
        {
            "Note": ["D3"],
            "source_file_name": ["clarinet-D3-mf.wav"],
            "sample_id": ["d3__abc123"],
            "density_metric_raw": [0.42],
            "density_metric_normalized": [1.0],
            "harmonic_density_sum": [1.0],
            "inharmonic_density_sum": [0.1],
            "subbass_density_sum": [0.01],
            "component_harmonic_energy_ratio": [0.80],
            "component_inharmonic_energy_ratio": [0.15],
            "component_subbass_energy_ratio": [0.05],
            "f0_final_hz": [146.83],
            "acoustic_f0_status": ["nominal_guided_acoustically_verified"],
            "f0_fit_accepted": [True],
        }
    )
    meta = pd.DataFrame(
        {
            "analysis_version": ["test"],
            "weight_function": ["log"],
            "phase2_harmonic_application_weight": [0.7273],
            "phase2_inharmonic_application_weight": [0.2217],
            "phase2_subbass_application_weight": [0.0509],
        }
    )
    compiled = tmp_path / "compiled_density_metrics.xlsx"
    with pd.ExcelWriter(compiled, engine="openpyxl") as writer:
        density.to_excel(writer, sheet_name="Density_Metrics", index=False)
        meta.to_excel(writer, sheet_name="Analysis_Metadata", index=False)

    output = tmp_path / "compiled_density_metrics_research.xlsx"
    research_export.export_research_workbook(
        input_path=compiled,
        output_path=output,
        overwrite=True,
        no_charts=True,
        include_ewsd=False,
    )

    metadata = pd.read_excel(output, sheet_name="Metadata")
    field_col = metadata.columns[0]
    value_col = metadata.columns[1]
    kv = dict(zip(metadata[field_col].astype(str), metadata[value_col], strict=False))

    assert float(kv["harmonic_density_weight"]) == pytest.approx(0.7273)
    assert float(kv["inharmonic_density_weight"]) == pytest.approx(0.2217)
    assert float(kv["subbass_density_weight"]) == pytest.approx(0.0509)


def test_sanitize_drops_identical_suffix_columns_after_rename() -> None:
    df = pd.DataFrame([[1.0, 1.0], [2.0, 2.0]])
    df.columns = ["metric_a", "metric_a"]
    out = research_export._sanitize_dataframe_columns(df)
    assert "metric_a_2" not in out.columns
    assert list(out.columns) == ["metric_a"]
