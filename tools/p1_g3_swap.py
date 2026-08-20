"""P1 — G3 window swap on the current tree (8192/1024 vs 4096/512).

Usage (repo root)::

    python -m tools.p1_g3_swap --out docs/validation/_p1_g3_swap
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from run_manifest import hash_file, load_run_manifest

G3 = Path(
    r"D:\METAIS\TROMBONE\IOWA_Trombone - Test\TenorTrombone"
    r"\IOWA_Trombone_ff\_Sustains_Stable\IOWA_Trb.T_ff.G3_SustainStable.aif"
)
WINDOWS = (
    ("g3_8192", 8192, 1024),
    ("g3_4096", 4096, 512),
)
KEYS = (
    "core_harmonic_energy_ratio",
    "core_residual_energy_ratio",
    "harmonic_energy_ratio",
    "residual_energy_ratio",
    "component_harmonic_energy_ratio",
    "harmonic_density_sum",
    "EWSD_score_acoustic_balanced",
    "harmonic_validated_count",
    "n_fft",
    "hop_length",
    "analysis_parameter_profile_id",
    "fft_policy",
)


def _git(cmd: list[str]) -> str:
    out = subprocess.run(
        ["git", *cmd],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    return (out.stdout or "").strip()


def _read_metrics(out_dir: Path) -> Dict[str, Any]:
    row: Dict[str, Any] = {}
    research = out_dir / "compiled_density_metrics_research.xlsx"
    compiled = out_dir / "compiled_density_metrics.xlsx"
    src = research if research.is_file() else compiled
    if src.is_file():
        for sheet in ("Spectral_Density_Metrics", "Density_Metrics"):
            try:
                df = pd.read_excel(src, sheet_name=sheet)
            except Exception:
                continue
            if df is None or df.empty:
                continue
            rec = df.iloc[0].to_dict()
            for key in KEYS:
                if key in rec and rec[key] is not None:
                    row[key] = rec[key]
            break
    wbs = list(out_dir.rglob("spectral_analysis.xlsx"))
    if wbs:
        try:
            meta = pd.read_excel(wbs[0], sheet_name="Metrics")
            if not meta.empty:
                rec = meta.iloc[0].to_dict()
                for key in KEYS:
                    if key not in row and key in rec:
                        row[key] = rec[key]
        except Exception:
            pass
        try:
            kv = pd.read_excel(wbs[0], sheet_name="Analysis_Metadata")
            if {"Parameter", "Value"}.issubset(set(kv.columns)):
                mapped = {
                    str(a).strip(): b
                    for a, b in zip(kv["Parameter"], kv["Value"])
                    if str(a).strip()
                }
                for key in KEYS:
                    if key not in row and key in mapped:
                        row[key] = mapped[key]
        except Exception:
            pass
    manifest = out_dir / "run_manifest.json"
    if manifest.is_file():
        payload = load_run_manifest(manifest)
        row["manifest_profile_id"] = payload.get("analysis_parameter_profile_id")
        row["manifest_fft_policy"] = payload.get("fft_policy")
        row["manifest_n_fft"] = payload.get("fixed_n_fft")
        row["manifest_hop"] = payload.get("fixed_hop_length")
        row["manifest_commit"] = payload.get("code_commit")
    return row


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
    metrics = _read_metrics(dest)
    metrics["exit_code"] = int(proc.returncode)
    metrics["n_fft_requested"] = n_fft
    metrics["hop_requested"] = hop
    return metrics


def _rel_delta(a: Any, b: Any) -> Optional[float]:
    try:
        fa = float(a)
        fb = float(b)
    except (TypeError, ValueError):
        return None
    den = max(abs(fa), 1e-9)
    return abs(fa - fb) / den


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="P1 G3 8192-vs-4096 swap")
    parser.add_argument(
        "--out",
        type=Path,
        default=_REPO / "docs" / "validation" / "_p1_g3_swap",
    )
    parser.add_argument("--audio", type=Path, default=G3)
    args = parser.parse_args(argv)
    audio = Path(args.audio)
    if not audio.is_file():
        print(f"missing audio: {audio}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    commit = _git(["rev-parse", "HEAD"])
    describe = _git(["describe", "--tags", "--always", "--dirty"])
    sha = hash_file(audio)
    payload: Dict[str, Any] = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "commit": commit,
        "git_describe": describe,
        "audio": str(audio),
        "audio_sha256": sha,
        "audio_bytes": int(audio.stat().st_size),
        "windows": {},
    }
    for tag, n_fft, hop in WINDOWS:
        payload["windows"][tag] = _run_one(audio, args.out / tag, n_fft, hop)
    a = payload["windows"]["g3_8192"]
    b = payload["windows"]["g3_4096"]
    core_delta = _rel_delta(
        a.get("core_harmonic_energy_ratio", a.get("harmonic_energy_ratio")),
        b.get("core_harmonic_energy_ratio", b.get("harmonic_energy_ratio")),
    )
    payload["core_h_rel_delta"] = core_delta
    payload["tolerance_3pct"] = (
        "pass" if core_delta is not None and core_delta <= 0.03 else "fail"
    )
    out_json = args.out / "p1_g3_swap.json"
    out_json.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str), flush=True)
    print(f"wrote {out_json}", flush=True)
    return 0 if payload["tolerance_3pct"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
