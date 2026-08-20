"""Per-note estimated SNR from already-computed harmonic peak-vs-floor values."""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np
import pandas as pd


def estimated_snr_db_from_harmonics(harm_df: Optional[pd.DataFrame]) -> float:
    """Power-weighted mean of validated-harmonic ``snr_db`` (peak vs local floor).

    ``snr_db`` is already computed per slot in ``harmonic_peak_validation``.
    This aggregates it to one note-level conditioner for EWSD comparisons.
    """
    if harm_df is None or not isinstance(harm_df, pd.DataFrame) or harm_df.empty:
        return float("nan")
    if "snr_db" not in harm_df.columns:
        return float("nan")
    frame = harm_df
    if "include_for_density" in frame.columns:
        mask = frame["include_for_density"].astype(str).str.lower().isin(
            {"true", "1", "1.0"}
        )
        if not bool(mask.any()):
            return float("nan")
        frame = frame.loc[mask]
    snr = pd.to_numeric(frame["snr_db"], errors="coerce")
    if "Power_raw" in frame.columns:
        w = pd.to_numeric(frame["Power_raw"], errors="coerce")
    elif "Amplitude_raw" in frame.columns:
        a = pd.to_numeric(frame["Amplitude_raw"], errors="coerce")
        w = a * a
    else:
        w = pd.Series(1.0, index=frame.index)
    ok = np.isfinite(snr) & np.isfinite(w) & (w > 0.0)
    if not bool(ok.any()):
        return float("nan")
    num = float(np.sum(w[ok] * snr[ok]))
    den = float(np.sum(w[ok]))
    if den <= 0.0 or not math.isfinite(num):
        return float("nan")
    return num / den


def estimated_snr_db_or_nan(value: Any) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return x if math.isfinite(x) else float("nan")
