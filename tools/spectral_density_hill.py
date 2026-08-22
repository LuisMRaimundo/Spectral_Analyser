#!/usr/bin/env python3
"""
spectral_density_hill.py — Auditory Component Density (ACD v1.0).

Numpy-only numerical reference for Hill-number density on ERB-merged
peaks (F-057, F-058, F-059, F-060). F-051–F-054 are already allocated
in ``docs/METRIC_FORMULA_INDEX.md`` (harmonic matching / body-stop);
ACD occupies the next free IDs.

References
----------
- Glasberg, B. R., & Moore, B. C. J. (1990). Derivation of auditory
  filter shapes from notched-noise data. *Hearing Research, 47*(1–2),
  103–138.
- Moore, B. C. J., & Glasberg, B. R. (1983). Suggested formulae for
  calculating auditory-filter bandwidths and excitation patterns.
  *Journal of the Acoustical Society of America, 74*(3), 750–753.
- Hill, M. O. (1973). Diversity and evenness: A unifying notation and
  its consequences. *Ecology, 54*(2), 427–432.
- Jost, L. (2006). Entropy and diversity. *Oikos, 113*(2), 363–375.

See REFERENCES.md at the repository root for canonical APA-7 entries.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Optional

import numpy as np

MODULE_REVISION: str = "ACD v1.0"
ACD_FORMULA_IDS: str = "F-057,F-058,F-059,F-060"

ERB_SLOPE: float = 0.108  # Glasberg & Moore (1990) -- primary_source
ERB_INTERCEPT_HZ: float = 24.7  # Glasberg & Moore (1990) -- primary_source
ERB_RATE_SCALE: float = 21.4  # Moore & Glasberg (1983) -- primary_source
ERB_RATE_COEFF: float = 0.00437  # Moore & Glasberg (1983) -- primary_source
ENERGY_EPS: float = 1e-30  # numerical floor -- internal_default
ERB_FRACTION_DEFAULT: float = 1.0  # merge bandwidth in ERB units -- internal_default

MergeStrategy = Literal["moving_centroid", "fixed_erb_grid"]
MERGE_STRATEGY_MOVING_CENTROID: MergeStrategy = "moving_centroid"
MERGE_STRATEGY_FIXED_ERB_GRID: MergeStrategy = "fixed_erb_grid"
MERGE_STRATEGIES: tuple[MergeStrategy, ...] = (
    MERGE_STRATEGY_MOVING_CENTROID,
    MERGE_STRATEGY_FIXED_ERB_GRID,
)
# Task 1.3: fixed_erb_grid reduced Stage 1 FFT-tier wander (3.80% → 2.74%).
# Neither strategy fell below ~2%; hard assignment is the remaining limit.
MERGE_STRATEGY_DEFAULT: MergeStrategy = MERGE_STRATEGY_FIXED_ERB_GRID

_COMPARTMENT_KEYS: tuple[str, str, str] = ("harmonic", "inharmonic", "subbass")


def erb_bandwidth_hz(freq_hz: np.ndarray) -> np.ndarray:
    """ERB(f) = 0.108*f + 24.7  (Glasberg & Moore, 1990)."""
    f = np.asarray(freq_hz, dtype=float)
    return ERB_SLOPE * f + ERB_INTERCEPT_HZ


def erb_rate(freq_hz: np.ndarray) -> np.ndarray:
    """E(f) = 21.4 * log10(1 + 0.00437*f)  (Moore & Glasberg, 1983)."""
    f = np.asarray(freq_hz, dtype=float)
    return ERB_RATE_SCALE * np.log10(1.0 + ERB_RATE_COEFF * f)


def _finite_nonnegative_pair(
    freq_hz: np.ndarray,
    amplitudes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    f = np.asarray(freq_hz, dtype=float).reshape(-1)
    a = np.asarray(amplitudes, dtype=float).reshape(-1)
    if f.size != a.size:
        raise ValueError("freq_hz and amplitudes must have the same length")
    mask = np.isfinite(f) & np.isfinite(a) & (a >= 0.0) & (f > 0.0)
    return f[mask].astype(float, copy=False), a[mask].astype(float, copy=False)


def merge_peaks_within_erb(
    freq_hz: np.ndarray,
    amplitudes: np.ndarray,
    *,
    erb_fraction: float = ERB_FRACTION_DEFAULT,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Merge peaks lying inside one auditory filter into a single component.

    Returns (merged_freq_hz, merged_amplitude, merged_count).

    Algorithm (single pass, frequency-ascending):
      - sort by frequency
      - open a cluster at the first peak
      - a subsequent peak joins the open cluster if
            f_next - f_cluster_centroid <= erb_fraction * ERB(f_cluster_centroid)
        otherwise close the cluster and open a new one
      - merged amplitude   = sqrt(sum(A_i^2))            (energy-preserving)
      - merged frequency   = energy-weighted centroid    sum(f_i*A_i^2)/sum(A_i^2)
      - merged_count       = number of peaks absorbed

    Total energy is conserved exactly: sum(merged_A^2) == sum(A^2) to 1e-12.

    Glasberg & Moore (1990); Moore & Glasberg (1983).
    """
    frac = float(erb_fraction)
    if not np.isfinite(frac) or frac <= 0.0:
        raise ValueError("erb_fraction must be finite and > 0")

    f, a = _finite_nonnegative_pair(freq_hz, amplitudes)
    if f.size == 0:
        empty = np.zeros(0, dtype=float)
        return empty, empty, np.zeros(0, dtype=int)

    order = np.argsort(f, kind="mergesort")
    f = f[order]
    a = a[order]

    clusters_f: list[list[float]] = [[float(f[0])]]
    clusters_a: list[list[float]] = [[float(a[0])]]

    def _centroid(cf: list[float], ca: list[float]) -> float:
        pwr = np.square(np.asarray(ca, dtype=float))
        tot = float(np.sum(pwr))
        if tot <= ENERGY_EPS:
            return float(np.mean(np.asarray(cf, dtype=float)))
        return float(np.dot(np.asarray(cf, dtype=float), pwr) / tot)

    for i in range(1, int(f.size)):
        centroid = _centroid(clusters_f[-1], clusters_a[-1])
        erb = float(erb_bandwidth_hz(np.asarray([centroid], dtype=float))[0])
        if float(f[i]) - centroid <= frac * erb:
            clusters_f[-1].append(float(f[i]))
            clusters_a[-1].append(float(a[i]))
        else:
            clusters_f.append([float(f[i])])
            clusters_a.append([float(a[i])])

    n_c = len(clusters_f)
    merged_f = np.empty(n_c, dtype=float)
    merged_a = np.empty(n_c, dtype=float)
    merged_n = np.empty(n_c, dtype=int)
    for i, (cf, ca) in enumerate(zip(clusters_f, clusters_a)):
        pwr = np.square(np.asarray(ca, dtype=float))
        tot = float(np.sum(pwr))
        merged_a[i] = math.sqrt(max(tot, 0.0))
        merged_f[i] = _centroid(cf, ca)
        merged_n[i] = int(len(ca))
    return merged_f, merged_a, merged_n


