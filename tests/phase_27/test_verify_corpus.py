"""WP5 / P4 — verify_corpus, freeze runbook, package 4.3.0."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from analysis_provenance import resolve_package_version
from production_policy import default_parameter_profile_id
from run_manifest import build_run_manifest, write_run_manifest
from run_orchestrator import build_parser
from tools.reexport_corpus import _build_parser as reexport_parser
from tools.verify_corpus import (
    format_report,
    main as verify_corpus_main,
    parse_profile_id,
    verify_corpus,
)


def _write_compiled(
    path: Path,
    *,
    profile_id: str,
    notes: list[str] | None = None,
    fft_policy: str = "fixed",
    extra_profiles: list[str] | None = None,
    eligible: bool = True,
    degenerate: bool = False,
    rel_uncertainty: float | None = 0.12,
) -> None:
    notes = notes or ["A2"]
    profiles = extra_profiles or [profile_id] * len(notes)
    rows = {
        "Note": notes,
        "analysis_parameter_profile_id": profiles,
        "fft_policy": [fft_policy] * len(notes),
        "ewsd_primary_analysis_eligible": [eligible] * len(notes),
        "degenerate_partial_set": [degenerate] * len(notes),
        "EWSD_score_acoustic_balanced": [16.11] * len(notes),
        "EWSD_score_acoustic_balanced_rel_uncertainty": [rel_uncertainty] * len(notes),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(
            writer, sheet_name="Density_Metrics", index=False
        )


def _good_run(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    profile = default_parameter_profile_id("log")
    payload = build_run_manifest(
        corpus=tmp_path,
        out_dir=out,
        stages=[1, 2, 3],
        figures=True,
        weight_function="log",
        fft_policy="fixed",
        fixed_n_fft=8192,
        fixed_hop_length=1024,
        analysis_parameter_profile_id=profile,
    )
    write_run_manifest(out, payload)
    _write_compiled(out / "compiled_density_metrics.xlsx", profile_id=profile)
    return out


def test_package_version_is_4_3_0() -> None:
    pkg, source = resolve_package_version()
    assert source.startswith("pyproject.toml")
    assert pkg == "4.7.0"


def test_cli_still_defaults_to_fft_policy_fixed() -> None:
    orch = build_parser().parse_args(["--corpus", "D:/audio", "--out", "out"])
    assert orch.fft_policy == "fixed"
    assert orch.fixed_n_fft == 8192
    assert orch.fixed_hop_length == 1024
    rex = reexport_parser().parse_args(
        ["--stage1-root", "stage1", "--out", "out"]
    )
    assert rex.fft_policy == "fixed"
    assert rex.fixed_n_fft == 8192
    assert rex.fixed_hop_length == 1024


def test_run_manifest_records_production_fft_fields(tmp_path: Path) -> None:
    payload = build_run_manifest(
        corpus=tmp_path,
        out_dir=tmp_path / "out",
        stages=[1, 2, 3],
        weight_function="log",
    )
    assert payload["fft_policy"] == "fixed"
    assert payload["fixed_n_fft"] == 8192
    assert payload["fixed_hop_length"] == 1024
    assert payload["segment_policy"] == "sustain_primary_stable_diagnostic"
    assert payload["eligibility_policy"] == "1"
    tokens = parse_profile_id(payload["analysis_parameter_profile_id"])
    assert tokens["fft"] == "fixed"
    assert tokens["seg"] == "sustain_primary_stable_diagnostic"
    assert tokens["elig"] == "1"


def test_verify_corpus_accepts_planted_production_run(tmp_path: Path) -> None:
    out = _good_run(tmp_path)
    result = verify_corpus(out)
    assert result["ok"] is True
    assert result["comparable"] is True
    assert result["issues"] == []
    assert "fft=fixed" in result["analysis_parameter_profile_id"]
    report = format_report(result)
    assert "status: ok" in report
    assert verify_corpus_main([str(out)]) == 0


def test_verify_corpus_fails_without_manifest(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    result = verify_corpus(empty)
    assert result["ok"] is False
    assert any("missing run_manifest.json" in item for item in result["issues"])
    assert verify_corpus_main([str(empty)]) == 1


def test_verify_corpus_fails_adaptive_tier(tmp_path: Path) -> None:
    out = tmp_path / "adaptive"
    profile = (
        "wf=log|dst=runtime_configured|ceil=runtime_configured|"
        "fft=adaptive_tier|seg=sustain_primary_stable_diagnostic|elig=1"
    )
    payload = build_run_manifest(
        corpus=tmp_path,
        out_dir=out,
        stages=[2, 3],
        weight_function="log",
        fft_policy="adaptive_tier",
        analysis_parameter_profile_id=profile,
    )
    write_run_manifest(out, payload)
    result = verify_corpus(out)
    assert result["ok"] is False
    assert any("fft_policy" in item for item in result["issues"])
    allowed = verify_corpus(out, require_comparable=False)
    assert allowed["ok"] is True
    assert any("fft_policy" in item for item in allowed["warnings"])


def test_verify_corpus_fails_mixed_profile_ids(tmp_path: Path) -> None:
    out = tmp_path / "mixed"
    profile_a = default_parameter_profile_id("log")
    profile_b = default_parameter_profile_id("linear")
    payload = build_run_manifest(
        corpus=tmp_path,
        out_dir=out,
        stages=[2, 3],
        weight_function="log",
        analysis_parameter_profile_id=profile_a,
    )
    write_run_manifest(out, payload)
    _write_compiled(
        out / "compiled_density_metrics.xlsx",
        profile_id=profile_a,
        notes=["A2", "C3"],
        extra_profiles=[profile_a, profile_b],
    )
    result = verify_corpus(out)
    assert result["ok"] is False
    assert any("mixed analysis_parameter_profile_id" in item for item in result["issues"])


def test_verify_corpus_fails_degenerate_zero_ci(tmp_path: Path) -> None:
    out = tmp_path / "degen"
    profile = default_parameter_profile_id("log")
    payload = build_run_manifest(
        corpus=tmp_path,
        out_dir=out,
        stages=[2, 3],
        weight_function="log",
        analysis_parameter_profile_id=profile,
    )
    write_run_manifest(out, payload)
    _write_compiled(
        out / "compiled_density_metrics.xlsx",
        profile_id=profile,
        eligible=False,
        degenerate=True,
        rel_uncertainty=0.0,
    )
    result = verify_corpus(out)
    assert result["ok"] is False
    assert any("rel_uncertainty is 0.0" in item for item in result["issues"])


def test_runbook_documents_exact_commands() -> None:
    runbook = Path("docs/REEXPORT_RUNBOOK.md").read_text(encoding="utf-8")
    assert "--corpus" in runbook
    assert "--fft-policy fixed" in runbook
    assert "--fixed-n-fft 8192" in runbook
    assert "--fixed-hop-length 1024" in runbook
    assert "python -m tools.verify_corpus" in runbook
    assert "python -m tools.reexport_corpus" in runbook
    assert "run_manifest.json" in runbook
    assert "v4.2.1" in runbook
    assert "pretag_evidence" in runbook
    assert "analysis_results_v4.2.1" in runbook
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "REEXPORT_RUNBOOK.md" in readme
    assert "verify_corpus" in readme
