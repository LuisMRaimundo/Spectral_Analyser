from __future__ import annotations

import math

import pytest

from spectral_normalization import n_fft_normalization_factor


def test_legacy_kind_keyword_still_works_with_deprecation_warning(recwarn: pytest.WarningsRecorder) -> None:
    val = n_fft_normalization_factor(n_fft=4096, n_fft_reference=8192, kind="amplitude")
    assert val == pytest.approx(math.sqrt(2.0), rel=0.0, abs=1e-12)
    assert any(
        issubclass(w.category, DeprecationWarning)
        and "quantity_kind" in str(w.message)
        for w in recwarn
    )
