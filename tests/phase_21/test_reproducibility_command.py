from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from constants import DENSITY_WEIGHT_FUNCTION_DEFAULT, REEXPORT_REL_DELTA_FLAG_PCT
from run_manifest import (
    MANIFEST_SCHEMA_VERSION,
    STAGE3_SCORE_COLUMN,
    build_run_manifest,
    constants_hash,
    default_parameter_profile_id,
    discover_corpus_audio,
    parse_stages,
    write_run_manifest,
)
from run_orchestrator import build_parser
from tools.reexport_corpus import (
    ANALISE_3_BASELINE,
    annotate_diff_with_floor_rows,
    collect_floor_row_explanations,
    diff_stage3_series,
    load_stage3_series,
    summarize_diff,
)


def test_parse_stages_accepts_csv_and_rejects_unknown() -> None:
    assert parse_stages("1,2,3") == [1, 2, 3]
    assert parse_stages("2,3") == [2, 3]
    assert parse_stages(None) == [1, 2, 3]
    try:
        parse_stages("1,4")
    except ValueError:
        return
    raise AssertionError("stage 4 must be rejected")


def test_cli_exposes_corpus_out_stages_figures() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["--corpus", "D:/audio", "--out", "out", "--stages", "1,2,3", "--figures"]
    )
    assert args.corpus == "D:/audio"
    assert args.out == "out"
    assert args.stages == "1,2,3"
    assert args.figures is True
    assert args.weight_function == DENSITY_WEIGHT_FUNCTION_DEFAULT
    assert args.fft_policy == "fixed"


def test_discover_corpus_audio_finds_aif_and_wav(tmp_path: Path) -> None:
    (tmp_path / "IOWA_Tub.pp.A2_SustainStable.aif").write_bytes(b"aif")
    (tmp_path / "note.wav").write_bytes(b"wav")
    (tmp_path / "readme.txt").write_text("x", encoding="utf-8")
    found = {p.name for p in discover_corpus_audio(tmp_path)}
    assert found == {"IOWA_Tub.pp.A2_SustainStable.aif", "note.wav"}


def test_constants_hash_is_stable() -> None:
    first = constants_hash()
    second = constants_hash()
    assert first == second
    assert len(first) == 64


