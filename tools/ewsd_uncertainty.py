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
    Non-parametric bootstrap CI for strict and acoustic-balanced EWSD.

    Returns keys aligned with ``density_uncertainty.bootstrap_note_density_final``:
    ``ewsd_score_total``, ``ewsd_score_acoustic_balanced`` (point estimates),
    ``*_ci_low``, ``*_ci_high``, ``*_rel_uncertainty``, ``uncertainty_sources``,
    ``n_boot``, ``ci_mass``.
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

    if not any(comp.amplitudes.size > 0 for comp in compartments):
        nan = float("nan")
        return {
            "ewsd_score_total": point_strict,
            "ewsd_score_acoustic_balanced": point_balanced,
            "ewsd_score_total_ci_low": nan,
            "ewsd_score_total_ci_high": nan,
            "ewsd_score_acoustic_balanced_ci_low": nan,
            "ewsd_score_acoustic_balanced_ci_high": nan,
            "ewsd_score_total_rel_uncertainty": nan,
            "ewsd_score_acoustic_balanced_rel_uncertainty": nan,
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

    return {
        "ewsd_score_total": float(point_strict),
        "ewsd_score_acoustic_balanced": float(point_balanced),
        "ewsd_score_total_ci_low": float(np.percentile(boot_strict, lo_q)),
        "ewsd_score_total_ci_high": float(np.percentile(boot_strict, hi_q)),
        "ewsd_score_acoustic_balanced_ci_low": float(np.percentile(boot_balanced, lo_q)),
        "ewsd_score_acoustic_balanced_ci_high": float(np.percentile(boot_balanced, hi_q)),
        "ewsd_score_total_rel_uncertainty": _rel_unc(point_strict, boot_strict),
        "ewsd_score_acoustic_balanced_rel_uncertainty": _rel_unc(point_balanced, boot_balanced),
        "uncertainty_sources": "partials+ratios" if propagate_ratio_uncertainty else "partials",
        "n_boot": int(n_boot),
        "ci_mass": float(ci),
    }
