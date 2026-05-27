from __future__ import annotations

from pathlib import Path

import pandas as pd

import compile_metrics
import pipeline_orchestrator_gui as pog
from tools import export_research_density_workbook as research_export


def _write_min_note_workbook(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    harmonic = pd.DataFrame(
        {
            "Frequency (Hz)": [220.0, 440.0],
            "Amplitude_raw": [1.0, 0.8],
            "Power_raw": [1.0, 0.64],
            "include_for_density": [True, True],
        }
    )
    inharmonic = pd.DataFrame(
        {
            "Frequency (Hz)": [333.0],
            "Amplitude_raw": [0.2],
            "Power_raw": [0.04],
        }
    )
    subbass = pd.DataFrame(
        {
            "Frequency (Hz)": [55.0],
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
                "inharmonicity_model_applied",
            ],
            "Value": [
                compile_metrics.EXPECTED_ANALYSIS_SCHEMA_VERSION,
                0.8,
                0.15,
                0.05,
                "true",
            ],
        }
    )
    # Mirror current real-run short naming in per-note fit sheet.
    inharm_fit = pd.DataFrame(
        {
            "inharmonicity_coefficient_B": [2.5e-6],
            "fit_residual_std_cents": [1.2],
            "fit_status": ["ok"],
            "method": ["fletcher_1962_stiff_string_least_squares"],
        }
    )
    metrics = pd.DataFrame(
        {
            "pure_observation_w_h": [0.70],
            "pure_observation_w_i": [0.112],
            "pure_observation_w_s": [0.188],
            "n_fft": [4096],
            "harmonic_energy_sum": [1.0],
            "subbass_energy_sum": [0.01],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        harmonic.to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
        inharmonic.to_excel(writer, sheet_name="Inharmonic Spectrum", index=False)
        subbass.to_excel(writer, sheet_name="Sub-bass band", index=False)
        metadata.to_excel(writer, sheet_name="Analysis_Metadata", index=False)
        metrics.to_excel(writer, sheet_name="Metrics", index=False)
        inharm_fit.to_excel(writer, sheet_name="Inharmonicity_Fit", index=False)


def test_inharmonicity_fit_sheet_short_names_reach_density_metrics(tmp_path: Path) -> None:
    _write_min_note_workbook(tmp_path / "A4" / "spectral_analysis.xlsx")
    out_xlsx = tmp_path / "compiled.xlsx"
    compile_metrics.compile_density_metrics_with_pca(
        folder_path=tmp_path,
        output_path=out_xlsx,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
    )
    dm = pd.read_excel(out_xlsx, sheet_name="Density_Metrics")
    row = dm.iloc[0]
    assert abs(float(row["inharmonicity_coefficient_B"]) - 2.5e-6) < 1e-12
    assert abs(float(row["inharmonicity_fit_residual_std_cents"]) - 1.2) < 1e-12
    assert str(row["inharmonicity_fit_status"]).strip() == "ok"
    assert "fletcher_1962_stiff_string_least_squares" in str(row["inharmonicity_fit_method"]).strip()
    assert str(row["inharmonicity_model_applied"]).strip().lower() == "true"
    assert str(row["inharmonicity_fit_source"]).strip() == "per_note_inharmonicity_fit_sheet"


def test_inharmonicity_model_applied_is_nonblank_and_boolean_semantic(tmp_path: Path) -> None:
    # No explicit model_applied metadata -> extractor must still emit nonblank semantic.
    _write_min_note_workbook(tmp_path / "A4" / "spectral_analysis.xlsx")
    wb = tmp_path / "A4" / "spectral_analysis.xlsx"
    with pd.ExcelFile(wb) as xf:
        harmonic = xf.parse("Harmonic Spectrum")
        inharmonic = xf.parse("Inharmonic Spectrum")
        subbass = xf.parse("Sub-bass band")
        meta = xf.parse("Analysis_Metadata")
        metrics = xf.parse("Metrics")
        inharm_fit = xf.parse("Inharmonicity_Fit")
    meta = meta[meta["Parameter"].astype(str).str.lower() != "inharmonicity_model_applied"]
    with pd.ExcelWriter(wb, engine="openpyxl") as writer:
        harmonic.to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
        inharmonic.to_excel(writer, sheet_name="Inharmonic Spectrum", index=False)
        subbass.to_excel(writer, sheet_name="Sub-bass band", index=False)
        meta.to_excel(writer, sheet_name="Analysis_Metadata", index=False)
        metrics.to_excel(writer, sheet_name="Metrics", index=False)
        inharm_fit.to_excel(writer, sheet_name="Inharmonicity_Fit", index=False)

    out_xlsx = tmp_path / "compiled_model_applied.xlsx"
    compile_metrics.compile_density_metrics_with_pca(
        folder_path=tmp_path,
        output_path=out_xlsx,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
    )
    dm = pd.read_excel(out_xlsx, sheet_name="Density_Metrics")
    v = str(dm.iloc[0]["inharmonicity_model_applied"]).strip().lower()
    assert v in {"true", "false", "not_available"}
    assert v != ""


def test_obs_ws_artifact_high_obs_with_negligible_energy_is_flagged() -> None:
    diag = pog.compute_obs_ws_artifact_diagnostics(
        pure_observation_w_h=0.70,
        pure_observation_w_i=0.112,
        pure_observation_w_s=0.188,
        component_subbass_energy_ratio=0.0,
        harmonic_energy_sum=100.0,
        subbass_energy_sum=float("nan"),
        subbass_energy_sum_tier_normalized=float("nan"),
    )
    assert diag["obs_wS_artifact_flag"] is True
    assert diag["subbass_component_interpretation"] == "model_density_residual_not_physical_subbass_energy"
    assert "obs_wS_above_0p05" in str(diag["obs_wS_artifact_reason"])


def test_phase1_diag_populates_subbass_energy_sum_tier_normalized_from_compile_path(tmp_path: Path) -> None:
    wb = tmp_path / "A3" / "spectral_analysis.xlsx"
    _write_min_note_workbook(wb)
    diag = pog.RobustOrchestratorApp._extract_note_density_feedback_diagnostics(
        object(),
        wb,
    )
    assert "subbass_energy_sum_tier_normalized" in diag
    assert pd.notna(diag["subbass_energy_sum_tier_normalized"])
    assert float(diag["subbass_energy_sum_tier_normalized"]) > 0.0
    assert str(diag.get("subbass_energy_sum_tier_normalized_source", "")).strip() != ""


def test_filename_inference_clar_ord_ff_not_ambiguous(tmp_path: Path) -> None:
    merged = pd.DataFrame(
        {
            "source_file_name": ["Clar.-ord-D3-ff-N-T31u_Sustains.wav"],
            "Note": ["D3"],
        }
    )
    warnings: list[str] = []
    inst, dyn, tech, status, reason = research_export._build_instrument_dynamic_series(
        merged=merged,
        compiled_workbook=tmp_path / "compiled_density_metrics.xlsx",
        warnings=warnings,
        meta=research_export.ResearchExportMetadata(),
    )
    assert str(inst.iloc[0]).strip().lower() == "clarinet"
    assert str(dyn.iloc[0]).strip().lower() == "ff"
    assert str(tech.iloc[0]).strip().lower() == "ord"
    assert str(status.iloc[0]).strip() == "ok"
    assert str(reason.iloc[0]).strip() == ""
    assert warnings == []


def test_research_export_infers_from_per_note_processing_metadata_source_file_name(tmp_path: Path) -> None:
    compiled = tmp_path / "compiled_density_metrics.xlsx"
    density = pd.DataFrame(
        {
            "Note": ["D3"],
            "density_metric_raw": [0.42],
            "density_metric_normalized": [1.0],
            "harmonic_density_sum": [1.0],
            "inharmonic_density_sum": [0.1],
            "subbass_density_sum": [0.01],
            "component_harmonic_energy_ratio": [0.85],
            "component_inharmonic_energy_ratio": [0.14],
            "component_subbass_energy_ratio": [0.01],
            "f0_final_hz": [146.83],
            "f0_source": ["nominal_guided"],
            "f0_final_source": ["nominal_guided"],
            "acoustic_f0_status": ["nominal_guided_acoustically_verified"],
            "f0_fit_accepted": [True],
        }
    )
    pnp = pd.DataFrame(
        {
            "Note": ["D3"],
            "source_file_name": ["Clar.-ord-D3-ff-N-T31u_Sustains.wav"],
        }
    )
    meta = pd.DataFrame({"analysis_version": ["test"], "weight_function": ["log"]})
    with pd.ExcelWriter(compiled, engine="openpyxl") as writer:
        density.to_excel(writer, sheet_name="Density_Metrics", index=False)
        pnp.to_excel(writer, sheet_name="Per_Note_Processing_Metadata", index=False)
        meta.to_excel(writer, sheet_name="Analysis_Metadata", index=False)

    output = tmp_path / "compiled_density_metrics_research.xlsx"
    out = research_export.export_research_workbook(
        input_path=compiled,
        output_path=output,
        overwrite=True,
        no_charts=True,
    )
    sdm = pd.read_excel(out, sheet_name="Spectral_Density_Metrics")
    row = sdm.iloc[0]
    assert str(row["Instrument"]).strip().lower() == "clarinet"
    assert str(row["Dynamic"]).strip().lower() == "ff"
    assert str(row["Technique"]).strip().lower() == "ord"


def test_validation_summary_uses_phase1_obs_ws_artifact_csv(tmp_path: Path) -> None:
    density_df = pd.DataFrame(
        {
            "Note": ["A3", "A6", "C4"],
            "density_weights_source": ["phase2_corpus_profile"] * 3,
            "inharmonicity_coefficient_B": [1e-6, 2e-6, 3e-6],
        }
    )
    phase1 = pd.DataFrame(
        {
            "note": ["A3", "A6", "C4"],
            "obs_wS_artifact_flag": [True, True, False],
        }
    )
    phase1_path = tmp_path / "phase1_discovered_density_profiles.csv"
    phase1.to_csv(phase1_path, index=False)

    summary = compile_metrics._build_phase7_final_validation_summary_sheet(
        density_df,
        harmonic_weight=0.8,
        inharmonic_weight=0.15,
        subbass_weight=0.05,
        phase1_history_csv_path=phase1_path,
    )
    as_map = {
        str(r["field"]): str(r["value"])
        for _, r in summary.iterrows()
    }
    assert as_map["obs_wS_artifact_count"] == "2"
    assert as_map["obs_wS_artifact_notes"] == "A3;A6"
