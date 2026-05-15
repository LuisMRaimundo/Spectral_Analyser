"""Replace UTF-8-as-Latin-1 mojibake digraphs with correct characters (Portuguese)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_CORRECT = (
    "áàâãäåæçéêëìíîïðñòóôõöøùúûüýþÿ"
    "ÁÀÂÃÄÅÆÇÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞß"
)
WRONG_TO_CORRECT: dict[str, str] = {}
for ch in _CORRECT:
    wrong = ch.encode("utf-8").decode("latin-1")
    WRONG_TO_CORRECT[wrong] = ch


def fix_text(text: str) -> str:
    keys = sorted(WRONG_TO_CORRECT.keys(), key=len, reverse=True)
    out = text
    for w in keys:
        out = out.replace(w, WRONG_TO_CORRECT[w])
    return out


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        paths = [(ROOT / p).resolve() if not Path(p).is_absolute() else Path(p) for p in argv[1:]]
    else:
        paths = list(ROOT.rglob("*.py"))
    changed = 0
    for path in paths:
        if "fix_mojibake" in path.name:
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if "Ã" not in raw and "Â" not in raw:
            continue
        fixed = fix_text(raw)
        if fixed != raw:
            path.write_text(fixed, encoding="utf-8", newline="\n")
            print("fixed", path.relative_to(ROOT))
            changed += 1
    print("files_updated", changed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
