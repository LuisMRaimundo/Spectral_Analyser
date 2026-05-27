from __future__ import annotations

from pathlib import Path

import pandas as pd

import compile_metrics


def _write_note_workbook(
    path: Path,
    *,
    harmonic_amp: list[float],
    inharmonic_amp: list[float],
    subbass_amp: list[float],
    n_fft: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    harmonic = pd.DataFrame(
        {
            "Frequency (Hz)": [220.0 + i * 220.0 for i in range(len(harmonic_amp))],
            "Amplitude_raw": harmonic_amp,
            "Power_raw": [x * x for x in harmonic_amp],
            "include_for_density": [True] * len(harmonic_amp),
        }
    )
    inharmonic = pd.DataFrame(
        {
            "Frequency (Hz)": [300.0 + i * 170.0 for i in range(len(inharmonic_amp))],
            "Amplitude_raw": inharmonic_amp,
            "Power_raw": [x * x for x in inharmonic_amp],
        }
    )
    subbass = pd.DataFrame(
        {
            "Frequency (Hz)": [40.0 + i * 10.0 for i in range(len(subbass_amp))],
            "Amplitude_raw": subbass_amp,
            "Power_raw": [x * x for x in subbass_amp],
        }
    )
    metadata = pd.DataFrame(
        {
            "Parameter": [
                "analysis_schema_version",
                "component_harmonic_energy_ratio",
                "component_inharmonic_energy_ratio",
                "component_subbass_energy_ratio",
                "n_fft",
                "n_fft_effective",
            ],
            "Value": [
                compile_metrics.EXPECTED_ANALYSIS_SCHEMA_VERSION,
                0.7,
                0.2,
                0.1,
                float(n_fft),
                float(n_fft),
            ],
        }
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        harmonic.to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
        inharmonic.to_excel(writer, sheet_name="Inharmonic Spectrum", index=False)
        subbass.to_excel(writer, sheet_name="Sub-bass band", index=False)
        metadata.to_excel(writer, sheet_name="Analysis_Metadata", index=False)


def test_density_metrics_tier_normalized_columns_are_populated_on_export(tmp_path: Path) -> None:
    _write_note_workbook(
        tmp_path / "A4" / "spectral_analysis.xlsx",
        harmonic_amp=[4.0, 2.0],
        inharmonic_amp=[1.0],
        subbass_amp=[0.5],
        n_fft=4096,
    )
    _write_note_workbook(
        tmp_path / "B4" / "spectral_analysis.xlsx",
        harmonic_amp=[3.0, 1.0],
        inharmonic_amp=[2.0],
        subbass_amp=[1.0],
        n_fft=8192,
    )

    out_xlsx = tmp_path / "compiled_density_metrics.xlsx"
    out_df = compile_metrics.compile_density_metrics_with_pca(
        folder_path=tmp_path,
        output_path=out_xlsx,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
    )
    assert out_df is not None
    assert out_xlsx.exists()

    dm = pd.read_excel(out_xlsx, sheet_name="Density_Metrics")
    assert not dm.empty

    pairs = [
        ("harmonic_amplitude_sum", "harmonic_amplitude_sum_tier_normalized"),
        ("inharmonic_amplitude_sum", "inharmonic_amplitude_sum_tier_normalized"),
        ("subbass_amplitude_sum", "subbass_amplitude_sum_tier_normalized"),
        ("harmonic_energy_sum", "harmonic_energy_sum_tier_normalized"),
        ("inharmonic_energy_sum", "inharmonic_energy_sum_tier_normalized"),
        ("subbass_energy_sum", "subbass_energy_sum_tier_normalized"),
    ]
    for raw_col, norm_col in pairs:
        assert raw_col in dm.columns
        assert norm_col in dm.columns
        mask = pd.to_numeric(dm[raw_col], errors="coerce").notna()
        if mask.any():
            assert pd.to_numeric(dm.loc[mask, norm_col], errors="coerce").notna().all()

    raw_exists_mask = (
        pd.to_numeric(dm["harmonic_amplitude_sum"], errors="coerce").notna()
        | pd.to_numeric(dm["inharmonic_amplitude_sum"], errors="coerce").notna()
        | pd.to_numeric(dm["subbass_amplitude_sum"], errors="coerce").notna()
        | pd.to_numeric(dm["harmonic_energy_sum"], errors="coerce").notna()
        | pd.to_numeric(dm["inharmonic_energy_sum"], errors="coerce").notna()
        | pd.to_numeric(dm["subbass_energy_sum"], errors="coerce").notna()
    )
    assert raw_exists_mask.any()
    assert set(dm.loc[raw_exists_mask, "tier_consistency_status"].astype(str)) == {
        "all_tiers_normalised"
    }
