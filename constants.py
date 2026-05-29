"""
Constants for Signal Processing and Audio Analysis

This module centralises all magic numbers and provides documented constants
for use throughout the codebase.

See `docs/CONSTANTS_PROVENANCE.md` for the per-constant provenance registry
and `REFERENCES.md` for the canonical APA-7 bibliography.
"""

import numpy as np
from typing import Final
import logging
import warnings

from subbass_policy import SubBassPolicy

# ======================================================================
# FFT and Spectral Analysis Constants
# ======================================================================

# Default FFT parameters
DEFAULT_N_FFT: Final[int] = 4096
DEFAULT_HOP_LENGTH: Final[int] = 1024
DEFAULT_WINDOW: Final[str] = "hann"
DEFAULT_PLOT_DPI: Final[int] = 300

# Zero padding
DEFAULT_ZERO_PADDING: Final[int] = 1
MAX_ZERO_PADDING: Final[int] = 8  # For window characteristics calculation

# Window characteristics measurement
WINDOW_CHAR_FFT_PADDING: Final[int] = 8  # 8x zero-padding for accurate measurement
MAIN_LOBE_THRESHOLD_DB: Final[float] = -3.0  # -3dB points for main lobe width
SIDE_LOBE_EXCLUDE_REGION_BINS: Final[float] = 4.0  # ±2 bins around peak

# ======================================================================
# Energy Conservation Constants
# ======================================================================

# Energy conservation verification
ENERGY_CONSERVATION_TOLERANCE: Final[float] = 0.1  # 10% acceptable deviation
# Tight gate for reference STFT checks (e.g. Hann, hop=n_fft); see tests/test_stft_reference_goldens.py
ENERGY_CONSERVATION_TOLERANCE_STRICT: Final[float] = 0.02  # 2% — typical librosa Hann/hop=n_fft residual ~0.3%
ENERGY_CONSERVATION_WARNING_THRESHOLD: Final[float] = 0.05  # 5% warning threshold

# ======================================================================
# Spectral Smoothing Constants
# ======================================================================

# Spectral smoothing parameters
SMOOTHING_WINDOW_PERCENTAGE: Final[float] = 0.05  # 5% of spectrum length
SMOOTHING_MIN_WINDOW_LENGTH: Final[int] = 11  # Minimum window length (must be odd)
SMOOTHING_POLYORDER: Final[int] = 3  # Polynomial order for Savitzky-Golay
SMOOTHING_NOISE_FLOOR_PERCENTILE: Final[float] = 15.0  # 15th percentile for noise floor
SMOOTHING_NOISE_FLOOR_MULTIPLIER: Final[float] = 1.3  # 1.3x multiplier for threshold

# Optional Savitzky–Golay smoothing of |STFT| **before** peak lists / density (v6 default: off).
# For v5-style spectra (fewer spurious peaks), enable in the pipeline / GUI or set this to True.
# When off, partial-based density uses the same raw |STFT| as peak detection (no silent reshape).
DEFAULT_STFT_MAGNITUDE_SMOOTHING_ENABLED: Final[bool] = False

# Upper frequency (Hz) for aggregating sub-bass / noise-bed peak power not attributed to harmonics.
# deprecated, see SubBassPolicy.upper_bound_hz
SUBBASS_AGGREGATE_CUTOFF_HZ: Final[float] = 80.0
_SUBBASS_AGGREGATE_SHIM_WARNED = False


def deprecated_subbass_aggregate_cutoff_hz(
    *,
    f0_hz: float,
    sr_hz: float,
    n_fft: int,
) -> float:
    """deprecated, see SubBassPolicy.upper_bound_hz"""
    global _SUBBASS_AGGREGATE_SHIM_WARNED
    if not _SUBBASS_AGGREGATE_SHIM_WARNED:
        warnings.warn(
            "deprecated, see SubBassPolicy.upper_bound_hz",
            DeprecationWarning,
            stacklevel=2,
        )
        _SUBBASS_AGGREGATE_SHIM_WARNED = True
    return float(SubBassPolicy.upper_bound_hz(f0_hz=f0_hz, sr_hz=sr_hz, n_fft=n_fft))

