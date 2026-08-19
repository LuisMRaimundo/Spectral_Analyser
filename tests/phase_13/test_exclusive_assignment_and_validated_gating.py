from __future__ import annotations

"""Phase 13: exclusive harmonic assignment, validated-partial gating, labels."""

import pandas as pd
import pytest

from data_integrity import validate_unique_peak_bin_assignment
from debug_counts import validate_debug_count_invariants
from harmonic_peak_validation import (
    apply_exclusive_harmonic_assignment,
    apply_harmonic_body_stop,
)
from metric_contract import get_metric_definition
from proc_audio import AudioProcessor, frequency_to_note_name
from validated_partials import (
    gated_dissonance_partials,
    gated_effective_partial_density,
    gated_linear_amplitude_sums,
    gated_subbass_energy_sum,
    is_validated_partial,
    participation_ratio_from_amplitudes,
)


def _triple_floor_rows() -> list[dict]:
    """One 12 094.26 Hz peak claimed by n=109, 110, 111 (A2 / f0=110)."""
    f0 = 110.0
    peak_hz = 12094.26
    peak_bin = 4481
    cap = 0.30 * f0
    rows = []
    for n in (109, 110, 111):
        expected = n * f0
        rows.append(
            {
                "Harmonic Number": n,
                "expected_frequency_hz": expected,
                "extracted_frequency_hz": peak_hz,
                "Frequency (Hz)": peak_hz,
                "frequency_deviation_hz": peak_hz - expected,
                "peak_bin_index": peak_bin,
                "search_tol_hz": cap,
                "tolerance_limb": "spacing_cap",
                "candidate_status": "strict_validated",
                "include_for_density": True,
                "Amplitude_raw": 1.82,
                "Magnitude (dB)": 5.20,
            }
        )
    return rows


def test_exclusive_assignment_keeps_one_slot_for_injected_floor_peak() -> None:
    out = apply_exclusive_harmonic_assignment(_triple_floor_rows())
    included = [r for r in out if r.get("include_for_density")]
    assert len(included) == 1
    assert int(included[0]["Harmonic Number"]) == 110
    losers = [r for r in out if int(r["Harmonic Number"]) in {109, 111}]
    assert all(r["candidate_status"] == "rejected_by_tolerance" for r in losers)
    assert all(str(r["exclusion_reason"]).startswith("rejected_by_tolerance") for r in losers)
    assert all(r["tolerance_limb"] == "spacing_cap" for r in losers)
    assert all(not r.get("above_harmonic_body_stop") for r in losers)


def test_tolerance_reject_is_not_relabelled_as_body_stop() -> None:
    rows = apply_exclusive_harmonic_assignment(_triple_floor_rows())
    stopped, meta = apply_harmonic_body_stop(
        rows,
        f0_hz=110.0,
        enabled=True,
        density_frequency_ceiling_hz=20000.0,
    )
    by_n = {int(r["Harmonic Number"]): r for r in stopped}
    assert str(by_n[109]["exclusion_reason"]).startswith("rejected_by_tolerance")
    assert str(by_n[111]["exclusion_reason"]).startswith("rejected_by_tolerance")
    assert by_n[109]["candidate_status"] == "rejected_by_tolerance"
    assert by_n[111]["candidate_status"] == "rejected_by_tolerance"


def test_peak_bin_invariant_fails_closed_on_duplicate_included_bins() -> None:
    raw = pd.DataFrame(_triple_floor_rows())
    check = validate_unique_peak_bin_assignment(raw)
    assert check["ok"] is False
    assert 4481 in check["duplicated_bins"]
    row = validate_debug_count_invariants({}, harmonic_df=raw)
    assert row["debug_counts_invariant_status"] == "failed"
    assert "duplicate_peak_bin_index_among_include_for_density" in row[
        "debug_counts_invariant_failures"
    ]

    cleaned = pd.DataFrame(apply_exclusive_harmonic_assignment(_triple_floor_rows()))
    ok = validate_unique_peak_bin_assignment(cleaned)
    assert ok["ok"] is True
    passed = validate_debug_count_invariants({}, harmonic_df=cleaned)
    assert passed["debug_counts_invariant_status"] == "passed"


