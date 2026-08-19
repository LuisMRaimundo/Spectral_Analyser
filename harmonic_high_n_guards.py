"""Independent high-n harmonic guards (Phase C).

The spacing cap cannot stop floor harvest at high order: a ±β·f0 window
is tens of bins wide and almost always contains a noise peak. Persistence
(Phase B) and a minimum CFAR margin are independent of the body stop.
The body stop remains the load-bearing high-n cut; these guards keep
H1–H8 when that stop is switched off, and they flag a note when the
accepted count exceeds the body plus the false-alarm budget.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

import numpy as np

from constants import (
    CFAR_PFA,
    HARMONIC_BODY_STOP_CONSECUTIVE,
    HARMONIC_BODY_STOP_MARGIN_DB,
    HARMONIC_CONTINUITY_PERSISTENCE_OVERRIDE,
    HARMONIC_CONTINUITY_REJECT_STREAK,
    HARMONIC_CONTINUITY_RULE_ENABLED,
    HARMONIC_MIN_CFAR_MARGIN_DB,
)
from harmonic_peak_validation import apply_harmonic_body_stop

CFAR_MARGINAL = "cfar_marginal"
CONTINUITY_BREAK = "continuity_break"
_PROTECTED_STATUSES = frozenset(
    {
        "rejected_by_tolerance",
        "peak_already_assigned",
        "low_temporal_persistence",
        CFAR_MARGINAL,
        CONTINUITY_BREAK,
    }
)


def _order(row: Mapping[str, Any]) -> int:
    for key in ("Harmonic Number", "harmonic_number", "n"):
        if key in row:
            try:
                return int(row[key])
            except (TypeError, ValueError):
                continue
    return 0


def _protected(row: Mapping[str, Any]) -> bool:
    status = str(row.get("candidate_status") or "")
    reason = str(row.get("exclusion_reason") or "")
    if status in _PROTECTED_STATUSES:
        return True
    return reason.startswith("rejected_by_tolerance") or reason.startswith(
        "low_temporal_persistence"
    )


def expected_false_harmonic_slots(
    slot_count: int,
    pfa: float = CFAR_PFA,
) -> float:
    """``harmonic_slot_expected_count × P_fa``."""
    try:
        n = int(slot_count)
    except (TypeError, ValueError):
        return float("nan")
    try:
        p = float(pfa)
    except (TypeError, ValueError):
        return float("nan")
    if n < 0 or not np.isfinite(p) or p < 0.0:
        return float("nan")
    return float(n) * float(p)


def apply_cfar_margin_gate(
    rows: Sequence[Mapping[str, Any]],
    *,
    min_margin_db: float = HARMONIC_MIN_CFAR_MARGIN_DB,
) -> list[dict[str, Any]]:
    """Exclude included rows whose CFAR margin is in ``[0, min)`` dB."""
    out: list[dict[str, Any]] = []
    try:
        min_m = float(min_margin_db)
    except (TypeError, ValueError):
        min_m = float(HARMONIC_MIN_CFAR_MARGIN_DB)
    if not np.isfinite(min_m):
        min_m = float(HARMONIC_MIN_CFAR_MARGIN_DB)
    for raw in rows:
        row = dict(raw)
        if _protected(row) or not bool(row.get("include_for_density", False)):
            out.append(row)
            continue
        try:
            margin = float(row.get("cfar_margin_db", float("nan")))
        except (TypeError, ValueError):
            margin = float("nan")
        if np.isfinite(margin) and 0.0 <= margin < min_m:
            row["include_for_density"] = False
            row["candidate_status"] = CFAR_MARGINAL
            row["exclusion_reason"] = (
                f"{CFAR_MARGINAL} (margin={margin:.2f} dB < {min_m:.1f} dB)"
            )
        out.append(row)
    return out


def apply_continuity_rule(
    rows: Sequence[Mapping[str, Any]],
    *,
    enabled: bool = HARMONIC_CONTINUITY_RULE_ENABLED,
    streak_k: int = HARMONIC_CONTINUITY_REJECT_STREAK,
    persistence_override: float = HARMONIC_CONTINUITY_PERSISTENCE_OVERRIDE,
) -> list[dict[str, Any]]:
    """After ``k`` consecutive rejected slots, drop later accepts unless p ≥ 0.9.

    Off by default. Does not overwrite protected exclusion reasons.
    """
    out = [dict(r) for r in rows]
    if not bool(enabled):
        return out
    try:
        k = int(streak_k)
    except (TypeError, ValueError):
        k = int(HARMONIC_CONTINUITY_REJECT_STREAK)
    k = max(1, k)
    try:
        p_min = float(persistence_override)
    except (TypeError, ValueError):
        p_min = float(HARMONIC_CONTINUITY_PERSISTENCE_OVERRIDE)
    by_n = sorted(range(len(out)), key=lambda i: _order(out[i]))
    streak = 0
    freeze = False
    for i in by_n:
        row = out[i]
        if _order(row) < 1:
            continue
        included = bool(row.get("include_for_density", False))
        if freeze and included and not _protected(row):
            try:
                persist = float(row.get("persistence_fraction", float("nan")))
            except (TypeError, ValueError):
                persist = float("nan")
            if not (np.isfinite(persist) and persist >= p_min):
                row["include_for_density"] = False
                row["candidate_status"] = CONTINUITY_BREAK
                row["exclusion_reason"] = (
                    f"{CONTINUITY_BREAK} (streak>={k}, p={persist if np.isfinite(persist) else float('nan')})"
                )
                included = False
        if included:
            streak = 0
        else:
            streak += 1
            if streak >= k:
                freeze = True
    return out


def estimate_harmonic_body_stop_order(
    rows: Sequence[Mapping[str, Any]],
    f0_hz: float,
    **kwargs: Any,
) -> Optional[int]:
    """Diagnostic stop order without mutating ``rows`` (stop forced on)."""
    copies = [dict(r) for r in rows]
    kwargs = dict(kwargs)
    kwargs["enabled"] = True
    kwargs.setdefault("margin_db", HARMONIC_BODY_STOP_MARGIN_DB)
    kwargs.setdefault("consecutive", HARMONIC_BODY_STOP_CONSECUTIVE)
    _, meta = apply_harmonic_body_stop(copies, f0_hz=f0_hz, **kwargs)
    if not meta.get("harmonic_body_stop_triggered"):
        return None
    try:
        n = int(meta.get("harmonic_body_stop_order"))
    except (TypeError, ValueError):
        return None
    return n if n >= 1 else None


def summarize_high_n_guards(
    rows: Sequence[Mapping[str, Any]],
    *,
    slot_count: int,
    body_stop_order: Optional[float],
    pfa: float = CFAR_PFA,
) -> dict[str, Any]:
    """Per-note false-alarm budget and acceptance-suspect flag."""
    accepted = [r for r in rows if bool(r.get("include_for_density", False))]
    accepted_n = len(accepted)
    expected_fa = expected_false_harmonic_slots(slot_count, pfa)
    try:
        stop_n = int(body_stop_order) if body_stop_order is not None else None
        if stop_n is not None and stop_n < 1:
            stop_n = None
    except (TypeError, ValueError):
        stop_n = None
    if stop_n is None:
        above = 0
        suspect = False
    else:
        above = sum(1 for r in accepted if _order(r) > stop_n)
        suspect = bool(
            np.isfinite(expected_fa) and accepted_n > (float(stop_n) + float(expected_fa))
        )
    marginal = sum(
        1 for r in rows if str(r.get("candidate_status") or "") == CFAR_MARGINAL
    )
    return {
        "expected_false_harmonic_slots": float(expected_fa),
        "accepted_slots_above_body_stop": int(above),
        "harmonic_acceptance_suspect": bool(suspect),
        "cfar_marginal_count": int(marginal),
        "harmonic_validated_count": int(accepted_n),
    }
