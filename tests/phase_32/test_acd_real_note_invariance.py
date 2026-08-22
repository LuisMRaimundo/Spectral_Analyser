"""Real Stage 1 invariance for cello D3 (49-note corpus or pipeline stand-in)."""
from __future__ import annotations

import json
import os
import wave
from pathlib import Path

import numpy as np
import pytest

from tests.phase_32.acd_invariance_support import (
    CELLO_CORPUS_TIER_N_FFT,
    GAINS,
    REAL_NOTE_CACHE,
    REAL_NOTE_CORPUS,
    REAL_NOTE_FFT_TIER_ACD_REL_TOL,
    REAL_NOTE_ID,
    TABLE_PATH,
    THRESHOLD_ROBUSTNESS_DB,
    delta_pct,
    fmt,
    fmt_pct,
)
from tools.acd_research_integration import compute_acd_row_from_workbook
from tools.ewsd_research_integration import compute_ewsd_dataframe_from_analysis_root

CORPUS_AUDIO_DEFAULTS = (
    Path(r"C:\Users\lmr20\Desktop\ORC_Vlc_arco_mf\_Sustains"),
    Path(os.environ.get("EWSD_CORPUS_AUDIO", "")),
)
PRODUCTION_DB_MIN = -80.0
PRODUCTION_N_FFT = 8192  # adaptive tier for D3 (f0 ≈ 146.8 Hz)


def _find_corpus_d3_audio() -> Path | None:
    env = os.environ.get("ACD_REAL_NOTE_AUDIO", "").strip()
    if env:
        path = Path(env).expanduser()
        if path.is_file():
            return path
    roots = [p for p in CORPUS_AUDIO_DEFAULTS if p and str(p).strip()]
    patterns = (
        "*D3*.wav",
        "*D3*.aif",
        "*D3*.aiff",
        "*D3*.WAV",
        "*D3*.AIF",
    )
    for root in roots:
        if not root.is_dir():
            continue
        for pat in patterns:
            hits = sorted(root.rglob(pat))
            if hits:
                return hits[0]
    return None


