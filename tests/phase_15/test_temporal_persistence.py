from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from constants import PARTIAL_PERSISTENCE_MIN_FRACTION
from harmonic_peak_validation import apply_harmonic_body_stop
from metric_contract import get_metric_definition
from temporal_persistence import (
    LOW_TEMPORAL_PERSISTENCE,
    apply_persistence_gate,
    detect_frame_peaks,
    overlap_factor,
    persistence_metrics,
)


def _steady_plus_burst_stft(
    *,
    n_bins: int = 256,
    n_frames: int = 40,
    steady_bin: int = 40,
    burst_bin: int = 180,
    burst_frames: tuple[int, int] = (10, 12),
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(0)
    freqs = np.arange(n_bins, dtype=float) * 10.0
    mags = np.ones((n_bins, n_frames), dtype=float) + 0.02 * rng.random((n_bins, n_frames))
    mags[steady_bin, :] = 20.0
    mags[steady_bin - 1, :] = 7.0
    mags[steady_bin + 1, :] = 7.0
    a, b = burst_frames
    mags[burst_bin, a:b] = 20.0
    mags[burst_bin - 1, a:b] = 7.0
    mags[burst_bin + 1, a:b] = 7.0
    return mags, freqs


def test_overlap_and_contract() -> None:
    assert overlap_factor(n_fft=4096, hop_length=1024) == pytest.approx(4.0)
    defn = get_metric_definition("persistence_fraction")
    assert defn is not None
    assert defn.input_domain == "per-frame sustain peaks"


def test_steady_partial_accepted_burst_rejected() -> None:
    mags, freqs = _steady_plus_burst_stft()
    peaks = detect_frame_peaks(mags, freqs, frame_start=0, frame_end=40)
    n_frames = 40
    steady_hz = float(freqs[40])
    burst_hz = float(freqs[180])
    steady = persistence_metrics(steady_hz, peaks, tol_hz=15.0, sustain_frame_count=n_frames)
    burst = persistence_metrics(burst_hz, peaks, tol_hz=15.0, sustain_frame_count=n_frames)
    assert steady["persistence_fraction"] >= 0.95
    assert burst["persistence_fraction"] == pytest.approx(2.0 / 40.0)
    rows = apply_persistence_gate(
        [
            {
                "Frequency (Hz)": steady_hz,
                "extracted_frequency_hz": steady_hz,
                "search_tol_hz": 15.0,
                "include_for_density": True,
                "candidate_status": "strict_validated",
            },
            {
                "Frequency (Hz)": burst_hz,
                "extracted_frequency_hz": burst_hz,
                "search_tol_hz": 15.0,
                "include_for_density": True,
                "candidate_status": "strict_validated",
            },
        ],
        peaks,
        sustain_frame_count=n_frames,
        min_fraction=PARTIAL_PERSISTENCE_MIN_FRACTION,
    )
    assert rows[0]["include_for_density"] is True
    assert rows[1]["include_for_density"] is False
    assert rows[1]["candidate_status"] == LOW_TEMPORAL_PERSISTENCE
    assert str(rows[1]["exclusion_reason"]).startswith("low_temporal_persistence")


def test_floor_like_bins_have_low_persistence() -> None:
    mags, freqs = _steady_plus_burst_stft()
    # Leave 12 kHz-ish bins as floor ripple only (no injected peak).
    floor_hz = [12010.0, 12090.0, 12190.0]
    # Spectrum only goes to 2550 Hz in the helper; place floor bins in-band.
    floor_bins = [200, 210, 220]
    floor_hz = [float(freqs[k]) for k in floor_bins]
    peaks = detect_frame_peaks(mags, freqs)
    for f in floor_hz:
        p = persistence_metrics(f, peaks, tol_hz=20.0, sustain_frame_count=40)
        assert p["persistence_fraction"] < 0.3


def test_body_stop_does_not_overwrite_persistence_reason() -> None:
    rows = [
        {
            "Harmonic Number": 20,
            "expected_frequency_hz": 2200.0,
            "Frequency (Hz)": 2200.0,
            "extracted_frequency_hz": 2200.0,
            "include_for_density": False,
            "candidate_status": LOW_TEMPORAL_PERSISTENCE,
            "exclusion_reason": "low_temporal_persistence (p=0.100)",
            "Magnitude (dB)": 5.0,
        }
    ]
    out, _meta = apply_harmonic_body_stop(
        rows,
        f0_hz=110.0,
        enabled=True,
        density_frequency_ceiling_hz=20000.0,
    )
    assert str(out[0]["exclusion_reason"]).startswith("low_temporal_persistence")
    assert out[0]["candidate_status"] == LOW_TEMPORAL_PERSISTENCE


@pytest.mark.live_audio
def test_iowa_a2_audio_persistence_if_present() -> None:
    audio = Path(
        r"D:\METAIS\TUBA\Tuba\Tuba_Yowa\IOWA_tuba_pp"
        r"\_Sustains_Stable\IOWA_Tub.pp.A2_SustainStable.aif"
    )
    if not audio.is_file():
        pytest.skip("A2 audio not mounted")
    import librosa

    from proc_audio import AudioProcessor

    y, sr = librosa.load(str(audio), sr=None, mono=True)
    ap = AudioProcessor()
    ap.y = y
    ap.sr = float(sr)
    ap.n_fft = 4096
    ap.hop_length = 1024
    ap.window = "hann"
    S = librosa.stft(y, n_fft=4096, hop_length=1024, window="hann", center=True)
    ap.S = S
    ap.freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)
    peaks = ap._ensure_sustain_frame_peaks()
    n = int(ap.sustain_frame_count or 0)
    assert n > 10
    f0 = 110.01
    mag = np.abs(np.asarray(S))
    f0i = int(ap.sustain_frame_start or 0)
    f1i = int(ap.sustain_frame_end or mag.shape[1])
    avg = np.mean(mag[:, f0i:f1i], axis=1)
    fr = np.asarray(ap.freqs, dtype=float)
    # Spec: score against the time-averaged peak, not n·f0.
    for n_h in range(1, 9):
        nom = f0 * n_h
        band = np.where(np.abs(fr - nom) <= 0.30 * f0)[0]
        meas = float(fr[int(band[int(np.argmax(avg[band]))])])
        p = persistence_metrics(
            meas, peaks, tol_hz=0.30 * f0, sustain_frame_count=n
        )
        assert p["persistence_fraction"] >= 0.95, (n_h, meas, p["persistence_fraction"])
    # High-n floor slots must fail the 0.7 inclusion gate with body stop off.
    # Unstructured ripple is < 0.3 (see test_floor_like_bins_have_low_persistence).
    # On this take the 12 094 Hz line is a weak but temporally present feature
    # (p ≈ 0.6 at n_fft=4096); it still fails the gate.
    floor_rows = apply_persistence_gate(
        [
            {
                "Frequency (Hz)": f,
                "extracted_frequency_hz": f,
                "search_tol_hz": 0.30 * f0,
                "include_for_density": True,
                "candidate_status": "strict_validated",
            }
            for f in (12011.6, 12094.3, 12191.7)
        ],
        peaks,
        sustain_frame_count=n,
        min_fraction=PARTIAL_PERSISTENCE_MIN_FRACTION,
    )
    for row, f in zip(floor_rows, (12011.6, 12094.3, 12191.7)):
        assert row["include_for_density"] is False, (f, row["persistence_fraction"])
        assert row["candidate_status"] == LOW_TEMPORAL_PERSISTENCE
        assert float(row["persistence_fraction"]) < PARTIAL_PERSISTENCE_MIN_FRACTION
