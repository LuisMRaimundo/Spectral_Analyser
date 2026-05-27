from __future__ import annotations

from pathlib import Path

import pandas as pd

import compile_metrics


def _write_note_workbook(
    path: Path,
    *,
    b_value: float,
    fit_status: str | None,
    residual_std_cents: float | None,
    fit_method: str | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    harmonic = pd.DataFrame(
        {
            "Frequency (Hz)": [220.0, 440.0],
            "Amplitude_raw": [1.0, 0.7],
            "Power_raw": [1.0, 0.49],
            "include_for_density": [True, True],
        }
    )
    inharmonic = pd.DataFrame(
        {
            "Frequency (Hz)": [320.0],
            "Amplitude_raw": [0.2],
            "Power_raw": [0.04],
        }
    )
    subbass = pd.DataFrame(
        {
            "Frequency (Hz)": [45.0],
            "Amplitude_raw": [0.12],
            "Power_raw": [0.0144],
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
    inharm_sheet = pd.DataFrame(
        {
            "inharmonicity_coefficient_B": [b_value],
            "inharmonicity_fit_residual_std_cents": [residual_std_cents],
            "inharmonicity_fit_status": [fit_status],
            "inharmonicity_fit_method": [fit_method],
        }
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        harmonic.to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
        inharmonic.to_excel(writer, sheet_name="Inharmonic Spectrum", index=False)
        subbass.to_excel(writer, sheet_name="Sub-bass band", index=False)
        metadata.to_excel(writer, sheet_name="Analysis_Metadata", index=False)
        inharm_sheet.to_excel(writer, sheet_name="Inharmonicity_Fit", index=False)


def test_inharmonicity_diagnostics_export_complete_sheet_values(tmp_path: Path) -> None:
    _write_note_workbook(
        tmp_path / "C4" / "spectral_analysis.xlsx",
        b_value=2.2e-6,
        fit_status="ok",
        residual_std_cents=1.23,
        fit_method="stiff_string_least_squares",
    )
    out_xlsx = tmp_path / "compiled.xlsx"
    compile_metrics.compile_density_metrics_with_pca(
        folder_path=tmp_path,
        output_path=out_xlsx,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
    )
    dm = pd.read_excel(out_xlsx, sheet_name="Density_Metrics")
    assert len(dm) == 1

    required = [
        "inharmonicity_coefficient_B",
        "inharmonicity_fit_status",
        "inharmonicity_fit_residual_std_cents",
        "inharmonicity_fit_method",
        "inharmonicity_model_applied",
        "inharmonicity_fit_source",
    ]
    for col in required:
        assert col in dm.columns
    row = dm.iloc[0]
    assert abs(float(row["inharmonicity_coefficient_B"]) - 2.2e-6) < 1e-12
    assert str(row["inharmonicity_fit_status"]).strip() == "ok"
    assert abs(float(row["inharmonicity_fit_residual_std_cents"]) - 1.23) < 1e-12
    assert str(row["inharmonicity_fit_method"]).strip() == "stiff_string_least_squares"
    assert str(row["inharmonicity_fit_source"]).strip() == "per_note_inharmonicity_fit_sheet"


def test_inharmonicity_diagnostics_export_partial_sheet_marks_source(tmp_path: Path) -> None:
    _write_note_workbook(
        tmp_path / "A4" / "spectral_analysis.xlsx",
        b_value=3.3e-6,
        fit_status=None,
        residual_std_cents=None,
        fit_method="stiff_string_least_squares",
    )
    out_xlsx = tmp_path / "compiled.xlsx"
    compile_metrics.compile_density_metrics_with_pca(
        folder_path=tmp_path,
        output_path=out_xlsx,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
    )
    dm = pd.read_excel(out_xlsx, sheet_name="Density_Metrics")
    row = dm.iloc[0]
    assert abs(float(row["inharmonicity_coefficient_B"]) - 3.3e-6) < 1e-12
    assert str(row["inharmonicity_fit_source"]).strip() == "partial_export_missing_status"
    assert pd.isna(row["inharmonicity_fit_status"]) or str(row["inharmonicity_fit_status"]).strip() == ""
    assert pd.isna(row["inharmonicity_fit_residual_std_cents"])