# ======================================================================
# Psychoacoustic Constants
# ======================================================================

# Critical bands (Moore, 2012)
NUM_CRITICAL_BANDS: Final[int] = 24  # 0-23 Bark
CRITICAL_BAND_MASKING_STRONG_THRESHOLD: Final[float] = 0.5  # Bark distance for strong masking
CRITICAL_BAND_MASKING_MODERATE_THRESHOLD: Final[float] = 1.0  # Bark distance for moderate masking
CRITICAL_BAND_MASKING_WEAK_THRESHOLD: Final[float] = 2.0  # Bark distance for weak masking

# Masking model parameters (Parncutt, 1989)
MASKING_WITHIN_BAND_OFFSET_DB: Final[float] = -10.0  # Within same critical band
MASKING_ADJACENT_BAND_OFFSET_DB: Final[float] = -15.0  # Adjacent critical band
MASKING_ADJACENT_BAND_SLOPE_DB: Final[float] = -10.0  # Per Bark unit
MASKING_NEARBY_BAND_OFFSET_DB: Final[float] = -20.0  # Nearby critical bands
MASKING_NEARBY_BAND_SLOPE_DB: Final[float] = -5.0  # Per Bark unit
MASKING_FAR_BAND_OFFSET_DB: Final[float] = -30.0  # Far critical bands
MASKING_FAR_BAND_SLOPE_DB: Final[float] = -2.0  # Per Bark unit
MASKING_ABSOLUTE_THRESHOLD_DB: Final[float] = -80.0  # Minimum threshold

# Frequency limits
FREQ_MIN_HZ: Final[float] = 20.0  # Minimum audible frequency
FREQ_MAX_HZ: Final[float] = 20000.0  # Maximum audible frequency (Nyquist for 44.1kHz)
FREQ_MID_LOW_HZ: Final[float] = 1000.0  # Low-mid boundary
FREQ_MID_HIGH_HZ: Final[float] = FREQ_MAX_HZ / 4.0  # Mid-high boundary
BODY_DENSITY_MAX_HZ: Final[float] = FREQ_MAX_HZ
FULL_SPECTRUM_MAX_HZ: Final[float] = 20000.0

# Equal loudness weighting
EQUAL_LOUDNESS_LOW_WEIGHT_MIN: Final[float] = 0.5  # Minimum weight for low frequencies
EQUAL_LOUDNESS_HIGH_WEIGHT_MAX: Final[float] = 1.0  # Maximum weight for mid frequencies
EQUAL_LOUDNESS_HIGH_WEIGHT_DECAY: Final[float] = 0.5  # Decay factor for high frequencies
EQUAL_LOUDNESS_HIGH_FREQ_RANGE: Final[float] = 15000.0  # Range for high frequency decay

# ======================================================================
# Harmonic Analysis Constants
# ======================================================================

# Harmonic detection
HARMONIC_DETECTION_THRESHOLD_DB: Final[float] = -60.0  # Default threshold for harmonic detection
# ROBUSTNESS FIX: Explicit SNR threshold for consistent detection across tiers
# Harmonics must be at least this many dB above local noise floor to be detected
SNR_THRESHOLD_DB: Final[float] = 6.0  # Explicit SNR threshold above noise floor (recommended: 6-12 dB)

# Dissonance: cap harmonic partials used for pairwise models (CPU / stability)
DISSONANCE_PAIRWISE_PARTIAL_CAP: Final[int] = 80
DISSONANCE_CAP_COMPUTATION_NOTE: Final[str] = (
    "Dissonance values were computed using a capped partial list for computational stability."
)

# Density export policy (shared by compile_metrics / per-note Analysis_Metadata)
EFFECTIVE_DENSITY_COMPONENT_POLICY_DOC: Final[str] = (
    "Harmonics: per-partial power down to a relative threshold (weak harmonic power merged); "
    "inharmonic energy: default single aggregate power component (not one FFT bin per row); "
    "sub-bass: single aggregate power component below the sub-bass cutoff from spectral peaks in that band "
    "(see density.aggregate_subbass_noise_peak_power; default local-maxima on the FFT grid, not sum of every bin)."
)

