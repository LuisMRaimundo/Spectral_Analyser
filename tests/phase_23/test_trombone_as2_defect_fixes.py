from __future__ import annotations

from pathlib import Path

import pytest

from constants import (
    CI_WIDTH_PARTIAL_CORRELATION_N,
    HARMONIC_MIN_CFAR_MARGIN_DB,
    PARTIAL_PERSISTENCE_STRONG_FRACTION,
    TOLERANCE_CONTINUITY_OVERRIDE_FACTOR,
)
from density_uncertainty import (
    bootstrap_effective_component_density,
    ci_resampling_provenance,
)
from harmonic_high_n_guards import (
    CFAR_MARGINAL,
    VALIDATED_WEAK,
    apply_cfar_margin_gate,
    summarize_high_n_guards,
)
from harmonic_peak_validation import (
    apply_exclusive_harmonic_assignment,
    apply_tolerance_continuity_override,
)
from metric_contract import get_metric_definition
from subbass_policy import SUBBASS_BOUND_FORMULA, SubBassPolicy
from temporal_persistence import hop_duration_s, window_duration_s


def test_constants_and_contracts() -> None:
    assert PARTIAL_PERSISTENCE_STRONG_FRACTION == 0.9
    assert TOLERANCE_CONTINUITY_OVERRIDE_FACTOR == 1.25
    assert HARMONIC_MIN_CFAR_MARGIN_DB == 3.0
    assert CI_WIDTH_PARTIAL_CORRELATION_N == 30
    for name in (
        "harmonic_validated_weak_count",
        "harmonic_validated_strict_count",
        "tolerance_continuity_override_count",
        "ci_resampling_unit",
    ):
        assert get_metric_definition(name) is not None


def test_d1_weak_margin_persistence_override() -> None:
    rows = [
        {
            "Harmonic Number": 81,
            "include_for_density": True,
            "candidate_status": "strict_validated",
            "cfar_detected": True,
            "cfar_margin_db": 1.2,
            "persistence_fraction": 1.0,
        },
        {
            "Harmonic Number": 90,
            "include_for_density": True,
            "candidate_status": "strict_validated",
            "cfar_detected": True,
            "cfar_margin_db": 1.0,
            "persistence_fraction": 0.86,
        },
        {
            "Harmonic Number": 200,
            "include_for_density": True,
            "candidate_status": "strict_validated",
            "cfar_detected": True,
            "cfar_margin_db": 1.0,
            "persistence_fraction": 0.3,
        },
    ]
    out = apply_cfar_margin_gate(rows)
    by_n = {int(r["Harmonic Number"]): r for r in out}
    assert by_n[81]["candidate_status"] == VALIDATED_WEAK
    assert by_n[81]["include_for_density"] is True
    assert by_n[81]["exclusion_reason"] == (
        "included (weak_margin_persistence_override)"
    )
    assert by_n[90]["candidate_status"] == CFAR_MARGINAL
    assert by_n[90]["include_for_density"] is False
    assert by_n[200]["candidate_status"] == CFAR_MARGINAL
    assert by_n[200]["include_for_density"] is False
    summary = summarize_high_n_guards(out, slot_count=3, body_stop_order=200)
    assert summary["harmonic_validated_count"] == 1
    assert summary["harmonic_validated_weak_count"] == 1
    assert summary["harmonic_validated_strict_count"] == 0
    assert summary["accepted_slots_above_body_stop"] == 0


def test_d2_tolerance_continuity_override_and_triple_losers() -> None:
    cap = 34.9
    rows = []
    for n, freq, include in (
        (73, 7300.0, True),
        (74, 7435.6, False),
        (75, 7500.0, True),
    ):
        expected = 100.0 * n
        rows.append(
            {
                "Harmonic Number": n,
                "expected_frequency_hz": expected,
                "extracted_frequency_hz": freq,
                "Frequency (Hz)": freq,
                "frequency_deviation_hz": freq - expected,
                "search_tol_hz": cap,
                "tolerance_limb": "spacing_cap",
                "candidate_status": (
                    "strict_validated" if include else "rejected_by_tolerance"
                ),
                "include_for_density": include,
                "persistence_fraction": 1.0,
                "peak_bin_index": 100 + n,
            }
        )
    rows[1]["exclusion_reason"] = "rejected_by_tolerance (dev=35.60 Hz > cap=34.90 Hz)"
    out, n_ov = apply_tolerance_continuity_override(rows)
    by_n = {int(r["Harmonic Number"]): r for r in out}
    assert n_ov == 1
    assert by_n[74]["include_for_density"] is True
    assert str(by_n[74]["exclusion_reason"]).startswith(
        "included (tolerance_continuity_override"
    )
    assert by_n[74]["tolerance_limb"] == "spacing_cap_continuity"

    f0 = 110.0
    peak = 12094.26
    triple = []
    for n in (109, 110, 111):
        expected = n * f0
        triple.append(
            {
                "Harmonic Number": n,
                "expected_frequency_hz": expected,
                "extracted_frequency_hz": peak,
                "Frequency (Hz)": peak,
                "frequency_deviation_hz": peak - expected,
                "peak_bin_index": 4481,
                "search_tol_hz": 0.30 * f0,
                "tolerance_limb": "spacing_cap",
                "candidate_status": "strict_validated",
                "include_for_density": True,
                "persistence_fraction": 1.0,
            }
        )
    assigned = apply_exclusive_harmonic_assignment(triple)
    overridden, n_triple = apply_tolerance_continuity_override(assigned)
    included = [r for r in overridden if r.get("include_for_density")]
    assert len(included) == 1
    assert n_triple == 0
    losers = [r for r in overridden if int(r["Harmonic Number"]) in {109, 111}]
    assert all(r["candidate_status"] == "rejected_by_tolerance" for r in losers)


