# -*- coding: utf-8 -*-
# audio_utils.py – Utilities for audio I/O, units, and perceptual tolerances.

"""
Audio utilities:
- Robust audio file loading (fallback chain: librosa → soundfile → scipy → pydub).
- Consistent conversions between amplitude, power, and dB (magnitude/power).
- Perceptual harmonic tolerance (cents + absolute Hz floor) for partial _matching_.

Note: keep this module as the single source of truth for unit conversions and tolerances.
"""

from __future__ import annotations

import logging
from pathlib import Path
import numpy as np

# --- I/O stacks (fallback order) ---
import librosa
import soundfile as sf
from scipy.io import wavfile
from pydub import AudioSegment

logger = logging.getLogger(__name__)


# ======================================================================
#                           AUDIO LOADING
# ======================================================================

def load_audio_with_fallback(file_path: Path) -> tuple[np.ndarray | None, int | None]:
    """
    Load mono audio as float32, preserving sample rate, using the fallback chain.
    Order: librosa → soundfile → scipy.io.wavfile (WAV only) → pydub (ffmpeg).

    Args:
        file_path: path to the audio file.

    Returns:
        (y, sr), or (None, None) if every loading attempt fails.
    """
    path_str = str(file_path)

    # 1) librosa
    try:
        y, sr = librosa.load(path_str, sr=None, mono=True)
        if y is not None and len(y) > 0:
            logger.debug(f"Loaded '{path_str}' with librosa.")
            return y.astype(np.float32, copy=False), int(sr)
    except Exception as e:
        logger.debug(f"librosa failed for '{path_str}': {e}")

    # 2) soundfile
    try:
        y, sr = sf.read(path_str, dtype="float32", always_2d=False)
        if y.ndim > 1:  # mono
            y = np.mean(y, axis=1)
        logger.debug(f"Loaded '{path_str}' with soundfile.")
        return y.astype(np.float32, copy=False), int(sr)
    except Exception as e:
        logger.debug(f"soundfile failed for '{path_str}': {e}")

    # 3) scipy.io.wavfile (WAV only)
    try:
        if path_str.lower().endswith(".wav"):
            sr, y = wavfile.read(path_str)
            if y.ndim > 1:
                y = np.mean(y, axis=1)
            if y.dtype.kind != "f":
                info = np.iinfo(y.dtype)
                y = y.astype(np.float32) / max(abs(info.min), info.max)
            logger.debug(f"Loaded '{path_str}' with scipy.io.wavfile.")
            return y.astype(np.float32, copy=False), int(sr)
    except Exception as e:
        logger.debug(f"scipy.io.wavfile failed for '{path_str}': {e}")

    # 4) pydub (ffmpeg)
    try:
        audio = AudioSegment.from_file(path_str)
        if audio.channels > 1:
            audio = audio.set_channels(1)
        y = np.array(audio.get_array_of_samples(), dtype=np.float32)
        y /= float(1 << (8 * audio.sample_width - 1))  # normalise to [-1, 1]
        sr = int(audio.frame_rate)
        logger.debug(f"Loaded '{path_str}' with pydub.")
        return y.astype(np.float32, copy=False), sr
    except Exception as e:
        logger.debug(f"pydub failed for '{path_str}': {e}")

    logger.error(f"All loading methods failed for '{path_str}'")
    return None, None


# ======================================================================
#                   UNITS: AMPLITUDE / POWER / dB
# ======================================================================

# Conventions:
# - Magnitude (dB) = 20*log10(|X|)
# - RMS (dB) = 20*log10(RMS amplitude)
_EPS = np.finfo(float).tiny

def amp_to_db_mag(a: np.ndarray | float) -> np.ndarray | float:
    """Amplitude linear → Magnitude (dB)."""
    return 20.0 * np.log10(np.maximum(np.asarray(a, dtype=float), _EPS))

def db_mag_to_amp(db: np.ndarray | float) -> np.ndarray | float:
    """Magnitude (dB) → Amplitude linear."""
    return np.power(10.0, np.asarray(db, dtype=float) / 20.0)

def power_to_db(p: np.ndarray | float) -> np.ndarray | float:
    """Linear power → power dB."""
    return 10.0 * np.log10(np.maximum(np.asarray(p, dtype=float), _EPS))

def db_to_power(dbp: np.ndarray | float) -> np.ndarray | float:
    """Power dB → linear power."""
    return np.power(10.0, np.asarray(dbp, dtype=float) / 10.0)


# ======================================================================
#        PERCEPTUAL TOLERANCE: CENTS ↔ RATIO ↔ HZ (with Hz floor)
# ======================================================================

def cents_to_ratio(cents: float) -> float:
    """Convert cents → frequency ratio."""
    return float(2.0 ** (float(cents) / 1200.0))

def ratio_to_cents(ratio: float) -> float:
    """Convert frequency ratio → cents."""
    r = max(float(ratio), _EPS)
    return float(1200.0 * np.log2(r))

def tol_hz_from_cents(f_ref: float, cents: float, min_hz: float = 2.0) -> float:
    """
    Convert a cents tolerance to Hz, with an absolute Hz floor.
    f_ref: reference frequency (e.g. h*f0)
    cents: tolerance in cents (e.g. 5.0)
    min_hz: absolute floor (e.g. 2.0 Hz)
    """
    f_ref = float(f_ref)
    cents = float(cents)
    hz = f_ref * (2.0 ** (cents / 1200.0) - 1.0)
    return float(max(min_hz, hz))

def harmonic_tolerance_hz(f0: float,
                          h: int,
                          search_band_cents: float = 15.0,
                          min_tolerance_hz: float = 2.0) -> float:
    """
    Perceptual tolerance for harmonic h: Δf_h = max(min_tolerance_hz, (h*f0)*(2^(cents/1200)-1)).
    Uses cents (perceptual consistency) and an absolute Hz floor (robustness at low frequencies).
    """
    f_ref = float(h) * float(f0)
    return tol_hz_from_cents(f_ref, search_band_cents, min_tolerance_hz)
