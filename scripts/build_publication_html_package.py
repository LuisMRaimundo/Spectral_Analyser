#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a publication-only copy of per-note spectrogram assets (PNG + cleaned Plotly HTML).

**All defaults stay under the repository root** (see ``--dest``). Pass ``--source``
pointing at an ``analysis_results`` tree (can be absolute on your machine when you
run locally; this script itself lives only in SoundSpectrAnalyse-main_6).

Does **not** modify the source ``analysis_results`` tree — copies only.

Usage (from repo root)::

    python scripts/build_publication_html_package.py --source path/to/analysis_results

Optional::

    python scripts/build_publication_html_package.py --source ... --dest publication_html_package
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

PNG_NAMES = (
    "spectrogram.png",
    "component_amplitude_mass_pie.png",
    "component_energy_ratio_pie.png",
)

# Post-clean verification: path-oriented patterns (avoid false positives such as
# the substring "desktop" inside unrelated minified JavaScript identifiers).
_SCAN_RES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("C:\\Users", re.compile(r"C:\\\\Users\\\\", re.I)),
    ("C:/Users", re.compile(r"C:/Users/", re.I)),
    ("lmr20", re.compile(r"lmr20", re.I)),
    ("teste_corpus_pequeno", re.compile(r"teste_corpus_pequeno", re.I)),
    ("file_url_triple_slash", re.compile(r"file:///+(?:[A-Za-z]:|%3[Aa])", re.I)),
    ("analysis_results_path", re.compile(r"[\\\\/]analysis_results[\\\\/]", re.I)),
    ("redacted_for_publication", re.compile(r"redacted_for_publication", re.I)),
    ("windows_desktop_folder", re.compile(r"[\\\\/]Desktop[\\\\/](?:Users|[^\\\\/]{1,120}[\\\\/])", re.I)),
)

_RE_FILE_URL = re.compile(
    r"file:///+(?:[A-Za-z]:|%3[Aa])(?:[/\\]|%2[Ff]|%5[Cc])[^\s\"'<>]{8,800}",
    re.IGNORECASE,
)
_RE_WIN_ABS = re.compile(
    r"(?:[A-Za-z]:)(?:\\|/|%(?:2[Ff]|5[Cc]))(?:Users|users)(?:\\|/|%(?:2[Ff]|5[Cc]))[^\s\"'<>]{4,400}",
    re.IGNORECASE,
)
_RE_ABS_POSIX_HOME = re.compile(
    r"/(?:Users|home|mnt)/[^\s\"'<>]{2,400}",
    re.IGNORECASE,
)


def scan_text_for_publication_leaks(text: str) -> list[str]:
    bad: list[str] = []
    for label, rx in _SCAN_RES:
        if rx.search(text):
            bad.append(label)
    return bad


def scan_bytes(data: bytes) -> list[str]:
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        text = str(data)
    return scan_text_for_publication_leaks(text)


def clean_html_bytes(raw: bytes, *, note_label: str) -> tuple[bytes, list[str]]:
    log: list[str] = []
    try:
        s = raw.decode("utf-8")
    except UnicodeDecodeError:
        s = raw.decode("utf-8", errors="replace")
        log.append("utf-8_decode_errors_replaced")

    before = s
    s = _RE_FILE_URL.sub("Spectrogram 3D", s)
    if s != before:
        log.append("replaced_file_url_tokens")
    before = s
    s = _RE_WIN_ABS.sub(note_label, s)
    if s != before:
        log.append("replaced_windows_absolute_paths")
    before = s
    s = _RE_ABS_POSIX_HOME.sub(note_label, s)
    if s != before:
        log.append("replaced_posix_home_style_paths")

    for token, repl in (
        ("teste_corpus_pequeno", "corpus"),
        ("dfgdf", ""),
        ("analysis_results", "output"),
    ):
        if token.lower() in s.lower():
            s = re.sub(re.escape(token), repl, s, flags=re.IGNORECASE)
            log.append(f"scrubbed_token:{token}")

    if "lmr20" in s.lower():
        s = re.sub(r"lmr20", "user", s, flags=re.IGNORECASE)
        log.append("scrubbed_username_token")

    neutral_title = f'"text":"Spectrogram 3D — {note_label}"'

    def _shorten_giant_text(m: re.Match[str]) -> str:
        inner = m.group(1)
        if len(inner) > 120 and ("\\" in inner or "/" in inner):
            return neutral_title
        return m.group(0)

    s2 = re.sub(r'"text"\s*:\s*"([^"]{200,20000})"', _shorten_giant_text, s)
    if s2 != s:
        s = s2
        log.append("shortened_oversized_json_text_fields")

    return s.encode("utf-8", errors="replace"), log


