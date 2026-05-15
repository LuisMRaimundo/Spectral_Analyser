#!/usr/bin/env python3
"""
Scan exported artefacts for forbidden local path text (publication / Zenodo gate).

Usage:
    python scripts/check_publication_paths.py <file_or_folder>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from metadata_sanitizer import (  # noqa: E402
    list_publication_path_violations_in_excel,
    string_fails_publication_scan,
)


def _scan_text_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [f"{path}: read error {e}"]
    if string_fails_publication_scan(text):
        return [f"{path.name}: forbidden path pattern in text"]
    return []


def _scan_json_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [f"{path}: read error {e}"]
    if string_fails_publication_scan(text):
        return [f"{path.name}: forbidden path pattern in JSON text"]
    try:
        obj = json.loads(text)
    except Exception:
        return []
    if string_fails_publication_scan(json.dumps(obj, default=str)):
        return [f"{path.name}: forbidden path pattern after JSON parse"]
    return []


_SCAN_EXTS = {".xlsx", ".json", ".txt", ".csv", ".html", ".md"}


def _scan_file(p: Path) -> tuple[str, bool, str]:
    suf = p.suffix.lower()
    if suf == ".xlsx":
        bad = list_publication_path_violations_in_excel(p)
        return (str(p), not bad, "; ".join(bad) if bad else "")
    if suf == ".json":
        bad = _scan_json_file(p)
        return (str(p), not bad, "; ".join(bad) if bad else "")
    if suf in (".txt", ".csv", ".html", ".md"):
        bad = _scan_text_file(p)
        return (str(p), not bad, "; ".join(bad) if bad else "")
    return (str(p), True, "skipped (extension not scanned)")


def _iter_scan_targets(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name.startswith("."):
            continue
        if p.suffix.lower() in _SCAN_EXTS:
            out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Publication path scan (no C:\\Users\\… in exports).")
    ap.add_argument("target", type=Path, help="File or directory to scan")
    args = ap.parse_args()
    target = args.target.resolve()
    print(f"=== Publication path scan ===\nTarget: {target}\n")

    if not target.exists():
        print(f"[FAIL] {target} — missing")
        print("\nSummary: FAIL (1 file)")
        return 1

    rows: list[tuple[str, bool, str]] = []
    if target.is_file():
        rows.append(_scan_file(target))
    else:
        files = _iter_scan_targets(target)
        if not files:
            print("(no scannable files under this folder)")
            print("\nSummary: PASS (0 files)")
            return 0
        for p in files:
            rows.append(_scan_file(p))

    n_fail = 0
    for path, ok, detail in rows:
        tag = "PASS" if ok else "FAIL"
        if not ok:
            n_fail += 1
        tail = f" — {detail}" if detail else ""
        print(f"[{tag}] {path}{tail}")

    print(f"\nSummary: {'PASS' if n_fail == 0 else 'FAIL'} — {len(rows)} file(s), {n_fail} failure(s).")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
