"""F-061 spectral mass — derived Stage 3 column (no signal processing).

Construct: how much is sounding, as (compromise component count) ×
(bounded per-component size). Design intent: presence constitutes
richness; loudness modulates it but must not overturn it.

    count          = (ACD_D0 * ACD_score) ** MASS_COUNT_BLEND
    size_factor    = ACD_magnitude_per_component ** MASS_LEVEL_EXPONENT
    spectral_mass  = count * size_factor

Inputs are existing ACD exports. NaN in any input, or ACD_status != "ok",
yields NaN (never 0.0).

Planned exact form (F-061.1), not implemented: in-code Hill numbers of
order 1 and 2 with an audibility floor, once perceptual validation
exists. This module stays the Excel-selected candidate-D blend until
that work is done.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

MASS_COUNT_BLEND: float = 0.5
MASS_LEVEL_EXPONENT: float = 0.15

SPECTRAL_MASS_FORMULA_ID: str = "F-061"
SPECTRAL_MASS_FORMULA_VERSION: str = "1.0"

SPECTRAL_MASS_COLUMN: str = "spectral_mass"
SPECTRAL_MASS_COUNT_COLUMN: str = "spectral_mass_count"
SPECTRAL_MASS_COUNT_BLEND_COLUMN: str = "spectral_mass_count_blend"
SPECTRAL_MASS_LEVEL_EXPONENT_COLUMN: str = "spectral_mass_level_exponent"
SPECTRAL_MASS_FORMULA_ID_COLUMN: str = "spectral_mass_formula_id"
SPECTRAL_MASS_FORMULA_VERSION_COLUMN: str = "spectral_mass_formula_version"

EWSD_ACOUSTIC_BALANCED_COLUMN: str = "EWSD_score_acoustic_balanced"

# Blue data bars on spectral_mass (#4472C4). Distinct from the red
# EWSD_score_acoustic_balanced bars (FFC00000).
SPECTRAL_MASS_DATA_BAR_COLOR: str = "FF4472C4"

_PLACEMENT_COLUMNS: Sequence[str] = (
    SPECTRAL_MASS_COLUMN,
    SPECTRAL_MASS_COUNT_COLUMN,
    SPECTRAL_MASS_COUNT_BLEND_COLUMN,
    SPECTRAL_MASS_LEVEL_EXPONENT_COLUMN,
    SPECTRAL_MASS_FORMULA_ID_COLUMN,
    SPECTRAL_MASS_FORMULA_VERSION_COLUMN,
)


def compute_spectral_mass(
    d0: float,
    d1: float,
    lam: float,
    *,
    status: str = "ok",
) -> tuple[float, float]:
    """Return ``(spectral_mass, spectral_mass_count)`` or ``(NaN, NaN)``."""
    if str(status).strip() != "ok":
        return float("nan"), float("nan")
    try:
        d0_f = float(d0)
        d1_f = float(d1)
        lam_f = float(lam)
    except (TypeError, ValueError):
        return float("nan"), float("nan")
    if not np.isfinite(d0_f) or not np.isfinite(d1_f) or not np.isfinite(lam_f):
        return float("nan"), float("nan")
    if d0_f <= 0.0 or d1_f <= 0.0 or lam_f <= 0.0:
        return float("nan"), float("nan")
    count = float((d0_f * d1_f) ** MASS_COUNT_BLEND)
    mass = float(count * (lam_f ** MASS_LEVEL_EXPONENT))
    return mass, count


def place_spectral_mass_right_of_ewsd(df: pd.DataFrame) -> pd.DataFrame:
    """``spectral_mass`` then ``spectral_mass_count`` sit immediately right of EWSD."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return df
    if EWSD_ACOUSTIC_BALANCED_COLUMN not in df.columns:
        return df
    wanted = [c for c in _PLACEMENT_COLUMNS if c in df.columns]
    if not wanted:
        return df
    remaining = [c for c in df.columns if c not in wanted]
    idx = remaining.index(EWSD_ACOUSTIC_BALANCED_COLUMN)
    ordered = remaining[: idx + 1] + wanted + remaining[idx + 1 :]
    return df.loc[:, ordered]


