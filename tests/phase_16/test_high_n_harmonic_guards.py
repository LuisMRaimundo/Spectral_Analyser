from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from constants import (
    CFAR_PFA,
    HARMONIC_CONTINUITY_RULE_ENABLED,
    HARMONIC_MIN_CFAR_MARGIN_DB,
)
from data_integrity import validate_unique_peak_bin_assignment
from harmonic_high_n_guards import (
    CFAR_MARGINAL,
    CONTINUITY_BREAK,
    apply_cfar_margin_gate,
    apply_continuity_rule,
    expected_false_harmonic_slots,
    summarize_high_n_guards,
)
from harmonic_peak_validation import (
    apply_exclusive_harmonic_assignment,
    apply_harmonic_body_stop,
    _classify_harmonic_candidate,
)
from metric_contract import get_metric_definition


def test_false_alarm_budget_and_contracts() -> None:
    assert expected_false_harmonic_slots(181, CFAR_PFA) == pytest.approx(1.81)
    assert HARMONIC_MIN_CFAR_MARGIN_DB == 3.0
    assert HARMONIC_CONTINUITY_RULE_ENABLED is False
    for name in (
        "expected_false_harmonic_slots",
        "accepted_slots_above_body_stop",
    ):
        defn = get_metric_definition(name)
        assert defn is not None


def test_cfar_marginal_is_excluded_from_density() -> None:
    status, include = _classify_harmonic_candidate(
        amplitude_raw=1.0,
        local_peak_valid=True,
        snr_db=10.0,
        prominence_db=10.0,
        cfar_detected=True,
        cfar_margin_db=1.5,
    )
    assert status == CFAR_MARGINAL
    assert include is False
    legacy, legacy_inc = _classify_harmonic_candidate(
        amplitude_raw=1.0,
        local_peak_valid=True,
        snr_db=10.0,
        prominence_db=10.0,
        cfar_detected=True,
    )
    assert legacy == "strict_validated"
    assert legacy_inc is True


def test_body_stop_off_a2_like_keeps_only_h1_h8() -> None:
    rows = []
    for n in range(1, 9):
        rows.append(
            {
                "Harmonic Number": n,
                "expected_frequency_hz": 110.0 * n,
                "Frequency (Hz)": 110.0 * n,
                "extracted_frequency_hz": 110.0 * n,
                "include_for_density": True,
                "candidate_status": "strict_validated",
                "cfar_margin_db": 20.0,
                "persistence_fraction": 1.0,
                "Magnitude (dB)": 20.0 - n,
                "snr_db": 25.0,
            }
        )
    for n, freq in ((109, 12011.6), (110, 12094.3), (111, 12191.7)):
        rows.append(
            {
                "Harmonic Number": n,
                "expected_frequency_hz": 110.0 * n,
                "Frequency (Hz)": freq,
                "extracted_frequency_hz": freq,
                "include_for_density": True,
                "candidate_status": "strict_validated",
                "cfar_margin_db": 1.2,
                "persistence_fraction": 0.25,
                "Magnitude (dB)": 5.0,
                "snr_db": 6.0,
            }
        )
    gated = apply_cfar_margin_gate(rows)
    assert sum(1 for r in gated if r.get("candidate_status") == CFAR_MARGINAL) >= 3
    for row in gated:
        if float(row.get("persistence_fraction", 1.0)) < 0.7:
            row["include_for_density"] = False
            if str(row.get("candidate_status")) != CFAR_MARGINAL:
                row["candidate_status"] = "low_temporal_persistence"
    stopped, meta = apply_harmonic_body_stop(
        gated,
        f0_hz=110.0,
        enabled=False,
        density_frequency_ceiling_hz=20000.0,
    )
    assert meta["harmonic_body_stop_triggered"] is False
    included = [int(r["Harmonic Number"]) for r in stopped if r.get("include_for_density")]
    assert included == list(range(1, 9))
    summary = summarize_high_n_guards(
        stopped, slot_count=181, body_stop_order=8
    )
    assert summary["accepted_slots_above_body_stop"] == 0
    assert summary["harmonic_acceptance_suspect"] is False
    assert summary["cfar_marginal_count"] >= 3


