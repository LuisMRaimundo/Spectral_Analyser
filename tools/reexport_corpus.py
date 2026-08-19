"""Re-export Stage 2/3 after a code change and diff Stage 3 vs a baseline.

Usage::

    python -m tools.reexport_corpus --stage1-root <analysis_results> --out <dir> \\
        --baseline docs/validation/ANALISE_3_TUBA_PP_EWSD_2026_08_19.json

The wrapper runs ``run_orchestrator`` stages 2 and 3 (optionally 1) and
writes a per-note Δ table for ``EWSD_score_acoustic_balanced``. Notes
whose relative change exceeds ``REEXPORT_REL_DELTA_FLAG_PCT`` are listed
with any ``rejected_floor`` CFAR margins found in the Stage 1 workbooks.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from constants import (
    DENSITY_WEIGHT_FUNCTION_DEFAULT,
    FFT_POLICY_DEFAULT,
    FIXED_HOP_LENGTH_DEFAULT,
    FIXED_N_FFT_DEFAULT,
    REEXPORT_REL_DELTA_FLAG_PCT,
)
from run_manifest import (
    STAGE3_SCORE_COLUMN,
    discover_corpus_audio,
    looks_like_stage1_root,
    parse_stages,
)

ANALISE_3_BASELINE = (
    _REPO_ROOT / "docs" / "validation" / "ANALISE_3_TUBA_PP_EWSD_2026_08_19.json"
)
FLOOR_STATUS_TOKEN = "rejected_floor"
SCORE_ALIASES = (
    STAGE3_SCORE_COLUMN,
    "ewsd_score_acoustic_balanced",
    "EWSD_score_acoustic_balance",
)


def _note_key(value: Any) -> str:
    return str(value or "").strip()


def _first_present(df: pd.DataFrame, names: Sequence[str]) -> Optional[str]:
    lower = {str(c).strip().lower(): str(c) for c in df.columns}
    for name in names:
        hit = lower.get(str(name).strip().lower())
        if hit:
            return hit
    return None


def load_stage3_series(path: Union[str, Path]) -> pd.DataFrame:
    """Load ``Note`` + EWSD acoustic-balanced scores from xlsx / json / csv / manifest."""
    src = Path(path)
    if not src.is_file():
        raise FileNotFoundError(src)
    suffix = src.suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        sheets = {}
        with pd.ExcelFile(src) as xf:
            sheets = {name: name for name in xf.sheet_names}
        preferred_names = [
            name
            for name in ("Spectral_Density_Metrics", "Density_Metrics", "Metrics")
            if name in sheets
        ]
        if not preferred_names:
            preferred_names = list(sheets)
        df = None
        for name in preferred_names:
            candidate = pd.read_excel(src, sheet_name=name)
            if (
                _first_present(candidate, ("Note", "sample_note_tag", "note"))
                and _first_present(candidate, SCORE_ALIASES)
            ):
                df = candidate
                break
        if df is None:
            raise ValueError(f"{src} has no Note / {STAGE3_SCORE_COLUMN} columns")
    elif suffix == ".csv":
        df = pd.read_csv(src)
    else:
        payload = json.loads(src.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "notes" in payload:
            df = pd.DataFrame(payload["notes"])
        elif isinstance(payload, dict) and "outputs" in payload:
            research = payload.get("outputs", {}).get("research_workbook")
            if research and Path(research).is_file():
                return load_stage3_series(research)
            raise ValueError(f"manifest {src} has no readable research workbook")
        elif isinstance(payload, list):
            df = pd.DataFrame(payload)
        else:
            raise ValueError(f"unrecognised Stage 3 series JSON: {src}")
    note_col = _first_present(df, ("Note", "sample_note_tag", "note"))
    score_col = _first_present(df, SCORE_ALIASES)
    if note_col is None or score_col is None:
        raise ValueError(f"{src} has no Note / {STAGE3_SCORE_COLUMN} columns")
    out = pd.DataFrame(
        {
            "Note": df[note_col].map(_note_key),
            STAGE3_SCORE_COLUMN: pd.to_numeric(df[score_col], errors="coerce"),
        }
    )
    out = out[out["Note"] != ""]
    return out.drop_duplicates(subset=["Note"], keep="first").reset_index(drop=True)


def relative_delta_pct(current: float, baseline: float) -> float:
    if baseline == 0 or baseline != baseline:
        if current == 0 or current != current:
            return 0.0
        return float("inf")
    return 100.0 * (float(current) - float(baseline)) / abs(float(baseline))


def diff_stage3_series(
    current: pd.DataFrame,
    baseline: pd.DataFrame,
    *,
    threshold_pct: float = REEXPORT_REL_DELTA_FLAG_PCT,
) -> pd.DataFrame:
    """Per-note Δ and relative Δ of the Stage 3 acoustic-balanced score."""
    left = current.rename(columns={STAGE3_SCORE_COLUMN: "current"}).copy()
    right = baseline.rename(columns={STAGE3_SCORE_COLUMN: "baseline"}).copy()
    merged = left.merge(right, on="Note", how="outer")
    merged["delta"] = merged["current"] - merged["baseline"]
    merged["rel_delta_pct"] = [
        relative_delta_pct(c, b)
        for c, b in zip(merged["current"].tolist(), merged["baseline"].tolist())
    ]
    merged["abs_rel_delta_pct"] = merged["rel_delta_pct"].abs()
    merged["exceeds_threshold"] = merged["abs_rel_delta_pct"] > float(threshold_pct)
    return merged.sort_values("Note").reset_index(drop=True)


def _sheet_or_empty(path: Path, name: str) -> pd.DataFrame:
    try:
        return pd.read_excel(path, sheet_name=name)
    except Exception:
        return pd.DataFrame()


def collect_floor_row_explanations(stage1_root: Union[str, Path]) -> List[Dict[str, Any]]:
    """List ``rejected_floor`` rows and their CFAR margins from Stage 1 workbooks."""
    root = Path(stage1_root)
    explanations: List[Dict[str, Any]] = []
    if not root.is_dir():
        return explanations
    for workbook in sorted(root.rglob("spectral_analysis.xlsx")):
        note = ""
        metrics = _sheet_or_empty(workbook, "Metrics")
        if not metrics.empty:
            note_col = _first_present(metrics, ("Note", "sample_note_tag"))
            if note_col:
                note = _note_key(metrics.iloc[0][note_col])
        if not note:
            note = workbook.parent.name
        rows: List[Dict[str, Any]] = []
        for sheet in (
            "Confirmed_Inharmonic_Partials",
            "Inharmonic Spectrum",
            "Harmonic Spectrum",
        ):
            df = _sheet_or_empty(workbook, sheet)
            if df.empty:
                continue
            status_col = _first_present(
                df, ("inharmonic_status", "exclusion_reason", "status")
            )
            margin_col = _first_present(
                df, ("cfar_margin_db_i", "cfar_margin_db")
            )
            if status_col is None:
                continue
            status = df[status_col].astype(str)
            mask = status.str.contains(FLOOR_STATUS_TOKEN, case=False, na=False)
            picked = df.loc[mask]
            for _, rec in picked.iterrows():
                margin = float("nan")
                if margin_col is not None:
                    try:
                        margin = float(rec[margin_col])
                    except (TypeError, ValueError):
                        margin = float("nan")
                freq = rec.get("Frequency (Hz)", rec.get("frequency_hz"))
                rows.append(
                    {
                        "sheet": sheet,
                        "frequency_hz": None if freq != freq else freq,
                        "cfar_margin_db": None if margin != margin else margin,
                        "status": str(rec[status_col]),
                    }
                )
        if not rows:
            continue
        margins = [
            float(r["cfar_margin_db"])
            for r in rows
            if r.get("cfar_margin_db") is not None
        ]
        explanations.append(
            {
                "Note": note,
                "workbook": str(workbook),
                "floor_row_count": len(rows),
                "cfar_margin_db_min": min(margins) if margins else None,
                "cfar_margin_db_max": max(margins) if margins else None,
                "rows": rows,
            }
        )
    return explanations


def annotate_diff_with_floor_rows(
    diff: pd.DataFrame,
    explanations: Sequence[Dict[str, Any]],
) -> pd.DataFrame:
    by_note = {_note_key(item["Note"]): item for item in explanations}
    out = diff.copy()
    out["floor_row_count"] = 0
    out["cfar_margin_db_min"] = float("nan")
    out["explanation"] = ""
    for idx, row in out.iterrows():
        item = by_note.get(_note_key(row["Note"]))
        if item:
            out.at[idx, "floor_row_count"] = int(item["floor_row_count"])
            if item.get("cfar_margin_db_min") is not None:
                out.at[idx, "cfar_margin_db_min"] = item["cfar_margin_db_min"]
        if not bool(row.get("exceeds_threshold")):
            continue
        if item:
            margin = item.get("cfar_margin_db_min")
            margin_txt = "n/a" if margin is None else f"{margin:.2f} dB"
            out.at[idx, "explanation"] = (
                f"removed floor rows={item['floor_row_count']}; "
                f"min CFAR margin={margin_txt}"
            )
        else:
            out.at[idx, "explanation"] = (
                "exceeds threshold without rejected_floor rows in Stage 1 "
                "(φ / compile / gating change)"
            )
    return out


def summarize_diff(diff: pd.DataFrame) -> Dict[str, Any]:
    finite = diff["abs_rel_delta_pct"].replace([float("inf")], pd.NA).dropna()
    flagged = diff[diff["exceeds_threshold"]].copy()
    return {
        "n_notes": int(len(diff)),
        "n_compared": int(diff[["current", "baseline"]].dropna().shape[0]),
        "max_abs_rel_delta_pct": None if finite.empty else float(finite.max()),
        "n_exceeding_threshold": int(len(flagged)),
        "flagged_notes": [
            {
                "Note": _note_key(row["Note"]),
                "baseline": None if pd.isna(row["baseline"]) else float(row["baseline"]),
                "current": None if pd.isna(row["current"]) else float(row["current"]),
                "rel_delta_pct": None
                if pd.isna(row["rel_delta_pct"])
                else float(row["rel_delta_pct"]),
                "explanation": str(row.get("explanation") or ""),
                "floor_row_count": int(row.get("floor_row_count") or 0),
                "cfar_margin_db_min": None
                if pd.isna(row.get("cfar_margin_db_min"))
                else float(row["cfar_margin_db_min"]),
            }
            for _, row in flagged.iterrows()
        ],
    }


def build_diff_markdown(
    *,
    summary: Dict[str, Any],
    diff: pd.DataFrame,
    baseline_label: str,
    current_label: str,
    threshold_pct: float,
) -> str:
    lines = [
        "# Stage 3 re-export diff",
        "",
        f"Baseline: {baseline_label}",
        f"Current: {current_label}",
        f"Metric: `{STAGE3_SCORE_COLUMN}`",
        f"Flag threshold: |Δ| / |baseline| > {threshold_pct:g} %",
        "",
        f"Notes compared: {summary['n_compared']} / {summary['n_notes']}",
        f"Maximum |rel Δ|: {summary['max_abs_rel_delta_pct']}",
        f"Notes exceeding threshold: {summary['n_exceeding_threshold']}",
        "",
        "## Flagged notes",
        "",
    ]
    flagged = summary.get("flagged_notes") or []
    if not flagged:
        lines.append("None.")
    else:
        lines.append("| Note | baseline | current | rel Δ % | explanation |")
        lines.append("|------|---------:|--------:|--------:|-------------|")
        for item in flagged:
            lines.append(
                "| {Note} | {baseline} | {current} | {rel_delta_pct} | {explanation} |".format(
                    Note=item["Note"],
                    baseline="—" if item["baseline"] is None else f"{item['baseline']:.4g}",
                    current="—" if item["current"] is None else f"{item['current']:.4g}",
                    rel_delta_pct="—"
                    if item["rel_delta_pct"] is None
                    else f"{item['rel_delta_pct']:.2f}",
                    explanation=item["explanation"] or "",
                )
            )
    lines.extend(["", "## All notes", ""])
    lines.append("| Note | baseline | current | Δ | rel Δ % | flag |")
    lines.append("|------|---------:|--------:|--:|--------:|:----:|")
    for _, row in diff.iterrows():
        lines.append(
            "| {note} | {base} | {cur} | {delta} | {rel} | {flag} |".format(
                note=_note_key(row["Note"]),
                base="—" if pd.isna(row["baseline"]) else f"{float(row['baseline']):.4g}",
                cur="—" if pd.isna(row["current"]) else f"{float(row['current']):.4g}",
                delta="—" if pd.isna(row["delta"]) else f"{float(row['delta']):.4g}",
                rel="—"
                if pd.isna(row["rel_delta_pct"])
                else f"{float(row['rel_delta_pct']):.2f}",
                flag="yes" if bool(row["exceeds_threshold"]) else "",
            )
        )
    lines.append("")
    return "\n".join(lines)


def write_diff_artefacts(
    out_dir: Union[str, Path],
    *,
    diff: pd.DataFrame,
    summary: Dict[str, Any],
    markdown: str,
) -> Dict[str, Path]:
    dest = Path(out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    json_path = dest / "stage3_reexport_diff.json"
    md_path = dest / "stage3_reexport_diff.md"
    csv_path = dest / "stage3_reexport_diff.csv"
    payload = {
        "summary": summary,
        "notes": json.loads(diff.to_json(orient="records")),
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    diff.to_csv(csv_path, index=False)
    return {"json": json_path, "markdown": md_path, "csv": csv_path}


def run_reexport(
    *,
    stage1_root: Path,
    out_dir: Path,
    stages: Sequence[int] = (2, 3),
    figures: bool = False,
    weight_function: str = DENSITY_WEIGHT_FUNCTION_DEFAULT,
    audio_files: Optional[Sequence[Path]] = None,
    fft_policy: str = FFT_POLICY_DEFAULT,
    fixed_n_fft: int = FIXED_N_FFT_DEFAULT,
    fixed_hop_length: int = FIXED_HOP_LENGTH_DEFAULT,
) -> Dict[str, Any]:
    """Run selected stages and return the orchestrator result dict."""
    from pipeline_orchestrator_integrated import RobustOrchestrator

    if 1 in stages and not audio_files:
        raise ValueError("Stage 1 requires audio files")
    if 1 not in stages and not looks_like_stage1_root(stage1_root):
        raise FileNotFoundError(
            f"no spectral_analysis.xlsx under {stage1_root}"
        )
    orchestrator = RobustOrchestrator(
        audio_files=list(audio_files or []),
        main_analysis_output_dir=out_dir,
        weight_function=weight_function,
        stage1_search_root=None if 1 in stages else stage1_root,
        figures=figures,
        fft_policy=str(fft_policy),
        fixed_n_fft=int(fixed_n_fft),
        fixed_hop_length=int(fixed_hop_length),
    )
    return orchestrator.run_selected_stages(list(stages), figures=figures)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Re-export Stage 2/3 from existing Stage 1 workbooks and diff "
            "EWSD_score_acoustic_balanced against a previous series."
        )
    )
    parser.add_argument(
        "--corpus",
        type=str,
        help="Audio corpus directory (implies Stage 1–3 when --stages omitted).",
    )
    parser.add_argument(
        "--fft-policy",
        default=FFT_POLICY_DEFAULT,
        choices=("fixed", "adaptive_tier"),
        help=f"FFT policy (default: {FFT_POLICY_DEFAULT}).",
    )
    parser.add_argument(
        "--fixed-n-fft",
        type=int,
        default=FIXED_N_FFT_DEFAULT,
    )
    parser.add_argument(
        "--fixed-hop-length",
        type=int,
        default=FIXED_HOP_LENGTH_DEFAULT,
    )
    parser.add_argument(
        "--stage1-root",
        type=str,
        help="Directory tree containing spectral_analysis.xlsx (or audio if Stage 1).",
    )
    parser.add_argument("--out", required=True, type=str, help="Output directory.")
    parser.add_argument(
        "--baseline",
        type=str,
        default=str(ANALISE_3_BASELINE),
        help="Previous Stage 3 series (xlsx / json / csv / run_manifest.json).",
    )
    parser.add_argument("--stages", default="2,3", help="Stages to run (default: 2,3).")
    parser.add_argument(
        "--figures",
        action="store_true",
        help="Write Stage 3 charts (EWSD CI figure).",
    )
    parser.add_argument(
        "--weight-function",
        default=DENSITY_WEIGHT_FUNCTION_DEFAULT,
        help=f"Stage 2/3 φ (default: {DENSITY_WEIGHT_FUNCTION_DEFAULT}).",
    )
    parser.add_argument(
        "--threshold-pct",
        type=float,
        default=REEXPORT_REL_DELTA_FLAG_PCT,
        help="Relative-Δ flag percent (default: REEXPORT_REL_DELTA_FLAG_PCT).",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Diff an existing research workbook in --out; do not re-run stages.",
    )
    parser.add_argument(
        "--current",
        type=str,
        help="Explicit current Stage 3 workbook/series (overrides --out lookup).",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stages = parse_stages(args.stages)
    corpus = Path(args.corpus) if getattr(args, "corpus", None) else None
    audio_files = discover_corpus_audio(corpus) if corpus and corpus.is_dir() else None
    if corpus is not None and 1 not in stages:
        stages = parse_stages("1,2,3")
    stage1_root = Path(args.stage1_root) if args.stage1_root else (corpus or out_dir)
    if not args.skip_run:
        run_reexport(
            stage1_root=stage1_root,
            out_dir=out_dir,
            stages=stages,
            figures=bool(args.figures),
            weight_function=str(args.weight_function),
            audio_files=audio_files,
            fft_policy=str(args.fft_policy),
            fixed_n_fft=int(args.fixed_n_fft),
            fixed_hop_length=int(args.fixed_hop_length),
        )
    current_path = Path(args.current) if args.current else None
    if current_path is None:
        candidate = out_dir / "compiled_density_metrics_research.xlsx"
        if candidate.is_file():
            current_path = candidate
        else:
            manifest = out_dir / "run_manifest.json"
            if manifest.is_file():
                current_path = manifest
    if current_path is None or not current_path.exists():
        print("error: no current Stage 3 series to diff", file=sys.stderr)
        return 1
    current = load_stage3_series(current_path)
    baseline = load_stage3_series(args.baseline)
    diff = diff_stage3_series(current, baseline, threshold_pct=float(args.threshold_pct))
    explanations = collect_floor_row_explanations(stage1_root)
    if 1 in stages:
        explanations = collect_floor_row_explanations(out_dir) or explanations
    diff = annotate_diff_with_floor_rows(diff, explanations)
    summary = summarize_diff(diff)
    markdown = build_diff_markdown(
        summary=summary,
        diff=diff,
        baseline_label=str(args.baseline),
        current_label=str(current_path),
        threshold_pct=float(args.threshold_pct),
    )
    artefacts = write_diff_artefacts(
        out_dir, diff=diff, summary=summary, markdown=markdown
    )
    print(f"Compared {summary['n_compared']} notes; "
          f"{summary['n_exceeding_threshold']} exceed {args.threshold_pct:g} %")
    print(f"Diff markdown: {artefacts['markdown']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
