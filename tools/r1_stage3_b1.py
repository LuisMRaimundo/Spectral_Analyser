"""R1 — B1 resolution test on the canonical Stage-1→3 path.

Reads ``EWSD_score_acoustic_balanced``, ``core_harmonic_energy_ratio``,
and ``effective_partial_density`` from the compiled Stage-3 research
workbook only. Does not fall back to Stage-1 Metrics or in-memory
diagnostics.

Usage (repo root)::

    python -m tools.r1_stage3_b1
    python -m tools.r1_stage3_b1 --out docs/validation/_r1_stage3_b1
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from run_manifest import hash_file

KEYS = (
    "EWSD_score_acoustic_balanced",
    "core_harmonic_energy_ratio",
    "effective_partial_density",
)
NFFTS = (4096, 8192, 16384)
TOL = 0.03

G3 = Path(
    r"D:\METAIS\TROMBONE\IOWA_Trombone - Test\TenorTrombone"
    r"\IOWA_Trombone_ff\_Sustains_Stable\IOWA_Trb.T_ff.G3_SustainStable.aif"
)
_FLUTE_DIR = Path(
    r"D:\METAIS\TROMBONE\IOWA-flute - test\IOWA_Flute_ff\_Sustains_Stable"
)
FLUTE = Path(_FLUTE_DIR / "IOWA_Fl.ff.C5_SustainStable.aif")
if not FLUTE.is_file() and _FLUTE_DIR.is_dir():
    _cands = sorted(_FLUTE_DIR.glob("*.aif"))
    FLUTE = _cands[0] if _cands else FLUTE


def _git(args: List[str]) -> str:
    r = subprocess.run(
        ["git", *args], cwd=str(_REPO), capture_output=True, text=True, check=False
    )
    return (r.stdout or "").strip()


def write_synth_wav(path: Path, *, f0: float = 220.0, sec: float = 1.2) -> Path:
    import soundfile as sf

    sr = 44100
    t = np.arange(int(sr * sec)) / float(sr)
    y = np.zeros_like(t)
    for n in range(1, 9):
        y += (0.5 ** (n - 1)) * np.sin(2.0 * np.pi * n * f0 * t)
    peak = float(np.max(np.abs(y))) or 1.0
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), (y / peak).astype(np.float64), sr)
    return path


def read_stage3_compiled(out_dir: Path) -> Dict[str, float]:
    """Read the three B1 keys from the Stage-3 research workbook only."""
    research = out_dir / "compiled_density_metrics_research.xlsx"
    if not research.is_file():
        raise FileNotFoundError(f"missing Stage-3 research workbook: {research}")
    df = pd.read_excel(research, sheet_name="Spectral_Density_Metrics")
    if df is None or df.empty:
        raise ValueError(f"empty Spectral_Density_Metrics in {research}")
    rec = df.iloc[0].to_dict()
    out: Dict[str, float] = {}
    missing = []
    for key in KEYS:
        if key not in rec or rec[key] is None:
            missing.append(key)
            continue
        try:
            out[key] = float(rec[key])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key} not numeric in {research}") from exc
    if missing:
        raise KeyError(f"Stage-3 sheet missing {missing} in {research}")
    return out


def _rel_spread(values: Sequence[float], ref: float, tol: float) -> bool:
    if not np.isfinite(ref) or abs(ref) < 1e-12:
        return all(abs(v) < tol for v in values if np.isfinite(v))
    return all(abs(v - ref) / abs(ref) <= tol for v in values if np.isfinite(v))


def _run_one(audio: Path, dest: Path, n_fft: int, hop: int) -> Dict[str, Any]:
    dest.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(_REPO / "run_orchestrator.py"),
        str(audio),
        "--out",
        str(dest),
        "--stages",
        "1,2,3",
        "--fft-policy",
        "fixed",
        "--fixed-n-fft",
        str(n_fft),
        "--fixed-hop-length",
        str(hop),
        "--weight-function",
        "log",
    ]
    print(" ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(_REPO), check=False)
    row: Dict[str, Any] = {
        "exit_code": int(proc.returncode),
        "n_fft": n_fft,
        "hop": hop,
        "source": "compiled_density_metrics_research.xlsx:Spectral_Density_Metrics",
    }
    if proc.returncode != 0:
        row["error"] = f"orchestrator exit {proc.returncode}"
        return row
    try:
        row.update(read_stage3_compiled(dest))
    except Exception as exc:
        row["error"] = str(exc)
    return row


def evaluate_signal(name: str, audio: Path, dest: Path) -> Dict[str, Any]:
    rows: Dict[str, Any] = {}
    for n_fft in NFFTS:
        hop = max(1, n_fft // 8)
        rows[str(n_fft)] = _run_one(audio, dest / f"{name}_{n_fft}", n_fft, hop)
    ref = rows[str(8192)]
    ok = True
    spreads: Dict[str, Dict[str, Any]] = {}
    for key in KEYS:
        vals = [rows[str(n)].get(key, float("nan")) for n in NFFTS]
        ref_v = ref.get(key, float("nan"))
        try:
            nums = [float(v) for v in vals]
            ref_f = float(ref_v)
        except (TypeError, ValueError):
            ok = False
            spreads[key] = {"values": vals, "pass": False, "reason": "not numeric"}
            continue
        passed = _rel_spread(nums, ref_f, TOL) and all(np.isfinite(nums))
        ok = ok and passed
        spreads[key] = {
            "values": {str(n): rows[str(n)].get(key) for n in NFFTS},
            "pass": passed,
        }
    return {
        "name": name,
        "audio": str(audio),
        "audio_sha256": hash_file(audio) if audio.is_file() else None,
        "pass": ok,
        "rows": rows,
        "spreads": spreads,
    }


def run_b1(out: Path) -> Dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    synth = write_synth_wav(out / "synth_a4.wav")
    signals: List[Tuple[str, Path]] = [("synthetic", synth)]
    if G3.is_file():
        signals.append(("g3", G3))
    if FLUTE.is_file():
        signals.append(("flute", FLUTE))
    results = []
    for name, path in signals:
        results.append(evaluate_signal(name, path, out))
    payload: Dict[str, Any] = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "commit": _git(["rev-parse", "HEAD"]),
        "git_describe": _git(["describe", "--tags", "--always", "--dirty"]),
        "tag": _git(["describe", "--tags", "--exact-match", "HEAD"]) or None,
        "tolerance": TOL,
        "source": "Stage-3 compiled_density_metrics_research.xlsx Spectral_Density_Metrics",
        "signals": [s[0] for s in signals],
        "results": results,
        "pass": bool(results) and all(r["pass"] for r in results),
    }
    (out / "r1_stage3_b1.json").write_text(
        json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="R1 Stage-3 B1 resolution test")
    p.add_argument(
        "--out",
        type=Path,
        default=_REPO / "docs" / "validation" / "_r1_stage3_b1",
    )
    args = p.parse_args(argv)
    payload = run_b1(args.out)
    print(json.dumps(payload, indent=2, default=str), flush=True)
    print("PASS" if payload["pass"] else "FAIL", flush=True)
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
