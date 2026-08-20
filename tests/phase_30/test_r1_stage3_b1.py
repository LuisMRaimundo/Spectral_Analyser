"""R1: Stage-3 B1 reader uses the compiled research workbook only."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tools.r1_stage3_b1 import KEYS, _rel_spread, read_stage3_compiled


def test_read_stage3_compiled_requires_research_workbook(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_stage3_compiled(tmp_path)


def test_read_stage3_compiled_ignores_stage1_metrics(tmp_path: Path) -> None:
    note = tmp_path / "note"
    note.mkdir()
    pd.DataFrame(
        [
            {
                "EWSD_score_acoustic_balanced": 6.7,
                "core_harmonic_energy_ratio": 0.05,
                "effective_partial_density": 1.1,
            }
        ]
    ).to_excel(note / "spectral_analysis.xlsx", sheet_name="Metrics", index=False)
    with pytest.raises(FileNotFoundError):
        read_stage3_compiled(tmp_path)


def test_read_stage3_compiled_from_research_sheet(tmp_path: Path) -> None:
    research = tmp_path / "compiled_density_metrics_research.xlsx"
    pd.DataFrame(
        [
            {
                "EWSD_score_acoustic_balanced": 91.31,
                "core_harmonic_energy_ratio": 0.9222,
                "effective_partial_density": 4.5,
            }
        ]
    ).to_excel(research, sheet_name="Spectral_Density_Metrics", index=False)
    row = read_stage3_compiled(tmp_path)
    assert set(row) == set(KEYS)
    assert row["EWSD_score_acoustic_balanced"] == pytest.approx(91.31)
    assert row["core_harmonic_energy_ratio"] == pytest.approx(0.9222)
    assert row["effective_partial_density"] == pytest.approx(4.5)


def test_rel_spread_three_percent() -> None:
    assert _rel_spread([0.9222, 0.9222, 0.9300], 0.9222, 0.03)
    assert not _rel_spread([0.9222, 0.7878], 0.9222, 0.03)
