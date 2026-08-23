"""
Inharmonicity coefficient estimation for quasi-harmonic spectra.

Fits B in f_n = n * f0 * sqrt(1 + B * n^2) by weighted least squares on
near-harmonic peaks within a cents window. Assignment is a global
Hungarian match followed by a monotone-frequency prune.

References
----------
- Fletcher, H. (1962). Normal vibration frequencies of a stiff piano string.
  Journal of the Acoustical Society of America, 36(1), 203–209.
- Fletcher, N. H., & Rossing, T. D. (1998). The physics of musical instruments
  (2nd ed.). Springer.

See REFERENCES.md at the repository root for canonical APA-7 entries.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

import numpy as np
from scipy.optimize import linear_sum_assignment

F0_REFIT_BAND_RATIO: float = 2.0
CENTS_WINDOW_DEFAULT: float = 80.0
ASSIGNMENT_METHOD: str = "global_monotone_v2"
ASSIGNMENT_METHOD_LEGACY: str = "legacy_greedy"
FIT_METHOD: str = "fletcher_1962_joint_f0_B_least_squares"
FIT_ITERATION_CAP: int = 4
LARGE_COST: float = 1.0e9
INHARMONICITY_B_FORMULA_VERSION: str = "2.0"

STRING_FAMILY_TOKENS: frozenset[str] = frozenset(
    {
        "cello",
        "violoncello",
        "violin",
        "viola",
        "double bass",
        "doublebass",
        "contrabass",
        "bass",
        "guitar",
        "piano",
        "harp",
        "clavier",
        "clavecin",
        "harpsichord",
        "lute",
        "theorbo",
        "banjo",
        "mandolin",
        "zither",
        "string",
        "strings",
        "arco",
        "pizz",
    }
)


def _model_freq(n: float, f0: float, b: float) -> float:
    inner = 1.0 + float(b) * float(n) * float(n)
    if not np.isfinite(inner) or inner <= 0.0:
        return float("nan")
    return float(n) * float(f0) * float(np.sqrt(inner))


def _cents_err(freq: np.ndarray, pred: float) -> np.ndarray:
    return 1200.0 * np.log2(np.maximum(freq, 1e-12) / max(float(pred), 1e-12))


def _match_orders_legacy_greedy(
    freqs: np.ndarray,
    *,
    f0_anchor: float,
    b_anchor: float,
    cap: int,
    cents_window: float,
):
    """Pre-repair greedy nearest-peak loop. Kept one version for regression."""
    chosen_freqs = []
    chosen_orders = []
    used_idx: set = set()
    for n in range(1, cap + 1):
        pred = float(n) * f0_anchor * float(np.sqrt(1.0 + max(0.0, b_anchor) * n * n))
        cents_err = _cents_err(freqs, pred)
        if cents_err.size == 0:
            continue
        best = int(np.argmin(np.abs(cents_err)))
        if best in used_idx:
            continue
        if abs(float(cents_err[best])) <= float(cents_window):
            used_idx.add(best)
            chosen_freqs.append(float(freqs[best]))
            chosen_orders.append(int(n))
    return np.asarray(chosen_freqs, dtype=float), np.asarray(chosen_orders, dtype=float)


def _longest_monotone_keep(orders: np.ndarray, freqs: np.ndarray) -> np.ndarray:
    """Indices of the longest strictly frequency-increasing subsequence in n."""
    n = int(orders.size)
    if n == 0:
        return np.asarray([], dtype=int)
    order = np.argsort(orders)
    f = freqs[order]
    length = np.ones(n, dtype=int)
    prev = np.full(n, -1, dtype=int)
    for i in range(n):
        for j in range(i):
            if f[j] < f[i] - 1e-15 and length[j] + 1 > length[i]:
                length[i] = length[j] + 1
                prev[i] = j
    end = int(np.argmax(length))
    keep_ord = []
    while end >= 0:
        keep_ord.append(end)
        end = int(prev[end])
    keep_ord.reverse()
    return order[np.asarray(keep_ord, dtype=int)]


def match_orders_detailed(
    freqs: np.ndarray,
    *,
    f0_anchor: float,
    b_anchor: float,
    cap: int,
    cents_window: float,
    nearest_band: int | None = None,
) -> dict[str, Any]:
    """Global cents assignment with a monotone-frequency prune.

    Every attempted order is either matched or listed in ``orders_missed``.
    ``nearest_band`` (first-pass B≈0) restricts peak j to orders within
    that many integers of ``round(f_j / f0)`` so unused high-n slots cannot
    wrap stretched peaks.
    """
    empty = {
        "freqs": np.asarray([], dtype=float),
        "orders": np.asarray([], dtype=float),
        "orders_matched": np.asarray([], dtype=int),
        "orders_attempted": np.asarray([], dtype=int),
        "orders_missed": np.asarray([], dtype=int),
        "assignment_method": ASSIGNMENT_METHOD,
    }
    freqs = np.asarray(freqs, dtype=float).ravel()
    freqs = freqs[np.isfinite(freqs) & (freqs > 0.0)]
    orders = np.arange(1, int(max(1, cap)) + 1, dtype=int)
    empty["orders_attempted"] = orders
    empty["orders_missed"] = orders
    if freqs.size == 0 or orders.size == 0:
        return empty

    window = float(cents_window)
    cost = np.full((orders.size, freqs.size), LARGE_COST, dtype=float)
    n_hat = np.rint(freqs / max(float(f0_anchor), 1e-12))
    for i, n in enumerate(orders):
        pred = _model_freq(float(n), f0_anchor, b_anchor)
        if not np.isfinite(pred):
            continue
        err = np.abs(_cents_err(freqs, pred))
        ok = err <= window
        if nearest_band is not None:
            ratio = freqs / max(float(f0_anchor), 1e-12)
            ok = ok & (np.abs(n_hat - float(n)) <= float(nearest_band))
            ok = ok & (np.abs(ratio - n_hat) <= 0.25)
        cost[i, ok] = err[ok]

    attempted = orders
    row_ind, col_ind = linear_sum_assignment(cost)
    assigned_n = []
    assigned_f = []
    assigned_peak = []
    for r, c in zip(row_ind, col_ind):
        if cost[r, c] >= LARGE_COST * 0.5:
            continue
        assigned_n.append(int(orders[r]))
        assigned_f.append(float(freqs[c]))
        assigned_peak.append(int(c))

    if not assigned_n:
        return empty

    n_arr = np.asarray(assigned_n, dtype=float)
    f_arr = np.asarray(assigned_f, dtype=float)
    keep = _longest_monotone_keep(n_arr, f_arr)
    kept_n = n_arr[keep]
    kept_f = f_arr[keep]
    missed = np.asarray(sorted(set(int(x) for x in attempted) - set(int(x) for x in kept_n)), dtype=int)
    return {
        "freqs": kept_f,
        "orders": kept_n,
        "orders_matched": np.asarray(kept_n, dtype=int),
        "orders_attempted": np.asarray(attempted, dtype=int),
        "orders_missed": missed,
        "assignment_method": ASSIGNMENT_METHOD,
    }


def _match_orders(
    freqs: np.ndarray,
    *,
    f0_anchor: float,
    b_anchor: float,
    cap: int,
    cents_window: float,
):
    """Assign observed peaks to harmonic orders (global monotone v2)."""
    detail = match_orders_detailed(
        freqs,
        f0_anchor=f0_anchor,
        b_anchor=b_anchor,
        cap=cap,
        cents_window=cents_window,
    )
    return detail["freqs"], detail["orders"]


def _contiguous_prefix(orders: np.ndarray, freqs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Prefer a run that includes n=1 when it has at least 3 members."""
    if orders.size == 0:
        return freqs, orders
    idx = np.argsort(orders)
    n = np.asarray(orders, dtype=int)[idx]
    f = np.asarray(freqs, dtype=float)[idx]
    runs: list[tuple[int, int]] = []
    run_start = 0
    for i in range(1, n.size + 1):
        ended = i == n.size or int(n[i]) != int(n[i - 1]) + 1
        if ended:
            runs.append((run_start, i))
            run_start = i
    for start, stop in runs:
        if 1 in set(int(x) for x in n[start:stop]) and (stop - start) >= 3:
            return f[start:stop], n[start:stop].astype(float)
    best = max(runs, key=lambda rs: (rs[1] - rs[0], -abs(int(n[rs[0]]) - 1)))
    return f[best[0] : best[1]], n[best[0] : best[1]].astype(float)


