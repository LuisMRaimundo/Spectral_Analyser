"""Agreement between listener pairwise density orderings and EWSD rank.

No listener data are collected here. The functions score a filled response
CSV against an EWSD series (Spearman ρ of implied ranks).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, Sequence

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def win_scores(responses: pd.DataFrame) -> pd.Series:
    """Count how often each note is chosen as denser."""
    scores: Dict[str, float] = {}
    for _, row in responses.iterrows():
        choice = str(row.get("denser_choice") or "").strip()
        a = str(row.get("note_a") or "").strip()
        b = str(row.get("note_b") or "").strip()
        if choice not in {a, b}:
            continue
        scores[choice] = scores.get(choice, 0.0) + 1.0
        other = b if choice == a else a
        scores.setdefault(other, 0.0)
    return pd.Series(scores, dtype=float)


def spearman_rank_agreement(
    listener_scores: pd.Series,
    ewsd_scores: pd.Series,
) -> float:
    """Spearman ρ between listener win-counts and EWSD scores (common notes)."""
    common = sorted(set(listener_scores.index) & set(ewsd_scores.index))
    if len(common) < 3:
        return float("nan")
    left = listener_scores.reindex(common).astype(float)
    right = ewsd_scores.reindex(common).astype(float)
    return float(left.rank().corr(right.rank(), method="spearman"))


def agreement_report(
    responses: pd.DataFrame,
    ewsd: pd.Series,
) -> dict:
    listener = win_scores(responses)
    rho = spearman_rank_agreement(listener, ewsd)
    return {
        "n_pairs_scored": int((responses["denser_choice"].astype(str).str.strip() != "").sum()),
        "n_notes": int(len(listener)),
        "spearman_rho": rho,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Score filled pairwise judgements against an EWSD series."
    )
    parser.add_argument("--responses", required=True, help="Filled response CSV.")
    parser.add_argument(
        "--ewsd",
        required=True,
        help="CSV with columns Note, EWSD_score_acoustic_balanced.",
    )
    args = parser.parse_args(argv)
    responses = pd.read_csv(args.responses)
    ewsd_df = pd.read_csv(args.ewsd)
    ewsd = pd.Series(
        pd.to_numeric(ewsd_df["EWSD_score_acoustic_balanced"], errors="coerce").values,
        index=ewsd_df["Note"].astype(str).str.strip(),
    )
    report = agreement_report(responses, ewsd)
    print(
        f"pairs={report['n_pairs_scored']} notes={report['n_notes']} "
        f"Spearman ρ={report['spearman_rho']}"
    )
    if report["spearman_rho"] != report["spearman_rho"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
