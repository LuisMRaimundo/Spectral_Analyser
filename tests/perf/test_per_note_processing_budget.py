"""Performance regression guards.

These tests exist because a pure-Python O(n^2) roughness routine
(``mir_descriptors._roughness_aures_1985``) once silently consumed ~76% of
per-note runtime (≈360 s on a cello C2 with n_fft=16384) and shipped to a
user. CI had no timing assertion, so the regression was invisible. The two
guards below lock in:

  1. the vectorised, critical-band-windowed roughness kernel, and
  2. a generous end-to-end per-note wall-clock budget,

so any future change that reintroduces an accidental O(n^2) blow-up fails
fast in CI instead of reaching a user.

Thresholds are deliberately loose (≈10x the observed healthy runtime) so the
tests are robust to slow CI machines while still catching catastrophic
regressions (the historical bug was ~17x slower than the budget here).
"""

from __future__ import annotations

import time
import wave
from pathlib import Path

import numpy as np
import pytest

from mir_descriptors import _roughness_aures_1985


def _brute_force_roughness(freq: np.ndarray, amp: np.ndarray) -> float:
    """Reference O(n^2) implementation (the original formulation)."""
    f = np.asarray(freq, dtype=float)
    a = np.maximum(np.asarray(amp, dtype=float), 0.0)
    s = 0.0
    for i in range(f.size):
        for j in range(i + 1, f.size):
            fi, fj = float(f[i]), float(f[j])
            if fi <= 0.0 or fj <= 0.0:
                continue
            fmin = min(fi, fj)
            df = abs(fi - fj)
            x = df / max(0.25 * fmin + 24.7, 1e-9)
            s += float(a[i] * a[j] * x * np.exp(1.0 - x))
    return float(max(s, 0.0))


def test_roughness_matches_reference_within_tolerance() -> None:
    """The fast kernel must reproduce the brute-force value to ~1e-7."""
    rng = np.random.default_rng(0)
    for n in (50, 300, 1200):
        f = np.sort(rng.uniform(40.0, 8000.0, n))
        a = rng.uniform(0.0, 1.0, n)
        ref = _brute_force_roughness(f, a)
        fast = _roughness_aures_1985(f, a)
        rel = abs(fast - ref) / (abs(ref) + 1e-12)
        assert rel < 1e-6, f"n={n}: rel_err={rel:.2e} (ref={ref}, fast={fast})"


def test_roughness_full_spectrum_size_is_fast() -> None:
    """A full ~16k-bin spectrum must evaluate in well under a second.

    The historical O(n^2) version took ~90 s per call at this size; the
    windowed kernel takes <1 s. A 5 s ceiling catches a reintroduced
    quadratic blow-up with a wide safety margin.
    """
    rng = np.random.default_rng(1)
    f = np.sort(rng.uniform(20.0, 20000.0, 16000))
    a = rng.uniform(0.0, 1.0, 16000)
    t0 = time.perf_counter()
    val = _roughness_aures_1985(f, a)
    elapsed = time.perf_counter() - t0
    assert np.isfinite(val)
    assert elapsed < 5.0, f"roughness on 16k bins took {elapsed:.2f}s (budget 5s)"


def _write_harmonic_wav(
    path: Path,
    *,
    f0_hz: float,
    n_harmonics: int,
    sr_hz: int = 44100,
    seconds: float = 1.5,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(sr_hz * seconds), dtype=float) / float(sr_hz)
    y = np.zeros_like(t)
    for n in range(1, int(n_harmonics) + 1):
        y += (1.0 / float(n)) * np.sin(2.0 * np.pi * float(n) * float(f0_hz) * t)
    y = 0.25 * y / float(np.max(np.abs(y)))
    pcm = np.asarray(np.clip(y, -1.0, 1.0) * 32767.0, dtype=np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr_hz))
        wf.writeframes(pcm.tobytes())
    return path


@pytest.mark.slow
def test_single_note_processing_within_wall_clock_budget(tmp_path: Path) -> None:
    """End-to-end per-note budget on a dense low-register note.

    Uses the worst-case-ish configuration that exposed the regression
    (large n_fft, low f0 → hundreds of harmonic orders). With the fixed
    kernel this completes in ~20 s; a 120 s ceiling flags a catastrophic
    regression (the historical bug was ~333 s) without flaking on slow CI.
    """
    from proc_audio import AudioProcessor

    wav = _write_harmonic_wav(
        tmp_path / "audio" / "C2_dense.wav", f0_hz=65.41, n_harmonics=60
    )
    out = tmp_path / "run"
    ap = AudioProcessor()
    ap.load_audio_files([str(wav)])

    t0 = time.perf_counter()
    ap.apply_filters_and_generate_data(
        results_directory=out,
        n_fft=16384,
        zero_padding=2,
        freq_max=20000.0,
        dissonance_enabled=False,
        dissonance_curve=False,
        dissonance_scale=False,
        compare_models=False,
        compile_per_call=False,
        parallel_processing=False,
    )
    elapsed = time.perf_counter() - t0
    assert elapsed < 120.0, (
        f"single dense note took {elapsed:.1f}s (budget 120s); "
        "suspect an O(n^2) regression in the per-note path."
    )
