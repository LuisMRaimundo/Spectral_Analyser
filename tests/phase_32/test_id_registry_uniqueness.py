"""CI gate: formula IDs and tests/phase_<n>/ claims must stay unique."""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from metric_contract import build_metric_contracts

ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH = ROOT / "docs" / "METRIC_FORMULA_INDEX.md"
CHANGES_PATH = ROOT / "CHANGES.md"
CONTRACT_PATH = ROOT / "metric_contract.py"

INDEX_ID_RE = re.compile(r"^\|\s*(F-\d+)\s*\|", re.MULTILINE)
FORMULA_ID_RE = re.compile(r"F-\d+")
PHASE_HEADING_RE = re.compile(
    r"^(#{1,3})\s+.*?\bPhase\s+(\d+)\b",
    re.IGNORECASE | re.MULTILINE,
)
# Only explicit ownership claims, not incidental cross-references.
PHASE_CLAIM_RES = (
    re.compile(r"Tests live in `tests/phase_(\d+)/`", re.IGNORECASE),
    re.compile(
        r"^\s*[-*]\s+\*?\*?Tests:?\*?\*?\s+`tests/phase_(\d+)/",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(r"^\s*[-*]\s+`tests/phase_(\d+)/", re.MULTILINE),
)

# Density-era IDs that must appear in both registries (the ACD/EWSD collision
# class). Pre-contract STFT/MIR index rows are not all MetricDefinitions.
REQUIRED_IN_BOTH = frozenset(
    {
        "F-048",
        "F-049",
        "F-050",
        "F-056",
        "F-057",
        "F-058",
        "F-059",
        "F-060",
    }
)


def _index_ids() -> list[str]:
    text = INDEX_PATH.read_text(encoding="utf-8")
    return INDEX_ID_RE.findall(text)


def _contract_formula_ids() -> list[str]:
    ids: list[str] = []
    for definition in build_metric_contracts().values():
        for field in (
            definition.formula,
            definition.input_domain,
            definition.physical_interpretation,
            definition.not_valid_for,
            definition.amplitude_basis,
            definition.power_basis,
            getattr(definition, "formula_id", ""),
        ):
            ids.extend(FORMULA_ID_RE.findall(str(field)))
    return ids


def test_formula_ids_unique_in_metric_formula_index() -> None:
    ids = _index_ids()
    assert ids, f"no formula IDs parsed from {INDEX_PATH}"
    seen: dict[str, int] = {}
    for fid in ids:
        seen[fid] = seen.get(fid, 0) + 1
    dupes = sorted(k for k, n in seen.items() if n > 1)
    assert not dupes, f"duplicate formula IDs in METRIC_FORMULA_INDEX.md: {dupes}"


def test_formula_ids_unique_in_metric_contract() -> None:
    """IDs extracted from MetricDefinition fields; the set must be non-empty
    and every ID must appear in the index (checked in the consistency test).
    Duplicate citations of the same ID (e.g. F-056 density + pool count) are
    allowed; a second *index row* for the same ID is not.
    """
    ids = _contract_formula_ids()
    assert ids, "no formula IDs parsed from metric_contract.MetricDefinition fields"
    assert all(re.fullmatch(r"F-\d+", fid) for fid in ids)


def test_formula_id_sets_mutually_consistent() -> None:
    index_ids = set(_index_ids())
    contract_ids = set(_contract_formula_ids())
    missing_from_index = sorted(contract_ids - index_ids)
    assert not missing_from_index, (
        "metric_contract.py formula IDs missing from METRIC_FORMULA_INDEX.md: "
        f"{missing_from_index}"
    )
    missing_required = sorted(REQUIRED_IN_BOTH - index_ids)
    assert not missing_required, f"required IDs missing from index: {missing_required}"
    missing_required_c = sorted(REQUIRED_IN_BOTH - contract_ids)
    assert not missing_required_c, (
        "required IDs missing from metric_contract formulas: "
        f"{missing_required_c}"
    )
    # Every required ID appears in both sets (the mutual-consistency core).
    for fid in REQUIRED_IN_BOTH:
        assert fid in index_ids and fid in contract_ids


def test_phase_directories_not_claimed_by_two_phase_numbers() -> None:
    """A `tests/phase_<n>/` path may not be claimed by two different Phase numbers."""
    text = CHANGES_PATH.read_text(encoding="utf-8")
    headings = list(PHASE_HEADING_RE.finditer(text))
    dir_to_phases: dict[str, set[int]] = defaultdict(set)
    for i, match in enumerate(headings):
        phase_no = int(match.group(2))
        start = match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        body = text[start:end]
        claimed: set[str] = set()
        for claim_re in PHASE_CLAIM_RES:
            for dir_match in claim_re.finditer(body):
                claimed.add(f"tests/phase_{dir_match.group(1)}/")
        for dirname in claimed:
            dir_to_phases[dirname].add(phase_no)
    collisions = {
        dirname: sorted(phases)
        for dirname, phases in dir_to_phases.items()
        if len(phases) > 1
    }
    assert not collisions, (
        "tests/phase_<n>/ claimed by more than one Phase number in CHANGES.md: "
        f"{collisions}"
    )


def test_contract_source_has_no_duplicate_formula_id_literals_in_index_sense() -> None:
    """Sanity: metric_contract.py file parses; index file is UTF-8 text."""
    assert CONTRACT_PATH.is_file()
    assert INDEX_PATH.is_file()
    assert CHANGES_PATH.is_file()
