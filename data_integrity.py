"""
Data Integrity and Robust Statistics Module

Phase 4 Implementation: Data Integrity Perfection

This module provides:
- Robust normalization strategies (IQR-based, percentile-based)
- Outlier detection and handling
- Data validation functions
- Global reference scaling
"""

import math
import numpy as np
import pandas as pd
from typing import Any, Optional, Tuple, Union, Dict
import logging

logger = logging.getLogger(__name__)

# Canonical missing sentinel for exported floats (not computed / undefined).
MISSING_FLOAT = float("nan")


def metric_float_or_nan(value: Any) -> float:
    """
    Convert to float while preserving missingness.

    ``None``, invalid strings, non-finite values → NaN. Real ``0.0`` stays zero.
    """
    if value is None:
        return MISSING_FLOAT
    try:
        x = float(value)
    except (TypeError, ValueError):
        return MISSING_FLOAT
    if not math.isfinite(x):
        return MISSING_FLOAT
    return x


def metric_int_or_nan(value: Any) -> Any:
    """
    Integer-like export with missingness preserved.

    ``None``, invalid, non-finite → ``pd.NA``. Otherwise ``int`` (truncates
    toward zero like ``int(float(x))``).
    """
    if value is None:
        return pd.NA
    try:
        x = float(value)
    except (TypeError, ValueError):
        return pd.NA
    if not math.isfinite(x):
        return pd.NA
    return int(x)


def metric_ratio_or_nan(numerator: Any, denominator: Any) -> float:
    """Ratio only when numerator and denominator are finite and denominator > 0."""
    n = metric_float_or_nan(numerator)
    d = metric_float_or_nan(denominator)
    if not math.isfinite(n) or not math.isfinite(d) or d <= 0.0:
        return MISSING_FLOAT
    return float(n / d)


def metric_series_or_nan(df: pd.DataFrame, column: str) -> pd.Series:
    """Numeric column if present; otherwise all-NaN series aligned to ``df``."""
    if column not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce")


# ======================================================================
# Robust Statistics (IQR-based)
# ======================================================================

def calculate_iqr_bounds(
    data: np.ndarray,
    iqr_multiplier: float = 1.5
) -> Tuple[float, float, float, float]:
    """
    Calculate IQR-based bounds for outlier detection.
    
    Phase 4: Robust Statistics Implementation
    
    Args:
        data: Input data array
        iqr_multiplier: Multiplier for IQR (default 1.5, standard for Tukey's method)
        
    Returns:
        Tuple of (Q1, Q3, lower_bound, upper_bound)
    """
    if data.size == 0:
        return (0.0, 0.0, 0.0, 0.0)
    
    data_clean = data[np.isfinite(data)]
    if data_clean.size == 0:
        return (0.0, 0.0, 0.0, 0.0)
    
    Q1 = np.percentile(data_clean, 25)
    Q3 = np.percentile(data_clean, 75)
    IQR = Q3 - Q1
    
    lower_bound = Q1 - iqr_multiplier * IQR
    upper_bound = Q3 + iqr_multiplier * IQR
    
    return (Q1, Q3, lower_bound, upper_bound)


def detect_outliers(
    data: np.ndarray,
    iqr_multiplier: float = 1.5,
    return_mask: bool = False
) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
    """
    Detect outliers using IQR method.
    
    Phase 4: Robust Statistics Implementation
    
    Args:
        data: Input data array
        iqr_multiplier: Multiplier for IQR (default 1.5)
        return_mask: If True, return boolean mask instead of outlier values
        
    Returns:
        Outlier values or (outliers, mask) if return_mask=True
    """
    if data.size == 0:
        if return_mask:
            return (np.array([]), np.array([], dtype=bool))
        return np.array([])
    
    _, _, lower_bound, upper_bound = calculate_iqr_bounds(data, iqr_multiplier)
    
    outlier_mask = (data < lower_bound) | (data > upper_bound)
    
    if return_mask:
        return (data[outlier_mask], outlier_mask)
    return data[outlier_mask]


