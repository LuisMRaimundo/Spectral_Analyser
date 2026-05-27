from __future__ import annotations

from pathlib import Path

import pandas as pd

import compile_metrics


def _write_note_workbook(path: Path, *, with_mir: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    harmonic = pd.DataFrame(
        {
            "Frequency (Hz)": [220.0, 440.0],
            "Amplitude_raw": [1.0, 0.5],
            "Power_raw": [1.0, 0.25],
            "include_for_density": [True, True],
        }
    )
    inharmonic = pd.DataFrame(
        {
            "Frequency (Hz)": [330.0],
            "Amplitude_raw": [0.2],
            "Power_raw": [0.04],
        }
    )
    subbass = pd.DataFrame(
        {
            "Frequency (Hz)": [50.0],
            "Amplitude_raw": [0.1],
            "Power_raw": [0.01],
        }
    )
    metadata = pd.DataFrame(
        {
            "Parameter": [
                "analysis_schema_version",
                "component_harmonic_energy_ratio",
                "component_inharmonic_energy_ratio",
                "component_subbass_energy_ratio",
            ],
            "Value": [
                compile_metrics.EXPECTED_ANALYSIS_SCHEMA_VERSION,
                0.7,
                0.2,
                0.1,
            ],
        }
    )
    metrics = pd.DataFrame(
        {
            "spectral_centroid_hz": [1450.0] if with_mir else [None],
            "spectral_rolloff_hz_85": [2550.0] if with_mir else [None],
            "spectral_flatness": [0.21] if with_mir else [None],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        harmonic.to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
        inharmonic.to_excel(writer, sheet_name="Inharmonic Spectrum", index=False)
        subbass.to_excel(writer, sheet_name="Sub-bass band", index=False)
        metadata.to_excel(writer, sheet_name="Analysis_Metadata", index=False)
        metrics.to_excel(writer, sheet_name="Metrics", index=False)


def test_mir_descriptor_values_exported_when_present(tmp_path: Path) -> None:
    _write_note_workbook(tmp_path / "C4" / "spectral_analysis.xlsx", with_mir=True)
    out_xlsx = tmp_path / "compiled.xlsx"
    compile_metrics.compile_density_metrics_with_pca(
        folder_path=tmp_path,
        output_path=out_xlsx,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
    )
    dm = pd.read_excel(out_xlsx, sheet_name="Density_Metrics")
    row = dm.iloc[0]
    assert abs(float(row["spectral_centroid_hz"]) - 1450.0) < 1e-12
    assert abs(float(row["spectral_rolloff_hz_85"]) - 2550.0) < 1e-12
    assert abs(float(row["spectral_flatness"]) - 0.21) < 1e-12
    assert bool(row["mir_descriptors_available"]) is True


def test_mir_descriptor_availability_flags_when_missing(tmp_path: Path) -> None:
    _write_note_workbook(tmp_path / "A4" / "spectral_analysis.xlsx", with_mir=False)
    out_xlsx = tmp_path / "compiled.xlsx"
    compile_metrics.compile_density_metrics_with_pca(
        folder_path=tmp_path,
        output_path=out_xlsx,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
    )
    dm = pd.read_excel(out_xlsx, sheet_name="Density_Metrics")
    row = dm.iloc[0]
    assert "mir_descriptors_available" in dm.columns
    assert "mir_descriptors_missing_reason" in dm.columns
    assert bool(row["mir_descriptors_available"]) is False
    assert str(row["mir_descriptors_missing_reason"]).strip() != ""
