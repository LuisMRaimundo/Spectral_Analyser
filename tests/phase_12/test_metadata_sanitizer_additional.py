from __future__ import annotations

"""
Additional contract-level coverage for metadata_sanitizer.py.

Public APIs under test:
- publication toggles and formal tokens (``REDACT_TOKEN``, omit-key sets);
- platform / orchestrator label generalization;
- absolute-path detection and publication-safe path redaction;
- recursive metadata sanitization (dict/list/tuple/DataFrame);
- publication-clean export filters (Analysis_Metadata rows, flat meta,
  research metadata, sparse-column drops, canonical density columns);
- JSON/repository export sanitization (``sanitize_export_metadata_*``);
- publication scan helpers and ``validate_no_private_paths`` on text exports.

Focus areas (no production code changes):
- stable missing-value / blank-column handling;
- provenance/status token preservation vs path redaction;
- non-mutation and deterministic output;
- row/column preservation on DataFrame cleaners;
- cross-platform path string handling (Windows + POSIX strings).

Excel workbook read/write helpers are intentionally not exercised here.
"""

import json
import re
from pathlib import Path

import pandas as pd
import pytest

import metadata_sanitizer as ms


_WIN_SAMPLE = r"C:\Users\alice\Desktop\corpus\sample.wav"
_POSIX_SAMPLE = "/Users/alice/Desktop/corpus/sample.wav"
_HOME_SAMPLE = "/home/bob/project/sample.wav"


# ---------------------------------------------------------------------------
# Constants and toggles
# ---------------------------------------------------------------------------

def test_redact_token_and_omit_key_sets_are_stable() -> None:
    assert ms.REDACT_TOKEN == "redacted_for_publication"
    assert "compile_metrics_file" in ms.PUBLICATION_ANALYSIS_META_PARAMETERS_OMIT
    assert "Source_File" in ms.PUBLICATION_META_FLAT_KEYS_OMIT
    assert len(ms.PUBLICATION_ANALYSIS_META_PARAMETERS_OMIT) == len(
        set(ms.PUBLICATION_ANALYSIS_META_PARAMETERS_OMIT)
    )
    assert len(ms.PUBLICATION_META_FLAT_KEYS_OMIT) == len(
        set(ms.PUBLICATION_META_FLAT_KEYS_OMIT)
    )


def test_publication_toggle_helpers_reflect_module_constants() -> None:
    assert ms.publication_redaction_enabled() is bool(ms.REDACT_LOCAL_PATHS_FOR_PUBLICATION)
    assert ms.publication_clean_export_enabled() is bool(ms.PUBLICATION_CLEAN_EXPORT)


def test_format_utc_publication_timestamp_is_locale_neutral_iso_z() -> None:
    ts = ms.format_utc_publication_timestamp()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", ts)


# ---------------------------------------------------------------------------
# Platform / orchestrator label normalization
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, None),
        ("", ""),
        ("  ", "  "),
        ("Windows-10-amd64", "Windows"),
        ("darwin-21.6.0", "macOS"),
        ("macosx-12.0", "macOS"),
        ("Linux x86_64", "Linux"),
        ("FreeBSD 13", "unknown_platform"),
    ],
)
def test_generalize_platform_for_publication(raw: object, expected: object) -> None:
    assert ms.generalize_platform_for_publication(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, None),
        ("", ""),
        ("validated_pipeline", "validated_pipeline"),
        ("not_validated_orchestrator_v2", "gui_orchestrator_pipeline"),
    ],
)
def test_neutralize_orchestrator_validation_label(raw: object, expected: object) -> None:
    assert ms.neutralize_orchestrator_validation_label(raw) == expected