def _eight_real_plus_floor() -> tuple[list[dict], list[dict], list[dict]]:
    harmonic = []
    amps = [1.00, 0.90, 0.95, 0.60, 0.20, 0.12, 0.04, 0.03]
    for n, amp in enumerate(amps, 1):
        harmonic.append(
            {
                "Harmonic Number": n,
                "Frequency (Hz)": 110.0 * n,
                "Amplitude_raw": amp,
                "include_for_density": True,
            }
        )
    inharmonic = [
        {
            "Frequency (Hz)": 3000.0 + i,
            "Amplitude_raw": 0.05,
            "Acoustic_Interpretation_Status": "candidate_not_confirmed_partial",
        }
        for i in range(40)
    ]
    subbass = [
        {
            "Frequency (Hz)": 70.0,
            "Amplitude_raw": 0.40,
            "Low_Frequency_Class": "physical_low_frequency_residual",
        }
    ]
    return harmonic, inharmonic, subbass


def test_validated_partial_gating_ignores_floor_rows_in_four_consumers() -> None:
    harmonic, inharmonic, subbass = _eight_real_plus_floor()
    real_amps = [r["Amplitude_raw"] for r in harmonic]
    expected_pr = participation_ratio_from_amplitudes(real_amps)

    h, i, s = gated_linear_amplitude_sums(
        harmonic_rows=harmonic,
        inharmonic_rows=inharmonic,
        subbass_rows=subbass,
    )
    assert h == sum(real_amps)
    assert i == 0.0
    assert s == 0.0
    assert gated_effective_partial_density(harmonic + inharmonic) == pytest.approx(expected_pr)
    pairs = gated_dissonance_partials(harmonic + inharmonic)
    assert len(pairs) == 8
    assert all(is_validated_partial(r, kind="inharmonic") is False for r in inharmonic)
    assert gated_subbass_energy_sum(subbass, f0_hz=110.0) == 0.0


def test_subbass_residual_above_f020_contributes_zero_energy() -> None:
    rows = [
        {
            "Frequency (Hz)": 40.0,
            "Amplitude_raw": 0.5,
            "Low_Frequency_Class": "subbass_compartment",
        },
        {
            "Frequency (Hz)": 70.0,
            "Amplitude_raw": 9.0,
            "Low_Frequency_Class": "physical_low_frequency_residual",
        },
    ]
    assert gated_subbass_energy_sum(rows, f0_hz=110.0) == pytest.approx(0.5 * 0.5)


def test_partial_pitch_name_uses_frequency_not_sample_tag() -> None:
    assert frequency_to_note_name(110.0).startswith("A2")
    assert frequency_to_note_name(220.0).startswith("A3")
    assert frequency_to_note_name(440.0).startswith("A4")
    ap = AudioProcessor()
    ap.note = "A2"
    ap.sample_id = "iowa-tuba-a2"
    row = ap._build_harmonic_candidate_row(
        hnum=2,
        expected_freq_hz=220.0,
        tol_hz=5.0,
        complete_magnitudes=None,
        complete_freqs=None,
    )
    assert row["sample_note_tag"] == "A2"
    assert "Note" not in row
    assert row["partial_pitch_name"] == ""


def test_pie_caption_carries_tag_run_and_version() -> None:
    ap = AudioProcessor()
    ap.code_commit = "abc1234"
    ap.analysis_run_label = "run 3"
    caption = ap._component_pie_caption(
        "A2", chart="Validated-partial amplitude balance"
    )
    assert caption == "Validated-partial amplitude balance · A2 · run 3 · abc1234"


def test_metric_contract_input_domain_is_validated_partials() -> None:
    for name in (
        "effective_partial_density",
        "linear_sum_amplitude_*",
        "sethares_dissonance",
    ):
        defn = get_metric_definition(name)
        assert defn is not None
        assert defn.input_domain == "validated_partials_only"
