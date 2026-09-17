"""Digital silence must not block a mixed corpus or fabricate measurements."""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import soundfile as sf

import compile_metrics as cm
from audio_silence_trim import DIGITAL_SILENCE_ABS, is_digital_silence
from proc_audio import AudioProcessor


def _write_sine(path: Path, *, freq_hz: float, sr: int = 22050, seconds: float = 0.4) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(sr * seconds), dtype=float) / float(sr)
    y = (0.35 * np.sin(2.0 * np.pi * float(freq_hz) * t)).astype(np.float64)
    pcm = np.asarray(np.clip(y, -1.0, 1.0) * 32767.0, dtype=np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr))
        wf.writeframes(pcm.tobytes())
    return path


def _write_silence(path: Path, *, sr: int = 22050, seconds: float = 0.4) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    y = np.zeros(int(sr * seconds), dtype=np.float64)
    sf.write(str(path), y, sr, subtype="FLOAT")
    return path


def _run_stage1(tmp_path: Path, wavs: list[Path]) -> Path:
    run = tmp_path / "run"
    ap = AudioProcessor()
    ap.load_audio_files([str(p) for p in wavs])
    ap.apply_filters_and_generate_data(
        results_directory=run,
        n_fft=4096,
        hop_length=512,
        dissonance_enabled=False,
        dissonance_curve=False,
        dissonance_scale=False,
        compare_models=False,
        compile_per_call=False,
        parallel_processing=False,
    )
    return run


def _meta_map(wb: Path) -> dict[str, object]:
    meta = pd.read_excel(wb, sheet_name="Analysis_Metadata")
    return dict(zip(meta.iloc[:, 0].astype(str), meta.iloc[:, 1]))


def test_is_digital_silence_helper() -> None:
    assert is_digital_silence(np.zeros(64))
    assert is_digital_silence(np.full(64, DIGITAL_SILENCE_ABS))
    assert not is_digital_silence(np.array([0.0, 1e-3, 0.0]))


def test_mixed_corpus_silence_does_not_block_valid_tone(tmp_path: Path) -> None:
    audio = tmp_path / "audio"
    silence = _write_silence(audio / "G3_silence.wav")
    tone = _write_sine(audio / "A4_sine.wav", freq_hz=440.0)
    run = _run_stage1(tmp_path, [silence, tone])
    workbooks = sorted(run.rglob("spectral_analysis.xlsx"))
    assert len(workbooks) == 2
    summary = cm.assert_results_dir_schema_or_raise(run)
    assert summary["stale"] == 0
    assert summary["valid"] == 2

    by_note = {wb.parent.name: wb for wb in workbooks}
    silence_meta = _meta_map(by_note["G3"])
    tone_meta = _meta_map(by_note["A4"])
    assert str(silence_meta.get("digital_silence_input")).lower() in {"true", "1"}
    assert str(silence_meta.get("valid_for_primary_statistics")).lower() in {"false", "0"}
    assert str(silence_meta.get("eligibility_exclusion_reason")) == "digital_silence"
    f0_meas = pd.to_numeric(pd.Series([silence_meta.get("f0_final_hz")]), errors="coerce").iloc[0]
    assert not np.isfinite(float(f0_meas))
    f0_tone = float(pd.to_numeric(pd.Series([tone_meta.get("f0_final_hz")]), errors="coerce").iloc[0])
    assert np.isfinite(f0_tone)
    assert abs(1200.0 * np.log2(f0_tone / 440.0)) < 80.0

    compiled = tmp_path / "compiled.xlsx"
    cm.compile_density_metrics_with_pca(
        folder_path=run,
        output_path=compiled,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
    )
    assert compiled.is_file()


def test_all_silence_corpus_is_ineligible_and_schema_complete(tmp_path: Path) -> None:
    wav = _write_silence(tmp_path / "audio" / "G3_silence.wav")
    run = _run_stage1(tmp_path, [wav])
    wbs = list(run.rglob("spectral_analysis.xlsx"))
    assert len(wbs) == 1
    summary = cm.assert_results_dir_schema_or_raise(run)
    assert summary["stale"] == 0
    assert summary["valid"] == 1
    meta = _meta_map(wbs[0])
    assert str(meta.get("eligibility_exclusion_reason")) == "digital_silence"
    assert str(meta.get("valid_for_primary_statistics")).lower() in {"false", "0"}
    compiled = tmp_path / "compiled.xlsx"
    cm.compile_density_metrics_with_pca(
        folder_path=run,
        output_path=compiled,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
    )
    assert compiled.is_file()


def test_valid_tone_export_unchanged_schema(tmp_path: Path) -> None:
    wav = _write_sine(tmp_path / "audio" / "A4_sine.wav", freq_hz=440.0)
    run = _run_stage1(tmp_path, [wav])
    summary = cm.assert_results_dir_schema_or_raise(run)
    assert summary["stale"] == 0
    assert summary["valid"] == 1
    meta = _meta_map(next(run.rglob("spectral_analysis.xlsx")))
    assert str(meta.get("analysis_schema_version")) == cm.EXPECTED_ANALYSIS_SCHEMA_VERSION
    assert str(meta.get("digital_silence_input")).lower() not in {"true", "1"}


def test_genuinely_invalid_workbook_still_fails_schema_guard(tmp_path: Path) -> None:
    results = tmp_path / "bad"
    results.mkdir()
    path = results / "spectral_analysis.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(
            [{"Parameter": "analysis_schema_version", "Value": "stale_v1"}]
        ).to_excel(writer, sheet_name="Analysis_Metadata", index=False)
        pd.DataFrame({"Frequency (Hz)": [440.0], "Amplitude": [1.0]}).to_excel(
            writer, sheet_name="Harmonic Spectrum", index=False
        )
        pd.DataFrame({"Frequency (Hz)": [100.0]}).to_excel(
            writer, sheet_name="Inharmonic Spectrum", index=False
        )
        pd.DataFrame({"Frequency (Hz)": [30.0]}).to_excel(
            writer, sheet_name="Sub-bass band", index=False
        )
    with pytest.raises(RuntimeError, match=cm.STALE_PIPELINE_USER_MESSAGE.split()[0]):
        cm.assert_results_dir_schema_or_raise(results)
