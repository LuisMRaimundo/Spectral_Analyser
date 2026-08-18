"""Helper-level contracts for low-f₀ spacing-capped tolerance and body stop."""

from __future__ import annotations

import numpy as np

from constants import (
    HARMONIC_MATCH_TOLERANCE_CENTS,
    HARMONIC_TOLERANCE_POLICY_VERSION,
    HARMONIC_TOLERANCE_SPACING_CAP_FRACTION,
    INHARMONICITY_B_ENABLE_THRESHOLD,
)
from proc_audio import AudioProcessor
from density_uncertainty import evaluate_density_fragility, window_perturbation_spread_pct
from harmonic_peak_validation import (
    apply_harmonic_body_stop,
    compute_spacing_capped_tolerance_hz,
    evaluate_low_f0_resolution_guard,
)
from harmonic_validation import spacing_capped_tolerance_hz


def test_policy_version_and_beta_defaults() -> None:
    assert HARMONIC_TOLERANCE_POLICY_VERSION == "2"
    assert HARMONIC_TOLERANCE_SPACING_CAP_FRACTION == 0.30
    assert spacing_capped_tolerance_hz is compute_spacing_capped_tolerance_hz


def test_spacing_cap_inactive_at_low_order() -> None:
    tol_hz, limb = compute_spacing_capped_tolerance_hz(
        1, 523.0, bin_spacing_hz=2.0, harmonic_tolerance_cents=35.0
    )
    expected = 523.0 * 35.0 / 1200.0
    assert limb == "cents"
    assert abs(tol_hz - expected) < 1e-12


def test_spacing_cap_centered_on_stretched_prediction() -> None:
    """A 0.30·f0 cap around n·f0 misses real H40 when B = 5e-4; the
    Inharmonicity_Fit centre does not.
    """
    f0 = 220.0
    b_hat = 5.0e-4
    n = 40
    assert b_hat > INHARMONICITY_B_ENABLE_THRESHOLD
    ideal = float(n) * f0
    predicted = AudioProcessor._expected_harmonic_hz(n, f0, b_hat)
    tol_hz, limb = compute_spacing_capped_tolerance_hz(
        n, f0, bin_spacing_hz=1.0, harmonic_tolerance_cents=35.0
    )
    assert limb == "spacing_cap"
    assert abs(predicted - ideal) > tol_hz
    assert abs(predicted - predicted) <= tol_hz


def test_spacing_cap_binds_near_h20_for_default_cents() -> None:
    f0 = 32.7
    crossover = HARMONIC_TOLERANCE_SPACING_CAP_FRACTION / (
        HARMONIC_MATCH_TOLERANCE_CENTS / 1200.0
    )
    n_cap = int(np.ceil(crossover)) + 1
    tol_hz, limb = compute_spacing_capped_tolerance_hz(
        n_cap, f0, bin_spacing_hz=1.35, harmonic_tolerance_cents=35.0
    )
    assert limb == "spacing_cap"
    assert abs(tol_hz - 0.30 * f0) < 1e-9


def test_bin_floor_limb_when_fft_is_coarse() -> None:
    tol_hz, limb = compute_spacing_capped_tolerance_hz(
        1, 32.7, bin_spacing_hz=20.0, harmonic_tolerance_cents=35.0
    )
    assert limb == "bin_floor"
    assert abs(tol_hz - 20.0) < 1e-12


def test_body_stop_cuts_validated_tail_at_noise_floor() -> None:
    f0 = 33.0
    rows = []
    for n in range(1, 40):
        mag = -10.0 if n <= 28 else -45.0
        snr = 20.0 if n <= 28 else 2.0
        rows.append(
            {
                "Harmonic Number": n,
                "expected_frequency_hz": n * f0,
                "Magnitude (dB)": mag,
                "snr_db": snr,
                "include_for_density": n <= 28 or n >= 32,
                "Amplitude_raw": 10 ** (mag / 20.0),
            }
        )
    out, meta = apply_harmonic_body_stop(rows, f0_hz=f0, enabled=True)
    assert meta["harmonic_body_stop_triggered"] is True
    assert 0.9e3 <= float(meta["harmonic_body_stop_hz"]) <= 1.5e3
    stop_n = int(meta["harmonic_body_stop_order"])
    assert all(
        (not r["include_for_density"]) or int(r["Harmonic Number"]) <= stop_n for r in out
    )
    assert any(r.get("above_harmonic_body_stop") for r in out)


def test_body_stop_inactive_when_envelope_stays_above_floor() -> None:
    f0 = 523.0
    rows = [
        {
            "Harmonic Number": n,
            "expected_frequency_hz": n * f0,
            "Magnitude (dB)": -8.0 - 0.3 * n,
            "snr_db": 25.0,
            "include_for_density": True,
            "Amplitude_raw": 0.1,
        }
        for n in range(1, 23)
    ]
    out, meta = apply_harmonic_body_stop(
        rows, f0_hz=f0, enabled=True, density_frequency_ceiling_hz=20000.0
    )
    assert meta["harmonic_body_stop_triggered"] is False
    assert float(meta["density_effective_ceiling_hz"]) == 20000.0
    assert all(r["include_for_density"] for r in out)


def test_low_f0_guard_escalates_n_fft_when_sustain_allows() -> None:
    out = evaluate_low_f0_resolution_guard(
        f0_hz=32.7,
        bin_spacing_hz=10.77,
        n_fft=4096,
        sample_rate_hz=44100.0,
        sustain_seconds=1.5,
    )
    assert out["n_fft_escalated"] is True
    assert out["n_fft"] > 4096
    assert out["bin_to_f0_ratio"] <= 0.125 or out["low_f0_resolution_warning"]


def test_audit_reason_above_harmonic_body_stop() -> None:
    from harmonic_peak_validation import _harmonic_inclusion_audit_exclusion_reason

    reason = _harmonic_inclusion_audit_exclusion_reason(
        include_for_density=False,
        expected_frequency_hz=2000.0,
        frequency_deviation_hz=0.0,
        candidate_status="strict_validated",
        local_peak_valid=True,
        snr_db=10.0,
        prominence_db=10.0,
        above_harmonic_body_stop=True,
    )
    assert reason == "above_harmonic_body_stop"


def test_fragility_flag_from_ci_or_perturbation() -> None:
    wide = evaluate_density_fragility(
        point_estimate=100.0, ci_low=80.0, ci_high=130.0, perturbation_spread_pct=1.0
    )
    assert wide["density_fragile"] is True
    assert wide["density_fragile_from_ci"] is True
    pert = evaluate_density_fragility(
        point_estimate=100.0, ci_low=99.0, ci_high=101.0, perturbation_spread_pct=12.0
    )
    assert pert["density_fragile"] is True
    assert pert["density_fragile_from_perturbation"] is True
    stable = evaluate_density_fragility(
        point_estimate=100.0, ci_low=97.0, ci_high=103.0, perturbation_spread_pct=2.0
    )
    assert stable["density_fragile"] is False
    assert window_perturbation_spread_pct([100.0, 102.0, 98.0], center=100.0) == 4.0
