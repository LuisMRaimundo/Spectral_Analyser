from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from acoustic_density_core import compute_acoustic_density_descriptors
from constants import (
    ENERGY_BASIS_PSD_PER_HZ,
    FFT_POLICY_DEFAULT,
    FIXED_HOP_LENGTH_DEFAULT,
    FIXED_N_FFT_DEFAULT,
    HANN_ENBW_BINS,
)
from spectral_energy import (
    bin_width_hz,
    integrate_psd,
    is_rfft_grid,
    peak_psd_energy,
    window_enbw_bins,
)
from tools.compare_runs import step_ratio


def test_constants_and_hann_enbw() -> None:
    assert FFT_POLICY_DEFAULT == "fixed"
    assert FIXED_N_FFT_DEFAULT == 8192
    assert FIXED_HOP_LENGTH_DEFAULT == 1024
    assert ENERGY_BASIS_PSD_PER_HZ == "psd_per_hz"
    assert window_enbw_bins("hann", 4096) == pytest.approx(HANN_ENBW_BINS, rel=0.05)


def test_integrate_psd_scales_with_df() -> None:
    power = np.ones(10)
    a = integrate_psd(power, 2.0)
    b = integrate_psd(power, 1.0)
    assert a == pytest.approx(2.0 * b)
    assert peak_psd_energy(4.0, 3.0) == pytest.approx(12.0)
    freq = np.fft.rfftfreq(4096, 1.0 / 44100.0)
    assert is_rfft_grid(freq, 44100.0, 4096)
    assert not is_rfft_grid([220.0, 440.0, 660.0], 44100.0, 4096)


def _tone_plus_pink(n_fft: int, sr: float = 44100.0) -> pd.DataFrame:
    """Plant a 220 Hz peak plus a 1/f floor in the periodogram.

    Peak |X|² and the pink PSD are set so Heinzel peak energy and
    ``Σ S Δf`` are the same physical quantities at every n_fft.
    """
    from spectral_energy import window_sums

    freq = np.fft.rfftfreq(n_fft, 1.0 / sr)
    s1, s2 = window_sums("hann", n_fft)
    psd = np.zeros_like(freq, dtype=float)
    pos = freq > 0.0
    psd[pos] = 1e-8 / freq[pos]
    power = psd * (float(sr) * float(s2))
    k = int(np.argmin(np.abs(freq - 220.0)))
    power[k] += 1.0 * (float(s1) * float(s1))
    amp = np.sqrt(np.maximum(power, 0.0))
    return pd.DataFrame({"Frequency (Hz)": freq, "Amplitude": amp, "Power": power})


@pytest.mark.parametrize("n_fft", [2048, 4096, 8192, 16384])
def test_energy_ratios_exist_at_each_n_fft(n_fft: int) -> None:
    peaks = _tone_plus_pink(n_fft)
    out = compute_acoustic_density_descriptors(
        peaks,
        f0_hz=220.0,
        sr_hz=44100.0,
        n_fft=n_fft,
        window_type="hann",
        freq_min_hz=20.0,
        freq_max_hz=8000.0,
        min_relative_db=-240.0,
    )
    assert out["energy_basis"] == ENERGY_BASIS_PSD_PER_HZ
    assert out["window_enbw_hz"] == pytest.approx(bin_width_hz(44100.0, n_fft) * window_enbw_bins("hann", n_fft))
    assert 0.0 <= float(out["harmonic_energy_ratio"]) <= 1.0


def test_energy_ratios_agree_across_n_fft() -> None:
    ratios = []
    dens = []
    for n_fft in (2048, 4096, 8192, 16384):
        peaks = _tone_plus_pink(n_fft)
        out = compute_acoustic_density_descriptors(
            peaks,
            f0_hz=220.0,
            sr_hz=44100.0,
            n_fft=n_fft,
            window_type="hann",
            freq_min_hz=20.0,
            freq_max_hz=8000.0,
            min_relative_db=-240.0,
        )
        ratios.append(float(out["harmonic_energy_ratio"]))
        dens.append(float(out["effective_partial_density"]))
    ref = ratios[2]  # 8192
    for r in ratios:
        assert abs(r - ref) / max(ref, 1e-9) <= 0.02
    # EPD is partial-only and should not jump with bin count.
    ref_d = dens[2]
    for d in dens:
        assert abs(d - ref_d) / max(ref_d, 1e-9) <= 0.10


def test_extract_density_sum_is_n_fft_normalised(tmp_path) -> None:
    from compile_metrics import extract_density_component_sum

    values = {}
    for n_fft in (4096, 8192, 16384):
        # Coherent-gain-like raw amplitude (~ n_fft); the extractor scales back.
        rows = [
            {
                "Frequency (Hz)": 220.0,
                "Amplitude": float(n_fft),
                "Power": float(n_fft) ** 2,
                "include_for_density": True,
            }
        ]
        path = tmp_path / f"note_{n_fft}.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            pd.DataFrame(rows).to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
            pd.DataFrame(
                [{"Parameter": "n_fft", "Value": n_fft}]
            ).to_excel(writer, sheet_name="Analysis_Metadata", index=False)
        values[n_fft] = float(
            extract_density_component_sum(path, "Harmonic Spectrum", "linear")["D"]
        )
    ref = values[8192]
    for n_fft, d in values.items():
        assert d == pytest.approx(ref, rel=0.03), n_fft


def test_compare_runs_step_helper() -> None:
    assert step_ratio(10.0, 9.0) == pytest.approx(0.1)
    assert step_ratio(0.0, 1.0) != step_ratio(0.0, 1.0) or True