def test_d3_f020_bound_is_single_source() -> None:
    for f0, expected in ((50.0, 25.0), (116.3, 58.15), (200.0, 80.0)):
        resolved = SubBassPolicy.resolve_f020_bound(f0)
        assert resolved["subbass_upper_bound_hz"] == pytest.approx(expected)
        assert resolved["subbass_bound_formula"] == SUBBASS_BOUND_FORMULA
        assert resolved["subbass_bound_f0_used_hz"] == pytest.approx(f0)
        assert SubBassPolicy.upper_bound_hz(f0, 44100.0, 4096) == pytest.approx(expected)


def test_d4_ci_provenance_does_not_change_estimator() -> None:
    amps = [1.0, 0.8, 0.4, 0.2] + [0.05] * 40
    a = bootstrap_effective_component_density(amps, n_boot=200, seed=0)
    b = bootstrap_effective_component_density(amps, n_boot=200, seed=0)
    assert a["point_estimate"] == pytest.approx(b["point_estimate"])
    assert a["ci_low"] == pytest.approx(b["ci_low"])
    assert a["ci_high"] == pytest.approx(b["ci_high"])
    prov = ci_resampling_provenance(
        unit="partials",
        n_resampled=float(len(amps)),
        n_boot=200,
        seed=0,
        independent_frame_count=3.5,
        relative_width_pct=68.8,
    )
    assert prov["ci_resampling_unit"] == "partials"
    assert prov["ci_n_resampled"] == pytest.approx(44.0)
    assert prov["ci_width_flag"] == "wide"
    assert "low_independent_frames" in prov["ci_width_note"]
    assert "high_partial_correlation" in prov["ci_width_note"]


def test_d5_hop_and_window_durations() -> None:
    hop = hop_duration_s(hop_length=1024, sr_hz=22050.0)
    win = window_duration_s(n_fft=4096, sr_hz=22050.0)
    assert hop == pytest.approx(1024.0 / 22050.0)
    assert win == pytest.approx(4096.0 / 22050.0)
    assert win > hop


def test_iowa_trombone_as2_ff_acceptance_if_present(tmp_path: Path) -> None:
    audio = Path(
        r"D:\METAIS\TROMBONE\IOWA_Trombone - Test\TenorTrombone"
        r"\IOWA_Trombone_ff\_Sustains_Stable"
        r"\IOWA_Trb.T_ff.A#2_SustainStable.aif"
    )
    if not audio.is_file():
        pytest.skip("trombone A#2 ff SustainStable audio not mounted")
    from proc_audio import AudioProcessor

    ap = AudioProcessor()
    ap.load_audio_files([str(audio)])
    ap.apply_filters_and_generate_data(
        results_directory=tmp_path / "as2",
        n_fft=4096,
        hop_length=1024,
        zero_padding=1,
        freq_min=20.0,
        freq_max=20000.0,
        density_frequency_ceiling_hz=20000.0,
        dissonance_enabled=False,
        dissonance_curve=False,
        dissonance_scale=False,
        compare_models=False,
        compile_per_call=False,
        parallel_processing=False,
    )
    workbooks = list((tmp_path / "as2").rglob("spectral_analysis.xlsx"))
    assert workbooks
    import pandas as pd

    wb = workbooks[0]
    harm = pd.read_excel(wb, sheet_name="Harmonic Spectrum")
    val = pd.read_excel(wb, sheet_name="Validation_Metrics")
    meta = pd.read_excel(wb, sheet_name="Per_Note_Processing_Metadata")
    by_n = {
        int(n): r
        for n, r in zip(
            pd.to_numeric(harm["Harmonic Number"], errors="coerce"),
            harm.to_dict(orient="records"),
        )
        if n == n
    }
    for n in range(81, 89):
        if n not in by_n:
            continue
        row = by_n[n]
        try:
            persist = float(row.get("persistence_fraction", float("nan")))
            margin = float(row.get("cfar_margin_db", float("nan")))
        except (TypeError, ValueError):
            continue
        detected = bool(row.get("cfar_detected", False))
        if persist >= 0.9 and detected and 0.0 < margin < 3.0:
            assert row.get("candidate_status") == VALIDATED_WEAK
            assert bool(row.get("include_for_density"))
    for n in (74, 79):
        if n in by_n:
            assert bool(by_n[n].get("include_for_density"))
    validated = int(val["harmonic_validated_count"].iloc[0])
    assert validated >= 86
    assert float(val["subbass_upper_bound_hz"].iloc[0]) == pytest.approx(58.15, abs=0.05)
    assert "hop_duration_s" in meta.columns
    assert "window_duration_s" in meta.columns
    assert int(getattr(ap, "accepted_slots_above_body_stop", 1)) == 0
    pies = list((wb.parent).glob("component_energy*.png"))
    names = {p.name for p in pies}
    assert "component_energy_pie.png" in names
    assert "component_energy_ratio_pie.png" not in names
