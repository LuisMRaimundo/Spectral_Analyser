from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from constants import (
    CI_BASIS_INDEPENDENT_FRAME_MIN,
    DENSITY_CI_DEFAULT_ON,
    UNCERTAINTY_REL_FLAG_PCT,
)
from density_uncertainty import (
    bootstrap_effective_component_density,
    build_uncertainty_summary,
    ci_basis_counts,
)
from metric_contract import get_metric_definition
from publication_chart_policy import (
    ci_columns_for_metric,
    compose_chart_title,
    write_stage3_ewsd_ci_chart,
)
from validated_partials import participation_ratio_from_amplitudes


def test_density_ci_is_on_by_default() -> None:
    assert DENSITY_CI_DEFAULT_ON is True
    assert UNCERTAINTY_REL_FLAG_PCT == 25.0
    assert CI_BASIS_INDEPENDENT_FRAME_MIN == 10


def test_epd_bootstrap_brackets_unchanged_f047_point() -> None:
    amps = [1.0, 0.7, 0.5, 0.35, 0.2, 0.12, 0.08, 0.05]
    point = participation_ratio_from_amplitudes(amps)
    res = bootstrap_effective_component_density(amps, n_boot=2000, seed=1)
    assert res["point_estimate"] == pytest.approx(point, rel=1e-12)
    assert res["ci_low"] <= point <= res["ci_high"]
    assert res["ci_basis_partial_count"] == len(amps)
    assert res["relative_uncertainty"] >= 0.0


def test_ci_basis_flags_fewer_than_ten_independent_frames() -> None:
    short = ci_basis_counts(independent_frame_count=9, partial_count=8)
    assert short["ci_basis_frame_count"] == 9.0
    assert short["ci_basis_partial_count"] == 8.0
    assert short["ci_basis_frames_insufficient"] is True
    ok = ci_basis_counts(independent_frame_count=10, partial_count=8)
    assert ok["ci_basis_frames_insufficient"] is False


def test_uncertainty_summary_flags_rel_above_25_pct() -> None:
    rows = [
        {
            "Note": "A2",
            "note_density_final": 1.0,
            "note_density_final_rel_uncertainty": 0.30,
            "note_effective_component_density": 3.8,
            "note_effective_component_density_rel_uncertainty": 0.05,
            "EWSD_score_acoustic_balanced": 0.5,
            "EWSD_score_acoustic_balanced_rel_uncertainty": 0.10,
            "ci_basis_frame_count": 5,
            "ci_basis_partial_count": 8,
        }
    ]
    df = build_uncertainty_summary(rows)
    assert set(df["metric"]) == {
        "note_density_final",
        "note_effective_component_density",
        "EWSD_score_acoustic_balanced",
    }
    ndf = df[df["metric"] == "note_density_final"].iloc[0]
    assert bool(ndf["uncertainty_flag"]) is True
    assert float(ndf["rel_uncertainty_pct"]) == pytest.approx(30.0)
    assert bool(ndf["ci_basis_frames_insufficient"]) is True
    epd = df[df["metric"] == "note_effective_component_density"].iloc[0]
    assert bool(epd["uncertainty_flag"]) is False


def test_chart_title_carries_note_run_commit_version() -> None:
    title = compose_chart_title(
        "Spectral_Density_Metrics",
        "EWSD_score_acoustic_balanced",
        status="canonical",
        note_tag="tuba",
        run_id="stage3",
        commit="abc1234",
        analysis_version="4.1.0",
    )
    assert title.startswith("Spectral_Density_Metrics — EWSD_score_acoustic_balanced — canonical")
    assert "tuba" in title
    assert "stage3" in title
    assert "abc1234" in title
    assert "4.1.0" in title
    assert ci_columns_for_metric("EWSD_score_acoustic_balanced") == (
        "EWSD_score_acoustic_balanced_ci_low",
        "EWSD_score_acoustic_balanced_ci_high",
    )
    assert ci_columns_for_metric("note_effective_component_density") == (
        "note_effective_component_density_ci_low",
        "note_effective_component_density_ci_high",
    )