def robust_normalize(
    data: np.ndarray,
    method: str = "iqr",
    clip_range: Optional[Tuple[float, float]] = (0.0, 1.0),
    iqr_multiplier: float = 1.5,
    percentile_low: float = 5.0,
    percentile_high: float = 95.0
) -> np.ndarray:
    """
    Robust normalization using IQR or percentile-based methods.
    
    Phase 4: Standardize Normalization Strategy
    
    Args:
        data: Input data array
        method: Normalization method ('iqr', 'percentile', 'robust_zscore')
        clip_range: Optional clipping range (None to disable)
        iqr_multiplier: Multiplier for IQR bounds
        percentile_low: Lower percentile for percentile method
        percentile_high: Upper percentile for percentile method
        
    Returns:
        Normalized data array
    """
    if data.size == 0:
        return np.array([])

    data_clean = data[np.isfinite(data)]
    if data_clean.size == 0:
        # No finite inputs: entire output is missing — do not use zeros here.
        return np.full_like(data, np.nan, dtype=float)

    if method == "iqr":
        # IQR-based normalization (robust to outliers)
        Q1, Q3, lower_bound, upper_bound = calculate_iqr_bounds(data_clean, iqr_multiplier)
        
        # Normalize to [0, 1] using IQR bounds
        if upper_bound > lower_bound:
            normalized = (data - lower_bound) / (upper_bound - lower_bound)
        else:
            # All **finite** values identical: conventionally map to 0.0 (not missing).
            normalized = np.zeros_like(data, dtype=float)
    
    elif method == "percentile":
        # Percentile-based normalization
        p_low = np.percentile(data_clean, percentile_low)
        p_high = np.percentile(data_clean, percentile_high)
        
        if p_high > p_low:
            normalized = (data - p_low) / (p_high - p_low)
        else:
            normalized = np.zeros_like(data)
    
    elif method == "robust_zscore":
        # Robust Z-score using median and MAD (Median Absolute Deviation)
        median = np.median(data_clean)
        mad = np.median(np.abs(data_clean - median))
        
        if mad > 0:
            # Normalize to approximately [-3, 3] then map to [0, 1]
            z_scores = (data - median) / (1.4826 * mad)  # 1.4826 makes MAD consistent with std for normal dist
            normalized = (z_scores + 3.0) / 6.0  # Map [-3, 3] to [0, 1]
        else:
            normalized = np.zeros_like(data)
    
    else:
        # Fallback to standard min-max
        data_min = np.min(data_clean)
        data_max = np.max(data_clean)
        if data_max > data_min:
            normalized = (data - data_min) / (data_max - data_min)
        else:
            normalized = np.zeros_like(data)
    
    # Clip if requested
    if clip_range is not None:
        normalized = np.clip(normalized, clip_range[0], clip_range[1])
    
    # Preserve NaN/Inf in original positions
    result = np.full_like(data, np.nan)
    result[np.isfinite(data)] = normalized[np.isfinite(data)]
    
    return result


# ======================================================================
# Global Reference Scaling
# ======================================================================