def _wls_t_c(orders: np.ndarray, freqs: np.ndarray, a_coef: float, c_coef: float) -> float:
    """Heuristic t for the n^4 coefficient under the same WLS weights."""
    n2 = orders * orders
    n4 = n2 * n2
    y = freqs * freqs
    weights = 1.0 / np.maximum(y, 1e-12)
    design = np.column_stack([n2, n4])
    resid = y - (float(a_coef) * n2 + float(c_coef) * n4)
    dof = int(orders.size - 2)
    if dof <= 0:
        return 0.0
    sigma2 = float(np.sum(weights * resid * resid) / dof)
    xtwx = (design.T * weights) @ design
    try:
        cov = sigma2 * np.linalg.inv(xtwx)
        se_c = float(np.sqrt(max(float(cov[1, 1]), 0.0)))
    except np.linalg.LinAlgError:
        return 0.0
    if not np.isfinite(se_c) or se_c <= 0.0:
        return 0.0
    return float(c_coef / se_c)


def _wls_ac(orders: np.ndarray, freqs: np.ndarray) -> tuple[float, float] | None:
    """Weighted LS for f_n^2 = a n^2 + c n^4, weights w ∝ 1/f_n^2.

    Variance of f^2 scales with f^2 · var(f). An alternative is to fit in
    cents-residual space; this implementation uses the WLS form on f^2.
    """
    n2 = orders * orders
    n4 = n2 * n2
    y = freqs * freqs
    weights = 1.0 / np.maximum(y, 1e-12)
    x = np.column_stack([n2, n4])
    xw = x * weights[:, None]
    try:
        beta, *_ = np.linalg.lstsq(xw, y * weights, rcond=None)
    except np.linalg.LinAlgError:
        return None
    a_coef = float(beta[0])
    c_coef = float(beta[1])
    if not np.isfinite(a_coef) or not np.isfinite(c_coef):
        return None
    return a_coef, c_coef


