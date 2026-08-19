"""Export pairwise density-judgement lists. No listener data are collected.

The CSV schema is the response sheet for a later listening study. This
module only writes empty templates and a stimuli list from note IDs
(or from a Stage 3 series).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

RESPONSE_COLUMNS: tuple[str, ...] = (
    "pair_id",
    "note_a",
    "note_b",
    "listener_id",
    "session_id",
    "denser_choice",
    "confidence",
    "utc",
    "comment",
)
STIMULI_COLUMNS: tuple[str, ...] = (
    "note_id",
    "source_path",
    "ewsd_score_acoustic_balanced",
    "register",
    "dynamic",
)


def build_adjacent_pairs(notes: Sequence[str]) -> List[tuple[str, str]]:
    """Consecutive pairs in the given order, plus the first-vs-last pair."""
    clean = [str(n).strip() for n in notes if str(n).strip()]
    pairs = [(clean[i], clean[i + 1]) for i in range(len(clean) - 1)]
    if len(clean) >= 3:
        pairs.append((clean[0], clean[-1]))
    return pairs


def write_stimuli_list(
    rows: Iterable[dict],
    path: Path,
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(STIMULI_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in STIMULI_COLUMNS})
    return path


def write_response_template(
    pairs: Sequence[tuple[str, str]],
    path: Path,
    *,
    listener_id: str = "",
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(RESPONSE_COLUMNS))
        writer.writeheader()
        for i, (a, b) in enumerate(pairs, start=1):
            writer.writerow(
                {
                    "pair_id": f"P{i:03d}",
                    "note_a": a,
                    "note_b": b,
                    "listener_id": listener_id,
                    "session_id": "",
                    "denser_choice": "",
                    "confidence": "",
                    "utc": "",
                    "comment": "",
                }
            )
    return path


def notes_from_stage3(path: Path) -> List[dict]:
    df = pd.read_excel(path, sheet_name="Spectral_Density_Metrics")
    note_col = "Note" if "Note" in df.columns else df.columns[0]
    score_col = (
        "EWSD_score_acoustic_balanced"
        if "EWSD_score_acoustic_balanced" in df.columns
        else None
    )
    out: List[dict] = []
    for _, row in df.iterrows():
        out.append(
            {
                "note_id": str(row[note_col]).strip(),
                "source_path": "",
                "ewsd_score_acoustic_balanced": (
                    "" if score_col is None else row[score_col]
                ),
                "register": row.get("Register", ""),
                "dynamic": row.get("Dynamic", ""),
            }
        )
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write pairwise density-judgement templates (no data collection)."
    )
    parser.add_argument("--notes", nargs="*", help="Note IDs, in presentation order.")
    parser.add_argument("--stage3", type=str, help="Research workbook to take notes from.")
    parser.add_argument("--out-dir", default="perceptual_study", help="Output directory.")
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir)
    if args.stage3:
        rows = notes_from_stage3(Path(args.stage3))
        notes = [r["note_id"] for r in rows]
    else:
        notes = list(args.notes or [])
        rows = [{"note_id": n, "source_path": "", "ewsd_score_acoustic_balanced": "",
                 "register": "", "dynamic": ""} for n in notes]
    if len(notes) < 2:
        print("error: need at least two notes", file=sys.stderr)
        return 2
    write_stimuli_list(rows, out_dir / "stimuli_list.csv")
    write_response_template(build_adjacent_pairs(notes), out_dir / "response_template.csv")
    print(f"Wrote stimuli and response template under {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
