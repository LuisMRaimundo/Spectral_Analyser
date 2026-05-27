from __future__ import annotations

import wave
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np

from proc_audio import AudioProcessor


def write_sine_wav(path: Path, *, freq_hz: float, sr_hz: int = 22050, seconds: float = 1.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(sr_hz * seconds), dtype=float) / float(sr_hz)
    y = 0.30 * np.sin(2.0 * np.pi * float(freq_hz) * t)
    pcm = np.asarray(np.clip(y, -1.0, 1.0) * 32767.0, dtype=np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr_hz))
        wf.writeframes(pcm.tobytes())
    return path


def run_stage1_synthetic_notes(
    base_dir: Path,
    *,
    notes: Iterable[Tuple[str, float]],
) -> List[Path]:
    audio_dir = base_dir / "audio"
    run_dir = base_dir / "run"
    wavs: List[Path] = []
    for note, f0 in notes:
        wavs.append(write_sine_wav(audio_dir / f"{note}_synthetic.wav", freq_hz=float(f0)))

    ap = AudioProcessor()
    ap.load_audio_files([str(p) for p in wavs])
    ap.apply_filters_and_generate_data(
        results_directory=run_dir,
        dissonance_enabled=False,
        dissonance_curve=False,
        dissonance_scale=False,
        compare_models=False,
        compile_per_call=False,
        parallel_processing=False,
    )

    workbooks = sorted(run_dir.rglob("spectral_analysis.xlsx"))
    if not workbooks:
        raise AssertionError("Stage 1 produced no spectral_analysis.xlsx files.")
    return workbooks
