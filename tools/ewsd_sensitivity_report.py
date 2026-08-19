#!/usr/bin/env python3
"""
EWSD acoustic sensitivity report (Tier B).

Computes alpha-exponent rank stability and basic construct checks on an EWSD
dataframe (typically from ``compute_ewsd_dataframe_from_analysis_root`` or a
reference export).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

FAMILIES = ("harmonic", "nonharmonic_residual", "noise_subbass")
# Amplitude-family φ keys accepted by ``ewsd_pure.original_sum_metric``.
# Discrete D3/D10/D17/D24 metrics are excluded: they are not φ transforms.
PHI_SENSITIVITY_KEYS: Tuple[str, ...] = (
    "linear",
    "log",
    "sqrt",
    "cbrt",
    "squared",
    "cubic",
    "exponential",
    "inverse log",
)
# Compressive / near-default family used for the README invariance claim.
PHI_COMPRESSIVE_KEYS: Tuple[str, ...] = ("linear", "log", "sqrt", "cbrt")


def _score_series(frame: pd.DataFrame, *names: str) -> pd.Series:
    for name in names:
        if name in frame.columns:
            return pd.to_numeric(frame[name], errors="coerce")
    return pd.Series(np.nan, index=frame.index)


def balanced_score_from_row(row: pd.Series, alpha: float) -> float:
    total = 0.0
    for fam in FAMILIES:
        mass = pd.to_numeric(row.get(f"ratio_weighted_metric_{fam}"), errors="coerce")
        pen = pd.to_numeric(row.get(f"concentration_penalty_{fam}"), errors="coerce")
        if not np.isfinite(mass) or not np.isfinite(pen):
            continue
        pen = float(min(max(float(pen), 0.0), 1.0))
        total += float(mass) * (pen ** float(alpha))
    return float(total)


def alpha_rank_stability(
    frame: pd.DataFrame,
    *,
    alphas: Sequence[float] = (0.25, 0.5, 0.75, 1.0),
    note_col: str = "Note",
) -> pd.DataFrame:
    """Return Spearman rank correlations between alpha settings across notes."""
    from scipy.stats import spearmanr

    if frame.empty or note_col not in frame.columns:
        return pd.DataFrame(columns=["alpha_a", "alpha_b", "spearman_rho", "n_notes"])

    scores: dict[float, pd.Series] = {}
    for alpha in alphas:
        scores[float(alpha)] = frame.apply(balanced_score_from_row, axis=1, alpha=float(alpha))

    rows: list[dict[str, Any]] = []
    alpha_list = sorted(scores.keys())
    for i, a1 in enumerate(alpha_list):
        for a2 in alpha_list[i + 1 :]:
            s1 = scores[a1]
            s2 = scores[a2]
            mask = np.isfinite(s1.to_numpy(dtype=float)) & np.isfinite(s2.to_numpy(dtype=float))
            n = int(mask.sum())
            if n < 3:
                rho = float("nan")
            else:
                rho = float(spearmanr(s1[mask], s2[mask]).statistic)
            rows.append(
                {
                    "alpha_a": a1,
                    "alpha_b": a2,
                    "spearman_rho": rho,
                    "n_notes": n,
                }
            )
    return pd.DataFrame(rows)


def construct_checks(frame: pd.DataFrame) -> dict[str, Any]:
    """Acoustic construct checks on an EWSD table (no perceptual claims)."""
    from scipy.stats import spearmanr

    out: dict[str, Any] = {"n_rows": int(len(frame))}
    strict = _score_series(frame, "ewsd_score", "EWSD_score_total")
    balanced = _score_series(frame, "ewsd_score_acoustic_balanced", "EWSD_score_acoustic_balanced")
    strict_arr = strict.to_numpy(dtype=float)
    balanced_arr = balanced.to_numpy(dtype=float)
    mask = np.isfinite(strict_arr) & np.isfinite(balanced_arr)
    n = int(mask.sum())
    out["n_finite_scores"] = n
    if n >= 3:
        rho_sb = float(spearmanr(strict[mask], balanced[mask]).statistic)
        out["spearman_strict_vs_balanced"] = rho_sb
        out["strict_balanced_not_identical"] = bool(
            np.nanmax(np.abs((strict[mask] - balanced[mask]).to_numpy(dtype=float))) > 1e-9
        )
    else:
        out["spearman_strict_vs_balanced"] = float("nan")
        out["strict_balanced_not_identical"] = False

    if "Note_midi_sort" in frame.columns and n >= 5:
        midi = pd.to_numeric(frame.loc[mask, "Note_midi_sort"], errors="coerce")
        out["spearman_register_vs_balanced"] = float(
            spearmanr(midi, balanced[mask]).statistic
        )
    else:
        out["spearman_register_vs_balanced"] = float("nan")

    pen_cols = [f"concentration_penalty_{fam}" for fam in FAMILIES]
    present = [c for c in pen_cols if c in frame.columns]
    if present and n >= 3:
        mean_pen = frame.loc[mask, present].apply(pd.to_numeric, errors="coerce").mean(axis=1)
        out["spearman_mean_penalty_vs_strict"] = float(
            spearmanr(mean_pen, strict[mask]).statistic
        )
    else:
        out["spearman_mean_penalty_vs_strict"] = float("nan")

    return out


def _spearman_pairs(score_cols: Mapping[str, pd.Series]) -> pd.DataFrame:
    from scipy.stats import spearmanr

    keys = list(score_cols.keys())
    rows: list[dict[str, Any]] = []
    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            s1 = pd.to_numeric(score_cols[a], errors="coerce")
            s2 = pd.to_numeric(score_cols[b], errors="coerce")
            mask = np.isfinite(s1.to_numpy(dtype=float)) & np.isfinite(s2.to_numpy(dtype=float))
            n = int(mask.sum())
            if n < 3:
                rho = float("nan")
            else:
                rho = float(spearmanr(s1[mask], s2[mask]).statistic)
            rows.append(
                {
                    "phi_a": a,
                    "phi_b": b,
                    "spearman_rho": rho,
                    "n_notes": n,
                }
            )
    return pd.DataFrame(rows)


def phi_rank_stability(score_frame: pd.DataFrame, *, note_col: str = "Note") -> pd.DataFrame:
    """Spearman ρ between EWSD ranks under different φ columns."""
    if score_frame is None or score_frame.empty:
        return pd.DataFrame(columns=["phi_a", "phi_b", "spearman_rho", "n_notes"])
    cols = {
        str(c): score_frame[c]
        for c in score_frame.columns
        if str(c) != note_col
    }
    return _spearman_pairs(cols)


def ewsd_balanced_by_phi_from_compartments(
    notes: Sequence[Mapping[str, Any]],
    *,
    phis: Sequence[str] = PHI_SENSITIVITY_KEYS,
) -> pd.DataFrame:
    """Recompute acoustic-balanced EWSD for each note under every φ.

    Each note mapping needs ``Note`` and ``compartments``: a sequence of
    ``{family, amplitudes, analysis_ratio}`` with family in ``H`` / ``I`` / ``S``.
    """
    try:
        from tools.ewsd_pure import CompartmentInputs, compute_note_ewsd
    except ImportError:  # pragma: no cover - script execution
        from ewsd_pure import CompartmentInputs, compute_note_ewsd

    family_map = {"H": 0, "I": 1, "S": 2, "S_noise": 2}
    rows: list[dict[str, Any]] = []
    for note in notes:
        tag = str(note.get("Note") or "")
        raw_comps = list(note.get("compartments") or [])
        by_fam: dict[int, Mapping[str, Any]] = {}
        for part in raw_comps:
            idx = family_map.get(str(part.get("family") or ""))
            if idx is not None:
                by_fam[idx] = part
        row: dict[str, Any] = {"Note": tag}
        for phi in phis:
            inputs = []
            for idx in (0, 1, 2):
                part = by_fam.get(idx, {})
                amps = np.asarray(part.get("amplitudes") or [], dtype=float)
                ratio = float(part.get("analysis_ratio") or 0.0)
                inputs.append(
                    CompartmentInputs(
                        values=amps,
                        analysis_ratio=ratio,
                        weight_function=str(phi),
                    )
                )
            out = compute_note_ewsd(inputs)
            row[str(phi)] = float(out["ewsd_score_acoustic_balanced"])
        rows.append(row)
    return pd.DataFrame(rows)


def ewsd_balanced_by_phi_from_analysis_root(
    analysis_root: Path,
    *,
    phis: Sequence[str] = PHI_SENSITIVITY_KEYS,
    frequency_ceiling_hz: float = 20000.0,
) -> pd.DataFrame:
    """Recompute EWSD-R acoustic-balanced scores under each φ from Stage 1 workbooks."""
    try:
        from tools.ewsd_research_integration import compute_ewsd_dataframe_from_analysis_root
    except ImportError:  # pragma: no cover - script execution
        from ewsd_research_integration import compute_ewsd_dataframe_from_analysis_root

    merged: Optional[pd.DataFrame] = None
    for phi in phis:
        frame = compute_ewsd_dataframe_from_analysis_root(
            analysis_root,
            use_excel_weight_function=False,
            weight_function=str(phi),
            frequency_ceiling_hz=frequency_ceiling_hz,
            include_uncertainty=False,
        )
        if frame is None or frame.empty or "Note" not in frame.columns:
            continue
        score = _score_series(frame, "ewsd_score_acoustic_balanced", "EWSD_score_acoustic_balanced")
        piece = pd.DataFrame({"Note": frame["Note"].astype(str), str(phi): score})
        if merged is None:
            merged = piece
        else:
            merged = merged.merge(piece, on="Note", how="outer")
    return merged if merged is not None else pd.DataFrame(columns=["Note"])


def min_phi_spearman_rho(stability: pd.DataFrame) -> float:
    if stability is None or stability.empty or "spearman_rho" not in stability.columns:
        return float("nan")
    vals = pd.to_numeric(stability["spearman_rho"], errors="coerce")
    finite = vals[np.isfinite(vals.to_numpy(dtype=float))]
    if finite.empty:
        return float("nan")
    return float(finite.min())


def build_phi_report_markdown(
    score_frame: pd.DataFrame,
    *,
    source: str,
    default_phi: str = "log",
) -> str:
    stability = phi_rank_stability(score_frame)
    min_rho = min_phi_spearman_rho(stability)
    compressive_cols = [c for c in PHI_COMPRESSIVE_KEYS if c in score_frame.columns]
    keep = ["Note"] + compressive_cols if "Note" in score_frame.columns else compressive_cols
    compressive = score_frame.loc[:, [c for c in keep if c in score_frame.columns]]
    compressive_stability = phi_rank_stability(compressive)
    min_rho_comp = min_phi_spearman_rho(compressive_stability)
    n_notes = int(len(score_frame))
    invariant = bool(np.isfinite(min_rho) and min_rho >= 0.90)
    lines = [
        "# EWSD weight-function φ sensitivity",
        "",
        f"Source: `{source}`",
        f"Notes: {n_notes}",
        f"Default φ: `{default_phi}` (log-amplitude loudness proxy).",
        "",
        "Spearman ρ of `EWSD_score_acoustic_balanced` ranks across amplitude-family φ.",
        "Discrete D3/D10/D17/D24 keys are excluded (they are not φ transforms).",
        "",
        "## Pairwise rank agreement",
        "",
    ]
    if stability.empty:
        lines.append("_No stability table (empty input)._")
    else:
        lines.append("| φ_a | φ_b | Spearman ρ | n notes |")
        lines.append("|-----|-----|------------|---------|")
        for _, row in stability.iterrows():
            lines.append(
                f"| {row['phi_a']} | {row['phi_b']} | {row['spearman_rho']:.4f} | {int(row['n_notes'])} |"
            )
    lines.extend(
        [
            "",
            f"Minimum pairwise Spearman ρ (all amplitude-family φ): **{min_rho:.4f}**",
            f"Minimum pairwise Spearman ρ (compressive family linear/log/sqrt/cbrt): **{min_rho_comp:.4f}**",
            "",
            (
                f"EWSD ordering is φ-invariant to ρ ≥ {min_rho:.3f} on this corpus."
                if invariant
                else (
                    f"EWSD ordering is **not** φ-invariant across all amplitude-family φ "
                    f"(minimum pairwise ρ = {min_rho:.3f}). "
                    f"Among compressive φ (linear, log, sqrt, cbrt) ρ ≥ {min_rho_comp:.3f}."
                )
            ),
            "",
        ]
    )
    return "\n".join(lines)


def build_report_markdown(
    frame: pd.DataFrame,
    *,
    source: str,
    alphas: Sequence[float] = (0.25, 0.5, 0.75, 1.0),
) -> str:
    stability = alpha_rank_stability(frame, alphas=alphas)
    checks = construct_checks(frame)
    lines = [
        "# EWSD acoustic construct & sensitivity report",
        "",
        f"Source: `{source}`",
        f"Rows: {checks.get('n_rows', 0)} (finite scores: {checks.get('n_finite_scores', 0)})",
        "",
        "## Alpha rank stability (acoustic-balanced recomputation)",
        "",
        "Spearman ρ between note ranks at different penalty exponents α.",
        "",
    ]
    if stability.empty:
        lines.append("_No stability table (empty input)._")
    else:
        lines.append("| α_a | α_b | Spearman ρ | n notes |")
        lines.append("|-----|-----|------------|---------|")
        for _, row in stability.iterrows():
            lines.append(
                f"| {row['alpha_a']} | {row['alpha_b']} | {row['spearman_rho']:.4f} | {int(row['n_notes'])} |"
            )

    lines.extend(
        [
            "",
            "## Construct checks (acoustic, non-perceptual)",
            "",
            f"- Strict vs balanced Spearman ρ: **{checks.get('spearman_strict_vs_balanced', float('nan')):.4f}**",
            f"- Strict ≠ balanced (numerically): **{checks.get('strict_balanced_not_identical')}**",
            f"- Register (MIDI) vs balanced Spearman ρ: **{checks.get('spearman_register_vs_balanced', float('nan')):.4f}**",
            f"- Mean compartment penalty vs strict Spearman ρ: **{checks.get('spearman_mean_penalty_vs_strict', float('nan')):.4f}**",
            "",
            "Interpretation: high α-a vs α-b rank stability supports using α=0.5 for",
            "cross-instrument comparison; register correlation documents physical capacity",
            "effects rather than perceptual validation.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_phi_report(
    *,
    analysis_root: Optional[Path] = None,
    notes: Optional[Sequence[Mapping[str, Any]]] = None,
    phis: Sequence[str] = PHI_SENSITIVITY_KEYS,
    frequency_ceiling_hz: float = 20000.0,
    output_md: Optional[Path] = None,
    output_json: Optional[Path] = None,
    source: str = "",
    default_phi: str = "log",
) -> dict[str, Any]:
    if analysis_root is not None:
        scores = ewsd_balanced_by_phi_from_analysis_root(
            Path(analysis_root),
            phis=phis,
            frequency_ceiling_hz=frequency_ceiling_hz,
        )
        src = source or str(analysis_root)
    elif notes is not None:
        scores = ewsd_balanced_by_phi_from_compartments(notes, phis=phis)
        src = source or "in-memory compartments"
    else:
        raise ValueError("Provide analysis_root or notes")

    stability = phi_rank_stability(scores)
    min_rho = min_phi_spearman_rho(stability)
    md = build_phi_report_markdown(scores, source=src, default_phi=default_phi)
    payload = {
        "source": src,
        "default_phi": default_phi,
        "n_notes": int(len(scores)),
        "min_spearman_rho": min_rho,
        "min_spearman_rho_compressive": min_phi_spearman_rho(
            phi_rank_stability(
                scores.loc[
                    :,
                    [
                        c
                        for c in (["Note"] + list(PHI_COMPRESSIVE_KEYS))
                        if c in scores.columns
                    ],
                ]
            )
        ),
        "phi_rank_stability": stability.to_dict(orient="records"),
        "scores": scores.to_dict(orient="records"),
    }
    if output_md is not None:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(md, encoding="utf-8")
    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def run_report(
    *,
    analysis_root: Optional[Path] = None,
    reference_xlsx: Optional[Path] = None,
    frequency_ceiling_hz: float = 20000.0,
    output_md: Optional[Path] = None,
    output_json: Optional[Path] = None,
    alphas: Sequence[float] = (0.25, 0.5, 0.75, 1.0),
) -> dict[str, Any]:
    if analysis_root is not None:
        from tools.ewsd_research_integration import compute_ewsd_dataframe_from_analysis_root

        frame = compute_ewsd_dataframe_from_analysis_root(
            analysis_root,
            frequency_ceiling_hz=frequency_ceiling_hz,
            include_uncertainty=False,
        )
        source = str(analysis_root)
    elif reference_xlsx is not None:
        frame = pd.read_excel(reference_xlsx, sheet_name="EWSD_All_Columns")
        source = str(reference_xlsx)
    else:
        raise ValueError("Provide analysis_root or reference_xlsx")

    if "primary_analysis_eligible" in frame.columns:
        frame = frame[frame["primary_analysis_eligible"].astype(bool)].copy()

    md = build_report_markdown(frame, source=source, alphas=alphas)
    payload = {
        "source": source,
        "construct_checks": construct_checks(frame),
        "alpha_rank_stability": alpha_rank_stability(frame, alphas=alphas).to_dict(orient="records"),
    }

    if output_md is not None:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(md, encoding="utf-8")
    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="EWSD acoustic sensitivity report")
    parser.add_argument("--analysis-root", type=Path, default=None)
    parser.add_argument("--reference-xlsx", type=Path, default=None)
    parser.add_argument("--frequency-ceiling-hz", type=float, default=20000.0)
    parser.add_argument("--output-md", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument(
        "--phi",
        action="store_true",
        help="Recompute EWSD under all amplitude-family φ and write Spearman ranks.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.phi:
        if args.analysis_root is None:
            raise SystemExit("--phi requires --analysis-root")
        out_md = args.output_md or Path("docs/validation/EWSD_SENSITIVITY_PHI.md")
        out_json = args.output_json or Path("docs/validation/EWSD_SENSITIVITY_PHI.json")
        run_phi_report(
            analysis_root=args.analysis_root,
            frequency_ceiling_hz=args.frequency_ceiling_hz,
            output_md=out_md,
            output_json=out_json,
        )
        print(f"Wrote {out_md} and {out_json}")
        return 0

    out_md = args.output_md or Path("ewsd_sensitivity_report.md")
    out_json = args.output_json or Path("ewsd_sensitivity_report.json")
    run_report(
        analysis_root=args.analysis_root,
        reference_xlsx=args.reference_xlsx,
        frequency_ceiling_hz=args.frequency_ceiling_hz,
        output_md=out_md,
        output_json=out_json,
    )
    print(f"Wrote {out_md} and {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
