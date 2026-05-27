"""
Online adaptive estimator for the H/I/S final-density profile.

Implements a Dirichlet-style pseudo-count update with a Jensen–Shannon
divergence reliability gate and a mild forgetting factor. Receives pure
observation triplets (never prior-mixed) and exposes posterior mean,
confidence, and uncertainty.

References
----------
- Lin, J. (1991). Divergence measures based on the Shannon entropy.
  IEEE Transactions on Information Theory, 37(1), 145–151.
- Gelman, A., Carlin, J. B., Stern, H. S., Dunson, D. B., Vehtari, A.,
  & Rubin, D. B. (2013). Bayesian data analysis (3rd ed.). CRC Press.

See REFERENCES.md at the repository root for canonical APA-7 entries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np


EPS = 1e-12


def _normalize_triplet(values: Tuple[float, float, float]) -> np.ndarray:
    vec = np.maximum(np.asarray(values, dtype=float), 0.0)
    s = float(np.sum(vec))
    if not np.isfinite(s) or s <= EPS:
        return np.array([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0], dtype=float)
    return vec / s


def _js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    p = np.maximum(np.asarray(p, dtype=float), EPS)
    q = np.maximum(np.asarray(q, dtype=float), EPS)
    p = p / float(np.sum(p))
    q = q / float(np.sum(q))
    m = 0.5 * (p + q)
    kl_pm = float(np.sum(p * np.log(p / m)))
    kl_qm = float(np.sum(q * np.log(q / m)))
    return max(0.0, 0.5 * (kl_pm + kl_qm))


@dataclass
class AdaptiveUpdateResult:
    profile: Tuple[float, float, float]
    confidence: float
    uncertainty: float
    reliability: float
    js_divergence: float


class AdaptiveDensityEngine:
    """
    Online learner for H/I/S final-density profile.

    - Bayesian-like concentration update (Dirichlet-style pseudo-counts).
    - Robustness gate based on Jensen-Shannon divergence.
    - Mild forgetting factor to remain responsive across long runs.
    """

    def __init__(
        self,
        *,
        initial_profile: Tuple[float, float, float] = (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
        initial_strength: float = 8.0,
        forgetting: float = 0.02,
        divergence_temperature: float = 0.18,
    ) -> None:
        self._forgetting = float(max(0.0, min(0.20, forgetting)))
        self._temp = float(max(0.05, divergence_temperature))
        p0 = _normalize_triplet(initial_profile)
        self._alpha = p0 * float(max(1.0, initial_strength))

    def profile(self) -> Tuple[float, float, float]:
        mean = self._alpha / max(float(np.sum(self._alpha)), EPS)
        return (float(mean[0]), float(mean[1]), float(mean[2]))

    def uncertainty(self) -> float:
        concentration = float(np.sum(self._alpha))
        return float(1.0 / (1.0 + concentration))

    def confidence(self) -> float:
        return float(1.0 - self.uncertainty())

    def update(
        self,
        observation: Tuple[float, float, float],
        *,
        evidence_strength: float = 1.0,
    ) -> AdaptiveUpdateResult:
        """Update from pure data ratio observation (never prior-mixed)."""
        obs = _normalize_triplet(observation)
        prior_mean = self._alpha / max(float(np.sum(self._alpha)), EPS)
        jsd = _js_divergence(obs, prior_mean)

        # Reliability gate: high divergence reduces update impact.
        reliability = float(np.exp(-jsd / self._temp))
        reliability = float(max(0.10, min(1.0, reliability)))

        # Evidence gain controls how much this note shifts the posterior.
        gain = float(max(0.25, min(4.0, evidence_strength))) * reliability

        self._alpha = (1.0 - self._forgetting) * self._alpha + gain * obs
        self._alpha = np.maximum(self._alpha, EPS)

        prof = self.profile()
        return AdaptiveUpdateResult(
            profile=prof,
            confidence=self.confidence(),
            uncertainty=self.uncertainty(),
            reliability=reliability,
            js_divergence=jsd,
        )

    def state_dict(self) -> Dict[str, float]:
        ph, pi, ps = self.profile()
        return {
            "profile_h": ph,
            "profile_i": pi,
            "profile_s": ps,
            "confidence": self.confidence(),
            "uncertainty": self.uncertainty(),
            "concentration_sum": float(np.sum(self._alpha)),
            "forgetting": self._forgetting,
            "divergence_temperature": self._temp,
        }
