#!/usr/bin/env python3
"""Emit Hutchinson–Knopoff vs Zwicker CB comparison below 500 Hz.

Default arithmetic is unchanged (hk1978). Author decision on the hybrid
default is outstanding.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from dissonance_models import (
    HK_LOW_FREQUENCY_CUTOFF_HZ,
    HutchinsonKnopoffDissonance,
)
from mir_descriptors import critical_bandwidth_zwicker_hz

ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = ROOT / "docs" / "validation" / "HK_SUBBASS_BANDWIDTH.md"

FREQS_HZ = (
    20.0,
    30.0,
    40.0,
    50.0,
    65.4,
    80.0,
    100.0,
    110.0,
    146.83,
    200.0,
    250.0,
    300.0,
    400.0,
    500.0,
)


def _hk_cbw(f: float) -> float:
    return HutchinsonKnopoffDissonance.cbw(f, low_frequency_basis="hk1978")


def _zwicker_cbw(f: float) -> float:
    return float(critical_bandwidth_zwicker_hz(np.asarray([f]))[0])


def _corpus_mounted() -> bool:
    env = os.environ.get("ACD_REAL_NOTE_AUDIO", "").strip()
    if env and Path(env).expanduser().is_file():
        return True
    ewsd = os.environ.get("EWSD_CORPUS_AUDIO", "").strip()
    cello = Path(r"C:\Users\lmr20\Desktop\ORC_Vlc_arco_mf\_Sustains")
    if cello.is_dir():
        return True
    return bool(ewsd and Path(ewsd).expanduser().is_dir())


def _s_region_fixture() -> list[tuple[float, float]]:
    """Synthetic cello C2 sub-bass cluster (below f0 = 65.4 Hz)."""
    freqs = np.array([32.7, 41.2, 49.0, 55.0, 61.7], dtype=float)
    amps = 1.0 / np.arange(1, freqs.size + 1, dtype=float)
    return list(zip(freqs.tolist(), amps.tolist()))


def generate() -> dict:
    rows = []
    for f in FREQS_HZ:
        hk = _hk_cbw(f)
        zw = _zwicker_cbw(f)
        rows.append({"f": f, "hk": hk, "zwicker": zw, "ratio_zw_hk": zw / hk})

    hk_model = HutchinsonKnopoffDissonance(low_frequency_basis="hk1978")
    hy_model = HutchinsonKnopoffDissonance(
        low_frequency_basis="zwicker_below_200hz"
    )
    partials = _s_region_fixture()
    d_hk = hk_model.total_dissonance(partials, [])
    d_hy = hy_model.total_dissonance(partials, [])
    return {
        "rows": rows,
        "s_hk": d_hk,
        "s_hybrid": d_hy,
        "s_ratio": (d_hy / d_hk) if d_hk else float("nan"),
        "corpus": _corpus_mounted(),
    }


def write_markdown(payload: dict) -> None:
    lines = [
        "# Hutchinson–Knopoff sub-bass bandwidth",
        "",
        "`HutchinsonKnopoffDissonance.cbw` remains `1.72 · f^0.65` by default",
        "(`low_frequency_basis=\"hk1978\"`). At 50 Hz that is ~21.7 Hz against",
        "a Zwicker critical band near 100 Hz. The 1978 fit is known to degrade",
        "below ~200 Hz; sub-bass is a first-class H/I/S partition in this",
        "pipeline, so the S-region dissonance share is distorted by the same",
        "mechanism as the round-3 ERB roughness kernel.",
        "",
        "An optional `low_frequency_basis=\"zwicker_below_200hz\"` switches to",
        f"Zwicker CB below {HK_LOW_FREQUENCY_CUTOFF_HZ:.0f} Hz. ",
        "**Default arithmetic is unchanged.** Whether the hybrid should become the",
        "default is an author decision (CHANGES.md open item).",
        "",
        "The four previously noted defects in this file were not touched.",
        "",
        "## Bandwidth table (20–500 Hz)",
        "",
        "| f (Hz) | HK `1.72 f^0.65` | Zwicker CB | Zwicker / HK |",
        "|---:|---:|---:|---:|",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| {row['f']:g} | {row['hk']:.2f} | {row['zwicker']:.2f} | "
            f"{row['ratio_zw_hk']:.2f} |"
        )

    lines += [
        "",
        "## Synthetic S-region (cello C2 stand-in)",
        "",
        "Partials at 32.7, 41.2, 49.0, 55.0, 61.7 Hz with amplitudes 1/n.",
        "Corpus audio was not used for this row.",
        "",
        f"- HK 1978 total dissonance: `{payload['s_hk']:.6g}`",
        f"- Hybrid (Zwicker below 200 Hz): `{payload['s_hybrid']:.6g}`",
        f"- Hybrid / HK: `{payload['s_ratio']:.3f}`",
        "",
        "## Corpus S-region",
        "",
    ]
    if payload["corpus"]:
        lines += [
            "A corpus path is visible, but this script does not run Stage 1",
            "peak-picking. Task 4 remains gated on a signed-off roughness",
            "basis before any 49-note recompute.",
            "",
        ]
    else:
        lines += [
            "Not reachable (`ACD_REAL_NOTE_AUDIO` unset; default cello path",
            "absent). No live S-region difference is reported.",
            "",
        ]
    lines += [
        "## Outstanding judgement",
        "",
        "Keep `hk1978` until the author decides whether sub-bass H&K should",
        "use Zwicker CB below 200 Hz. Changing the default would move",
        "S-region dissonance on every note with energy below that cutoff.",
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
