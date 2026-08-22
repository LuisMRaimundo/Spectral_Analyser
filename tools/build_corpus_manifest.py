#!/usr/bin/env python3
"""Walk a corpus root and emit a JSON manifest for later verification.

Reuses ``tools.ewsd_core.file_sha256`` (the same checksum the pipeline
already stores as ``source_sha256``). Moving the corpus to a versioned
location is a separate manual step.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from tools.ewsd_core import file_sha256

AUDIO_SUFFIXES = {".wav", ".flac", ".aiff", ".aif", ".mp3", ".ogg"}


def _audio_info(path: Path) -> dict:
    row = {
        "relative_path": "",
        "source_sha256": file_sha256(path),
        "duration_s": None,
        "sample_rate_hz": None,
        "channels": None,
    }
    try:
        import soundfile as sf

        info = sf.info(str(path))
        row["duration_s"] = float(info.duration)
        row["sample_rate_hz"] = int(info.samplerate)
        row["channels"] = int(info.channels)
    except Exception:
        pass
    return row


def build_manifest(corpus_root: Path) -> dict:
    root = corpus_root.expanduser().resolve()
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in AUDIO_SUFFIXES:
            continue
        row = _audio_info(path)
        row["relative_path"] = path.relative_to(root).as_posix()
        files.append(row)
    return {
        "corpus_root": str(root),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "n_files": len(files),
        "files": files,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "corpus_root",
        nargs="?",
        default=os.environ.get("EWSD_CORPUS_AUDIO")
        or os.environ.get("ACD_REAL_NOTE_AUDIO")
        or r"C:\Users\lmr20\Desktop\ORC_Vlc_arco_mf\_Sustains",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="docs/validation/corpus_manifest.json",
    )
    args = parser.parse_args()
    root = Path(args.corpus_root)
    if not root.exists():
        raise SystemExit(f"corpus root not found: {root}")
    payload = build_manifest(root)
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {dest} ({payload['n_files']} files)")


if __name__ == "__main__":
    main()
