"""Balanced component density — Hill number q=1 (F-056).

Pure exponential Shannon entropy of component energy shares. The F-047
participation-ratio pool is unchanged; this module applies a stricter
pool for D1 only.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from validated_partials import CONFIRMED_INHARMONIC_STATUSES, SUBBASS_MEMBERSHIP_MEMBER

DIAGNOSTIC_LOW_FREQUENCY_RESIDUAL_NOT_PARTIAL: str = (
    "diagnostic_low_frequency_residual_not_partial"
)

BALANCED_DENSITY_FORMULA_ID: str = "F-056"
BALANCED_DENSITY_PROVENANCE: str = "defined"
BALANCED_DENSITY_COLUMN: str = "note_balanced_component_density"
BALANCED_DENSITY_POOL_COUNT_COLUMN: str = "note_balanced_component_density_pool_count"
EWSD_ACOUSTIC_BALANCED_COLUMN: str = "EWSD_score_acoustic_balanced"

# Pool definition (verbatim from the F-056 contract).
BALANCED_DENSITY_POOL_DEFINITION: str = (
    "validated harmonic components (include_for_density == True) "
    "UNION confirmed inharmonic components "
    "UNION sub-bass components whose membership/interpretation status marks them "
    "as partials. EXCLUDE any row whose Acoustic_Interpretation_Status equals "
    "\"diagnostic_low_frequency_residual_not_partial\" and any unconfirmed row. "
    "(Note: this pool is stricter than the F-047 pool. Do not change F-047.)"
)

BALANCED_DENSITY_FORMULA_TEXT: str = (
    "P_i = A_i ** 2; p_i = P_i / sum(P)  # skip components with P_i == 0; "
    "D1 = exp( - sum(p_i * ln(p_i)) ). "
    "Empty pool or sum(P) == 0 -> NaN; single component -> D1 = 1.0."
)

_INCLUDE_TRUTHY = frozenset({"true", "1", "1.0", "yes"})


def balanced_component_density(amplitudes: Iterable[float]) -> float:
    """Hill number q=1 of energy shares. No I/O. float64 throughout.

    Empty pool or sum(P)==0 -> NaN. Single component -> 1.0.
    """
    amps = np.asarray(list(amplitudes), dtype=np.float64).reshape(-1)
    if amps.size == 0:
        return float(np.nan)
    finite = np.isfinite(amps)
    if not bool(np.any(finite)):
        return float(np.nan)
    power = np.square(amps[finite], dtype=np.float64)
    positive = power > np.float64(0.0)
    if not bool(np.any(positive)):
        return float(np.nan)
    power = power[positive]
    total = np.float64(np.sum(power, dtype=np.float64))
    if not np.isfinite(total) or total <= np.float64(0.0):
        return float(np.nan)
    if power.size == 1:
        return float(np.float64(1.0))
    shares = power / total
    entropy = np.float64(0.0) - np.float64(
        np.sum(shares * np.log(shares), dtype=np.float64)
    )
    return float(np.exp(entropy, dtype=np.float64))


def balanced_density_is_primary_valid(value: float) -> bool:
    """True only when D1 is a finite Hill number (never empty-pool NaN/0)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    return bool(np.isfinite(v) and v >= 1.0)


def _include_for_density_mask(df: pd.DataFrame) -> pd.Series:
    if "include_for_density" not in df.columns:
        return pd.Series(False, index=df.index)
    raw = df["include_for_density"]
    if pd.api.types.is_bool_dtype(raw):
        return raw.astype(bool)
    return raw.astype(str).str.strip().str.lower().isin(_INCLUDE_TRUTHY)


def _status_series(df: pd.DataFrame, *names: str) -> Optional[pd.Series]:
    for name in names:
        if name in df.columns:
            return df[name].astype(str).str.strip()
    return None


def _exclude_diagnostic_residual(df: pd.DataFrame) -> pd.DataFrame:
    status = _status_series(df, "Acoustic_Interpretation_Status")
    if status is None:
        return df
    return df.loc[status != DIAGNOSTIC_LOW_FREQUENCY_RESIDUAL_NOT_PARTIAL]


def _confirmed_inharmonic_mask(df: pd.DataFrame) -> pd.Series:
    status = _status_series(
        df,
        "inharmonic_status",
        "Acoustic_Interpretation_Status",
        "acoustic_status",
        "partial_confirmation_status",
    )
    if status is None:
        return pd.Series(False, index=df.index)
    return status.isin(CONFIRMED_INHARMONIC_STATUSES)


