from __future__ import annotations

import os
from pathlib import Path
from typing import List

import librosa
import numpy as np
import pytest

from inharmonicity_model import fit_inharmonicity_coefficient
from note_parser import canonical_note_from_filename


def _discover_clarinet_dir() -> Path | None:
    env = os.getenv("CLARINET_SUSTAINS_DIR", "").strip()
    if env:
        p = Path(env)
        if p.is_dir():
            return p
    return None


def _simple_peak_freqs(y: np.ndarray, sr: float, n_fft: int = 8192) -> np.ndarray:
    frame = y[:n_fft]
    if frame.size < n_fft:
        pad = np.zeros(n_fft, dtype=float)
        pad[: frame.size] = frame
        frame = pad
    mag = np.abs(np.fft.rfft(frame * np.hanning(n_fft)))
    freq = np.fft.rfftfreq(n_fft, d=1.0 / float(sr))
    local_max = np.where((mag[1:-1] > mag[:-2]) & (mag[1:-1] >= mag[2:]))[0] + 1
    if local_max.size == 0:
        return np.array([], dtype=float)
    # Keep strongest peaks only, avoid very low-frequency junk.
    keep = local_max[np.argsort(mag[local_max])[-80:]]
    sel = freq[keep]
    sel = sel[np.isfinite(sel) & (sel > 20.0)]
    return np.sort(sel.astype(float))


def test_clarinet_corpus_B_is_small() -> None:
    corpus_dir = _discover_clarinet_dir()
    if corpus_dir is None:
        pytest.skip("Set CLARINET_SUSTAINS_DIR to run corpus-level clarinet B test.")

    files = sorted(
        [
            p
            for p in corpus_dir.rglob("*")
            if p.suffix.lower() in {".wav", ".flac", ".aif", ".aiff", ".mp3"}
        ]
    )
    if not files:
        pytest.skip("No audio files found under CLARINET_SUSTAINS_DIR.")

    b_values: List[float] = []
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
        peaks = _simple_peak_freqs(np.asarray(y, dtype=float), float(sr))
        if peaks.size == 0:
            continue
        fit = fit_inharmonicity_coefficient(
            candidate_freqs_hz=peaks,
            f0_hz=f0_hz,
            order_cap=40,
            cents_window=80.0,
        )
        if fit["fit_status"] == "ok":
            b_values.append(float(fit["inharmonicity_coefficient_B"]))

    if not b_values:
        pytest.skip("No successful inharmonicity fits obtained from clarinet corpus.")
    assert float(np.mean(b_values)) < 1e-5
