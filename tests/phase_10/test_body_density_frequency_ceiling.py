from __future__ import annotations

import numpy as np
import pandas as pd

from acoustic_density_core import compute_acoustic_density_descriptors


def _build_peaks(*, high_scale: float) -> pd.DataFrame:
    rows: list[dict[str, float]] = []
    # Body-relevant partials (below configured body ceiling).
    for f, a in ((440.0, 1.0), (880.0, 0.6), (1320.0, 0.4), (1760.0, 0.3), (2640.0, 0.2), (3520.0, 0.15)):
        rows.append({"Frequency (Hz)": f, "Amplitude": a, "Power": a * a})
    # High-frequency components above body ceiling used to test invariance.
    for f, a in ((6000.0, 0.20 * high_scale), (9000.0, 0.12 * high_scale), (14000.0, 0.10 * high_scale)):
        rows.append({"Frequency (Hz)": f, "Amplitude": a, "Power": a * a})
    return pd.DataFrame(rows)


def test_body_density_ceiling_invariance_and_full_spectrum_sensitivity() -> None:
    body_ceiling_hz = 4800.0
    base = compute_acoustic_density_descriptors(
        _build_peaks(high_scale=1.0),
        f0_hz=440.0,
        body_freq_max_hz=body_ceiling_hz,
        density_frequency_ceiling_hz=body_ceiling_hz,
    )
    boosted_high = compute_acoustic_density_descriptors(
        _build_peaks(high_scale=6.0),
        f0_hz=440.0,
        body_freq_max_hz=body_ceiling_hz,
        density_frequency_ceiling_hz=body_ceiling_hz,
    )

    assert np.isclose(
        float(base["density_body_weighted_sum_body_ceiling"]),
        float(boosted_high["density_body_weighted_sum_body_ceiling"]),
        rtol=0.0,
        atol=1e-9,
    )
    assert np.isclose(
        float(base["harmonic_body_energy_sum_body_ceiling"]),
        float(boosted_high["harmonic_body_energy_sum_body_ceiling"]),
        rtol=0.0,
        atol=1e-9,
    )
    assert float(boosted_high["density_full_spectrum_weighted_sum_20khz"]) > float(
        base["density_full_spectrum_weighted_sum_20khz"]
    )