def _subbass_partial_mask(df: pd.DataFrame) -> pd.Series:
    if "subbass_membership" in df.columns:
        mem = df["subbass_membership"].astype(str).str.strip()
        return mem.eq(SUBBASS_MEMBERSHIP_MEMBER)
    status = _status_series(df, "Acoustic_Interpretation_Status", "acoustic_status")
    if status is None:
        return pd.Series(False, index=df.index)
    return status.isin(CONFIRMED_INHARMONIC_STATUSES)


def _amplitude_column(df: pd.DataFrame) -> Optional[str]:
    if "Amplitude_raw" in df.columns:
        return "Amplitude_raw"
    if "Amplitude" in df.columns:
        return "Amplitude"
    return None


def _finite_amplitudes(df: pd.DataFrame) -> Tuple[np.ndarray, int]:
    """Return (amplitudes including zeros, admitted count). Missing amp → not admitted."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return np.asarray([], dtype=np.float64), 0
    col = _amplitude_column(df)
    if col is None:
        return np.asarray([], dtype=np.float64), 0
    amp = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=np.float64)
    ok = np.isfinite(amp)
    return amp[ok].astype(np.float64, copy=False), int(ok.sum())


def filter_balanced_density_pool(
    *,
    harmonic_df: Optional[pd.DataFrame] = None,
    inharmonic_df: Optional[pd.DataFrame] = None,
    subbass_df: Optional[pd.DataFrame] = None,
) -> Tuple[np.ndarray, int]:
    """Stricter D1 pool. Does not implement or alter F-047."""
    parts: list[np.ndarray] = []
    count = 0

    if harmonic_df is not None and isinstance(harmonic_df, pd.DataFrame) and not harmonic_df.empty:
        h = harmonic_df.loc[_include_for_density_mask(harmonic_df)]
        h = _exclude_diagnostic_residual(h)
        amps, n = _finite_amplitudes(h)
        parts.append(amps)
        count += n

    if (
        inharmonic_df is not None
        and isinstance(inharmonic_df, pd.DataFrame)
        and not inharmonic_df.empty
    ):
        i = inharmonic_df.loc[_confirmed_inharmonic_mask(inharmonic_df)]
        i = _exclude_diagnostic_residual(i)
        amps, n = _finite_amplitudes(i)
        parts.append(amps)
        count += n

    if subbass_df is not None and isinstance(subbass_df, pd.DataFrame) and not subbass_df.empty:
        s = subbass_df.loc[_subbass_partial_mask(subbass_df)]
        s = _exclude_diagnostic_residual(s)
        amps, n = _finite_amplitudes(s)
        parts.append(amps)
        count += n

    if not parts:
        return np.asarray([], dtype=np.float64), 0
    return np.concatenate(parts).astype(np.float64, copy=False), int(count)


def balanced_density_from_component_tables(
    *,
    harmonic_df: Optional[pd.DataFrame] = None,
    inharmonic_df: Optional[pd.DataFrame] = None,
    subbass_df: Optional[pd.DataFrame] = None,
) -> Tuple[float, int]:
    amps, count = filter_balanced_density_pool(
        harmonic_df=harmonic_df,
        inharmonic_df=inharmonic_df,
        subbass_df=subbass_df,
    )
    return balanced_component_density(amps), int(count)


def place_columns_immediately_left_of(
    df: pd.DataFrame,
    *,
    columns: Sequence[str],
    anchor: str,
) -> pd.DataFrame:
    """Move ``columns`` (if present) to immediately left of ``anchor``.

    Existing columns other than ``columns`` keep their relative order.
    If ``anchor`` is absent, ``df`` is returned unchanged.
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return df
    if anchor not in df.columns:
        return df
    wanted = [c for c in columns if c in df.columns]
    if not wanted:
        return df
    remaining = [c for c in df.columns if c not in wanted]
    idx = remaining.index(anchor)
    ordered = remaining[:idx] + wanted + remaining[idx:]
    return df.loc[:, ordered]


def place_balanced_density_left_of_ewsd(df: pd.DataFrame) -> pd.DataFrame:
    """``note_balanced_component_density`` sits immediately left of EWSD."""
    return place_columns_immediately_left_of(
        df,
        columns=(
            BALANCED_DENSITY_POOL_COUNT_COLUMN,
            BALANCED_DENSITY_COLUMN,
        ),
        anchor=EWSD_ACOUSTIC_BALANCED_COLUMN,
    )
