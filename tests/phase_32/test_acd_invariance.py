"""Gain / FFT-tier / peak-threshold invariance: ACD vs EWSD side by side."""
from __future__ import annotations

import json
import re

import numpy as np
import pytest

from tests.phase_32.acd_invariance_support import (
    FFT_TIERS,
    GAINS,
    MONOTONICITY_DB,
    REAL_H_A,
    REAL_H_F,
    REAL_I_A,
    REAL_I_F,
    REAL_NOTE_CACHE,
    REAL_NOTE_CORPUS,
    REAL_NOTE_FFT_TIER_ACD_REL_TOL,
    REAL_NOTE_ID,
    REAL_S_A,
    REAL_S_F,
    SYNTH_H_A,
    SYNTH_H_F,
    SYNTH_I_A,
    SYNTH_I_F,
    SYNTH_S_A,
    SYNTH_S_F,
    TABLE_PATH,
    THRESHOLD_ROBUSTNESS_DB,
    EWSD_CLONE_VECTORS,
    acd_score,
    add_fft_sidelobes,
    delta_pct,
    ewsd_compartment_score,
    ewsd_pair,
    extras_at_level_db,
    fmt,
    fmt_pct,
)
from tools.spectral_density_hill import erb_bandwidth_hz


def test_gain_sweep_acd_flat() -> None:
    base = acd_score(SYNTH_H_A, SYNTH_H_F, SYNTH_I_A, SYNTH_I_F, SYNTH_S_A, SYNTH_S_F)
    for g in GAINS:
        got = acd_score(
            g * SYNTH_H_A, SYNTH_H_F, g * SYNTH_I_A, SYNTH_I_F, g * SYNTH_S_A, SYNTH_S_F
        )
        assert got == pytest.approx(base, abs=1e-10)


def test_fft_tier_acd_stable() -> None:
    base = acd_score(SYNTH_H_A, SYNTH_H_F, SYNTH_I_A, SYNTH_I_F, SYNTH_S_A, SYNTH_S_F)
    for n_fft in FFT_TIERS:
        hf, ha = add_fft_sidelobes(SYNTH_H_F, SYNTH_H_A, n_fft)
        iff, ia = add_fft_sidelobes(SYNTH_I_F, SYNTH_I_A, n_fft)
        for f in SYNTH_H_F:
            assert (44100.0 / 4096.0) < float(erb_bandwidth_hz(np.asarray([f]))[0])
        got = acd_score(ha, hf, ia, iff, SYNTH_S_A, SYNTH_S_F)
        assert got == pytest.approx(base, rel=0.05, abs=1e-9)


