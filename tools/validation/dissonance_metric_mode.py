#!/usr/bin/env python3
"""Compare dissonance metric modes and H&K eq. (3) vs the legacy export.

Writes ``docs/validation/DISSONANCE_METRIC_MODE.md`` and a golden JSON.
Uses synthetic 1/n series at the committed cello register (audio not required).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from dissonance_models import (
    DEFAULT_DISSONANCE_METRIC_MODE,
    DISSONANCE_METRIC_MODES,
    HutchinsonKnopoffDissonance,
    SetharesDissonance,
    VassilakisDissonance,
)
from tools.validation.hk_subbass_bandwidth import _note_to_f0_hz

ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = ROOT / "docs" / "validation" / "DISSONANCE_METRIC_MODE.md"
GOLDEN_PATH = ROOT / "tests" / "phase_33" / "golden" / "dissonance_round5.json"
N_PARTIALS = 20
PEAK_COUNTS = (5, 10, 20, 40)
PEAK_F0_HZ = 146.83


def _series_df(f0: float, n: int = N_PARTIALS) -> pd.DataFrame:
    idx = np.arange(1, int(n) + 1, dtype=float)
    return pd.DataFrame(
        {"Frequency (Hz)": f0 * idx, "Amplitude": 1.0 / idx}
    )


def _legacy_sethares_override(
    model: SetharesDissonance, df: pd.DataFrame
) -> float:
    """Exact pre-4.6.0 Sethares override (pure-Python O(n^2) loop)."""
    if df is None or df.empty:
        return 0.0
    if "Frequency (Hz)" not in df.columns or (
        "Amplitude" not in df.columns and "Magnitude (dB)" not in df.columns
    ):
        return 0.0
    dfx = df.copy()
    if "Amplitude" not in dfx.columns:
        dfx["Amplitude"] = 10 ** (dfx["Magnitude (dB)"] / 20)
    dfx = dfx[(dfx["Frequency (Hz)"] > 0) & (dfx["Amplitude"] > 0)]
    freqs = dfx["Frequency (Hz)"].to_numpy(dtype=float)
    amps = dfx["Amplitude"].to_numpy(dtype=float)
    n = len(freqs)
    if n < 2:
        return 0.0
    total = 0.0
    n_pairs = 0
    sum_minamp = 0.0
    for i in range(n - 1):
        for j in range(i + 1, n):
            a_min = amps[i] if amps[i] < amps[j] else amps[j]
            sum_minamp += a_min
            total += model.pure_tones_dissonance(freqs[i], freqs[j], amps[i], amps[j])
            n_pairs += 1
    if n_pairs <= 0:
        return 0.0
    if model.metric_mode == "sum":
        return float(total)
    if model.metric_mode == "mean_pair":
        return float(total / n_pairs)
    if model.metric_mode == "minamp_norm":
        return float(total / sum_minamp) if sum_minamp > 0 else 0.0
    return float((total / n_pairs) * model.metric_scale)


def _rank(values: list[float]) -> list[int]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0] * len(values)
    for r, i in enumerate(order):
        ranks[i] = r
    return ranks


def _spearman(a: list[float], b: list[float]) -> float:
    ra = np.asarray(_rank(a), dtype=float)
    rb = np.asarray(_rank(b), dtype=float)
    ra = ra - ra.mean()
    rb = rb - rb.mean()
    denom = float(np.sqrt(np.sum(ra * ra) * np.sum(rb * rb)))
    if denom <= 0:
        return float("nan")
    return float(np.sum(ra * rb) / denom)


def build_payload() -> dict:
    notes = json.loads(
        (
            ROOT / "tests" / "phase_11" / "fixtures" / "ewsd_corpus_reference.json"
        ).read_text(encoding="utf-8")
    )["notes"]
    register = [
        {"note": str(item["Note"]), "f0": _note_to_f0_hz(str(item["Note"]))}
        for item in notes
    ]
    vass = VassilakisDissonance()
    hk = HutchinsonKnopoffDissonance()

    rows = []
    for item in register:
        df = _series_df(item["f0"])
        seth_modes = {
            mode: float(
                SetharesDissonance(metric_mode=mode).calculate_dissonance_metric(
                    df, metric_mode=mode
                )
            )
            for mode in DISSONANCE_METRIC_MODES
        }
        rows.append(
            {
                "note": item["note"],
                "f0": item["f0"],
                "sethares": seth_modes,
                "vassilakis_minamp_norm": float(
                    vass.calculate_dissonance_metric(df)
                ),
                "hk_eq3": float(hk.calculate_dissonance_metric(df)),
                "hk_legacy_mean_pair_scaled": float(
                    hk.legacy_mean_pair_scaled_dissonance(df)
                ),
            }
        )

    peak_rows = []
    for n in PEAK_COUNTS:
        df = _series_df(PEAK_F0_HZ, n)
        peak_rows.append(
            {
                "n_partials": n,
                "n_pairs": n * (n - 1) // 2,
                "sethares": {
                    mode: float(
                        SetharesDissonance(metric_mode=mode).calculate_dissonance_metric(
                            df, metric_mode=mode
                        )
                    )
                    for mode in DISSONANCE_METRIC_MODES
                },
            }
        )

    # Same f0, varying peak count: mean_pair_scaled ranks the sparse
    # spectrum highest; minamp_norm ranks the dense spectrum highest.
    mixed_spec = tuple(
        (f"D3_n{n}", PEAK_F0_HZ, n) for n in PEAK_COUNTS
    )
    mixed_rows = []
    for name, f0, n in mixed_spec:
        df = _series_df(f0, n)
        mixed_rows.append(
            {
                "note": name,
                "f0": f0,
                "n_partials": n,
                "sethares_minamp_norm": float(
                    SetharesDissonance().calculate_dissonance_metric(
                        df, metric_mode="minamp_norm"
                    )
                ),
                "sethares_mean_pair_scaled": float(
                    SetharesDissonance(metric_mode="mean_pair_scaled").calculate_dissonance_metric(
                        df, metric_mode="mean_pair_scaled"
                    )
                ),
                "hk_eq3": float(hk.calculate_dissonance_metric(df)),
                "hk_legacy_mean_pair_scaled": float(
                    hk.legacy_mean_pair_scaled_dissonance(df)
                ),
            }
        )
    mixed_seth_new = [r["sethares_minamp_norm"] for r in mixed_rows]
    mixed_seth_old = [r["sethares_mean_pair_scaled"] for r in mixed_rows]
    mixed_hk_new = [r["hk_eq3"] for r in mixed_rows]
    mixed_hk_old = [r["hk_legacy_mean_pair_scaled"] for r in mixed_rows]

    seth_default = [r["sethares"][DEFAULT_DISSONANCE_METRIC_MODE] for r in rows]
    seth_legacy = [r["sethares"]["mean_pair_scaled"] for r in rows]
    hk_new = [r["hk_eq3"] for r in rows]
    hk_old = [r["hk_legacy_mean_pair_scaled"] for r in rows]
    rank_moved_seth = sum(
        1 for a, b in zip(_rank(seth_default), _rank(seth_legacy)) if a != b
    )
    rank_moved_hk = sum(1 for a, b in zip(_rank(hk_new), _rank(hk_old)) if a != b)

    equivalence = []
    for item in register[:8]:
        df = _series_df(item["f0"])
        for mode in DISSONANCE_METRIC_MODES:
            model = SetharesDissonance(metric_mode=mode)
            base = float(model.calculate_dissonance_metric(df, metric_mode=mode))
            old = _legacy_sethares_override(model, df)
            equivalence.append(
                {
                    "note": item["note"],
                    "mode": mode,
                    "base": base,
                    "legacy_override": old,
                    "abs_diff": abs(base - old),
                }
            )

    return {
        "default_metric_mode": DEFAULT_DISSONANCE_METRIC_MODE,
        "n_notes": len(rows),
        "n_partials": N_PARTIALS,
        "register": rows,
        "peak_count_sweep": peak_rows,
        "sethares_rank_spearman_minamp_vs_mean_pair_scaled": _spearman(
            seth_default, seth_legacy
        ),
        "sethares_rank_moves": rank_moved_seth,
        "hk_rank_spearman_eq3_vs_legacy": _spearman(hk_new, hk_old),
        "hk_rank_moves": rank_moved_hk,
        "hk_median_ratio_eq3_over_legacy": float(
            np.median(np.asarray(hk_new) / np.maximum(np.asarray(hk_old), 1e-30))
        ),
        "seth_median_ratio_minamp_over_mean_pair_scaled": float(
            np.median(
                np.asarray(seth_default) / np.maximum(np.asarray(seth_legacy), 1e-30)
            )
        ),
        "sethares_override_equivalence": equivalence,
        "mixed_peak_count": mixed_rows,
        "mixed_sethares_rank_moves": sum(
            1 for a, b in zip(_rank(mixed_seth_new), _rank(mixed_seth_old)) if a != b
        ),
        "mixed_hk_rank_moves": sum(
            1 for a, b in zip(_rank(mixed_hk_new), _rank(mixed_hk_old)) if a != b
        ),
        "mixed_sethares_rank_spearman": _spearman(mixed_seth_new, mixed_seth_old),
        "mixed_hk_rank_spearman": _spearman(mixed_hk_new, mixed_hk_old),
    }


def write_markdown(payload: dict) -> Path:
    lines = [
        "# Dissonance metric-mode comparison",
        "",
        "Default export mode is now **`minamp_norm`**. `mean_pair_scaled` divided",
        "by `n_pairs ~ n²/2` while only near-neighbour pairs contribute, so the",
        "scalar fell as detected peak count rose. That confounds texture studies:",
        "spectra dense in partials were assigned *lower* roughness.",
        "`minamp_norm` is invariant to peak count and to a global amplitude scale.",
        "Every row exports `dissonance_metric_mode`.",
        "",
        f"Synthetic 1/n series, {payload['n_partials']} partials, on the committed",
        f"{payload['n_notes']}-note cello register (audio not required).",
        "",
        f"- Sethares rank Spearman (`minamp_norm` vs `mean_pair_scaled`): "
        f"**{payload['sethares_rank_spearman_minamp_vs_mean_pair_scaled']:.3f}**",
        f"- Sethares notes whose rank moved: **{payload['sethares_rank_moves']}** / "
        f"{payload['n_notes']}",
        f"- Median Sethares `minamp_norm` / `mean_pair_scaled`: "
        f"**{payload['seth_median_ratio_minamp_over_mean_pair_scaled']:.3f}**",
        f"- H&K rank Spearman (eq. 3 vs legacy mean-pair): "
        f"**{payload['hk_rank_spearman_eq3_vs_legacy']:.3f}**",
        f"- H&K notes whose rank moved: **{payload['hk_rank_moves']}** / "
        f"{payload['n_notes']}",
        f"- Median H&K eq. 3 / legacy: "
        f"**{payload['hk_median_ratio_eq3_over_legacy']:.3f}**",
        "",
        "Equal-n 1/n series share `n_pairs` and the amplitude vector, so",
        "`minamp_norm` and `mean_pair_scaled` are monotonic in the same pair",
        "sum and **ranks do not move**. The texture confound appears when peak",
        "count varies (below).",
        "",
        "## Variable peak count (texture confound)",
        "",
        "Same f0 (146.83 Hz), n = 5/10/20/40. `mean_pair_scaled` ranks the ",
        "sparse spectrum first; `minamp_norm` ranks the dense spectrum first.",
        "",
        f"Sethares rank moves: **{payload['mixed_sethares_rank_moves']}** / 4 "
        f"(Spearman {payload['mixed_sethares_rank_spearman']:.3f}). "
        f"H&K rank moves: **{payload['mixed_hk_rank_moves']}** / 4 "
        f"(Spearman {payload['mixed_hk_rank_spearman']:.3f}).",
        "",
        "| Note | f0 | n | Sethares minamp_norm | Sethares mean_pair_scaled | HK eq.3 | HK legacy |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["mixed_peak_count"]:
        lines.append(
            f"| {row['note']} | {row['f0']:.2f} | {row['n_partials']} | "
            f"{row['sethares_minamp_norm']:.6g} | "
            f"{row['sethares_mean_pair_scaled']:.6g} | "
            f"{row['hk_eq3']:.6g} | {row['hk_legacy_mean_pair_scaled']:.6g} |"
        )
    lines.extend(
        [
            "",
            "## Peak-count dependence (D3 stand-in, 146.83 Hz)",
            "",
            "| n | n_pairs | sum | mean_pair | mean_pair_scaled | minamp_norm |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in payload["peak_count_sweep"]:
        s = row["sethares"]
        lines.append(
            f"| {row['n_partials']} | {row['n_pairs']} | {s['sum']:.6g} | "
            f"{s['mean_pair']:.6g} | {s['mean_pair_scaled']:.6g} | "
            f"{s['minamp_norm']:.6g} |"
        )
    lines.extend(
        [
            "",
            "`mean_pair` / `mean_pair_scaled` fall as n rises. `minamp_norm` does not.",
            "",
            "## Register (Sethares four modes + H&K)",
            "",
            "| Note | f0 | sum | mean_pair | mean_pair_scaled | minamp_norm | HK eq.3 | HK legacy |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in payload["register"]:
        s = row["sethares"]
        lines.append(
            f"| {row['note']} | {row['f0']:.2f} | {s['sum']:.6g} | "
            f"{s['mean_pair']:.6g} | {s['mean_pair_scaled']:.6g} | "
            f"{s['minamp_norm']:.6g} | {row['hk_eq3']:.6g} | "
            f"{row['hk_legacy_mean_pair_scaled']:.6g} |"
        )
    lines.extend(
        [
            "",
            "See `docs/validation/DISSONANCE_MIGRATION.md` for the 4.6.0 column map.",
            "",
        ]
    )
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(lines), encoding="utf-8")
    return DOC_PATH


def write_golden(payload: dict) -> Path:
    GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    slim = {
        "default_metric_mode": payload["default_metric_mode"],
        "n_notes": payload["n_notes"],
        "sethares_rank_spearman_minamp_vs_mean_pair_scaled": payload[
            "sethares_rank_spearman_minamp_vs_mean_pair_scaled"
        ],
        "sethares_rank_moves": payload["sethares_rank_moves"],
        "hk_rank_spearman_eq3_vs_legacy": payload["hk_rank_spearman_eq3_vs_legacy"],
        "hk_rank_moves": payload["hk_rank_moves"],
        "hk_median_ratio_eq3_over_legacy": payload["hk_median_ratio_eq3_over_legacy"],
        "seth_median_ratio_minamp_over_mean_pair_scaled": payload[
            "seth_median_ratio_minamp_over_mean_pair_scaled"
        ],
        "peak_count_sweep": payload["peak_count_sweep"],
        "register": [
            {
                "note": r["note"],
                "f0": r["f0"],
                "sethares_minamp_norm": r["sethares"]["minamp_norm"],
                "sethares_mean_pair_scaled": r["sethares"]["mean_pair_scaled"],
                "hk_eq3": r["hk_eq3"],
                "hk_legacy_mean_pair_scaled": r["hk_legacy_mean_pair_scaled"],
            }
            for r in payload["register"]
        ],
        "sethares_override_equivalence_max_abs_diff": max(
            x["abs_diff"] for x in payload["sethares_override_equivalence"]
        ),
        "mixed_peak_count": payload["mixed_peak_count"],
        "mixed_sethares_rank_moves": payload["mixed_sethares_rank_moves"],
        "mixed_hk_rank_moves": payload["mixed_hk_rank_moves"],
    }
    GOLDEN_PATH.write_text(json.dumps(slim, indent=2) + "\n", encoding="utf-8")
    return GOLDEN_PATH


def main() -> None:
    payload = build_payload()
    print(write_markdown(payload))
    print(write_golden(payload))


if __name__ == "__main__":
    main()