def add_spectral_mass_column(df: pd.DataFrame) -> pd.DataFrame:
    """F-061: spectral_mass = (D0*D1)**MASS_COUNT_BLEND * lam**MASS_LEVEL_EXPONENT.

    Also exports spectral_mass_count = sqrt(D0*D1) and echoes the two constants
    as spectral_mass_count_blend / spectral_mass_level_exponent per row.
    """
    out = df.copy()
    d0 = (
        pd.to_numeric(out["ACD_D0"], errors="coerce")
        if "ACD_D0" in out.columns
        else pd.Series(np.nan, index=out.index, dtype=float)
    )
    d1 = (
        pd.to_numeric(out["ACD_score"], errors="coerce")
        if "ACD_score" in out.columns
        else pd.Series(np.nan, index=out.index, dtype=float)
    )
    lam = (
        pd.to_numeric(out["ACD_magnitude_per_component"], errors="coerce")
        if "ACD_magnitude_per_component" in out.columns
        else pd.Series(np.nan, index=out.index, dtype=float)
    )
    if "ACD_status" in out.columns:
        status_ok = out["ACD_status"].map(
            lambda v: str(v).strip() == "ok" if pd.notna(v) else False
        )
    else:
        status_ok = pd.Series(False, index=out.index)

    valid = (
        status_ok.astype(bool)
        & d0.notna()
        & d1.notna()
        & lam.notna()
        & np.isfinite(d0.to_numpy(dtype=float, copy=False))
        & np.isfinite(d1.to_numpy(dtype=float, copy=False))
        & np.isfinite(lam.to_numpy(dtype=float, copy=False))
        & (d0 > 0.0)
        & (d1 > 0.0)
        & (lam > 0.0)
    )

    count = pd.Series(np.nan, index=out.index, dtype=float)
    mass = pd.Series(np.nan, index=out.index, dtype=float)
    if bool(valid.any()):
        count.loc[valid] = (d0.loc[valid] * d1.loc[valid]) ** MASS_COUNT_BLEND
        mass.loc[valid] = count.loc[valid] * (lam.loc[valid] ** MASS_LEVEL_EXPONENT)

    out[SPECTRAL_MASS_COLUMN] = mass
    out[SPECTRAL_MASS_COUNT_COLUMN] = count
    out[SPECTRAL_MASS_COUNT_BLEND_COLUMN] = MASS_COUNT_BLEND
    out[SPECTRAL_MASS_LEVEL_EXPONENT_COLUMN] = MASS_LEVEL_EXPONENT
    out[SPECTRAL_MASS_FORMULA_ID_COLUMN] = SPECTRAL_MASS_FORMULA_ID
    out[SPECTRAL_MASS_FORMULA_VERSION_COLUMN] = SPECTRAL_MASS_FORMULA_VERSION
    return place_spectral_mass_right_of_ewsd(out)


def spectral_mass_data_bar_rule():
    """Same DataBarRule shape as the red EWSD bars; blue fill."""
    from openpyxl.formatting.rule import DataBarRule

    return DataBarRule(
        start_type="min",
        end_type="max",
        color=SPECTRAL_MASS_DATA_BAR_COLOR,
        showValue=True,
        minLength=0,
        maxLength=100,
    )


def apply_spectral_mass_data_bar(ws, headers=None) -> None:
    """Attach the blue data-bar rule to ``spectral_mass`` on ``ws``."""
    from openpyxl.utils import get_column_letter

    if headers is None:
        headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    last = ws.max_row
    if last < 2:
        return
    try:
        ci = list(headers).index(SPECTRAL_MASS_COLUMN) + 1
    except ValueError:
        return
    letter = get_column_letter(ci)
    ws.conditional_formatting.add(f"{letter}2:{letter}{last}", spectral_mass_data_bar_rule())
