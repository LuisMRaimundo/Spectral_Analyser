# -*- coding: utf-8 -*-
"""Legacy density sheet export and compile read path."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from compile_metrics import read_excel_metrics


def test_read_excel_metrics_merges_legacy_density_sheet(tmp_path: Path) -> None:
    path = tmp_path / "spectral_analysis.xlsx"
    metrics = pd.DataFrame(
        [
            {
                "Note": "A4",
                "canonical_density": 12.5,
                "weight_function": "log",
            }
        ]
    )
    legacy = pd.DataFrame(
        [
            {
                "Note": "A4",
                "weight_function": "log",
                "Density Metric": 12.5,
                "Spectral Density Metric": 45.0,
                "Filtered Density Metric": 3.2,
                "Combined Density Metric": 8.1,
                "spectral_masking_enabled": False,
            }
        ]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        metrics.to_excel(writer, sheet_name="Metrics", index=False)
        legacy.to_excel(writer, sheet_name="Legacy_Density_Metrics", index=False)

    out = read_excel_metrics(path)
    assert out["Spectral Density Metric"] == pytest.approx(45.0)
    assert out["Filtered Density Metric"] == pytest.approx(3.2)
    assert out["Combined Density Metric"] == pytest.approx(8.1)
    assert out["Density Metric"] == pytest.approx(12.5)


def test_build_legacy_density_metrics_row() -> None:
    from proc_audio import AudioProcessor

    ap = AudioProcessor()
    ap.note = "C4"
    ap.weight_function = "linear"
    ap.canonical_density_v5_adapted = 10.0
    ap.spectral_density_metric_value = 20.0
    ap.filtered_density_metric_value = 2.0
    ap.combined_density_metric_value = 5.0
    row = ap._build_legacy_density_metrics_row("C4")
    assert row["Spectral Density Metric"] == 20.0
    assert row["Filtered Density Metric"] == 2.0
    assert row["Combined Density Metric"] == 5.0
    assert row["Density Metric"] == 10.0
    assert row["spectral_masking_enabled"] is False
