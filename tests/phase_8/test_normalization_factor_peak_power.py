from __future__ import annotations

import pytest

from spectral_normalization import n_fft_normalization_factor


def test_peak_power_sum_factor_scales_with_squared_nfft_ratio() -> None:
    f_4096 = n_fft_normalization_factor(
        n_fft=4096,
        n_fft_reference=8192,
        quantity_kind="peak_power_sum",
    )
    f_16384 = n_fft_normalization_factor(
        n_fft=16384,
        n_fft_reference=8192,
        quantity_kind="peak_power_sum",
    )
    assert f_4096 == pytest.approx(4.0, rel=0.0, abs=1e-12)
    assert f_16384 == pytest.approx(0.25, rel=0.0, abs=1e-12)
