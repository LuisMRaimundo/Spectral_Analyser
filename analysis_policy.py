"""
Central analysis policy version tokens.

``proc_audio``, ``compile_metrics``, and orchestrators should import these
constants instead of duplicating ad-hoc version strings.
"""

from __future__ import annotations

from typing import Final

try:
    from density import CANONICAL_DENSITY_FORMULA_VERSION as DENSITY_FORMULA_VERSION
except ImportError:  # pragma: no cover — defensive for partial installs
    DENSITY_FORMULA_VERSION: Final[str] = "v5_apply_density_metric_adapted_v6_1"

F0_POLICY_VERSION: Final[str] = "f0_prior_constrained_harmonic_fit_v1"
HARMONIC_FREQUENCY_POLICY_VERSION: Final[str] = "subbin_interpolated_peak_frequency_v1"
NONHARMONIC_POLICY_VERSION: Final[str] = "nonharmonic_peak_candidates_not_partials_v1"
try:
    from low_frequency_policy import LOW_FREQUENCY_POLICY_VERSION as LOW_FREQUENCY_POLICY_VERSION
except ImportError:  # pragma: no cover — defensive for partial installs
    LOW_FREQUENCY_POLICY_VERSION: Final[str] = "dc_removed_adaptive_subfundamental_guard_v1"
MISSING_METRIC_POLICY_VERSION: Final[str] = "nan_not_zero_v1"
EXPORT_SCHEMA_VERSION: Final[str] = "spectral_analysis_schema_2026_05"