INHARMONIC_MODE_FOR_EFFECTIVE_DENSITY: Final[str] = "aggregate"

SUBBASS_POLICY_FOR_EFFECTIVE_DENSITY_DOC: Final[str] = (
    "One aggregate sub-bass / noise-bed power term added to the effective-component vector; "
    "not enumerated as independent partials."
)

COUNT_SEMANTICS_NOTE_DOC: Final[str] = (
    "harmonic_order_count (alias unique_harmonic_order_count): number of detected harmonic orders n·f₀ on the "
    "harmonic list — the defensible public discrete harmonic count for Density_Metrics. "
    "harmonic_candidate_count / inharmonic_candidate_count / subbass_candidate_count classify rows on the "
    "detected-peak table (not verified local maxima on a frequency-sorted full spectrum); they are audit/debug "
    "counts on Debug_Counts. harmonic_bin_count / inharmonic_bin_count / subbass_bin_count count spectrum-table "
    "rows or bins — also Debug_Counts only. "
    "rolloff_compensated_harmonic_density_component_count is the harmonic-component population used in the "
    "rolloff-compensated sum carried by super_analysis_results.json spectral_metrics; it is not synonymous "
    "with harmonic_order_count from spectral_analysis.xlsx."
)

LEGACY_PARTIAL_COUNT_ALIASES_NOTE: Final[str] = (
    "Legacy harmonic_peak_count / *_partial_count names may still appear internally or on Debug_Counts as "
    "aliases for the same candidate-slot semantics as harmonic_candidate_count — not musical partial orders."
)

ROBUST_SALIENT_INHARMONIC_PEAK_PICKING_ENABLED: Final[bool] = False
HARMONIC_TOLERANCE_BASE: Final[float] = 0.1  # 10% base tolerance
HARMONIC_TOLERANCE_ADAPTIVE_FACTOR: Final[float] = 0.1  # Adaptive tolerance factor
HARMONIC_MAX_CHECK: Final[int] = 100  # Maximum harmonics to check (practical limit)

# Harmonic validation (cents-based slot matching; optional Validation_Metrics sheet)
HARMONIC_MATCH_TOLERANCE_CENTS: Final[float] = 35.0
# Must be safely above floor(20000 / f0) for the lowest supported notes.
# The previous value, 64, truncated low-register notes in Validation_Metrics
# and made expected harmonic counts look artificially similar across register.
# 1024 covers f0 down to ~19.5 Hz at a 20 kHz analysis ceiling.
HARMONIC_VALIDATION_MAX_HARMONICS: Final[int] = 1024
HARMONIC_VALIDATION_WARN_MEDIAN_ABS_CENTS: Final[float] = 25.0
HARMONIC_VALIDATION_WARN_MAX_ABS_CENTS: Final[float] = 80.0
HARMONIC_VALIDATION_WARN_MISSING_RATIO: Final[float] = 0.55
HARMONIC_VALIDATION_WARN_NON_HARMONIC_CANDIDATE_RATIO: Final[float] = 0.35
HARMONIC_VALIDATION_WARN_RMS_CENTS: Final[float] = 30.0

# Harmonic-order alignment status (cents + match ratio; energy share does not downgrade these)
HARMONIC_ALIGNMENT_EXCELLENT_MIN_ORDER_MATCH_RATIO: Final[float] = 0.85
HARMONIC_ALIGNMENT_EXCELLENT_MAX_WEIGHTED_MEAN_ABS_CENTS: Final[float] = 10.0
HARMONIC_ALIGNMENT_EXCELLENT_MAX_P95_ABS_CENTS: Final[float] = 18.0
HARMONIC_ALIGNMENT_GOOD_MIN_ORDER_MATCH_RATIO: Final[float] = 0.70
HARMONIC_ALIGNMENT_GOOD_MAX_WEIGHTED_MEAN_ABS_CENTS: Final[float] = 18.0
# Unweighted mean abs cents (same numeric caps as weighted; order + cents only)
HARMONIC_ALIGNMENT_EXCELLENT_MAX_MEAN_ABS_CENTS: Final[float] = 10.0
HARMONIC_ALIGNMENT_GOOD_MAX_MEAN_ABS_CENTS: Final[float] = 18.0

