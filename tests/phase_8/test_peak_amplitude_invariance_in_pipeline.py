from __future__ import annotations

from pathlib import Path

import pytest

from tests.phase_8.helpers import run_single_note_pipeline_and_read_compiled


def test_peak_amplitude_sum_tier_normalized_is_fft_invariant_in_pipeline(tmp_path: Path) -> None:
    dm_4096 = run_single_note_pipeline_and_read_compiled(tmp_path, n_fft=4096)
    dm_8192 = run_single_note_pipeline_and_read_compiled(tmp_path, n_fft=8192)

    v_4096 = float(dm_4096.iloc[0]["harmonic_amplitude_sum_tier_normalized"])
    v_8192 = float(dm_8192.iloc[0]["harmonic_amplitude_sum_tier_normalized"])

    assert v_4096 == pytest.approx(v_8192, rel=0.05, abs=0.0)
