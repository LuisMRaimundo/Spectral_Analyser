"""R6 — sequential runbook re-exports (execution, not a formula change)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence, Tuple

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from run_manifest import AUDIO_SUFFIXES, MANIFEST_FILENAME
from tools.verify_corpus import verify_corpus

LOG_DIR = _REPO / "docs" / "validation" / "_r6_reexport"
LOG_DIR.mkdir(parents=True, exist_ok=True)

TromboneRoot = Path(r"D:\METAIS\TROMBONE\IOWA_Trombone\TenorTrombone")
FluteRoot = Path(r"D:\MADEIRAS\FLAUTA\IOWA_flute")
CelloFf = Path(r"D:\CORDAS_3\CELLO\IOWA_Cello_Arco\CELLO\IOWA_cello_arco_ff")

FOLDER_CORPORA: List[Tuple[str, Path, Path]] = [
    (
        "trombone_pp",
        TromboneRoot / "IOWA_Trombone_pp" / "_Sustains",
        TromboneRoot / "IOWA_Trombone_pp" / "_Sustains" / "analysis_results_v4.2.3",
    ),
    (
        "trombone_mf",
        TromboneRoot / "IOWA_Trombone_mf" / "_Sustains",
        TromboneRoot / "IOWA_Trombone_mf" / "_Sustains" / "analysis_results_v4.2.3",
    ),
    (
        "trombone_ff",
        TromboneRoot / "IOWA_Trombone_ff" / "_Sustains",
        TromboneRoot / "IOWA_Trombone_ff" / "_Sustains" / "analysis_results_v4.2.3",
    ),
    (
        "flute_pp",
        FluteRoot / "IOWA_Flute_pp" / "_Sustains",
        FluteRoot / "IOWA_Flute_pp" / "_Sustains" / "analysis_results_v4.2.3",
    ),
    (
        "flute_mf",
        FluteRoot / "IOWA_Flute_mf" / "_Sustains",
        FluteRoot / "IOWA_Flute_mf" / "_Sustains" / "analysis_results_v4.2.3",
    ),
    (
        "flute_ff",
        FluteRoot / "IOWA_Flute_ff" / "_Sustains",
        FluteRoot / "IOWA_Flute_ff" / "_Sustains" / "analysis_results_v4.2.3",
    ),
]


def _audio_in(folder: Path) -> List[Path]:
    return sorted(
        p
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_SUFFIXES
    )


def cello_ff_sustains() -> List[Path]:
    files: List[Path] = []
    if not CelloFf.is_dir():
        return files
    for child in sorted(CelloFf.iterdir()):
        if not child.is_dir():
            continue
        sust = child / "_Sustains"
        if sust.is_dir():
            files.extend(_audio_in(sust))
    return files


def _already_done(out: Path) -> bool:
    man = out / MANIFEST_FILENAME
    xlsx = out / "compiled_density_metrics_research.xlsx"
    return man.is_file() and xlsx.is_file()


def _run_orchestrator(*, out: Path, corpus: Path | None, files: Sequence[Path]) -> int:
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
    ]
    if corpus is not None:
        cmd.extend(["--corpus", str(corpus)])
    else:
        cmd.extend(str(p) for p in files)
    log = LOG_DIR / f"{out.name}_{datetime.now().strftime('%H%M%S')}.log"
    # Prefer a stable per-corpus log name via caller.
    print("RUN", " ".join(cmd[:8]), "...", flush=True)
    proc = subprocess.run(cmd, cwd=str(_REPO))
    return int(proc.returncode)


def _verify(out: Path) -> dict:
    result = verify_corpus(out)
    (LOG_DIR / f"verify_{out.parent.name}.json").write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8"
    )
    return result


def main() -> int:
    started = datetime.now(timezone.utc).isoformat()
    summary = {"started": started, "jobs": []}
    jobs: List[Tuple[str, Path | None, Path, List[Path]]] = []
    for name, corpus, out in FOLDER_CORPORA:
        jobs.append((name, corpus, out, []))
    cello_files = cello_ff_sustains()
    jobs.append(
        (
            "cello_ff",
            None,
            CelloFf / "analysis_results_v4.2.3",
            cello_files,
        )
    )

    status = 0
    for name, corpus, out, files in jobs:
        rec = {"name": name, "out": str(out), "n_audio": None}
        if corpus is not None:
            rec["n_audio"] = len(_audio_in(corpus))
            rec["corpus"] = str(corpus)
        else:
            rec["n_audio"] = len(files)
            rec["corpus"] = "cello_ff _Sustains leaves"
        print(f"\n==== {name} n={rec['n_audio']} ====", flush=True)
        if rec["n_audio"] == 0:
            rec["status"] = "skip_empty"
            summary["jobs"].append(rec)
            status = 1
            continue
        if _already_done(out):
            rec["status"] = "already_done"
            ver = _verify(out)
            rec["verify_ok"] = ver.get("ok")
            summary["jobs"].append(rec)
            continue
        out.mkdir(parents=True, exist_ok=True)
        rc = _run_orchestrator(out=out, corpus=corpus, files=files)
        rec["orchestrator_rc"] = rc
        if rc != 0:
            rec["status"] = "orchestrator_fail"
            summary["jobs"].append(rec)
            status = 1
            break
        ver = _verify(out)
        rec["verify_ok"] = ver.get("ok")
        rec["verify_issues"] = ver.get("issues")
        rec["status"] = "ok" if ver.get("ok") else "verify_fail"
        summary["jobs"].append(rec)
        if not ver.get("ok"):
            status = 1
            break

    summary["ended"] = datetime.now(timezone.utc).isoformat()
    (LOG_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
