from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import compile_metrics


def _write_per_note_workbook(
    path: Path,
    *,
    harmonic_amp: list[float],
    inharmonic_amp: list[float],
    subbass_amp: list[float],
    w_h: float,
    w_i: float,
    w_s: float,
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
                "note_source",
            ],
            "Value": [
                compile_metrics.EXPECTED_ANALYSIS_SCHEMA_VERSION,
                w_h,
                w_i,
                w_s,
                "filename_token",
            ],
        }
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        harmonic.to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
        inharmonic.to_excel(writer, sheet_name="Inharmonic Spectrum", index=False)
        subbass.to_excel(writer, sheet_name="Sub-bass band", index=False)
        metadata.to_excel(writer, sheet_name="Analysis_Metadata", index=False)


def test_density_metrics_sheet_uses_phase2_profile_on_export(tmp_path: Path) -> None:
    n1 = tmp_path / "A4" / "spectral_analysis.xlsx"
    n2 = tmp_path / "B4" / "spectral_analysis.xlsx"
    _write_per_note_workbook(
        n1,
        harmonic_amp=[4.0, 2.0],  # D_H = 6.0
        inharmonic_amp=[1.0],  # D_I = 1.0
        subbass_amp=[0.5],  # D_S = 0.5
        w_h=0.70,
        w_i=0.20,
        w_s=0.10,
    )
    _write_per_note_workbook(
        n2,
        harmonic_amp=[3.0, 1.0],  # D_H = 4.0
        inharmonic_amp=[2.0],  # D_I = 2.0
        subbass_amp=[1.0],  # D_S = 1.0
        w_h=0.50,
        w_i=0.30,
        w_s=0.20,
    )

    out_xlsx = tmp_path / "compiled_export_test.xlsx"
    in_memory = compile_metrics.compile_density_metrics_with_pca(
        folder_path=tmp_path,
        output_path=out_xlsx,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
        harmonic_weight=0.6,
        inharmonic_weight=0.3,
        subbass_weight=0.1,
    )
    assert in_memory is not None
    assert out_xlsx.exists()

    density_sheet = pd.read_excel(out_xlsx, sheet_name="Density_Metrics")
    assert not density_sheet.empty
    assert set(density_sheet["density_weights_source"].astype(str)) == {"phase2_corpus_profile"}

    expected = {
        "A4": {"D_H": 6.0, "D_I": 1.0, "D_S": 0.5, "w_h": 0.70, "w_i": 0.20, "w_s": 0.10},
        "B4": {"D_H": 4.0, "D_I": 2.0, "D_S": 1.0, "w_h": 0.50, "w_i": 0.30, "w_s": 0.20},
    }
    for _, row in density_sheet.iterrows():
        note = str(row["Note"])
        ref = expected[note]
        expected_phase2 = ref["D_H"] * 0.6 + ref["D_I"] * 0.3 + ref["D_S"] * 0.1
        expected_per_note = (
            ref["D_H"] * ref["w_h"] + ref["D_I"] * ref["w_i"] + ref["D_S"] * ref["w_s"]
        )
        assert float(row["density_metric_raw"]) == pytest.approx(expected_phase2, rel=0.0, abs=1e-12)
        assert float(row["density_metric_raw_per_note_balance"]) == pytest.approx(
            expected_per_note, rel=0.0, abs=1e-12
        )

    # When the in-memory frame already carries the canonical weighted column,
    # the written sheet must preserve it exactly.
    if "density_metric_raw" in in_memory.columns:
        in_mem = in_memory.set_index("Note")["density_metric_raw"].astype(float)
        sheet = density_sheet.set_index("Note")["density_metric_raw"].astype(float)
        for note in ("A4", "B4"):
            assert float(sheet.loc[note]) == pytest.approx(
                float(in_mem.loc[note]), rel=0.0, abs=1e-12
            )
