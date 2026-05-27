from __future__ import annotations

import pandas as pd
import pytest

from acoustic_density_core import compute_acoustic_density_descriptors


def _synthetic_peaks() -> pd.DataFrame:
    # Construct a spectrum with clear harmonic, inharmonic, and subbass content.
    return pd.DataFrame(
        {
            "frequency_hz": [
                55.0,   # subbass candidate (< 0.75 * 110)
                110.0,  # harmonic 1
                220.0,  # harmonic 2
                330.0,  # harmonic 3
                500.0,  # inharmonic
                730.0,  # inharmonic
            ],
            "power": [
                0.10,
                10.0,
                6.0,
                4.0,
                2.0,
                0.8,
            ],
        }
    )


def test_pure_observation_is_invariant_to_prior() -> None:
    peaks = _synthetic_peaks()

    neutral_prior = compute_acoustic_density_descriptors(
        peaks,
        f0_hz=110.0,
        f0_fit_accepted=True,
        density_summation_mode="his_note_adaptive",
        harmonic_density_weight=1.0 / 3.0,
        inharmonic_density_weight=1.0 / 3.0,
        subbass_density_weight=1.0 / 3.0,
    )
    biased_prior = compute_acoustic_density_descriptors(
        peaks,
        f0_hz=110.0,
        f0_fit_accepted=True,
        density_summation_mode="his_note_adaptive",
        harmonic_density_weight=0.95,
        inharmonic_density_weight=0.04,
        subbass_density_weight=0.01,
    )

    # Canonical pure observation must be independent of caller-provided prior.
    assert neutral_prior["pure_observation_w_h"] == pytest.approx(
        biased_prior["pure_observation_w_h"], rel=0.0, abs=1e-12
    )
    assert neutral_prior["pure_observation_w_i"] == pytest.approx(
        biased_prior["pure_observation_w_i"], rel=0.0, abs=1e-12
    )
    assert neutral_prior["pure_observation_w_s"] == pytest.approx(
        biased_prior["pure_observation_w_s"], rel=0.0, abs=1e-12
    )

    # Backward-compatibility aliases now expose pure observation.
    assert neutral_prior["harmonic_density_weight"] == pytest.approx(
        neutral_prior["pure_observation_w_h"], rel=0.0, abs=1e-12
    )
    assert neutral_prior["inharmonic_density_weight"] == pytest.approx(
        neutral_prior["pure_observation_w_i"], rel=0.0, abs=1e-12
    )
    assert neutral_prior["subbass_density_weight"] == pytest.approx(
        neutral_prior["pure_observation_w_s"], rel=0.0, abs=1e-12
    )
