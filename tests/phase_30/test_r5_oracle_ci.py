"""R5 — planted-amplitude oracle and frame-count C2."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tools.ewsd_pure import CompartmentInputs, compute_note_ewsd
from tools.r5_oracle_ci import (
    FRAME_COUNTS,
    N_PARTIALS,
    oracle_from_planted,
    planted_amplitudes,
    planted_frequencies,
    run_c1,
    run_c2,
)
from validated_partials import participation_ratio_from_amplitudes


def test_oracle_is_ewsd_pure_not_bootstrap() -> None:
    amps = planted_amplitudes()
    freqs = planted_frequencies()
    oracle = oracle_from_planted(amps, freqs)
    direct = compute_note_ewsd(
        [
            CompartmentInputs(
                values=amps,
                analysis_ratio=1.0,
                frequencies_hz=freqs,
                weight_function="log",
                apply_anti_concentration=True,
            )
        ]
    )
    assert oracle["ewsd_score_acoustic_balanced"] == pytest.approx(
        float(direct["ewsd_score_acoustic_balanced"])
    )
    assert oracle["note_effective_component_density"] == pytest.approx(
        participation_ratio_from_amplitudes(list(amps))
    )


def test_c1_uses_external_oracle() -> None:
    c1 = run_c1(n=20, n_boot=40, seed=20260820)
    assert c1["n"] == 20
    assert c1["n_partials"] == N_PARTIALS
    assert c1["oracle_source"] == "planted_amplitudes_ewsd_pure"
    assert "planted-amplitude oracle" in c1["note"]
    assert 0.0 <= c1["ewsd_coverage_pct"] <= 100.0
    assert 0.0 <= c1["epd_coverage_pct"] <= 100.0


def test_c2_varies_frames_not_partials() -> None:
    c2 = run_c2(n_trials=4, n_boot=30, seed=20260820)
    ns = [r["n_frames"] for r in c2["rows"]]
    assert ns == list(FRAME_COUNTS)
    assert all(r["n_partials"] == N_PARTIALS for r in c2["rows"])
    assert np.isfinite(c2["loglog_slope"])
    # Width must be able to shrink: at least one doubling does not grow.
    widths = [r["width"] for r in c2["rows"]]
    assert any(widths[i + 1] <= widths[i] * 1.05 for i in range(len(widths) - 1))


def test_docs_have_r5_addendum() -> None:
    report = Path("docs/validation/MEASUREMENT_PERFORMANCE_REPORT.md").read_text(
        encoding="utf-8"
    )
    assert "## Addendum — 20 August 2026 (R5; scores not rewritten)" in report
    assert "planted-amplitude oracle" in report
    assert "100.0 %" in report
    assert "−0.281" in report
    construct = Path("docs/validation/EWSD_CONSTRUCT_VALIDITY.md").read_text(
        encoding="utf-8"
    )
    assert "empirically **100 %**" in construct
    assert "−0.281" in construct
    status = Path("docs/validation/UPGRADE_PROGRAMME_STATUS.md").read_text(
        encoding="utf-8"
    )
    assert "R5" in status
    assert "R2–R6" in status