def merge_peaks_fixed_erb_grid(
    freq_hz: np.ndarray,
    amplitudes: np.ndarray,
    *,
    erb_fraction: float = ERB_FRACTION_DEFAULT,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Merge peaks by a fixed partition of the ERB-rate axis.

    bin_index = floor(erb_rate(f) / erb_fraction)

    Deterministic and order-independent: no moving centroid, so no chaining.
    Merged amplitude = sqrt(sum(A_i^2)); merged frequency = energy-weighted
    centroid within the bin. Energy conserved exactly.
    """
    frac = float(erb_fraction)
    if not np.isfinite(frac) or frac <= 0.0:
        raise ValueError("erb_fraction must be finite and > 0")

    f, a = _finite_nonnegative_pair(freq_hz, amplitudes)
    if f.size == 0:
        empty = np.zeros(0, dtype=float)
        return empty, empty, np.zeros(0, dtype=int)

    rates = erb_rate(f)
    bin_idx = np.floor(rates / frac)
    unique = np.unique(bin_idx)
    n_c = int(unique.size)
    merged_f = np.empty(n_c, dtype=float)
    merged_a = np.empty(n_c, dtype=float)
    merged_n = np.empty(n_c, dtype=int)
    for i, b in enumerate(unique):
        mask = bin_idx == b
        ff = f[mask]
        aa = a[mask]
        pwr = np.square(aa)
        tot = float(np.sum(pwr))
        merged_a[i] = math.sqrt(max(tot, 0.0))
        if tot <= ENERGY_EPS:
            merged_f[i] = float(np.mean(ff))
        else:
            merged_f[i] = float(np.dot(ff, pwr) / tot)
        merged_n[i] = int(ff.size)
    order = np.argsort(merged_f, kind="mergesort")
    return merged_f[order], merged_a[order], merged_n[order]


def merge_peaks(
    freq_hz: np.ndarray,
    amplitudes: np.ndarray,
    *,
    erb_fraction: float = ERB_FRACTION_DEFAULT,
    merge_strategy: MergeStrategy = MERGE_STRATEGY_DEFAULT,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Dispatch to the selected ERB merge strategy."""
    strategy = str(merge_strategy).strip().lower()
    if strategy == MERGE_STRATEGY_FIXED_ERB_GRID:
        return merge_peaks_fixed_erb_grid(
            freq_hz, amplitudes, erb_fraction=erb_fraction
        )
    if strategy == MERGE_STRATEGY_MOVING_CENTROID:
        return merge_peaks_within_erb(
            freq_hz, amplitudes, erb_fraction=erb_fraction
        )
    raise ValueError(
        f"unknown merge_strategy {merge_strategy!r}; "
        f"expected one of {MERGE_STRATEGIES}"
    )


def energy_shares(amplitudes: np.ndarray) -> np.ndarray:
    """p_i = A_i^2 / sum(A_j^2). Returns empty array if total energy <= ENERGY_EPS."""
    a = np.asarray(amplitudes, dtype=float).reshape(-1)
    a = a[np.isfinite(a) & (a >= 0.0)]
    if a.size == 0:
        return np.zeros(0, dtype=float)
    pwr = np.square(a)
    total = float(np.sum(pwr))
    if not np.isfinite(total) or total <= ENERGY_EPS:
        return np.zeros(0, dtype=float)
    return (pwr / total).astype(float, copy=False)


def hill_number(shares: np.ndarray, q: float) -> float:
    """D_q = (sum p_i^q)^(1/(1-q)); D_1 = exp(-sum p_i ln p_i); D_inf = 1/max(p_i).

    Handle q == 1 and q == inf as explicit limit branches, not by nudging q.
    Returns NaN on empty input.

    Hill (1973); Jost (2006).
    """
    p = np.asarray(shares, dtype=float).reshape(-1)
    p = p[np.isfinite(p) & (p > ENERGY_EPS)]
    if p.size == 0:
        return float("nan")
    total = float(np.sum(p))
    if not np.isfinite(total) or total <= ENERGY_EPS:
        return float("nan")
    p = p / total

    qv = float(q)
    if not np.isfinite(qv) and math.isinf(qv) and qv > 0.0:
        return float(1.0 / float(np.max(p)))
    if qv == 1.0:
        return float(math.exp(float(-np.sum(p * np.log(p)))))
    if qv == 0.0:
        return float(p.size)
    powered = float(np.sum(np.power(p, qv)))
    if powered <= ENERGY_EPS:
        return float("nan")
    return float(powered ** (1.0 / (1.0 - qv)))


def hill_profile(amplitudes: np.ndarray) -> dict[str, float]:
    """Return D0, D1, D2, Dinf plus evenness ratios D2/D0 and D1/D0."""
    p = energy_shares(amplitudes)
    d0 = hill_number(p, 0.0)
    d1 = hill_number(p, 1.0)
    d2 = hill_number(p, 2.0)
    d_inf = hill_number(p, math.inf)
    even_d2 = float(d2 / d0) if np.isfinite(d2) and np.isfinite(d0) and d0 > 0.0 else float("nan")
    even_d1 = float(d1 / d0) if np.isfinite(d1) and np.isfinite(d0) and d0 > 0.0 else float("nan")
    return {
        "D0": d0,
        "D1": d1,
        "D2": d2,
        "Dinf": d_inf,
        "evenness_D2_over_D0": even_d2,
        "evenness_D1_over_D0": even_d1,
    }


@dataclass(frozen=True)
class DensityCompartment:
    count_raw: int
    count_merged: int
    energy: float
    d0: float
    d1: float
    d2: float
    d_inf: float
    evenness_d2_d0: float
    mean_energy_per_effective_component: float
    status: str


def _empty_compartment(status: str, count_raw: int = 0) -> DensityCompartment:
    return DensityCompartment(
        count_raw=int(count_raw),
        count_merged=0,
        energy=float("nan") if status != "empty" else 0.0,
        d0=float("nan"),
        d1=float("nan"),
        d2=float("nan"),
        d_inf=float("nan"),
        evenness_d2_d0=float("nan"),
        mean_energy_per_effective_component=float("nan"),
        status=status,
    )


def compute_density_compartment(
    amplitudes: np.ndarray,
    frequencies_hz: np.ndarray | None = None,
    *,
    merge_within_erb: bool = True,
    erb_fraction: float = ERB_FRACTION_DEFAULT,
    merge_strategy: MergeStrategy = MERGE_STRATEGY_DEFAULT,
) -> DensityCompartment:
    """One H/I/S compartment: ERB-merge (optional) then Hill profile.

    Empty or degenerate energy → NaN Hill numbers, never a silent 0.0.
    """
    a_all = np.asarray(amplitudes, dtype=float).reshape(-1)
    raw_mask = np.isfinite(a_all) & (a_all >= 0.0)
    count_raw = int(np.count_nonzero(raw_mask))
    if count_raw == 0:
        return _empty_compartment("empty", 0)

    a_work = a_all[raw_mask]
    if merge_within_erb:
        if frequencies_hz is None:
            return _empty_compartment("missing_frequency", count_raw)
        f_all = np.asarray(frequencies_hz, dtype=float).reshape(-1)
        if f_all.size != a_all.size:
            return _empty_compartment("frequency_length_mismatch", count_raw)
        try:
            _mf, a_work, _mn = merge_peaks(
                f_all[raw_mask],
                a_work,
                erb_fraction=erb_fraction,
                merge_strategy=merge_strategy,
            )
        except ValueError as exc:
            reason = (
                "invalid_merge_strategy"
                if "merge_strategy" in str(exc)
                else "invalid_erb_fraction"
            )
            return _empty_compartment(reason, count_raw)
        if a_work.size == 0:
            return _empty_compartment("empty", count_raw)

    energy = float(np.sum(np.square(a_work)))
    if not np.isfinite(energy) or energy <= ENERGY_EPS:
        return DensityCompartment(
            count_raw=count_raw,
            count_merged=int(a_work.size),
            energy=0.0 if np.isfinite(energy) else float("nan"),
            d0=float("nan"),
            d1=float("nan"),
            d2=float("nan"),
            d_inf=float("nan"),
            evenness_d2_d0=float("nan"),
            mean_energy_per_effective_component=float("nan"),
            status="degenerate_energy",
        )

    prof = hill_profile(a_work)
    d2 = float(prof["D2"])
    lam = float(energy / d2) if np.isfinite(d2) and d2 > 0.0 else float("nan")
    return DensityCompartment(
        count_raw=count_raw,
        count_merged=int(a_work.size),
        energy=energy,
        d0=float(prof["D0"]),
        d1=float(prof["D1"]),
        d2=d2,
        d_inf=float(prof["Dinf"]),
        evenness_d2_d0=float(prof["evenness_D2_over_D0"]),
        mean_energy_per_effective_component=lam,
        status="ok",
    )


def _dq_of(comp: DensityCompartment, q: float) -> float:
    qv = float(q)
    if qv == 0.0:
        return float(comp.d0)
    if qv == 1.0:
        return float(comp.d1)
    if qv == 2.0:
        return float(comp.d2)
    if math.isinf(qv) and qv > 0.0:
        return float(comp.d_inf)
    return float("nan")


def compute_note_density(
    compartments: Mapping[str, DensityCompartment],
    *,
    q: float = 1.0,
) -> dict[str, float]:
    """Note-level Auditory Component Density.

    r_k   = energy_k / sum_j energy_j          (derived, NOT read from Excel)
    ACD   = sum_k r_k * D_q,k                  (F-057; default q=1 → D1)
    LAM   = sum_k energy_k / ACD               (F-058) magnitude per effective component
    Returns r_k, ACD, LAM, and the per-compartment profile flattened.

    Headline score uses D1. The previous D2-based value is always exported
    as ``ACD_score_D2_dominance``. Empty compartments (NaN D_q) do not
    contribute a silent 0.0 to ACD.
    """
    out: dict[str, Any] = {
        "ACD_score": float("nan"),
        "ACD_score_D2_dominance": float("nan"),
        "ACD_magnitude_per_component": float("nan"),
        "ACD_D0": float("nan"),
        "ACD_D1": float("nan"),
        "ACD_D2": float("nan"),
        "ACD_Dinf": float("nan"),
        "ACD_D0_minus_D1": float("nan"),
        "ACD_evenness_D2_over_D0": float("nan"),
        "ACD_status": "empty",
        "q": float(q),
    }
    energies: dict[str, float] = {}
    usable: dict[str, DensityCompartment] = {}
    warnings: list[str] = []

    for key, comp in compartments.items():
        name = str(key)
        out[f"status_{name}"] = comp.status
        out[f"count_raw_{name}"] = float(comp.count_raw)
        out[f"count_merged_{name}"] = float(comp.count_merged)
        out[f"energy_{name}"] = float(comp.energy)
        out[f"D0_{name}"] = float(comp.d0)
        out[f"D1_{name}"] = float(comp.d1)
        out[f"D2_{name}"] = float(comp.d2)
        out[f"Dinf_{name}"] = float(comp.d_inf)
        out[f"evenness_d2_d0_{name}"] = float(comp.evenness_d2_d0)
        out[f"lambda_{name}"] = float(comp.mean_energy_per_effective_component)
        out[f"r_{name}"] = float("nan")
        if comp.status == "ok" and np.isfinite(comp.energy) and comp.energy > ENERGY_EPS:
            dq = _dq_of(comp, q)
            if np.isfinite(dq):
                usable[name] = comp
                energies[name] = float(comp.energy)
            else:
                warnings.append(f"{name}:dq_nan")
        elif comp.status == "empty":
            out[f"r_{name}"] = 0.0
        else:
            warnings.append(f"{name}:{comp.status}")

    e_total = float(sum(energies.values()))
    if e_total <= ENERGY_EPS or not usable:
        if not usable and not warnings:
            out["ACD_status"] = "empty"
        else:
            out["ACD_status"] = (
                "no_usable_compartment:" + ",".join(warnings)
                if warnings
                else "no_usable_compartment"
            )
        return out

    acd = 0.0
    acd_d2 = 0.0
    d0_w = 0.0
    d1_w = 0.0
    d2_w = 0.0
    dinf_w = 0.0
    for name, comp in usable.items():
        rk = float(energies[name] / e_total)
        out[f"r_{name}"] = rk
        acd += rk * _dq_of(comp, q)
        acd_d2 += rk * float(comp.d2)
        d0_w += rk * float(comp.d0)
        d1_w += rk * float(comp.d1)
        d2_w += rk * float(comp.d2)
        dinf_w += rk * float(comp.d_inf)

    out["ACD_score"] = float(acd)
    out["ACD_score_D2_dominance"] = float(acd_d2)
    out["ACD_magnitude_per_component"] = (
        float(e_total / acd) if np.isfinite(acd) and acd > 0.0 else float("nan")
    )
    out["ACD_D0"] = float(d0_w)
    out["ACD_D1"] = float(d1_w)
    out["ACD_D2"] = float(d2_w)
    out["ACD_Dinf"] = float(dinf_w)
    out["ACD_D0_minus_D1"] = (
        float(d0_w - d1_w)
        if np.isfinite(d0_w) and np.isfinite(d1_w)
        else float("nan")
    )
    out["ACD_evenness_D2_over_D0"] = (
        float(d2_w / d0_w) if np.isfinite(d2_w) and np.isfinite(d0_w) and d0_w > 0.0 else float("nan")
    )
    out["ACD_status"] = "ok" if not warnings else "ok_with_unused:" + ",".join(warnings)
    out["energy_total"] = e_total
    return out


def merge_peaks_roex_overlap(*args: Any, **kwargs: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Identified next step after hard assignment — not implemented.

    Both ``moving_centroid`` and ``fixed_erb_grid`` still wander ≥ 2 %
    across production FFT tiers. The remaining artefact is hard
    assignment: a peak belongs to one cluster or one ERB-rate bin.
    A roex-overlap weighting would assign each partial smoothly by
    auditory-filter overlap rather than binning. Do not implement here.
    """
    raise NotImplementedError(
        "merge_peaks_roex_overlap is a documented next step after hard "
        "assignment; it is not implemented (ACD v1.0)."
    )


def compute_density_from_excitation_pattern(*args: Any, **kwargs: Any) -> dict[str, float]:
    """Tier B scaffold — excitation-pattern front end (not implemented).

    Intended chain (do not implement in ACD v1.0; no loudness-model dependency):

    1. roex auditory filters
    2. excitation pattern ``E(g)`` on ERB-rate sampled at 0.25 ERB over 1.75–39 ERB
    3. specific loudness ``N'(g)`` in sones/ERB (Moore, Glasberg & Baer, 1997;
       ISO 532-2:2017)
    4. Hill numbers on ``p(g) = N'(g) / L``

    Raises
    ------
    NotImplementedError
        Always. Interface is fixed so the work can be scheduled later.
    """
    raise NotImplementedError(
        "compute_density_from_excitation_pattern is a Tier B scaffold; "
        "roex / ISO 532-2 loudness is not implemented (ACD v1.0)."
    )