def main() -> int:
    ap = argparse.ArgumentParser(description="Copy per-note PNGs + cleaned spectrogram_3d HTML into a publication folder.")
    ap.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to an analysis_results directory (read-only).",
    )
    ap.add_argument(
        "--dest",
        type=Path,
        default=_ROOT / "publication_html_package",
        help=f"Output root (default: {_ROOT / 'publication_html_package'})",
    )
    args = ap.parse_args()
    source: Path = args.source.expanduser().resolve()
    dest: Path = args.dest.expanduser()
    if not dest.is_absolute():
        dest = (_ROOT / dest).resolve()
    else:
        dest = dest.resolve()

    if not source.is_dir():
        print(f"ERROR: --source is not a directory: {source}", file=sys.stderr)
        return 2

    try:
        dest.relative_to(_ROOT)
    except ValueError:
        print(
            f"ERROR: --dest must be inside the repository root:\n  {_ROOT}\n  got: {dest}",
            file=sys.stderr,
        )
        return 2

    dest.mkdir(parents=True, exist_ok=True)
    notes_root = dest / "notes"
    notes_root.mkdir(parents=True, exist_ok=True)

    html_found: list[str] = []
    html_cleaned: list[str] = []
    html_excluded: list[str] = []
    removals_summary: list[str] = []

    for outer in sorted(source.iterdir()):
        if not outer.is_dir():
            continue
        note_dir: Path | None = None
        inner_note: str | None = None
        for child in outer.iterdir():
            if child.is_dir():
                inner_note = child.name
                note_dir = child
                break
        if inner_note is None or note_dir is None:
            continue

        dest_dir = notes_root / inner_note
        dest_dir.mkdir(parents=True, exist_ok=True)

        for png in PNG_NAMES:
            src_png = note_dir / png
            if src_png.is_file():
                shutil.copy2(src_png, dest_dir / png)

        html_src = note_dir / "spectrogram_3d.html"
        html_found.append(str(html_src))
        if not html_src.is_file():
            html_excluded.append(f"{html_src} (missing)")
            continue

        raw = html_src.read_bytes()
        pre_bad = scan_bytes(raw)
        try:
            cleaned, logs = clean_html_bytes(raw, note_label=inner_note)
        except Exception as exc:  # noqa: BLE001
            html_excluded.append(f"{html_src} (clean_failed: {exc})")
            continue

        post_bad = scan_bytes(cleaned)
        if post_bad:
            html_excluded.append(f"{html_src} (still_contains_after_clean: {', '.join(post_bad)})")
            continue

        out_html = dest_dir / "spectrogram_3d_PUBLICATION.html"
        out_html.write_bytes(cleaned)
        html_cleaned.append(str(out_html))
        if pre_bad or logs:
            removals_summary.append(f"{html_src.name}@{inner_note}: pre={pre_bad or ['(none)']} actions={logs}")

    remaining: dict[str, list[str]] = {}
    for path in notes_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".py", ".pyc", ".md"}:
            continue
        hits = scan_bytes(path.read_bytes())
        if hits:
            remaining[str(path.relative_to(dest))] = hits

    rep_path = dest / "PUBLICATION_HTML_CLEANUP_REPORT.md"
    clean_flag = not remaining
    with rep_path.open("w", encoding="utf-8") as fh:
        fh.write("# Publication HTML cleanup report\n\n")
        fh.write("## Scope\n")
        fh.write(f"- **Source (read-only):** `{source}`\n")
        fh.write(f"- **Output:** `{dest}`\n")
        fh.write("- **Original analysis_results files:** not modified (copies only).\n\n")
        fh.write("## 1. HTML files found\n")
        for p in html_found:
            fh.write(f"- `{p}`\n")
        fh.write("\n## 2. HTML files cleaned (written)\n")
        for p in html_cleaned:
            fh.write(f"- `{p}`\n")
        fh.write("\n## 3. HTML files excluded\n")
        if not html_excluded:
            fh.write("- *(none)*\n")
        else:
            for p in html_excluded:
                fh.write(f"- {p}\n")
        fh.write("\n## 4. Local path strings removed (per file actions)\n")
        if not removals_summary:
            fh.write("- No high-risk substrings detected before cleaning, or only structural `file://` JS fragments.\n")
        else:
            for line in removals_summary:
                fh.write(f"- {line}\n")
        fh.write("\n## 5. Remaining risky strings after package scan (`notes/` only)\n")
        if not remaining:
            fh.write("- **None** — path-oriented regex scan passed.\n")
        else:
            for rel, hits in sorted(remaining.items()):
                fh.write(f"- `{rel}`: {', '.join(hits)}\n")
        fh.write(
            "\n## 5b. Naive `Desktop` substring\n"
            "- A literal search for `desktop` may still hit minified Plotly JS identifiers; "
            "the gate above uses path-style patterns only.\n"
        )
        fh.write("\n## 6. Original files confirmation\n")
        fh.write("- All work was copy-only into the `--dest` tree.\n")
        fh.write("- No writes were performed under `--source`.\n\n")
        fh.write("## 7. Publish HTML vs PNG-only\n")
        if clean_flag and len(html_cleaned) == len(html_found):
            fh.write(
                "- **Recommendation:** Cleaned HTML passed the scan; publish alongside PNGs. "
                "Keep PNGs as a fallback.\n"
            )
        else:
            fh.write("- **Recommendation:** Prefer PNG-only until every HTML passes the scan.\n")
        fh.write("\n---\nGenerated by `scripts/build_publication_html_package.py`.\n")

    print("Wrote", rep_path)
    print("publication_clean:", clean_flag)
    return 0 if clean_flag else 1


if __name__ == "__main__":
    raise SystemExit(main())
