"""WP1 — residual exclusion is the window main-lobe, not ENBW."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from acoustic_density_core import compute_acoustic_density_descriptors
from constants import RESIDUAL_EXCLUSION_FOOTPRINT
from inharmonic_confirmation import _leakage_guard
from spectral_energy import (
    analysis_band_regions_hz,
    peak_power_footprint_bins,
    peak_psd_energy,
    residual_exclusion_footprint_bins,
    residual_exclusion_hz,
    window_enbw_bins,
    window_sums,
)
from spectral_leakage_guards import DEFAULT_MAIN_LOBE_WIDTH_BINS, leakage_halfwidth_hz


def _windowed_sinusoid(
    n_fft: int,
    *,
    f0: float = 220.0,
    sr: float = 44100.0,
    window: str = "hann",
) -> pd.DataFrame:
    t = np.arange(int(n_fft), dtype=float) / float(sr)
    x = np.sin(2.0 * np.pi * float(f0) * t)
    try:
        from scipy.signal import get_window

        w = np.asarray(get_window(window, int(n_fft), fftbins=True), dtype=float)
    except Exception:
        w = np.hanning(int(n_fft))
    spec = np.fft.rfft(x * w)
    freq = np.fft.rfftfreq(int(n_fft), 1.0 / float(sr))
    power = np.abs(spec) ** 2
    amp = np.sqrt(np.maximum(power, 0.0))
    return pd.DataFrame({"Frequency (Hz)": freq, "Amplitude": amp, "Power": power})


def _tone_plus_pink_known_snr(
    n_fft: int,
    *,
    f0: float = 220.0,
    sr: float = 44100.0,
    window: str = "hann",
    pink_amp: float = 1e-8,
) -> tuple[pd.DataFrame, float]:
    """Plant one peak plus a 1/f floor. Return (peaks, residual share GT)."""
    freq = np.fft.rfftfreq(int(n_fft), 1.0 / float(sr))
    s1, s2 = window_sums(window, int(n_fft))
    psd = np.zeros_like(freq, dtype=float)
    pos = freq > 0.0
    psd[pos] = float(pink_amp) / freq[pos]
    power = psd * (float(sr) * float(s2))
    k = int(np.argmin(np.abs(freq - float(f0))))
    power[k] += 1.0 * (float(s1) * float(s1))
    amp = np.sqrt(np.maximum(power, 0.0))
    peaks = pd.DataFrame({"Frequency (Hz)": freq, "Amplitude": amp, "Power": power})

    excl = residual_exclusion_hz(window, float(sr), int(n_fft))
    residual, excluded, band = analysis_band_regions_hz(20.0, 8000.0, [float(f0)], excl)
    assert residual + excluded == pytest.approx(band)
    keep = (freq >= 20.0) & (freq <= 8000.0) & (np.abs(freq - float(f0)) > 0.5 * excl)
    from spectral_energy import integrate_psd, bin_width_hz

    df = bin_width_hz(float(sr), int(n_fft))
    r_energy = integrate_psd(
        power[keep], df, sr_hz=float(sr), n_fft=int(n_fft), window=window
    )
    h_energy = peak_psd_energy(float(power[k]), 1.0, window=window, n_fft=int(n_fft))
    gt = float(r_energy / (r_energy + h_energy)) if (r_energy + h_energy) > 0.0 else 0.0
    return peaks, gt


def test_exclusion_wider_than_enbw() -> None:
    assert RESIDUAL_EXCLUSION_FOOTPRINT == 8.0
    assert residual_exclusion_footprint_bins("blackmanharris") == 8.0
    assert residual_exclusion_footprint_bins("hann") == 4.0
    assert DEFAULT_MAIN_LOBE_WIDTH_BINS == 8.0
    enbw = window_enbw_bins("blackmanharris", 8192)
    assert residual_exclusion_footprint_bins("blackmanharris") > enbw
    assert peak_power_footprint_bins("hann", 4096) == pytest.approx(
        window_enbw_bins("hann", 4096)
    )


def test_region_invariant_fail_closed() -> None:
    residual, excluded, band = analysis_band_regions_hz(
        20.0, 20000.0, [220.0, 440.0, 660.0], 40.0
    )
    assert residual + excluded == pytest.approx(band)
    assert band == pytest.approx(19980.0)
    assert residual <= band
    assert excluded <= band
    assert residual_region_plus_excluded_is_band()


def residual_region_plus_excluded_is_band() -> bool:
    residual, excluded, band = analysis_band_regions_hz(0.0, 100.0, [50.0], 1000.0)
    return residual + excluded == pytest.approx(band) and residual == 0.0


@pytest.mark.parametrize("n_fft", [2048, 4096, 8192, 16384])
def test_single_sinusoid_residual_share_below_one_percent(n_fft: int) -> None:
    peaks = _windowed_sinusoid(n_fft)
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
    assert float(out["residual_energy_ratio"]) < 0.01
    resid = float(out["residual_region_hz_total"])
    excl = float(out["excluded_region_hz_total"])
    band = float(out["analysis_band_hz"])
    assert resid + excl == pytest.approx(band, abs=1e-6)
    assert resid <= band
    assert float(out["residual_exclusion_footprint_bins"]) == 4.0
    assert float(out["peak_power_footprint_bins"]) == pytest.approx(
        window_enbw_bins("hann", n_fft)
    )


@pytest.mark.parametrize("n_fft", [2048, 4096, 8192, 16384])
def test_tone_plus_pink_residual_share_matches_ground_truth(n_fft: int) -> None:
    peaks, gt = _tone_plus_pink_known_snr(n_fft)
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
    got = float(out["residual_energy_ratio"])
    assert abs(got - gt) <= 0.02


def test_as2_h1_skirt_is_leakage() -> None:
    """131.9 Hz next to trombone A♯2 H1 (116.54 Hz) at 8192 is a skirt."""
    not_leakage, order = _leakage_guard(
        131.9,
        [{"frequency_hz": 116.54, "harmonic_order": 1}],
        sr=44100.0,
        n_fft=8192,
        bin_width_hz=None,
    )
    assert not_leakage is False
    assert order == 1
    hw = leakage_halfwidth_hz(sr=44100.0, n_fft=8192)
    assert hw == pytest.approx(0.5 * 8.0 * (44100.0 / 8192.0))


def test_confirmed_i_excluded_from_residual() -> None:
    n_fft = 4096
    peaks = _windowed_sinusoid(n_fft, f0=220.0)
    freq = peaks["Frequency (Hz)"].to_numpy(dtype=float)
    power = peaks["Power"].to_numpy(dtype=float)
    k = int(np.argmin(np.abs(freq - 1500.0)))
    power[k] += float(np.max(power)) * 0.05
    peaks = peaks.copy()
    peaks["Power"] = power
    peaks["Amplitude"] = np.sqrt(np.maximum(power, 0.0))
    bare = compute_acoustic_density_descriptors(
        peaks,
        f0_hz=220.0,
        sr_hz=44100.0,
        n_fft=n_fft,
        window_type="hann",
        freq_min_hz=20.0,
        freq_max_hz=8000.0,
        min_relative_db=-240.0,
    )
    gated = compute_acoustic_density_descriptors(
        peaks,
        f0_hz=220.0,
        sr_hz=44100.0,
        n_fft=n_fft,
        window_type="hann",
        freq_min_hz=20.0,
        freq_max_hz=8000.0,
        min_relative_db=-240.0,
        confirmed_inharmonic_freqs_hz=[1500.0],
    )
    assert float(gated["excluded_region_hz_total"]) > float(bare["excluded_region_hz_total"])


TROMBONE_G3 = Path(
    r"D:\METAIS\TROMBONE\IOWA_Trombone - Test\TenorTrombone"
    r"\IOWA_Trombone_ff\_Sustains_Stable\IOWA_Trb.T_ff.G3_SustainStable.aif"
)
TROMBONE_GS3 = Path(
    r"D:\METAIS\TROMBONE\IOWA_Trombone - Test\TenorTrombone"
    r"\IOWA_Trombone_ff\_Sustains_Stable\IOWA_Trb.T_ff.G#3_SustainStable.aif"
)


def _stage1_core_ratio(audio: Path, n_fft: int, hop: int, dest: Path) -> float:
    from proc_audio import AudioProcessor

    dest.mkdir(parents=True, exist_ok=True)
    ap = AudioProcessor()
    ap.load_audio_files([str(audio)])
    ap.apply_filters_and_generate_data(
        results_directory=dest,
        n_fft=int(n_fft),
        hop_length=int(hop),
        zero_padding=2,
        window="blackmanharris",
        freq_min=20.0,
        freq_max=20000.0,
        db_min=-90.0,
        db_max=0.0,
        density_frequency_ceiling_hz=20000.0,
        dissonance_enabled=False,
        dissonance_curve=False,
        dissonance_scale=False,
        compare_models=False,
        compile_per_call=False,
        parallel_processing=False,
    )
    return float(getattr(ap, "harmonic_energy_ratio", float("nan")))


@pytest.mark.skipif(not TROMBONE_G3.is_file(), reason="trombone G3 take not on this machine")
def test_g3_core_h_ratio_within_three_percent_across_n_fft(tmp_path: Path) -> None:
    ratios = []
    for n_fft in (4096, 8192, 16384):
        ratios.append(
            _stage1_core_ratio(TROMBONE_G3, n_fft, max(1, n_fft // 8), tmp_path / str(n_fft))
        )
    ref = ratios[1]
    for r in ratios:
        assert np.isfinite(r)
        assert abs(r - ref) / max(abs(ref), 1e-9) <= 0.03


@pytest.mark.skipif(
    not (TROMBONE_G3.is_file() and TROMBONE_GS3.is_file()),
    reason="trombone G3/G#3 takes not on this machine",
)
def test_g3_gs3_core_h_does_not_follow_the_window(tmp_path: Path) -> None:
    g3_8192 = _stage1_core_ratio(TROMBONE_G3, 8192, 1024, tmp_path / "g3_8192")
    g3_4096 = _stage1_core_ratio(TROMBONE_G3, 4096, 512, tmp_path / "g3_4096")
    gs3_4096 = _stage1_core_ratio(TROMBONE_GS3, 4096, 512, tmp_path / "gs3_4096")
    gs3_8192 = _stage1_core_ratio(TROMBONE_GS3, 8192, 1024, tmp_path / "gs3_8192")
    # Same note, swapped window: core_H must not jump with n_fft.
    assert abs(g3_8192 - g3_4096) / max(abs(g3_8192), 1e-9) <= 0.03
    assert abs(gs3_8192 - gs3_4096) / max(abs(gs3_8192), 1e-9) <= 0.03
    # The remaining G3 vs G#3 difference is the note, not the window.
    note_delta = abs(g3_8192 - gs3_8192)
    window_delta = abs(g3_8192 - g3_4096)
    assert note_delta >= window_delta