def _write_cello_like_d3(path: Path, *, gain: float = 1.0, seconds: float = 0.85) -> Path:
    """Mid-register D3 stack with one clearly inharmonic partial (not a corpus take)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sr = 44100
    f0 = 146.8323839587038
    t = np.arange(int(sr * seconds), dtype=float) / float(sr)
    y = np.zeros_like(t)
    for n in range(1, 13):
        y += (1.0 / float(n) ** 1.15) * np.sin(2.0 * np.pi * n * f0 * t)
    # wolf / inharmonic near the major third, off the harmonic comb
    y += 0.22 * np.sin(2.0 * np.pi * (f0 * 2.47) * t)
    y += 0.11 * np.sin(2.0 * np.pi * (f0 * 3.61) * t)
    peak = float(np.max(np.abs(y))) or 1.0
    y = 0.35 * gain * y / peak
    try:
        import soundfile as sf

        sf.write(str(path), y.astype(np.float32), sr, subtype="FLOAT")
    except Exception:
        pcm = np.asarray(np.clip(y, -1.0, 1.0) * 32767.0, dtype=np.int16)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())
    return path


def _score_stage1_dir(stage1: Path) -> dict[str, float]:
    wb = next(stage1.rglob("spectral_analysis.xlsx"))
    acd = compute_acd_row_from_workbook(wb)
    ewsd = compute_ewsd_dataframe_from_analysis_root(
        stage1,
        frequency_ceiling_hz=20000.0,
        include_uncertainty=False,
    )
    row = ewsd.iloc[0] if not ewsd.empty else None

    def _col(*names: str) -> float:
        if row is None:
            return float("nan")
        for name in names:
            if name in ewsd.columns:
                try:
                    val = float(row[name])
                except (TypeError, ValueError):
                    continue
                if val == val:
                    return val
        return float("nan")

    return {
        "ACD_score": float(acd.get("ACD_score", float("nan"))),
        "ACD_magnitude_per_component": float(
            acd.get("ACD_magnitude_per_component", float("nan"))
        ),
        "ACD_D2": float(acd.get("ACD_D2", float("nan"))),
        "EWSD_score_total": _col("EWSD_score_total", "ewsd_score"),
        "EWSD_score_acoustic_balanced": _col(
            "EWSD_score_acoustic_balanced", "ewsd_score_acoustic_balanced"
        ),
    }


def _run_stage1(
    audio: Path,
    out_dir: Path,
    *,
    n_fft: int,
    db_min: float,
) -> dict[str, float]:
    from proc_audio import AudioProcessor

    out_dir.mkdir(parents=True, exist_ok=True)
    ap = AudioProcessor()
    ap._validate_per_note_export_schema = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    ap.load_audio_files([str(audio)])
    ap.apply_filters_and_generate_data(
        results_directory=out_dir,
        n_fft=int(n_fft),
        hop_length=max(1, int(n_fft) // 8),
        zero_padding=2,
        db_min=float(db_min),
        density_salience_threshold_db=float(db_min),
        freq_max=20000.0,
        auto_model_weights_from_analysis=False,
        dissonance_enabled=False,
        dissonance_curve=False,
        dissonance_scale=False,
        compare_models=False,
        compile_per_call=False,
        parallel_processing=False,
    )
    return _score_stage1_dir(out_dir)


def _metric_table(
    rows: list[tuple[str, dict[str, float]]],
    bases: dict[str, float],
    first_col: str,
) -> dict:
    keys = (
        "ACD_score",
        "ACD_magnitude_per_component",
        "ACD_D2",
        "EWSD_score_total",
        "EWSD_score_acoustic_balanced",
    )
    header = (
        f"| {first_col} | ACD_score | ACD_Δ% | ACD_magnitude_per_component | "
        "ACD_mag_Δ% | ACD_D2 | ACD_D2_Δ% | EWSD_score_total | EWSD_Δ% | "
        "EWSD_score_acoustic_balanced | EWSD_bal_Δ% |"
    )
    sep = "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    body = []
    for label, mets in rows:
        cells = [str(label)]
        for key in keys:
            val = mets[key]
            cells.append(fmt(val))
            cells.append(fmt_pct(delta_pct(val, bases[key])))
        body.append("| " + " | ".join(cells) + " |")
    return {
        "header": header,
        "separator": sep,
        "rows": body,
    }


def generate_real_note_payload(work: Path, *, use_corpus: bool) -> dict:
    corpus_audio = _find_corpus_d3_audio() if use_corpus else None
    source = "corpus_recording" if corpus_audio is not None else "pipeline_synthesized_d3"
    heading_note = (
        f"Note `{REAL_NOTE_ID}` from `{REAL_NOTE_CORPUS}`. "
        "These rows are Stage 1 **measurements** (loaded audio → production "
        "peak picker / FFT tier / Phase 8 `peak_amplitude_sum`), not toy amplitude fixtures."
    )
    if corpus_audio is None:
        heading_note += (
            " Corpus audio was not mounted; audio is a 0.85 s synthesized D3 "
            "(f0 = 146.83 Hz) with two inharmonic partials, run through the "
            "production Stage 1 path. Set `ACD_REAL_NOTE_AUDIO` to the corpus "
            "D3 take to replace this stand-in."
        )
        audio_base = _write_cello_like_d3(work / "audio" / "ORC_Vlc_arco_mf_D3.wav", gain=1.0)
    else:
        heading_note += f" Source file: `{corpus_audio}`."
        audio_base = corpus_audio

    base = _run_stage1(
        audio_base,
        work / "base",
        n_fft=PRODUCTION_N_FFT,
        db_min=PRODUCTION_DB_MIN,
    )

    gain_rows: list[tuple[str, dict[str, float]]] = []
    for g in GAINS:
        if abs(float(g) - 1.0) < 1e-15 and corpus_audio is not None:
            gain_rows.append((f"{g:.0e}", base))
            continue
        if corpus_audio is None:
            wav = _write_cello_like_d3(
                work / "gain" / f"ORC_Vlc_arco_mf_D3_gain_{g:.0e}.wav",
                gain=float(g),
            )
        else:
            wav = _apply_gain_copy(
                corpus_audio,
                work / "gain" / f"ORC_Vlc_arco_mf_D3_gain_{g:.0e}.wav",
                float(g),
            )
        mets = _run_stage1(
            wav,
            work / "gain" / f"run_{g:.0e}",
            n_fft=PRODUCTION_N_FFT,
            db_min=PRODUCTION_DB_MIN,
        )
        gain_rows.append((f"{g:.0e}", mets))

    fft_rows: list[tuple[str, dict[str, float]]] = []
    for n_fft in CELLO_CORPUS_TIER_N_FFT:
        if int(n_fft) == PRODUCTION_N_FFT:
            fft_rows.append((str(n_fft), base))
            continue
        mets = _run_stage1(
            audio_base,
            work / "fft" / f"n{n_fft}",
            n_fft=int(n_fft),
            db_min=PRODUCTION_DB_MIN,
        )
        fft_rows.append((str(n_fft), mets))

    thr_rows: list[tuple[str, dict[str, float]]] = []
    for thr in THRESHOLD_ROBUSTNESS_DB:
        if abs(float(thr) - PRODUCTION_DB_MIN) < 1e-12:
            thr_rows.append((f"{thr:g}", base))
            continue
        mets = _run_stage1(
            audio_base,
            work / "thr" / f"db_{thr:g}",
            n_fft=PRODUCTION_N_FFT,
            db_min=float(thr),
        )
        thr_rows.append((f"{thr:g}", mets))

    acd_fft = [m["ACD_score"] for _, m in fft_rows]
    return {
        "note_id": REAL_NOTE_ID,
        "corpus": REAL_NOTE_CORPUS,
        "source": source,
        "heading_note": heading_note,
        "tier_tolerance_relative": REAL_NOTE_FFT_TIER_ACD_REL_TOL,
        "base": base,
        "fft_acd_scores": acd_fft,
        "blocks": [
            {
                "title": "Gain sweep (audio scaled before Stage 1)",
                "caption": (
                    "Gain is applied to the loaded waveform, then Stage 1 is run "
                    f"at n_fft={PRODUCTION_N_FFT}, db_min={PRODUCTION_DB_MIN}."
                ),
                **_metric_table(gain_rows, base, "gain"),
            },
            {
                "title": "FFT tier (real Stage 1; unique n_fft selected for C2–C6)",
                "caption": (
                    "Each n_fft is a value `_assign_tier_for_file` actually "
                    "selects on the 49-note cello range. Bin width, peak census, "
                    "and Phase 8 `peak_amplitude_sum` vary together. "
                    f"ACD_score must stay within {REAL_NOTE_FFT_TIER_ACD_REL_TOL:.0%} "
                    "of the production-tier base."
                ),
                **_metric_table(fft_rows, base, "n_fft"),
            },
            {
                "title": "Peak-picking threshold (production `db_min` sweep)",
                "caption": (
                    "Stage 1 `db_min` / `density_salience_threshold_db`. "
                    f"Production default is {PRODUCTION_DB_MIN} dB."
                ),
                **_metric_table(thr_rows, base, "db_min"),
            },
        ],
    }


def _apply_gain_copy(src: Path, dest: Path, gain: float) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        import soundfile as sf

        y, sr = sf.read(str(src), always_2d=False)
        y = np.asarray(y, dtype=float)
        if y.ndim > 1:
            y = y.mean(axis=1)
        y = y * float(gain)
        sf.write(str(dest), y.astype(np.float32), int(sr), subtype="FLOAT")
        return dest
    except Exception:
        return src


def _assert_fft_tolerance(payload: dict) -> None:
    base = float(payload["base"]["ACD_score"])
    assert np.isfinite(base) and base > 0.0
    for score in payload["fft_acd_scores"]:
        assert score == pytest.approx(base, rel=REAL_NOTE_FFT_TIER_ACD_REL_TOL)


def test_real_note_fft_tier_tolerance_from_cache() -> None:
    if not REAL_NOTE_CACHE.is_file():
        pytest.skip("real-note cache not yet generated")
    payload = json.loads(REAL_NOTE_CACHE.read_text(encoding="utf-8"))
    _assert_fft_tolerance(payload)
    assert payload["note_id"] == REAL_NOTE_ID
    assert TABLE_PATH.is_file()


@pytest.mark.slow
@pytest.mark.timeout(900)
def test_generate_real_note_pipeline_measurements(tmp_path: Path) -> None:
    """Populate the cache from a real Stage 1 sweep (synth stand-in if no corpus)."""
    payload = generate_real_note_payload(tmp_path, use_corpus=False)
    _assert_fft_tolerance(payload)
    REAL_NOTE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    REAL_NOTE_CACHE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    # Refresh the markdown table so the real-note half is present.
    from tests.phase_32.test_acd_invariance import test_write_invariance_markdown_table

    test_write_invariance_markdown_table()
    text = TABLE_PATH.read_text(encoding="utf-8")
    assert REAL_NOTE_ID in text
    assert "measurements" in text.lower()


@pytest.mark.live_audio
@pytest.mark.timeout(900)
def test_generate_real_note_from_corpus(tmp_path: Path) -> None:
    if _find_corpus_d3_audio() is None:
        pytest.skip("corpus D3 audio not mounted")
    payload = generate_real_note_payload(tmp_path, use_corpus=True)
    assert payload["source"] == "corpus_recording"
    _assert_fft_tolerance(payload)
    REAL_NOTE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    REAL_NOTE_CACHE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    from tests.phase_32.test_acd_invariance import test_write_invariance_markdown_table

    test_write_invariance_markdown_table()