def test_accepted_above_stop_is_zero_after_gating() -> None:
    rows = []
    for n in range(1, 12):
        rows.append(
            {
                "Harmonic Number": n,
                "expected_frequency_hz": 110.0 * n,
                "Frequency (Hz)": 110.0 * n,
                "include_for_density": n <= 10,
                "candidate_status": "strict_validated" if n <= 10 else "below_noise_floor",
                "Magnitude (dB)": 20.0 if n <= 8 else 2.0,
                "snr_db": 20.0 if n <= 8 else 1.0,
                "cfar_margin_db": 12.0 if n <= 8 else 0.5,
            }
        )
    stopped, meta = apply_harmonic_body_stop(
        rows,
        f0_hz=110.0,
        enabled=True,
        density_frequency_ceiling_hz=20000.0,
    )
    stop_n = meta.get("harmonic_body_stop_order")
    summary = summarize_high_n_guards(
        stopped, slot_count=len(rows), body_stop_order=stop_n
    )
    assert summary["accepted_slots_above_body_stop"] == 0


def test_suspect_flag_when_accepted_exceeds_body_plus_budget() -> None:
    rows = [
        {
            "Harmonic Number": n,
            "include_for_density": True,
            "candidate_status": "strict_validated",
        }
        for n in range(1, 41)
    ]
    summary = summarize_high_n_guards(rows, slot_count=200, body_stop_order=8)
    assert summary["expected_false_harmonic_slots"] == pytest.approx(2.0)
    assert summary["accepted_slots_above_body_stop"] == 32
    assert summary["harmonic_acceptance_suspect"] is True


def test_continuity_off_by_default_and_freezes_when_enabled() -> None:
    rows = []
    for n in range(1, 12):
        included = n <= 4 or n >= 8
        rows.append(
            {
                "Harmonic Number": n,
                "include_for_density": included,
                "candidate_status": "strict_validated" if included else "below_noise_floor",
                "persistence_fraction": 0.5,
            }
        )
    off = apply_continuity_rule(rows, enabled=False)
    assert [r["include_for_density"] for r in off] == [
        r["include_for_density"] for r in rows
    ]
    on = apply_continuity_rule(rows, enabled=True, streak_k=3)
    included = [int(r["Harmonic Number"]) for r in on if r.get("include_for_density")]
    assert included == [1, 2, 3, 4]
    assert on[7]["candidate_status"] == CONTINUITY_BREAK
    persist_ok = [dict(r) for r in rows]
    persist_ok[7]["persistence_fraction"] = 0.95
    overridden = apply_continuity_rule(persist_ok, enabled=True, streak_k=3)
    assert overridden[7]["include_for_density"] is True


def test_body_stop_does_not_overwrite_cfar_marginal() -> None:
    rows = [
        {
            "Harmonic Number": 20,
            "expected_frequency_hz": 2200.0,
            "Frequency (Hz)": 2200.0,
            "include_for_density": False,
            "candidate_status": CFAR_MARGINAL,
            "exclusion_reason": "cfar_marginal (margin=1.20 dB < 3.0 dB)",
            "Magnitude (dB)": 5.0,
        }
    ]
    out, _meta = apply_harmonic_body_stop(
        rows,
        f0_hz=110.0,
        enabled=True,
        density_frequency_ceiling_hz=20000.0,
    )
    assert str(out[0]["exclusion_reason"]).startswith("cfar_marginal")
    assert out[0]["candidate_status"] == CFAR_MARGINAL