def test_stage3_ewsd_ci_chart_writes_png(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    frame = pd.DataFrame(
        {
            "Note": ["A2", "Bb2"],
            "EWSD_score_acoustic_balanced": [0.40, 0.55],
            "EWSD_score_acoustic_balanced_ci_low": [0.30, 0.45],
            "EWSD_score_acoustic_balanced_ci_high": [0.50, 0.65],
        }
    )
    path = tmp_path / "ewsd_acoustic_balanced_ci.png"
    out = write_stage3_ewsd_ci_chart(
        frame, path, note_tag="tuba", run_id="stage3", analysis_version="4.1.0"
    )
    assert out is not None
    assert Path(out).is_file()
    assert Path(out).stat().st_size > 0


def _write_a2_like_note_workbook(path: Path, *, independent_frames: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    amps = [1.00, 0.72, 0.51, 0.36, 0.24, 0.16, 0.10, 0.07]
    harmonic = pd.DataFrame(
        {
            "Harmonic Number": list(range(1, 9)),
            "Frequency (Hz)": [110.0 * n for n in range(1, 9)],
            "Amplitude_raw": amps,
            "Magnitude (dB)": [20.0 * np.log10(a) for a in amps],
            "include_for_density": [True] * 8,
        }
    )
    inharmonic = pd.DataFrame(
        {"Frequency (Hz)": [], "Amplitude_raw": [], "Magnitude (dB)": []}
    )
    subbass = pd.DataFrame(
        {"Frequency (Hz)": [], "Amplitude_raw": [], "Magnitude (dB)": []}
    )
    meta = pd.DataFrame(
        {
            "sustain_frame_count": [42],
            "sustain_frame_count_independent": [independent_frames],
            "frame_duration_s": [0.0232],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        harmonic.to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
        inharmonic.to_excel(writer, sheet_name="Inharmonic Spectrum", index=False)
        subbass.to_excel(writer, sheet_name="Sub-bass band", index=False)
        meta.to_excel(writer, sheet_name="Per_Note_Processing_Metadata", index=False)


def test_a2_like_epd_ci_reported_and_short_frames_flagged(tmp_path: Path) -> None:
    from compile_metrics import _energy_distribution_density

    path = tmp_path / "A2" / "spectral_analysis.xlsx"
    _write_a2_like_note_workbook(path, independent_frames=5.0)
    out = _energy_distribution_density(path)
    point = float(out["note_effective_component_density"])
    assert np.isfinite(point) and point > 1.0
    assert float(out["note_effective_component_density_ci_low"]) <= point
    assert point <= float(out["note_effective_component_density_ci_high"])
    assert float(out["ci_basis_partial_count"]) == 8.0
    assert float(out["ci_basis_frame_count"]) == 5.0
    assert bool(out["ci_basis_frames_insufficient"]) is True
    assert get_metric_definition("note_effective_component_density_ci") is not None
    assert get_metric_definition("ci_basis_frame_count") is not None
    assert get_metric_definition("ci_basis_partial_count") is not None


def test_research_export_writes_uncertainty_summary_and_ci_chart(tmp_path: Path) -> None:
    from tests.phase_11.test_research_export_includes_ewsd import (
        _write_compiled_workbook,
        _write_per_note_workbook,
    )
    from tools import export_research_density_workbook as research_export

    _write_per_note_workbook(tmp_path / "D3" / "spectral_analysis.xlsx", note="D3")
    compiled = tmp_path / "compiled_density_metrics.xlsx"
    _write_compiled_workbook(compiled, note="D3")
    meta = pd.read_excel(compiled, sheet_name="Analysis_Metadata")
    density = pd.read_excel(compiled, sheet_name="Density_Metrics")
    density["note_effective_component_density"] = 2.4
    density["note_effective_component_density_ci_low"] = 2.0
    density["note_effective_component_density_ci_high"] = 2.8
    density["note_effective_component_density_rel_uncertainty"] = 0.08
    density["ci_basis_frame_count"] = 5
    density["ci_basis_partial_count"] = 6
    density["ci_basis_frames_insufficient"] = True
    with pd.ExcelWriter(compiled, engine="openpyxl") as writer:
        density.to_excel(writer, sheet_name="Density_Metrics", index=False)
        meta.to_excel(writer, sheet_name="Analysis_Metadata", index=False)

    output = tmp_path / "compiled_density_metrics_research.xlsx"
    research_export.export_research_workbook(
        input_path=compiled,
        output_path=output,
        overwrite=True,
        no_charts=False,
        include_ewsd=True,
    )
    sheets = set(pd.ExcelFile(output).sheet_names)
    assert "Uncertainty_Summary" in sheets
    uq = pd.read_excel(output, sheet_name="Uncertainty_Summary")
    assert "ci_basis_frames_insufficient" in uq.columns
    assert bool(uq["ci_basis_frames_insufficient"].iloc[0]) is True
    sdm = pd.read_excel(output, sheet_name="Spectral_Density_Metrics")
    assert "note_effective_component_density_ci_low" in sdm.columns
    chart = output.parent / "ewsd_acoustic_balanced_ci.png"
    if chart.is_file():
        assert chart.stat().st_size > 0
    else:
        pytest.importorskip("matplotlib")
        pytest.fail("Stage 3 EWSD CI chart was not written")
