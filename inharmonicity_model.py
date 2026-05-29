"""
Inharmonicity coefficient estimation for quasi-harmonic spectra.

Fits B in f_n = n * f0 * sqrt(1 + B * n^2) by least squares on near-harmonic
peaks within a cents window. Returns B, predicted stretched-harmonic
frequencies, residual standard deviation, and an explicit fit_status.

References
----------
- Fletcher, H. (1962). Normal vibration frequencies of a stiff piano string.
  Journal of the Acoustical Society of America, 36(1), 203–209.
- Fletcher, N. H., & Rossing, T. D. (1998). The physics of musical instruments
  (2nd ed.). Springer.

See REFERENCES.md at the repository root for canonical APA-7 entries.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np


def _match_orders(
    freqs: np.ndarray,
    *,
    f0_anchor: float,
    b_anchor: float,
    cap: int,
    cents_window: float,
):
    """Assign observed peaks to harmonic orders nearest the current model.

    The matching prediction is the full stiff-string model
    ``n * f0_anchor * sqrt(1 + b_anchor * n^2)`` so that, after the first
    iteration, strongly stretched high orders are matched to the correct order
    instead of drifting to ``n+1``.
    """
    chosen_freqs = []
    chosen_orders = []
    used_idx: set = set()
    for n in range(1, cap + 1):
        pred = float(n) * f0_anchor * float(np.sqrt(1.0 + max(0.0, b_anchor) * n * n))
        cents_err = 1200.0 * np.log2(np.maximum(freqs, 1e-12) / max(pred, 1e-12))
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


def fit_inharmonicity_coefficient(
    candidate_freqs_hz: np.ndarray,
    f0_hz: float,
    order_cap: int = 40,
    cents_window: float = 80.0,
) -> dict:
    """Jointly fit ``(f0, B)`` in ``f_n = n * f0 * sqrt(1 + B * n^2)``.

    The model squared is linear in two parameters::

        f_n^2 = a * n^2 + c * n^4,    with  a = f0^2,  c = f0^2 * B

    so ``(a, c)`` are obtained by ordinary least squares on the squared
    frequencies, and then ``f0 = sqrt(a)``, ``B = c / a``. This **joint**
    estimation is the key correction over a fixed-``f0`` fit: when ``f0_hz`` is a
    robust-fitted fundamental that has drifted sharp to minimise harmonic
    residuals, a fixed-``f0`` fit attributes the absorbed stretch to ``B ≈ 0``.
    Estimating ``f0`` and ``B`` together separates the two and recovers the true
    inharmonicity magnitude.

    ``f0_hz`` is used only to seed harmonic-order assignment; order assignment is
    then refined for a few iterations using the current ``(f0, B)`` estimate.

    Returns the same keys as before plus ``inharmonicity_fit_f0_hz`` (the
    jointly-fitted fundamental). ``inharmonicity_coefficient_B`` is the
    jointly-fitted ``B``.
    """
    method = "fletcher_1962_joint_f0_B_least_squares"
    out: Dict[str, Any] = {
        "inharmonicity_coefficient_B": float(0.0),
        "inharmonicity_fit_f0_hz": float("nan"),
        "stretched_harmonic_predicted_freqs_hz": np.asarray([], dtype=float),
        "fit_residual_std_cents": float("nan"),
        "fit_status": "insufficient_partials",
        "method": method,
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

    for _iteration in range(4):
        cf, cn = _match_orders(
            freqs,
            f0_anchor=f0_anchor,
            b_anchor=b_hat,
            cap=cap,
            cents_window=float(cents_window),
        )
        if cf.size < 3:
            if obs_f.size < 3:
                return out  # never had enough matched partials
            break
        obs_f, obs_n = cf, cn

        # Joint linear least squares: f_n^2 = a*n^2 + c*n^4.
        n2 = obs_n * obs_n
        n4 = n2 * n2
        g = obs_f * obs_f
        design = np.column_stack([n2, n4])
        try:
            coef, *_ = np.linalg.lstsq(design, g, rcond=None)
        except np.linalg.LinAlgError:
            return out
        a_coef = float(coef[0])
        c_coef = float(coef[1])
        if not np.isfinite(a_coef) or a_coef <= 0.0:
            # Degenerate joint fit; fall back to the fixed-seed 1-parameter fit.
            y = (obs_f / np.maximum(obs_n * f0_seed, 1e-12)) ** 2 - 1.0
            denom = float(np.sum(n4))
            b_hat = max(0.0, float(np.sum(n2 * y) / denom)) if denom > 0 else 0.0
            f0_fit = f0_seed
            break

        f0_new = float(np.sqrt(a_coef))
        b_new = max(0.0, c_coef / a_coef)

        # Significance gate on the n^4 (inharmonicity) term. The joint 2-parameter
        # fit will absorb sub-bin frequency-measurement noise into a small
        # spurious B on a perfectly harmonic signal. We keep B only when the
        # n^4 coefficient is statistically distinguishable from zero (one-sided
        # t-test, |t| >= 2 ≈ 95%), giving inharmonicity detection a noise-model
        # grounding instead of an arbitrary magnitude floor.
        if obs_n.size > 2:
            resid = g - design @ np.asarray([a_coef, c_coef], dtype=float)
            dof = int(obs_n.size - 2)
            sigma2 = float(np.sum(resid * resid) / dof) if dof > 0 else float("inf")
            try:
                xtx_inv = np.linalg.inv(design.T @ design)
                se_c = float(np.sqrt(max(sigma2 * float(xtx_inv[1, 1]), 0.0)))
            except np.linalg.LinAlgError:
                se_c = float("inf")
            t_c = float(c_coef / se_c) if np.isfinite(se_c) and se_c > 0.0 else 0.0
            if t_c < 2.0:
                b_new = 0.0  # n^4 term not significant → no detectable inharmonicity

        # Sanity guard against runaway joint fits: keep f0 within a quarter-tone
        # band-ish of the seed (joint fit should refine, not relocate, f0).
        if not (0.5 * f0_seed <= f0_new <= 2.0 * f0_seed):
            f0_new = f0_seed
            y = (obs_f / np.maximum(obs_n * f0_seed, 1e-12)) ** 2 - 1.0
            denom = float(np.sum(n4))
            b_new = max(0.0, float(np.sum(n2 * y) / denom)) if denom > 0 else 0.0

        converged = (
            abs(f0_new - f0_anchor) <= 1e-4 * f0_anchor
            and abs(b_new - b_hat) <= 1e-9 + 1e-3 * b_hat
        )
        f0_anchor = f0_new
        f0_fit = f0_new
        b_hat = b_new
        if converged:
            break

    if obs_f.size < 3:
        return out

    n2 = obs_n * obs_n
    pred_fit = obs_n * f0_fit * np.sqrt(1.0 + b_hat * n2)
    res_cents = 1200.0 * np.log2(np.maximum(obs_f, 1e-12) / np.maximum(pred_fit, 1e-12))
    res_std = float(np.std(res_cents)) if res_cents.size else float("nan")

    n_grid = np.arange(1, cap + 1, dtype=float)
    pred_grid = n_grid * f0_fit * np.sqrt(1.0 + b_hat * (n_grid**2))

    out["inharmonicity_coefficient_B"] = float(b_hat)
    out["inharmonicity_fit_f0_hz"] = float(f0_fit)
    out["stretched_harmonic_predicted_freqs_hz"] = pred_grid.astype(float)
    out["fit_residual_std_cents"] = float(res_std)
    # Conservative rejection gate: model accepted only with stable residual spread.
    if np.isfinite(res_std) and res_std <= max(25.0, float(cents_window) * 0.5):
        out["fit_status"] = "ok"
    else:
        out["fit_status"] = "rejected_poor_fit"
    return out
