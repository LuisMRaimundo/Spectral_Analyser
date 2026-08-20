"""R5 — external-truth EWSD/EPD oracle and frame-count C2.

Oracle scores come from ``ewsd_pure`` / F-047 on planted amplitudes.
They do not go through ``bootstrap_ewsd_from_compartments``.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from density_uncertainty import bootstrap_effective_component_density
from tools.ewsd_pure import (
    ACOUSTIC_BALANCE_ALPHA_DEFAULT,
    CompartmentInputs,
    compute_note_ewsd,
)
from tools.ewsd_uncertainty import (
    bootstrap_ewsd_from_compartments,
    compartment_bootstrap_data_from_arrays,
)
from validated_partials import participation_ratio_from_amplitudes

MASTER_SEED = 20260820
N_PARTIALS = 8
ROLLOFF_DB_OCT = -6.0
F0_HZ = 220.0
SNR_DB = 20.0
N_C1 = 200
N_BOOT = 200
FRAME_COUNTS: Tuple[int, ...] = (4, 8, 16, 32)
C1_TRIAL_OFFSET = 900
C2_TRIAL_OFFSET = 1400
OVERSAMPLE = 10


def planted_amplitudes(
    n_partials: int = N_PARTIALS,
    rolloff_db_oct: float = ROLLOFF_DB_OCT,
) -> np.ndarray:
    out = []
    for k in range(1, int(n_partials) + 1):
        octaves = math.log2(float(k))
        out.append(float(10.0 ** ((float(rolloff_db_oct) * octaves) / 20.0)))
    return np.asarray(out, dtype=float)


def planted_frequencies(
    n_partials: int = N_PARTIALS,
    f0_hz: float = F0_HZ,
) -> np.ndarray:
    return np.asarray([float(f0_hz) * k for k in range(1, int(n_partials) + 1)], dtype=float)


def oracle_from_planted(
    amplitudes: Sequence[float],
    frequencies_hz: Optional[Sequence[float]] = None,
    *,
    weight_function: str = "log",
    acoustic_balance_alpha: float = ACOUSTIC_BALANCE_ALPHA_DEFAULT,
) -> Dict[str, float]:
    """Reference EWSD/EPD from planted amps. No bootstrap."""
    amps = np.asarray(amplitudes, dtype=float).ravel()
    amps = amps[np.isfinite(amps) & (amps > 0.0)]
    freqs: Optional[np.ndarray] = None
    if frequencies_hz is not None:
        f = np.asarray(frequencies_hz, dtype=float).ravel()
        if f.size == amps.size:
            freqs = f
    note = compute_note_ewsd(
        [
            CompartmentInputs(
                values=amps,
                analysis_ratio=1.0,
                frequencies_hz=freqs,
                weight_function=weight_function,
                apply_anti_concentration=True,
            )
        ],
        acoustic_balance_alpha=acoustic_balance_alpha,
    )
    return {
        "ewsd_score_acoustic_balanced": float(note["ewsd_score_acoustic_balanced"]),
        "ewsd_score_total": float(note["ewsd_score_total"]),
        "note_effective_component_density": float(
            participation_ratio_from_amplitudes(list(amps))
        ),
    }


def noisy_amplitudes(
    planted: Sequence[float],
    snr_db: float,
    rng: np.random.Generator,
) -> np.ndarray:
    amps = np.asarray(planted, dtype=float).ravel()
    rms = float(np.sqrt(np.mean(np.square(amps)))) if amps.size else 0.0
    sigma = rms / (10.0 ** (float(snr_db) / 20.0)) if rms > 0.0 else 0.0
    obs = amps + sigma * rng.standard_normal(amps.size)
    return np.maximum(obs, 1e-12)


def production_interval(
    amplitudes: Sequence[float],
    frequencies_hz: Sequence[float],
    *,
    seed: int,
    n_boot: int = N_BOOT,
) -> Dict[str, float]:
    """Exported-style partial-resample CIs (unchanged bootstrap)."""
    amps = np.asarray(amplitudes, dtype=float).ravel()
    freqs = np.asarray(frequencies_hz, dtype=float).ravel()
    h = compartment_bootstrap_data_from_arrays(amps, 1.0, frequencies_hz=freqs)
    ewsd = bootstrap_ewsd_from_compartments([h], n_boot=int(n_boot), seed=int(seed))
    epd = bootstrap_effective_component_density(amps, n_boot=int(n_boot), seed=int(seed))
    return {
        "ewsd_score_acoustic_balanced": float(ewsd["ewsd_score_acoustic_balanced"]),
        "ewsd_ci_low": float(ewsd["ewsd_score_acoustic_balanced_ci_low"]),
        "ewsd_ci_high": float(ewsd["ewsd_score_acoustic_balanced_ci_high"]),
        "epd": float(epd["point_estimate"]),
        "epd_ci_low": float(epd["ci_low"]),
        "epd_ci_high": float(epd["ci_high"]),
    }


def _covers(lo: float, hi: float, truth: float) -> bool:
    return bool(np.isfinite(lo) and np.isfinite(hi) and np.isfinite(truth) and lo <= truth <= hi)


def _c1_score(cov: float) -> int:
    if 93.0 <= cov <= 97.0:
        return 100
    if 90.0 <= cov <= 99.0:
        return 70
    return 30


def oversampled_oracle(
    planted: Sequence[float],
    frequencies_hz: Sequence[float],
    *,
    snr_db: float = SNR_DB,
    n_frames: int = OVERSAMPLE * FRAME_COUNTS[-1],
    seed: int = MASTER_SEED + 50,
) -> Dict[str, float]:
    """10×-long known-noise mean of the planted process. Still not a bootstrap."""
    rng = np.random.default_rng(int(seed))
    frames = [noisy_amplitudes(planted, snr_db, rng) for _ in range(int(n_frames))]
    mean_amps = np.mean(np.vstack(frames), axis=0)
    return oracle_from_planted(mean_amps, frequencies_hz)


def run_c1(
    *,
    n: int = N_C1,
    n_boot: int = N_BOOT,
    snr_db: float = SNR_DB,
    seed: int = MASTER_SEED,
) -> Dict[str, Any]:
    planted = planted_amplitudes()
    freqs = planted_frequencies()
    oracle = oracle_from_planted(planted, freqs)
    over = oversampled_oracle(planted, freqs, snr_db=snr_db, seed=seed + 50)
    cover_e = 0
    cover_p = 0
    for i in range(int(n)):
        rng = np.random.default_rng(int(seed) + C1_TRIAL_OFFSET + i)
        obs = noisy_amplitudes(planted, snr_db, rng)
        interval = production_interval(obs, freqs, seed=int(seed) + i, n_boot=n_boot)
        if _covers(
            interval["ewsd_ci_low"],
            interval["ewsd_ci_high"],
            oracle["ewsd_score_acoustic_balanced"],
        ):
            cover_e += 1
        if _covers(interval["epd_ci_low"], interval["epd_ci_high"], oracle["note_effective_component_density"]):
            cover_p += 1
    cov_e = 100.0 * cover_e / float(n)
    cov_p = 100.0 * cover_p / float(n)
    return {
        "ewsd_coverage_pct": cov_e,
        "epd_coverage_pct": cov_p,
        "n": int(n),
        "n_boot": int(n_boot),
        "snr_db": float(snr_db),
        "n_partials": int(planted.size),
        "score": _c1_score(cov_e),
        "oracle_ewsd": oracle["ewsd_score_acoustic_balanced"],
        "oracle_epd": oracle["note_effective_component_density"],
        "oversampled_oracle_ewsd": over["ewsd_score_acoustic_balanced"],
        "oversampled_oracle_epd": over["note_effective_component_density"],
        "oracle_source": "planted_amplitudes_ewsd_pure",
        "note": (
            "Coverage is of the planted-amplitude oracle (ewsd_pure / F-047), "
            "not of the estimator point inside its own interval."
        ),
    }


def _frame_bootstrap_interval(
    frames: Sequence[np.ndarray],
    frequencies_hz: Sequence[float],
    *,
    seed: int,
    n_boot: int,
) -> Dict[str, float]:
    stacked = [np.asarray(f, dtype=float).ravel() for f in frames]
    n = len(stacked)
    mean_amps = np.mean(np.vstack(stacked), axis=0)
    point = oracle_from_planted(mean_amps, frequencies_hz)
    rng = np.random.default_rng(int(seed))
    boot_e = np.empty(int(n_boot), dtype=float)
    boot_p = np.empty(int(n_boot), dtype=float)
    for b in range(int(n_boot)):
        idx = rng.integers(0, n, n)
        draw = np.mean(np.vstack([stacked[i] for i in idx]), axis=0)
        met = oracle_from_planted(draw, frequencies_hz)
        boot_e[b] = met["ewsd_score_acoustic_balanced"]
        boot_p[b] = met["note_effective_component_density"]
    lo_q, hi_q = 2.5, 97.5
    return {
        "ewsd": float(point["ewsd_score_acoustic_balanced"]),
        "ewsd_ci_low": float(np.percentile(boot_e, lo_q)),
        "ewsd_ci_high": float(np.percentile(boot_e, hi_q)),
        "epd": float(point["note_effective_component_density"]),
        "epd_ci_low": float(np.percentile(boot_p, lo_q)),
        "epd_ci_high": float(np.percentile(boot_p, hi_q)),
        "width": float(np.percentile(boot_e, hi_q) - np.percentile(boot_e, lo_q)),
        "n_frames": int(n),
        "n_partials": int(mean_amps.size),
    }


def _loglog_slope(ns: Sequence[float], widths: Sequence[float]) -> float:
    x = np.log(np.asarray(ns, dtype=float))
    y = np.log(np.asarray(widths, dtype=float))
    ok = np.isfinite(x) & np.isfinite(y)
    if int(ok.sum()) < 2:
        return float("nan")
    coef = np.polyfit(x[ok], y[ok], 1)
    return float(coef[0])


def run_c2(
    *,
    frame_counts: Sequence[int] = FRAME_COUNTS,
    n_trials: int = 40,
    n_boot: int = N_BOOT,
    snr_db: float = SNR_DB,
    seed: int = MASTER_SEED,
) -> Dict[str, Any]:
    planted = planted_amplitudes()
    freqs = planted_frequencies()
    oracle = oracle_from_planted(planted, freqs)
    rows: List[Dict[str, Any]] = []
    for nf in frame_counts:
        widths: List[float] = []
        cover_e = 0
        cover_p = 0
        for t in range(int(n_trials)):
            rng = np.random.default_rng(int(seed) + C2_TRIAL_OFFSET + 17 * int(nf) + t)
            frames = [noisy_amplitudes(planted, snr_db, rng) for _ in range(int(nf))]
            interval = _frame_bootstrap_interval(
                frames,
                freqs,
                seed=int(seed) + 3000 + int(nf) + t,
                n_boot=n_boot,
            )
            widths.append(float(interval["width"]))
            if _covers(
                interval["ewsd_ci_low"],
                interval["ewsd_ci_high"],
                oracle["ewsd_score_acoustic_balanced"],
            ):
                cover_e += 1
            if _covers(
                interval["epd_ci_low"],
                interval["epd_ci_high"],
                oracle["note_effective_component_density"],
            ):
                cover_p += 1
        med_w = float(np.median(widths)) if widths else float("nan")
        rows.append(
            {
                "n_frames": int(nf),
                "n_partials": int(planted.size),
                "width": med_w,
                "ewsd_coverage_pct": 100.0 * cover_e / float(n_trials),
                "epd_coverage_pct": 100.0 * cover_p / float(n_trials),
                "n_trials": int(n_trials),
            }
        )
    slope = _loglog_slope([r["n_frames"] for r in rows], [r["width"] for r in rows])
    # 1/√n has slope −0.5 on log width vs log n. Do not tune the bootstrap
    # if the measured slope misses that band.
    slope_ok = bool(np.isfinite(slope) and -0.65 <= slope <= -0.35)
    shrinking = True
    prev = None
    for r in rows:
        w = float(r["width"])
        if prev is not None and np.isfinite(w) and np.isfinite(prev) and w > prev * 1.05:
            shrinking = False
        prev = w
    coverage_ok = all(90.0 <= float(r["ewsd_coverage_pct"]) <= 99.0 for r in rows)
    c2_pass = bool(slope_ok and shrinking and coverage_ok)
    return {
        "rows": rows,
        "pass": c2_pass,
        "score": 100 if c2_pass else 30,
        "loglog_slope": slope,
        "n_partials": int(planted.size),
        "snr_db": float(snr_db),
        "oracle_ewsd": oracle["ewsd_score_acoustic_balanced"],
        "oracle_epd": oracle["note_effective_component_density"],
        "note": (
            "n is independent noisy frames at fixed 8 partials and SNR; "
            "CI resamples frames. Width fit is log(width) vs log(n)."
        ),
    }


def run_r5(
    *,
    n_c1: int = N_C1,
    n_c2_trials: int = 40,
    n_boot: int = N_BOOT,
    seed: int = MASTER_SEED,
) -> Dict[str, Any]:
    c1 = run_c1(n=n_c1, n_boot=n_boot, seed=seed)
    c2 = run_c2(n_trials=n_c2_trials, n_boot=n_boot, seed=seed)
    return {"C1": c1, "C2": c2}


def main() -> None:
    bundle = run_r5()
    c1 = bundle["C1"]
    c2 = bundle["C2"]
    print(
        f"C1 EWSD={c1['ewsd_coverage_pct']:.1f}% EPD={c1['epd_coverage_pct']:.1f}% "
        f"score={c1['score']} oracle_ewsd={c1['oracle_ewsd']:.4f}"
    )
    print(
        "C2 "
        + ", ".join(
            f"n={r['n_frames']} w={r['width']:.4f} covE={r['ewsd_coverage_pct']:.1f}"
            for r in c2["rows"]
        )
        + f"; slope={c2['loglog_slope']:.3f} pass={c2['pass']}"
    )


if __name__ == "__main__":
    main()
