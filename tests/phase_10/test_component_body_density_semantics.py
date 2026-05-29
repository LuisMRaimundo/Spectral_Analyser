from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from compile_metrics import extract_density_component_sum
from tests.phase_7_1b.helpers import run_stage1_synthetic_notes


def _write_mock_per_note_workbook(path: Path, *, include_cloud: bool) -> None:
    harmonic_rows = [
        {"Harmonic Number": 1, "Frequency (Hz)": 440.0, "Power_raw": 10.0, "include_for_density": True},
        {"Harmonic Number": 2, "Frequency (Hz)": 880.0, "Power_raw": 20.0, "include_for_density": True},
        {"Harmonic Number": 3, "Frequency (Hz)": 1320.0, "Power_raw": 30.0, "include_for_density": True},
        {"Harmonic Number": 12, "Frequency (Hz)": 5280.0, "Power_raw": 999.0, "include_for_density": True},
    ]
    if include_cloud:
        for i in range(150):
            harmonic_rows.append(
                {
                    "Harmonic Number": np.nan,
                    "Frequency (Hz)": 200.0 + float(i),
                    "Power_raw": 20000.0,
                    "include_for_density": False,
                }
            )
    inharmonic_rows = [
        {"Frequency (Hz)": 1500.0, "Power_raw": 5.0},
        {"Frequency (Hz)": 2400.0, "Power_raw": 7.0},
        {"Frequency (Hz)": 6400.0, "Power_raw": 999.0},
    ]
    subbass_rows = [
        {"Frequency (Hz)": 70.0, "Power_raw": 2.0},
        {"Frequency (Hz)": 5200.0, "Power_raw": 999.0},
    ]
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(harmonic_rows).to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
        pd.DataFrame(inharmonic_rows).to_excel(writer, sheet_name="Inharmonic Spectrum", index=False)
        pd.DataFrame(subbass_rows).to_excel(writer, sheet_name="Sub-bass band", index=False)


def test_component_body_density_ignores_nonincluded_fft_cloud(tmp_path: Path) -> None:
    wb_plain = tmp_path / "plain.xlsx"
    wb_cloud = tmp_path / "cloud.xlsx"
    _write_mock_per_note_workbook(wb_plain, include_cloud=False)
    _write_mock_per_note_workbook(wb_cloud, include_cloud=True)

    body_ceiling_hz = 4800.0
    h_plain = extract_density_component_sum(wb_plain, "Harmonic Spectrum", "power", max_frequency_hz=body_ceiling_hz)
    i_plain = extract_density_component_sum(wb_plain, "Inharmonic Spectrum", "power", max_frequency_hz=body_ceiling_hz)
    s_plain = extract_density_component_sum(wb_plain, "Sub-bass band", "power", max_frequency_hz=body_ceiling_hz)
    h_cloud = extract_density_component_sum(wb_cloud, "Harmonic Spectrum", "power", max_frequency_hz=body_ceiling_hz)

    assert float(h_plain["D"]) == pytest.approx(60.0)
    assert float(i_plain["D"]) == pytest.approx(12.0)
    assert float(s_plain["D"]) == pytest.approx(2.0)
    expected_density = 0.5 * 60.0 + 0.3 * 12.0 + 0.2 * 2.0
    assert float(0.5 * h_plain["D"] + 0.3 * i_plain["D"] + 0.2 * s_plain["D"]) == pytest.approx(expected_density)
    assert float(h_cloud["D"]) == pytest.approx(float(h_plain["D"]))


def test_harmonic_component_sum_matches_included_harmonic_rows(tmp_path: Path) -> None:
    workbooks = run_stage1_synthetic_notes(tmp_path, notes=[("A4", 440.0)])
    wb = workbooks[0]
    harm = pd.read_excel(wb, sheet_name="Harmonic Spectrum")
    metrics = pd.read_excel(wb, sheet_name="Metrics").iloc[0]
    body_ceiling_hz = float(pd.to_numeric(metrics.get("body_density_frequency_ceiling_hz"), errors="coerce"))
    mask = harm["include_for_density"].astype(bool) & (pd.to_numeric(harm["Frequency (Hz)"], errors="coerce") <= body_ceiling_hz)
    expected = pd.to_numeric(harm.loc[mask, "Power_raw"], errors="coerce").fillna(0.0).sum()
    assert float(metrics["harmonic_component_energy_sum_body_ceiling"]) == pytest.approx(float(expected), rel=1e-6, abs=1e-9)


def test_inharmonic_component_sum_matches_inharmonic_sheet_candidates(tmp_path: Path) -> None:
    workbooks = run_stage1_synthetic_notes(tmp_path, notes=[("A4", 440.0)])
    wb = workbooks[0]
    inharm = pd.read_excel(wb, sheet_name="Inharmonic Spectrum")
    metrics = pd.read_excel(wb, sheet_name="Metrics").iloc[0]
    if inharm.empty:
        expected = 0.0
    else:
        body_ceiling_hz = float(pd.to_numeric(metrics.get("body_density_frequency_ceiling_hz"), errors="coerce"))
        mask = pd.to_numeric(inharm["Frequency (Hz)"], errors="coerce") <= body_ceiling_hz
        expected = pd.to_numeric(inharm.loc[mask, "Power_raw"], errors="coerce").fillna(0.0).sum()
    assert float(metrics["inharmonic_component_energy_sum_body_ceiling"]) == pytest.approx(float(expected), rel=1e-6, abs=1e-9)


def test_subbass_component_sum_matches_subbass_policy_rows(tmp_path: Path) -> None:
    workbooks = run_stage1_synthetic_notes(tmp_path, notes=[("A4", 440.0)])
    wb = workbooks[0]
    sub = pd.read_excel(wb, sheet_name="Sub-bass band")
    metrics = pd.read_excel(wb, sheet_name="Metrics").iloc[0]
    if sub.empty:
        expected = 0.0
    else:
        accepted = pd.Series(True, index=sub.index)
        if "Classification_Level" in sub.columns:
            accepted = accepted & ~sub["Classification_Level"].astype(str).str.contains(
                "diagnostic", case=False, na=False
            )
        if "Acoustic_Interpretation_Status" in sub.columns:
            accepted = accepted & sub["Acoustic_Interpretation_Status"].astype(str).str.contains(
                "accepted|candidate|validated",
                case=False,
                na=False,
            )
        expected = pd.to_numeric(sub.loc[accepted, "Power_raw"], errors="coerce").fillna(0.0).sum()
    assert float(metrics["subbass_component_energy_sum"]) == pytest.approx(float(expected), rel=1e-6, abs=1e-9)


def test_strict_harmonic_peaks_matches_density_include_mask(tmp_path: Path) -> None:
    workbooks = run_stage1_synthetic_notes(tmp_path, notes=[("A4", 440.0)])
    wb = workbooks[0]
    harm = pd.read_excel(wb, sheet_name="Harmonic Spectrum")
    strict = pd.read_excel(wb, sheet_name="Strict_Harmonic_Peaks")
    included = harm.loc[harm["include_for_density"].astype(bool)].copy()
    assert len(strict) == len(included)
    assert set(np.round(pd.to_numeric(strict["Frequency (Hz)"], errors="coerce"), 6)) == set(
        np.round(pd.to_numeric(included["Frequency (Hz)"], errors="coerce"), 6)
    )

