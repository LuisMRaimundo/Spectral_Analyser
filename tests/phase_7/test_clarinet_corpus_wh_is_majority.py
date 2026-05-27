from __future__ import annotations

import os
from pathlib import Path

import librosa
import numpy as np
import pandas as pd
import pytest

from acoustic_density_core import compute_acoustic_density_descriptors
from adaptive_density_engine import AdaptiveDensityEngine
from note_parser import canonical_note_from_filename


def _discover_clarinet_dir() -> Path | None:
    env = os.getenv("CLARINET_SUSTAINS_DIR", "").strip()
    if not env:
        return None
    p = Path(env)
    return p if p.is_dir() else None


def _simple_peak_table(y: np.ndarray, sr: float, n_fft: int = 8192) -> pd.DataFrame:
    frame = y[:n_fft]
    if frame.size < n_fft:
        pad = np.zeros(n_fft, dtype=float)
        pad[: frame.size] = frame
        frame = pad
    mag = np.abs(np.fft.rfft(frame * np.hanning(n_fft)))
    freq = np.fft.rfftfreq(n_fft, d=1.0 / float(sr))
    local_max = np.where((mag[1:-1] > mag[:-2]) & (mag[1:-1] >= mag[2:]))[0] + 1
    if local_max.size == 0:
        return pd.DataFrame(columns=["frequency_hz", "power"])
    keep = local_max[np.argsort(mag[local_max])[-120:]]
    sel_f = freq[keep]
    sel_p = np.square(mag[keep])
    ok = np.isfinite(sel_f) & np.isfinite(sel_p) & (sel_f > 20.0) & (sel_p > 0.0)
    return pd.DataFrame({"frequency_hz": sel_f[ok].astype(float), "power": sel_p[ok].astype(float)})


def test_clarinet_corpus_wh_is_majority() -> None:
    corpus_dir = _discover_clarinet_dir()
    if corpus_dir is None:
        pytest.skip("Set CLARINET_SUSTAINS_DIR to run corpus-level clarinet wH test.")

    files = sorted(
        [
            p
            for p in corpus_dir.rglob("*")
            if p.suffix.lower() in {".wav", ".flac", ".aif", ".aiff", ".mp3"}
        ]
    )
    if not files:
        pytest.skip("No audio files found under CLARINET_SUSTAINS_DIR.")

    engine = AdaptiveDensityEngine()
    used = 0
    for fp in files:
        note_token, _ = canonical_note_from_filename(fp.name, parent_folder=fp.parent.name)
        if not note_token:
            continue
        try:
            f0_hz = float(librosa.note_to_hz(note_token))
        except Exception:
            continue
        try:
            y, sr = librosa.load(str(fp), sr=None, mono=True, duration=1.5)
        except Exception:
            continue
        if y.size == 0:
            continue
        peaks_df = _simple_peak_table(np.asarray(y, dtype=float), float(sr))
        if peaks_df.empty:
            continue
        desc = compute_acoustic_density_descriptors(
            peaks_df,
            f0_hz=f0_hz,
            f0_fit_accepted=True,
            density_summation_mode="his_note_adaptive",
            sr_hz=float(sr),
            n_fft=8192,
        )
        obs = (
            float(desc.get("pure_observation_w_h", 0.0)),
            float(desc.get("pure_observation_w_i", 0.0)),
            float(desc.get("pure_observation_w_s", 0.0)),
        )
        engine.update(obs, evidence_strength=1.0)
        used += 1

    if used < 10:
        pytest.skip("Not enough usable clarinet notes for stable adaptive-profile estimate.")
    assert float(engine.state_dict()["profile_h"]) >= 0.50
