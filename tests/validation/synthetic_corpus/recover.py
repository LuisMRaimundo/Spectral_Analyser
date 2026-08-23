"""Recover N, B, EPD, and confirmed-I from a planted construct spectrum."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from harmonic_peak_validation import compute_spacing_capped_tolerance_hz
from inharmonic_confirmation import (
    STATUS_CONFIRMED,
    STATUS_STRETCHED,
    confirm_inharmonic_candidates,
    f007_frequency_hz,
    reassign_stretched_to_harmonics,
)
from inharmonicity_model import fit_inharmonicity_coefficient
from tests.validation.synthetic_corpus.generate import ConstructSpec, plant_spectrum
from validated_partials import participation_ratio_from_amplitudes


def _detect_peaks(freqs: np.ndarray, mags: np.ndarray) -> List[dict[str, Any]]:
    rows: List[dict[str, Any]] = []
    df = float(freqs[1] - freqs[0]) if freqs.size >= 2 else 0.0
    for i in range(2, int(mags.size) - 2):
        if mags[i] > mags[i - 1] and mags[i] >= mags[i + 1]:
            denom = float(mags[i - 1] - 2.0 * mags[i] + mags[i + 1])
            if abs(denom) > 1e-18:
                delta = 0.5 * float(mags[i - 1] - mags[i + 1]) / denom
                delta = float(np.clip(delta, -0.5, 0.5))
            else:
                delta = 0.0
            rows.append(
                {
                    "Frequency (Hz)": float(freqs[i]) + delta * df,
                    "Amplitude": float(mags[i]),
                    "Amplitude_raw": float(mags[i]),
                    "peak_bin_index": int(i),
                }
            )
    return rows


def _assign_harmonics(
    peaks: List[dict[str, Any]],
    *,
    f0_hz: float,
    b_hz: float,
    n_max: int,
    bin_spacing_hz: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    used: set[int] = set()
    harmonics: List[dict[str, Any]] = []
    for n in range(1, int(n_max) + 1):
        pred = f007_frequency_hz(n, f0_hz, b_hz)
        tol, _limb = compute_spacing_capped_tolerance_hz(
            n, f0_hz, bin_spacing_hz=float(bin_spacing_hz)
        )
        best_i = None
        best_err = float("inf")
        for i, row in enumerate(peaks):
            if i in used:
                continue
            err = abs(float(row["Frequency (Hz)"]) - pred)
            if err <= float(tol) and err < best_err:
                best_err = err
                best_i = i
        if best_i is None:
            continue
        used.add(best_i)
        rec = dict(peaks[best_i])
        rec["Harmonic Number"] = n
        rec["include_for_density"] = True
        harmonics.append(rec)
    residual = [dict(row) for i, row in enumerate(peaks) if i not in used]
    return harmonics, residual


def recover_construct(spec: ConstructSpec) -> Dict[str, Any]:
    """Run the Stage 1 evidence path on a planted spectrum."""
    freqs, mags = plant_spectrum(spec)
    peaks = _detect_peaks(freqs, mags)
    bin_hz = float(freqs[1] - freqs[0]) if freqs.size >= 2 else 0.0
    harmonics, residual = _assign_harmonics(
        peaks,
        f0_hz=spec.f0_hz,
        b_hz=0.0,
        n_max=spec.n_harmonic,
        bin_spacing_hz=bin_hz,
    )
    peak_freqs = np.asarray([r["Frequency (Hz)"] for r in peaks], dtype=float)
    fit = fit_inharmonicity_coefficient(
        peak_freqs if peak_freqs.size else np.asarray([], dtype=float),
        spec.f0_hz,
        order_cap=max(8, spec.n_harmonic),
        cents_window=80.0,
    )
    try:
        b_hat = float(fit.get("inharmonicity_coefficient_B", 0.0))
    except (TypeError, ValueError):
        b_hat = 0.0
    if not np.isfinite(b_hat):
        b_hat = 0.0
    model_on = spec.family in {"stiff", "bell"} or abs(spec.b_true) > 0.0
    if spec.family == "harmonic":
        model_on = False
        b_for_grid = 0.0
    elif spec.family == "stiff":
        b_for_grid = b_hat
        harmonics, residual = _assign_harmonics(
            peaks,
            f0_hz=spec.f0_hz,
            b_hz=b_for_grid,
            n_max=spec.n_harmonic,
            bin_spacing_hz=bin_hz,
        )
    else:
        b_for_grid = 0.0
    confirmed = confirm_inharmonic_candidates(
        residual,
        magnitudes=mags,
        freqs=freqs,
        accepted_harmonics=harmonics,
        f0_hz=spec.f0_hz,
        B=b_for_grid,
        inharmonicity_model_applied=model_on,
        sr=spec.sr,
        n_fft=int(spec.n_fft),
    )
    stretched = [r for r in confirmed if r.get("inharmonic_status") == STATUS_STRETCHED]
    if stretched:
        harmonics.extend(reassign_stretched_to_harmonics(stretched))
        confirmed = [
            r for r in confirmed if r.get("inharmonic_status") != STATUS_STRETCHED
        ]
    confirmed_i = [r for r in confirmed if r.get("inharmonic_status") == STATUS_CONFIRMED]
    h_amps = [
        float(r.get("Amplitude_raw", r.get("Amplitude", 0.0)) or 0.0)
        for r in harmonics
        if r.get("include_for_density")
    ]
    i_amps = [
        float(r.get("Amplitude_raw", r.get("Amplitude", 0.0)) or 0.0)
        for r in confirmed_i
    ]
    epd_hat = participation_ratio_from_amplitudes(h_amps + i_amps)
    return {
        "name": spec.name,
        "family": spec.family,
        "snr_db": spec.snr_db,
        "n_true": spec.n_harmonic,
        "n_hat": len(harmonics),
        "b_true": spec.b_true,
        "b_hat": b_hat,
        "epd_true": spec.true_epd,
        "epd_hat": epd_hat,
        "confirmed_i_true": spec.confirmed_i_true,
        "confirmed_i_hat": len(confirmed_i),
        "fit_status": str(fit.get("fit_status") or ""),
        "h_amps": h_amps,
        "i_amps": i_amps,
        "h_freqs": [
            float(r.get("Frequency (Hz)", 0.0) or 0.0)
            for r in harmonics
            if r.get("include_for_density")
        ],
    }


def recover_table(specs: List[ConstructSpec] | None = None) -> pd.DataFrame:
    from tests.validation.synthetic_corpus.generate import iter_constructs

    rows = [recover_construct(spec) for spec in (specs or list(iter_constructs()))]
    return pd.DataFrame(rows)


def build_markdown_table(df: pd.DataFrame) -> str:
    lines = [
        "# Construct validation — synthetic corpus",
        "",
        "Planted constructs recovered through the Stage 1 evidence path",
        "(peak pick → F-007 assignment → stiff-string B fit → confirmed-I → EPD).",
        "SNR is the per-partial peak-to-floor ratio (dB), white floor.",
        "",
        "Acceptance: N ±1, B ±20 % (CONSTRUCT_B_REL_TOL after n=1 leverage cap; Phase I freeze was ±10 %), EPD ±10 %, confirmed-I exact.",
        "",
        "| construct | SNR dB | N true | N hat | B true | B hat | EPD true | EPD hat | I true | I hat |",
        "|-----------|-------:|-------:|------:|-------:|------:|---------:|--------:|-------:|------:|",
    ]
    for _, row in df.iterrows():
        lines.append(
            "| {name} | {snr:.0f} | {n_true} | {n_hat} | {b_true:.2e} | {b_hat:.2e} | "
            "{epd_true:.3f} | {epd_hat:.3f} | {i_true} | {i_hat} |".format(
                name=row["name"],
                snr=float(row["snr_db"]),
                n_true=int(row["n_true"]),
                n_hat=int(row["n_hat"]),
                b_true=float(row["b_true"]),
                b_hat=float(row["b_hat"]),
                epd_true=float(row["epd_true"]),
                epd_hat=float(row["epd_hat"]),
                i_true=int(row["confirmed_i_true"]),
                i_hat=int(row["confirmed_i_hat"]),
            )
        )
    lines.append("")
    return "\n".join(lines)
