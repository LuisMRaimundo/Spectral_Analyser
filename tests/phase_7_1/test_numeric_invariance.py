from __future__ import annotations

from numbers import Number

import numpy as np
import pandas as pd
import pytest

import acoustic_density_core as adc


def _synthetic_peaks(f0_hz: float) -> pd.DataFrame:
    freqs = [
        f0_hz,
        2.0 * f0_hz,
        3.0 * f0_hz,
        4.0 * f0_hz,
        1.31 * f0_hz,
        0.38 * f0_hz,
    ]
    powers = [1.0, 0.5, 0.25, 0.12, 0.02, 0.015]
    return pd.DataFrame({"frequency_hz": freqs, "power": powers})


def _assert_numeric_dicts_bit_identical(left: dict, right: dict) -> None:
    shared_keys = sorted(set(left.keys()) & set(right.keys()))
    for key in shared_keys:
        lv = left[key]
        rv = right[key]
        if isinstance(lv, bool) or isinstance(rv, bool):
            continue
        if not isinstance(lv, Number) or not isinstance(rv, Number):
            continue
        lf = float(lv)
        rf = float(rv)
        if np.isnan(lf) and np.isnan(rf):
            continue
        assert lf == rf, f"numeric mismatch at {key}: {lf!r} vs {rf!r}"


def test_subbass_direct_call_refactor_is_numeric_invariant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    peaks = _synthetic_peaks(220.0)

    baseline = adc.compute_acoustic_density_descriptors(
        peaks,
        f0_hz=220.0,
        f0_fit_accepted=True,
        density_summation_mode="his_note_adaptive",
        sr_hz=44100.0,
        n_fft=4096,
    )

    original_upper_bound = adc.SubBassPolicy.upper_bound_hz

    def _emulate_deprecated_operational_path(*, f0_hz: float, sr_hz: float, n_fft: int) -> float:
        # Pre-7.1 canonical path called deprecated wrapper, which delegated to
        # SubBassPolicy using n_fft=0 at the call site.
        return float(
            original_upper_bound(
                f0_hz=float(f0_hz),
                sr_hz=float(sr_hz),
                n_fft=0,
            )
        )

    monkeypatch.setattr(adc.SubBassPolicy, "upper_bound_hz", _emulate_deprecated_operational_path)

    emulated_old_path = adc.compute_acoustic_density_descriptors(
        peaks,
        f0_hz=220.0,
        f0_fit_accepted=True,
        density_summation_mode="his_note_adaptive",
        sr_hz=44100.0,
        n_fft=4096,
    )

    _assert_numeric_dicts_bit_identical(baseline, emulated_old_path)
