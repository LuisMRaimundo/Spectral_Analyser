"""Print WP1 census tables from the audit JSON."""

from __future__ import annotations

import json
from pathlib import Path


def _f(x, nd=3):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—"
    if v != v:
        return "—"
    return f"{v:.{nd}f}"


def main() -> None:
    data = json.loads(
        Path("docs/validation/_r6b/flute_b5b6_audit.json").read_text(encoding="utf-8")
    )
    for r in data:
        print(f"### {r['dynamic']} {r['note']}")
        print()
        print("| n | f (Hz) | A | SNR (dB) | gate (`candidate_status`) | include | exclusion |")
        print("|--:|-------:|--:|---------:|---------------------------|:-------:|-----------|")
        for h in r["census_H"]:
            print(
                f"| {h.get('order')} | {_f(h.get('freq_hz'))} | {_f(h.get('amp'), 4)} | "
                f"{_f(h.get('snr_db'), 2)} | {h.get('candidate_status')} | "
                f"{h.get('include_for_density')} | {h.get('exclusion_reason') or ''} |"
            )
        print()
        print("| f (Hz) | A | I status / gate | confirmation fail |")
        print("|-------:|--:|-----------------|-------------------|")
        for i in r["census_I"]:
            print(
                f"| {_f(i.get('freq_hz'))} | {_f(i.get('amp'), 4)} | "
                f"{i.get('inharmonic_status')} | {i.get('confirmation_failing_test')} |"
            )
        print()
        print("| f (Hz) | A | membership / gate | acoustic status |")
        print("|-------:|--:|-------------------|-----------------|")
        for s in r.get("census_S") or []:
            print(
                f"| {_f(s.get('freq_hz'))} | {_f(s.get('amp'), 4)} | "
                f"{s.get('membership')} | {s.get('acoustic_status')} |"
            )
        print()
        print(
            f"S listed {r['census_S_n_listed']}; members {r['n_S_member']} "
            f"(`{r['subbass_policy']}`, excluded {r['subbass_excluded']})."
        )
        print()


if __name__ == "__main__":
    main()
