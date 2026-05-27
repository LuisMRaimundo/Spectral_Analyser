from __future__ import annotations

from tests.phase_3.test_tier_normalisation_invariance import (
    test_tier_normalized_amplitude_sum_is_fft_invariant_within_2_percent,
)


def test_phase3_tier_normalisation_invariance_test_still_passes() -> None:
    # Backward-compatibility guard: the legacy Phase-3 property is intentionally
    # preserved through the compatibility mapping in spectral_normalization.
    test_tier_normalized_amplitude_sum_is_fft_invariant_within_2_percent()
