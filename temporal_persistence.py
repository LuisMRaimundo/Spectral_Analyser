"""Per-frame peak persistence (Phase B).

The time-averaged spectrum cannot tell a stable partial from floor ripple.
This module detects local maxima on each sustain STFT frame and scores a
candidate frequency by the fraction of those frames that contain a peak
within ``tol_hz``.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from constants import (
    FRAME_PEAK_MIN_ABOVE_MEDIAN_DB,
    PARTIAL_PERSISTENCE_MIN_FRACTION,
)

LOW_TEMPORAL_PERSISTENCE = "low_temporal_persistence"


def overlap_factor(*, n_fft: int, hop_length: int) -> float:
    hop = max(int(hop_length), 1)
    return float(max(int(n_fft), 1)) / float(hop)


def frame_duration_s(*, hop_length: int, sr_hz: float) -> float:
    if not np.isfinite(sr_hz) or sr_hz <= 0.0:
        return float("nan")
    return float(max(int(hop_length), 1)) / float(sr_hz)


def sustain_frame_span(
    *,
    n_frames: int,
    hop_length: int,
    sr_hz: float,
    sustain_start_sample: Optional[int] = None,
    sustain_end_sample: Optional[int] = None,
) -> tuple[int, int]:
    """Inclusive-start, exclusive-end frame indices covering the sustain."""
    n = max(int(n_frames), 0)
    if n <= 0:
        return 0, 0
    hop = max(int(hop_length), 1)
    if (
        sustain_start_sample is None
        or sustain_end_sample is None
        or int(sustain_end_sample) <= int(sustain_start_sample)
    ):
        return 0, n
    start = int(max(0, min(n, round(float(sustain_start_sample) / hop))))
    end = int(max(start + 1, min(n, round(float(sustain_end_sample) / hop))))
    return start, end


def detect_frame_peaks(
    magnitudes: np.ndarray,
    freqs: np.ndarray,
    *,
    frame_start: int = 0,
    frame_end: Optional[int] = None,
    min_above_median_db: float = FRAME_PEAK_MIN_ABOVE_MEDIAN_DB,
) -> list[dict[str, Any]]:
    """Local maxima on each sustain frame that clear the frame-median gate.

    ``magnitudes`` is ``(n_bins, n_frames)`` linear STFT magnitude.
    """
    mag = np.asarray(magnitudes, dtype=float)
    fr = np.asarray(freqs, dtype=float)
    if mag.ndim != 2 or fr.size < 3:
        return []
    n_bins, n_frames = mag.shape
    n_bins = int(min(n_bins, fr.size))
    start = max(0, int(frame_start))
    end = int(n_frames if frame_end is None else frame_end)
    end = min(n_frames, max(start, end))
    thr_db = float(min_above_median_db)
    rows: list[dict[str, Any]] = []
    for t in range(start, end):
        col = mag[:n_bins, t]
        finite = col[np.isfinite(col) & (col > 0.0)]
        if finite.size < 3:
            continue
        med = float(np.median(finite))
        if not np.isfinite(med) or med <= 0.0:
            continue
        floor_db = 20.0 * np.log10(med)
        for k in range(1, n_bins - 1):
            v = float(col[k])
            if not np.isfinite(v) or v <= 0.0:
                continue
            if not (v > float(col[k - 1]) and v > float(col[k + 1])):
                continue
            peak_db = 20.0 * np.log10(v)
            if peak_db - floor_db < thr_db:
                continue
            rows.append(
                {
                    "frame_index": int(t),
                    "peak_bin_index": int(k),
                    "frequency_hz": float(fr[k]),
                    "magnitude": v,
                    "magnitude_db": float(peak_db),
                }
            )
    return rows


def _band_peak_in_frame(
    mag_col: np.ndarray,
    freqs: np.ndarray,
    freq_hz: float,
    tol_hz: float,
    *,
    min_above_median_db: float = FRAME_PEAK_MIN_ABOVE_MEDIAN_DB,
) -> Optional[tuple[float, float]]:
    """Return ``(frequency_hz, magnitude_db)`` if the band has a usable peak."""
    col = np.asarray(mag_col, dtype=float)
    fr = np.asarray(freqs, dtype=float)
    n = int(min(col.size, fr.size))
    if n < 3:
        return None
    band = np.where(np.abs(fr[:n] - float(freq_hz)) <= float(tol_hz))[0]
    if band.size == 0:
        return None
    k = int(band[int(np.argmax(col[band]))])
    v = float(col[k])
    if not np.isfinite(v) or v <= 0.0:
        return None
    left = float(col[k - 1]) if k > 0 else 0.0
    right = float(col[k + 1]) if k + 1 < n else 0.0
    if not (v >= left and v >= right):
        return None
    exclude = {k - 1, k, k + 1}
    side = np.asarray(
        [float(col[i]) for i in band if i not in exclude],
        dtype=float,
    )
    side = side[np.isfinite(side) & (side > 0.0)]
    if side.size < 3:
        finite = col[np.isfinite(col) & (col > 0.0)]
        med = float(np.median(finite)) if finite.size else float("nan")
    else:
        med = float(np.median(side))
    if not np.isfinite(med) or med <= 0.0:
        return None
    peak_db = 20.0 * np.log10(v)
    if peak_db - 20.0 * np.log10(med) < float(min_above_median_db):
        return None
    return float(fr[k]), float(peak_db)


def persistence_metrics(
    freq_hz: float,
    frame_peaks: Sequence[Mapping[str, Any]],
    *,
    tol_hz: float,
    sustain_frame_count: int,
    magnitudes: Optional[np.ndarray] = None,
    freqs: Optional[np.ndarray] = None,
    frame_start: int = 0,
    frame_end: Optional[int] = None,
    min_above_median_db: float = FRAME_PEAK_MIN_ABOVE_MEDIAN_DB,
) -> dict[str, float]:
    """Fraction of sustain frames with a peak within ``tol_hz`` of ``freq_hz``."""
    nan = float("nan")
    out = {
        "persistence_fraction": nan,
        "frequency_jitter_cents": nan,
        "magnitude_jitter_db": nan,
        "persistence_hit_count": 0.0,
    }
    try:
        freq = float(freq_hz)
        tol = float(tol_hz)
        n_frames = int(sustain_frame_count)
    except (TypeError, ValueError):
        return out
    if not np.isfinite(freq) or freq <= 0.0 or n_frames <= 0:
        return out
    if not np.isfinite(tol) or tol <= 0.0:
        tol = 1e-6
    # Prefer the per-frame peak table. Scanning the STFT band for a
    # maximum harvests a noise peak in almost every high-n window and
    # is not "a detected peak" in the Phase B sense.
    if (not frame_peaks) and magnitudes is not None and freqs is not None:
        mag = np.asarray(magnitudes, dtype=float)
        fr = np.asarray(freqs, dtype=float)
        if mag.ndim == 2 and fr.size >= 3:
            start = max(0, int(frame_start))
            end = int(mag.shape[1] if frame_end is None else frame_end)
            end = min(int(mag.shape[1]), max(start, end))
            hits_f: list[float] = []
            hits_db: list[float] = []
            for t in range(start, end):
                hit = _band_peak_in_frame(
                    mag[:, t],
                    fr,
                    freq,
                    tol,
                    min_above_median_db=min_above_median_db,
                )
                if hit is None:
                    continue
                hits_f.append(hit[0])
                hits_db.append(hit[1])
            n_hit = len(hits_f)
            out["persistence_hit_count"] = float(n_hit)
            out["persistence_fraction"] = float(n_hit) / float(n_frames)
            if n_hit >= 2 and freq > 0.0:
                cents = [1200.0 * np.log2(f / freq) for f in hits_f if f > 0.0]
                if len(cents) >= 2:
                    out["frequency_jitter_cents"] = float(
                        np.std(np.asarray(cents, dtype=float))
                    )
                db = [d for d in hits_db if np.isfinite(d)]
                if len(db) >= 2:
                    out["magnitude_jitter_db"] = float(np.std(np.asarray(db, dtype=float)))
            return out
    hits_f: list[float] = []
    hits_db: list[float] = []
    seen_frames: set[int] = set()
    for peak in frame_peaks:
        try:
            pf = float(peak.get("frequency_hz", float("nan")))
            t = int(peak.get("frame_index"))
        except (TypeError, ValueError):
            continue
        if not np.isfinite(pf) or abs(pf - freq) > tol:
            continue
        if t in seen_frames:
            continue
        seen_frames.add(t)
        hits_f.append(pf)
        try:
            hits_db.append(float(peak.get("magnitude_db", float("nan"))))
        except (TypeError, ValueError):
            hits_db.append(float("nan"))
    n_hit = len(seen_frames)
    out["persistence_hit_count"] = float(n_hit)
    out["persistence_fraction"] = float(n_hit) / float(n_frames)
    if n_hit >= 2 and freq > 0.0:
        cents = [1200.0 * np.log2(f / freq) for f in hits_f if f > 0.0]
        if len(cents) >= 2:
            out["frequency_jitter_cents"] = float(np.std(np.asarray(cents, dtype=float)))
        db = [d for d in hits_db if np.isfinite(d)]
        if len(db) >= 2:
            out["magnitude_jitter_db"] = float(np.std(np.asarray(db, dtype=float)))
    return out


def apply_persistence_gate(
    rows: Sequence[Mapping[str, Any]],
    frame_peaks: Sequence[Mapping[str, Any]],
    *,
    sustain_frame_count: int,
    min_fraction: float = PARTIAL_PERSISTENCE_MIN_FRACTION,
    magnitudes: Optional[np.ndarray] = None,
    freqs: Optional[np.ndarray] = None,
    frame_start: int = 0,
    frame_end: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Attach persistence columns and drop low-persistence rows from density."""
    out: list[dict[str, Any]] = []
    min_p = float(min_fraction)
    n_frames = int(sustain_frame_count)
    for raw in rows:
        row = dict(raw)
        try:
            freq = float(
                row.get("extracted_frequency_hz", row.get("Frequency (Hz)", float("nan")))
            )
        except (TypeError, ValueError):
            freq = float("nan")
        try:
            tol = float(row.get("search_tol_hz", row.get("tol_hz", float("nan"))))
        except (TypeError, ValueError):
            tol = float("nan")
        metrics = persistence_metrics(
            freq,
            frame_peaks,
            tol_hz=tol,
            sustain_frame_count=n_frames,
            magnitudes=magnitudes,
            freqs=freqs,
            frame_start=frame_start,
            frame_end=frame_end,
        )
        row["persistence_fraction"] = metrics["persistence_fraction"]
        row["frequency_jitter_cents"] = metrics["frequency_jitter_cents"]
        row["magnitude_jitter_db"] = metrics["magnitude_jitter_db"]
        p = metrics["persistence_fraction"]
        if bool(row.get("include_for_density", False)) and np.isfinite(p) and p < min_p:
            row["include_for_density"] = False
            row["candidate_status"] = LOW_TEMPORAL_PERSISTENCE
            row["exclusion_reason"] = f"{LOW_TEMPORAL_PERSISTENCE} (p={p:.3f})"
        out.append(row)
    return out


