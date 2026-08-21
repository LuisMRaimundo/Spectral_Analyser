"""R6 halt guard: unexplained |Δ| > 25 % on > 5 % of matched notes.

Execution only. Does not change estimators. Pretag workbooks are
SustainStable Test-tree; new runs are full ``_Sustains`` — that mix is
stated on every row, not treated as a silent excuse to continue.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.compare_runs import load_metrics_frame

PRETAG = _REPO / "docs" / "validation" / "pretag_evidence"
HALT_FRAC = 0.05
HALT_ABS_REL = 0.25

PRETAG_FOR = {
    "trombone_pp": PRETAG / "trombone_pp_compiled_density_metrics_research.xlsx",
    "trombone_mf": PRETAG / "trombone_mf_compiled_density_metrics_research.xlsx",
    "trombone_ff": PRETAG / "trombone_ff_compiled_density_metrics_research.xlsx",
    "flute_pp": PRETAG / "flute_pp_compiled_density_metrics_research.xlsx",
    "flute_mf": PRETAG / "flute_mf_compiled_density_metrics_research.xlsx",
    "flute_ff": PRETAG / "flute_ff_compiled_density_metrics_research.xlsx",
}

METRIC_EWSD = "EWSD_score_acoustic_balanced"
METRIC_EPD = "note_effective_component_density"
METRIC_EPD_FALLBACK = "effective_partial_density"
METRIC_SNR = "estimated_snr_db"


def _rel_delta(new: float, old: float) -> float:
    if not (np.isfinite(new) and np.isfinite(old)):
        return float("nan")
    den = max(abs(old), 1e-12)
    return float((new - old) / den)


def compare_corpus(name: str, new_root: Path) -> Dict[str, Any]:
    pretag = PRETAG_FOR.get(name)
    if pretag is None or not Path(pretag).is_file():
        return {
            "name": name,
            "halt": False,
            "reason": "no_pretag_baseline",
            "new_root": str(new_root),
        }
    old = load_metrics_frame(Path(pretag))
    new = load_metrics_frame(Path(new_root))
    epd_old = METRIC_EPD if METRIC_EPD in old.columns else METRIC_EPD_FALLBACK
    epd_new = METRIC_EPD if METRIC_EPD in new.columns else METRIC_EPD_FALLBACK
    merged = old.merge(new, on="Note", how="inner", suffixes=("_old", "_new"))
    rows: List[Dict[str, Any]] = []
    for rec in merged.to_dict(orient="records"):
        ewsd_old = float(rec.get(f"{METRIC_EWSD}_old", rec.get(METRIC_EWSD, float("nan"))))
        ewsd_new = float(rec.get(f"{METRIC_EWSD}_new", float("nan")))
        # merge suffixes
        if f"{METRIC_EWSD}_old" in rec:
            ewsd_old = float(rec[f"{METRIC_EWSD}_old"])
            ewsd_new = float(rec[f"{METRIC_EWSD}_new"])
        epd_o = float(rec.get(f"{epd_old}_old", rec.get(epd_old, float("nan"))))
        epd_n = float(rec.get(f"{epd_new}_new", rec.get(epd_new, float("nan"))))
        if f"{epd_old}_old" in rec:
            epd_o = float(rec[f"{epd_old}_old"])
        if f"{epd_new}_new" in rec:
            epd_n = float(rec[f"{epd_new}_new"])
        d_e = _rel_delta(ewsd_new, ewsd_old)
        d_p = _rel_delta(epd_n, epd_o)
        snr = rec.get(f"{METRIC_SNR}_new", rec.get(METRIC_SNR, float("nan")))
        rows.append(
            {
                "Note": rec["Note"],
                "EWSD_old": ewsd_old,
                "EWSD_new": ewsd_new,
                "EWSD_rel": d_e,
                "EPD_old": epd_o,
                "EPD_new": epd_n,
                "EPD_rel": d_p,
                "estimated_snr_db": snr,
                "cut_mix": "pretag=SustainStable Test-tree; new=full _Sustains",
            }
        )
    n = len(rows)
    big = [r for r in rows if np.isfinite(r["EWSD_rel"]) and abs(r["EWSD_rel"]) > HALT_ABS_REL]
    frac = (len(big) / n) if n else 0.0
    worst = sorted(big, key=lambda r: abs(r["EWSD_rel"]), reverse=True)[:3]
    halt = bool(n > 0 and frac > HALT_FRAC)
    return {
        "name": name,
        "new_root": str(new_root),
        "pretag": str(pretag),
        "n_matched": n,
        "n_ewsd_abs_gt_25pct": len(big),
        "frac_ewsd_abs_gt_25pct": frac,
        "halt": halt,
        "reason": (
            "unexplained |Δ EWSD| > 25% on > 5% of matched notes; "
            "attach three worst audit sheets and wait"
            if halt
            else "below halt threshold"
        ),
        "three_worst": worst,
        "rows": rows,
        "note": (
            "Pretags are SustainStable Test-tree at 6b0e51a. "
            "Δ mixes tag/policy and full-vs-stable cut."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("new_root")
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()
    report = compare_corpus(args.name, Path(args.new_root))
    text = json.dumps(
        {k: v for k, v in report.items() if k != "rows"},
        indent=2,
        default=str,
    )
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(report, indent=2, default=str), encoding="utf-8"
        )
    return 2 if report.get("halt") else 0


if __name__ == "__main__":
    raise SystemExit(main())
