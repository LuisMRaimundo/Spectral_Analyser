from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest

from tools.ewsd_pure import (
    ACOUSTIC_BALANCE_ALPHA_DEFAULT,
    ewsd_from_compartment_summaries,
)
from tools.ewsd_research_integration import compute_ewsd_dataframe_from_analysis_root

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "ewsd_corpus_reference.json"
DEFAULT_CORPUS_ROOT = Path(
    r"C:\Users\lmr20\Desktop\ORC_Vlc_arco_mf\_Sustains\analysis_results"
)
DEFAULT_REFERENCE_XLSX = Path(
    r"C:\Users\lmr20\Desktop\ORC_Vlc_arco_mf\_Sustains\ewsd_ratio_respecting_results.xlsx"
)
CORPUS_FREQUENCY_CEILING_HZ = 20000.0


def _corpus_root() -> Path | None:
    env = os.environ.get("EWSD_CORPUS_ROOT", "").strip()
    if env:
        path = Path(env).expanduser()
        return path if path.is_dir() else None
    return DEFAULT_CORPUS_ROOT if DEFAULT_CORPUS_ROOT.is_dir() else None


@pytest.fixture(scope="module")
def corpus_reference() -> dict:
    assert FIXTURE_PATH.is_file(), f"missing committed corpus fixture: {FIXTURE_PATH}"
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_committed_corpus_reference_internal_consistency(corpus_reference: dict) -> None:
    notes = corpus_reference["notes"]
    assert len(notes) == 49

    for row in notes:
        strict, balanced = ewsd_from_compartment_summaries(
            row["compartments"],
            alpha=ACOUSTIC_BALANCE_ALPHA_DEFAULT,
        )
        assert strict == pytest.approx(row["EWSD_score_total"], abs=1e-10)
        assert balanced == pytest.approx(row["EWSD_score_acoustic_balanced"], abs=1e-10)
        assert row["primary_analysis_eligible"] is True


@pytest.mark.skipif(_corpus_root() is None, reason="EWSD corpus analysis folder not available")
def test_live_corpus_recompute_matches_reference_xlsx(corpus_reference: dict) -> None:
    root = _corpus_root()
    assert root is not None

    reference_path = Path(os.environ.get("EWSD_REFERENCE_XLSX", str(DEFAULT_REFERENCE_XLSX)))
    if not reference_path.is_file():
        pytest.skip(f"reference workbook not found: {reference_path}")

    expected = pd.read_excel(reference_path, sheet_name="EWSD_Main")
    computed = compute_ewsd_dataframe_from_analysis_root(
        root,
        frequency_ceiling_hz=CORPUS_FREQUENCY_CEILING_HZ,
        acoustic_balance_alpha=ACOUSTIC_BALANCE_ALPHA_DEFAULT,
    )

    merged = expected[["Note", "EWSD_score_total", "EWSD_score_acoustic_balanced"]].merge(
        computed[["Note", "ewsd_score", "ewsd_score_acoustic_balanced"]],
        on="Note",
        how="inner",
        validate="one_to_one",
    )
    assert len(merged) == len(expected) == 49

    dt = (merged["EWSD_score_total"] - merged["ewsd_score"]).abs()
    db = (merged["EWSD_score_acoustic_balanced"] - merged["ewsd_score_acoustic_balanced"]).abs()
    assert float(dt.max()) <= 1e-9
    assert float(db.max()) <= 1e-9

    fixture_by_note = {str(r["Note"]): r for r in corpus_reference["notes"]}
    for _, row in merged.iterrows():
        note = str(row["Note"])
        ref = fixture_by_note[note]
        assert float(row["ewsd_score"]) == pytest.approx(ref["EWSD_score_total"], abs=1e-9)
