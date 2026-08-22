from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from constants import CFAR_PFA, INHARMONIC_MIN_PROMINENCE_DB
from inharmonic_confirmation import (
    STATUS_CONFIRMED,
    STATUS_FLOOR,
    STATUS_LEAKAGE,
    STATUS_STRETCHED,
    confirm_inharmonic_candidates,
    f007_frequency_hz,
    reassign_stretched_to_harmonics,
)
from metric_contract import get_metric_definition
from validated_partials import gated_linear_amplitude_sums, is_validated_partial

A2_PHASE13 = Path(
    r"D:\METAIS\TUBA\Tuba\Tuba_Yowa\IOWA_tuba_pp"
    r"\_Sustains_Stable\analysis_results_phase13\A2\spectral_analysis.xlsx"
)
A2_RUN2 = Path(
    r"D:\METAIS\TUBA\Tuba\Tuba_Yowa\IOWA_tuba_pp"
    r"\_Sustains_Stable\analysis_results_2"
    r"\IOWA_Tub.pp.A2_SustainStable\spectral_analysis.xlsx"
)


def _spectrum(
    *,
    sr: float = 44100.0,
    n_fft: int = 8192,
    floor: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    mags = np.full(freqs.shape, float(floor), dtype=float)
    return freqs, mags, sr, float(n_fft)


def _add_peak(mags: np.ndarray, freqs: np.ndarray, freq_hz: float, snr_db: float) -> int:
    idx = int(np.argmin(np.abs(freqs - float(freq_hz))))
    idx = max(2, min(int(mags.size) - 3, idx))
    peak = float(mags[idx]) * (10.0 ** (float(snr_db) / 20.0))
    mags[idx] = peak
    mags[idx - 1] = 0.45 * peak
    mags[idx + 1] = 0.45 * peak
    return idx


def _rows_from_freqs(freqs_hz: list[float], mags: np.ndarray, freqs: np.ndarray) -> list[dict]:
    rows = []
    for f in freqs_hz:
        idx = int(np.argmin(np.abs(freqs - float(f))))
        amp = float(mags[idx])
        rows.append(
            {
                "Frequency (Hz)": float(freqs[idx]),
                "Amplitude": amp,
                "Amplitude_raw": amp,
                "peak_bin_index": idx,
            }
        )
    return rows


def test_cfar_pfa_matches_harmonic_default() -> None:
    assert CFAR_PFA == pytest.approx(1e-2)
    assert INHARMONIC_MIN_PROMINENCE_DB == pytest.approx(6.0)


def test_a2_like_floor_candidates_are_rejected_floor() -> None:
    freqs, mags, sr, n_fft = _spectrum()
    f0 = 110.0
    accepted = [{"Frequency (Hz)": f0 * n, "Harmonic Number": n} for n in range(1, 9)]
    floor_hz = [12011.6, 12094.3, 12191.7] + [400.0 + 37.0 * k for k in range(38)]
    for f in floor_hz:
        _add_peak(mags, freqs, f, snr_db=0.3)
    rows = _rows_from_freqs(floor_hz, mags, freqs)
    out = confirm_inharmonic_candidates(
        rows,
        magnitudes=mags,
        freqs=freqs,
        accepted_harmonics=accepted,
        f0_hz=f0,
        B=0.0,
        inharmonicity_model_applied=False,
        sr=sr,
        n_fft=int(n_fft),
    )
    assert len(out) == 41
    assert all(r["inharmonic_status"] == STATUS_FLOOR for r in out)
    assert all(r["cfar_detected_i"] is False for r in out)
    assert sum(1 for r in out if r["inharmonic_status"] == STATUS_CONFIRMED) == 0


def test_piano_like_stretched_partials_reassigned_to_h() -> None:
    freqs, mags, sr, n_fft = _spectrum()
    f0 = 110.0
    B = 2.0e-4
    stretched = [f007_frequency_hz(n, f0, B) for n in range(1, 31)]
    for f in stretched:
        _add_peak(mags, freqs, f, snr_db=25.0)
    rows = _rows_from_freqs(stretched, mags, freqs)
    out = confirm_inharmonic_candidates(
        rows,
        magnitudes=mags,
        freqs=freqs,
        accepted_harmonics=[],
        f0_hz=f0,
        B=B,
        inharmonicity_model_applied=True,
        sr=sr,
        n_fft=int(n_fft),
    )
    assert all(r["inharmonic_status"] == STATUS_STRETCHED for r in out)
    assert all(r["not_stretched_harmonic_i"] is False for r in out)
    assert sum(1 for r in out if r["inharmonic_status"] == STATUS_CONFIRMED) == 0
    reassigned = reassign_stretched_to_harmonics(out)
    assert len(reassigned) == 30
    assert all(r["candidate_status"] == "strict_validated_stretched" for r in reassigned)
    assert {int(r["Harmonic Number"]) for r in reassigned} == set(range(1, 31))


def test_bell_like_partials_confirm_exactly_ten() -> None:
    freqs, mags, sr, n_fft = _spectrum()
    f0 = 220.0
    accepted = [{"Frequency (Hz)": f0 * n, "Harmonic Number": n} for n in range(1, 4)]
    for rec in accepted:
        _add_peak(mags, freqs, rec["Frequency (Hz)"], snr_db=30.0)
    # Mid-gap inharmonic peaks (n+0.5)·f0, outside β·f0 of the F-007 comb.
    bell = [330.0, 550.0, 770.0, 990.0, 1210.0, 1430.0, 1650.0, 1870.0, 2090.0, 2310.0]
    for f in bell:
        _add_peak(mags, freqs, f, snr_db=20.0)
    rows = _rows_from_freqs(bell, mags, freqs)
    out = confirm_inharmonic_candidates(
        rows,
        magnitudes=mags,
        freqs=freqs,
        accepted_harmonics=accepted,
        f0_hz=f0,
        B=0.0,
        inharmonicity_model_applied=True,
        sr=sr,
        n_fft=int(n_fft),
    )
    confirmed = [r for r in out if r["inharmonic_status"] == STATUS_CONFIRMED]
    assert len(confirmed) == 10
    assert all(r["cfar_detected_i"] for r in confirmed)
    assert all(r["local_peak_valid_i"] for r in confirmed)
    assert all(r["not_leakage_i"] for r in confirmed)
    assert all(r["not_stretched_harmonic_i"] for r in confirmed)
    assert all(is_validated_partial(r, kind="inharmonic") for r in confirmed)


def test_h3_sidelobes_rejected_leakage_guarding_order_3() -> None:
    freqs, mags, sr, n_fft = _spectrum()
    f0 = 220.0
    h3 = 3.0 * f0
    bin_hz = float(freqs[1] - freqs[0])
    accepted = [{"Frequency (Hz)": h3, "Harmonic Number": 3}]
    _add_peak(mags, freqs, h3, snr_db=30.0)
    left = h3 - 1.2 * bin_hz
    right = h3 + 1.2 * bin_hz
    _add_peak(mags, freqs, left, snr_db=20.0)
    _add_peak(mags, freqs, right, snr_db=20.0)
    rows = _rows_from_freqs([left, right], mags, freqs)
    out = confirm_inharmonic_candidates(
        rows,
        magnitudes=mags,
        freqs=freqs,
        accepted_harmonics=accepted,
        f0_hz=f0,
        B=0.0,
        inharmonicity_model_applied=False,
        sr=sr,
        n_fft=int(n_fft),
    )
    assert len(out) == 2
    assert all(r["inharmonic_status"] == STATUS_LEAKAGE for r in out)
    assert all(int(r["leakage_guarding_harmonic_order"]) == 3 for r in out)
    assert sum(1 for r in out if r["inharmonic_status"] == STATUS_CONFIRMED) == 0


def test_confirmed_i_enters_gated_linear_sum() -> None:
    harmonic = [
        {
            "Frequency (Hz)": 220.0,
            "Amplitude_raw": 1.0,
            "include_for_density": True,
        }
    ]
    inharmonic = [
        {
            "Frequency (Hz)": 512.0,
            "Amplitude_raw": 0.4,
            "inharmonic_status": STATUS_CONFIRMED,
            "Acoustic_Interpretation_Status": STATUS_CONFIRMED,
        },
        {
            "Frequency (Hz)": 3000.0,
            "Amplitude_raw": 0.5,
            "inharmonic_status": STATUS_FLOOR,
            "Acoustic_Interpretation_Status": STATUS_FLOOR,
        },
    ]
    h, i, _s = gated_linear_amplitude_sums(
        harmonic_rows=harmonic, inharmonic_rows=inharmonic
    )
    assert h == pytest.approx(1.0)
    assert i == pytest.approx(0.4)


def test_metric_contract_inharmonic_density_confirmed_domain() -> None:
    d = get_metric_definition("inharmonic_density_sum")
    assert d is not None
    assert d.input_domain == "confirmed_inharmonic_partials"


@pytest.mark.live_audio
def test_iowa_tuba_a2_workbook_zero_confirmed_if_present() -> None:
    path = A2_PHASE13 if A2_PHASE13.is_file() else A2_RUN2
    if not path.is_file():
        pytest.skip("IOWA tuba A2 workbook not mounted")
    ih = pd.read_excel(path, sheet_name="Inharmonic Spectrum")
    try:
        complete = pd.read_excel(path, sheet_name="Complete Spectrum")
    except Exception:
        pytest.skip("Complete Spectrum missing from A2 workbook")
    if "Frequency (Hz)" not in complete.columns:
        pytest.skip("Complete Spectrum has no Frequency (Hz)")
    freqs = pd.to_numeric(complete["Frequency (Hz)"], errors="coerce").to_numpy(dtype=float)
    if "Amplitude" in complete.columns:
        mags = pd.to_numeric(complete["Amplitude"], errors="coerce").to_numpy(dtype=float)
    elif "Magnitude (dB)" in complete.columns:
        mags = np.power(
            10.0,
            pd.to_numeric(complete["Magnitude (dB)"], errors="coerce").to_numpy(dtype=float)
            / 20.0,
        )
    else:
        pytest.skip("Complete Spectrum has no amplitude column")
    keep = np.isfinite(freqs) & np.isfinite(mags)
    freqs = freqs[keep]
    mags = np.maximum(mags[keep], 1e-12)
    if freqs.size < 16:
        pytest.skip("Complete Spectrum too short")
    try:
        harm = pd.read_excel(path, sheet_name="Harmonic Spectrum")
    except Exception:
        harm = pd.DataFrame()
    accepted = []
    if not harm.empty and "include_for_density" in harm.columns:
        acc = harm.loc[harm["include_for_density"].astype(bool)]
        accepted = acc.to_dict(orient="records")
    candidates = ih.to_dict(orient="records") if not ih.empty else []
    if not candidates:
        pytest.skip("No inharmonic candidates on A2 workbook")
    out = confirm_inharmonic_candidates(
        candidates,
        magnitudes=mags,
        freqs=freqs,
        accepted_harmonics=accepted,
        f0_hz=110.01,
        B=0.0,
        inharmonicity_model_applied=False,
        sr=44100.0,
        n_fft=int(round((freqs.size - 1) * 2)),
    )
    assert all(r["inharmonic_status"] != STATUS_CONFIRMED for r in out)
    floor_n = sum(1 for r in out if r["inharmonic_status"] == STATUS_FLOOR)
    assert floor_n == len(out) or floor_n >= max(1, len(out) - 2)
