#!/usr/bin/env python3
"""
ewsd_pure.py — numpy-only EWSD-R v18 formulas (F-048, F-049).

No pandas, Excel, or GUI dependencies. Used for validation, golden tests,
and as the numerical reference behind ``tools.ewsd_core``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Union

import numpy as np

EWSD_PURE_REVISION: str = "EWSD-R v18.1-pure"
EWSD_FORMULA_IDS: str = "F-048,F-049,F-050"
ACOUSTIC_BALANCE_ALPHA_DEFAULT: float = 0.50

ArrayLike = Union[np.ndarray, Sequence[float]]


@dataclass(frozen=True)
class CompartmentInputs:
    values: np.ndarray
    analysis_ratio: float
    frequencies_hz: Optional[np.ndarray] = None
    weight_function: str = "log"
    apply_anti_concentration: bool = True


@dataclass(frozen=True)
class CompartmentMetrics:
    count: int
    original_sum_metric: float
    analysis_ratio_weight: float
    ratio_weighted_metric: float
    weighted_mass: float
    effective_component_count: float
    concentration_penalty: float
    entropy_normalized: float
    ewsd_score: float


def canonical_weight_key(name: str) -> str:
    key = (name or "linear").strip().lower()
    aliases = {
        "auto_from_excel": "auto_from_excel",
        "sum": "linear",
        "d2": "linear",
        "d8": "d17",
        "logarithmic": "log",
        "exp": "exponential",
        "square": "squared",
    }
    return aliases.get(key, key)


def _finite_nonnegative_vector(values: ArrayLike) -> np.ndarray:
    v = np.asarray(values, dtype=float).reshape(-1)
    v = v[np.isfinite(v) & (v >= 0.0)]
    return v.astype(float, copy=False)


def spectral_neff_from_linear_amplitudes(values: ArrayLike) -> float:
    """N_eff = 1 / sum(p_i^2), p_i = A_i^2 / sum(A_j^2)."""
    v = _finite_nonnegative_vector(values)
    if v.size == 0:
        return 0.0
    pwr = np.square(v)
    total = float(np.sum(pwr))
    if total <= 1e-30:
        return 0.0
    p = pwr / total
    den = float(np.sum(np.square(p)))
    if den <= 1e-30:
        return 0.0
    return float(1.0 / den)


def original_elementwise_weight(values: ArrayLike, key: str) -> np.ndarray:
    """Per-component non-negative weights for participation/concentration diagnostics."""
    k = canonical_weight_key(key)
    v = _finite_nonnegative_vector(values)
    if v.size == 0:
        return np.zeros(0, dtype=float)

    if k == "linear":
        out = v
    elif k == "sqrt":
        out = np.sqrt(v)
    elif k == "squared":
        out = np.square(v)
    elif k == "cbrt":
        out = np.cbrt(v)
    elif k == "cubic":
        out = np.power(v, 3)
    elif k in {"log", "d3", "d10"}:
        out = np.log1p(v)
    elif k == "exponential":
        out = np.expm1(np.clip(v, 0.0, 50.0))
    elif k == "inverse log":
        out = 1.0 / (np.log1p(v) + 1e-10)
    elif k == "d17":
        out = np.square(v)
    elif k == "d24":
        out = np.log1p(v)
    else:
        raise ValueError(f"Unknown weight function: {key}")

    return np.where(np.isfinite(out) & (out > 0.0), out, 0.0).astype(float)


def d24_strength_mask(values: np.ndarray, freqs: Optional[np.ndarray]) -> np.ndarray:
    if values.size == 0:
        return np.zeros(0, dtype=bool)
    a_max = float(np.nanmax(values)) if np.isfinite(values).any() else 0.0
    if a_max <= 0.0:
        return np.zeros(values.shape[0], dtype=bool)
    m = values >= (0.01 * a_max)
    if freqs is not None and len(freqs) == len(m):
        m &= np.asarray(freqs, dtype=float) <= 12000.0
    return m


def original_sum_metric(
    values: ArrayLike,
    key: str,
    frequencies_hz: Optional[ArrayLike] = None,
    d24_global_amplitude_max: Optional[float] = None,
) -> float:
    """Scalar sum/metric family matching SoundSpectrAnalyse density weighting."""
    k = canonical_weight_key(key)
    v_all = np.asarray(values, dtype=float).reshape(-1)
    f_all: Optional[np.ndarray] = None
    if frequencies_hz is not None:
        f_tmp = np.asarray(frequencies_hz, dtype=float).reshape(-1)
        if f_tmp.size == v_all.size:
            f_all = f_tmp

    mask = np.isfinite(v_all) & (v_all >= 0.0)
    if f_all is not None:
        mask &= np.isfinite(f_all)
    v = v_all[mask]
    f = f_all[mask] if f_all is not None else None

    if v.size == 0:
        return 0.0

    if k == "linear":
        return float(np.sum(v))
    if k == "sqrt":
        return float(np.sum(np.sqrt(v)))
    if k == "squared":
        return float(np.sum(np.square(v)))
    if k == "cbrt":
        return float(np.sum(np.cbrt(v)))
    if k == "cubic":
        return float(np.sum(np.power(v, 3)))
    if k in {"log", "d3"}:
        return float(np.sum(np.log1p(v)))
    if k == "exponential":
        return float(np.sum(np.expm1(np.clip(v, 0.0, 50.0))))
    if k == "inverse log":
        return float(np.sum(1.0 / (np.log1p(v) + 1e-10)))
    if k == "d10":
        n_eff = float(spectral_neff_from_linear_amplitudes(v))
        n = float(v.size)
        return float(np.sum(np.log1p(v)) * (n_eff / n)) if n > 0 else 0.0
    if k == "d17":
        n_eff = float(spectral_neff_from_linear_amplitudes(v))
        return float(np.log1p(float(np.sum(np.square(v)))) * np.log1p(n_eff))
    if k == "d24":
        m = np.ones(v.shape[0], dtype=bool)
        if f is not None:
            m &= f <= 12000.0
        if d24_global_amplitude_max is not None and np.isfinite(float(d24_global_amplitude_max)):
            a_max = float(d24_global_amplitude_max)
        else:
            a_max = float(np.max(v)) if v.size else 0.0
        if a_max <= 0.0:
            return 0.0
        m &= v >= (0.01 * a_max)
        return float(np.sum(np.log1p(v[m]))) if np.any(m) else 0.0

    raise ValueError(f"Unknown weight function: {key}")


def participation_stats(strengths: np.ndarray) -> tuple[int, float, float, float, float]:
    """
    Return (n, total_mass, neff, penalty, entropy_norm) for non-negative strengths.

    penalty = N_eff / N with N_eff = 1 / sum(p_i^2), p_i = s_i / sum(s_j).
    """
    s = strengths[np.isfinite(strengths) & (strengths > 0.0)]
    n = int(s.size)
    total = float(np.sum(s)) if n else 0.0
    if n == 0 or total <= 0.0:
        return 0, 0.0, 0.0, 0.0, 0.0
    p = s / total
    neff = float(1.0 / np.sum(p ** 2)) if np.sum(p ** 2) > 0 else 0.0
    penalty = float(neff / n) if n > 0 else 0.0
    entropy_norm = float(-np.sum(p * np.log(p + 1e-300)) / np.log(n)) if n > 1 else 0.0
    return n, total, neff, penalty, entropy_norm


def compute_compartment_metrics(inputs: CompartmentInputs) -> CompartmentMetrics:
    """Compute one H/I/S compartment contribution to strict EWSD (F-048)."""
    ratio = float(inputs.analysis_ratio)
    if not np.isfinite(ratio) or ratio <= 0.0:
        return CompartmentMetrics(0, 0.0, ratio, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    values = _finite_nonnegative_vector(inputs.values)
    freqs: Optional[np.ndarray] = None
    if inputs.frequencies_hz is not None:
        f = np.asarray(inputs.frequencies_hz, dtype=float).reshape(-1)
        if f.size == values.size:
            freqs = f[np.isfinite(values) & (values >= 0.0)]

    if values.size == 0:
        return CompartmentMetrics(0, 0.0, ratio, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    original_metric = float(
        original_sum_metric(values, inputs.weight_function, freqs)
    )
    strengths = original_elementwise_weight(values, inputs.weight_function)
    if canonical_weight_key(inputs.weight_function) == "d24":
        strengths = np.where(d24_strength_mask(values, freqs), strengths, 0.0)

    strengths = strengths * ratio
    n, total, neff, penalty, entropy_norm = participation_stats(strengths)
    ratio_weighted_metric = float(original_metric * ratio)
    score = (
        float(ratio_weighted_metric * penalty)
        if inputs.apply_anti_concentration
        else float(ratio_weighted_metric)
    )

    return CompartmentMetrics(
        count=n,
        original_sum_metric=original_metric,
        analysis_ratio_weight=ratio,
        ratio_weighted_metric=ratio_weighted_metric,
        weighted_mass=total,
        effective_component_count=neff,
        concentration_penalty=penalty,
        entropy_normalized=entropy_norm,
        ewsd_score=score,
    )


def compute_strict_ewsd_total(compartments: Sequence[CompartmentMetrics]) -> float:
    return float(sum(c.ewsd_score for c in compartments))


def compute_acoustic_balanced_score(
    compartments: Sequence[CompartmentMetrics],
    *,
    alpha: float = ACOUSTIC_BALANCE_ALPHA_DEFAULT,
) -> float:
    """F-049: sum_k D_k * penalty_k^alpha where D_k = ratio_weighted_metric_k."""
    a = float(alpha)
    if not np.isfinite(a) or a < 0.0:
        a = ACOUSTIC_BALANCE_ALPHA_DEFAULT
    total = 0.0
    for comp in compartments:
        pen = float(comp.concentration_penalty)
        pen = min(max(pen, 0.0), 1.0)
        total += float(comp.ratio_weighted_metric) * (pen ** a)
    return float(total)


def compute_note_ewsd(
    compartments: Sequence[CompartmentInputs],
    *,
    acoustic_balance_alpha: float = ACOUSTIC_BALANCE_ALPHA_DEFAULT,
) -> dict[str, Any]:
    """Compute strict and acoustic-balanced EWSD for one note from compartment inputs."""
    metrics = [compute_compartment_metrics(c) for c in compartments]
    strict = compute_strict_ewsd_total(metrics)
    balanced = compute_acoustic_balanced_score(metrics, alpha=acoustic_balance_alpha)
    return {
        "ewsd_score_total": strict,
        "ewsd_score_acoustic_balanced": balanced,
        "compartments": metrics,
    }


def ewsd_from_compartment_summaries(
    summaries: Sequence[Mapping[str, float]],
    *,
    alpha: float = ACOUSTIC_BALANCE_ALPHA_DEFAULT,
    apply_anti_concentration: bool = True,
) -> tuple[float, float]:
    """
    Reconstruct EWSD totals from pre-aggregated compartment rows.

    Each summary mapping must provide:
    ``ratio_weighted_metric``, ``concentration_penalty``, and optionally
    ``ewsd_score`` (strict, used when anti-concentration is enabled).
    """
    strict = 0.0
    balanced = 0.0
    a = float(alpha)
    if not np.isfinite(a) or a < 0.0:
        a = ACOUSTIC_BALANCE_ALPHA_DEFAULT

    for row in summaries:
        mass = float(row.get("ratio_weighted_metric", 0.0) or 0.0)
        pen = float(row.get("concentration_penalty", 0.0) or 0.0)
        pen = min(max(pen, 0.0), 1.0)
        if apply_anti_concentration and "ewsd_score" in row:
            strict += float(row["ewsd_score"])
        elif apply_anti_concentration:
            strict += mass * pen
        else:
            strict += mass
        balanced += mass * (pen ** a)
    return float(strict), float(balanced)


def ratios_valid(h: float, i: float, s: float, *, tol: float = 0.001) -> bool:
    vals = (float(h), float(i), float(s))
    if not all(np.isfinite(v) and v >= 0.0 for v in vals):
        return False
    total = sum(vals)
    return total > 0.0 and abs(total - 1.0) <= tol
