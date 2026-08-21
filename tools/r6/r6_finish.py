"""R6 finish: manifests, diffs, flags, Part D tables. Execution only."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.compare_runs import load_metrics_frame
from tools.r6.r6_pretag_halt import PRETAG_FOR, compare_corpus
from tools.run_measurement_evaluation import _note_rank, _score_part_d

OUT = _REPO / "docs" / "validation" / "_r6_reexport"

JOBS = {
    "trombone_pp": Path(r"D:\METAIS\TROMBONE\IOWA_Trombone\TenorTrombone\IOWA_Trombone_pp\_Sustains\analysis_results_v4.2.3"),
    "trombone_mf": Path(r"D:\METAIS\TROMBONE\IOWA_Trombone\TenorTrombone\IOWA_Trombone_mf\_Sustains\analysis_results_v4.2.3"),
    "trombone_ff": Path(r"D:\METAIS\TROMBONE\IOWA_Trombone\TenorTrombone\IOWA_Trombone_ff\_Sustains\analysis_results_v4.2.3"),
    "flute_pp": Path(r"D:\MADEIRAS\FLAUTA\IOWA_flute\IOWA_Flute_pp\_Sustains\analysis_results_v4.2.3"),
    "flute_mf": Path(r"D:\MADEIRAS\FLAUTA\IOWA_flute\IOWA_Flute_mf\_Sustains\analysis_results_v4.2.3"),
    "flute_ff": Path(r"D:\MADEIRAS\FLAUTA\IOWA_flute\IOWA_Flute_ff\_Sustains\analysis_results_v4.2.3"),
    "cello_ff": Path(r"D:\CORDAS_3\CELLO\IOWA_Cello_Arco\CELLO\IOWA_cello_arco_ff\analysis_results_v4.2.3"),
}

TUBA = Path(r"D:\METAIS\TUBA\Tuba\Tuba_Yowa\IOWA_tuba_pp\_Sustains\analysis_results_v4.2.1")
PROFILE = "wf=log|dst=-90.0|ceil=20000.0|fft=fixed|seg=sustain_primary_stable_diagnostic|elig=1"


def _bool_series(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series([False] * len(df), index=df.index)
    s = df[col]
    if s.dtype == object:
        return s.astype(str).str.lower().isin(("true", "1", "1.0", "yes"))
    return s.fillna(False).astype(bool)


def manifest_row(name: str, root: Path) -> Dict[str, Any]:
    man = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
    return {
        "name": name,
        "commit": man.get("code_commit"),
        "dirty": man.get("code_dirty"),
        "describe": man.get("git_describe"),
        "package_version": man.get("package_version"),
        "analysis_version": man.get("analysis_version"),
        "profile_id": man.get("analysis_parameter_profile_id"),
        "fft_policy": man.get("fft_policy"),
        "n_fft": man.get("fixed_n_fft"),
        "hop": man.get("fixed_hop_length"),
        "segment_policy": man.get("segment_policy"),
        "n_input": len(man.get("input_files") or []),
        "wall_s": man.get("wall_time_s"),
        "out": str(root),
    }


def flags_and_part_d(name: str, root: Path) -> Dict[str, Any]:
    df = load_metrics_frame(root)
    n = len(df)
    elig = _bool_series(df, "ewsd_primary_analysis_eligible")
    unrep = _bool_series(df, "stable_segment_unrepresentative")
    deg = _bool_series(df, "degenerate_partial_set")
    fragile = _bool_series(df, "density_fragile")
    newly_inelig = []
    newly_unrep = []
    if "Note" in df.columns:
        for rec, e, u in zip(df.to_dict("records"), elig, unrep):
            note = str(rec.get("Note"))
            if not e:
                newly_inelig.append(note)
            if u:
                newly_unrep.append(note)
    def _col(name: str) -> pd.Series:
        if name not in df.columns:
            return pd.Series(dtype=float)
        return pd.to_numeric(df[name], errors="coerce")

    h = _col("harmonic_validated_count")
    if h.empty or h.notna().sum() == 0:
        h = _col("validated_harmonic_component_count_body_ceiling")
    epd = _col("note_effective_component_density")
    ewsd = _col("EWSD_score_acoustic_balanced")
    resid = _col("core_residual_energy_ratio")
    rho_h = float(h.corr(epd, method="spearman")) if h.notna().sum() > 2 else float("nan")
    rho_e = float(ewsd.corr(epd, method="spearman")) if ewsd.notna().sum() > 2 else float("nan")
    epd_gt = int(((epd > h) & h.notna() & epd.notna()).sum()) if h is not None else 0
    closure = 0
    if all(c in df.columns for c in ("core_harmonic_energy_ratio", "core_residual_energy_ratio")):
        s = pd.to_numeric(df["core_harmonic_energy_ratio"], errors="coerce") + pd.to_numeric(
            df["core_residual_energy_ratio"], errors="coerce"
        )
        if "core_subbass_energy_ratio" in df.columns:
            s = s + pd.to_numeric(df["core_subbass_energy_ratio"], errors="coerce")
        closure = int((s.sub(1.0).abs() > 1e-3).sum())
    mono = 0
    if "Note" in df.columns and ewsd.notna().sum() > 2:
        order = df.assign(_midi=df["Note"].map(_note_rank), _ewsd=ewsd).dropna(subset=["_midi", "_ewsd"])
        order = order.sort_values("_midi")
        e = order["_ewsd"].to_numpy()
        m = order["_midi"].to_numpy()
        lo = pd.to_numeric(order["EWSD_score_acoustic_balanced_ci_low"], errors="coerce") if "EWSD_score_acoustic_balanced_ci_low" in order.columns else None
        hi = pd.to_numeric(order["EWSD_score_acoustic_balanced_ci_high"], errors="coerce") if "EWSD_score_acoustic_balanced_ci_high" in order.columns else None
        for i in range(1, len(e)):
            if m[i] <= m[i - 1]:
                continue
            if e[i] > e[i - 1]:
                overlap = False
                if lo is not None and hi is not None:
                    vals = [lo.iloc[i - 1], hi.iloc[i - 1], lo.iloc[i], hi.iloc[i]]
                    if all(np.isfinite(x) for x in vals):
                        overlap = not (vals[1] < vals[2] or vals[3] < vals[0])
                if not overlap:
                    mono += 1
    bounds = {}
    for note in ("G3", "G#3", "B4", "C5", "E6", "F6"):
        hit = df[df["Note"].astype(str).isin([note, note.replace("#", "♯")])]
        if hit.empty:
            continue
        bounds[note] = {
            "EWSD": float(pd.to_numeric(hit.iloc[0]["EWSD_score_acoustic_balanced"], errors="coerce")),
            "EPD": float(pd.to_numeric(hit.iloc[0].get("note_effective_component_density"), errors="coerce")),
        }
    pct_elig = float(100.0 * elig.mean()) if n else float("nan")
    item1 = 100 if pct_elig >= 95 else (70 if pct_elig >= 85 else 30)
    item2 = bool(np.isfinite(rho_h) and rho_h > 0 and epd_gt == 0 and closure == 0)
    return {
        "n": n,
        "pct_eligible": pct_elig,
        "ineligible_notes": newly_inelig,
        "unrepresentative_notes": newly_unrep,
        "n_degenerate": int(deg.sum()),
        "pct_fragile": float(100.0 * fragile.mean()) if n else float("nan"),
        "rho_H_EPD": rho_h,
        "rho_EWSD_EPD": rho_e,
        "epd_gt_validated": epd_gt,
        "energy_closure_violations": closure,
        "pitch_mono_violations": mono,
        "residual_median": float(resid.median()) if resid.notna().any() else float("nan"),
        "boundaries": bounds,
        "item1_score": item1,
        "item2_pass": item2,
    }


def midi_from_note(note: str) -> float:
    return _note_rank(note)


def cello_predictions(root: Path) -> Dict[str, Any]:
    df = load_metrics_frame(root)
    elig = _bool_series(df, "ewsd_primary_analysis_eligible")
    ewsd = pd.to_numeric(df["EWSD_score_acoustic_balanced"], errors="coerce")
    epd = pd.to_numeric(df["note_effective_component_density"], errors="coerce")
    midi = df["Note"].map(midi_from_note)
    ok = elig & ewsd.notna() & midi.notna()
    from scipy import stats

    rho_e, p_e = stats.spearmanr(midi[ok], ewsd[ok])
    okp = elig & epd.notna() & midi.notna()
    rho_p, p_p = stats.spearmanr(midi[okp], epd[okp])
    return {
        "n": int(len(df)),
        "n_eligible": int(elig.sum()),
        "rho_midi_ewsd": float(rho_e),
        "p_midi_ewsd": float(p_e),
        "rho_midi_epd": float(rho_p),
        "p_midi_epd": float(p_p),
        "note": "cello ff only — no pp/mf in this batch, so dynamic ε² is not recomputed here",
    }


def cordas2_epd_epsilon() -> Dict[str, Any]:
    """Same KW/ε² formula as analyze_ewsd_balanced.py, EPD column, CORDAS_2 trees."""
    from scipy import stats

    def epsilon_sq(H: float, k: int, n: int) -> float:
        if n <= k or k < 2:
            return float("nan")
        return float(max(0.0, (H - k + 1.0) / (n - k)))

    files = sorted(Path(r"D:\CORDAS_2").rglob("compiled_density_metrics_research.xlsx"))
    dyn: Dict[str, List[float]] = {"pp": [], "mf": [], "ff": []}
    bass_midi: List[float] = []
    bass_ewsd: List[float] = []
    bass_epd: List[float] = []
    n_files = 0
    for fp in files:
        try:
            df = pd.read_excel(fp, sheet_name="Spectral_Density_Metrics")
        except Exception:
            continue
        n_files += 1
        blob = str(fp).lower()
        if "ewsd_primary_analysis_eligible" in df.columns:
            el = df["ewsd_primary_analysis_eligible"]
            if el.dtype == object:
                mask = el.astype(str).str.lower().isin(("true", "1", "yes"))
            else:
                mask = el.fillna(False).astype(bool)
        else:
            mask = pd.Series([True] * len(df))
        ewsd = pd.to_numeric(df.get("EWSD_score_acoustic_balanced"), errors="coerce")
        epd = pd.to_numeric(
            df.get("note_effective_component_density", df.get("effective_partial_density")),
            errors="coerce",
        )
        dyn_lab = "?"
        leaf = fp.parent.name.lower() + " " + "/".join(p.lower() for p in fp.parts)
        if "_pp" in leaf or leaf.endswith("pp") or r"\pp" in blob or "_pp" in blob:
            dyn_lab = "pp"
        if "_mf" in blob or r"\mf" in blob:
            dyn_lab = "mf"
        if "_ff" in blob or r"\ff" in blob:
            dyn_lab = "ff"
        if dyn_lab in dyn:
            dyn[dyn_lab].extend(float(x) for x in epd[mask & epd.notna()].tolist())
        if "iowa" in blob and ("double" in blob or r"\cb" in blob or "iowa_cb" in blob or "bass" in blob):
            if "Note" in df.columns:
                for rec, keep in zip(df.to_dict("records"), mask):
                    if not keep:
                        continue
                    m = midi_from_note(str(rec.get("Note")))
                    ev = rec.get("EWSD_score_acoustic_balanced")
                    pv = rec.get("note_effective_component_density", rec.get("effective_partial_density"))
                    try:
                        evf, pvf = float(ev), float(pv)
                    except (TypeError, ValueError):
                        continue
                    if np.isfinite(m) and np.isfinite(evf):
                        bass_midi.append(m)
                        bass_ewsd.append(evf)
                        bass_epd.append(pvf if np.isfinite(pvf) else float("nan"))
    items = [(k, np.asarray(v, float)) for k, v in dyn.items() if len(v) >= 3]
    if len(items) >= 2:
        H, p = stats.kruskal(*[v for _, v in items])
        n = sum(len(v) for _, v in items)
        k = len(items)
        epd_kw = {"H": float(H), "p": float(p), "n": n, "k": k, "epsilon_sq": epsilon_sq(H, k, n)}
    else:
        epd_kw = {"ok": False, "n_groups": len(items)}
    from scipy import stats as st

    bass = {}
    if len(bass_midi) >= 8:
        rho, pv = st.spearmanr(bass_midi, bass_ewsd)
        okp = [np.isfinite(a) and np.isfinite(b) for a, b in zip(bass_midi, bass_epd)]
        if sum(okp) >= 8:
            rhop, pp = st.spearmanr(
                [m for m, f in zip(bass_midi, okp) if f],
                [e for e, f in zip(bass_epd, okp) if f],
            )
        else:
            rhop, pp = float("nan"), float("nan")
        bass = {
            "n": len(bass_midi),
            "rho_ewsd": float(rho),
            "p_ewsd": float(pv),
            "rho_epd": float(rhop),
            "p_epd": float(pp),
        }
    return {"n_workbooks": n_files, "epd_dynamic_kw": epd_kw, "iowa_bass": bass}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifests = [manifest_row(n, p) for n, p in JOBS.items()]
    diffs = {}
    for name, path in JOBS.items():
        if name in PRETAG_FOR:
            diffs[name] = compare_corpus(name, path)
            diffs[name].pop("rows", None)
    flags = {n: flags_and_part_d(n, p) for n, p in JOBS.items()}
    if TUBA.is_dir() and (TUBA / "run_manifest.json").is_file():
        flags["tuba_pp_v421"] = flags_and_part_d("tuba_pp", TUBA)
        manifests.append(manifest_row("tuba_pp_v421", TUBA))
    tables = [flags[n] for n in JOBS]
    item1_mean = float(np.mean([t["item1_score"] for t in tables]))
    item2 = all(t["item2_pass"] for t in tables)
    unexplained = sum(t["pitch_mono_violations"] for t in tables)
    item34 = 100 if unexplained == 0 else 30
    d_score = _score_part_d(item1_mean, item2, item34, None)
    # Recomputed composite from B1, B5, C1, C2, D only.
    b1 = 100  # PASS post-R2 at fixed window
    b5 = 100  # PASS post-R3
    c1 = 30  # 100% coverage
    c2 = 30  # slope −0.281
    composite = float(np.mean([b1, b5, c1, c2, d_score]))
    bundle = {
        "manifests": manifests,
        "same_commit": len({m["commit"] for m in manifests if m["name"] != "tuba_pp_v421"}) == 1,
        "same_profile_r6": len({m["profile_id"] for m in manifests if m["name"] != "tuba_pp_v421"}) == 1,
        "profile": PROFILE,
        "diffs": diffs,
        "flags": flags,
        "cello_predictions": cello_predictions(JOBS["cello_ff"]),
        "cordas2_sidecar": cordas2_epd_epsilon(),
        "part_d": {
            "item1_mean": item1_mean,
            "item2_pass": item2,
            "item34_score": item34,
            "item34_unexplained_mono": unexplained,
            "score": d_score,
            "n_corpora": len(JOBS),
        },
        "composite_r6": {
            "B1": b1,
            "B5": b5,
            "C1": c1,
            "C2": c2,
            "D": d_score,
            "mean": composite,
            "arithmetic": f"({b1}+{b5}+{c1}+{c2}+{d_score:.1f})/5",
        },
    }
    (OUT / "finish.json").write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: bundle[k] for k in ("same_commit", "same_profile_r6", "part_d", "composite_r6", "cello_predictions", "cordas2_sidecar")}, indent=2))


if __name__ == "__main__":
    main()
