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


def fit_inharmonicity_coefficient(
    candidate_freqs_hz: np.ndarray,
    f0_hz: float,
    order_cap: int = 40,
    cents_window: float = 80.0,
) -> dict:
    """
    Fit B in f_n = n * f0 * sqrt(1 + B * n^2) by least squares on near-harmonic peaks.
    """
    method = "fletcher_1962_stiff_string_least_squares"
    out: Dict[str, Any] = {
        "inharmonicity_coefficient_B": float(0.0),
        "stretched_harmonic_predicted_freqs_hz": np.asarray([], dtype=float),
        "fit_residual_std_cents": float("nan"),
        "fit_status": "insufficient_partials",
        "method": method,
    }

    try:
        f0 = float(f0_hz)
    except (TypeError, ValueError):
        return out
    if not np.isfinite(f0) or f0 <= 0.0:
        return out

    cap = int(max(1, order_cap))
    freqs = np.asarray(candidate_freqs_hz, dtype=float).ravel()
    freqs = freqs[np.isfinite(freqs) & (freqs > 0.0)]
    if freqs.size == 0:
        return out

    # Match observed peaks to harmonic indices by scanning each nominal order
    # and selecting the nearest frequency within a cents window.
    chosen_freqs = []
    chosen_orders = []
    used_idx = set()
    for n in range(1, cap + 1):
        pred = float(n) * f0
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

    if len(chosen_freqs) < 3:
        return out

    obs_f = np.asarray(chosen_freqs, dtype=float)
    obs_n = np.asarray(chosen_orders, dtype=float)
    n2 = obs_n * obs_n
    y = (obs_f / np.maximum(obs_n * f0, 1e-12)) ** 2 - 1.0
    denom = float(np.sum(n2 * n2))
    if not np.isfinite(denom) or denom <= 0.0:
        return out

    b_hat = float(np.sum(n2 * y) / denom)
    if not np.isfinite(b_hat):
        return out
    b_hat = max(0.0, b_hat)

    pred_fit = obs_n * f0 * np.sqrt(1.0 + b_hat * n2)
    res_cents = 1200.0 * np.log2(np.maximum(obs_f, 1e-12) / np.maximum(pred_fit, 1e-12))
    res_std = float(np.std(res_cents)) if res_cents.size else float("nan")

    n_grid = np.arange(1, cap + 1, dtype=float)
    pred_grid = n_grid * f0 * np.sqrt(1.0 + b_hat * (n_grid**2))

    out["inharmonicity_coefficient_B"] = float(b_hat)
    out["stretched_harmonic_predicted_freqs_hz"] = pred_grid.astype(float)
    out["fit_residual_std_cents"] = float(res_std)
    # Conservative rejection gate: model accepted only with stable residual spread.
    if np.isfinite(res_std) and res_std <= max(25.0, float(cents_window) * 0.5):
        out["fit_status"] = "ok"
    else:
        out["fit_status"] = "rejected_poor_fit"
    return out
