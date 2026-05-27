from __future__ import annotations

from pathlib import Path

import pandas as pd

import compile_metrics


def _write_note_workbook(path: Path, *, b_value: float) -> None:
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
            "inharmonicity_fit_residual_std_cents": [1.5],
            "inharmonicity_fit_status": ["ok"],
            "inharmonicity_fit_method": ["stiff_string_least_squares"],
        }
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        harmonic.to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
        inharmonic.to_excel(writer, sheet_name="Inharmonic Spectrum", index=False)
        subbass.to_excel(writer, sheet_name="Sub-bass band", index=False)
        metadata.to_excel(writer, sheet_name="Analysis_Metadata", index=False)
        inharm_sheet.to_excel(writer, sheet_name="Inharmonicity_Fit", index=False)


def test_inharmonicity_columns_propagate_to_compiled_density_metrics(tmp_path: Path) -> None:
    _write_note_workbook(tmp_path / "C4" / "spectral_analysis.xlsx", b_value=0.0)
    _write_note_workbook(tmp_path / "E4" / "spectral_analysis.xlsx", b_value=2e-5)
    _write_note_workbook(tmp_path / "G4" / "spectral_analysis.xlsx", b_value=1e-5)

    out_xlsx = tmp_path / "compiled_density_metrics.xlsx"
    _ = compile_metrics.compile_density_metrics_with_pca(
        folder_path=tmp_path,
        output_path=out_xlsx,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
        harmonic_weight=0.6,
        inharmonic_weight=0.3,
        subbass_weight=0.1,
    )
    dm = pd.read_excel(out_xlsx, sheet_name="Density_Metrics")

    for col in (
        "inharmonicity_coefficient_B",
        "inharmonicity_fit_residual_std_cents",
        "inharmonicity_fit_status",
        "inharmonicity_fit_method",
    ):
        assert col in dm.columns
    assert pd.to_numeric(dm["inharmonicity_coefficient_B"], errors="coerce").notna().all()
    assert dm["inharmonicity_fit_status"].astype(str).str.strip().ne("").all()
