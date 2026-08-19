"""Uncertainty quantification for the per-note scalar density (`note_density_final`).

`note_density_final = r_H * D_H + r_I * D_I + r_S * D_S`, where each band sum
`D_c = sum_i phi(A_i)` aggregates per-partial contributions under the active
amplitude weight function and `r_c` are the measured component energy ratios.

A single scalar with no stated uncertainty is fragile for scientific use. This
module provides two complementary, dependency-free (numpy-only) uncertainty
estimates:

1. ``bootstrap_note_density_final`` / ``bootstrap_density_ci`` — a
   non-parametric bootstrap over the per-partial contributions within each
   band. It captures the sampling uncertainty of the finite set of detected
   partials. ``bootstrap_note_density_final`` additionally supports
   ``propagate_ratio_uncertainty=True``, which recomputes the component energy
   ratios *inside each resample* (from the bootstrapped band energies) so the
   uncertainty of the ratios is propagated jointly with the band sums — the
   fuller UQ now used by the compiled pipeline. With ratios held fixed the
   estimate is the (smaller) partials-only uncertainty.

2. ``nfft_sensitivity`` — the dispersion of ``note_density_final`` recomputed
   across analysis resolutions (n_fft / window). It reports the coefficient of
   variation and relative range, i.e. how much the metric moves under
   reasonable analysis-parameter perturbations.

Both are descriptive (no distributional assumptions beyond the bootstrap's
exchangeability) and are intended to accompany the point estimate, not replace
it.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np

from constants import (
    CI_BASIS_INDEPENDENT_FRAME_MIN,
    CI_WIDTH_PARTIAL_CORRELATION_N,
    DENSITY_CI_DEFAULT_ON,
    DENSITY_CI_N_BOOT,
    DENSITY_CI_SEED,
    DENSITY_FRAGILE_CI_PCT,
    DENSITY_FRAGILE_PERTURBATION_PCT,
    DENSITY_WINDOW_PERTURBATION_MS,
    UNCERTAINTY_REL_FLAG_PCT,
)

__all__ = [
    "bootstrap_density_ci",
    "bootstrap_effective_component_density",
    "bootstrap_note_density_final",
    "build_uncertainty_summary",
    "ci_basis_counts",
    "ci_relative_width_pct",
    "ci_resampling_provenance",
    "evaluate_density_fragility",
    "nfft_sensitivity",
    "window_perturbation_spread_pct",
    "DENSITY_CI_DEFAULT_ON",
    "DENSITY_CI_N_BOOT",
    "DENSITY_CI_SEED",
    "DENSITY_WINDOW_PERTURBATION_MS",
]


def _band_density_sum(amps: np.ndarray, weight_function: str) -> float:
    """Per-band density sum ``D`` under the GUI amplitude weight function.

    Mirrors the canonical rules in
    ``compile_metrics.extract_density_component_sum``:
    ``linear -> sum(A)``, ``log -> log10(1 + sum(A))``,
    ``power -> sum(A^2)``. Any other key is treated as ``linear`` (documented;
    the CI for exotic discrete weight keys is then a linear-sum approximation).
    """
    wf = str(weight_function or "linear").strip().lower()
    a = amps[amps > 0.0] if amps.size else amps
    s = float(np.sum(a)) if a.size else 0.0
    if wf == "power":
        return float(np.sum(a * a)) if a.size else 0.0
    if wf == "log":
        return float(np.log10(1.0 + max(0.0, s)))
    return s  # linear (and fallback)


def bootstrap_note_density_final(
    band_amplitudes: Mapping[str, Tuple[Sequence[float], float]],
    *,
    weight_function: str = "linear",
    n_boot: int = 1500,
    ci: float = 0.95,
    seed: int = 0,
    propagate_ratio_uncertainty: bool = False,
) -> Dict[str, float]:
    """Transform-aware bootstrap CI for ``note_density_final``.

    ``note_density_final = sum_band r_band * D_band`` where
    ``D_band = phi(amplitudes_band)`` under ``weight_function`` (so the weight
    transform — e.g. the ``log`` of the band sum — is applied *inside* each
    bootstrap resample, not to a pre-aggregated value). Per-partial amplitudes
    within each band are resampled with replacement.

    Parameters
    ----------
    band_amplitudes:
        ``band -> (per_partial_amplitudes, energy_ratio)``.
    weight_function:
        GUI amplitude weight key (``linear`` / ``log`` / ``power`` / ...).
    propagate_ratio_uncertainty:
        When ``False`` (default) the measured component energy ratios
        ``r_band`` are held fixed across resamples (partials-only uncertainty).
        When ``True`` the ratios are *recomputed inside each resample* from the
        bootstrapped band energies ``E_band = sum(A_i^2)`` (so
        ``r_band = E_band / sum_band E_band``). This jointly propagates the
        sampling uncertainty of BOTH the band sums and the component ratios —
        the fuller uncertainty quantification. The point estimate always uses
        the originally-measured ratios.

    Returns the same keys as :func:`bootstrap_density_ci`, plus
    ``uncertainty_sources`` describing what was propagated.
    """
    if not (0.0 < float(ci) < 1.0):
        raise ValueError("ci must be in (0, 1)")
    n_boot = max(1, int(n_boot))
    rng = np.random.default_rng(int(seed))

    bands = []
    point = 0.0
    for name, (amps, ratio) in band_amplitudes.items():
        a = _as_1d_float(amps)
        a = a[a > 0.0]
        r = float(ratio)
        bands.append((a, r))
        point += r * _band_density_sum(a, weight_function)

    boot = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        resampled = []
        for a, r in bands:
            if a.size == 0:
                resampled.append((a, r, 0.0))
                continue
            idx = rng.integers(0, a.size, a.size)
            a_rs = a[idx]
            e_band = float(np.sum(a_rs * a_rs))
            resampled.append((a_rs, r, e_band))
        if propagate_ratio_uncertainty:
            e_total = sum(e for _, _, e in resampled)
            if e_total > 1e-30:
                total = sum(
                    (e / e_total) * _band_density_sum(a_rs, weight_function)
                    for a_rs, _, e in resampled
                )
            else:
                total = 0.0
        else:
            total = sum(
                r * _band_density_sum(a_rs, weight_function)
                for a_rs, r, _ in resampled
                if a_rs.size
            )
        boot[b] = total

    lo_q = (1.0 - float(ci)) / 2.0 * 100.0
    hi_q = (1.0 + float(ci)) / 2.0 * 100.0
    bstd = float(np.std(boot, ddof=1)) if n_boot > 1 else 0.0
    rel = float(bstd / abs(point)) if abs(point) > 1e-30 else float("nan")
    return {
        "point_estimate": float(point),
        "bootstrap_mean": float(np.mean(boot)),
        "bootstrap_std": bstd,
        "ci_low": float(np.percentile(boot, lo_q)),
        "ci_high": float(np.percentile(boot, hi_q)),
        "relative_uncertainty": rel,
        "n_boot": int(n_boot),
        "ci_mass": float(ci),
        "uncertainty_sources": (
            "partials+ratios" if propagate_ratio_uncertainty else "partials"
        ),
    }


def _as_1d_float(x: Sequence[float]) -> np.ndarray:
    a = np.asarray(list(x), dtype=float).ravel()
    return a[np.isfinite(a)]


def bootstrap_density_ci(
    band_contributions: Mapping[str, Tuple[Sequence[float], float]],
    *,
    n_boot: int = 2000,
    ci: float = 0.95,
    seed: int = 0,
) -> Dict[str, float]:
    """Bootstrap confidence interval for ``note_density_final``.

    Parameters
    ----------
    band_contributions:
        Mapping ``band -> (per_partial_contributions, energy_ratio)`` where
        ``per_partial_contributions`` is the sequence of per-partial weighted
        contributions ``phi(A_i)`` for that band (so ``D_band = sum(...)``) and
        ``energy_ratio`` is the band's measured component energy ratio ``r_band``.
        Bands with an empty contribution list contribute ``r_band * 0``.
    n_boot:
        Number of bootstrap resamples (>= 1).
    ci:
        Two-sided central interval mass (e.g. 0.95 → 2.5/97.5 percentiles).
    seed:
        RNG seed for reproducibility.

    Returns
    -------
    dict with keys: ``point_estimate``, ``bootstrap_mean``, ``bootstrap_std``,
    ``ci_low``, ``ci_high``, ``relative_uncertainty`` (std/|point|, NaN if
    point≈0), ``n_boot``, ``ci_mass``.
    """
    if not (0.0 < float(ci) < 1.0):
        raise ValueError("ci must be in (0, 1)")
    n_boot = max(1, int(n_boot))
    rng = np.random.default_rng(int(seed))

    bands = []
    point = 0.0
    for name, (contribs, ratio) in band_contributions.items():
        arr = _as_1d_float(contribs)
        r = float(ratio)
        bands.append((arr, r))
        point += r * float(np.sum(arr)) if arr.size else 0.0

    boot = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        total = 0.0
        for arr, r in bands:
            if arr.size == 0:
                continue
            idx = rng.integers(0, arr.size, arr.size)
            total += r * float(np.sum(arr[idx]))
        boot[b] = total

    lo_q = (1.0 - float(ci)) / 2.0 * 100.0
    hi_q = (1.0 + float(ci)) / 2.0 * 100.0
    ci_low = float(np.percentile(boot, lo_q))
    ci_high = float(np.percentile(boot, hi_q))
    bmean = float(np.mean(boot))
    bstd = float(np.std(boot, ddof=1)) if n_boot > 1 else 0.0
    rel = float(bstd / abs(point)) if abs(point) > 1e-30 else float("nan")
    return {
        "point_estimate": float(point),
        "bootstrap_mean": bmean,
        "bootstrap_std": bstd,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "relative_uncertainty": rel,
        "n_boot": int(n_boot),
        "ci_mass": float(ci),
    }


def ci_relative_width_pct(
    point_estimate: float,
    ci_low: float,
    ci_high: float,
) -> float:
    """Two-sided CI width as a percentage of ``|point_estimate|``."""
    try:
        point = float(point_estimate)
        lo = float(ci_low)
        hi = float(ci_high)
    except (TypeError, ValueError):
        return float("nan")
    if not (np.isfinite(point) and np.isfinite(lo) and np.isfinite(hi)):
        return float("nan")
    if abs(point) <= 1e-30:
        return float("nan")
    return float(100.0 * abs(hi - lo) / abs(point))


def window_perturbation_spread_pct(
    values: Sequence[float],
    *,
    center: Optional[float] = None,
) -> float:
    """``100 * (max - min) / |center|`` over a set of window-perturbed densities."""
    arr = _as_1d_float(values)
    if arr.size == 0:
        return float("nan")
    if center is None:
        mid = float(arr[0]) if arr.size == 1 else float(np.median(arr))
    else:
        try:
            mid = float(center)
        except (TypeError, ValueError):
            mid = float("nan")
    if not np.isfinite(mid) or abs(mid) <= 1e-30:
        return float("nan")
    return float(100.0 * (float(np.max(arr)) - float(np.min(arr))) / abs(mid))


def evaluate_density_fragility(
    *,
    point_estimate: float = float("nan"),
    ci_low: float = float("nan"),
    ci_high: float = float("nan"),
    perturbation_spread_pct: float = float("nan"),
    fragile_ci_pct: float = DENSITY_FRAGILE_CI_PCT,
    fragile_perturbation_pct: float = DENSITY_FRAGILE_PERTURBATION_PCT,
) -> Dict[str, float]:
    """Flag a density scalar as fragile when CI width or window spread exceeds 10 %."""
    ci_width = ci_relative_width_pct(point_estimate, ci_low, ci_high)
    try:
        spread = float(perturbation_spread_pct)
    except (TypeError, ValueError):
        spread = float("nan")
    fragile_ci = bool(np.isfinite(ci_width) and ci_width > float(fragile_ci_pct))
    fragile_pert = bool(np.isfinite(spread) and spread > float(fragile_perturbation_pct))
    return {
        "density_ci_relative_width_pct": float(ci_width),
        "density_perturbation_spread_pct": float(spread),
        "density_fragile": bool(fragile_ci or fragile_pert),
        "density_fragile_from_ci": bool(fragile_ci),
        "density_fragile_from_perturbation": bool(fragile_pert),
    }


def bootstrap_effective_component_density(
    amplitudes: Sequence[float],
    *,
    n_boot: int = DENSITY_CI_N_BOOT,
    ci: float = 0.95,
    seed: int = DENSITY_CI_SEED,
) -> Dict[str, float]:
    """Bootstrap CI for F-047 ``note_effective_component_density``.

    Resamples the pooled validated-partial amplitudes and recomputes
    ``(Σ A²)² / Σ A⁴``. The point estimate is the participation ratio on
    the original amplitudes; algebra is unchanged.
    """
    from validated_partials import participation_ratio_from_amplitudes

    if not (0.0 < float(ci) < 1.0):
        raise ValueError("ci must be in (0, 1)")
    amps = _as_1d_float(amplitudes)
    amps = amps[amps > 0.0]
    point = float(participation_ratio_from_amplitudes(amps))
    n_boot = max(1, int(n_boot))
    nan = float("nan")
    if amps.size < 2:
        return {
            "point_estimate": point,
            "ci_low": nan,
            "ci_high": nan,
            "relative_uncertainty": nan,
            "n_boot": int(n_boot),
            "ci_mass": float(ci),
            "ci_basis_partial_count": int(amps.size),
        }
    rng = np.random.default_rng(int(seed))
    boot = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        idx = rng.integers(0, amps.size, amps.size)
        boot[b] = float(participation_ratio_from_amplitudes(amps[idx]))
    lo_q = (1.0 - float(ci)) / 2.0 * 100.0
    hi_q = (1.0 + float(ci)) / 2.0 * 100.0
    bstd = float(np.std(boot, ddof=1)) if n_boot > 1 else 0.0
    rel = float(bstd / abs(point)) if abs(point) > 1e-30 else nan
    return {
        "point_estimate": point,
        "ci_low": float(np.percentile(boot, lo_q)),
        "ci_high": float(np.percentile(boot, hi_q)),
        "relative_uncertainty": rel,
        "n_boot": int(n_boot),
        "ci_mass": float(ci),
        "ci_basis_partial_count": int(amps.size),
    }


def ci_resampling_provenance(
    *,
    unit: str = "partials",
    n_resampled: float = float("nan"),
    n_boot: int = DENSITY_CI_N_BOOT,
    seed: int = DENSITY_CI_SEED,
    independent_frame_count: float = float("nan"),
    relative_width_pct: float = float("nan"),
    block_length_frames: float = float("nan"),
    rel_flag_pct: float = UNCERTAINTY_REL_FLAG_PCT,
    partial_correlation_n: int = CI_WIDTH_PARTIAL_CORRELATION_N,
) -> Dict[str, Any]:
    """Diagnostic CI provenance. Does not change the estimator."""
    try:
        n = float(n_resampled)
    except (TypeError, ValueError):
        n = float("nan")
    try:
        frames = float(independent_frame_count)
    except (TypeError, ValueError):
        frames = float("nan")
    try:
        width = float(relative_width_pct)
    except (TypeError, ValueError):
        width = float("nan")
    try:
        block = float(block_length_frames)
    except (TypeError, ValueError):
        block = float("nan")
    notes: list[str] = []
    if np.isfinite(frames) and frames < float(CI_BASIS_INDEPENDENT_FRAME_MIN):
        notes.append("low_independent_frames")
    token = str(unit or "partials").strip().lower() or "partials"
    try:
        n_corr = int(partial_correlation_n)
    except (TypeError, ValueError):
        n_corr = int(CI_WIDTH_PARTIAL_CORRELATION_N)
    if token == "partials" and np.isfinite(n) and n > float(n_corr):
        notes.append("high_partial_correlation")
    try:
        thresh = float(rel_flag_pct)
    except (TypeError, ValueError):
        thresh = float(UNCERTAINTY_REL_FLAG_PCT)
    wide = bool(np.isfinite(width) and width > thresh)
    return {
        "ci_resampling_unit": token,
        "ci_n_resampled": n if np.isfinite(n) else None,
        "ci_bootstrap_iterations": int(n_boot),
        "ci_block_length_frames": block if np.isfinite(block) else None,
        "ci_seed": int(seed),
        "ci_width_flag": "wide" if wide else "",
        "ci_width_note": "; ".join(notes) if wide and notes else "",
    }


def ci_basis_counts(
    *,
    independent_frame_count: float = float("nan"),
    partial_count: float = float("nan"),
    min_independent_frames: int = CI_BASIS_INDEPENDENT_FRAME_MIN,
) -> Dict[str, Any]:
    """Sample-size metadata that must sit beside every exported CI."""
    try:
        frames = float(independent_frame_count)
    except (TypeError, ValueError):
        frames = float("nan")
    try:
        parts = float(partial_count)
    except (TypeError, ValueError):
        parts = float("nan")
    try:
        min_n = int(min_independent_frames)
    except (TypeError, ValueError):
        min_n = int(CI_BASIS_INDEPENDENT_FRAME_MIN)
    insufficient = bool(np.isfinite(frames) and frames < float(min_n))
    return {
        "ci_basis_frame_count": frames,
        "ci_basis_partial_count": parts,
        "ci_basis_frames_insufficient": insufficient,
    }


def build_uncertainty_summary(
    rows: Sequence[Mapping[str, Any]],
    *,
    rel_flag_pct: float = UNCERTAINTY_REL_FLAG_PCT,
) -> "pd.DataFrame":
    """Per-note relative uncertainty and flags for the research workbook."""
    import pandas as pd

    try:
        thresh = float(rel_flag_pct)
    except (TypeError, ValueError):
        thresh = float(UNCERTAINTY_REL_FLAG_PCT)
    metrics = (
        (
            "note_density_final",
            "note_density_final_rel_uncertainty",
            "note_density_final_ci_low",
            "note_density_final_ci_high",
        ),
        (
            "note_effective_component_density",
            "note_effective_component_density_rel_uncertainty",
            "note_effective_component_density_ci_low",
            "note_effective_component_density_ci_high",
        ),
        (
            "EWSD_score_acoustic_balanced",
            "EWSD_score_acoustic_balanced_rel_uncertainty",
            "EWSD_score_acoustic_balanced_ci_low",
            "EWSD_score_acoustic_balanced_ci_high",
        ),
    )
    out_rows: list[dict[str, Any]] = []
    for raw in rows:
        note = str(raw.get("Note") or raw.get("sample_note_tag") or "")
        try:
            frames = float(raw.get("ci_basis_frame_count", raw.get(
                "sustain_frame_count_independent", float("nan")
            )))
        except (TypeError, ValueError):
            frames = float("nan")
        try:
            parts = float(raw.get("ci_basis_partial_count", float("nan")))
        except (TypeError, ValueError):
            parts = float("nan")
        basis = ci_basis_counts(
            independent_frame_count=frames, partial_count=parts
        )
        for name, rel_key, lo_key, hi_key in metrics:
            try:
                rel = float(raw.get(rel_key, float("nan")))
            except (TypeError, ValueError):
                rel = float("nan")
            if not np.isfinite(rel):
                try:
                    point = float(raw.get(name, float("nan")))
                    lo = float(raw.get(lo_key, float("nan")))
                    hi = float(raw.get(hi_key, float("nan")))
                    width = ci_relative_width_pct(point, lo, hi)
                    rel = float(width / 100.0) if np.isfinite(width) else float("nan")
                except (TypeError, ValueError):
                    rel = float("nan")
            rel_pct = float(rel * 100.0) if np.isfinite(rel) and abs(rel) <= 2.0 else (
                float(rel) if np.isfinite(rel) else float("nan")
            )
            flagged = bool(np.isfinite(rel_pct) and rel_pct > thresh)
            out_rows.append(
                {
                    "Note": note,
                    "metric": name,
                    "rel_uncertainty": rel if np.isfinite(rel) else float("nan"),
                    "rel_uncertainty_pct": rel_pct,
                    "uncertainty_flag": flagged,
                    "uncertainty_flag_threshold_pct": thresh,
                    "ci_basis_frame_count": basis["ci_basis_frame_count"],
                    "ci_basis_partial_count": basis["ci_basis_partial_count"],
                    "ci_basis_frames_insufficient": basis[
                        "ci_basis_frames_insufficient"
                    ],
                }
            )
    return pd.DataFrame(out_rows)


def nfft_sensitivity(values_by_resolution: Mapping[object, float]) -> Dict[str, float]:
    """Dispersion of ``note_density_final`` across analysis resolutions.

    Parameters
    ----------
    values_by_resolution:
        Mapping ``resolution_key -> note_density_final`` (e.g.
        ``{4096: 871.9, 8192: 905.3, 16384: 890.1}``). Non-finite values are
        ignored.

    Returns
    -------
    dict with: ``n``, ``mean``, ``std``, ``min``, ``max``,
    ``coefficient_of_variation`` (std/|mean|), ``relative_range``
    ((max-min)/|mean|). Returns NaNs when fewer than two finite values.
    """
    vals = _as_1d_float(list(values_by_resolution.values()))
    out = {
        "n": int(vals.size),
        "mean": float("nan"),
        "std": float("nan"),
        "min": float("nan"),
        "max": float("nan"),
        "coefficient_of_variation": float("nan"),
        "relative_range": float("nan"),
    }
    if vals.size == 0:
        return out
    mean = float(np.mean(vals))
    out["mean"] = mean
    out["min"] = float(np.min(vals))
    out["max"] = float(np.max(vals))
    if vals.size >= 2:
        std = float(np.std(vals, ddof=1))
        out["std"] = std
        if abs(mean) > 1e-30:
            out["coefficient_of_variation"] = float(std / abs(mean))
            out["relative_range"] = float((out["max"] - out["min"]) / abs(mean))
    else:
        out["std"] = 0.0
    return out