def test_threshold_sweep_acd_stable() -> None:
    base = acd_score(SYNTH_H_A, SYNTH_H_F, SYNTH_I_A, SYNTH_I_F, SYNTH_S_A, SYNTH_S_F)
    amax = float(np.max(SYNTH_H_A))
    for thr in THRESHOLD_ROBUSTNESS_DB:
        extras = extras_at_level_db(12, amax, thr)
        extra_f = SYNTH_H_F[-1] + 400.0 * np.arange(1, 13)
        got = acd_score(
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
            assert got >= base * 0.95


def test_ewsd_cloning_doubles_score() -> None:
    """EWSD_k doubles under cloning into a disjoint band (replication of the score).

    The penalty N_eff/N is unchanged, but D_k doubles, so the score doubles.
    That is the cloning property. EWSD fails Scaling and Babies only.
    """
    for vec in EWSD_CLONE_VECTORS:
        left = ewsd_compartment_score(vec)
        cloned = ewsd_compartment_score(np.concatenate([vec, vec]))
        assert left > 0.0
        assert cloned / left == pytest.approx(2.0, abs=1e-9)


def test_ewsd_fails_scaling_only_as_documented() -> None:
    base = ewsd_compartment_score(np.asarray([2.0, 0.2, 0.2], dtype=float))
    scaled = ewsd_compartment_score(10.0 * np.asarray([2.0, 0.2, 0.2], dtype=float))
    assert scaled != pytest.approx(base, rel=1e-3, abs=1e-12)


def test_ewsd_fails_babies_only_as_documented() -> None:
    strong = np.asarray([1.0, 1.0, 1.0], dtype=float)
    one = np.concatenate([strong, [10.0 ** (-60.0 / 20.0)]])
    s0 = ewsd_compartment_score(strong)
    s1 = ewsd_compartment_score(one)
    assert (s0 - s1) / s0 == pytest.approx(0.249, abs=0.01)


def test_write_invariance_markdown_table() -> None:
    lines = [
        "# ACD vs EWSD invariance (generated)",
        "",
        "Toy inputs unless a later section says otherwise. ACD is F-057 "
        "(`sum_k r_k D1_k` after ERB merge). EWSD is frozen F-048 / F-049 on "
        "the same amplitudes with Excel-like `r = (0.80, 0.15, 0.05)` and "
        "`φ = log`. Synthetic blocks are fixtures, not corpus measurements.",
        "",
        "## Axiomatic comparison (Hurley & Rickard 2009; Hill / Jost replication)",
        "",
        "EWSD rows state a failure only when a passing test in "
        "`tests/phase_32/` demonstrates it. EWSD fails **Scaling** and "
        "**Babies**, and only those two.",
        "",
        "| Property | ACD (F-057 / D1) | EWSD (F-048 score) |",
        "|---|---|---|",
        "| Scaling | Holds | Fails (level-dependent `log1p` shares) |",
        "| Babies (−60 dB extras) | Holds (D1 change < 1 % at −80 dB × 50) | Fails (−24.9 % / −93.9 %) |",
        "| Cloning (disjoint replica) | Holds (D_q doubles) | Holds (ratio = 2.000000) |",
        "| Dalton / Robin Hood | Holds (D1 increases) | not claimed |",
        "| Rising Tide | Holds (diversity dual of the 2009 sparsity axiom) | not claimed |",
        "| Bill Gates | Holds (D1 → 1) | not claimed |",
        "",
        "## Gain sweep (synthetic note)",
        "",
        "| gain | ACD_score | EWSD_score_total | EWSD_score_acoustic_balanced |",
        "|---:|---:|---:|---:|",
    ]
    for g in GAINS:
        acd = acd_score(
            g * SYNTH_H_A, SYNTH_H_F, g * SYNTH_I_A, SYNTH_I_F, g * SYNTH_S_A, SYNTH_S_F
        )
        e048, e049 = ewsd_pair(g * SYNTH_H_A, g * SYNTH_I_A, g * SYNTH_S_A)
        lines.append(f"| {g:.0e} | {fmt(acd)} | {fmt(e048)} | {fmt(e049)} |")

    lines += [
        "",
        "## Gain sweep (research-export D3 fixture amplitudes)",
        "",
        "| gain | ACD_score | EWSD_score_total | EWSD_score_acoustic_balanced |",
        "|---:|---:|---:|---:|",
    ]
    for g in GAINS:
        acd = acd_score(g * REAL_H_A, REAL_H_F, g * REAL_I_A, REAL_I_F, g * REAL_S_A, REAL_S_F)
        e048, e049 = ewsd_pair(g * REAL_H_A, g * REAL_I_A, g * REAL_S_A)
        lines.append(f"| {g:.0e} | {fmt(acd)} | {fmt(e048)} | {fmt(e049)} |")

    lines += [
        "",
        "## FFT-tier sidelobe model (synthetic; bin width `fs/n_fft`)",
        "",
        "non-discriminating (synthetic sidelobe model; both metrics flat). "
        "See the real-note Stage 1 tier sweep below, where bin width, "
        "resolved-peak count, and Phase 8 `peak_amplitude_sum` normalisation "
        "vary together.",
        "",
        "| n_fft | ACD_score | EWSD_score_total | EWSD_score_acoustic_balanced | note |",
        "|---:|---:|---:|---:|---|",
    ]
    for n_fft in FFT_TIERS:
        hf, ha = add_fft_sidelobes(SYNTH_H_F, SYNTH_H_A, n_fft)
        iff, ia = add_fft_sidelobes(SYNTH_I_F, SYNTH_I_A, n_fft)
        acd = acd_score(ha, hf, ia, iff, SYNTH_S_A, SYNTH_S_F)
        e048, e049 = ewsd_pair(ha, ia, SYNTH_S_A)
        lines.append(
            f"| {n_fft} | {fmt(acd)} | {fmt(e048)} | {fmt(e049)} | "
            "non-discriminating (synthetic sidelobe model; both metrics flat) |"
        )

    acd_base = acd_score(SYNTH_H_A, SYNTH_H_F, SYNTH_I_A, SYNTH_I_F, SYNTH_S_A, SYNTH_S_F)
    e048_base, e049_base = ewsd_pair(SYNTH_H_A, SYNTH_I_A, SYNTH_S_A)
    amax = float(np.max(SYNTH_H_A))

    lines += [
        "",
        "## Peak-picking threshold extras on H (synthetic)",
        "",
        "Column `extra_component_level_dB_re_max` is the level of twelve added "
        "components relative to the loudest original peak. First row is the "
        "same fixture with **no extras**; EWSD and ACD bases are computed, "
        "not hard-coded. Δ% is against each metric's own base.",
        "",
        "| extra_component_level_dB_re_max | ACD_score | ACD_Δ% | "
        "EWSD_score_total | EWSD_Δ% | EWSD_score_acoustic_balanced | EWSD_bal_Δ% |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        f"| (none) | {fmt(acd_base)} | {fmt_pct(0.0)} | {fmt(e048_base)} | "
        f"{fmt_pct(0.0)} | {fmt(e049_base)} | {fmt_pct(0.0)} |",
    ]
    for thr in THRESHOLD_ROBUSTNESS_DB:
        extras = extras_at_level_db(12, amax, thr)
        extra_f = SYNTH_H_F[-1] + 400.0 * np.arange(1, 13)
        ha = np.concatenate([SYNTH_H_A, extras])
        hf = np.concatenate([SYNTH_H_F, extra_f])
        acd = acd_score(ha, hf, SYNTH_I_A, SYNTH_I_F, SYNTH_S_A, SYNTH_S_F)
        e048, e049 = ewsd_pair(ha, SYNTH_I_A, SYNTH_S_A)
        lines.append(
            f"| {thr:g} | {fmt(acd)} | {fmt_pct(delta_pct(acd, acd_base))} | "
            f"{fmt(e048)} | {fmt_pct(delta_pct(e048, e048_base))} | "
            f"{fmt(e049)} | {fmt_pct(delta_pct(e049, e049_base))} |"
        )

    lines += [
        "",
        "## Monotonicity in genuine content",
        "",
        "Twelve extras at 0 dB re max are as loud as the loudest original "
        "component. That is an amplitude manipulation, not a detection-threshold "
        "manipulation. A rise in ACD is the expected result.",
        "",
        "| extra_component_level_dB_re_max | ACD_score | ACD_Δ% | "
        "EWSD_score_total | EWSD_Δ% | EWSD_score_acoustic_balanced | EWSD_bal_Δ% |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for thr in MONOTONICITY_DB:
        extras = extras_at_level_db(12, amax, thr)
        extra_f = SYNTH_H_F[-1] + 400.0 * np.arange(1, 13)
        ha = np.concatenate([SYNTH_H_A, extras])
        hf = np.concatenate([SYNTH_H_F, extra_f])
        acd = acd_score(ha, hf, SYNTH_I_A, SYNTH_I_F, SYNTH_S_A, SYNTH_S_F)
        e048, e049 = ewsd_pair(ha, SYNTH_I_A, SYNTH_S_A)
        assert acd > acd_base
        lines.append(
            f"| {thr:g} | {fmt(acd)} | {fmt_pct(delta_pct(acd, acd_base))} | "
            f"{fmt(e048)} | {fmt_pct(delta_pct(e048, e048_base))} | "
            f"{fmt(e049)} | {fmt_pct(delta_pct(e049, e049_base))} |"
        )

    lines += [
        "",
        "## Stated tolerances (synthetic)",
        "",
        "- ACD gain sweep: flat to `1e-10`.",
        "- ACD FFT-tier sidelobe model: relative 5 % (ERB merge absorbs intra-filter leakage). "
        "Row is non-discriminating; both metrics are flat. Real-note Stage 1 "
        f"tier tolerance: `{REAL_NOTE_FFT_TIER_ACD_REL_TOL:.0%} relative` on `ACD_score`.",
        "- ACD extras at −80 dB or weaker: relative 1 %.",
        "- EWSD columns are the frozen F-048/F-049 values on the same vectors; "
        "they are not required to be invariant. Demonstrated failures: Scaling and Babies only.",
        "",
    ]
    lines.extend(_real_note_markdown_section())

    TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TABLE_PATH.write_text("\n".join(lines), encoding="utf-8")
    text = TABLE_PATH.read_text(encoding="utf-8")
    assert "Holds (ratio = 2.000000)" in text
    assert "extra_component_level_dB_re_max" in text
    assert "Monotonicity in genuine content" in text
    assert "non-discriminating (synthetic sidelobe model; both metrics flat)" in text
    assert fmt(e048_base) in text
    assert "Fails" in text
    # 0 dB extras must not sit in the threshold-robustness table.
    robustness = text.split("## Monotonicity in genuine content")[0]
    thresh_block = robustness.split("Peak-picking threshold")[-1]
    assert not re.search(r"^\| 0(\.0)? \|", thresh_block, flags=re.MULTILINE)


def _real_note_markdown_section() -> list[str]:
    heading = [
        f"## Real-note invariance — {REAL_NOTE_ID}, {REAL_NOTE_CORPUS}",
        "",
    ]
    if not REAL_NOTE_CACHE.is_file():
        heading += [
            "Measurements are produced by `tests/phase_32/test_acd_real_note_invariance.py` "
            "(real Stage 1: gain on the loaded audio, production tier n_fft, "
            "production `db_min`). Cache file "
            f"`{REAL_NOTE_CACHE.as_posix()}` is not present in this checkout.",
            "",
        ]
        return heading
    payload = json.loads(REAL_NOTE_CACHE.read_text(encoding="utf-8"))
    heading += [
        str(payload.get("heading_note", "")).strip(),
        "",
        f"ACD FFT-tier tolerance asserted at `{REAL_NOTE_FFT_TIER_ACD_REL_TOL:.0%}` relative "
        "(winning merge strategy max |Δ%| + 1 pp, rounded up; not above 5%). "
        "Historical ACD_score rows below are D2 / moving_centroid; current default "
        "is D1 / fixed_erb_grid (`docs/validation/ACD_MERGE_STRATEGY.md`).",
        "",
    ]
    for block in payload.get("blocks", []):
        heading.append(f"### {block['title']}")
        heading.append("")
        heading.append(block["caption"])
        heading.append("")
        heading.append(block["header"])
        heading.append(block["separator"])
        heading.extend(block["rows"])
        heading.append("")
    return heading


def test_monotonicity_zero_db_raises_acd() -> None:
    base = acd_score(SYNTH_H_A, SYNTH_H_F, SYNTH_I_A, SYNTH_I_F, SYNTH_S_A, SYNTH_S_F)
    extras = extras_at_level_db(12, float(np.max(SYNTH_H_A)), 0.0)
    extra_f = SYNTH_H_F[-1] + 400.0 * np.arange(1, 13)
    got = acd_score(
        np.concatenate([SYNTH_H_A, extras]),
        np.concatenate([SYNTH_H_F, extra_f]),
        SYNTH_I_A,
        SYNTH_I_F,
        SYNTH_S_A,
        SYNTH_S_F,
    )
    assert got > base