# ---------------------------------------------------------------------------
# Path detection heuristics
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "value, expected",
    [
        (None, False),
        ("", False),
        ("relative/note.wav", False),
        ("sample.wav", False),
        (_WIN_SAMPLE, True),
        (_POSIX_SAMPLE, True),
        (_HOME_SAMPLE, True),
        ("D:", True),
    ],
)
def test_is_absolute_path_like(value: object, expected: bool) -> None:
    assert ms.is_absolute_path_like(value) is expected


def test_string_contains_forbidden_local_path_detects_user_home_patterns() -> None:
    assert ms.string_contains_forbidden_local_path(_WIN_SAMPLE) is True
    assert ms.string_contains_forbidden_local_path(_POSIX_SAMPLE) is True
    assert ms.string_contains_forbidden_local_path("harmonic_density") is False


@pytest.mark.parametrize(
    "value, expected",
    [
        ("http://example.com/audio.wav", False),
        ("file:///Users/alice/a.wav", True),
        (_WIN_SAMPLE, True),
        (_HOME_SAMPLE, True),
        ("~/Desktop/project", True),
        ("relative/audio.wav", False),
    ],
)
def test_detect_absolute_local_path(value: str, expected: bool) -> None:
    assert ms.detect_absolute_local_path(value) is expected


def test_string_fails_publication_scan_and_alias_agree() -> None:
    dirty = r"C:\Users\alice\Desktop\secret.xlsx"
    clean = "canonical_density_v5"
    assert ms.string_fails_publication_scan(dirty) is True
    assert ms.scan_text_for_forbidden_paths(dirty) is True
    assert ms.string_fails_publication_scan(clean) is False
    assert ms.scan_text_for_forbidden_paths(clean) is False


# ---------------------------------------------------------------------------
# Path redaction and basename extraction
# ---------------------------------------------------------------------------

def test_redact_path_replaces_absolute_paths_with_redact_token() -> None:
    assert ms.redact_path(_WIN_SAMPLE) == ms.REDACT_TOKEN
    assert ms.redact_path("harmonic_ratio") == "harmonic_ratio"
    assert ms.redact_path(None) is None


def test_redact_path_emits_dataset_relative_fragment_when_under_project_root(
    tmp_path: Path,
) -> None:
    audio = tmp_path / "corpus" / "sample.wav"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"test-bytes")
    rel = ms.redact_path(str(audio.resolve()), project_root=tmp_path)
    assert rel == "<DATASET_ROOT>/corpus/sample.wav"


@pytest.mark.parametrize(
    "path_text, expected",
    [
        (_WIN_SAMPLE, "sample.wav"),
        (_POSIX_SAMPLE, "sample.wav"),
        (_HOME_SAMPLE, "sample.wav"),
        ("sample.wav", "sample.wav"),
        (None, ""),
    ],
)
def test_sanitize_path_for_publication_extracts_basename(path_text: object, expected: str) -> None:
    assert ms.sanitize_path_for_publication(path_text) == expected


def test_publication_audio_and_output_dir_fields_are_export_safe() -> None:
    audio = ms.publication_audio_path_fields("runs/sample.wav")
    assert audio["audio_file_name"] == "sample.wav"
    assert audio["audio_file_stem"] == "sample"
    assert audio["audio_path_policy"] == "sanitized_for_publication"
    assert ms.detect_absolute_local_path(audio["audio_relative_path"]) is False

    out = ms.publication_output_dir_fields("/tmp/project/output/run1")
    assert out["output_dir_relative"] == "run1"
    assert out["output_path_policy"] == "sanitized_for_publication"


# ---------------------------------------------------------------------------
# Recursive metadata sanitization
# ---------------------------------------------------------------------------

def test_sanitize_metadata_dict_redacts_path_sensitive_keys_and_preserves_status() -> None:
    src = {
        "file_path": _WIN_SAMPLE,
        "input_schema_validation_status": "validated_pipeline",
        "note": "C4",
        "metric": 1.25,
    }
    out = ms.sanitize_metadata_dict(src)
    assert out["file_path"] == ms.REDACT_TOKEN
    assert out["input_schema_validation_status"] == "validated_pipeline"
    assert out["note"] == "C4"
    assert out["metric"] == 1.25
    assert src["file_path"] == _WIN_SAMPLE


