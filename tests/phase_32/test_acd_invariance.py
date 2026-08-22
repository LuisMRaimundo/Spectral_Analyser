"""Gain / FFT-tier / peak-threshold invariance: ACD vs EWSD side by side."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tools.ewsd_pure import (
    CompartmentInputs,
    compute_acoustic_balanced_score,
    compute_compartment_metrics,
    compute_strict_ewsd_total,
)
from tools.spectral_density_hill import (
    compute_density_compartment,
    compute_note_density,
    erb_bandwidth_hz,
)

TABLE_PATH = Path(__file__).resolve().parents[2] / "docs" / "validation" / "ACD_INVARIANCE_TABLE.md"

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
THRESHOLDS_DB = (0.0, -20.0, -40.0, -60.0, -80.0, -100.0)


def _acd(h_a, h_f, i_a, i_f, s_a, s_f) -> float:
    note = compute_note_density(
        {
            "harmonic": compute_density_compartment(h_a, h_f),
            "inharmonic": compute_density_compartment(i_a, i_f),
            "subbass": compute_density_compartment(s_a, s_f),
        }
    )
    return float(note["ACD_score"])


def _ewsd(h_a, i_a, s_a, r=(0.80, 0.15, 0.05)) -> tuple[float, float]:
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
    return compute_strict_ewsd_total(comps), compute_acoustic_balanced_score(comps, alpha=0.50)


def _add_fft_sidelobes(freq: np.ndarray, amp: np.ndarray, n_fft: int, fs: float = 44100.0):
    """Model extra bin leakage: one pair of sidelobes per peak, closer at larger n_fft."""
    df = fs / float(n_fft)
    extra_f = []
    extra_a = []
    for f, a in zip(freq, amp):
        extra_f.extend([f - df, f + df])
        extra_a.extend([0.05 * a, 0.05 * a])
    return np.concatenate([freq, extra_f]), np.concatenate([amp, extra_a])


def test_gain_sweep_acd_flat() -> None:
    base = _acd(SYNTH_H_A, SYNTH_H_F, SYNTH_I_A, SYNTH_I_F, SYNTH_S_A, SYNTH_S_F)
    for g in GAINS:
        got = _acd(g * SYNTH_H_A, SYNTH_H_F, g * SYNTH_I_A, SYNTH_I_F, g * SYNTH_S_A, SYNTH_S_F)
        assert got == pytest.approx(base, abs=1e-10)


def test_fft_tier_acd_stable() -> None:
    base = _acd(SYNTH_H_A, SYNTH_H_F, SYNTH_I_A, SYNTH_I_F, SYNTH_S_A, SYNTH_S_F)
    for n_fft in FFT_TIERS:
        hf, ha = _add_fft_sidelobes(SYNTH_H_F, SYNTH_H_A, n_fft)
        iff, ia = _add_fft_sidelobes(SYNTH_I_F, SYNTH_I_A, n_fft)
        # sidelobes stay inside one ERB of each parent at these spacings
        for f in SYNTH_H_F:
            assert (44100.0 / 4096.0) < float(erb_bandwidth_hz(np.asarray([f]))[0])
        got = _acd(ha, hf, ia, iff, SYNTH_S_A, SYNTH_S_F)
        assert got == pytest.approx(base, rel=0.05, abs=1e-9)


def test_threshold_sweep_acd_stable() -> None:
    base = _acd(SYNTH_H_A, SYNTH_H_F, SYNTH_I_A, SYNTH_I_F, SYNTH_S_A, SYNTH_S_F)
    amax = float(np.max(SYNTH_H_A))
    for thr in THRESHOLDS_DB:
        floor = amax * (10.0 ** (thr / 20.0))
        extras = np.full(12, 0.5 * floor + 1e-18)
        extra_f = SYNTH_H_F[-1] + 400.0 * np.arange(1, 13)
        got = _acd(
            np.concatenate([SYNTH_H_A, extras]),
            np.concatenate([SYNTH_H_F, extra_f]),
            SYNTH_I_A,
            SYNTH_I_F,
            SYNTH_S_A,
            SYNTH_S_F,
        )
        if thr <= -80.0:
            assert got == pytest.approx(base, rel=0.01)
        else:
            # stronger extras may register; still bounded
            assert got >= base * 0.95


def test_write_invariance_markdown_table() -> None:
    lines = [
        "# ACD vs EWSD invariance (generated)",
        "",
        "Toy inputs only. ACD is F-057 (`sum_k r_k D2_k` after ERB merge). "
        "EWSD is frozen F-048 / F-049 on the same amplitudes with Excel-like "
        "`r = (0.80, 0.15, 0.05)` and `φ = log`. Not a corpus measurement.",
        "",
        "## Gain sweep (synthetic note)",
        "",
        "| gain | ACD_score | EWSD_score_total | EWSD_score_acoustic_balanced |",
        "|---:|---:|---:|---:|",
    ]
    for g in GAINS:
        acd = _acd(g * SYNTH_H_A, SYNTH_H_F, g * SYNTH_I_A, SYNTH_I_F, g * SYNTH_S_A, SYNTH_S_F)
        e048, e049 = _ewsd(g * SYNTH_H_A, g * SYNTH_I_A, g * SYNTH_S_A)
        lines.append(f"| {g:.0e} | {acd:.12g} | {e048:.12g} | {e049:.12g} |")

    lines += [
        "",
        "## Gain sweep (research-export D3 fixture amplitudes)",
        "",
        "| gain | ACD_score | EWSD_score_total | EWSD_score_acoustic_balanced |",
        "|---:|---:|---:|---:|",
    ]
    for g in GAINS:
        acd = _acd(g * REAL_H_A, REAL_H_F, g * REAL_I_A, REAL_I_F, g * REAL_S_A, REAL_S_F)
        e048, e049 = _ewsd(g * REAL_H_A, g * REAL_I_A, g * REAL_S_A)
        lines.append(f"| {g:.0e} | {acd:.12g} | {e048:.12g} | {e049:.12g} |")

    lines += [
        "",
        "## FFT-tier sidelobe model (synthetic; bin width `fs/n_fft`)",
        "",
        "| n_fft | ACD_score | EWSD_score_total | EWSD_score_acoustic_balanced |",
        "|---:|---:|---:|---:|",
    ]
    for n_fft in FFT_TIERS:
        hf, ha = _add_fft_sidelobes(SYNTH_H_F, SYNTH_H_A, n_fft)
        iff, ia = _add_fft_sidelobes(SYNTH_I_F, SYNTH_I_A, n_fft)
        acd = _acd(ha, hf, ia, iff, SYNTH_S_A, SYNTH_S_F)
        e048, e049 = _ewsd(ha, ia, SYNTH_S_A)
        lines.append(f"| {n_fft} | {acd:.12g} | {e048:.12g} | {e049:.12g} |")

    lines += [
        "",
        "## Peak-picking threshold extras on H (synthetic; 12 extras at half the linear floor)",
        "",
        "| threshold_dB_re_max | ACD_score | EWSD_score_total | EWSD_score_acoustic_balanced |",
        "|---:|---:|---:|---:|",
    ]
    amax = float(np.max(SYNTH_H_A))
    for thr in THRESHOLDS_DB:
        floor = amax * (10.0 ** (thr / 20.0))
        extras = np.full(12, 0.5 * floor + 1e-18)
        extra_f = SYNTH_H_F[-1] + 400.0 * np.arange(1, 13)
        ha = np.concatenate([SYNTH_H_A, extras])
        hf = np.concatenate([SYNTH_H_F, extra_f])
        acd = _acd(ha, hf, SYNTH_I_A, SYNTH_I_F, SYNTH_S_A, SYNTH_S_F)
        e048, e049 = _ewsd(ha, SYNTH_I_A, SYNTH_S_A)
        lines.append(f"| {thr} | {acd:.12g} | {e048:.12g} | {e049:.12g} |")

    lines += [
        "",
        "## Stated tolerances",
        "",
        "- ACD gain sweep: flat to `1e-10`.",
        "- ACD FFT-tier sidelobe model: relative 5 % (ERB merge absorbs intra-filter leakage).",
        "- ACD extras at −80 dB or weaker: relative 1 %.",
        "- EWSD columns are the frozen F-048/F-049 values on the same vectors; they are not required to be invariant.",
        "",
    ]
    TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TABLE_PATH.write_text("\n".join(lines), encoding="utf-8")
    assert TABLE_PATH.is_file()
    text = TABLE_PATH.read_text(encoding="utf-8")
    assert "ACD_score" in text
    assert "EWSD_score_total" in text
