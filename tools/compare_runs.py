"""Compare two Stage 3 research workbooks at tier boundaries.

Usage::

    python -m tools.compare_runs <run_a> <run_b> \\
        --metrics EWSD_score_acoustic_balanced,core_harmonic_energy_ratio,\\
                  harmonic_density_sum,subbass_density_sum,effective_partial_density \\
        --boundaries G3:G#3,B4:C5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

ENERGY_DEPENDENT = {
    "EWSD_score_acoustic_balanced",
    "EWSD_score_total",
    "core_harmonic_energy_ratio",
    "harmonic_energy_ratio",
    "harmonic_density_sum",
    "inharmonic_density_sum",
    "subbass_density_sum",
}
DEFAULT_METRICS = (
    "EWSD_score_acoustic_balanced",
    "core_harmonic_energy_ratio",
    "harmonic_density_sum",
    "subbass_density_sum",
    "effective_partial_density",
)
DEFAULT_BOUNDARIES = (("G3", "G#3"), ("B4", "C5"))


def _first_col(df: pd.DataFrame, *names: str) -> Optional[str]:
    lower = {str(c).strip().lower(): str(c) for c in df.columns}
    for name in names:
        hit = lower.get(str(name).strip().lower())
        if hit:
            return hit
    return None


def load_metrics_frame(path: Path) -> pd.DataFrame:
    src = Path(path)
    if src.is_dir():
        for cand in (
            src / "compiled_density_metrics_research.xlsx",
            src / "compiled_density_metrics.xlsx",
        ):
            if cand.is_file():
                src = cand
                break
        else:
            raise FileNotFoundError(f"no compiled workbook under {path}")
    sheets = pd.ExcelFile(src).sheet_names
    for name in ("Spectral_Density_Metrics", "Density_Metrics", "Metrics"):
        if name in sheets:
            df = pd.read_excel(src, sheet_name=name)
            note_col = _first_col(df, "Note", "sample_note_tag")
            if note_col:
                df = df.rename(columns={note_col: "Note"})
                df["Note"] = df["Note"].astype(str).str.strip()
                return df
    raise ValueError(f"{src} has no Note sheet")


def _num(df: pd.DataFrame, note: str, metric: str) -> float:
    col = _first_col(df, metric)
    if col is None:
        return float("nan")
    hit = df.loc[df["Note"].str.replace("♯", "#") == note.replace("♯", "#")]
    if hit.empty:
        return float("nan")
    return float(pd.to_numeric(hit.iloc[0][col], errors="coerce"))


def step_ratio(a: float, b: float) -> float:
    if a != a or b != b or a == 0.0:
        return float("nan")
    return abs(b - a) / abs(a)


def compare(
    run_a: Path,
    run_b: Path,
    *,
    metrics: Sequence[str],
    boundaries: Sequence[Tuple[str, str]],
    energy_step_max: float = 0.10,
    pair_rel_max: float = 0.05,
) -> Dict[str, Any]:
    fa = load_metrics_frame(run_a)
    fb = load_metrics_frame(run_b)
    notes = sorted(set(fa["Note"].tolist()) | set(fb["Note"].tolist()))
    per_note: List[Dict[str, Any]] = []
    pair_fail = False
    for note in notes:
        rec: Dict[str, Any] = {"Note": note}
        for metric in metrics:
            va = _num(fa, note, metric)
            vb = _num(fb, note, metric)
            rec[f"{metric}_a"] = va
            rec[f"{metric}_b"] = vb
            rec[f"{metric}_rel"] = step_ratio(va, vb)
            if (
                metric in ENERGY_DEPENDENT
                and rec[f"{metric}_rel"] == rec[f"{metric}_rel"]
                and rec[f"{metric}_rel"] > pair_rel_max
            ):
                pair_fail = True
        per_note.append(rec)

    boundary_rows: List[Dict[str, Any]] = []
    step_fail = False
    for left, right in boundaries:
        rec = {"boundary": f"{left}:{right}"}
        epd_step = step_ratio(
            _num(fa, left, "effective_partial_density"),
            _num(fa, right, "effective_partial_density"),
        )
        rec["effective_partial_density_step"] = epd_step
        for metric in metrics:
            st = step_ratio(_num(fa, left, metric), _num(fa, right, metric))
            rec[f"{metric}_step"] = st
            if (
                metric in ENERGY_DEPENDENT
                and st == st
                and st > energy_step_max
                and not (epd_step == epd_step and epd_step > energy_step_max)
            ):
                step_fail = True
        boundary_rows.append(rec)

    return {
        "per_note": per_note,
        "boundaries": boundary_rows,
        "pair_fail": pair_fail,
        "step_fail": step_fail,
        "ok": not (pair_fail or step_fail),
    }


def _parse_boundaries(raw: str) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for token in str(raw or "").split(","):
        if ":" not in token:
            continue
        a, b = token.split(":", 1)
        out.append((a.strip(), b.strip()))
    return out or list(DEFAULT_BOUNDARIES)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Compare two Stage 3 runs")
    parser.add_argument("run_a")
    parser.add_argument("run_b")
    parser.add_argument(
        "--metrics",
        default=",".join(DEFAULT_METRICS),
    )
    parser.add_argument(
        "--boundaries",
        default="G3:G#3,B4:C5",
    )
    parser.add_argument("--json-out", type=str, default="")
    args = parser.parse_args(argv)
    metrics = [m.strip() for m in str(args.metrics).split(",") if m.strip()]
    payload = compare(
        Path(args.run_a),
        Path(args.run_b),
        metrics=metrics,
        boundaries=_parse_boundaries(args.boundaries),
    )
    print(json.dumps(payload, indent=2))
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