def test_sanitize_metadata_value_handles_nested_containers_and_embedded_paths() -> None:
    nested = {
        "paths": [r"C:\Users\a\one.wav", "safe_label"],
        "pair": (r"/Users/a/two.wav", "ok"),
    }
    out = ms.sanitize_metadata_value(nested)
    assert out["paths"][0] == ms.REDACT_TOKEN
    assert out["paths"][1] == "safe_label"
    # POSIX user-home sub replaces the /Users/<user> prefix inside the tuple item.
    assert ms.REDACT_TOKEN in out["pair"][0]
    assert out["pair"][1] == "ok"

    embedded = f"prefix {_WIN_SAMPLE} suffix"
    assert ms.REDACT_TOKEN in ms.sanitize_metadata_value(embedded)


def test_sanitize_metadata_dict_passthrough_when_redaction_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ms, "REDACT_LOCAL_PATHS_FOR_PUBLICATION", False)
    src = {"file_path": _WIN_SAMPLE, "note": "D4"}
    out = ms.sanitize_metadata_dict(src)
    assert out == src
    assert out is not src


def test_sanitize_dataframe_for_publication_redacts_cells_without_mutating_input() -> None:
    df = pd.DataFrame(
        {
            "Note": ["C4"],
            "file_path": [_WIN_SAMPLE],
            "status": ["validated_pipeline"],
        }
    )
    snapshot = df.copy()
    out = ms.sanitize_dataframe_for_publication(df)
    assert out["file_path"].iloc[0] == ms.REDACT_TOKEN
    assert out["status"].iloc[0] == "validated_pipeline"
    pd.testing.assert_frame_equal(df, snapshot)


# ---------------------------------------------------------------------------
# Publication-clean Analysis_Metadata / flat meta / research metadata
# ---------------------------------------------------------------------------

def test_filter_analysis_meta_rows_publication_clean() -> None:
    rows = [
        ("platform", "Darwin 21"),
        ("cwd", "/home/user/project"),
        ("note", "C4"),
        ("compile_metrics_file", "/secret/compile_metrics.py"),
        ("input_schema_validation_status", "not_validated_orchestrator"),
        ("custom_path", _WIN_SAMPLE),
    ]
    out = ms.filter_analysis_meta_rows_publication_clean(rows)
    params = dict(out)
    assert params["platform"] == "macOS"
    assert params["note"] == "C4"
    assert params["input_schema_validation_status"] == "gui_orchestrator_pipeline"
    assert params["custom_path"] == "sample.wav"
    assert "cwd" not in params
    assert "compile_metrics_file" not in params


def test_filter_analysis_meta_rows_passthrough_when_clean_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ms, "PUBLICATION_CLEAN_EXPORT", False)
    rows = [("cwd", "/home/user/project"), ("note", "C4")]
    assert ms.filter_analysis_meta_rows_publication_clean(rows) == rows


def test_apply_publication_clean_meta_flat_removes_dev_keys_and_generalizes_platform() -> None:
    meta = {
        "platform": "Linux x86_64",
        "cwd": "/secret/cwd",
        "density": 0.42,
        "Source_File": "note.wav",
        "proc_audio_file": "/secret/proc_audio.py",
    }
    out = ms.apply_publication_clean_meta_flat(meta)
    assert out == {"platform": "Linux", "density": 0.42}
    assert "cwd" not in out and "Source_File" not in out


def test_apply_publication_clean_research_metadata_fields() -> None:
    rows = {
        "platform": "Darwin 21",
        "source_compiled_workbook": _WIN_SAMPLE,
        "compiled_from": _WIN_SAMPLE,
        "note": "G3",
    }
    out = ms.apply_publication_clean_research_metadata_fields(
        rows, workbook_basename="compiled_metrics.xlsx"
    )
    assert out["research_export_source_workbook"] == "compiled_metrics.xlsx"
    assert out["platform"] == "macOS"
    assert out["note"] == "G3"
    assert "source_compiled_workbook" not in out
    assert out["compiled_from"] == "sample.wav"


