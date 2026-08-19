from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tools.perceptual_agreement import agreement_report, spearman_rank_agreement, win_scores
from tools.perceptual_pairs import (
    RESPONSE_COLUMNS,
    STIMULI_COLUMNS,
    build_adjacent_pairs,
    write_response_template,
    write_stimuli_list,
)


def test_pairwise_schema_and_template(tmp_path: Path) -> None:
    notes = ["C2", "E2", "A2", "C3"]
    pairs = build_adjacent_pairs(notes)
    assert ("C2", "E2") in pairs
    assert ("C2", "C3") in pairs
    stimuli = write_stimuli_list(
        [
            {
                "note_id": n,
                "source_path": "",
                "ewsd_score_acoustic_balanced": i,
                "register": "",
                "dynamic": "",
            }
            for i, n in enumerate(notes)
        ],
        tmp_path / "stimuli_list.csv",
    )
    template = write_response_template(pairs, tmp_path / "response_template.csv")
    stim = pd.read_csv(stimuli)
    resp = pd.read_csv(template)
    assert list(stim.columns) == list(STIMULI_COLUMNS)
    assert list(resp.columns) == list(RESPONSE_COLUMNS)
    assert resp["denser_choice"].fillna("").eq("").all()


def test_agreement_is_perfect_when_listener_follows_ewsd() -> None:
    ewsd = pd.Series({"C2": 40.0, "E2": 30.0, "A2": 20.0, "C3": 10.0})
    rows = []
    notes = list(ewsd.index)
    for i, a in enumerate(notes):
        for b in notes[i + 1 :]:
            denser = a if ewsd[a] >= ewsd[b] else b
            rows.append({"note_a": a, "note_b": b, "denser_choice": denser})
    report = agreement_report(pd.DataFrame(rows), ewsd)
    assert report["spearman_rho"] == pytest.approx(1.0)
    shuffled = pd.Series({"C2": 10.0, "E2": 40.0, "A2": 20.0, "C3": 30.0})
    rho = spearman_rank_agreement(win_scores(pd.DataFrame(rows)), shuffled)
    assert rho < 1.0


def test_readme_states_ewsd_is_acoustic_until_listener_study() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "acoustic until" in readme.lower() or (
        "ewsd is acoustic" in readme.lower() and "listener" in readme.lower()
    )
    protocol = Path("docs/validation/PERCEPTUAL_PROTOCOL.md")
    assert protocol.is_file()
    text = protocol.read_text(encoding="utf-8")
    assert "no data collection" in text.lower()
