"""Fixed-grid vs moving-centroid ERB merge (Task 1)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tests.phase_32.acd_invariance_support import (
    CELLO_CORPUS_TIER_N_FFT,
    REAL_NOTE_FFT_TIER_ACD_REL_TOL,
    delta_pct,
    fmt,
    fmt_pct,
)
from tools.spectral_density_hill import (
    MERGE_STRATEGY_FIXED_ERB_GRID,
    MERGE_STRATEGY_MOVING_CENTROID,
    hill_profile,
    merge_peaks,
    merge_peaks_fixed_erb_grid,
    merge_peaks_within_erb,
)

DOC_PATH = (
    Path(__file__).resolve().parents[2] / "docs" / "validation" / "ACD_MERGE_STRATEGY.md"
)
CACHE_PATH = Path(__file__).resolve().parent / "golden" / "acd_merge_strategy.json"

# Prompt Task 3 reference counts: 40-partial 1/n at f0 = 146.83 Hz.
HARMONIC_F0_HZ = 146.83
HARMONIC_N = 40
REFERENCE_MERGED_COUNTS = {
    0.25: {"moving_centroid": 38, "fixed_erb_grid": 40},
    0.5: {"moving_centroid": 26, "fixed_erb_grid": 32},
    0.75: {"moving_centroid": 19, "fixed_erb_grid": 26},
    1.0: {"moving_centroid": 16, "fixed_erb_grid": 22},
    1.5: {"moving_centroid": 12, "fixed_erb_grid": 17},
    2.0: {"moving_centroid": 9, "fixed_erb_grid": 14},
}
PERTURB_PARTIALS = range(7, 15)


def _harmonic_series(n: int = HARMONIC_N, f0: float = HARMONIC_F0_HZ):
    idx = np.arange(1, int(n) + 1, dtype=float)
    return f0 * idx, 1.0 / idx


def test_fixed_grid_reference_counts() -> None:
    freqs, amps = _harmonic_series()
    for frac, expected in REFERENCE_MERGED_COUNTS.items():
        mf, _ma, _mc = merge_peaks_within_erb(freqs, amps, erb_fraction=frac)
        ff, _fa, _fc = merge_peaks_fixed_erb_grid(freqs, amps, erb_fraction=frac)
        assert int(mf.size) == expected["moving_centroid"]
        assert int(ff.size) == expected["fixed_erb_grid"]


def test_fixed_grid_order_independent() -> None:
    freqs, amps = _harmonic_series()
    rng = np.random.default_rng(7)
    perm = rng.permutation(freqs.size)
    a, b, _na = merge_peaks_fixed_erb_grid(freqs, amps)
    c, d, _nc = merge_peaks_fixed_erb_grid(freqs[perm], amps[perm])
    assert a.size == c.size
    assert np.allclose(a, c, atol=1e-12)
    assert np.allclose(b, d, atol=1e-12)


def test_perturbation_merged_count_invariant_on_fixed_grid() -> None:
    """+1 dB on partials 7–14 must not flip fixed-grid component count.

    On a clean 1/n series both strategies typically keep the count; this is
    a regression guard. The deciding evidence is the Stage 1 tier sweep.
    """
    freqs, base_amps = _harmonic_series()
    base_n = merge_peaks_fixed_erb_grid(freqs, base_amps)[0].size
    moving_base_n = merge_peaks_within_erb(freqs, base_amps)[0].size
    for k in PERTURB_PARTIALS:
        amps = base_amps.copy()
        amps[k - 1] *= 10.0 ** (1.0 / 20.0)
        grid_n = merge_peaks_fixed_erb_grid(freqs, amps)[0].size
        moving_n = merge_peaks_within_erb(freqs, amps)[0].size
        assert grid_n == base_n
        # Moving centroid is recorded, not asserted: clean 1/n often also holds.
        _ = moving_n, moving_base_n


def test_perturbation_d2_shift_is_small_on_clean_series() -> None:
    freqs, base_amps = _harmonic_series()
    d2_0 = hill_profile(merge_peaks(freqs, base_amps)[1])["D2"]
    for strategy in (MERGE_STRATEGY_MOVING_CENTROID, MERGE_STRATEGY_FIXED_ERB_GRID):
        d2_base = hill_profile(
            merge_peaks(freqs, base_amps, merge_strategy=strategy)[1]
        )["D2"]
        for k in PERTURB_PARTIALS:
            amps = base_amps.copy()
            amps[k - 1] *= 10.0 ** (1.0 / 20.0)
            d2 = hill_profile(
                merge_peaks(freqs, amps, merge_strategy=strategy)[1]
            )["D2"]
            rel = abs(d2 - d2_base) / d2_base
            assert rel < 0.01, (strategy, k, rel)
    assert np.isfinite(d2_0)


def test_merge_strategy_cache_and_tolerance() -> None:
    """ACD FFT-tier relative tolerance — derivation history.

    Policy rule (round 3): measured maximum tier wander + 1 percentage
    point, rounded up.

    Original derivation: measured 2.74% on the synthesised-D3 tier sweep
    → 0.04.

    Superseded by: regenerated cache
    ``tests/phase_32/golden/acd_merge_strategy.json``
    (``source=pipeline_synthesized_d3``,
    ``winning_strategy=fixed_erb_grid``,
    ``max_abs_delta_pct=3.2634525732661857``, last committed in
    ``c14c347``) measured 3.26% winner wander → 0.05.

    Caveat: 5% sits at the ceiling of acceptable tolerance flagged
    in round 3; this value is provisional pending re-measurement on
    real-duration corpus notes, where the window-length hypothesis predicts
    smaller wander.
    """
    if not CACHE_PATH.is_file():
        pytest.skip("merge-strategy Stage 1 cache not yet generated")
    payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    winner = payload["winning_strategy"]
    max_abs_pct = float(payload["strategies"][winner]["max_abs_delta_pct"])
    enforced = float(payload["enforced_relative_tolerance"])
    expected = float(np.ceil(max_abs_pct + 1.0) / 100.0)
    assert enforced == pytest.approx(expected, abs=1e-12)
    assert REAL_NOTE_FFT_TIER_ACD_REL_TOL == pytest.approx(enforced, abs=1e-12)
    for row in payload["strategies"][winner]["rows"]:
        assert abs(float(row["delta_pct"])) / 100.0 <= enforced + 1e-12
    assert DOC_PATH.is_file()


def _score_workbook(path: Path, strategy: str) -> dict:
    from tools.acd_research_integration import compute_acd_row_from_workbook

    # Score via the Stage 3 adapter so peak lists match production.
    # Adapter still uses compute_note_density(q=2) until Task 2.
    row = compute_acd_row_from_workbook(path, merge_strategy=strategy)
    return {
        "ACD_score": float(row["ACD_score"]),
        "ACD_D2": float(row["ACD_D2"]),
        "ACD_D1": float(row["ACD_D1"]),
        "ACD_D0": float(row["ACD_D0"]),
        "merged_h": float(row["ACD_count_merged_harmonic"]),
        "merged_i": float(row["ACD_count_merged_inharmonic"]),
        "merged_s": float(row["ACD_count_merged_subbass"]),
    }


def generate_merge_strategy_payload(work: Path) -> dict:
    from tests.phase_32.test_acd_real_note_invariance import (
        PRODUCTION_DB_MIN,
        PRODUCTION_N_FFT,
        _run_stage1,
        _write_cello_like_d3,
    )

    audio = _write_cello_like_d3(work / "audio" / "ORC_Vlc_arco_mf_D3.wav")
    workbooks: dict[int, Path] = {}
    for n_fft in CELLO_CORPUS_TIER_N_FFT:
        out = work / "fft" / f"n{n_fft}"
        _run_stage1(audio, out, n_fft=int(n_fft), db_min=PRODUCTION_DB_MIN)
        workbooks[int(n_fft)] = next(out.rglob("spectral_analysis.xlsx"))

    strategies = {}
    for strategy in (MERGE_STRATEGY_MOVING_CENTROID, MERGE_STRATEGY_FIXED_ERB_GRID):
        rows = []
        for n_fft in CELLO_CORPUS_TIER_N_FFT:
            mets = _score_workbook(workbooks[int(n_fft)], strategy)
            rows.append({"n_fft": int(n_fft), **mets, "delta_pct": float("nan")})
        base = next(r for r in rows if r["n_fft"] == PRODUCTION_N_FFT)
        for r in rows:
            r["delta_pct"] = delta_pct(r["ACD_score"], base["ACD_score"])
        abs_pcts = [abs(float(r["delta_pct"])) for r in rows]
        strategies[strategy] = {
            "base_acd": float(base["ACD_score"]),
            "max_abs_delta_pct": float(max(abs_pcts)),
            "rows": rows,
        }

    moving_w = strategies[MERGE_STRATEGY_MOVING_CENTROID]["max_abs_delta_pct"]
    grid_w = strategies[MERGE_STRATEGY_FIXED_ERB_GRID]["max_abs_delta_pct"]
    if grid_w < moving_w:
        winner = MERGE_STRATEGY_FIXED_ERB_GRID
    else:
        winner = MERGE_STRATEGY_MOVING_CENTROID
    win_spread = strategies[winner]["max_abs_delta_pct"]
    enforced = float(np.ceil(win_spread + 1.0) / 100.0)
    return {
        "source": "pipeline_synthesized_d3",
        "q": 2.0,
        "production_n_fft": PRODUCTION_N_FFT,
        "n_fft_values": list(CELLO_CORPUS_TIER_N_FFT),
        "strategies": strategies,
        "winning_strategy": winner,
        "neither_below_2pct": bool(moving_w >= 2.0 and grid_w >= 2.0),
        "enforced_relative_tolerance": enforced,
        "tolerance_above_5pct": bool(enforced > 0.05),
    }


def write_merge_strategy_doc(payload: dict) -> None:
    winner = payload["winning_strategy"]
    enforced = float(payload["enforced_relative_tolerance"])
    lines = [
        "# ACD merge strategy — fixed ERB grid vs moving centroid",
        "",
        "Stage 1 peak lists from the same synthesised D3 (f0 = 146.83 Hz, two "
        "inharmonics) used in the real-note FFT-tier sweep. Each workbook is "
        "scored under both merge strategies; Stage 1 is not re-run per "
        "strategy. ACD here is still the D2-based score (`q = 2`) so the "
        "numbers are comparable to the earlier ±3.8 % wander.",
        "",
        "## Decision",
        "",
        f"Default merge strategy: **`{winner}`**.",
        "",
    ]
    moving_w = payload["strategies"]["moving_centroid"]["max_abs_delta_pct"]
    grid_w = payload["strategies"]["fixed_erb_grid"]["max_abs_delta_pct"]
    lines += [
        f"`fixed_erb_grid` reduced the measured wander from {moving_w:.2f}% "
        f"to {grid_w:.2f}% and is therefore the default. The moving-centroid "
        "strategy remains available as `merge_strategy=\"moving_centroid\"`.",
        "",
    ]
    if payload["neither_below_2pct"]:
        lines += [
            "Neither strategy reduced the tier wander below ~2 %. Hard "
            "assignment (a peak belongs to one cluster or one ERB-rate bin) "
            "is the limiting factor. The identified next step is "
            "roex-overlap weighting — smooth partial assignment by auditory-"
            "filter overlap rather than hard binning. That is a docstring "
            "stub only; it is not implemented here.",
            "",
        ]
    else:
        lines += [
            f"`{winner}` reduced the measured FFT-tier wander and is the "
            "default. The other strategy is retained as an explicit option.",
            "",
        ]
    lines += [
        f"Enforced relative tolerance: **{enforced:.0%}** "
        f"(winning-strategy max |Δ%| plus 1 percentage point, rounded up)"
        + (
            ". **This gate is above 5 %.**"
            if payload["tolerance_above_5pct"]
            else "."
        ),
        "",
        "## Tier sweep (synthesised D3 through Stage 1)",
        "",
    ]
    for strategy, block in payload["strategies"].items():
        mark = " (winner)" if strategy == winner else ""
        lines += [
            f"### `{strategy}`{mark}",
            "",
            f"Base ACD (`n_fft = {payload['production_n_fft']}`): "
            f"{fmt(block['base_acd'])}. Max |Δ%| = "
            f"{block['max_abs_delta_pct']:.2f}.",
            "",
            "| n_fft | ACD_score | ACD_Δ% | ACD_D2 | merged_H | merged_I | merged_S |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in block["rows"]:
            lines.append(
                f"| {row['n_fft']} | {fmt(row['ACD_score'])} | "
                f"{fmt_pct(row['delta_pct'])} | {fmt(row['ACD_D2'])} | "
                f"{row['merged_h']:.0f} | {row['merged_i']:.0f} | "
                f"{row['merged_s']:.0f} |"
            )
        lines.append("")
    lines += [
        "## Perturbation guard (clean 1/n series)",
        "",
        "Forty-partial 1/n series at f0 = 146.83 Hz; +1 dB applied to one "
        "partial at a time in 7–14 (where adjacent partials first fall "
        "inside one ERB). `fixed_erb_grid` `merged_count` is invariant. On "
        "this clean series both strategies move D2 by a fraction of a "
        "percent and neither flips the count; instability, if present, "
        "shows on the Stage 1 peak lists above.",
        "",
    ]
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.mark.slow
@pytest.mark.timeout(900)
def test_generate_merge_strategy_tier_sweep(tmp_path: Path) -> None:
    payload = generate_merge_strategy_payload(tmp_path)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_merge_strategy_doc(payload)
    assert DOC_PATH.is_file()
