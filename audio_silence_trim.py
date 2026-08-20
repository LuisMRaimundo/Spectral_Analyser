"""Lead/trail digital-silence trim (R3). Does not import or modify ADSR_Segmenter."""

from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np

DIGITAL_SILENCE_ABS = 1e-7


MIN_PAD_S = 0.005


def trim_digital_silence(
    y: np.ndarray,
    sr: int,
    *,
    abs_threshold: float = DIGITAL_SILENCE_ABS,
    min_pad_s: float = MIN_PAD_S,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Drop leading and trailing *pads* below ``abs_threshold``.

    A pad is a run of at least ``min_pad_s`` (default 5 ms). Single
    zero-crossings at tone onset are kept. An all-silent file is kept
    as a valid zero signal. ADSR segmentation is unchanged.
    """
    arr = np.asarray(y, dtype=np.float64)
    if arr.ndim > 1:
        arr = np.mean(arr, axis=1)
    n = int(arr.size)
    min_run = max(1, int(round(float(min_pad_s) * float(sr)))) if sr else 1
    meta: Dict[str, Any] = {
        "lead_trim_samples": 0,
        "trail_trim_samples": 0,
        "lead_trim_s": 0.0,
        "trail_trim_s": 0.0,
        "silence_trim_applied": False,
        "samples_before": n,
        "samples_after": n,
        "abs_threshold": float(abs_threshold),
        "min_pad_s": float(min_pad_s),
    }
    if n == 0:
        return arr, meta
    active = np.flatnonzero(np.abs(arr) > float(abs_threshold))
    if active.size == 0:
        return arr, meta
    start = int(active[0])
    end = int(active[-1]) + 1
    if start < min_run:
        start = 0
    if (n - end) < min_run:
        end = n
    out = arr[start:end]
    meta["lead_trim_samples"] = start
    meta["trail_trim_samples"] = n - end
    meta["lead_trim_s"] = float(start) / float(sr) if sr else 0.0
    meta["trail_trim_s"] = float(n - end) / float(sr) if sr else 0.0
    meta["silence_trim_applied"] = bool(start > 0 or end < n)
    meta["samples_after"] = int(out.size)
    return out, meta