# Inharmonicity-aware harmonic tolerance (McAulay & Quatieri, 1986;
# Serra & Smith, 1990): per-partial tolerance floor can expand according to
# local FFT-bin spacing in cents to prevent deterministic bin-quantization
# from being mislabeled as inharmonic content.
INHARMONICITY_FIT_ORDER_CAP: Final[int] = 40
INHARMONICITY_FIT_CENTS_WINDOW: Final[float] = 80.0
INHARMONICITY_B_ENABLE_THRESHOLD: Final[float] = 1e-5
ADAPTIVE_HARMONIC_TOLERANCE_POLICY_DOC: Final[str] = (
    "tolerance_cents(n) = max(harmonic_tolerance_cents, 1200 * bin_spacing_hz / (n * f0_hz)); "
    "enables robust harmonic assignment under finite FFT-bin resolution."
)

# Fixed frequency maximum for harmonic detection (comparability)
FIXED_FREQ_MAX_HZ: Final[float] = 20000.0  # Fixed maximum frequency for summation (Option A: recommended)

# Harmonic completeness
HARMONIC_COMPLETENESS_WEIGHT_BASE: Final[float] = 1.0  # Base weight (1/n for harmonic n)
HARMONIC_COMPLETENESS_MAX_HARMONICS: Final[int] = 100  # Maximum harmonics to check (same as HARMONIC_MAX_CHECK)

# ======================================================================
# Spectral Density Constants
# ======================================================================

# Spectral sparsity
SPARSITY_THRESHOLD_RELATIVE: Final[float] = 0.01  # ~-40 dB relative threshold
SPARSITY_BANDWIDTH_FACTOR: Final[float] = 4.0  # Effective bandwidth = 4 * std

# Spectral concentration
SPECTRAL_CONCENTRATION_DEFAULT_PEAKS: Final[int] = 5  # Default number of peaks

# Perceptual spectral density
PERCEPTUAL_DENSITY_POWER_EXPONENT: Final[float] = 0.3  # |X|^0.6 weighted
PERCEPTUAL_DENSITY_OCCUPANCY_WEIGHT: Final[float] = 0.5  # Weight for occupancy
PERCEPTUAL_DENSITY_UNIFORMITY_WEIGHT: Final[float] = 0.3  # Weight for uniformity
PERCEPTUAL_DENSITY_COMPLETENESS_WEIGHT: Final[float] = 0.2  # Weight for completeness
PERCEPTUAL_DENSITY_LOG_SCALE_FACTOR: Final[float] = 3.0  # Weber-Fechner correction factor

# ======================================================================
# Temporal Analysis Constants
# ======================================================================

# Spectral flux
SPECTRAL_FLUX_POSITIVE_ONLY: Final[bool] = True  # Only count increases

# Attack time
ATTACK_TIME_THRESHOLD: Final[float] = 0.9  # 90% of maximum energy

# Spectral rolloff
SPECTRAL_ROLLOFF_PERCENTILE: Final[float] = 0.85  # 85% of energy

# ======================================================================
# Normalization Constants
# ======================================================================

# Normalization targets
NORMALIZATION_TARGET_RMS_DB: Final[float] = -20.0  # Target RMS level in dB
NORMALIZATION_MIN_AMPLITUDE: Final[float] = 1e-20  # Minimum amplitude to avoid log(0)