def finite_or_nan(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return parsed if np.isfinite(parsed) else float("nan")


def stretch_enabled(b: float, threshold: float) -> bool:
    """Enable stretched prediction when |B| exceeds the numerical threshold."""
    return bool(np.isfinite(b) and abs(float(b)) > float(threshold))


def apply_inharmonicity_family_scope(
    fit: Mapping[str, Any],
    *,
    instrument: str | None = None,
) -> dict[str, Any]:
    """String-family B vs phenomenological spectral stretch.

    Mapping: token match against ``STRING_FAMILY_TOKENS`` (cello, violin,
    viola, guitar, piano, harp, …). Absent metadata defaults to the
    phenomenological export and flags ``inharmonicity_model_scope``.
    """
    out = dict(fit)
    b_val = out.get("inharmonicity_coefficient_B", float("nan"))
    try:
        b_f = float(b_val)
    except (TypeError, ValueError):
        b_f = float("nan")
    token = str(instrument or "").strip().lower()
    in_family = bool(token) and any(name in token for name in STRING_FAMILY_TOKENS)
    if in_family:
        out["inharmonicity_model_scope"] = "string_family"
        out["spectral_stretch_coefficient"] = float("nan")
        return out
    out["spectral_stretch_coefficient"] = b_f
    out["inharmonicity_coefficient_B"] = float("nan")
    out["inharmonicity_model_scope"] = (
        "out_of_family" if token else "out_of_family_unspecified"
    )
    return out


def _legacy_detail(
    freqs: np.ndarray,
    *,
    f0_anchor: float,
    b_anchor: float,
    cap: int,
    cents_window: float,
) -> dict[str, Any]:
    cf, cn = _match_orders_legacy_greedy(
        freqs,
        f0_anchor=f0_anchor,
        b_anchor=b_anchor,
        cap=cap,
        cents_window=cents_window,
    )
    attempted = np.arange(1, int(max(1, cap)) + 1, dtype=int)
    missed = np.asarray(sorted(set(int(x) for x in attempted) - set(int(x) for x in cn)), dtype=int)
    return {
        "freqs": cf,
        "orders": cn,
        "orders_matched": np.asarray(cn, dtype=int),
        "orders_attempted": attempted,
        "orders_missed": missed,
        "assignment_method": ASSIGNMENT_METHOD_LEGACY,
    }


def fit_inharmonicity_coefficient(
    candidate_freqs_hz: np.ndarray,
    f0_hz: float,
    order_cap: int = 40,
    cents_window: float = CENTS_WINDOW_DEFAULT,
    assignment_method: str = ASSIGNMENT_METHOD,
) -> dict:
    """Jointly fit ``(f0, B)`` in ``f_n = n * f0 * sqrt(1 + B * n^2)``.

    ``f_n^2 = a n^2 + c n^4`` is estimated by WLS with weights
    ``w_n ∝ 1 / f_n^2``. B is signed (unclamped). The ``|t| >= 2`` screen
    is a heuristic significance screen; residuals are dominated by
    systematic peak-frequency estimation error, so no formal coverage is
    claimed.
    """
    method = FIT_METHOD
    out: Dict[str, Any] = {
        "inharmonicity_coefficient_B": float(0.0),
        "inharmonicity_fit_f0_hz": float("nan"),
        "stretched_harmonic_predicted_freqs_hz": np.asarray([], dtype=float),
        "fit_residual_std_cents": float("nan"),
        "fit_status": "insufficient_partials",
        "method": method,
        "harmonic_assignment_method": str(assignment_method or ASSIGNMENT_METHOD),
        "orders_attempted": np.asarray([], dtype=int),
        "orders_matched": np.asarray([], dtype=int),
        "orders_missed": np.asarray([], dtype=int),
        "inharmonicity_b_sign_status": "not_significant",
        "fit_converged": False,
        "spectral_stretch_coefficient": float("nan"),
        "inharmonicity_model_scope": "",
    }

    try:
        f0_seed = float(f0_hz)
    except (TypeError, ValueError):
        return out
    if not np.isfinite(f0_seed) or f0_seed <= 0.0:
        return out

    cap = int(max(1, order_cap))
    freqs = np.asarray(candidate_freqs_hz, dtype=float).ravel()
    freqs = freqs[np.isfinite(freqs) & (freqs > 0.0)]
    if freqs.size == 0:
        return out

    f0_anchor = f0_seed
    b_hat = 0.0
    f0_fit = f0_seed
    obs_f = np.asarray([], dtype=float)
    obs_n = np.asarray([], dtype=float)
    last_detail: dict[str, Any] = {}
    converged = False

    use_legacy = str(assignment_method or "").strip() == ASSIGNMENT_METHOD_LEGACY
    for iteration in range(FIT_ITERATION_CAP):
        if use_legacy:
            detail = _legacy_detail(
                freqs,
                f0_anchor=f0_anchor,
                b_anchor=b_hat,
                cap=cap,
                cents_window=float(cents_window),
            )
        else:
            detail = match_orders_detailed(
                freqs,
                f0_anchor=f0_anchor,
                b_anchor=b_hat,
                cap=cap,
                cents_window=float(cents_window),
                nearest_band=1 if abs(float(b_hat)) < 1e-12 else None,
            )
        last_detail = detail
        cf = detail["freqs"]
        cn = detail["orders"]
        if cf.size < 3:
            out["orders_attempted"] = detail.get("orders_attempted", np.asarray([], dtype=int))
            out["orders_matched"] = detail.get("orders_matched", np.asarray([], dtype=int))
            out["orders_missed"] = detail.get("orders_missed", np.asarray([], dtype=int))
            if obs_f.size < 3:
                return out
            break
        obs_f, obs_n = cf, cn
        fit_f, fit_n = _contiguous_prefix(obs_n, obs_f)
        if fit_n.size >= 3:
            obs_f, obs_n = fit_f, fit_n

        wls = _wls_ac(obs_n, obs_f)
        n2 = obs_n * obs_n
        n4 = n2 * n2
        if wls is None:
            y = (obs_f / np.maximum(obs_n * f0_seed, 1e-12)) ** 2 - 1.0
            denom = float(np.sum(n4))
            b_hat = float(np.sum(n2 * y) / denom) if denom > 0 else 0.0
            f0_fit = f0_seed
            break
        a_coef, c_coef = wls
        if a_coef <= 0.0:
            y = (obs_f / np.maximum(obs_n * f0_seed, 1e-12)) ** 2 - 1.0
            denom = float(np.sum(n4))
            b_hat = float(np.sum(n2 * y) / denom) if denom > 0 else 0.0
            f0_fit = f0_seed
            break

        f0_new = float(np.sqrt(a_coef))
        b_new = float(c_coef / a_coef)
        # Octave-each-way sanity band around the seed (not a quarter-tone).
        # Also refuse relocation when the lowest matched peak is above 2*seed
        # (the series is a higher harmonic of the seed, not a refined f0).
        if (
            not (f0_seed / F0_REFIT_BAND_RATIO <= f0_new <= f0_seed * F0_REFIT_BAND_RATIO)
            or float(np.min(obs_f)) > f0_seed * F0_REFIT_BAND_RATIO
        ):
            f0_new = f0_seed
            y = (obs_f / np.maximum(obs_n * f0_seed, 1e-12)) ** 2 - 1.0
            denom = float(np.sum(n4))
            b_new = float(np.sum(n2 * y) / denom) if denom > 0 else 0.0

        step_ok = (
            abs(f0_new - f0_anchor) <= 1e-4 * f0_anchor
            and abs(b_new - b_hat) <= 1e-9 + 1e-3 * max(abs(b_hat), 1e-12)
        )
        f0_anchor = f0_new
        f0_fit = f0_new
        b_hat = b_new
        if step_ok:
            converged = True
            break
        if iteration == FIT_ITERATION_CAP - 1:
            converged = False

    if obs_f.size < 3:
        return out

    n2 = obs_n * obs_n
    wls_final = _wls_ac(obs_n, obs_f)
    sign_status = "not_significant"
    if wls_final is not None and wls_final[0] > 0.0:
        a_coef, c_coef = wls_final
        t_c = _wls_t_c(obs_n, obs_f, a_coef, c_coef)
        if abs(t_c) < 2.0:
            b_hat = 0.0
            sign_status = "not_significant"
        elif b_hat < 0.0:
            sign_status = "negative_stretch"
        else:
            sign_status = "positive"
    out["inharmonicity_b_sign_status"] = sign_status

    pred_fit = np.array(
        [_model_freq(n, f0_fit, b_hat) for n in obs_n], dtype=float
    )
    res_cents = 1200.0 * np.log2(np.maximum(obs_f, 1e-12) / np.maximum(pred_fit, 1e-12))
    res_rms = float(np.sqrt(np.mean(res_cents * res_cents))) if res_cents.size else float("nan")
    if res_cents.size > 2:
        res_std = float(np.std(res_cents, ddof=2))
    else:
        res_std = float("nan")

    n_grid = np.arange(1, cap + 1, dtype=float)
    pred_grid = n_grid * float(f0_fit) * np.sqrt(
        np.maximum(1.0 + float(b_hat) * (n_grid * n_grid), 0.0)
    )

    out["inharmonicity_coefficient_B"] = float(b_hat)
    out["inharmonicity_fit_f0_hz"] = float(f0_fit)
    out["stretched_harmonic_predicted_freqs_hz"] = pred_grid.astype(float)
    out["fit_residual_std_cents"] = float(res_std)
    out["fit_converged"] = bool(converged)
    out["harmonic_assignment_method"] = (
        ASSIGNMENT_METHOD_LEGACY if use_legacy else ASSIGNMENT_METHOD
    )
    if last_detail:
        out["orders_attempted"] = last_detail.get("orders_attempted", np.asarray([], dtype=int))
        out["orders_matched"] = last_detail.get("orders_matched", last_detail.get("orders", np.asarray([], dtype=int)))
        out["orders_missed"] = last_detail.get("orders_missed", np.asarray([], dtype=int))
    gate = res_rms if np.isfinite(res_rms) else res_std
    if np.isfinite(gate) and gate <= max(25.0, float(cents_window) * 0.5):
        out["fit_status"] = "ok"
    else:
        out["fit_status"] = "rejected_poor_fit"
    if abs(float(b_hat)) < 1e-12:
        out["inharmonicity_b_sign_status"] = "not_significant"
    return out
