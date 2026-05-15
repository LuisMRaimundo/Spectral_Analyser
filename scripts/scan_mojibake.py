#!/usr/bin/env python3
"""Scan Python sources for UTF-8-read-as-Latin-1 mojibake (Phase 7).

Flags only lines where UTF-8 multibyte sequences were split into separate
Unicode codepoints (U+00C3/U+00C2 followed by U+0080–U+00BF), which never
occurs in correctly decoded UTF-8 Portuguese text for those pairs.
Also flags common smart-quote / dash mojibake literals.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_FILES = frozenset()

LATIN1_UTF8_DIGRAPH = re.compile(r"[\u00c3\u00c2][\u0080-\u00bf]")
SMART_MOJIBAKE = ("â€™", "â€œ", "â€”", "â€“", "â€¦", "â€˜", "â€")


def main(argv: list[str]) -> int:
    bad: list[tuple[Path, int, str]] = []
    for path in sorted(ROOT.rglob("*.py")):
        if path.name == "scan_mojibake.py":
            continue
        try:
            rel = path.relative_to(ROOT)
        except ValueError:
            continue
        if rel in SKIP_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if LATIN1_UTF8_DIGRAPH.search(line) or any(s in line for s in SMART_MOJIBAKE):
                bad.append((path.relative_to(ROOT), i, line.strip()[:200]))
    if bad:
        for p, ln, snippet in bad[:200]:
            print(f"{p}:{ln}: {snippet}")
        print(f"TOTAL {len(bad)} suspicious lines (showing up to 200)")
        return 1
    print("OK: no mojibake marker patterns found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
