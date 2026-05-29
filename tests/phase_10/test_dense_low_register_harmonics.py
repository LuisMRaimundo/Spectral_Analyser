from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from proc_audio import AudioProcessor


def _write_dense_harmonic_wav(
    path: Path,
    *,
    f0_hz: float,
    n_harmonics: int,
    sr_hz: int = 44100,
    seconds: float = 2.0,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(sr_hz * seconds), dtype=float) / float(sr_hz)
    y = np.zeros_like(t)
    for n in range(1, int(n_harmonics) + 1):
        y += (1.0 / float(n)) * np.sin(2.0 * np.pi * float(n) * float(f0_hz) * t)
    y = 0.25 * y / np.max(np.abs(y))
    pcm = np.asarray(np.clip(y, -1.0, 1.0) * 32767.0, dtype=np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr_hz))
        wf.writeframes(pcm.tobytes())
    return path


def test_dense_c2_like_spectrum_includes_many_low_register_harmonics(tmp_path: Path) -> None:
    """Cello-like dense harmonic stacks must not collapse to a handful of orders."""
    f0 = 65.41
    wav = _write_dense_harmonic_wav(
        tmp_path / "audio" / "C2_dense.wav",
        f0_hz=f0,
        n_harmonics=60,
    )
    out = tmp_path / "run"
    ap = AudioProcessor()
    ap.load_audio_files([str(wav)])
    ap.apply_filters_and_generate_data(
        results_directory=out,
        n_fft=16384,
        freq_max=8000.0,
        dissonance_enabled=False,
        dissonance_curve=False,
        dissonance_scale=False,
        compare_models=False,
        compile_per_call=False,
        parallel_processing=False,
    )
    wb = next(out.rglob("spectral_analysis.xlsx"))
    harm = pd.read_excel(wb, sheet_name="Harmonic Spectrum")
    included = harm.loc[harm["include_for_density"].astype(bool)].copy()
    included_hnums = pd.to_numeric(included["Harmonic Number"], errors="coerce").dropna().astype(int)
    assert len(included_hnums) >= 30, (
        f"expected >=30 strict density harmonics for dense C2-like signal, got {len(included_hnums)}"
    )
    # No large gaps in the first 30 orders: real partials should fill in continuously.
    first30 = included_hnums[included_hnums <= 30]
    assert len(first30) >= 20, (
        f"expected continuous low-order coverage, got only {sorted(first30.tolist())}"
    )
    # Weak high-order noise spikes must not dominate the accepted set.
    high_sparse = included_hnums[(included_hnums > 40) & (included_hnums <= 80)]
    assert len(high_sparse) <= len(first30), (
        f"high-order sparse accepts {sorted(high_sparse.tolist())} should not exceed low-order count"
    )