def test_run_manifest_contains_required_fields(tmp_path: Path) -> None:
    audio = tmp_path / "C2.wav"
    audio.write_bytes(b"RIFF")
    payload = build_run_manifest(
        corpus=tmp_path,
        out_dir=tmp_path / "out",
        stages=[1, 2, 3],
        figures=True,
        weight_function="log",
        input_files=[audio],
        wall_time_s=1.25,
    )
    path = write_run_manifest(tmp_path / "out", payload)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    for key in (
        "schema_version",
        "code_commit",
        "package_version",
        "analysis_version",
        "constants_hash",
        "analysis_parameter_profile_id",
        "input_files",
        "wall_time_s",
        "export_schema_version",
    ):
        assert key in loaded
    assert loaded["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert loaded["weight_function"] == "log"
    assert loaded["analysis_parameter_profile_id"] == default_parameter_profile_id("log")
    assert loaded["input_files"][0]["sha256"]
    assert loaded["wall_time_s"] == 1.25
    assert loaded["figures"] is True


def test_stage3_export_reads_stage1_from_search_root(tmp_path: Path) -> None:
    from tests.phase_11.test_research_export_includes_ewsd import (
        _write_compiled_workbook,
        _write_per_note_workbook,
    )
    from tools import export_research_density_workbook as research_export

    stage1 = tmp_path / "stage1"
    _write_per_note_workbook(stage1 / "D3" / "spectral_analysis.xlsx", note="D3")
    out = tmp_path / "out"
    out.mkdir()
    compiled = out / "compiled_density_metrics.xlsx"
    _write_compiled_workbook(compiled, note="D3")
    output = out / "compiled_density_metrics_research.xlsx"
    research_export.export_research_workbook(
        input_path=compiled,
        output_path=output,
        overwrite=True,
        no_charts=True,
        include_ewsd=True,
        analysis_root=stage1,
    )
    sdm = pd.read_excel(output, sheet_name="Spectral_Density_Metrics")
    assert "EWSD_score_acoustic_balanced" in sdm.columns
    assert pd.notna(sdm.iloc[0]["EWSD_score_acoustic_balanced"])


def test_readme_documents_reproducibility_command() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "--corpus" in readme
    assert "--out" in readme
    assert "--stages 1,2,3" in readme
    assert "--figures" in readme
    assert "run_manifest.json" in readme
    assert "reexport_corpus" in readme


def test_tuba_reexport_report_within_four_percent() -> None:
    report = Path("docs/validation/TUBA_PP_REEXPORT_DIFF.md").read_text(encoding="utf-8")
    payload = json.loads(
        Path("docs/validation/TUBA_PP_REEXPORT_DIFF.json").read_text(encoding="utf-8")
    )
    assert "Notes exceeding threshold: 0" in report
    assert payload["summary"]["n_compared"] == 37
    assert payload["summary"]["n_exceeding_threshold"] == 0
    assert float(payload["summary"]["max_abs_rel_delta_pct"]) < 4.0


def test_analise3_baseline_has_37_notes() -> None:
    series = load_stage3_series(ANALISE_3_BASELINE)
    assert len(series) == 37
    assert series.iloc[0]["Note"] == "C1"
    assert abs(float(series.loc[series["Note"] == "A2", STAGE3_SCORE_COLUMN].iloc[0]) - 19.9) < 1e-9


def test_stage3_diff_flags_notes_above_threshold() -> None:
    baseline = pd.DataFrame(
        {"Note": ["A2", "C1"], STAGE3_SCORE_COLUMN: [20.0, 100.0]}
    )
    current = pd.DataFrame(
        {"Note": ["A2", "C1"], STAGE3_SCORE_COLUMN: [20.2, 80.0]}
    )
    diff = diff_stage3_series(
        current, baseline, threshold_pct=REEXPORT_REL_DELTA_FLAG_PCT
    )
    by_note = {row["Note"]: row for _, row in diff.iterrows()}
    assert bool(by_note["A2"]["exceeds_threshold"]) is False
    assert bool(by_note["C1"]["exceeds_threshold"]) is True
    assert abs(float(by_note["C1"]["rel_delta_pct"]) + 20.0) < 1e-9


def test_floor_row_explanations_list_cfar_margin(tmp_path: Path) -> None:
    note_dir = tmp_path / "A2"
    note_dir.mkdir()
    path = note_dir / "spectral_analysis.xlsx"
    metrics = pd.DataFrame({"Note": ["A2"]})
    confirmed = pd.DataFrame(
        {
            "Frequency (Hz)": [12094.0, 12110.0],
            "inharmonic_status": ["rejected_floor", "rejected_floor"],
            "cfar_margin_db_i": [-3.4, -1.1],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        metrics.to_excel(writer, sheet_name="Metrics", index=False)
        confirmed.to_excel(
            writer, sheet_name="Confirmed_Inharmonic_Partials", index=False
        )
    explanations = collect_floor_row_explanations(tmp_path)
    assert len(explanations) == 1
    assert explanations[0]["Note"] == "A2"
    assert explanations[0]["floor_row_count"] == 2
    assert explanations[0]["cfar_margin_db_min"] == -3.4
    diff = pd.DataFrame(
        {
            "Note": ["A2"],
            "baseline": [19.9],
            "current": [18.0],
            "delta": [-1.9],
            "rel_delta_pct": [-9.5],
            "abs_rel_delta_pct": [9.5],
            "exceeds_threshold": [True],
        }
    )
    annotated = annotate_diff_with_floor_rows(diff, explanations)
    assert "removed floor rows=2" in str(annotated.iloc[0]["explanation"])
    assert "min CFAR margin=-3.40 dB" in str(annotated.iloc[0]["explanation"])
    summary = summarize_diff(annotated)
    assert summary["n_exceeding_threshold"] == 1
    assert summary["flagged_notes"][0]["floor_row_count"] == 2