# Density metric normalization
MAX_ABS_DENSITY: Final[float] = 20.0  # Maximum absolute density (empirical limit for base metric)
# NOTE: Scaled density metrics (base * 10.0) can exceed 200.0 due to:
# - Frequency-dependent normalization (n^1.5 boost for higher harmonics)
# - Many harmonics (100+) contributing to sum
# - Logarithmic weight functions
# Realistic maximum for scaled density: 2000.0 (for very rich sounds)
MAX_SCALED_DENSITY: Final[float] = 2000.0  # Maximum scaled density (base * 10.0)
MAX_COMBINED_DENSITY: Final[float] = 1000.0  # Maximum combined density (logarithmic combination)
DENSITY_METRIC_WEIGHT_D: Final[float] = 0.3  # Weight for Density Metric
DENSITY_METRIC_WEIGHT_S: Final[float] = 0.2  # Weight for Spectral Density Metric
DENSITY_METRIC_WEIGHT_E: Final[float] = 0.2  # Weight for Entropy
DENSITY_METRIC_WEIGHT_C: Final[float] = 0.3  # Weight for Combined Metric
TOTAL_METRIC_SCALE: Final[float] = 10.0  # Scale factor for total metric (0-10)

# ======================================================================
# Signal Processing Constants
# ======================================================================

# Signal length limits
MAX_SIGNAL_LENGTH: Final[int] = 20_000_000  # Maximum signal length before truncation
SIGNAL_TRUNCATION_FACTOR: Final[int] = 5  # Truncation factor for long signals
LARGE_SIGNAL_THRESHOLD: Final[int] = 5_000_000  # Threshold for "large" signal

# Memory management
FFT_DOWNGRADE_FACTOR: Final[int] = 4  # Factor for FFT size downgrade on memory error
FFT_MIN_SIZE: Final[int] = 1024  # Minimum FFT size after downgrade

# ======================================================================
# Numerical Stability Constants
# ======================================================================

# Small values to avoid division by zero or log(0)
EPSILON: Final[float] = 1e-12  # General epsilon
EPSILON_POWER: Final[float] = 1e-12  # For power calculations
EPSILON_AMPLITUDE: Final[float] = 1e-20  # For amplitude calculations
EPSILON_FREQUENCY: Final[float] = 1e-6  # For frequency calculations (1 mHz)

# Clipping ranges
CLIP_MIN: Final[float] = 0.0  # Minimum value for clipping
CLIP_MAX: Final[float] = 1.0  # Maximum value for clipping (normalized)

# ======================================================================
# Window Function Constants
# ======================================================================

# Default window parameters
KAISER_DEFAULT_BETA: Final[float] = 6.5  # Default Kaiser window beta
GAUSSIAN_DEFAULT_STD_FACTOR: Final[float] = 8.0  # n_fft / 8.0 for Gaussian std

# ======================================================================
# Bark Scale Constants
# ======================================================================

# Bark scale conversion (Zwicker & Fastl, 1999)
BARK_COEFFICIENT_1: Final[float] = 13.0
BARK_COEFFICIENT_2: Final[float] = 0.00076
BARK_COEFFICIENT_3: Final[float] = 3.5
BARK_COEFFICIENT_4: Final[float] = 7500.0

# Approximate Bark-to-Hz conversion boundaries
BARK_TO_HZ_LOW_THRESHOLD: Final[float] = 2.0  # Bark threshold for low frequency approximation
BARK_TO_HZ_MID_THRESHOLD: Final[float] = 10.0  # Bark threshold for mid frequency approximation
BARK_TO_HZ_LOW_FREQ_BASE: Final[float] = 200.0  # Base frequency for mid-range
BARK_TO_HZ_LOW_FREQ_SLOPE: Final[float] = 100.0  # Hz per Bark for mid-range
BARK_TO_HZ_HIGH_FREQ_BASE: Final[float] = 1000.0  # Base frequency for high-range
BARK_TO_HZ_HIGH_EXP_FACTOR: Final[float] = 3.0  # Exponential factor for high-range

# ======================================================================
# Validation Constants
# ======================================================================

# Tolerance values
TOLERANCE_DEFAULT: Final[float] = 5.0  # Default tolerance in Hz
TOLERANCE_MIN: Final[float] = 0.0  # Minimum tolerance
TOLERANCE_MAX: Final[float] = 100.0  # Maximum tolerance

