from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from compile_metrics import (
    _extract_band_amplitude_sum_for_density,
    _extract_band_power_sum_for_density,
    extract_density_component_sum,
    SUBBASS_SPECTRUM_SHEET_PREFERENCES,
)
from constants import EXPORT_COMPLETE_SPECTRUM_PITCH_NAMES
from metric_contract import get_metric_definition
from proc_audio import AudioProcessor, frequency_to_note_name
from subbass_policy import SubBassPolicy
from validated_partials import (
    SUBBASS_MEMBERSHIP_DIAGNOSTIC,
    SUBBASS_MEMBERSHIP_MEMBER,
    annotate_subbass_membership,
    attach_sample_identity_columns,
    count_floor_rows_rejected,
    count_subbass_members,
    gated_subbass_energy_sum,
    low_frequency_diagnostic_upper_hz,
    resolve_subbass_member_mask,
)


def _a2_like_subbass_sheet() -> pd.DataFrame:
    """Member at 40 Hz plus an F-020 diagnostic row at 90 Hz (f0 = 110)."""
    return pd.DataFrame(
        {
            "Frequency (Hz)": [40.0, 90.0],
            "Amplitude_raw": [0.5, 9.0],
            "Power_raw": [0.25, 81.0],
            "Low_Frequency_Class": [
                "subfundamental_residual",
                "physical_low_frequency_residual",
            ],
            "Note": ["A2", "A2"],
        }
    )


def test_f020_bound_for_a2_is_55_hz() -> None:
    assert SubBassPolicy.upper_bound_hz(110.0, 44100.0, 4096) == pytest.approx(55.0)
    assert low_frequency_diagnostic_upper_hz(110.0, 55.0) == pytest.approx(110.0)


def test_annotate_marks_diagnostic_row_and_drops_note_overload() -> None:
    tagged = annotate_subbass_membership(_a2_like_subbass_sheet(), f0_hz=110.0)
    tagged = attach_sample_identity_columns(
        tagged, sample_note_tag="A2", sample_id="iowa-tuba-a2"
    )
    assert "Note" not in tagged.columns
    assert list(tagged["sample_note_tag"]) == ["A2", "A2"]
    assert list(tagged["subbass_membership"]) == [
        SUBBASS_MEMBERSHIP_MEMBER,
        SUBBASS_MEMBERSHIP_DIAGNOSTIC,
    ]
    assert tagged["Acoustic_Interpretation_Status"].iloc[1] == SUBBASS_MEMBERSHIP_DIAGNOSTIC
    assert count_subbass_members(tagged, f0_hz=110.0) == 1
    assert gated_subbass_energy_sum(tagged.to_dict(orient="records"), f0_hz=110.0) == pytest.approx(
        0.25
    )


def test_floor_rows_rejected_count_is_not_a_partial_count() -> None:
    ih = pd.DataFrame(
        {
            "inharmonic_status": [
                "confirmed_inharmonic_partial",
                "rejected_floor",
                "rejected_floor",
                "rejected_leakage",
            ]
        }
    )
    assert count_floor_rows_rejected(ih) == 2
    assert get_metric_definition("floor_rows_rejected_count").input_domain != (
        "validated_partials_only"
    )
    assert get_metric_definition("harmonic_validated_count").input_domain == (
        "validated_partials_only"
    )
    assert get_metric_definition("inharmonic_confirmed_count").input_domain == (
        "confirmed_inharmonic_partials"
    )
    assert "partial count" in get_metric_definition(
        "harmonic_slot_candidate_count"
    ).not_valid_for.lower() or "validated" in get_metric_definition(
        "harmonic_slot_candidate_count"
    ).not_valid_for.lower()


def test_f020_diagnostic_row_contributes_zero_to_s_sums(tmp_path: Path) -> None:
    rows = annotate_subbass_membership(_a2_like_subbass_sheet(), f0_hz=110.0)
    wb = tmp_path / "subbass_hygiene.xlsx"
    with pd.ExcelWriter(wb, engine="openpyxl") as writer:
        rows.to_excel(writer, sheet_name="Sub-bass band", index=False)
        pd.DataFrame(
            {
                "Frequency (Hz)": [110.0],
                "Amplitude_raw": [1.0],
                "Power_raw": [1.0],
                "include_for_density": [True],
            }
        ).to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
        pd.DataFrame(
            {"Frequency (Hz)": [333.0], "Amplitude_raw": [0.1], "Power_raw": [0.01]}
        ).to_excel(writer, sheet_name="Inharmonic Spectrum", index=False)
        pd.DataFrame([{"Note": "A2", "f0_used_for_density_hz": 110.0}]).to_excel(
            writer, sheet_name="Metrics", index=False
        )

    linear = extract_density_component_sum(wb, "Sub-bass band", "linear")
    power = extract_density_component_sum(wb, "Sub-bass band", "power")
    assert linear["inclusion_policy"] == "subbass_members_only"
    assert linear["excluded_count"] == 1
    assert float(linear["D"]) == pytest.approx(0.5)
    assert float(power["D"]) == pytest.approx(0.25)

    xf = pd.ExcelFile(wb)
    amp_sum, amp_n, amp_src = _extract_band_amplitude_sum_for_density(
        xf, list(xf.sheet_names), SUBBASS_SPECTRUM_SHEET_PREFERENCES, label="subbass"
    )
    pow_sum, pow_n, pow_src = _extract_band_power_sum_for_density(
        xf, list(xf.sheet_names), SUBBASS_SPECTRUM_SHEET_PREFERENCES, label="subbass"
    )
    xf.close()
    assert amp_sum == pytest.approx(0.5)
    assert amp_n == 1
    assert pow_sum == pytest.approx(0.25)
    assert pow_n == 1
    assert "subbass_members_only" in amp_src
    assert "subbass_members_only" in pow_src


def test_legacy_subbass_sheet_without_membership_stays_unfiltered(tmp_path: Path) -> None:
    wb = tmp_path / "legacy_subbass.xlsx"
    pd.DataFrame(
        {"Frequency (Hz)": [70.0], "Amplitude_raw": [2.0], "Power_raw": [4.0]}
    ).to_excel(wb, sheet_name="Sub-bass band", index=False)
    out = extract_density_component_sum(wb, "Sub-bass band", "power")
    assert float(out["D"]) == pytest.approx(4.0)
    assert out["inclusion_policy"] == "all_rows_no_membership_column"


def test_complete_spectrum_pitch_names_default_off() -> None:
    assert EXPORT_COMPLETE_SPECTRUM_PITCH_NAMES is False
    ap = AudioProcessor()
    assert ap.export_complete_spectrum_pitch_names is False


def test_partial_pitch_name_is_not_the_sample_tag() -> None:
    assert frequency_to_note_name(110.0).startswith("A2")
    pitch_90 = frequency_to_note_name(90.0)
    assert pitch_90
    assert not pitch_90.startswith("A2")
    mask, policy, excluded = resolve_subbass_member_mask(
        annotate_subbass_membership(_a2_like_subbass_sheet(), f0_hz=110.0),
        f0_hz=110.0,
    )
    assert policy == "subbass_members_only"
    assert excluded == 1
    assert list(mask) == [True, False]
