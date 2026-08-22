"""Shared ACD / EWSD helpers for invariance-table generation (no formula edits)."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from tools.ewsd_pure import (
    CompartmentInputs,
    compute_acoustic_balanced_score,
    compute_compartment_metrics,
    compute_strict_ewsd_total,
)
from tools.spectral_density_hill import compute_density_compartment, compute_note_density

SYNTH_H_F = np.asarray([200.0, 600.0, 1400.0, 3200.0], dtype=float)
SYNTH_H_A = np.asarray([1.0, 0.7, 0.45, 0.25], dtype=float)
SYNTH_I_F = np.asarray([350.0, 900.0], dtype=float)
SYNTH_I_A = np.asarray([0.18, 0.12], dtype=float)
SYNTH_S_F = np.asarray([55.0], dtype=float)
SYNTH_S_A = np.asarray([0.06], dtype=float)

# Per-note workbook amplitudes from the Stage 3 research-export fixture (D3).
REAL_H_F = np.asarray([146.83, 293.66, 440.0], dtype=float)
REAL_H_A = np.asarray([1.0, 0.7, 0.5], dtype=float)
REAL_I_F = np.asarray([220.0, 330.0], dtype=float)
REAL_I_A = np.asarray([0.15, 0.10], dtype=float)
REAL_S_F = np.asarray([55.0], dtype=float)
REAL_S_A = np.asarray([0.05], dtype=float)

GAINS = np.array([1e-3, 1e-2, 1e-1, 1.0, 10.0, 1e2, 1e4])
FFT_TIERS = (4096, 8192, 16384)
# Production peak-picking floors used in Stage 1 (db_min / density_salience).
# 0 dB re max is an amplitude-manipulation case, not a detection floor.
THRESHOLD_ROBUSTNESS_DB = (-20.0, -40.0, -60.0, -80.0, -100.0)
MONOTONICITY_DB = (0.0,)

# Unique n_fft values `_assign_tier_for_file` selects for the 49-note cello
# range C2–C6 (see pipeline_orchestrator_gui.FFT_SETTINGS_BY_CLUSTER).
CELLO_CORPUS_TIER_N_FFT = (16384, 8192, 4096, 2048)
REAL_NOTE_ID = "D3"
REAL_NOTE_CORPUS = "ORC_Vlc_arco_mf _Sustains (49-note cello corpus)"
# Real Stage 1 changes bin width, peak census, and Phase 8 peak_amplitude_sum
# together. Exact invariance is not expected. Gate is the winning merge
# strategy's measured max |Δ%| plus 1 percentage point, rounded up
# (fixed_erb_grid 2.74% → 4%). This is not above 5%.
REAL_NOTE_FFT_TIER_ACD_REL_TOL = 0.04

TABLE_PATH = (
    Path(__file__).resolve().parents[2] / "docs" / "validation" / "ACD_INVARIANCE_TABLE.md"
)
REAL_NOTE_CACHE = Path(__file__).resolve().parent / "golden" / "acd_real_note_invariance.json"

EWSD_CLONE_VECTORS = (
    np.asarray([1.0, 1.0, 1.0], dtype=float),
    np.asarray([2.0, 0.2, 0.2], dtype=float),
    np.asarray([1.0, 0.5, 0.25, 0.1], dtype=float),
)


def acd_note_metrics(h_a, h_f, i_a, i_f, s_a, s_f, *, erb_fraction: float = 1.0) -> dict:
    note = compute_note_density(
        {
            "harmonic": compute_density_compartment(
                h_a, h_f, erb_fraction=erb_fraction
            ),
            "inharmonic": compute_density_compartment(
                i_a, i_f, erb_fraction=erb_fraction
            ),
            "subbass": compute_density_compartment(
                s_a, s_f, erb_fraction=erb_fraction
            ),
        }
    )
    return note


def acd_score(h_a, h_f, i_a, i_f, s_a, s_f, *, erb_fraction: float = 1.0) -> float:
    return float(
        acd_note_metrics(h_a, h_f, i_a, i_f, s_a, s_f, erb_fraction=erb_fraction)[
            "ACD_score"
        ]
    )


def ewsd_pair(h_a, i_a, s_a, r=(0.80, 0.15, 0.05)) -> tuple[float, float]:
    comps = [
        compute_compartment_metrics(
            CompartmentInputs(values=h_a, analysis_ratio=r[0], weight_function="log")
        ),
        compute_compartment_metrics(
            CompartmentInputs(values=i_a, analysis_ratio=r[1], weight_function="log")
        ),
        compute_compartment_metrics(
            CompartmentInputs(values=s_a, analysis_ratio=r[2], weight_function="log")
        ),
    ]
    return compute_strict_ewsd_total(comps), compute_acoustic_balanced_score(
        comps, alpha=0.50
    )


def ewsd_compartment_score(values: np.ndarray, *, ratio: float = 1.0) -> float:
    return float(
        compute_compartment_metrics(
            CompartmentInputs(
                values=np.asarray(values, dtype=float),
                analysis_ratio=ratio,
                weight_function="log",
            )
        ).ewsd_score
    )


def add_fft_sidelobes(freq: np.ndarray, amp: np.ndarray, n_fft: int, fs: float = 44100.0):
    """Model extra bin leakage: one pair of sidelobes per peak, closer at larger n_fft."""
    df = fs / float(n_fft)
    extra_f = []
    extra_a = []
    for f, a in zip(freq, amp):
        extra_f.extend([f - df, f + df])
        extra_a.extend([0.05 * a, 0.05 * a])
    return np.concatenate([freq, extra_f]), np.concatenate([amp, extra_a])


def extras_at_level_db(n: int, amax: float, level_db: float) -> np.ndarray:
    floor = amax * (10.0 ** (level_db / 20.0))
    return np.full(n, 0.5 * floor + 1e-18)


def delta_pct(value: float, base: float) -> float:
    if not np.isfinite(value) or not np.isfinite(base) or abs(base) < 1e-30:
        return float("nan")
    return 100.0 * (float(value) - float(base)) / float(base)


def fmt(value: float, digits: int = 12) -> str:
    if value is None or not np.isfinite(value):
        return "NaN"
    return f"{float(value):.{digits}g}"


def fmt_pct(value: float) -> str:
    if value is None or not np.isfinite(value):
        return "NaN"
    return f"{float(value):+.4f}"