# Frequency validation
FREQ_VALIDATION_MIN: Final[float] = 0.0  # Minimum valid frequency
FREQ_VALIDATION_MAX: Final[float] = 20000.0  # Maximum valid frequency

# Amplitude validation
AMP_VALIDATION_MIN_DB: Final[float] = -120.0  # Minimum valid amplitude (dB)
AMP_VALIDATION_MAX_DB: Final[float] = 20.0  # Maximum valid amplitude (dB)

# ======================================================================
# Publication / Zenodo export policy
# ======================================================================

# When True, exported Excel/JSON/CSV/text metadata must not contain local absolute paths
# (see ``metadata_sanitizer``). Runtime logs may still print full paths for debugging.
REDACT_LOCAL_PATHS_FOR_PUBLICATION: Final[bool] = True

# When True, publication/research Excel exports omit private paths, empty diagnostic-only
# columns, row-wise provenance noise, and internal orchestrator labels (see ``metadata_sanitizer``).
PUBLICATION_CLEAN_EXPORT: Final[bool] = True


# ======================================================================
# Phase 7 register-invariant strength formula
# ======================================================================

# Phase 7 (2026-05-26): default = 1.0. Three equal weights enforce
# occupancy-ratio symmetry across the H/I/S strength terms. Changing
# these weights tilts the H/I/S balance away from neutral occupancy
# proportionality and should be done deliberately and documented.
STRENGTH_OCCUPANCY_WEIGHT_HARMONIC: Final[float] = 1.0

# Phase 7 (2026-05-26): default = 1.0. Three equal weights enforce
# occupancy-ratio symmetry across the H/I/S strength terms. Changing
# these weights tilts the H/I/S balance away from neutral occupancy
# proportionality and should be done deliberately and documented.
STRENGTH_OCCUPANCY_WEIGHT_INHARMONIC: Final[float] = 1.0

# Phase 7 (2026-05-26): default = 1.0. Three equal weights enforce
# occupancy-ratio symmetry across the H/I/S strength terms. Changing
# these weights tilts the H/I/S balance away from neutral occupancy
# proportionality and should be done deliberately and documented.
STRENGTH_OCCUPANCY_WEIGHT_SUBBASS: Final[float] = 1.0


# ======================================================================
# Phase 6: provenance warning for unsourced numeric constants
# ======================================================================

