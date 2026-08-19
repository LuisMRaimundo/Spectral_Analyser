"""Validated-partial predicate and gated consumer helpers (Fix 2).

Harmonic rows enter density / dissonance / amplitude pies only when
``include_for_density`` is True. Inharmonic rows currently carry
``candidate_not_confirmed_partial`` and are excluded until a documented
confirmation class exists. Ungated values stay available under ``*_ungated``.
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


def is_validated_partial(row: Mapping[str, Any], *, kind: str = "harmonic") -> bool:
    """Return True when ``row`` is a confirmed partial for the given family."""
    if row is None:
        return False
    family = str(kind or "harmonic").strip().lower()
    if family == "harmonic":
        return bool(row.get("include_for_density", False))
    status = str(
        row.get("Acoustic_Interpretation_Status")
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
) -> list[tuple[float, float]]:
    """(frequency_hz, amplitude) pairs for the dissonance model."""
    out: list[tuple[float, float]] = []
    for row in harmonic_rows:
        if not is_validated_partial(row, kind="harmonic"):
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
