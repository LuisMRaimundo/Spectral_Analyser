"""Acoustic-validity contracts per instrument family.

These tests encode *physical* expectations that a correct spectral analysis
must satisfy, so that acoustically impossible results fail in CI rather than
being caught by a human reading a workbook.

Motivating regression: a prominence/validation bug made a dense low-register
cello C2 (which should resolve dozens of harmonics) report FEWER included
harmonics than a sparse high flute note — i.e. the cello came out as "less
harmonically rich" than the flute, which is physically impossible. The
ordering guard below (``test_dense_low_note_is_richer_than_sparse_high_note``)
locks that out permanently.

Signals are synthetic harmonic stacks with known partial counts, rendered to
WAV and run through the real per-note pipeline. We assert on
``include_for_density`` from the per-note ``Harmonic Spectrum`` sheet.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from proc_audio import AudioProcessor


def _write_harmonic_wav(
    path: Path,
    *,
    f0_hz: float,
    n_harmonics: int,
    sr_hz: int = 44100,
    seconds: float = 1.5,
    rolloff: float = 1.0,
) -> Path:
    """Render ``n_harmonics`` partials at ``f0`` with 1/n**rolloff amplitudes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(sr_hz * seconds), dtype=float) / float(sr_hz)
    y = np.zeros_like(t)
    nyq = 0.45 * sr_hz
    for n in range(1, int(n_harmonics) + 1):
        fn = float(n) * float(f0_hz)
        if fn >= nyq:
            break
        y += (1.0 / float(n) ** rolloff) * np.sin(2.0 * np.pi * fn * t)
    peak = float(np.max(np.abs(y))) or 1.0
    y = 0.25 * y / peak
    pcm = np.asarray(np.clip(y, -1.0, 1.0) * 32767.0, dtype=np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr_hz))
        wf.writeframes(pcm.tobytes())
    return path


def _run_note(tmp_path: Path, name: str, *, f0_hz: float, n_harmonics: int,
              n_fft: int) -> pd.DataFrame:
    wav = _write_harmonic_wav(
        tmp_path / "audio" / f"{name}.wav", f0_hz=f0_hz, n_harmonics=n_harmonics
    )
    out = tmp_path / f"run_{name}"
    ap = AudioProcessor()
    ap.load_audio_files([str(wav)])
    ap.apply_filters_and_generate_data(
        results_directory=out,
        n_fft=n_fft,
        zero_padding=2,
        freq_max=20000.0,
        dissonance_enabled=False,
        dissonance_curve=False,
        dissonance_scale=False,
        compare_models=False,
        compile_per_call=False,
        parallel_processing=False,
    )
    wb = next(out.rglob("spectral_analysis.xlsx"))
    return pd.read_excel(wb, sheet_name="Harmonic Spectrum")


def _included_orders(harm: pd.DataFrame) -> list[int]:
    inc = harm.loc[harm["include_for_density"].astype(bool)]
    return sorted(
        pd.to_numeric(inc["Harmonic Number"], errors="coerce")
        .dropna()
        .astype(int)
        .tolist()
    )


@pytest.mark.slow
def test_dense_low_string_resolves_many_continuous_harmonics(tmp_path: Path) -> None:
    """Cello-like C2 (f0≈65 Hz, dense) must resolve many low-order partials."""
    harm = _run_note(tmp_path, "cello_C2", f0_hz=65.41, n_harmonics=60, n_fft=16384)
    orders = _included_orders(harm)
    assert len(orders) >= 30, f"dense low note: only {len(orders)} included: {orders}"
    low = [n for n in orders if n <= 30]
    assert len(low) >= 20, f"low-order coverage too sparse: {low}"
    # The accepted set must not be dominated by isolated high-order spikes.
    high_sparse = [n for n in orders if 40 < n <= 80]
    assert len(high_sparse) <= len(low), (
        f"high-order sparse accepts {high_sparse} exceed low-order {low}"
    )


@pytest.mark.slow
def test_sparse_high_flute_resolves_few_harmonics(tmp_path: Path) -> None:
    """Flute-like E5 (f0≈659 Hz) with few partials yields a modest count."""
    harm = _run_note(tmp_path, "flute_E5", f0_hz=659.26, n_harmonics=6, n_fft=8192)
    orders = _included_orders(harm)
    # Six partials were synthesised; allow a small margin but reject a flood
    # of spurious high-order accepts.
    assert 1 <= len(orders) <= 12, f"sparse high note unexpected count: {orders}"


@pytest.mark.slow
def test_dense_low_note_is_richer_than_sparse_high_note(tmp_path: Path) -> None:
    """Physical-impossibility guard: a dense low cello note must report at
    least as many included harmonics as a sparse high flute note."""
    cello = _included_orders(
        _run_note(tmp_path, "cello_C2b", f0_hz=65.41, n_harmonics=60, n_fft=16384)
    )
    flute = _included_orders(
        _run_note(tmp_path, "flute_E5b", f0_hz=659.26, n_harmonics=6, n_fft=8192)
    )
    assert len(cello) >= len(flute), (
        f"physically impossible: dense cello C2 included {len(cello)} harmonics "
        f"but sparse flute E5 included {len(flute)}"
    )
