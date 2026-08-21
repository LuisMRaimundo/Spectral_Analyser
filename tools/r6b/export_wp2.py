"""R6b WP2 — new-code exports of Iowa bass and cello pp/mf.

Execution only. Same profile as R6. Does not edit analysis modules or
``analyze_ewsd_balanced.py``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence, Tuple

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from run_manifest import AUDIO_SUFFIXES, MANIFEST_FILENAME
from tools.verify_corpus import verify_corpus

LOG_DIR = _REPO / "docs" / "validation" / "_r6b"
LOG_DIR.mkdir(parents=True, exist_ok=True)

BASS_ROOT = Path(r"D:\CORDAS_3\DOUBLE-BASS\IOWA_Cb_tratados")
CELLO_ROOT = Path(r"D:\CORDAS_3\CELLO\IOWA_Cello_Arco\CELLO")


def _audio_in(folder: Path) -> List[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        p
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_SUFFIXES
    )


def bass_jobs() -> List[Tuple[str, Path, Path, List[Path]]]:
    jobs: List[Tuple[str, Path, Path, List[Path]]] = []
    if not BASS_ROOT.is_dir():
        return jobs
    for leaf in sorted(BASS_ROOT.rglob("_Sustains_Stable")):
        if not leaf.is_dir():
            continue
        files = _audio_in(leaf)
        if not files:
            continue
        name = f"iowa_bass_{leaf.parent.name}"
        out = leaf / "analysis_results_v4.2.3"
        jobs.append((name, leaf, out, files))
    return jobs


def cello_jobs(dynamics: Sequence[str]) -> List[Tuple[str, Path, Path, List[Path]]]:
    jobs: List[Tuple[str, Path, Path, List[Path]]] = []
    for dyn in dynamics:
        root = CELLO_ROOT / f"IOWA_cello_arco_{dyn}"
        files: List[Path] = []
        if root.is_dir():
            for child in sorted(root.iterdir()):
                if not child.is_dir() or child.name.startswith("analysis_"):
                    continue
                files.extend(_audio_in(child / "_Sustains"))
        name = f"cello_{dyn}"
        out = root / "analysis_results_v4.2.3"
        jobs.append((name, root, out, files))
    return jobs


def _already_done(out: Path) -> bool:
    return (out / MANIFEST_FILENAME).is_file() and (
        out / "compiled_density_metrics_research.xlsx"
    ).is_file()


def _run_orchestrator(*, out: Path, files: Sequence[Path]) -> int:
    cmd = [
        sys.executable,
        str(_REPO / "run_orchestrator.py"),
        "--out",
        str(out),
        "--stages",
        "1,2,3",
        "--figures",
        "--fft-policy",
        "fixed",
        "--fixed-n-fft",
        "8192",
        "--fixed-hop-length",
        "1024",
        *[str(p) for p in files],
    ]
    print("RUN", name_preview(out), "n=", len(files), flush=True)
    return int(subprocess.run(cmd, cwd=str(_REPO)).returncode)


def name_preview(out: Path) -> str:
    return str(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=("bass", "cello_pp", "cello_mf", "cello", "all"), default="bass")
    args = ap.parse_args()

    jobs: List[Tuple[str, Path, Path, List[Path]]] = []
    if args.only in {"bass", "all"}:
        jobs.extend(bass_jobs())
    if args.only in {"cello_pp", "cello", "all"}:
        jobs.extend(cello_jobs(["pp"]))
    if args.only in {"cello_mf", "cello", "all"}:
        jobs.extend(cello_jobs(["mf"]))

    started = datetime.now(timezone.utc).isoformat()
    summary = {"started": started, "only": args.only, "jobs": []}
    status = 0
    for name, corpus, out, files in jobs:
        rec = {
            "name": name,
            "corpus": str(corpus),
            "out": str(out),
            "n_audio": len(files),
        }
        print(f"\n==== {name} n={len(files)} ====", flush=True)
        if not files:
            rec["status"] = "skip_empty"
            summary["jobs"].append(rec)
            status = 1
            continue
        if _already_done(out):
            rec["status"] = "already_done"
            ver = verify_corpus(out)
            rec["verify_ok"] = ver.get("ok")
            rec["verify_issues"] = ver.get("issues")
            summary["jobs"].append(rec)
            continue
        out.mkdir(parents=True, exist_ok=True)
        rc = _run_orchestrator(out=out, files=files)
        rec["orchestrator_rc"] = rc
        if rc != 0:
            rec["status"] = "orchestrator_fail"
            summary["jobs"].append(rec)
            status = 1
            break
        ver = verify_corpus(out)
        rec["verify_ok"] = ver.get("ok")
        rec["verify_issues"] = ver.get("issues")
        rec["status"] = "ok" if ver.get("ok") else "verify_fail"
        summary["jobs"].append(rec)
        if not ver.get("ok"):
            status = 1
            break

    summary["ended"] = datetime.now(timezone.utc).isoformat()
    dest = LOG_DIR / f"export_{args.only}.json"
    dest.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
