"""R6b WP2 halt: |ΔEWSD| > 25 % on > 5 % of pretag-matched notes.

Pretags for Iowa bass / cello are the existing CORDAS_2
``analysis_results`` workbooks (the trees behind ρ = −0.046 / the old
cello sheets). New trees are ``analysis_results_v4.2.3``.
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

HALT_FRAC = 0.05
HALT_ABS_REL = 0.25
METRIC = "EWSD_score_acoustic_balanced"
EPD = "note_effective_component_density"

CORDAS2_BASS = Path(r"D:\CORDAS_2\IOWA\DOUBLE-BASS\IOWA_Cb_tratados")
CORDAS3_BASS = Path(r"D:\CORDAS_3\DOUBLE-BASS\IOWA_Cb_tratados")
CORDAS2_CELLO = Path(r"D:\CORDAS_2\IOWA\CELLO\IOWA_Cello_Arco\CELLO")
CORDAS3_CELLO = Path(r"D:\CORDAS_3\CELLO\IOWA_Cello_Arco\CELLO")


def _rel(new: float, old: float) -> float:
    if not (np.isfinite(new) and np.isfinite(old)):
        return float("nan")
    return float((new - old) / max(abs(old), 1e-12))


def _leaf_pairs_bass() -> List[tuple[str, Path, Path]]:
    pairs = []
    for old in sorted(CORDAS2_BASS.rglob("analysis_results/compiled_density_metrics_research.xlsx")):
        leaf = old.parents[2].name  # DB_Arco_sX_yy
        new = CORDAS3_BASS / old.relative_to(CORDAS2_BASS)
        new = new.parent.parent / "analysis_results_v4.2.3" / "compiled_density_metrics_research.xlsx"
        # old: .../DB_Arco_sA_ff/_Sustains_Stable/analysis_results/compiled.xlsx
        # new: .../DB_Arco_sA_ff/_Sustains_Stable/analysis_results_v4.2.3/compiled.xlsx
        new = old.parents[1]  # _Sustains_Stable on CORDAS_2
        # map to CORDAS_3 same relative from tratados
        rel = old.parents[1].relative_to(CORDAS2_BASS)
        new = CORDAS3_BASS / rel / "analysis_results_v4.2.3" / "compiled_density_metrics_research.xlsx"
        pairs.append((leaf, old, new))
    return pairs


def _compare_pair(name: str, old_xlsx: Path, new_xlsx: Path) -> Dict[str, Any]:
    rec: Dict[str, Any] = {"name": name, "old": str(old_xlsx), "new": str(new_xlsx)}
    if not old_xlsx.is_file() or not new_xlsx.is_file():
        rec["halt"] = False
        rec["reason"] = "missing_workbook"
        rec["old_exists"] = old_xlsx.is_file()
        rec["new_exists"] = new_xlsx.is_file()
        return rec
    old = load_metrics_frame(old_xlsx)
    new = load_metrics_frame(new_xlsx)
    merged = old.merge(new, on="Note", how="inner", suffixes=("_old", "_new"))
    rows = []
    for r in merged.to_dict(orient="records"):
        e_old = float(r[f"{METRIC}_old"])
        e_new = float(r[f"{METRIC}_new"])
        p_old = float(r.get(f"{EPD}_old", float("nan")))
        p_new = float(r.get(f"{EPD}_new", float("nan")))
        d = _rel(e_new, e_old)
        rows.append(
            {
                "Note": r["Note"],
                "EWSD_old": e_old,
                "EWSD_new": e_new,
                "d_EWSD": d,
                "EPD_old": p_old,
                "EPD_new": p_new,
                "d_EPD": _rel(p_new, p_old),
            }
        )
    n = len(rows)
    n_halt = sum(1 for x in rows if np.isfinite(x["d_EWSD"]) and abs(x["d_EWSD"]) > HALT_ABS_REL)
    frac = (n_halt / n) if n else 0.0
    worst = sorted(rows, key=lambda x: abs(x["d_EWSD"]) if np.isfinite(x["d_EWSD"]) else -1, reverse=True)[:3]
    rec.update(
        {
            "matched": n,
            "n_over_25pct": n_halt,
            "frac": frac,
            "halt": bool(n > 0 and frac > HALT_FRAC),
            "three_worst": worst,
            "mixed_baseline_caveat": (
                "Old CORDAS_2 trees are SustainStable pre-v4.2.3; new trees are "
                "v4.2.3 on the same Stable files (Iowa bass has no full _Sustains). "
                "Δ mixes code/policy, not a full-vs-stable cut."
            ),
        }
    )
    return rec


def _string_from_folder(name: str) -> str:
    import re
    n = name.lower().replace("á", "a").replace("ó", "o").replace("é", "e")
    m = re.search(r"s([acdg])_", n)
    if m:
        return m.group(1).upper()
    if "corda a" in n or "corda la" in n or n.endswith("a"):
        if "corda" in n:
            return "A"
    if "corda c" in n or "corda do" in n:
        return "C"
    if "corda d" in n or "corda re" in n:
        return "D"
    if "corda g" in n or "corda sol" in n:
        return "G"
    return "?"


def _new_cello_rows(dyn: str) -> pd.DataFrame:
    root = CORDAS3_CELLO / f"IOWA_cello_arco_{dyn}" / "analysis_results_v4.2.3"
    rows = []
    if not root.is_dir():
        return pd.DataFrame()
    for folder in root.iterdir():
        if not folder.is_dir():
            continue
        met_path = None
        for cand in folder.rglob("spectral_analysis.xlsx"):
            met_path = cand
            break
        if met_path is None:
            continue
        try:
            met = pd.read_excel(met_path, sheet_name="Metrics")
        except Exception:
            continue
        if met.empty:
            continue
        rec = met.iloc[0]
        rows.append(
            {
                "Note": rec.get("Note"),
                "string": _string_from_folder(folder.name),
                METRIC: rec.get(METRIC),
                EPD: rec.get(EPD, rec.get("effective_partial_density")),
                "folder": folder.name,
            }
        )
    return pd.DataFrame(rows)


def _leaf_pairs_cello() -> List[tuple[str, Path, str]]:
    pairs = []
    for old in sorted(CORDAS2_CELLO.rglob("analysis_results/compiled_density_metrics_research.xlsx")):
        # .../IOWA_cello_arco_pp_Corda A/_Sustains_Stable/analysis_results/compiled
        leaf = old.parents[2].name
        dyn = "pp" if "_pp" in leaf.lower() or leaf.lower().endswith("pp") else (
            "mf" if "_mf" in leaf.lower() or "mf" in leaf.lower() else (
                "ff" if "_ff" in leaf.lower() or "ff" in leaf.lower() else "?"
            )
        )
        if dyn not in {"pp", "mf"}:
            continue
        pairs.append((leaf, old, dyn))
    return pairs


def compare_cello() -> Dict[str, Any]:
    reports = []
    new_by_dyn = {d: _new_cello_rows(d) for d in ("pp", "mf")}
    for name, old_xlsx, dyn in _leaf_pairs_cello():
        s = _string_from_folder(name)
        rec: Dict[str, Any] = {"name": name, "string": s, "dynamic": dyn, "old": str(old_xlsx)}
        new = new_by_dyn.get(dyn, pd.DataFrame())
        if new.empty or not old_xlsx.is_file():
            rec["halt"] = False
            rec["reason"] = "missing"
            rec["matched"] = 0
            rec["n_over_25pct"] = 0
            reports.append(rec)
            continue
        old = load_metrics_frame(old_xlsx)
        sub = new[new["string"] == s].copy()
        merged = old.merge(sub, on="Note", how="inner", suffixes=("_old", "_new"))
        rows = []
        for r in merged.to_dict(orient="records"):
            e_old = float(r[f"{METRIC}_old"])
            e_new = float(r[f"{METRIC}_new"])
            p_old = float(r.get(f"{EPD}_old", float("nan")))
            p_new = float(r.get(f"{EPD}_new", float("nan")))
            rows.append(
                {
                    "Note": r["Note"],
                    "EWSD_old": e_old,
                    "EWSD_new": e_new,
                    "d_EWSD": _rel(e_new, e_old),
                    "EPD_old": p_old,
                    "EPD_new": p_new,
                    "d_EPD": _rel(p_new, p_old),
                }
            )
        n = len(rows)
        n_halt = sum(1 for x in rows if np.isfinite(x["d_EWSD"]) and abs(x["d_EWSD"]) > HALT_ABS_REL)
        frac = (n_halt / n) if n else 0.0
        worst = sorted(rows, key=lambda x: abs(x["d_EWSD"]) if np.isfinite(x["d_EWSD"]) else -1, reverse=True)[:3]
        rec.update(
            {
                "matched": n,
                "n_over_25pct": n_halt,
                "frac": frac,
                "halt": bool(n > 0 and frac > HALT_FRAC),
                "three_worst": worst,
                "mixed_baseline_caveat": (
                    "Old CORDAS_2 cello trees are SustainStable pre-v4.2.3; "
                    "new trees are v4.2.3 on CORDAS_3 _Sustains (same note counts)."
                ),
            }
        )
        reports.append(rec)
    return reports


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", choices=("bass", "cello"), default="bass")
    args = ap.parse_args()
    if args.corpus == "cello":
        reports = compare_cello()
    else:
        reports = [_compare_pair(n, o, nw) for n, o, nw in _leaf_pairs_bass()]
    # pool
    matched = sum(r.get("matched") or 0 for r in reports)
    n_over = sum(r.get("n_over_25pct") or 0 for r in reports)
    frac = (n_over / matched) if matched else 0.0
    all_worst = []
    for r in reports:
        for w in r.get("three_worst") or []:
            w = dict(w)
            w["leaf"] = r["name"]
            all_worst.append(w)
    all_worst = sorted(
        all_worst,
        key=lambda x: abs(x["d_EWSD"]) if np.isfinite(x.get("d_EWSD", float("nan"))) else -1,
        reverse=True,
    )[:3]
    out = {
        "corpus": args.corpus,
        "leaves": reports,
        "pooled_matched": matched,
        "pooled_n_over_25pct": n_over,
        "pooled_frac": frac,
        "halt": bool(matched > 0 and frac > HALT_FRAC),
        "three_worst_pooled": all_worst,
    }
    dest = _REPO / "docs" / "validation" / "_r6b" / f"halt_{args.corpus}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: out[k] for k in out if k != "leaves"}, indent=2, default=str))
    print("wrote", dest)
    return 0 if not out["halt"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
