from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pandas as pd

import compile_metrics
from proc_audio import AudioProcessor


def write_sine_wav(
    path: Path,
    *,
    freq_hz: float,
    amplitude: float,
    sr_hz: int = 44100,
    seconds: float = 1.0,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(sr_hz * seconds), dtype=float) / float(sr_hz)
    y = float(amplitude) * np.sin(2.0 * np.pi * float(freq_hz) * t)
    pcm = np.asarray(np.clip(y, -1.0, 1.0) * 32767.0, dtype=np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr_hz))
        wf.writeframes(pcm.tobytes())
    return path


def run_single_note_pipeline_and_read_compiled(
    tmp_path: Path,
    *,
    n_fft: int,
    freq_hz: float = 1000.0,
    amplitude: float = 0.5,
    sr_hz: int = 44100,
) -> pd.DataFrame:
    run_root = tmp_path / f"run_nfft_{int(n_fft)}"
    wav_path = write_sine_wav(
        run_root / "audio" / f"B5_{int(n_fft)}.wav",
        freq_hz=freq_hz,
        amplitude=amplitude,
        sr_hz=sr_hz,
        seconds=1.0,
    )
    ap = AudioProcessor()
    # The stale-schema guard is orthogonal to this normalization regression;
    # disable it in this synthetic test harness so Stage 1 workbooks are
    # always emitted for the cross-n_fft comparison.
    ap._validate_per_note_export_schema = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    ap.load_audio_files([str(wav_path)])
    ap.apply_filters_and_generate_data(
        results_directory=run_root / "stage1",
        n_fft=int(n_fft),
        auto_model_weights_from_analysis=False,
        dissonance_enabled=False,
        dissonance_curve=False,
        dissonance_scale=False,
        compare_models=False,
        compile_per_call=False,
        parallel_processing=False,
    )

    out_xlsx = run_root / "compiled_density_metrics.xlsx"
    compile_metrics.compile_density_metrics_with_pca(
        folder_path=run_root / "stage1",
        output_path=out_xlsx,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
    )
    return pd.read_excel(out_xlsx, sheet_name="Density_Metrics")
