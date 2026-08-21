"""Place new v4.2.3 workbooks where the unchanged CORDAS script can see them.

Does not edit ``D:\\CORDAS_2\\reports\\analyze_ewsd_balanced.py``.
Old Iowa-bass / Iowa-cello ``analysis_results/compiled_*.xlsx`` files are
temporarily renamed so the script's rglob does not double-count.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

_REPO = Path(__file__).resolve().parents[2]
SCRIPT = Path(r"D:\CORDAS_2\reports\analyze_ewsd_balanced.py")
C2_BASS = Path(r"D:\CORDAS_2\IOWA\DOUBLE-BASS\IOWA_Cb_tratados")
C3_BASS = Path(r"D:\CORDAS_3\DOUBLE-BASS\IOWA_Cb_tratados")
C2_CELLO = Path(r"D:\CORDAS_2\IOWA\CELLO\IOWA_Cello_Arco\CELLO")
C3_CELLO = Path(r"D:\CORDAS_3\CELLO\IOWA_Cello_Arco\CELLO")
BAK_SUFFIX = ".r6b_hidden"


def _epsilon_sq(H: float, k: int, n: int) -> float:
    if n <= k or k < 2:
        return float("nan")
    return float(max(0.0, (H - k + 1.0) / (n - k)))


def hide_old_compiled(root: Path) -> list[Path]:
    hidden: list[Path] = []
    for p in root.rglob("analysis_results/compiled_density_metrics_research.xlsx"):
        dest = p.with_name(p.name + BAK_SUFFIX)
        if dest.exists():
            continue
        p.rename(dest)
        hidden.append(dest)
    return hidden


def restore_hidden(hidden: list[Path]) -> None:
    for dest in hidden:
        orig = dest.with_name(dest.name[: -len(BAK_SUFFIX)])
        if dest.exists() and not orig.exists():
            dest.rename(orig)


def copy_new_into(src_root: Path, dest_root: Path) -> list[Path]:
    copied: list[Path] = []
    for src in src_root.rglob("analysis_results_v4.2.3/compiled_density_metrics_research.xlsx"):
        rel = src.relative_to(src_root)
        dest = dest_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        man = src.parent / "run_manifest.json"
        if man.is_file():
            shutil.copy2(man, dest.parent / "run_manifest.json")
        copied.append(dest)
    return copied


def _spearman_from_script_csv(instrument: str) -> dict:
    csv = Path(r"D:\CORDAS_2\reports\ewsd_balanced_note_rows.csv")
    out = {"csv": str(csv), "exists": csv.is_file(), "instrument": instrument}
    if not csv.is_file():
        return out
    df = pd.read_csv(csv)
    sub = df[
        (df["instrument"] == instrument)
        & (df["collection"] == "IOWA")
        & df["eligible"].astype(str).str.lower().isin(("true", "1"))
    ].copy()
    sub["ewsd"] = pd.to_numeric(sub["ewsd"], errors="coerce")
    sub["midi"] = pd.to_numeric(sub["midi"], errors="coerce")
    sub = sub.dropna(subset=["midi", "ewsd"])
    if len(sub) < 8:
        out["n"] = int(len(sub))
        return out
    rho, p = stats.spearmanr(sub["midi"], sub["ewsd"])
    out.update({"n": int(len(sub)), "rho_ewsd": float(rho), "p_ewsd": float(p)})
    return out


def _load_new_instrument(root: Path) -> pd.DataFrame:
    frames = []
    for fp in root.rglob("analysis_results_v4.2.3/compiled_density_metrics_research.xlsx"):
        df = pd.read_excel(fp, sheet_name="Spectral_Density_Metrics")
        df["_workbook"] = str(fp)
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _elig(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    elig = df.get("ewsd_primary_analysis_eligible")
    if elig is None:
        return df
    if elig.dtype == object:
        ok = elig.astype(str).str.lower().isin(("true", "1", "yes"))
    else:
        ok = elig.fillna(False).astype(bool)
    return df[ok].copy()


def sidecar_rho(df: pd.DataFrame) -> dict:
    df = _elig(df)
    if df.empty:
        return {"n": 0}
    midi = pd.to_numeric(df["MIDI"], errors="coerce")
    ewsd = pd.to_numeric(df["EWSD_score_acoustic_balanced"], errors="coerce")
    epd = pd.to_numeric(df["note_effective_component_density"], errors="coerce")
    m = midi.notna() & ewsd.notna()
    rho_e, p_e = stats.spearmanr(midi[m], ewsd[m])
    m2 = midi.notna() & epd.notna()
    rho_p, p_p = stats.spearmanr(midi[m2], epd[m2])
    return {
        "n_ewsd": int(m.sum()),
        "rho_ewsd": float(rho_e),
        "p_ewsd": float(p_e),
        "n_epd": int(m2.sum()),
        "rho_epd": float(rho_p),
        "p_epd": float(p_p),
    }


def sidecar_dynamic_eps2(df: pd.DataFrame) -> dict:
    df = _elig(df)
    if df.empty or "Dynamic" not in df.columns:
        return {"ok": False}
    out = {}
    for col, key in (
        ("EWSD_score_acoustic_balanced", "ewsd"),
        ("note_effective_component_density", "epd"),
    ):
        groups = {}
        for d, g in df.groupby(df["Dynamic"].astype(str).str.lower()):
            x = pd.to_numeric(g[col], errors="coerce").dropna().to_numpy()
            if len(x) >= 3:
                groups[d] = x
        if len(groups) < 2:
            out[key] = {"ok": False, "groups": {k: len(v) for k, v in groups.items()}}
            continue
        H, p = stats.kruskal(*groups.values())
        n = int(sum(len(v) for v in groups.values()))
        k = len(groups)
        out[key] = {
            "ok": True,
            "H": float(H),
            "p": float(p),
            "k": k,
            "n": n,
            "epsilon_sq": _epsilon_sq(float(H), k, n),
            "groups": {k: int(len(v)) for k, v in groups.items()},
        }
    return out


def main() -> int:
    if not SCRIPT.is_file():
        print("missing unchanged script", SCRIPT)
        return 1
    copied = []
    copied.extend(copy_new_into(C3_BASS, C2_BASS))
    copied.extend(copy_new_into(C3_CELLO, C2_CELLO))
    hidden = []
    hidden.extend(hide_old_compiled(C2_BASS))
    hidden.extend(hide_old_compiled(C2_CELLO))
    print("copied", len(copied), "hidden_old", len(hidden), flush=True)
    try:
        rc = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(SCRIPT.parent)).returncode
        script_json = Path(r"D:\CORDAS_2\reports\ewsd_balanced_analysis.json")
        script_dyn = {}
        if script_json.is_file():
            payload = json.loads(script_json.read_text(encoding="utf-8"))
            script_dyn = (payload.get("tests") or {}).get("dynamic") or {}
            midi = payload.get("midi_spearman") or []
        else:
            midi = []
    finally:
        restore_hidden(hidden)
        print("restored", len(hidden), flush=True)

    bass = _load_new_instrument(C3_BASS)
    cello = _load_new_instrument(C3_CELLO)
    result = {
        "script_rc": rc,
        "copied_n": len(copied),
        "script_dynamic_ewsd": script_dyn,
        "script_midi_spearman": midi,
        "script_iowa_bass": _spearman_from_script_csv("Double bass"),
        "script_iowa_cello": _spearman_from_script_csv("Cello"),
        "sidecar_bass": sidecar_rho(bass),
        "sidecar_cello": sidecar_rho(cello),
        "sidecar_cello_dynamic_eps2": sidecar_dynamic_eps2(cello),
    }
    dest = _REPO / "docs" / "validation" / "_r6b" / "cordas_new_trees.json"
    dest.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
