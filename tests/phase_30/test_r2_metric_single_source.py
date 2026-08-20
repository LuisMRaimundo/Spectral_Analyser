"""R2 — one EWSD / core_H at the fixed window."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_integrity import validate_metric_single_source
from tools.canonical_note_metrics import (
    METRIC_PATHS,
    core_ratios_from_component_his,
    read_metrics_map,
    stamp_stage1_ewsd,
    values_agree,
)
from verify_export import inspect_workbook_invariants


def _write_clean_tone_workbook(path: Path, *, note: str = "A4") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    harmonic = pd.DataFrame(
        {
            "Harmonic Number": list(range(1, 9)),
            "Frequency (Hz)": [440.0 * n for n in range(1, 9)],
            "Amplitude_raw": [0.5 ** (n - 1) for n in range(1, 9)],
            "Magnitude (dB)": [0.0] + [-6.0 * n for n in range(1, 8)],
            "include_for_density": [True] * 8,
        }
    )
    inharmonic = pd.DataFrame(
        {
            "Frequency (Hz)": [123.0],
            "Amplitude_raw": [1e-9],
            "Magnitude (dB)": [-180.0],
        }
    )
    metrics = pd.DataFrame(
        {
            "Note": [note],
            "weight_function": ["log"],
            "component_harmonic_energy_ratio": [1.0],
            "component_inharmonic_energy_ratio": [0.0],
            "component_subbass_energy_ratio": [0.0],
            "core_harmonic_energy_ratio": [1.0],
            "core_residual_energy_ratio": [0.0],
            "core_subbass_energy_ratio": [0.0],
            "pure_observation_w_h": [1.0],
            "pure_observation_w_i": [0.0],
            "pure_observation_w_s": [0.0],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        harmonic.to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
        inharmonic.to_excel(writer, sheet_name="Inharmonic Spectrum", index=False)
        metrics.to_excel(writer, sheet_name="Metrics", index=False)


def test_metric_paths_table_covers_ewsd_and_core() -> None:
    names = {row["path"] for row in METRIC_PATHS}
    assert "stage1_ewsd" in names
    assert "stage3_ewsd" in names
    assert "stage1_core_h" in names
    assert "stage3_core_h" in names
    assert "diagnostic_ewsd_alias" in names


def test_core_ratios_from_component_his() -> None:
    out = core_ratios_from_component_his(0.80, 0.15, 0.05)
    assert out["core_harmonic_energy_ratio"] == pytest.approx(0.80)
    assert out["core_residual_energy_ratio"] == pytest.approx(0.15)
    assert out["core_subbass_energy_ratio"] == pytest.approx(0.05)


def test_validate_metric_single_source_fail_closed() -> None:
    ok = validate_metric_single_source(
        {
            "core_harmonic_energy_ratio": 1.0,
            "component_harmonic_energy_ratio": 1.0,
            "EWSD_score_acoustic_balanced": 12.0,
        },
        stage3={"EWSD_score_acoustic_balanced": 12.0, "core_harmonic_energy_ratio": 1.0},
    )
    assert ok["ok"] is True
    bad = validate_metric_single_source(
        {
            "core_harmonic_energy_ratio": 0.05,
            "component_harmonic_energy_ratio": 1.0,
            "EWSD_score_acoustic_balanced": 8.0,
        },
        stage3={"EWSD_score_acoustic_balanced": 12.0, "core_harmonic_energy_ratio": 1.0},
    )
    assert bad["ok"] is False
    assert "core_H!=component_H" in bad["conflicts"]
    assert "stage1_ewsd!=stage3_ewsd" in bad["conflicts"]
    assert bad["failures"].startswith("metric_single_source:")


def test_planted_clean_tone_stage1_equals_stage3(tmp_path: Path) -> None:
    wb = tmp_path / "A4" / "spectral_analysis.xlsx"
    _write_clean_tone_workbook(wb)
    stamped = stamp_stage1_ewsd(wb)
    assert stamped["ok"] is True
    metrics = read_metrics_map(wb)
    assert float(metrics["core_harmonic_energy_ratio"]) >= 0.99
    from tools.canonical_note_metrics import compute_stage3_ewsd_row

    s3 = compute_stage3_ewsd_row(wb.parent)
    assert not s3.empty
    s3_ewsd = float(s3.iloc[0]["ewsd_score_acoustic_balanced"])
    assert values_agree(metrics["EWSD_score_acoustic_balanced"], s3_ewsd)
    inv = inspect_workbook_invariants(wb)
    assert inv["metric_single_source"]["ok"] is True
    assert inv["ok"] is True


def test_live_synthetic_stage1_equals_stage3_at_fixed_window(tmp_path: Path) -> None:
    """B1 synthetic through Stage-1 Metrics and Stage-3 SDM at 8192/1024."""
    from tools.r1_stage3_b1 import _run_one, write_synth_wav

    wav = write_synth_wav(tmp_path / "synth_a4.wav", f0=440.0, sec=4.0)
    dest = tmp_path / "run"
    row = _run_one(wav, dest, 8192, 1024)
    if int(row.get("exit_code", 1)) != 0:
        pytest.fail(str(row.get("error") or row))
    research = dest / "compiled_density_metrics_research.xlsx"
    if not research.is_file():
        pytest.fail(f"missing Stage-3 workbook: {row}")
    s3 = pd.read_excel(research, sheet_name="Spectral_Density_Metrics").iloc[0]
    wbs = list(dest.rglob("spectral_analysis.xlsx"))
    assert wbs, "Stage-1 workbook missing"
    metrics = read_metrics_map(wbs[0])
    assert float(metrics["core_harmonic_energy_ratio"]) >= 0.99
    assert values_agree(
        metrics["core_harmonic_energy_ratio"],
        s3.get("core_harmonic_energy_ratio"),
    )
    assert values_agree(
        metrics.get("EWSD_score_acoustic_balanced"),
        s3.get("EWSD_score_acoustic_balanced"),
    )


def test_verify_export_flags_core_h_split(tmp_path: Path) -> None:
    path = tmp_path / "split.xlsx"
    metrics = pd.DataFrame(
        {
            "Note": ["A4"],
            "core_harmonic_energy_ratio": [0.05],
            "component_harmonic_energy_ratio": [1.0],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        metrics.to_excel(writer, sheet_name="Metrics", index=False)
    inv = inspect_workbook_invariants(path)
    assert inv["ok"] is False
    assert "metric_single_source" in inv["failures"]
