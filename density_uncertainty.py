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

from typing import Dict, Mapping, Sequence, Tuple

import numpy as np

__all__ = [
    "bootstrap_density_ci",
    "bootstrap_note_density_final",
    "nfft_sensitivity",
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