class GlobalReferenceScaler:
    """
    Global reference scaler for consistent normalization across datasets.
    
    Phase 4: Standardize Normalization Strategy
    
    This class maintains global statistics (from a reference dataset) to ensure
    consistent normalization across different analyses.
    """
    
    def __init__(self):
        self.reference_stats: Optional[Dict[str, float]] = None
        self.method: str = "percentile"
    
    def fit(self, reference_data: np.ndarray, method: str = "percentile") -> None:
        """
        Fit scaler to reference dataset.
        
        Args:
            reference_data: Reference dataset to compute statistics from
            method: Method for computing reference ('percentile', 'iqr', 'mean_std')
        """
        if reference_data.size == 0:
            logger.warning("Empty reference data provided to GlobalReferenceScaler")
            return
        
        data_clean = reference_data[np.isfinite(reference_data)]
        if data_clean.size == 0:
            logger.warning("No finite values in reference data")
            return
        
        self.method = method
        
        if method == "percentile":
            self.reference_stats = {
                'p5': float(np.percentile(data_clean, 5)),
                'p95': float(np.percentile(data_clean, 95)),
                'median': float(np.median(data_clean)),
                'mean': float(np.mean(data_clean))
            }
        elif method == "iqr":
            Q1, Q3, lower, upper = calculate_iqr_bounds(data_clean)
            self.reference_stats = {
                'Q1': float(Q1),
                'Q3': float(Q3),
                'lower_bound': float(lower),
                'upper_bound': float(upper),
                'median': float(np.median(data_clean))
            }
        elif method == "mean_std":
            self.reference_stats = {
                'mean': float(np.mean(data_clean)),
                'std': float(np.std(data_clean)),
                'median': float(np.median(data_clean))
            }
        else:
            # Fallback to min-max
            self.reference_stats = {
                'min': float(np.min(data_clean)),
                'max': float(np.max(data_clean)),
                'mean': float(np.mean(data_clean))
            }
    
    def transform(
        self,
        data: np.ndarray,
        clip_range: Optional[Tuple[float, float]] = (0.0, 1.0)
    ) -> np.ndarray:
        """
        Transform data using global reference statistics.
        
        Args:
            data: Data to transform
            clip_range: Optional clipping range
            
        Returns:
            Transformed data
        """
        if self.reference_stats is None:
            logger.warning("GlobalReferenceScaler not fitted. Using local normalization.")
            return robust_normalize(data, method="iqr", clip_range=clip_range)
        
        if data.size == 0:
            return np.array([])
        
        data_clean = data[np.isfinite(data)]
        if data_clean.size == 0:
            return np.zeros_like(data)
        
        if self.method == "percentile":
            p_low = self.reference_stats['p5']
            p_high = self.reference_stats['p95']
            if p_high > p_low:
                normalized = (data - p_low) / (p_high - p_low)
            else:
                normalized = np.zeros_like(data)
        
        elif self.method == "iqr":
            lower = self.reference_stats['lower_bound']
            upper = self.reference_stats['upper_bound']
            if upper > lower:
                normalized = (data - lower) / (upper - lower)
            else:
                normalized = np.zeros_like(data)
        
        elif self.method == "mean_std":
            mean = self.reference_stats['mean']
            std = self.reference_stats['std']
            if std > 0:
                # Normalize to approximately [-3, 3] then map to [0, 1]
                z_scores = (data - mean) / std
                normalized = (z_scores + 3.0) / 6.0
            else:
                normalized = np.zeros_like(data)
        
        else:
            # Min-max fallback
            data_min = self.reference_stats['min']
            data_max = self.reference_stats['max']
            if data_max > data_min:
                normalized = (data - data_min) / (data_max - data_min)
            else:
                normalized = np.zeros_like(data)
        
        # Clip if requested
        if clip_range is not None:
            normalized = np.clip(normalized, clip_range[0], clip_range[1])
        
        # Preserve NaN/Inf
        result = np.full_like(data, np.nan)
        result[np.isfinite(data)] = normalized[np.isfinite(data)]
        
        return result
    
    def fit_transform(
        self,
        data: np.ndarray,
        method: str = "percentile",
        clip_range: Optional[Tuple[float, float]] = (0.0, 1.0)
    ) -> np.ndarray:
        """Fit and transform in one step."""
        self.fit(data, method=method)
        return self.transform(data, clip_range=clip_range)


# ======================================================================
# Data Validation
# ======================================================================

