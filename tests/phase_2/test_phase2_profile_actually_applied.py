from __future__ import annotations

from pathlib import Path

import pytest

import compile_metrics


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


def test_phase2_corpus_profile_controls_density_metric_raw(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Build a minimal 3-note corpus layout expected by the compiler walker.
    paths = [
        _touch(tmp_path / "C4" / "spectral_analysis.xlsx"),
        _touch(tmp_path / "E4" / "spectral_analysis.xlsx"),
        _touch(tmp_path / "G4" / "spectral_analysis.xlsx"),
    ]
    _ = paths

    fixture_rows = {
        "C4": {
            "Harmonic Partials sum": 10.0,
            "Inharmonic Partials sum": 4.0,
            "Sub-bass sum": 1.0,
            "component_harmonic_energy_ratio": 0.70,
            "component_inharmonic_energy_ratio": 0.20,
            "component_subbass_energy_ratio": 0.10,
        },
        "E4": {
            "Harmonic Partials sum": 8.0,
            "Inharmonic Partials sum": 3.0,
            "Sub-bass sum": 2.0,
            "component_harmonic_energy_ratio": 0.65,
            "component_inharmonic_energy_ratio": 0.25,
            "component_subbass_energy_ratio": 0.10,
        },
        "G4": {
            "Harmonic Partials sum": 12.0,
            "Inharmonic Partials sum": 2.0,
            "Sub-bass sum": 2.0,
            "component_harmonic_energy_ratio": 0.60,
            "component_inharmonic_energy_ratio": 0.30,
            "component_subbass_energy_ratio": 0.10,
        },
    }

    def _fake_read_excel_metrics(file_path: Path):
        note = file_path.parent.name
        row = fixture_rows[note].copy()
        row["f0_final_hz"] = 261.63
        return row

    monkeypatch.setattr(compile_metrics, "read_excel_metrics", _fake_read_excel_metrics)

    df = compile_metrics.compile_density_metrics_with_pca(
        folder_path=tmp_path,
        output_path=None,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
        harmonic_weight=0.6,
        inharmonic_weight=0.3,
        subbass_weight=0.1,
    )
    assert df is not None
    assert not df.empty
    assert set(df["density_weights_source"].astype(str).tolist()) == {"phase2_corpus_profile"}

    for _, row in df.iterrows():
        expected_corpus = (
            float(row["Harmonic Partials sum"]) * 0.6
            + float(row["Inharmonic Partials sum"]) * 0.3
            + float(row["Sub-bass sum"]) * 0.1
        )
        expected_per_note = (
            float(row["Harmonic Partials sum"]) * float(row["component_harmonic_energy_ratio"])
            + float(row["Inharmonic Partials sum"]) * float(row["component_inharmonic_energy_ratio"])
            + float(row["Sub-bass sum"]) * float(row["component_subbass_energy_ratio"])
        )
        assert float(row["density_metric_raw"]) == pytest.approx(expected_corpus, rel=0.0, abs=1e-12)
        assert float(row["density_metric_raw_per_note_balance"]) == pytest.approx(
            expected_per_note, rel=0.0, abs=1e-12
        )
