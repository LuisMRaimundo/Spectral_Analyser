"""Lead/trail digital-silence trim (R3). Does not import or modify ADSR_Segmenter."""

from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np

DIGITAL_SILENCE_ABS = 1e-7


def trim_digital_silence(
    y: np.ndarray,
    sr: int,
    *,
    abs_threshold: float = DIGITAL_SILENCE_ABS,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Drop leading and trailing samples below ``abs_threshold``.

    Used so a file with ≤ 2 s of digital pad matches the trimmed take.
    ADSR segmentation is unchanged.
    """
    arr = np.asarray(y, dtype=np.float64)
    if arr.ndim > 1:
        arr = np.mean(arr, axis=1)
    n = int(arr.size)
    meta: Dict[str, Any] = {
        "lead_trim_samples": 0,
        "trail_trim_samples": 0,
        "lead_trim_s": 0.0,
        "trail_trim_s": 0.0,
        "silence_trim_applied": False,
        "samples_before": n,
        "samples_after": n,
        "abs_threshold": float(abs_threshold),
    }
    if n == 0:
        return arr, meta
    active = np.flatnonzero(np.abs(arr) > float(abs_threshold))
    if active.size == 0:
        meta["lead_trim_samples"] = n
        meta["lead_trim_s"] = float(n) / float(sr) if sr else 0.0
        meta["silence_trim_applied"] = True
        meta["samples_after"] = 0
        return arr[:0], meta
    start = int(active[0])
    end = int(active[-1]) + 1
    out = arr[start:end]
    meta["lead_trim_samples"] = start
    meta["trail_trim_samples"] = n - end
    meta["lead_trim_s"] = float(start) / float(sr) if sr else 0.0
    meta["trail_trim_s"] = float(n - end) / float(sr) if sr else 0.0
    meta["silence_trim_applied"] = bool(start > 0 or end < n)
    meta["samples_after"] = int(out.size)
    return out, meta