def attach_persistence_columns(
    rows: Sequence[Mapping[str, Any]],
    frame_peaks: Sequence[Mapping[str, Any]],
    *,
    sustain_frame_count: int,
    magnitudes: Optional[np.ndarray] = None,
    freqs: Optional[np.ndarray] = None,
    frame_start: int = 0,
    frame_end: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Score candidates without changing inclusion (used for inharmonic rows)."""
    out: list[dict[str, Any]] = []
    n_frames = int(sustain_frame_count)
    for raw in rows:
        row = dict(raw)
        try:
            freq = float(row.get("Frequency (Hz)", row.get("frequency_hz", float("nan"))))
        except (TypeError, ValueError):
            freq = float("nan")
        try:
            tol = float(row.get("search_tol_hz", row.get("tol_hz", float("nan"))))
        except (TypeError, ValueError):
            tol = float("nan")
        if not np.isfinite(tol) or tol <= 0.0:
            # Residual candidates: one bin-width fallback when no slot tolerance.
            try:
                bin_hz = float(row.get("bin_width_hz", float("nan")))
            except (TypeError, ValueError):
                bin_hz = float("nan")
            tol = bin_hz if np.isfinite(bin_hz) and bin_hz > 0.0 else 5.0
        metrics = persistence_metrics(
            freq,
            frame_peaks,
            tol_hz=tol,
            sustain_frame_count=n_frames,
            magnitudes=magnitudes,
            freqs=freqs,
            frame_start=frame_start,
            frame_end=frame_end,
        )
        row["persistence_fraction"] = metrics["persistence_fraction"]
        row["frequency_jitter_cents"] = metrics["frequency_jitter_cents"]
        row["magnitude_jitter_db"] = metrics["magnitude_jitter_db"]
        out.append(row)
    return out
