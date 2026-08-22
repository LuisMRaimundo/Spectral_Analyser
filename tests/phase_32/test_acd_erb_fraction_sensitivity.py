"""erb_fraction sensitivity on a 1/n harmonic series (not 8-ERB spacing)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tests.phase_32.acd_invariance_support import fmt
from tools.spectral_density_hill import (
    MERGE_STRATEGY_DEFAULT,
    MERGE_STRATEGY_FIXED_ERB_GRID,
    MERGE_STRATEGY_MOVING_CENTROID,
    hill_profile,
    merge_peaks,
)

DOC_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "validation"
    / "ACD_ERB_FRACTION_SENSITIVITY.md"
)
STAGE1_CACHE = Path(__file__).resolve().parent / "golden" / "acd_erb_fraction_stage1.json"

ERB_FRACTIONS = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0)
HARMONIC_F0_HZ = 146.83
HARMONIC_N = 40
REGISTER_F0_HZ = (65.4, 146.8, 261.6, 523.3, 1046.5)
REFERENCE_COUNTS = {
    0.25: {"moving_centroid": 38, "fixed_erb_grid": 40},
    0.5: {"moving_centroid": 26, "fixed_erb_grid": 32},
    0.75: {"moving_centroid": 19, "fixed_erb_grid": 26},
    1.0: {"moving_centroid": 16, "fixed_erb_grid": 22},
    1.5: {"moving_centroid": 12, "fixed_erb_grid": 17},
    2.0: {"moving_centroid": 9, "fixed_erb_grid": 14},
}
RECOVERY_REL = 0.01


def _harmonic_series(n: int = HARMONIC_N, f0: float = HARMONIC_F0_HZ):
    idx = np.arange(1, int(n) + 1, dtype=float)
    return f0 * idx, 1.0 / idx


def _profile(freqs: np.ndarray, amps: np.ndarray, erb_fraction: float) -> dict:
    mf, ma, _mc = merge_peaks(
        freqs,
        amps,
        erb_fraction=erb_fraction,
        merge_strategy=MERGE_STRATEGY_DEFAULT,
    )
    prof = hill_profile(ma)
    return {
        "merged_count": int(mf.size),
        "D0": float(prof["D0"]),
        "D1": float(prof["D1"]),
        "D2": float(prof["D2"]),
    }


def test_reference_merged_counts_on_harmonic_series() -> None:
    freqs, amps = _harmonic_series()
    for frac, expected in REFERENCE_COUNTS.items():
        moving = merge_peaks(
            freqs, amps, erb_fraction=frac, merge_strategy=MERGE_STRATEGY_MOVING_CENTROID
        )[0].size
        grid = merge_peaks(
            freqs, amps, erb_fraction=frac, merge_strategy=MERGE_STRATEGY_FIXED_ERB_GRID
        )[0].size
        assert int(moving) == expected["moving_centroid"]
        assert int(grid) == expected["fixed_erb_grid"]


def test_k_recovery_does_not_hold_on_one_over_n_series() -> None:
    """D1 == N is not a property of a 1/n series even when nothing merges."""
    freqs, amps = _harmonic_series()
    unmerged = hill_profile(amps)
    assert abs(unmerged["D1"] - float(HARMONIC_N)) / HARMONIC_N > 0.20
    row = _profile(freqs, amps, 0.25)
    assert row["merged_count"] == HARMONIC_N
    assert abs(row["D1"] - float(HARMONIC_N)) / HARMONIC_N > 0.20


def test_d1_stays_within_1pct_of_unmerged_only_at_small_fraction() -> None:
    freqs, amps = _harmonic_series()
    d1_u = float(hill_profile(amps)["D1"])
    holds = []
    for frac in ERB_FRACTIONS:
        row = _profile(freqs, amps, frac)
        if abs(row["D1"] - d1_u) <= RECOVERY_REL * d1_u:
            holds.append(frac)
    assert holds[0] == 0.25
    assert max(holds) == 0.5


def test_merged_count_is_more_sensitive_than_d1() -> None:
    freqs, amps = _harmonic_series()
    base = _profile(freqs, amps, 1.0)
    lo = _profile(freqs, amps, 0.25)
    hi = _profile(freqs, amps, 2.0)
    count_span = abs(hi["merged_count"] - lo["merged_count"]) / lo["merged_count"]
    d1_span = abs(hi["D1"] - lo["D1"]) / lo["D1"]
    assert count_span > d1_span
    assert count_span > 0.50
    assert d1_span < 0.15
    assert base["merged_count"] == 22


def test_write_erb_fraction_sensitivity_doc() -> None:
    freqs, amps = _harmonic_series()
    d1_unmerged = float(hill_profile(amps)["D1"])
    series_rows = {frac: _profile(freqs, amps, frac) for frac in ERB_FRACTIONS}
    register_rows = {}
    for f0 in REGISTER_F0_HZ:
        ff, aa = _harmonic_series(f0=f0)
        register_rows[f0] = _profile(ff, aa, 1.0)

    d1_holds = [
        frac
        for frac, row in series_rows.items()
        if abs(row["D1"] - d1_unmerged) <= RECOVERY_REL * d1_unmerged
    ]
    count_holds = [
        frac for frac, row in series_rows.items() if row["merged_count"] == HARMONIC_N
    ]
    lo = series_rows[0.25]
    hi = series_rows[2.0]
    count_span = 100.0 * abs(hi["merged_count"] - lo["merged_count"]) / lo["merged_count"]
    d1_span = 100.0 * abs(hi["D1"] - lo["D1"]) / lo["D1"]

    stage1_rows = {}
    if STAGE1_CACHE.is_file():
        stage1_rows = json.loads(STAGE1_CACHE.read_text(encoding="utf-8")).get(
            "rows", {}
        )
        stage1_rows = {float(k): v for k, v in stage1_rows.items()}

    lines = [
        "# ACD `erb_fraction` sensitivity",
        "",
        "The previous sweep placed tones 8 ERB apart, which cannot merge at "
        "any `erb_fraction <= 1.5`. That test could not fail, so the claim "
        "\"usable range at least [0.5, 1.5]\" is **unsupported and discarded**.",
        "",
        "This document uses a 40-partial 1/n series at f0 = 146.83 Hz, where "
        "adjacent partials first fall inside one ERB at partial 8 "
        "(`146.83 <= 0.108 f + 24.7` gives `f >= 1131 Hz`). Merge strategy is "
        f"the Task 1 default **`{MERGE_STRATEGY_DEFAULT}`**. Default "
        "`erb_fraction` remains 1.0.",
        "",
        "## Reference merged counts (both strategies)",
        "",
        "| erb_fraction | moving centroid | fixed grid |",
        "|---:|---:|---:|",
    ]
    for frac, exp in REFERENCE_COUNTS.items():
        lines.append(
            f"| {frac:g} | {exp['moving_centroid']} | {exp['fixed_erb_grid']} |"
        )

    lines += [
        "",
        "## Harmonic series at f0 = 146.83 Hz (`fixed_erb_grid`)",
        "",
        f"Unmerged D1 = {d1_unmerged:.3f}. D1 == N=40 does not hold at any "
        "tested fraction: a 1/n law already concentrates energy, so D1 is a "
        "dominance-weighted count, not the raw partial census.",
        "",
        "| erb_fraction | merged_count | D0 | D1 | D2 |",
        "|---:|---:|---:|---:|---:|",
    ]
    for frac in ERB_FRACTIONS:
        row = series_rows[frac]
        lines.append(
            f"| {frac:g} | {row['merged_count']} | {row['D0']:.3f} | "
            f"{row['D1']:.3f} | {row['D2']:.3f} |"
        )

    d1_range = (
        f"[{min(d1_holds):g}, {max(d1_holds):g}]" if d1_holds else "empty"
    )
    count_range = (
        f"[{min(count_holds):g}, {max(count_holds):g}]" if count_holds else "empty"
    )
    lines += [
        "",
        "## K-recovery on this series",
        "",
        f"- `merged_count == 40` (every partial still resolved): {count_range}.",
        f"- `D1` within 1 % of the unmerged 1/n value {d1_unmerged:.3f}: "
        f"{d1_range}.",
        "- `D1 == 40` within 1 %: **never**, including at `erb_fraction = 0.25` "
        "where nothing merges.",
        "",
        f"`merged_count` is the more sensitive parameter: from "
        f"`erb_fraction = 0.25` to `2.0` it changes by {count_span:.1f}%, "
        f"while D1 changes by {d1_span:.1f}%. D2 is nearly flat "
        f"({series_rows[0.25]['D2']:.3f} → {series_rows[2.0]['D2']:.3f}), "
        "which is the saturation documented in `ACD_THEORY.md`.",
        "",
        "## Register dependence (fixed 40-partial 1/n, `erb_fraction = 1.0`)",
        "",
        "Merging is register-dependent by design: upper partials of low notes "
        "are unresolved and should merge. That effect will appear in any "
        "corpus result as an apparent correlation between density and pitch.",
        "",
        "| f0 (Hz) | merged_count | D1 | D2 |",
        "|---:|---:|---:|---:|",
    ]
    for f0 in REGISTER_F0_HZ:
        row = register_rows[f0]
        lines.append(
            f"| {f0:g} | {row['merged_count']} | {row['D1']:.3f} | "
            f"{row['D2']:.3f} |"
        )
    d1_lo = register_rows[REGISTER_F0_HZ[0]]["D1"]
    d1_hi = register_rows[REGISTER_F0_HZ[-1]]["D1"]
    lines += [
        "",
        f"D1 rises from {d1_lo:.3f} at 65.4 Hz to {d1_hi:.3f} at 1046.5 Hz "
        f"({100.0 * (d1_hi / d1_lo - 1.0):+.1f}%) at fixed harmonic structure. "
        "The low-note merged count is smaller because more upper partials "
        "share an ERB-rate bin.",
        "",
        "## Synthesised D3 through Stage 1",
        "",
    ]
    if not stage1_rows:
        lines += [
            "Stage 1 peak-list sweep is not in this checkout. Generate it with "
            "`test_generate_erb_fraction_stage1_d3` (slow).",
            "",
        ]
    else:
        lines += [
            "Same synthesised D3 as the merge-strategy sweep, scored under "
            f"`{MERGE_STRATEGY_DEFAULT}` at production `n_fft = 8192`.",
            "",
            "| erb_fraction | merged_H+I+S | ACD_score (D1) | ACD_D1 | ACD_D2 |",
            "|---:|---:|---:|---:|---:|",
        ]
        for frac in ERB_FRACTIONS:
            row = stage1_rows[frac]
            lines.append(
                f"| {frac:g} | {row['merged_total']:.0f} | "
                f"{fmt(row['ACD_score'])} | {fmt(row['ACD_D1'])} | "
                f"{fmt(row['ACD_D2'])} |"
            )
        lines.append("")

    lines += [
        "## Cross-reference",
        "",
        "Default `ERB_FRACTION_DEFAULT = 1.0` is unchanged. See "
        "`docs/CONSTANTS_PROVENANCE.md` and `docs/validation/ACD_MERGE_STRATEGY.md`.",
        "",
    ]
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(lines), encoding="utf-8")
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "unsupported and discarded" in text
    assert "Register dependence" in text
    assert "1/n" in text


def generate_stage1_erb_fraction_payload(work: Path) -> dict:
    from tests.phase_32.test_acd_real_note_invariance import (
        PRODUCTION_DB_MIN,
        PRODUCTION_N_FFT,
        _run_stage1,
        _write_cello_like_d3,
    )
    from tools.acd_research_integration import compute_acd_row_from_workbook

    audio = _write_cello_like_d3(work / "audio" / "ORC_Vlc_arco_mf_D3.wav")
    _run_stage1(
        audio, work / "stage1", n_fft=PRODUCTION_N_FFT, db_min=PRODUCTION_DB_MIN
    )
    wb = next((work / "stage1").rglob("spectral_analysis.xlsx"))
    rows = {}
    for frac in ERB_FRACTIONS:
        row = compute_acd_row_from_workbook(
            wb,
            erb_fraction=frac,
            merge_strategy=MERGE_STRATEGY_DEFAULT,
        )
        rows[str(frac)] = {
            "ACD_score": float(row["ACD_score"]),
            "ACD_D1": float(row["ACD_D1"]),
            "ACD_D2": float(row["ACD_D2"]),
            "merged_h": float(row["ACD_count_merged_harmonic"]),
            "merged_i": float(row["ACD_count_merged_inharmonic"]),
            "merged_s": float(row["ACD_count_merged_subbass"]),
            "merged_total": float(
                row["ACD_count_merged_harmonic"]
                + row["ACD_count_merged_inharmonic"]
                + row["ACD_count_merged_subbass"]
            ),
        }
    return {"n_fft": PRODUCTION_N_FFT, "merge_strategy": MERGE_STRATEGY_DEFAULT, "rows": rows}


@pytest.mark.slow
@pytest.mark.timeout(300)
def test_generate_erb_fraction_stage1_d3(tmp_path: Path) -> None:
    payload = generate_stage1_erb_fraction_payload(tmp_path)
    STAGE1_CACHE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    test_write_erb_fraction_sensitivity_doc()
    assert "ACD_score (D1)" in DOC_PATH.read_text(encoding="utf-8")
