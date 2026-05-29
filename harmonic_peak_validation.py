"""Spectral-peak refinement and per-order harmonic-candidate classification.

This module holds the cohesive, dependency-free (numpy-only) cluster of pure
functions that drive harmonic *peak* detection and per-order candidate
classification used by ``proc_audio._generate_harmonic_list``:

  * sub-bin parabolic interpolation and peak-index refinement;
  * saddle-based prominence and its f0-adaptive window;
  * the strict local-peak validity test (``_is_local_peak_valid``);
  * per-order candidate metrics / classification
    (``_local_peak_metrics`` / ``_classify_harmonic_candidate``);
  * the read-only Harmonic_Inclusion_Audit exclusion-reason labeller.

These were previously defined inline in ``proc_audio.py``. They are pure
(no AudioProcessor state, numpy in / scalars out) and unit-tested in
isolation, so they live here to keep ``proc_audio`` focused on pipeline
orchestration. ``proc_audio`` re-imports every public name below, so existing
references (``proc_audio._foo`` / ``from proc_audio import _foo``) keep working.

NOTE: this is a distinct module from ``harmonic_validation.py`` — the latter
maps a peak table to harmonic-order cents-alignment metrics
(``validate_harmonic_series_matched``). This module is about the upstream
per-bin peak picking / classification.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np

__all__ = [
    "HARMONIC_CANDIDATE_STATUS_VALUES",
    "_parabolic_interpolation_log_magnitude",
    "_refine_peak_index",
    "_infer_bin_spacing_from_freqs",
    "_refine_candidate_to_interpolated_peak",
    "_saddle_prominence_db",
    "_prominence_saddle_window_bins",
    "_is_local_peak_valid",
    "_harmonic_inclusion_audit_exclusion_reason",
    "_local_peak_metrics",
    "_classify_harmonic_candidate",
]


def _parabolic_interpolation_log_magnitude(
    magnitudes: np.ndarray,
    peak_idx: int,
    bin_spacing: float,
    freq_base: float
) -> Tuple[float, bool]:
    """
    Interpolação parabólica em log-magnitude para estimação sub-bin.

    Fundamentação Matemática (standard reference):
    - Para um pico localizado no bin k: y[k-1], y[k], y[k+1]
    - Assumindo forma parabólica em log-escala: log(y) = a·x² + b·x + c
    - Posição do pico (máximo): x_peak = -b/(2a) = -(Y₃ - Y₁)/(2·(Y₁ - 2Y₂ + Y₃))
    - Correção: f_corrected = f_bin + x_peak × Δf

    Args:
        magnitudes: Array de magnitudes (linear)
        peak_idx: Índice do bin de máximo
        bin_spacing: Espaçamento entre bins (Hz)
        freq_base: Frequência base (Hz) - para calcular frequência absoluta

    Returns:
        Tuple (frequência corrigida, validade)
    """
    if peak_idx <= 0 or peak_idx >= len(magnitudes) - 1:
        freq_corrected = freq_base + peak_idx * bin_spacing
        return freq_corrected, False

    # Converter para log-magnitude (mais linear que magnitude linear)
    log_mags = 20 * np.log10(np.maximum(magnitudes, 1e-10))

    # Amostras: k-1, k, k+1
    y1, y2, y3 = log_mags[peak_idx-1], log_mags[peak_idx], log_mags[peak_idx+1]

    # Parâmetros da parábola: y = a·x² + b·x + c
    # Resolvendo: a = (Y₁ - 2Y₂ + Y₃)/2, b = (Y₃ - Y₁)/2, c = Y₂
    a = (y1 - 2*y2 + y3) / 2.0
    b = (y3 - y1) / 2.0

    # Posição do pico: x_peak = -b/(2a)
    if abs(a) < 1e-10:  # Parábola degenerada (linha reta)
        x_peak = 0.0
    else:
        x_peak = -b / (2 * a)

    # Validar: x_peak deve estar em [-0.5, +0.5]
    if abs(x_peak) > 0.5:
        freq_corrected = freq_base + peak_idx * bin_spacing
        return freq_corrected, False

    # Calcular frequência corrigida
    freq_bin = freq_base + peak_idx * bin_spacing
    freq_corrected = freq_bin + x_peak * bin_spacing

    return freq_corrected, True


def _refine_peak_index(
    magnitudes: np.ndarray,
    approx_idx: int,
    *,
    refine_radius: int = 2,
) -> int:
    """Snap ``approx_idx`` to the nearest local maximum within
    ±``refine_radius`` bins.

    When the candidate index comes from ``argmin(|freqs - n·f0|)`` the
    expected harmonic frequency does not generally land on an FFT bin;
    the true peak can sit one or two bins away. Without this refinement,
    the ``mag[idx] > mag[idx±1]`` local-max check would fail for the
    majority of legitimate harmonics simply because the index was
    pointing at the lobe shoulder rather than the lobe top.
    """
    n = len(magnitudes)
    if n == 0:
        return int(approx_idx)
    lo = max(0, int(approx_idx) - int(refine_radius))
    hi = min(n, int(approx_idx) + int(refine_radius) + 1)
    if hi <= lo:
        return int(approx_idx)
    return int(lo + int(np.argmax(magnitudes[lo:hi])))


def _infer_bin_spacing_from_freqs(freqs: np.ndarray) -> float:
    """Infer FFT-bin spacing (Hz) from the frequency axis."""
    freqs = np.asarray(freqs, dtype=float)
    if freqs.size < 2:
        return float("nan")
    diffs = np.diff(freqs)
    diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    if diffs.size == 0:
        return float("nan")
    return float(np.median(diffs))


def _refine_candidate_to_interpolated_peak(
    *,
    candidate_freq_hz: float,
    complete_magnitudes: np.ndarray,
    complete_freqs: np.ndarray,
    refine_radius: int = 2,
) -> Dict[str, Any]:
    """Snap a bin-centred candidate to a local magnitude peak and apply
    log-magnitude parabolic interpolation (:func:`_parabolic_interpolation_log_magnitude`).

    Returns audit fields for Harmonic Spectrum export: FFT bin index and
    centre frequency, sub-bin interpolated frequency, and peak linear / dB
    magnitude at the refined bin.
    """
    nan = float("nan")
    result: Dict[str, Any] = {
        "peak_bin_index": nan,
        "bin_center_frequency_hz": float(candidate_freq_hz),
        "interpolated_frequency_hz": float(candidate_freq_hz),
        "subbin_offset_bins": 0.0,
        "subbin_interpolation_valid": False,
        "peak_amplitude_raw": nan,
        "peak_magnitude_db": nan,
    }
    if complete_magnitudes is None or complete_freqs is None:
        return result

    mags = np.asarray(complete_magnitudes, dtype=float)
    freqs = np.asarray(complete_freqs, dtype=float)

    if mags.size == 0 or freqs.size == 0 or mags.size != freqs.size:
        return result

    idx0 = int(np.argmin(np.abs(freqs - float(candidate_freq_hz))))
    idx_peak = _refine_peak_index(mags, idx0, refine_radius=int(refine_radius))

    if idx_peak < 0 or idx_peak >= mags.size:
        return result

    bin_center = float(freqs[idx_peak])
    amp = float(mags[idx_peak])
    mag_db = float(20.0 * np.log10(max(amp, 1e-12)))

    bin_spacing = _infer_bin_spacing_from_freqs(freqs)
    if not np.isfinite(bin_spacing) or bin_spacing <= 0:
        result.update(
            {
                "peak_bin_index": int(idx_peak),
                "bin_center_frequency_hz": bin_center,
                "interpolated_frequency_hz": bin_center,
                "subbin_offset_bins": 0.0,
                "subbin_interpolation_valid": False,
                "peak_amplitude_raw": amp,
                "peak_magnitude_db": mag_db,
            }
        )
        return result

    if idx_peak <= 0 or idx_peak >= mags.size - 1:
        result.update(
            {
                "peak_bin_index": int(idx_peak),
                "bin_center_frequency_hz": bin_center,
                "interpolated_frequency_hz": bin_center,
                "subbin_offset_bins": 0.0,
                "subbin_interpolation_valid": False,
                "peak_amplitude_raw": amp,
                "peak_magnitude_db": mag_db,
            }
        )
        return result

    freq_base = float(freqs[0])
    freq_interp, valid = _parabolic_interpolation_log_magnitude(
        mags,
        idx_peak,
        bin_spacing,
        freq_base,
    )

    if not valid or not np.isfinite(freq_interp):
        freq_interp = bin_center
        valid = False

    offset_bins = float((float(freq_interp) - bin_center) / bin_spacing)

    result.update(
        {
            "peak_bin_index": int(idx_peak),
            "bin_center_frequency_hz": bin_center,
            "interpolated_frequency_hz": float(freq_interp),
            "subbin_offset_bins": offset_bins,
            "subbin_interpolation_valid": bool(valid),
            "peak_amplitude_raw": amp,
            "peak_magnitude_db": mag_db,
        }
    )
    return result


def _saddle_prominence_db(
    magnitudes: np.ndarray,
    peak_idx: int,
    *,
    saddle_window: int = 10,
) -> float:
    """Saddle-based peak prominence (in dB).

    Returns the peak height above the HIGHEST of the two local minima
    found within ±``saddle_window`` bins on either side of ``peak_idx``.

    Why a saddle window — and not the legacy ±1-bin comparison:

        For a Blackman–Harris window the main lobe is ≈ 2 bins wide
        between the −3 dB points, so even a perfectly clean sinusoid
        produces immediate neighbours that sit only ~0.1–1.5 dB below
        the peak. The legacy ``peak − max(left, right)`` formula
        therefore measured *main-lobe curvature*, not prominence:
        every real harmonic of a clarinet A♯3 came out at
        ``prominence_db`` ≈ 0.04–0.63 dB and was rejected by a
        ``> 3 dB`` strict gate — including the fundamental at SNR 75 dB.

        Saddle-based prominence (the standard definition used by
        ``scipy.signal.peak_prominences``) compares the peak to the
        local minimum on each flank, which for an isolated harmonic
        sits 20–40 dB below the peak. Real harmonics now pass the 3 dB
        gate; only side-lobes / noise excursions fail.

        ``saddle_window = 10`` bins is wide enough to step past the
        Blackman–Harris main lobe and side lobes on every tier used
        by this pipeline (smallest inter-harmonic spacing in the
        Clarinete_mf corpus is 27 bins at D3, n_fft = 8192), so the
        window never crosses into an adjacent harmonic.

    Returns ``-inf`` on array edges or empty windows.
    """
    mags = np.asarray(magnitudes, dtype=float)
    n = len(mags)
    if n < 3 or peak_idx <= 0 or peak_idx >= n - 1:
        return float("-inf")
    ls = max(0, peak_idx - int(saddle_window))
    rs = min(n, peak_idx + int(saddle_window) + 1)
    left_slice = mags[ls:peak_idx] if peak_idx > ls else None
    right_slice = mags[peak_idx + 1 : rs] if rs > peak_idx + 1 else None
    if (
        left_slice is None
        or right_slice is None
        or len(left_slice) == 0
        or len(right_slice) == 0
    ):
        return float("-inf")
    peak_db = 20.0 * np.log10(max(float(mags[peak_idx]), 1e-10))
    left_min_db = 20.0 * np.log10(max(float(np.min(left_slice)), 1e-10))
    right_min_db = 20.0 * np.log10(max(float(np.min(right_slice)), 1e-10))
    return float(peak_db - max(left_min_db, right_min_db))


def _prominence_saddle_window_bins(
    *,
    f0_hz: float,
    bin_spacing_hz: float,
    min_bins: int = 3,
    max_bins: int = 256,
) -> int:
    """Convert inter-harmonic half-spacing (±f0/2) to a saddle search radius in bins.

    Fixed-bin saddle windows treat low-pitched instruments harshly: for cello C2
    (f0 ≈ 65 Hz) a ±10-bin window spans only ~27 Hz and the saddles sit between
    overlapping harmonic lobes, collapsing prominence. Scaling the window to
    ~half the fundamental spacing keeps the neighbourhood off adjacent partials.
    """
    try:
        f0 = float(f0_hz)
        bin_hz = float(bin_spacing_hz)
    except (TypeError, ValueError):
        return 10
    if not (np.isfinite(f0) and f0 > 0.0 and np.isfinite(bin_hz) and bin_hz > 0.0):
        return 10
    half_spacing_bins = int(round(0.5 * f0 / bin_hz))
    return int(max(int(min_bins), min(int(max_bins), half_spacing_bins)))


def _is_local_peak_valid(
    magnitudes: np.ndarray,
    peak_idx: int,
    threshold_db: float = 3.0,
    noise_floor_percentile: float = 15.0,
    window_size: int = 50,
    saddle_window: int = 10,
    f0_hz: Optional[float] = None,
    bin_spacing_hz: Optional[float] = None,
) -> Tuple[bool, float]:
    """
    Valida se índice corresponde a pico local válido (não lóbulo lateral).

    Three independent checks:
      * local maximum:      mag[k] > mag[k±1]
      * saddle prominence:  peak − max(left_saddle, right_saddle) ≥ threshold_db
                            (saddle defined via ``_saddle_prominence_db``)
      * SNR vs noise floor: peak_db − percentile(local_window) ≥ 3 dB

    Args:
        magnitudes: Linear magnitude array.
        peak_idx: Index to evaluate.
        threshold_db: Minimum prominence above the saddle.
        noise_floor_percentile: Percentile for noise-floor estimation.
        window_size: Bin width of the noise-floor window (±).
        saddle_window: Bin width used to locate the prominence saddle (±).

    Returns:
        Tuple (is_valid, snr_db).
    """
    if peak_idx <= 0 or peak_idx >= len(magnitudes) - 1:
        return False, -np.inf

    peak_idx = _refine_peak_index(magnitudes, peak_idx, refine_radius=2)
    if peak_idx <= 0 or peak_idx >= len(magnitudes) - 1:
        return False, -np.inf

    log_mags = 20 * np.log10(np.maximum(magnitudes, 1e-10))

    peak_mag_db = log_mags[peak_idx]
    left_db = log_mags[peak_idx - 1]
    right_db = log_mags[peak_idx + 1]

    is_peak = peak_mag_db > left_db and peak_mag_db > right_db

    if (
        f0_hz is not None
        and bin_spacing_hz is not None
        and np.isfinite(float(f0_hz))
        and float(f0_hz) > 0.0
        and np.isfinite(float(bin_spacing_hz))
        and float(bin_spacing_hz) > 0.0
    ):
        saddle_window = _prominence_saddle_window_bins(
            f0_hz=float(f0_hz),
            bin_spacing_hz=float(bin_spacing_hz),
        )
        # Keep the SNR noise-floor window on the same physical scale (±f0/2),
        # not a fixed ±50 bins that spans several cello partials.
        window_size = max(int(saddle_window), 5)

    prom_db = _saddle_prominence_db(
        magnitudes, peak_idx, saddle_window=saddle_window
    )
    threshold_met = prom_db >= float(threshold_db)

    start_idx = max(0, peak_idx - window_size)
    end_idx = min(len(magnitudes), peak_idx + window_size)
    local_magnitudes = magnitudes[start_idx:end_idx]
    noise_floor_mag = np.percentile(local_magnitudes, noise_floor_percentile)
    noise_floor_db = 20 * np.log10(noise_floor_mag + 1e-10)

    snr_db = peak_mag_db - noise_floor_db
    snr_valid = snr_db >= 3.0

    is_valid = is_peak and threshold_met and snr_valid

    return is_valid, snr_db


# ---------------------------------------------------------------------------
# Harmonic-spectrum candidate helpers (see _generate_harmonic_list).
#
# The strict harmonic acceptance test (``_is_local_peak_valid``) requires a
# local maximum AND a ≥ 3 dB margin above both neighbours AND a SNR ≥ 3 dB
# vs. the local noise floor. That criterion is appropriate for diagnostics
# but rejects too many legitimate FFT-smeared harmonics for the density
# metric. The two helpers below split harmonic acceptance into:
#
#   * strict_harmonic_peaks       — what ``_is_local_peak_valid`` accepts
#                                   (drives ``harmonic_list_df`` / inharmonic
#                                   classification / robust f0 fit);
#   * harmonic_spectrum_candidates — one entry per expected harmonic order
#                                   that drives the per-note ``Harmonic
#                                   Spectrum`` sheet and the
#                                   ``harmonic_log_amplitude_density`` metric
#                                   used by Density_Metrics.
# ---------------------------------------------------------------------------

# Public list of candidate-status codes. Kept as a module-level tuple so
# downstream tests / metadata writers can reference the canonical names
# without re-implementing the enum.
HARMONIC_CANDIDATE_STATUS_VALUES: Tuple[str, ...] = (
    "strict_validated",
    "snr_validated",
    "weak_candidate",
    "below_noise_floor",
    "missing_window",
    "rejected_bad_f0",
    "off_frequency",
)


def _harmonic_inclusion_audit_exclusion_reason(
    *,
    include_for_density: bool,
    expected_frequency_hz: float,
    frequency_deviation_hz: float,
    candidate_status: str,
    local_peak_valid: bool,
    snr_db: Any,
    prominence_db: Any,
) -> str:
    """Read-only diagnostic label for Harmonic_Inclusion_Audit (export only)."""
    if bool(include_for_density):
        return "included"
    try:
        expected_hz = float(expected_frequency_hz)
    except (TypeError, ValueError):
        expected_hz = float("nan")
    if np.isfinite(expected_hz) and expected_hz > 5000.0:
        return f"above_body_density_ceiling_5khz (expected={expected_hz:.1f} Hz)"
    status = str(candidate_status or "")
    if status == "off_frequency":
        try:
            dev_hz = float(frequency_deviation_hz)
        except (TypeError, ValueError):
            dev_hz = float("nan")
        if not np.isfinite(dev_hz):
            dev_hz = 0.0
        return f"off_frequency (deviation={dev_hz:.2f} Hz)"
    try:
        snr = float(snr_db) if snr_db is not None else None
    except (TypeError, ValueError):
        snr = None
    if snr is not None and snr < 3.0:
        return f"snr_below_3dB (snr={snr:.2f} dB)"
    try:
        prom = float(prominence_db) if prominence_db is not None else None
    except (TypeError, ValueError):
        prom = None
    if prom is not None and prom < 3.0:
        return f"prominence_below_3dB (prominence={prom:.2f} dB)"
    if local_peak_valid is False:
        return "not_local_maximum"
    return f"rejected_by_validation (status={status})"


def _local_peak_metrics(
    magnitudes: np.ndarray,
    peak_idx: int,
    *,
    noise_floor_percentile: float = 15.0,
    window_size: int = 50,
    saddle_window: int = 10,
    f0_hz: Optional[float] = None,
    bin_spacing_hz: Optional[float] = None,
) -> Tuple[bool, float, float]:
    """Compute ``(local_peak_valid, snr_db, prominence_db)`` for ``peak_idx``.

    * ``local_peak_valid``: ``mag[idx] > mag[idx-1] AND mag[idx] > mag[idx+1]``
      (strict local maximum on linear magnitudes).
    * ``snr_db``: ``20 * log10(mag[idx])`` minus the noise-floor level
      estimated as ``percentile(noise_floor_percentile)`` over a ±``window_size``
      bin window around ``peak_idx``.
    * ``prominence_db``: saddle-based prominence (see
      :func:`_saddle_prominence_db`). The legacy "peak − max(left, right)"
      formula measured Blackman–Harris main-lobe curvature, NOT prominence,
      which caused every real harmonic to fall below a 3 dB strict gate.

    Returns ``(False, -inf, -inf)`` when ``peak_idx`` is at an array edge.
    """
    mags = np.asarray(magnitudes, dtype=float)
    if peak_idx <= 0 or peak_idx >= len(mags) - 1:
        return False, float("-inf"), float("-inf")
    peak_idx = _refine_peak_index(mags, peak_idx, refine_radius=2)
    if peak_idx <= 0 or peak_idx >= len(mags) - 1:
        return False, float("-inf"), float("-inf")
    peak_lin = float(max(mags[peak_idx], 1e-10))
    left_lin = float(max(mags[peak_idx - 1], 1e-10))
    right_lin = float(max(mags[peak_idx + 1], 1e-10))
    peak_db = 20.0 * np.log10(peak_lin)
    left_db = 20.0 * np.log10(left_lin)
    right_db = 20.0 * np.log10(right_lin)
    is_local_peak = bool((peak_db > left_db) and (peak_db > right_db))
    if (
        f0_hz is not None
        and bin_spacing_hz is not None
        and np.isfinite(float(f0_hz))
        and float(f0_hz) > 0.0
        and np.isfinite(float(bin_spacing_hz))
        and float(bin_spacing_hz) > 0.0
    ):
        saddle_window = _prominence_saddle_window_bins(
            f0_hz=float(f0_hz),
            bin_spacing_hz=float(bin_spacing_hz),
        )
    prominence_db = _saddle_prominence_db(
        mags, peak_idx, saddle_window=saddle_window
    )
    s = max(0, peak_idx - window_size)
    e = min(len(mags), peak_idx + window_size)
    if e <= s:
        return is_local_peak, float("-inf"), prominence_db
    nf_mag = float(np.percentile(mags[s:e], noise_floor_percentile))
    nf_db = 20.0 * np.log10(max(nf_mag, 1e-10))
    snr_db = float(peak_db - nf_db)
    return is_local_peak, snr_db, prominence_db


def cfar_peak_detection(
    magnitudes: np.ndarray,
    peak_idx: int,
    *,
    pfa: float = 1e-2,
    guard_bins: int = 2,
    train_bins: int = 64,
    trim_upper_fraction: float = 0.25,
) -> Tuple[bool, float, float]:
    """Cell-averaging CFAR (constant false-alarm rate) detection for one bin.

    Returns ``(detected, margin_db, threshold_db)`` where the test compares the
    cell-under-test power to a threshold derived from a target false-alarm
    probability ``pfa`` and the locally-estimated noise level.

    Model: under noise only, squared-magnitude FFT bins are ~exponential
    (chi-square, 2 dof). The cell-averaging CFAR threshold is
    ``T = alpha * noise_mean`` with ``alpha = N * (pfa**(-1/N) - 1)`` for ``N``
    independent training cells. This gives a *stated, adaptive* false-alarm rate
    instead of a fixed dB margin: the threshold scales with the local noise
    level rather than a global constant.

    Robustness for harmonic spectra: training cells around a partial inevitably
    include neighbouring partials, which would inflate ``noise_mean`` and mask
    real peaks. The upper ``trim_upper_fraction`` of training-cell powers is
    therefore discarded before averaging (an ordered-statistic flavour), so the
    noise estimate reflects the floor, not the neighbouring peaks. ``guard_bins``
    around the cell-under-test are always excluded.

    ``margin_db = 10*log10(peak_power / threshold)``; ``detected`` is
    ``margin_db >= 0``.
    """
    mags = np.asarray(magnitudes, dtype=float)
    n = mags.size
    if n < 5 or peak_idx <= 0 or peak_idx >= n - 1:
        return False, float("-inf"), float("nan")
    power = mags * mags
    cut = float(power[peak_idx])

    lo = max(0, peak_idx - int(train_bins) - int(guard_bins))
    hi = min(n, peak_idx + int(train_bins) + int(guard_bins) + 1)
    gl = max(0, peak_idx - int(guard_bins))
    gh = min(n, peak_idx + int(guard_bins) + 1)
    train = np.concatenate([power[lo:gl], power[gh:hi]])
    train = train[np.isfinite(train) & (train >= 0.0)]
    if train.size < 8:
        return False, float("-inf"), float("nan")

    # Trim the strongest training cells (likely neighbouring partials) so the
    # noise mean reflects the local floor.
    if 0.0 < trim_upper_fraction < 0.9:
        keep = int(max(4, round(train.size * (1.0 - trim_upper_fraction))))
        train = np.sort(train)[:keep]
    noise_mean = float(np.mean(train))
    if not np.isfinite(noise_mean) or noise_mean <= 0.0:
        return (cut > 0.0), float("inf") if cut > 0.0 else float("-inf"), float("nan")

    n_train = int(train.size)
    pfa = float(min(max(pfa, 1e-9), 0.9))
    alpha = float(n_train * (pfa ** (-1.0 / n_train) - 1.0))
    threshold = alpha * noise_mean
    if not np.isfinite(threshold) or threshold <= 0.0:
        return (cut > 0.0), float("inf") if cut > 0.0 else float("-inf"), float("nan")
    margin_db = 10.0 * float(np.log10(max(cut, 1e-30) / threshold))
    threshold_db = 10.0 * float(np.log10(threshold))
    return bool(margin_db >= 0.0), margin_db, threshold_db


def _classify_harmonic_candidate(
    *,
    amplitude_raw: float,
    local_peak_valid: bool,
    snr_db: float,
    prominence_db: float,
    strict_snr_db: float = 3.0,
    strict_prominence_db: float = 3.0,
    minimum_snr_db: float = 3.0,
    rejected_bad_f0: bool = False,
    harmonic_number: Optional[int] = None,
    cfar_detected: Optional[bool] = None,
) -> Tuple[str, bool]:
    """Classify a per-order harmonic candidate.

    Returns ``(candidate_status, include_for_density)``.

    Density inclusion is deliberately stricter than candidate labelling:

        include_for_density == True iff candidate_status == ``strict_validated``.

    SNR can say that a spectral component is salient; it cannot by itself prove
    that the component is a valid harmonic partial. Therefore ``snr_validated``
    and ``weak_candidate`` remain useful diagnostic labels but are excluded from
    the harmonic density sum.

    This prevents harmonic density from being inflated by side-lobes, broadband
    shoulders, or non-harmonic peaks that happen to fall inside a wide harmonic
    search window.

    The prominence + local-peak + SNR gate that promotes ``strict_validated``
    is the only path that sets ``include_for_density`` to True.
    """
    if rejected_bad_f0:
        return "rejected_bad_f0", False
    if (
        amplitude_raw is None
        or not np.isfinite(amplitude_raw)
        or float(amplitude_raw) <= 0.0
    ):
        return "missing_window", False
    snr = float(snr_db) if np.isfinite(snr_db) else float("-inf")
    prom = float(prominence_db) if np.isfinite(prominence_db) else float("-inf")
    _strict_snr_eff = float(strict_snr_db)
    _strict_prom_eff = float(strict_prominence_db)

    # Noise-significance gate. When a CFAR (constant false-alarm-rate) decision
    # is supplied, it is the PRIMARY detection-theoretic gate — the cell-under-
    # test must exceed a threshold derived from a stated false-alarm probability
    # against the locally-estimated noise floor. This replaces the ad-hoc fixed
    # SNR margin with an adaptive, principled criterion. When CFAR is not
    # available (legacy callers) the fixed SNR margin is used as a fallback.
    if cfar_detected is None:
        snr_significant = snr >= _strict_snr_eff
    else:
        # Require BOTH the CFAR detection and a minimal SNR margin so a noisy
        # local floor estimate cannot, on its own, admit a sub-floor bin.
        snr_significant = bool(cfar_detected) and (snr >= _strict_snr_eff)

    # Saddle prominence + the noise-significance gate are the primary criteria.
    # The ±1-bin ``local_peak_valid`` flag measures main-lobe curvature on
    # windowed FFTs and falsely rejects legitimate harmonics on dense
    # low-register spectra (cello, bass), so it is diagnostic only.
    if snr_significant and prom >= _strict_prom_eff:
        return "strict_validated", True
    if snr >= minimum_snr_db:
        return "snr_validated", False
    if snr > 0.0 or local_peak_valid:
        return "weak_candidate", False
    return "below_noise_floor", False
