#!/usr/bin/env python3
"""Emit roughness bandwidth-basis comparison tables and figures.

Author validation artefact. Does not declare the Zwicker default validated.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from mir_descriptors import (
    PL_CB_FRACTION,
    critical_bandwidth_zwicker_hz,
    erb_bandwidth_hz,
    roughness_parncutt_kernel,
    _legacy_conflated_bandwidth_hz,
)

ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = ROOT / "docs" / "validation" / "ROUGHNESS_BANDWIDTH_BASIS.md"
FIG_DIR = ROOT / "docs" / "validation" / "figures"
DATA_DIR = ROOT / "docs" / "validation" / "data"

F0_HZ = (65.4, 110.0, 146.83, 220.0, 440.0, 1000.0)
KERNELS = (
    ("legacy_conflated", "0.25 f + 24.7 (pre-round-3)"),
    ("erb", "0.25 · ERB (round 3)"),
    ("zwicker_cb", "0.25 · Zwicker CB (proposed default)"),
)
N_PARTIALS = 20
SWEEP_POINTS = 400


def _two_tone(f0: float, df: float, basis: str) -> float:
    return roughness_parncutt_kernel(
        np.asarray([f0, f0 + df], dtype=float),
        np.asarray([1.0, 1.0], dtype=float),
        bandwidth_basis=basis,
    )


def _harmonic_series(f0: float, n: int = N_PARTIALS):
    idx = np.arange(1, int(n) + 1, dtype=float)
    return f0 * idx, 1.0 / idx


def _peak_df(f0: float, basis: str) -> float:
    dfs = np.linspace(0.5, max(2.0 * f0, 400.0), SWEEP_POINTS)
    vals = np.array([_two_tone(f0, float(df), basis) for df in dfs])
    return float(dfs[int(np.argmax(vals))])


def _pl_reference_df(f0: float) -> float:
    return float(PL_CB_FRACTION * critical_bandwidth_zwicker_hz(np.asarray([f0]))[0])


def _maybe_corpus_rows() -> list[dict]:
    rows: list[dict] = []
    env = os.environ.get("ACD_REAL_NOTE_AUDIO", "").strip()
    if env:
        path = Path(env).expanduser()
        if path.is_file():
            rows.append({"note_id": path.stem, "path": str(path), "reachable": True})
    ewsd = os.environ.get("EWSD_CORPUS_AUDIO", "").strip()
    candidates = [Path(r"C:\Users\lmr20\Desktop\ORC_Vlc_arco_mf\_Sustains")]
    if ewsd:
        candidates.append(Path(ewsd).expanduser())
    for root in candidates:
        if root.is_dir():
            rows.append({"note_id": "(directory mounted)", "path": str(root), "reachable": True})
            break
    return rows


def write_figures(curves: dict) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for f0, data in curves.items():
        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        for basis, _label in KERNELS:
            dfs = data[basis]["df"]
            vals = data[basis]["val"]
            peak = float(np.max(vals)) if np.max(vals) > 0 else 1.0
            ax.plot(dfs, vals / peak, label=_label)
        ax.set_xlabel("Δf (Hz)")
        ax.set_ylabel("normalised roughness")
        ax.set_title(f"Two-tone roughness, f0 = {f0:g} Hz")
        ax.legend(fontsize=8)
        ax.set_xlim(0.0, float(f0))
        ax.grid(True, alpha=0.3)
        name = f"roughness_twotone_f0_{int(round(f0))}hz.png"
        dest = FIG_DIR / name
        fig.tight_layout()
        fig.savefig(dest, dpi=120)
        plt.close(fig)
        written.append(str(dest.relative_to(ROOT)).replace("\\", "/"))
    return written


def write_curve_tables(curves: dict) -> list[str]:
    """Full two-tone sweeps as CSV (author can overlay on published figures)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for f0, data in curves.items():
        name = f"roughness_twotone_f0_{int(round(f0))}hz.csv"
        dest = DATA_DIR / name
        dfs = np.asarray(data["legacy_conflated"]["df"], dtype=float)
        header = "df_hz,legacy_conflated,erb,zwicker_cb"
        rows = [header]
        for i, df in enumerate(dfs):
            rows.append(
                f"{df:.6g},"
                f"{float(data['legacy_conflated']['val'][i]):.8g},"
                f"{float(data['erb']['val'][i]):.8g},"
                f"{float(data['zwicker_cb']['val'][i]):.8g}"
            )
        dest.write_text("\n".join(rows) + "\n", encoding="utf-8")
        written.append(str(dest.relative_to(ROOT)).replace("\\", "/"))
    return written


def generate() -> dict:
    curves: dict[float, dict] = {}
    peaks: list[dict] = []
    series: list[dict] = []
    for f0 in F0_HZ:
        octave = np.linspace(0.5, float(f0), SWEEP_POINTS)
        curves[f0] = {}
        peak_row = {"f0": f0, "pl_ref_zwicker_025": _pl_reference_df(f0)}
        ser_row = {"f0": f0}
        for basis, _label in KERNELS:
            vals = np.array([_two_tone(f0, float(df), basis) for df in octave])
            curves[f0][basis] = {"df": octave, "val": vals}
            peak_row[basis] = _peak_df(f0, basis)
            freqs, amps = _harmonic_series(f0)
            ser_row[basis] = roughness_parncutt_kernel(
                freqs, amps, bandwidth_basis=basis
            )
        peaks.append(peak_row)
        series.append(ser_row)

    figures = write_figures(curves)
    tables = write_curve_tables(curves)
    corpus = _maybe_corpus_rows()
    return {
        "peaks": peaks,
        "series": series,
        "figures": figures,
        "tables": tables,
        "corpus": corpus,
        "curves": curves,
    }