@pytest.mark.live_audio
def test_run2_duplicate_notes_pass_invariant_if_present() -> None:
    root = Path(
        r"D:\METAIS\TUBA\Tuba\Tuba_Yowa\IOWA_tuba_pp"
        r"\_Sustains_Stable\analysis_results_2"
    )
    if not root.is_dir():
        pytest.skip("run-2 workbooks not mounted")
    workbooks = list(root.rglob("spectral_analysis.xlsx"))
    assert workbooks, "run-2 folder exists but has no workbooks"
    scanned = 0
    for wb in workbooks:
        try:
            harm = pd.read_excel(wb, sheet_name="Harmonic Spectrum")
        except Exception:
            continue
        if harm.empty or "include_for_density" not in harm.columns:
            continue
        scanned += 1
        rows = harm.to_dict(orient="records")
        assigned = apply_exclusive_harmonic_assignment(rows)
        assigned = apply_cfar_margin_gate(assigned)
        f0_hz = 110.0
        try:
            meta_df = pd.read_excel(wb, sheet_name="Analysis_Metadata")
            mmap = dict(
                zip(meta_df["Parameter"].astype(str), meta_df["Value"])
            )
            for key in ("f0_used_for_density_hz", "f0_final", "f0"):
                try:
                    cand = float(mmap.get(key, float("nan")))
                except (TypeError, ValueError):
                    cand = float("nan")
                if cand == cand and cand > 0.0:
                    f0_hz = cand
                    break
        except Exception:
            pass
        stopped, meta = apply_harmonic_body_stop(
            assigned,
            f0_hz=f0_hz,
            enabled=True,
            density_frequency_ceiling_hz=20000.0,
        )
        check = validate_unique_peak_bin_assignment(pd.DataFrame(stopped))
        assert check["ok"] is True, (wb.name, check)
        stop_n = meta.get("harmonic_body_stop_order")
        summary = summarize_high_n_guards(
            stopped, slot_count=max(len(stopped), 1), body_stop_order=stop_n
        )
        assert summary["accepted_slots_above_body_stop"] == 0, wb.name
    assert scanned > 0


@pytest.mark.live_audio
def test_iowa_a2_body_stop_off_h1_h8_if_present(tmp_path: Path) -> None:
    audio = Path(
        r"D:\METAIS\TUBA\Tuba\Tuba_Yowa\IOWA_tuba_pp"
        r"\_Sustains_Stable\IOWA_Tub.pp.A2_SustainStable.aif"
    )
    if not audio.is_file():
        pytest.skip("A2 audio not mounted")
    from proc_audio import AudioProcessor

    ap = AudioProcessor()
    ap.load_audio_files([str(audio)])
    ap.apply_filters_and_generate_data(
        results_directory=tmp_path / "a2_phase16",
        n_fft=4096,
        hop_length=1024,
        zero_padding=1,
        freq_min=20.0,
        freq_max=20000.0,
        density_frequency_ceiling_hz=20000.0,
        harmonic_body_stop_enabled=False,
        dissonance_enabled=False,
        dissonance_curve=False,
        dissonance_scale=False,
        compare_models=False,
        compile_per_call=False,
        parallel_processing=False,
    )
    workbooks = list((tmp_path / "a2_phase16").rglob("spectral_analysis.xlsx"))
    assert workbooks
    harm = pd.read_excel(workbooks[0], sheet_name="Harmonic Spectrum")
    included = harm.loc[harm["include_for_density"].astype(bool)]
    orders = sorted(int(n) for n in included["Harmonic Number"].tolist())
    assert orders, "no included harmonics"
    assert max(orders) <= 8
    assert set(range(1, 7)).issubset(set(orders))
    high = harm.loc[pd.to_numeric(harm["Harmonic Number"], errors="coerce") >= 9]
    if not high.empty and "include_for_density" in high.columns:
        assert not high["include_for_density"].astype(bool).any()
    # H7/H8 sit near the 3 dB CFAR-margin floor on this 1.08 s take at
    # n_fft=4096; they may be cfar_marginal rather than strict.
    assert int(getattr(ap, "accepted_slots_above_body_stop", 1)) == 0