_PROVENANCE_SOURCED_CONSTANTS: Final[frozenset[str]] = frozenset(
    {
        "AMP_VALIDATION_MAX_DB",
        "AMP_VALIDATION_MIN_DB",
        "ATTACK_TIME_THRESHOLD",
        "BARK_COEFFICIENT_1",
        "BARK_COEFFICIENT_2",
        "BARK_COEFFICIENT_3",
        "BARK_COEFFICIENT_4",
        "BARK_TO_HZ_HIGH_EXP_FACTOR",
        "BARK_TO_HZ_HIGH_FREQ_BASE",
        "BARK_TO_HZ_LOW_FREQ_BASE",
        "BARK_TO_HZ_LOW_FREQ_SLOPE",
        "BARK_TO_HZ_LOW_THRESHOLD",
        "BARK_TO_HZ_MID_THRESHOLD",
        "CLIP_MAX",
        "CLIP_MIN",
        "CRITICAL_BAND_MASKING_MODERATE_THRESHOLD",
        "CRITICAL_BAND_MASKING_STRONG_THRESHOLD",
        "CRITICAL_BAND_MASKING_WEAK_THRESHOLD",
        "DEFAULT_HOP_LENGTH",
        "DEFAULT_N_FFT",
        "DEFAULT_PLOT_DPI",
        "DEFAULT_ZERO_PADDING",
        "DISSONANCE_PAIRWISE_PARTIAL_CAP",
        "EPSILON",
        "EPSILON_AMPLITUDE",
        "EPSILON_FREQUENCY",
        "EPSILON_POWER",
        "EQUAL_LOUDNESS_HIGH_WEIGHT_MAX",
        "FFT_MIN_SIZE",
        "FIXED_FREQ_MAX_HZ",
        "FREQ_MAX_HZ",
        "FREQ_MID_HIGH_HZ",
        "FREQ_MID_LOW_HZ",
        "FREQ_MIN_HZ",
        "FREQ_VALIDATION_MAX",
        "FREQ_VALIDATION_MIN",
        "GAUSSIAN_DEFAULT_STD_FACTOR",
        "HARMONIC_COMPLETENESS_MAX_HARMONICS",
        "HARMONIC_COMPLETENESS_WEIGHT_BASE",
        "HARMONIC_DETECTION_THRESHOLD_DB",
        "HARMONIC_MATCH_TOLERANCE_CENTS",
        "HARMONIC_MAX_CHECK",
        "HARMONIC_TOLERANCE_ADAPTIVE_FACTOR",
        "HARMONIC_TOLERANCE_BASE",
        "HARMONIC_VALIDATION_MAX_HARMONICS",
        "INHARMONICITY_FIT_CENTS_WINDOW",
        "INHARMONICITY_FIT_ORDER_CAP",
        "KAISER_DEFAULT_BETA",
        "MAIN_LOBE_THRESHOLD_DB",
        "MASKING_ABSOLUTE_THRESHOLD_DB",
        "MAX_ZERO_PADDING",
        "NORMALIZATION_MIN_AMPLITUDE",
        "NORMALIZATION_TARGET_RMS_DB",
        "NUM_CRITICAL_BANDS",
        "SMOOTHING_MIN_WINDOW_LENGTH",
        "SMOOTHING_POLYORDER",
        "SNR_THRESHOLD_DB",
        "SPARSITY_BANDWIDTH_FACTOR",
        "SPECTRAL_CONCENTRATION_DEFAULT_PEAKS",
        "SPECTRAL_ROLLOFF_PERCENTILE",
        "STRENGTH_OCCUPANCY_WEIGHT_HARMONIC",
        "STRENGTH_OCCUPANCY_WEIGHT_INHARMONIC",
        "STRENGTH_OCCUPANCY_WEIGHT_SUBBASS",
        "SUBBASS_AGGREGATE_CUTOFF_HZ",
        "TOLERANCE_MIN",
        "TOTAL_METRIC_SCALE",
        "WINDOW_CHAR_FFT_PADDING",
    }
)

_UNSOURCED_PROVENANCE_WARNED = False
_LOGGER = logging.getLogger(__name__)


def _iter_numeric_constant_names() -> list[str]:
    names: list[str] = []
    for key, value in globals().items():
        if not key.isupper():
            continue
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float, np.integer, np.floating)):
            names.append(key)
    return sorted(set(names))


def _warn_unsourced_constants_once() -> None:
    global _UNSOURCED_PROVENANCE_WARNED
    if _UNSOURCED_PROVENANCE_WARNED:
        return
    unsourced = [n for n in _iter_numeric_constant_names() if n not in _PROVENANCE_SOURCED_CONSTANTS]
    if unsourced:
        preview = ", ".join(unsourced[:12])
        if len(unsourced) > 12:
            preview += ", ..."
        _LOGGER.info(
            "Constants without primary-source provenance (%d, classified as internal_default in docs/CONSTANTS_PROVENANCE.md): %s",
            len(unsourced),
            preview,
        )
    _UNSOURCED_PROVENANCE_WARNED = True


_warn_unsourced_constants_once()


# ======================================================================
# Documentation
# ======================================================================

"""
Constants Usage Guide:

1. Import constants:
   from constants import DEFAULT_N_FFT, ENERGY_CONSERVATION_TOLERANCE

2. Replace magic numbers:
   # Before: n_fft = 4096
   # After: n_fft = DEFAULT_N_FFT

3. Use in calculations:
   # Before: threshold = 0.9 * max_energy
   # After: threshold = ATTACK_TIME_THRESHOLD * max_energy

4. Document rationale:
   Each constant includes a comment explaining its purpose and source.
"""

