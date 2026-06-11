from __future__ import annotations

"""
Helper-level contract tests for proc_audio.py (layer 2).

Complements tests/phase_12/test_proc_audio_core_additional.py with focused
coverage of schema/export helpers, parameter validation, STFT edge weights,
F0 provenance finalization, harmonic-candidate builders, and deterministic
synthetic-spectrum behavior — without broad pipeline integration.

No production code changes. No real audio corpus, GUI, plotting, or Excel I/O.
"""

import math

import numpy as np
import pandas as pd
import pytest

import proc_audio as PA
from proc_audio import ANALYSIS_SCHEMA_VERSION, AudioProcessor, validate_audio_parameters


def _synthetic_spectrum(
    *,
    sr: int = 44100,
    n_fft: int = 4096,
    harmonic_hz: list[float],
    baseline: float = 0.001,
    peak: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    freqs = np.linspace(0.0, sr / 2.0, n_fft // 2 + 1)
    mags = np.full_like(freqs, baseline)
    for target in harmonic_hz:
        idx = int(np.argmin(np.abs(freqs - target)))
        lo = max(0, idx - 1)
        hi = min(len(mags), idx + 2)
        mags[lo:hi] = [peak * 0.3, peak, peak * 0.3][: hi - lo]
    return freqs, mags


def _processor_with_peaks(
    *,
    f0: float,
    harmonic_multiples: list[int],
    sr: int = 44100,
    n_fft: int = 4096,
) -> AudioProcessor:
    ap = AudioProcessor()
    ap.sr = sr
    ap.n_fft = n_fft
    ap.note = "Synth"
    hz = [f0 * h for h in harmonic_multiples]
    ap.filtered_list_df = pd.DataFrame(
        {
            "Frequency (Hz)": hz,
            "Amplitude": [1.0 - 0.1 * i for i in range(len(hz))],
        }
    )
    return ap


# ---------------------------------------------------------------------------
# 1. Schema / runtime metadata helpers
# ---------------------------------------------------------------------------

def test_spectral_sheet_has_raw_columns_contract() -> None:
    assert PA._spectral_sheet_has_raw_columns(None) is True
    assert PA._spectral_sheet_has_raw_columns(pd.DataFrame()) is True
    assert PA._spectral_sheet_has_raw_columns(pd.DataFrame({"Amplitude": [1.0]})) is False
    assert PA._spectral_sheet_has_raw_columns(
        pd.DataFrame({"Amplitude_raw": [1.0], "Power_raw": [1.0]})
    ) is True


def test_log_runtime_paths_pins_analysis_schema_version() -> None:
    info = PA.log_runtime_paths()
    assert info["analysis_schema_version"] == ANALYSIS_SCHEMA_VERSION
    assert info["analysis_schema_version"] == "single_pass_raw_export_v2"
    assert "proc_audio_file" in info
    assert "proc_audio_runtime_signature" in info


def test_proc_audio_runtime_signature_is_deterministic() -> None:
    assert PA._proc_audio_runtime_signature() == PA._proc_audio_runtime_signature()


# ---------------------------------------------------------------------------
# 2. Parameter validation and normalization
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("n_fft", "hop", "sr", "length", "ok", "msg_part"),
    [
        (4096, 1024, 44100, 8192, True, None),
        (4096, 1024, 44100, 100, False, "Signal length"),
        (4096, 0, 44100, 8192, False, "hop_length"),
        (4096, 5000, 44100, 8192, False, "hop_length"),
    ],
)
def test_validate_audio_parameters_boundaries(
    n_fft: int, hop: int, sr: int, length: int, ok: bool, msg_part: str | None
) -> None:
    valid, msg = validate_audio_parameters(n_fft, hop, sr, length)
    assert valid is ok
    if not ok:
        assert msg is not None and msg_part in msg


def test_validate_and_store_parameters_normalizes_weights_and_default_hop() -> None:
    ap = AudioProcessor()
    ap._validate_and_store_parameters(
        2048,
        None,
        "hann",
        "log",
        3.0,
        1.0,
        False,
        "sethares",
        False,
        False,
        False,
    )
    assert ap.n_fft == 2048
    assert ap.hop_length == 512
    assert ap.harmonic_weight == pytest.approx(0.75, abs=1e-9)
    assert ap.inharmonic_weight == pytest.approx(0.25, abs=1e-9)
    assert ap.weight_function == "log"


def test_validate_and_store_parameters_rejects_nonpositive_n_fft() -> None:
    ap = AudioProcessor()
    with pytest.raises(ValueError, match="n_fft must be positive"):
        ap._validate_and_store_parameters(
            0, 512, "hann", "linear", 1.0, 0.0, False, "sethares", False, False, False
        )


def test_normalize_weight_function_ui_key_aliases() -> None:
    assert AudioProcessor._normalize_weight_function_ui_key("d2") == "linear"
    assert AudioProcessor._normalize_weight_function_ui_key("d8") == "d17"
    assert AudioProcessor._normalize_weight_function_ui_key(None) == "linear"


# ---------------------------------------------------------------------------
# 3. STFT edge-frame helpers
# ---------------------------------------------------------------------------

def test_edge_frame_counts_and_weights_shape_and_caps() -> None:
    ap = AudioProcessor()
    ap.hop_length = 512
    n_frames, n_fft = 100, 4096
    first, last = ap._calculate_edge_frame_counts(n_frames, n_fft)
    assert first == last == 4
    weights = ap._calculate_edge_frame_weights(10, n_fft)
    assert weights.shape == (10,)
    assert weights[0] == pytest.approx(2.0, abs=1e-12)
    assert weights[-1] == pytest.approx(2.0, abs=1e-12)
    assert np.all(weights >= 1.0)
    assert np.all(weights <= 2.0)


def test_edge_frame_weights_do_not_mutate_external_state() -> None:
    ap = AudioProcessor()
    ap.hop_length = 256
    before = ap.hop_length
    _ = ap._calculate_edge_frame_weights(20, 2048)
    assert ap.hop_length == before


# ---------------------------------------------------------------------------
# 4. Window resolution
# ---------------------------------------------------------------------------

def test_get_window_arg_hann_length_matches_n_fft() -> None:
    ap = AudioProcessor()
    ap.n_fft = 1024
    ap.window = "hann"
    win = ap._get_window_arg()
    assert len(win) == 1024
    assert np.all(np.isfinite(win))
    assert float(win.max()) == pytest.approx(1.0, rel=1e-6)


def test_get_window_arg_accepts_custom_array_and_rejects_length_mismatch() -> None:
    ap = AudioProcessor()
    ap.n_fft = 8
    ap.window = np.hanning(8)
    assert len(ap._get_window_arg()) == 8
    ap.window = np.hanning(4)
    with pytest.raises(ValueError, match="Window length"):
        ap._get_window_arg()


# ---------------------------------------------------------------------------
# 5. F0 provenance finalization
# ---------------------------------------------------------------------------

def test_finalize_f0_state_accepted_sets_explicit_provenance() -> None:
    ap = AudioProcessor()
    ap._finalize_f0_state(
        nominal_hz=440.0,
        candidate_hz=441.0,
        accept_fit=True,
        acceptance_mode="free_fit",
        fit_quality=0.01,
        residual_std_hz=0.5,
    )
    f0_hz, f0_source, acoustic_status = ap._canonical_f0_triplet_for_analysis()
    assert f0_hz == pytest.approx(441.0, rel=1e-12)
    assert f0_source == "prior_constrained_harmonic_fit"
    assert acoustic_status == "fit_accepted_acoustically_verified"
    assert ap.f0_fit_accepted is True
    assert ap.f0_fit_rejection_reason is None


def test_finalize_f0_state_rejected_keeps_nominal_with_explicit_fallback_source() -> None:
    ap = AudioProcessor()
    ap._finalize_f0_state(
        nominal_hz=440.0,
        candidate_hz=500.0,
        accept_fit=False,
        rejection_reason="residual_too_large",
    )
    assert ap.f0_final == pytest.approx(440.0, rel=1e-12)
    assert ap.f0_final_source == "filename_note_nominal_fallback_fit_rejected"
    assert ap.f0_source == "filename_note_nominal_fallback_fit_rejected"
    assert ap.f0_fit_accepted is False
    assert ap.f0_fit_rejection_reason == "residual_too_large"
    # Triplet uses f0_initial/prior when fit is not accepted; without those it
    # stays explicitly unresolved rather than silently promoting f0_final.
    f0_hz, f0_source, acoustic_status = ap._canonical_f0_triplet_for_analysis()
    assert math.isnan(f0_hz)
    assert f0_source == "missing"
    assert acoustic_status == "missing_invalid_f0"


# ---------------------------------------------------------------------------
# 6. Harmonic candidate helpers
# ---------------------------------------------------------------------------

def test_build_harmonic_candidate_row_missing_window_when_no_data() -> None:
    ap = AudioProcessor()
    ap.note = "A4"
    row = ap._build_harmonic_candidate_row(
        hnum=1,
        expected_freq_hz=440.0,
        tol_hz=5.0,
        complete_magnitudes=None,
        complete_freqs=None,
    )
    assert row["candidate_status"] == "missing_window"
    assert row["include_for_density"] is False
    assert math.isnan(row["Frequency (Hz)"])
    assert row["Note"] == "A4"


def test_build_harmonic_candidate_picks_closest_frequency_not_loudest_outlier() -> None:
    ap = AudioProcessor()
    ap.sr = 44100
    ap.n_fft = 4096
    ap.filtered_list_df = pd.DataFrame(
        {"Frequency (Hz)": [440.0, 880.0, 900.0], "Amplitude": [1.0, 0.5, 0.9]}
    )
    row = ap._build_harmonic_candidate_row(
        hnum=2,
        expected_freq_hz=880.0,
        tol_hz=30.0,
        complete_magnitudes=None,
        complete_freqs=None,
    )
    assert row["Frequency (Hz)"] == pytest.approx(880.0, abs=1e-9)
    assert row["Amplitude_raw"] == pytest.approx(0.5, abs=1e-9)


def test_build_harmonic_candidate_marks_off_frequency_peaks_non_included() -> None:
    ap = AudioProcessor()
    ap.sr = 44100
    ap.n_fft = 4096
    ap.filtered_list_df = pd.DataFrame({"Frequency (Hz)": [950.0], "Amplitude": [1.0]})
    row = ap._build_harmonic_candidate_row(
        hnum=2,
        expected_freq_hz=880.0,
        tol_hz=30.0,
        complete_magnitudes=None,
        complete_freqs=None,
    )
    assert row["candidate_status"] == "missing_window"
    assert row["include_for_density"] is False


def test_rebuild_harmonic_candidates_low_note_includes_only_detected_partials() -> None:
    f0 = 110.0
    sr, n_fft = 44100, 4096
    freqs, mags = _synthetic_spectrum(
        sr=sr, n_fft=n_fft, harmonic_hz=[f0 * h for h in (1, 2, 3, 4)]
    )
    ap = _processor_with_peaks(f0=f0, harmonic_multiples=[1, 2, 3, 4], sr=sr, n_fft=n_fft)
    rows = ap._rebuild_harmonic_candidate_rows(
        f0_hz=f0,
        freq_max=1000.0,
        tolerance=30.0,
        use_adaptive_tolerance=False,
        bin_spacing=float(freqs[1] - freqs[0]),
        has_sub_bin_interpolation=True,
        complete_magnitudes=mags,
        complete_freqs=freqs,
    )
    included = [r for r in rows if r["include_for_density"]]
    assert len(rows) == 10
    assert len(included) == 4
    assert all(r["candidate_status"] == "strict_validated" for r in included)


def test_rebuild_harmonic_candidates_high_note_does_not_inflate_missing_slots() -> None:
    f0 = 2000.0
    sr, n_fft = 44100, 4096
    freqs, mags = _synthetic_spectrum(sr=sr, n_fft=n_fft, harmonic_hz=[f0, 2 * f0])
    ap = _processor_with_peaks(f0=f0, harmonic_multiples=[1, 2], sr=sr, n_fft=n_fft)
    rows = ap._rebuild_harmonic_candidate_rows(
        f0_hz=f0,
        freq_max=10000.0,
        tolerance=50.0,
        use_adaptive_tolerance=False,
        bin_spacing=float(freqs[1] - freqs[0]),
        has_sub_bin_interpolation=True,
        complete_magnitudes=mags,
        complete_freqs=freqs,
    )
    included = [r for r in rows if r["include_for_density"]]
    assert len(rows) == 6
    assert len(included) <= 2
    assert len(included) >= 1


# ---------------------------------------------------------------------------
# 7. Amplitude validation and interval naming
# ---------------------------------------------------------------------------

def test_validate_amplitude_data_filters_non_finite_and_floors_positive() -> None:
    ap = AudioProcessor()
    out = ap._validate_amplitude_data(np.array(["ignored"]), np.array([0.0, np.nan, -1.0, 2.0]))
    assert out.tolist() == [pytest.approx(1e-12), pytest.approx(1e-12), pytest.approx(2.0)]
    assert ap._validate_amplitude_data(np.array([]), np.array([])).size == 0


def test_get_interval_name_canonical_and_out_of_tolerance() -> None:
    ap = AudioProcessor()
    assert ap._get_interval_name(700.0) == "Perfect 5th"
    assert ap._get_interval_name(50.0) is None
    assert ap._get_interval_name(float("nan")) is None


# ---------------------------------------------------------------------------
# 8. Copy semantics and determinism
# ---------------------------------------------------------------------------

def test_normalize_level_does_not_mutate_input_array() -> None:
    y = np.array([0.1, -0.2, 0.3], dtype=float)
    snapshot = y.copy()
    _ = PA._normalize_level(y, target_rms_db=-20.0)
    np.testing.assert_array_equal(y, snapshot)


def test_physical_peak_amplitude_does_not_mutate_input_magnitudes() -> None:
    mag = np.array([1.0, 2.0, 0.5], dtype=float)
    snapshot = mag.copy()
    _ = PA.physical_peak_amplitude(mag, "hann", 4096, is_one_sided=True)
    np.testing.assert_array_equal(mag, snapshot)


def _stable_harmonic_row_signature(row: dict) -> tuple:
    freq = row["Frequency (Hz)"]
    freq_key = "nan" if isinstance(freq, float) and math.isnan(freq) else float(freq)
    return (
        int(row["Harmonic Number"]),
        str(row["candidate_status"]),
        bool(row["include_for_density"]),
        freq_key,
    )


def test_harmonic_candidate_helpers_are_deterministic() -> None:
    f0 = 220.0
    sr, n_fft = 44100, 4096
    freqs, mags = _synthetic_spectrum(sr=sr, n_fft=n_fft, harmonic_hz=[f0, 2 * f0, 3 * f0])
    kwargs = dict(
        f0_hz=f0,
        freq_max=1000.0,
        tolerance=25.0,
        use_adaptive_tolerance=False,
        bin_spacing=float(freqs[1] - freqs[0]),
        has_sub_bin_interpolation=True,
        complete_magnitudes=mags.copy(),
        complete_freqs=freqs.copy(),
    )
    ap = _processor_with_peaks(f0=f0, harmonic_multiples=[1, 2, 3], sr=sr, n_fft=n_fft)
    rows_a = ap._rebuild_harmonic_candidate_rows(**kwargs)
    rows_b = ap._rebuild_harmonic_candidate_rows(**kwargs)
    assert [_stable_harmonic_row_signature(r) for r in rows_a] == [
        _stable_harmonic_row_signature(r) for r in rows_b
    ]
