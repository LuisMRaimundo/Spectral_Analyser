from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from proc_audio import _harmonic_inclusion_audit_exclusion_reason
from tests.phase_7_1b.helpers import run_stage1_synthetic_notes

AUDIT_COLUMNS = {
    "harmonic_number",
    "expected_frequency_hz",
    "extracted_frequency_hz",
    "frequency_deviation_hz",
    "frequency_deviation_cents",
    "magnitude_db",
    "power_raw",
    "snr_db",
    "prominence_db",
    "local_peak_valid",
    "candidate_status",
    "include_for_density",
    "included_in_strict_peaks",
    "included_in_body_density_5khz",
    "exclusion_reason",
    "search_ceiling_hz",
    "body_density_ceiling_hz",
}


def test_harmonic_inclusion_audit_exclusion_reason_included() -> None:
    reason = _harmonic_inclusion_audit_exclusion_reason(
        include_for_density=True,
        expected_frequency_hz=440.0,
        frequency_deviation_hz=0.0,
        candidate_status="strict_validated",
        local_peak_valid=True,
        snr_db=6.0,
        prominence_db=6.0,
    )
    assert reason == "included"


def test_harmonic_inclusion_audit_exclusion_reason_off_frequency() -> None:
    reason = _harmonic_inclusion_audit_exclusion_reason(
        include_for_density=False,
        expected_frequency_hz=900.0,
        frequency_deviation_hz=12.0,
        candidate_status="off_frequency",
        local_peak_valid=True,
        snr_db=8.0,
        prominence_db=8.0,
    )
    assert reason.startswith("off_frequency")


def test_per_note_workbook_exports_harmonic_inclusion_audit(tmp_path: Path) -> None:
    workbooks = run_stage1_synthetic_notes(tmp_path, notes=[("A4", 440.0)])
    wb = workbooks[0]
    audit = pd.read_excel(wb, sheet_name="Harmonic_Inclusion_Audit")
    assert not audit.empty
    assert AUDIT_COLUMNS.issubset(set(audit.columns))
    assert audit["exclusion_reason"].notna().all()
    assert audit["search_ceiling_hz"].notna().all()
    assert audit["body_density_ceiling_hz"].notna().all()

    meta = pd.read_excel(wb, sheet_name="Analysis_Metadata")
    meta_map = dict(zip(meta.iloc[:, 0], meta.iloc[:, 1]))
    assert int(meta_map.get("harmonic_density_included_count", 0)) == int(
        audit["include_for_density"].astype(bool).sum()
    )
