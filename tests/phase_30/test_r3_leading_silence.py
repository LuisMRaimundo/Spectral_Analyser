"""R3 — leading/trailing digital silence ≤ 2 s matches the trimmed take."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from audio_silence_trim import trim_digital_silence
from proc_audio import AudioProcessor


def _tone(sr: int = 44100, sec: float = 0.25) -> np.ndarray:
    t = np.arange(int(sr * sec)) / float(sr)
    y = np.zeros_like(t)
    for n in range(1, 9):
        y += (0.5 ** (n - 1)) * np.sin(2.0 * np.pi * n * 440.0 * t + 0.3)
    peak = float(np.max(np.abs(y))) or 1.0
    return (y / peak).astype(np.float64)


@pytest.mark.parametrize("pad_s", [0.0, 0.5, 2.0])
@pytest.mark.parametrize("side", ["lead", "trail"])
def test_trim_recovers_tone(pad_s: float, side: str) -> None:
    sr = 44100
    y0 = _tone(sr)
    pad = np.zeros(int(pad_s * sr), dtype=np.float64)
    y = np.concatenate([pad, y0] if side == "lead" else [y0, pad])
    got, meta = trim_digital_silence(y, sr)
    assert got.size == y0.size
    assert np.allclose(got, y0, atol=1e-12)
    if pad_s == 0.0:
        assert meta["silence_trim_applied"] is False
    else:
        assert meta["silence_trim_applied"] is True
        key = "lead_trim_s" if side == "lead" else "trail_trim_s"
        assert meta[key] == pytest.approx(pad_s, abs=1.0 / sr)


def test_load_audio_files_trims_lead_and_trail(tmp_path: Path) -> None:
    sr = 44100
    y0 = _tone(sr)
    base = tmp_path / "A4_base.wav"
    lead = tmp_path / "A4_lead.wav"
    trail = tmp_path / "A4_trail.wav"
    sf.write(str(base), y0, sr)
    sf.write(str(lead), np.concatenate([np.zeros(int(0.5 * sr)), y0]), sr)
    sf.write(str(trail), np.concatenate([y0, np.zeros(int(2.0 * sr))]), sr)

    def _loaded(path: Path) -> np.ndarray:
        ap = AudioProcessor()
        ap.load_audio_files([path])
        assert ap.audio_data
        return np.asarray(ap.audio_data[0][0], dtype=np.float64)

    y_base = _loaded(base)
    y_lead = _loaded(lead)
    y_trail = _loaded(trail)
    n = min(y_base.size, y_lead.size, y_trail.size)
    assert n > 1000
    assert np.allclose(y_lead[:n], y_base[:n], atol=1e-9)
    assert np.allclose(y_trail[:n], y_base[:n], atol=1e-9)
