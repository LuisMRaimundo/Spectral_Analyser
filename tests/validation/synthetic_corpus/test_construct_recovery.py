from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from constants import CONSTRUCT_B_REL_TOL, CONSTRUCT_EPD_REL_TOL, CONSTRUCT_N_ABS_TOL
from tests.validation.synthetic_corpus.generate import (
    CONSTRUCT_SNR_LEVELS_DB,
    iter_constructs,
    synthesize_waveform,
)
from tests.validation.synthetic_corpus.recover import (
    build_markdown_table,
    recover_construct,
    recover_table,
)


def test_snr_levels_are_the_acceptance_set() -> None:
    assert tuple(CONSTRUCT_SNR_LEVELS_DB) == (10, 20, 30, 40)


@pytest.mark.parametrize("spec", list(iter_constructs()), ids=lambda s: s.name)
def test_construct_recovers_n_b_epd_and_confirmed_i(spec) -> None:
    rec = recover_construct(spec)
    assert abs(int(rec["n_hat"]) - int(rec["n_true"])) <= CONSTRUCT_N_ABS_TOL
    if spec.family == "stiff":
        assert rec["b_hat"] == pytest.approx(
            spec.b_true, rel=CONSTRUCT_B_REL_TOL, abs=0.0
        )
    else:
        assert abs(float(rec["b_hat"])) < 1.5e-4
    assert rec["epd_hat"] == pytest.approx(
        rec["epd_true"], rel=CONSTRUCT_EPD_REL_TOL, abs=0.0
    )
    assert int(rec["confirmed_i_hat"]) == int(rec["confirmed_i_true"])


def test_waveform_generator_is_finite_and_unit_peak() -> None:
    spec = next(iter_constructs())
    y = synthesize_waveform(spec, duration_s=0.2, seed=1)
    assert y.size > 100
    assert np.isfinite(y).all()
    assert abs(float(np.max(np.abs(y))) - 1.0) < 1e-9


def test_recovery_table_covers_twelve_conditions() -> None:
    df = recover_table()
    assert len(df) == 12
    assert set(df["family"]) == {"harmonic", "stiff", "bell"}
    markdown = build_markdown_table(df)
    assert "Acceptance: N ±1" in markdown
    report = Path("docs/validation/CONSTRUCT_VALIDATION_SYNTHETIC.md")
    if report.is_file():
        text = report.read_text(encoding="utf-8")
        assert "N ±1" in text
        assert "confirmed-I" in text or "I hat" in text
