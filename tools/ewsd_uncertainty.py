#!/usr/bin/env python3
"""
Bootstrap uncertainty quantification for EWSD (F-048 / F-049).

Mirrors ``density_uncertainty.bootstrap_note_density_final``: resamples salient
partials within each H/I/S compartment and optionally recomputes component energy
ratios inside each bootstrap draw.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

import numpy as np

from scipy.stats import norm

from tools.ewsd_pure import (
    ACOUSTIC_BALANCE_ALPHA_DEFAULT,
    CompartmentInputs,
    CompartmentMetrics,
    compute_acoustic_balanced_score,
    compute_compartment_metrics,
    compute_strict_ewsd_total,
)

__all__ = (
    "CompartmentBootstrapData",
    "bootstrap_ewsd_from_compartments",
    "compartment_bootstrap_data_from_arrays",
)


@dataclass(frozen=True)
class CompartmentBootstrapData:
    """Salient partial amplitudes for one H/I/S compartment."""

    amplitudes: np.ndarray
    analysis_ratio: float
    frequencies_hz: Optional[np.ndarray] = None
    weight_function: str = "log"
    apply_anti_concentration: bool = True


def compartment_bootstrap_data_from_arrays(
    amplitudes: Sequence[float],
    analysis_ratio: float,
    *,
    frequencies_hz: Optional[Sequence[float]] = None,
    weight_function: str = "log",
    apply_anti_concentration: bool = True,
) -> CompartmentBootstrapData:
    amps = np.asarray(amplitudes, dtype=float).ravel()
    amps = amps[np.isfinite(amps) & (amps > 0.0)]
    freqs: Optional[np.ndarray] = None
    if frequencies_hz is not None:
        f = np.asarray(frequencies_hz, dtype=float).ravel()
        if f.size == amps.size:
            freqs = f
    return CompartmentBootstrapData(
        amplitudes=amps,
        analysis_ratio=float(analysis_ratio),
        frequencies_hz=freqs,
        weight_function=weight_function,
        apply_anti_concentration=apply_anti_concentration,
    )


def _compartment_energy(amplitudes: np.ndarray) -> float:
    if amplitudes.size == 0:
        return 0.0
    return float(np.sum(np.square(amplitudes)))


def _metrics_for_resample(
    compartments: Sequence[CompartmentBootstrapData],
    resampled: Sequence[tuple[np.ndarray, Optional[np.ndarray], float]],
    *,
    acoustic_balance_alpha: float,
) -> tuple[float, float]:
    metrics: list[CompartmentMetrics] = []
    for comp, (amps, freqs, ratio) in zip(compartments, resampled, strict=True):
        metrics.append(
            compute_compartment_metrics(
                CompartmentInputs(
                    values=amps,
                    analysis_ratio=ratio,
                    frequencies_hz=freqs,
                    weight_function=comp.weight_function,
                    apply_anti_concentration=comp.apply_anti_concentration,
                )
            )
        )
    strict = compute_strict_ewsd_total(metrics)
    balanced = compute_acoustic_balanced_score(metrics, alpha=acoustic_balance_alpha)
    return strict, balanced


def _energy_ratios_from_compartments(
    compartments: Sequence[CompartmentBootstrapData],
) -> list[float]:
    energies = [_compartment_energy(comp.amplitudes) for comp in compartments]
    total = float(sum(energies))
    if total <= 1e-30:
        return [0.0 for _ in compartments]
    return [e / total for e in energies]


def _jackknife_estimates(
    compartments: Sequence[CompartmentBootstrapData],
    *,
    acoustic_balance_alpha: float,
    propagate_ratio_uncertainty: bool,
) -> tuple[np.ndarray, np.ndarray]:
    """Leave-one-partial-out estimates for BCa acceleration."""
    strict_vals: list[float] = []
    bal_vals: list[float] = []
    for skip_k, comp in enumerate(compartments):
        n = int(comp.amplitudes.size)
        for i in range(n):
            draw: list[tuple[np.ndarray, Optional[np.ndarray], float]] = []
            energies: list[float] = []
            for k, other in enumerate(compartments):
                amps = other.amplitudes
                freqs = other.frequencies_hz
                if k == skip_k:
                    keep = np.ones(amps.size, dtype=bool)
                    keep[i] = False
                    amps = amps[keep]
                    if freqs is not None and freqs.size == other.amplitudes.size:
                        freqs = freqs[keep]
                    else:
                        freqs = None
                draw.append((amps, freqs, float(other.analysis_ratio)))
                energies.append(_compartment_energy(amps))
            if propagate_ratio_uncertainty:
                e_total = float(sum(energies))
                if e_total > 1e-30:
                    draw = [
                        (amps, freqs, e / e_total)
                        for (amps, freqs, _), e in zip(draw, energies, strict=True)
                    ]
                else:
                    draw = [(amps, freqs, 0.0) for amps, freqs, _ in draw]
            s, bal = _metrics_for_resample(
                compartments, draw, acoustic_balance_alpha=acoustic_balance_alpha
            )
            strict_vals.append(s)
            bal_vals.append(bal)
    if not strict_vals:
        return np.zeros(0, dtype=float), np.zeros(0, dtype=float)
    return np.asarray(strict_vals, dtype=float), np.asarray(bal_vals, dtype=float)


def _bca_limits(point: float, samples: np.ndarray, jack: np.ndarray, ci: float) -> tuple[float, float]:
    """Efron BCa interval from bootstrap samples and jackknife replicates."""
    nan = float("nan")
    if samples.size < 2 or jack.size < 2 or not np.isfinite(point):
        return nan, nan
    prop = float(np.mean(samples < point))
    prop = min(max(prop, 1.0 / (samples.size + 1.0)), 1.0 - 1.0 / (samples.size + 1.0))
    z0 = float(norm.ppf(prop))
    jack_mean = float(np.mean(jack))
    diffs = jack_mean - jack
    num = float(np.sum(diffs ** 3))
    den = float(np.sum(diffs ** 2))
    if den <= 1e-30:
        acc = 0.0
    else:
        acc = num / (6.0 * (den ** 1.5))
    alpha = (1.0 - float(ci)) / 2.0
    z_lo = float(norm.ppf(alpha))
    z_hi = float(norm.ppf(1.0 - alpha))

    def _adj(z: float) -> float:
        denom = 1.0 - acc * (z0 + z)
        if abs(denom) <= 1e-12:
            return float("nan")
        return float(norm.cdf(z0 + (z0 + z) / denom))

    p_lo = _adj(z_lo)
    p_hi = _adj(z_hi)
    if not np.isfinite(p_lo) or not np.isfinite(p_hi):
        return nan, nan
    p_lo = min(max(p_lo, 0.0), 1.0)
    p_hi = min(max(p_hi, 0.0), 1.0)
    return float(np.percentile(samples, 100.0 * p_lo)), float(np.percentile(samples, 100.0 * p_hi))


def bootstrap_ewsd_from_compartments(
    compartments: Sequence[CompartmentBootstrapData],
    *,
    acoustic_balance_alpha: float = ACOUSTIC_BALANCE_ALPHA_DEFAULT,
    n_boot: int = 800,
    ci: float = 0.95,
    seed: int = 0,
    propagate_ratio_uncertainty: bool = True,
) -> dict[str, Any]:
    """
    Partial-multiset sensitivity analysis for strict and acoustic-balanced EWSD.

    ``ewsd_score_total`` remains the Excel-ratio point estimate (F-048). When
    ``propagate_ratio_uncertainty`` is True the resampled draws use
    ``E_k / sum(E)``; that companion point is exported separately as
    ``ewsd_score_total_point_under_bootstrap_ratios`` so the two estimands
    are never conflated.

    The percentile and BCa intervals are a sensitivity analysis: partials of a
    note are a deterministic physical structure, not an i.i.d. draw from a
    superpopulation, so the interval has no defined coverage property.

    Sources that are **not** sampled: peak-picking threshold, FFT length and
    tier, window function, f0 estimation error, H/I/S assignment.

    Returns keys aligned with ``density_uncertainty.bootstrap_note_density_final``
    plus B1/B2 diagnostics. ``uncertainty_sources`` is
    ``partial_multiset_sensitivity`` (or ``unavailable``).
    """
    if not (0.0 < float(ci) < 1.0):
        raise ValueError("ci must be in (0, 1)")
    n_boot = max(1, int(n_boot))
    rng = np.random.default_rng(int(seed))

    fixed_resampled: list[tuple[np.ndarray, Optional[np.ndarray], float]] = []
    for comp in compartments:
        fixed_resampled.append((comp.amplitudes, comp.frequencies_hz, float(comp.analysis_ratio)))
    point_strict, point_balanced = _metrics_for_resample(
        compartments,
        fixed_resampled,
        acoustic_balance_alpha=acoustic_balance_alpha,
    )

    if propagate_ratio_uncertainty:
        energy_r = _energy_ratios_from_compartments(compartments)
        energy_fixed = [
            (comp.amplitudes, comp.frequencies_hz, float(r))
            for comp, r in zip(compartments, energy_r, strict=True)
        ]
        point_under_strict, point_under_balanced = _metrics_for_resample(
            compartments,
            energy_fixed,
            acoustic_balance_alpha=acoustic_balance_alpha,
        )
        ratio_def_boot = "resampled_energy_ratio"
    else:
        point_under_strict, point_under_balanced = point_strict, point_balanced
        ratio_def_boot = "excel_analysis_ratio"

    n_partials = int(sum(int(comp.amplitudes.size) for comp in compartments))
    if n_partials <= 2 or not any(comp.amplitudes.size > 0 for comp in compartments):
        nan = float("nan")
        return {
            "ewsd_score_total": point_strict,
            "ewsd_score_acoustic_balanced": point_balanced,
            "ewsd_score_total_point_under_bootstrap_ratios": float(point_under_strict),
            "ewsd_score_acoustic_balanced_point_under_bootstrap_ratios": float(point_under_balanced),
            "ewsd_ratio_definition_point": "excel_analysis_ratio",
            "ewsd_ratio_definition_bootstrap": ratio_def_boot,
            "ewsd_score_total_ci_low": nan,
            "ewsd_score_total_ci_high": nan,
            "ewsd_score_acoustic_balanced_ci_low": nan,
            "ewsd_score_acoustic_balanced_ci_high": nan,
            "ewsd_score_total_ci_low_bca": nan,
            "ewsd_score_total_ci_high_bca": nan,
            "ewsd_score_acoustic_balanced_ci_low_bca": nan,
            "ewsd_score_acoustic_balanced_ci_high_bca": nan,
            "ewsd_score_total_rel_uncertainty": nan,
            "ewsd_score_acoustic_balanced_rel_uncertainty": nan,
            "ewsd_bootstrap_bias_absolute": nan,
            "ewsd_bootstrap_bias_relative": nan,
            "uncertainty_sources": "unavailable",
            "n_boot": int(n_boot),
            "ci_mass": float(ci),
        }

    boot_strict = np.empty(n_boot, dtype=float)
    boot_balanced = np.empty(n_boot, dtype=float)

    for b in range(n_boot):
        draw: list[tuple[np.ndarray, Optional[np.ndarray], float]] = []
        energies: list[float] = []
        for comp in compartments:
            amps = comp.amplitudes
            freqs = comp.frequencies_hz
            if amps.size == 0:
                draw.append((amps, freqs, float(comp.analysis_ratio)))
                energies.append(0.0)
                continue
            idx = rng.integers(0, amps.size, amps.size)
            amps_rs = amps[idx]
            freqs_rs = freqs[idx] if freqs is not None and freqs.size == amps.size else None
            draw.append((amps_rs, freqs_rs, float(comp.analysis_ratio)))
            energies.append(_compartment_energy(amps_rs))

        if propagate_ratio_uncertainty:
            e_total = float(sum(energies))
            if e_total > 1e-30:
                draw = [(amps, freqs, e / e_total) for (amps, freqs, _), e in zip(draw, energies, strict=True)]
            else:
                draw = [(amps, freqs, 0.0) for amps, freqs, _ in draw]

        s, bal = _metrics_for_resample(
            compartments,
            draw,
            acoustic_balance_alpha=acoustic_balance_alpha,
        )
        boot_strict[b] = s
        boot_balanced[b] = bal

    lo_q = (1.0 - float(ci)) / 2.0 * 100.0
    hi_q = (1.0 + float(ci)) / 2.0 * 100.0

    def _rel_unc(point: float, samples: np.ndarray) -> float:
        std = float(np.std(samples, ddof=1)) if n_boot > 1 else 0.0
        return float(std / abs(point)) if abs(point) > 1e-30 else float("nan")

    jack_s, jack_b = _jackknife_estimates(
        compartments,
        acoustic_balance_alpha=acoustic_balance_alpha,
        propagate_ratio_uncertainty=propagate_ratio_uncertainty,
    )
    bca_s = _bca_limits(point_strict, boot_strict, jack_s, float(ci))
    bca_b = _bca_limits(point_balanced, boot_balanced, jack_b, float(ci))
    bias_abs = float(np.mean(boot_strict) - point_strict)
    bias_rel = float(bias_abs / abs(point_strict)) if abs(point_strict) > 1e-30 else float("nan")

    return {
        "ewsd_score_total": float(point_strict),
        "ewsd_score_acoustic_balanced": float(point_balanced),
        "ewsd_score_total_point_under_bootstrap_ratios": float(point_under_strict),
        "ewsd_score_acoustic_balanced_point_under_bootstrap_ratios": float(point_under_balanced),
        "ewsd_ratio_definition_point": "excel_analysis_ratio",
        "ewsd_ratio_definition_bootstrap": ratio_def_boot,
        "ewsd_score_total_ci_low": float(np.percentile(boot_strict, lo_q)),
        "ewsd_score_total_ci_high": float(np.percentile(boot_strict, hi_q)),
        "ewsd_score_acoustic_balanced_ci_low": float(np.percentile(boot_balanced, lo_q)),
        "ewsd_score_acoustic_balanced_ci_high": float(np.percentile(boot_balanced, hi_q)),
        "ewsd_score_total_ci_low_bca": bca_s[0],
        "ewsd_score_total_ci_high_bca": bca_s[1],
        "ewsd_score_acoustic_balanced_ci_low_bca": bca_b[0],
        "ewsd_score_acoustic_balanced_ci_high_bca": bca_b[1],
        "ewsd_score_total_rel_uncertainty": _rel_unc(point_strict, boot_strict),
        "ewsd_score_acoustic_balanced_rel_uncertainty": _rel_unc(point_balanced, boot_balanced),
        "ewsd_bootstrap_bias_absolute": bias_abs,
        "ewsd_bootstrap_bias_relative": bias_rel,
        "uncertainty_sources": "partial_multiset_sensitivity",
        "n_boot": int(n_boot),
        "ci_mass": float(ci),
    }
