from __future__ import annotations

from pathlib import Path

import pandas as pd

import compile_metrics


def _write_note_workbook(path: Path) -> None:
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
            "Frequency (Hz)": [330.0],
            "Amplitude_raw": [0.2],
            "Power_raw": [0.04],
        }
    )
    subbass = pd.DataFrame(
        {
            "Frequency (Hz)": [50.0],
            "Amplitude_raw": [0.01],
            "Power_raw": [0.0001],
        }
    )
    metadata = pd.DataFrame(
        {
            "Parameter": [
                "analysis_schema_version",
                "component_harmonic_energy_ratio",
                "component_inharmonic_energy_ratio",
                "component_subbass_energy_ratio",
                "analysis_parameter_profile_id",
                "is_primary_comparable_profile",
                "primary_comparable_profile_definition",
            ],
            "Value": [
                compile_metrics.EXPECTED_ANALYSIS_SCHEMA_VERSION,
                0.8,
                0.15,
                0.05,
                "PRIMARY",
                1,
                "wf=log,threshold=auto,ceiling=auto",
            ],
        }
    )
    inharm_fit = pd.DataFrame(
        {
            "inharmonicity_coefficient_B": [2e-6],
            "inharmonicity_fit_status": ["ok"],
            "inharmonicity_fit_residual_std_cents": [1.0],
            "inharmonicity_fit_method": ["stiff_string_least_squares"],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        harmonic.to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
        inharmonic.to_excel(writer, sheet_name="Inharmonic Spectrum", index=False)
        subbass.to_excel(writer, sheet_name="Sub-bass band", index=False)
        metadata.to_excel(writer, sheet_name="Analysis_Metadata", index=False)
        inharm_fit.to_excel(writer, sheet_name="Inharmonicity_Fit", index=False)


def test_final_validation_summary_contains_required_fields(tmp_path: Path) -> None:
    _write_note_workbook(tmp_path / "A3" / "spectral_analysis.xlsx")
    _write_note_workbook(tmp_path / "A6" / "spectral_analysis.xlsx")

    out_xlsx = tmp_path / "compiled.xlsx"
    compile_metrics.compile_density_metrics_with_pca(
        folder_path=tmp_path,
        output_path=out_xlsx,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
        harmonic_weight=0.8260033912117578,
        inharmonic_weight=0.12223562779874778,
        subbass_weight=0.051760980989494436,
    )
    summary = pd.read_excel(out_xlsx, sheet_name="Validation_Summary")
    assert not summary.empty
    required_fields = {
        "comparability_profile",
        "density_weights_source",
        "phase2_harmonic_weight",
        "phase2_inharmonic_weight",
        "phase2_subbass_weight",
        "tier_consistency_status_summary",
        "inharmonicity_B_mean",
        "inharmonicity_B_max",
        "inharmonicity_B_notes_above_1e-5",
        "obs_wS_artifact_count",
        "obs_wS_artifact_notes",
        "mir_descriptors_available_summary",
    }
    assert required_fields.issubset(set(summary["field"].astype(str)))