def test_drop_publication_noise_columns_from_dataframe() -> None:
    df = pd.DataFrame(
        {
            "Note": ["C4"],
            "metric": [1.0],
            "dead_text": [""],
            "redacted_only": [ms.REDACT_TOKEN],
        }
    )
    out = ms.drop_publication_noise_columns_from_dataframe(df)
    assert list(out.columns) == ["Note", "metric"]
    assert list(df.columns) == ["Note", "metric", "dead_text", "redacted_only"]


def test_publication_clean_drop_known_sparse_columns_and_canonical_density() -> None:
    sparse = pd.DataFrame(
        {
            "Note": ["C4"],
            "Source_File": [""],
            "metric": [0.5],
        }
    )
    dropped = ms.publication_clean_drop_known_sparse_columns(sparse)
    assert "Source_File" not in dropped.columns
    assert "metric" in dropped.columns

    both = pd.DataFrame(
        {"canonical_density": [0.4], "canonical_density_v5_adapted": [0.6]}
    )
    canonical = ms.publication_research_canonical_density_columns(both)
    assert list(canonical.columns) == ["canonical_density"]
    assert canonical["canonical_density"].iloc[0] == pytest.approx(0.4)

    renamed = pd.DataFrame({"canonical_density_v5_adapted": [0.7]})
    only = ms.publication_research_canonical_density_columns(renamed)
    assert list(only.columns) == ["canonical_density"]
    assert only["canonical_density"].iloc[0] == pytest.approx(0.7)


def test_publication_dataframe_cleaners_passthrough_empty_and_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    empty = pd.DataFrame()
    assert ms.drop_publication_noise_columns_from_dataframe(empty) is empty
    monkeypatch.setattr(ms, "PUBLICATION_CLEAN_EXPORT", False)
    df = pd.DataFrame({"dead": [""]})
    assert list(ms.drop_publication_noise_columns_from_dataframe(df).columns) == ["dead"]


# ---------------------------------------------------------------------------
# JSON / repository export sanitization
# ---------------------------------------------------------------------------

def test_sanitize_export_metadata_dict_expands_audio_file_and_drops_dataset_root() -> None:
    obj = {
        "audio_file": _WIN_SAMPLE,
        "note": "C4",
        "dataset_root": "/secret/root",
        "status": "validated_pipeline",
    }
    out = ms.sanitize_export_metadata_dict(obj)
    assert out["audio_file"] == "sample.wav"
    assert out["audio_file_name"] == "sample.wav"
    assert "dataset_root" not in out
    assert out["note"] == "C4"
    assert out["status"] == "validated_pipeline"


def test_sanitize_export_metadata_dict_sanitizes_output_dir_keys() -> None:
    obj = {"output_dir": _HOME_SAMPLE}
    out = ms.sanitize_export_metadata_dict(obj)
    assert out["output_dir_relative"] == "sample.wav"
    assert out["output_path_policy"] == "sanitized_for_publication"
    assert out["output_dir"] == out["output_dir_relative"]


def test_sanitize_run_parameters_json_roundtrip() -> None:
    payload = {"file_path": _WIN_SAMPLE, "hop_length": 512}
    raw = json.dumps(payload)
    cleaned = ms.sanitize_run_parameters_json(raw)
    parsed = json.loads(cleaned)
    assert parsed["file_path"] == "sample.wav"
    assert parsed["hop_length"] == 512


def test_sanitize_run_parameters_json_non_json_absolute_path() -> None:
    assert ms.sanitize_run_parameters_json(_WIN_SAMPLE) == "sample.wav"
    assert ms.sanitize_run_parameters_json("") == ""
    assert ms.sanitize_run_parameters_json("not-a-path") == "not-a-path"