def validate_metric_value(
    value: float,
    metric_name: str,
    expected_range: Optional[Tuple[float, float]] = None,
    allow_nan: bool = False,
    allow_inf: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Validate a single metric value.
    
    Phase 4: Add Data Validation
    
    Args:
        value: Value to validate
        metric_name: Name of metric (for error messages)
        expected_range: Optional (min, max) range
        allow_nan: Whether NaN is acceptable
        allow_inf: Whether Inf is acceptable
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not allow_nan and (np.isnan(value) or value is None):
        return (False, f"{metric_name} is NaN or None")
    
    if not allow_inf and np.isinf(value):
        return (False, f"{metric_name} is Inf")
    
    if expected_range is not None:
        min_val, max_val = expected_range
        if value < min_val or value > max_val:
            return (False, f"{metric_name} ({value:.6f}) outside expected range [{min_val}, {max_val}]")
    
    return (True, None)


def validate_metric_array(
    values: np.ndarray,
    metric_name: str,
    expected_range: Optional[Tuple[float, float]] = None,
    max_outlier_fraction: float = 0.1
) -> Tuple[bool, Optional[str], Dict[str, float]]:
    """
    Validate an array of metric values.
    
    Phase 4: Add Data Validation
    
    Args:
        values: Array of values to validate
        metric_name: Name of metric
        expected_range: Optional (min, max) range
        max_outlier_fraction: Maximum fraction of outliers allowed
        
    Returns:
        Tuple of (is_valid, error_message, statistics_dict)
    """
    if values.size == 0:
        return (False, f"{metric_name} array is empty", {})
    
    values_clean = values[np.isfinite(values)]
    if values_clean.size == 0:
        return (False, f"{metric_name} array has no finite values", {})
    
    stats = {
        'mean': float(np.mean(values_clean)),
        'median': float(np.median(values_clean)),
        'std': float(np.std(values_clean)),
        'min': float(np.min(values_clean)),
        'max': float(np.max(values_clean)),
        'nan_count': int(np.sum(np.isnan(values))),
        'inf_count': int(np.sum(np.isinf(values)))
    }
    
    # Check for too many outliers
    if max_outlier_fraction > 0:
        _, outlier_mask = detect_outliers(values_clean, return_mask=True)
        outlier_fraction = np.sum(outlier_mask) / values_clean.size
        if outlier_fraction > max_outlier_fraction:
            return (
                False,
                f"{metric_name} has {outlier_fraction*100:.1f}% outliers (max {max_outlier_fraction*100:.1f}%)",
                stats
            )
    
    # Check range if provided
    if expected_range is not None:
        min_val, max_val = expected_range
        out_of_range = np.sum((values_clean < min_val) | (values_clean > max_val))
        if out_of_range > 0:
            return (
                False,
                f"{metric_name} has {out_of_range} values outside range [{min_val}, {max_val}]",
                stats
            )
    
    return (True, None, stats)


def validate_audio_parameters(
    n_fft: int,
    hop_length: int,
    sr: int,
    signal_length: int
) -> Tuple[bool, Optional[str]]:
    """
    Validate audio processing parameters.
    
    Phase 4: Add Data Validation
    
    Args:
        n_fft: FFT size
        hop_length: Hop length
        sr: Sample rate
        signal_length: Signal length in samples
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate n_fft
    if n_fft < 64:
        return (False, f"n_fft ({n_fft}) too small (minimum 64)")
    if n_fft > 65536:
        return (False, f"n_fft ({n_fft}) too large (maximum 65536)")
    if (n_fft & (n_fft - 1)) != 0:
        logger.warning(f"n_fft ({n_fft}) is not a power of 2 (may be inefficient)")
    
    # Validate hop_length
    if hop_length < 1:
        return (False, f"hop_length ({hop_length}) must be positive")
    if hop_length > n_fft:
        return (False, f"hop_length ({hop_length}) > n_fft ({n_fft})")
    
    # Validate sample rate
    if sr < 8000:
        return (False, f"Sample rate ({sr}) too low (minimum 8000 Hz)")
    if sr > 192000:
        return (False, f"Sample rate ({sr}) too high (maximum 192000 Hz)")
    
    # Validate signal length
    if signal_length < n_fft:
        return (False, f"Signal length ({signal_length}) < n_fft ({n_fft})")
    
    # Check Nyquist
    nyquist = sr / 2.0
    freq_resolution = sr / n_fft
    if freq_resolution > nyquist / 100:
        logger.warning(f"Frequency resolution ({freq_resolution:.2f} Hz) may be too coarse")
    
    return (True, None)


# ======================================================================
# Log-Transform Normalization (Preserves Dynamic Range)
# ======================================================================

def normalize_log_transform(
    data: np.ndarray,
    clip_range: Optional[Tuple[float, float]] = (0.0, 1.0),
    epsilon: float = 1e-10
) -> np.ndarray:
    """
    Log-transform normalization that preserves dynamic range.
    
    Phase 4: Standardize Normalization Strategy
    
    This method preserves relative magnitude differences, ensuring that
    'fortissimo' values remain substantially higher than 'pianissimo'.
    
    Args:
        data: Input data array
        clip_range: Optional clipping range
        epsilon: Small value to avoid log(0)
        
    Returns:
        Normalized data array
    """
    orig = np.asarray(data)
    shape = orig.shape
    if orig.size == 0:
        return np.array([])

    # Folhas Metrics podem trazer object/bool/str; isfinite falha sem coerção numérica.
    flat = pd.to_numeric(pd.Series(orig.ravel()), errors="coerce").to_numpy(dtype=float)
    m = np.isfinite(flat)
    data_clean = flat[m]
    if data_clean.size == 0:
        return np.zeros_like(orig, dtype=float)

    # Apply log1p to handle wide dynamic range
    data_positive = np.maximum(data_clean, epsilon)
    log_data = np.log1p(data_positive)

    # Normalize to [0, 1]
    log_min = np.min(log_data)
    log_max = np.max(log_data)

    if log_max > log_min:
        normalized = (log_data - log_min) / (log_max - log_min)
    else:
        normalized = np.zeros_like(data_clean)

    # Clip if requested
    if clip_range is not None:
        normalized = np.clip(normalized, clip_range[0], clip_range[1])

    # Map back to original positions
    result_flat = np.full(flat.size, np.nan, dtype=float)
    result_flat[m] = normalized
    return result_flat.reshape(shape)

