"""R4 — estimated_snr_db and EPD-primary documentation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from estimated_snr import estimated_snr_db_from_harmonics
from metric_contract import get_metric_definition


def test_power_weighted_mean_snr() -> None:
    df = pd.DataFrame(
        {
            "include_for_density": [True, True, False],
            "snr_db": [10.0, 20.0, 99.0],
            "Power_raw": [3.0, 1.0, 100.0],
        }
    )
    assert estimated_snr_db_from_harmonics(df) == pytest.approx((3 * 10 + 1 * 20) / 4)


def test_empty_or_missing_is_nan() -> None:
    assert pd.isna(estimated_snr_db_from_harmonics(None))
    assert pd.isna(estimated_snr_db_from_harmonics(pd.DataFrame()))
    assert pd.isna(estimated_snr_db_from_harmonics(pd.DataFrame({"x": [1]})))
    none_included = pd.DataFrame(
        {
            "include_for_density": [False, False],
            "snr_db": [10.0, 20.0],
            "Power_raw": [1.0, 1.0],
        }
    )
    assert pd.isna(estimated_snr_db_from_harmonics(none_included))


def test_boolean_include_and_amplitude_weights() -> None:
    df = pd.DataFrame(
        {
            "include_for_density": [True, False],
            "snr_db": [12.0, 80.0],
            "Amplitude_raw": [2.0, 10.0],
        }
    )
    assert estimated_snr_db_from_harmonics(df) == pytest.approx(12.0)


def test_metric_contract_registers_estimated_snr() -> None:
    defn = get_metric_definition("estimated_snr_db")
    assert defn is not None
    assert defn.unit_or_scale == "dB"
    assert "peak" in defn.formula


def test_docs_name_epd_primary_and_b7() -> None:
    construct = Path("docs/validation/EWSD_CONSTRUCT_VALIDITY.md").read_text(
        encoding="utf-8"
    )
    assert "### SNR dependence (measured)" in construct
    assert "Primary noise-robust density" in construct
    assert "8.7668" in construct
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "primary noise-robust density" in readme
    findings = Path("docs/validation/PRETAG_FINDINGS_SUMMARY.md").read_text(
        encoding="utf-8"
    )
    assert "partially SNR-mediated" in findings
    assert "6.68 / 9.03 / 13.27" in findings