def test_redact_public_path_leakage_and_detect_private_fragment() -> None:
    assert ms.detect_private_path_leakage_fragment(_WIN_SAMPLE) is True
    assert ms.detect_private_path_leakage_fragment("harmonic_density") is False
    leaked = ms.redact_public_path_leakage(f"source: {_WIN_SAMPLE}")
    assert leaked == "source"
    assert ms.detect_absolute_local_path(leaked) is False


def test_get_metadata_privacy_mode_and_export_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPECTRAL_ANALYSER_EXPORT_PROFILE", raising=False)
    monkeypatch.delenv("SPECTRAL_ANALYSER_EXPORT_PROFILE", raising=False)
    monkeypatch.delenv("SPECTRAL_ANALYSER_METADATA_PRIVACY_MODE", raising=False)
    monkeypatch.delenv("SPECTRAL_ANALYSER_EXPORT_ABSOLUTE_PATHS", raising=False)
    assert ms.get_export_profile() == ""
    assert ms.get_metadata_privacy_mode() == "public"

    monkeypatch.setenv("SPECTRAL_ANALYSER_EXPORT_PROFILE", "public_repository")
    assert ms.get_metadata_privacy_mode() == "public"

    monkeypatch.delenv("SPECTRAL_ANALYSER_EXPORT_PROFILE", raising=False)
    monkeypatch.setenv("SPECTRAL_ANALYSER_EXPORT_ABSOLUTE_PATHS", "true")
    assert ms.get_metadata_privacy_mode() == "internal_debug"


# ---------------------------------------------------------------------------
# File helpers and batch enrichment
# ---------------------------------------------------------------------------

def test_short_sha256_for_file_and_make_public_audio_id(tmp_path: Path) -> None:
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"abc")
    h = ms.short_sha256_for_file(audio, length=12)
    assert h == "ba7816bf8f01"
    assert ms.short_sha256_for_file(tmp_path / "missing.wav") is None

    pub_id = ms.make_public_audio_id(audio, note="C4", index=2)
    assert pub_id.startswith("audio__")
    assert "__C4__" in pub_id
    assert pub_id.endswith("i2")


def test_enrich_and_redact_batch_audio_result(tmp_path: Path) -> None:
    audio = tmp_path / "note.wav"
    audio.write_bytes(b"payload")
    row = {"density": 0.5, "file_path": str(audio.resolve())}
    out = ms.enrich_and_redact_batch_audio_result(row, audio, note_name="E4")
    assert out["density"] == 0.5
    assert out["source_file_basename"] == "note.wav"
    assert out["public_audio_id"].startswith("audio__")
    assert out["file_path"] == ms.REDACT_TOKEN
    assert row["file_path"] == str(audio.resolve())


# ---------------------------------------------------------------------------
# validate_no_private_paths (text exports only)
# ---------------------------------------------------------------------------

def test_validate_no_private_paths_passes_clean_text_tree(tmp_path: Path) -> None:
    (tmp_path / "meta.json").write_text(
        json.dumps({"note": "C4", "metric": 0.5}), encoding="utf-8"
    )
    ok, errors = ms.validate_no_private_paths(tmp_path)
    assert ok is True
    assert errors == []


def test_validate_no_private_paths_flags_forbidden_fragments(tmp_path: Path) -> None:
    (tmp_path / "leak.txt").write_text(f"audio from {_WIN_SAMPLE}", encoding="utf-8")
    ok, errors = ms.validate_no_private_paths(tmp_path)
    assert ok is False
    assert errors
    assert any("forbidden fragment" in e or "private_path_fragment" in e for e in errors)


def test_validate_no_private_paths_missing_root() -> None:
    ok, errors = ms.validate_no_private_paths("/path/that/does/not/exist")
    assert ok is False
    assert any("does not exist" in e for e in errors)


