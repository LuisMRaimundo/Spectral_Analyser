"""Validated-partial predicate and gated consumer helpers (Fix 2 / Phase A).

Harmonic rows enter density / dissonance / amplitude pies only when
``include_for_density`` is True. Inharmonic rows enter only when
``inharmonic_status`` (or the acoustic-status alias) is
``confirmed_inharmonic_partial``. Ungated values stay available under
``*_ungated``.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

CONFIRMED_INHARMONIC_STATUSES: frozenset = frozenset(
    {
        "confirmed_inharmonic_partial",
        "confirmed_partial",
    }
)

VALIDATED_PARTIAL_INPUT_DOMAIN: str = "validated_partials_only"
SUBBASS_MEMBERSHIP_MEMBER: str = "subbass_member"
SUBBASS_MEMBERSHIP_DIAGNOSTIC: str = "lf_diagnostic_not_member"
REJECTED_FLOOR_STATUS: str = "rejected_floor"


def is_validated_partial(row: Mapping[str, Any], *, kind: str = "harmonic") -> bool:
    """Return True when ``row`` is a confirmed partial for the given family."""
    if row is None:
        return False
    family = str(kind or "harmonic").strip().lower()
    if family == "harmonic":
        return bool(row.get("include_for_density", False))
    status = str(
        row.get("inharmonic_status")
        or row.get("Acoustic_Interpretation_Status")
        or row.get("acoustic_status")
        or row.get("partial_confirmation_status")
        or ""
    ).strip()
    return status in CONFIRMED_INHARMONIC_STATUSES


def _row_linear_amplitude(row: Mapping[str, Any]) -> float:
    for key in ("Amplitude_raw", "Amplitude"):
        if key not in row:
            continue
        try:
            amp = float(row[key])
        except (TypeError, ValueError):
            continue
        if np.isfinite(amp) and amp > 0.0:
            return amp
    return 0.0


def gated_linear_amplitude_sums(
    *,
    harmonic_rows: Sequence[Mapping[str, Any]],
    inharmonic_rows: Sequence[Mapping[str, Any]] = (),
    subbass_rows: Sequence[Mapping[str, Any]] = (),
) -> tuple[float, float, float]:
    """Gated (H, I, S) linear amplitude sums. Floor / unconfirmed rows are 0."""
    h = float(
        sum(
            _row_linear_amplitude(r)
            for r in harmonic_rows
            if is_validated_partial(r, kind="harmonic")
        )
    )
    i = float(
        sum(
            _row_linear_amplitude(r)
            for r in inharmonic_rows
            if is_validated_partial(r, kind="inharmonic")
        )
    )
    s = float(
        sum(
            _row_linear_amplitude(r)
            for r in subbass_rows
            if is_validated_partial(r, kind="subbass")
        )
    )
    return h, i, s


def participation_ratio_from_amplitudes(amplitudes: Iterable[float]) -> float:
    """Hill q=2 / inverse Herfindahl on power: (ΣP)² / ΣP², P = A²."""
    amps = np.asarray(
        [float(a) for a in amplitudes if np.isfinite(float(a)) and float(a) > 0.0],
        dtype=float,
    )
    if amps.size == 0:
        return 0.0
    powers = np.square(amps)
    total = float(np.sum(powers))
    ss = float(np.sum(powers * powers))
    if ss <= 0.0:
        return 0.0
    return float((total * total) / ss)


def gated_effective_partial_density(
    harmonic_rows: Sequence[Mapping[str, Any]],
) -> float:
    """Participation ratio of validated harmonic partials only (F-012 domain)."""
    amps = [
        _row_linear_amplitude(r)
        for r in harmonic_rows
        if is_validated_partial(r, kind="harmonic")
    ]
    return participation_ratio_from_amplitudes(amps)


def gated_dissonance_partials(
    harmonic_rows: Sequence[Mapping[str, Any]],
    inharmonic_rows: Sequence[Mapping[str, Any]] = (),
) -> list[tuple[float, float]]:
    """(frequency_hz, amplitude) pairs for the dissonance model."""
    out: list[tuple[float, float]] = []
    families = (
        (harmonic_rows, "harmonic"),
        (inharmonic_rows, "inharmonic"),
    )
    for rows, kind in families:
        for row in rows:
            if not is_validated_partial(row, kind=kind):
                continue
            try:
                freq = float(row.get("Frequency (Hz)", row.get("extracted_frequency_hz")))
            except (TypeError, ValueError):
                continue
            amp = _row_linear_amplitude(row)
            if np.isfinite(freq) and freq > 0.0 and amp > 0.0:
                out.append((freq, amp))
    return out


def is_subbass_compartment_member(
    freq_hz: float,
    *,
    f0_hz: float,
    low_frequency_class: Optional[str] = None,
) -> bool:
    """True only for S-compartment members at or below F-020."""
    try:
        freq = float(freq_hz)
        f0 = float(f0_hz)
    except (TypeError, ValueError):
        return False
    if not np.isfinite(freq) or freq <= 0.0 or not np.isfinite(f0) or f0 <= 0.0:
        return False
    f020 = min(0.5 * f0, 80.0)
    if freq > f020:
        return False
    if str(low_frequency_class or "") == "physical_low_frequency_residual":
        return False
    return True


def gated_subbass_energy_sum(
    rows: Sequence[Mapping[str, Any]],
    *,
    f0_hz: float,
) -> float:
    """ΣA² of S-compartment members only. Residual rows above F-020 are 0."""
    total = 0.0
    for row in rows:
        try:
            freq = float(row.get("Frequency (Hz)", float("nan")))
        except (TypeError, ValueError):
            continue
        cls = str(row.get("Low_Frequency_Class") or row.get("low_frequency_class") or "")
        if not is_subbass_compartment_member(
            freq, f0_hz=f0_hz, low_frequency_class=cls
        ):
            continue
        amp = _row_linear_amplitude(row)
        total += float(amp * amp)
    return float(total)


def dataframe_rows(df: Optional[pd.DataFrame]) -> list[dict]:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return []
    return df.to_dict(orient="records")


def subbass_membership_label(
    freq_hz: float,
    *,
    f0_hz: float,
    low_frequency_class: Optional[str] = None,
) -> str:
    """``subbass_member`` below F-020; otherwise ``lf_diagnostic_not_member``."""
    if is_subbass_compartment_member(
        freq_hz, f0_hz=f0_hz, low_frequency_class=low_frequency_class
    ):
        return SUBBASS_MEMBERSHIP_MEMBER
    return SUBBASS_MEMBERSHIP_DIAGNOSTIC


def low_frequency_diagnostic_upper_hz(
    f0_hz: float,
    f020_hz: float,
    *,
    cap_hz: float = 200.0,
) -> float:
    """Export ceiling for F-020 diagnostic rows (not the S-compartment bound)."""
    try:
        f020 = float(f020_hz)
    except (TypeError, ValueError):
        f020 = 80.0
    if not np.isfinite(f020) or f020 <= 0.0:
        f020 = 80.0
    try:
        cap = float(cap_hz)
    except (TypeError, ValueError):
        cap = 200.0
    if not np.isfinite(cap) or cap <= 0.0:
        cap = 200.0
    try:
        f0 = float(f0_hz)
    except (TypeError, ValueError):
        f0 = float("nan")
    if np.isfinite(f0) and f0 > 0.0:
        return float(max(f020, min(f0, cap)))
    return float(max(f020, cap))


def annotate_subbass_membership(
    df: Optional[pd.DataFrame],
    *,
    f0_hz: float,
) -> pd.DataFrame:
    """Add ``subbass_membership`` and mark diagnostic rows on the Sub-bass sheet."""
    out = df.copy() if df is not None and isinstance(df, pd.DataFrame) else pd.DataFrame()
    if out.empty:
        out["subbass_membership"] = pd.Series(dtype=str)
        return out
    freq_col = "Frequency (Hz)" if "Frequency (Hz)" in out.columns else None
    freqs = (
        pd.to_numeric(out[freq_col], errors="coerce")
        if freq_col is not None
        else pd.Series(np.nan, index=out.index)
    )
    if "Low_Frequency_Class" in out.columns:
        classes = out["Low_Frequency_Class"].astype(str)
    else:
        classes = pd.Series([""] * len(out), index=out.index)
    labels = [
        subbass_membership_label(
            float(f) if np.isfinite(float(f)) else float("nan"),
            f0_hz=f0_hz,
            low_frequency_class=str(c or ""),
        )
        for f, c in zip(freqs.to_numpy(dtype=float), classes.to_numpy())
    ]
    out["subbass_membership"] = labels
    member_status = "diagnostic_low_frequency_residual_not_partial"
    if "Acoustic_Interpretation_Status" in out.columns:
        status = [str(v) for v in out["Acoustic_Interpretation_Status"].to_numpy()]
        for i, lab in enumerate(labels):
            if lab == SUBBASS_MEMBERSHIP_DIAGNOSTIC:
                status[i] = SUBBASS_MEMBERSHIP_DIAGNOSTIC
        out["Acoustic_Interpretation_Status"] = status
    else:
        out["Acoustic_Interpretation_Status"] = [
            SUBBASS_MEMBERSHIP_DIAGNOSTIC if lab == SUBBASS_MEMBERSHIP_DIAGNOSTIC else member_status
            for lab in labels
        ]
    return out


def resolve_subbass_member_mask(
    df: pd.DataFrame,
    *,
    f0_hz: Optional[float] = None,
) -> tuple[np.ndarray, str, int]:
    """Row mask for F-020 S members. Legacy sheets without labels stay unfiltered."""
    n = 0 if df is None or not isinstance(df, pd.DataFrame) else int(len(df))
    if n == 0:
        return np.zeros(0, dtype=bool), "empty", 0
    cols = {str(c).strip().lower(): c for c in df.columns}
    mem_key = cols.get("subbass_membership")
    if mem_key is not None:
        mem = df[mem_key].astype(str).str.strip()
        mask = mem.eq(SUBBASS_MEMBERSHIP_MEMBER).to_numpy()
        return mask, "subbass_members_only", int((~mask).sum())

    freq_key = cols.get("frequency (hz)")
    class_key = cols.get("low_frequency_class")
    freqs = (
        pd.to_numeric(df[freq_key], errors="coerce").to_numpy(dtype=float)
        if freq_key is not None
        else np.full(n, np.nan)
    )
    classes = (
        df[class_key].astype(str).to_numpy()
        if class_key is not None
        else np.array([""] * n, dtype=object)
    )
    f0: Optional[float] = None
    if f0_hz is not None:
        try:
            f0_try = float(f0_hz)
        except (TypeError, ValueError):
            f0_try = float("nan")
        if np.isfinite(f0_try) and f0_try > 0.0:
            f0 = f0_try
    if f0 is not None:
        mask = np.array(
            [
                is_subbass_compartment_member(
                    float(f), f0_hz=f0, low_frequency_class=str(c or "")
                )
                for f, c in zip(freqs, classes)
            ],
            dtype=bool,
        )
        return mask, "subbass_members_only", int((~mask).sum())
    if class_key is not None:
        mask = np.array(
            [str(c) != "physical_low_frequency_residual" for c in classes],
            dtype=bool,
        )
        return mask, "exclude_physical_low_frequency_residual", int((~mask).sum())
    return np.ones(n, dtype=bool), "all_rows_no_membership_column", 0


def count_subbass_members(df: Optional[pd.DataFrame], *, f0_hz: Optional[float] = None) -> int:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return 0
    mask, _, _ = resolve_subbass_member_mask(df, f0_hz=f0_hz)
    return int(mask.sum())


def count_floor_rows_rejected(inharmonic_df: Optional[pd.DataFrame]) -> int:
    """Count residual candidates with ``inharmonic_status = rejected_floor``."""
    if inharmonic_df is None or not isinstance(inharmonic_df, pd.DataFrame) or inharmonic_df.empty:
        return 0
    cols = {str(c).strip().lower(): c for c in inharmonic_df.columns}
    status_key = cols.get("inharmonic_status")
    if status_key is None:
        return 0
    status = inharmonic_df[status_key].astype(str).str.strip()
    return int(status.eq(REJECTED_FLOOR_STATUS).sum())


def attach_sample_identity_columns(
    df: Optional[pd.DataFrame],
    *,
    sample_note_tag: str,
    sample_id: str,
) -> pd.DataFrame:
    """Take identity on per-row sheets. Drops overloaded ``Note`` if present."""
    out = df.copy() if df is not None and isinstance(df, pd.DataFrame) else pd.DataFrame()
    out["sample_note_tag"] = str(sample_note_tag or "")
    out["sample_id"] = str(sample_id or "")
    if "Note" in out.columns:
        out = out.drop(columns=["Note"])
    return out