def write_markdown(payload: dict) -> None:
    lines = [
        "# Roughness bandwidth basis — author validation artefact",
        "",
        "**Primary-source confirmation is outstanding.** This document compares",
        "three kernels so the author can read them against the published",
        "Plomp & Levelt (1965) dissonance curves. The default",
        "`bandwidth_basis=\"zwicker_cb\"` **may change** on that reading.",
        "Do not treat these numbers as a validated basis.",
        "",
        "Kernels:",
        "",
        "- `legacy_conflated`: `x = df / (0.25 f + 24.7)` (pre-round-3).",
        "- `erb`: `x = df / (0.25 · ERB(f))`, `ERB(f) = 0.108 f + 24.7` (round 3).",
        "- `zwicker_cb`: `x = df / (0.25 · CB_Z(f))`,",
        "  `CB_Z(f) = 25 + 75 (1 + 1.4 (f/1000)^2)^0.69` (Zwicker & Fastl, 2007).",
        "",
        "The ACD ERB helper in `tools/spectral_density_hill.py` is independent",
        "and was not imported here.",
        "",
        "## Quarter-bandwidth widths",
        "",
        "| f (Hz) | 0.25·ERB | 0.25·Zwicker CB | ratio Z/ERB |",
        "|---:|---:|---:|---:|",
    ]
    for f0 in F0_HZ:
        erb = float(PL_CB_FRACTION * erb_bandwidth_hz(np.asarray([f0]))[0])
        zw = float(PL_CB_FRACTION * critical_bandwidth_zwicker_hz(np.asarray([f0]))[0])
        lines.append(f"| {f0:g} | {erb:.2f} | {zw:.2f} | {zw / erb:.2f} |")

    lines += [
        "",
        "## Maximum-location table",
        "",
        "`df` of the two-tone peak (unit amplitudes). Plomp–Levelt reference",
        "column is **0.25 × Zwicker CB(f0)** — the conventional “~25% of a",
        "critical band” location on the Zwicker scale. At 1 kHz the published",
        "Plomp–Levelt maximum is near 30–40 Hz. These columns are for the",
        "author to compare with the 1965 figures; they are not a validation.",
        "",
        "| f0 (Hz) | legacy `0.25f+24.7` | 0.25·ERB | 0.25·Zwicker | PL ref (0.25·Zwicker CB) |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in payload["peaks"]:
        lines.append(
            f"| {row['f0']:g} | {row['legacy_conflated']:.2f} | "
            f"{row['erb']:.2f} | {row['zwicker_cb']:.2f} | "
            f"{row['pl_ref_zwicker_025']:.2f} |"
        )

    lines += [
        "",
        "## Corpus-register impact (20-partial 1/n series)",
        "",
        "Total pairwise roughness. Ratios are not a constant scale factor.",
        "",
        "| f0 (Hz) | legacy | ERB | Zwicker | ERB/Zwicker | legacy/Zwicker |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["series"]:
        z = float(row["zwicker_cb"])
        e = float(row["erb"])
        L = float(row["legacy_conflated"])
        lines.append(
            f"| {row['f0']:g} | {L:.6g} | {e:.6g} | {z:.6g} | "
            f"{e / z:.3f} | {L / z:.3f} |"
        )

    lines += [
        "",
        "## Two-tone curves",
        "",
        "Each PNG is normalised to its own maximum. Raw (unnormalised) sweeps",
        "are in `docs/validation/data/`. Compact table: roughness at selected",
        "Δf / f0 ratios for f0 = 146.83 Hz (unit amplitudes).",
        "",
    ]
    d3 = payload["curves"][146.83]
    dfs = np.asarray(d3["legacy_conflated"]["df"], dtype=float)
    lines += [
        "| Δf/f0 | Δf (Hz) | legacy | ERB | Zwicker |",
        "|---:|---:|---:|---:|---:|",
    ]
    for ratio in (0.02, 0.05, 0.10, 0.15, 0.17, 0.20, 0.25, 0.50, 1.00):
        target = ratio * 146.83
        idx = int(np.argmin(np.abs(dfs - target)))
        lines.append(
            f"| {ratio:.2f} | {dfs[idx]:.2f} | "
            f"{float(d3['legacy_conflated']['val'][idx]):.5g} | "
            f"{float(d3['erb']['val'][idx]):.5g} | "
            f"{float(d3['zwicker_cb']['val'][idx]):.5g} |"
        )
    lines += ["", "CSV sweeps:", ""]
    for table in payload["tables"]:
        lines.append(f"- `{table}`")
    lines += ["", "Figures:", ""]
    for fig in payload["figures"]:
        rel = Path(fig).name
        lines.append(f"- `docs/validation/figures/{rel}`")
        lines.append("")
        lines.append(f"![two-tone roughness](figures/{rel})")
        lines.append("")

    lines += [
        "## Real corpus notes",
        "",
    ]
    if not payload["corpus"]:
        lines += [
            "No corpus take was mounted (`ACD_REAL_NOTE_AUDIO` unset; default",
            "cello path absent). Task 4 remains gated.",
            "",
        ]
    else:
        lines += [
            "A path was visible; peak-list scoring of live notes is not run",
            "from this script (Stage 1 is out of scope here). Mounted:",
            "",
        ]
        for row in payload["corpus"]:
            lines.append(f"- `{row['note_id']}` — `{row['path']}`")
        lines.append("")

    lines += [
        "## Outstanding judgement",
        "",
        "The default may change after the author compares the figures with",
        "Plomp & Levelt (1965). Until then, treat `zwicker_cb` as a proposed",
        "default, not a validated one.",
        "",
    ]
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    payload = generate()
    write_markdown(payload)
    print(f"wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