def test_assert_no_private_paths_raises_on_violation(tmp_path: Path) -> None:
    (tmp_path / "bad.csv").write_text(_POSIX_SAMPLE, encoding="utf-8")
    with pytest.raises(AssertionError, match="Private path patterns found"):
        ms.assert_no_private_paths(tmp_path)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_apply_publication_clean_meta_flat_passthrough_when_clean_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ms, "PUBLICATION_CLEAN_EXPORT", False)
    meta = {"cwd": "/secret", "platform": "Linux x86_64"}
    assert ms.apply_publication_clean_meta_flat(meta) == meta


def test_redact_path_and_dataframe_passthrough_when_redaction_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ms, "REDACT_LOCAL_PATHS_FOR_PUBLICATION", False)
    assert ms.redact_path(_WIN_SAMPLE) == _WIN_SAMPLE
    df = pd.DataFrame({"file_path": [_WIN_SAMPLE]})
    assert ms.sanitize_dataframe_for_publication(df) is df


def test_get_metadata_privacy_mode_internal_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPECTRAL_ANALYSER_EXPORT_ABSOLUTE_PATHS", raising=False)
    monkeypatch.setenv("SPECTRAL_ANALYSER_METADATA_PRIVACY_MODE", "internal_debug")
    assert ms.get_metadata_privacy_mode() == "internal_debug"


def test_detect_absolute_local_path_accepts_path_objects(tmp_path: Path) -> None:
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"x")
    assert ms.detect_absolute_local_path(Path(audio.resolve())) is True


def test_publication_path_fields_honour_dataset_root(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    audio = root / "notes" / "sample.wav"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"x")
    fields = ms.publication_audio_path_fields(audio, dataset_root=root)
    assert fields["audio_relative_path"] == "notes/sample.wav"
    out_fields = ms.publication_output_dir_fields(root / "output" / "run1", dataset_root=root)
    assert out_fields["output_dir_relative"] == "output/run1"
    # Basename fallback when host-relative resolution is unavailable on the runner.
    assert ms.sanitize_path_for_publication(audio, dataset_root=root) in {
        "notes/sample.wav",
        "sample.wav",
    }


def test_redact_public_path_leakage_passthrough_in_internal_debug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPECTRAL_ANALYSER_METADATA_PRIVACY_MODE", "internal_debug")
    text = f"notes stored at {_WIN_SAMPLE}"
    assert ms.redact_public_path_leakage(text) == text


def test_sanitize_export_metadata_value_handles_path_objects() -> None:
    assert ms.sanitize_export_metadata_value(Path(_WIN_SAMPLE)) == "sample.wav"


def test_sanitize_metadata_dict_nested_under_path_sensitive_key() -> None:
    src = {"output_dir": {"nested": _WIN_SAMPLE}}
    out = ms.sanitize_metadata_dict(src)
    assert out["output_dir"]["nested"] == ms.REDACT_TOKEN


def test_apply_publication_clean_research_metadata_fields_passthrough_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ms, "PUBLICATION_CLEAN_EXPORT", False)
    rows = {"source_compiled_workbook": "compiled.xlsx", "note": "C4"}
    assert ms.apply_publication_clean_research_metadata_fields(
        rows, workbook_basename="ignored.xlsx"
    ) == rows


def test_sanitize_metadata_dict_is_deterministic() -> None:
    src = {"file_path": _WIN_SAMPLE, "nested": {"audio_path": _POSIX_SAMPLE}}
    a = ms.sanitize_metadata_dict(src)
    b = ms.sanitize_metadata_dict(src)
    assert a == b


def test_sanitize_export_metadata_dict_is_deterministic() -> None:
    src = {"audio_file": _WIN_SAMPLE, "note": "A4"}
    assert ms.sanitize_export_metadata_dict(src) == ms.sanitize_export_metadata_dict(src)
