#!/usr/bin/env python3
"""Stage 3 ACD contract, diagnostics, and fail-closed assessment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Sequence

import pandas as pd

from tools.spectral_density_hill import MODULE_REVISION

STAGE3_ACD_STATUS_OK: Final[str] = "ok"
STAGE3_ACD_STATUS_DEGRADED: Final[str] = "degraded"
STAGE3_ACD_STATUS_FAILED: Final[str] = "failed"

MERGE_STATUS_FAILED: Final[frozenset[str]] = frozenset(
    {
        "acd_computation_failed",
        "no_per_note_workbooks_found",
    }
)


class AcdStage3Error(RuntimeError):
    """Base error for Stage 3 ACD contract violations."""


class AcdComputationFailed(AcdStage3Error):
    """ACD core computation raised an exception."""


class AcdWorkbooksNotFound(AcdStage3Error):
    """No per-note spectral_analysis workbooks under the analysis folder."""


@dataclass(frozen=True)
class AcdStage3MergeResult:
    spectral_density_metrics: pd.DataFrame
    diagnostics: pd.DataFrame
    diagnostics_summary: pd.DataFrame
    status: str
    messages: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.status == STAGE3_ACD_STATUS_OK


def build_acd_diagnostics(
    sd: pd.DataFrame,
    *,
    analysis_root: str,
    n_workbooks: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    empty_note = pd.DataFrame(
        columns=["Note", "acd_merge_status", "ACD_status", "ACD_score", "stage3_acd_issue"]
    )
    empty_summary = pd.DataFrame(columns=["stage3_acd_status_row", "ACD_version", "stage3_acd_issue"])
    if sd is None or sd.empty or "Note" not in sd.columns:
        return empty_note, empty_summary

    rows: list[dict[str, object]] = []
    for _, row in sd.iterrows():
        status = str(row.get("acd_merge_status", "")).strip()
        issue = ""
        if status in MERGE_STATUS_FAILED:
            issue = status
        elif status == "note_not_in_acd_output":
            issue = "note_not_in_acd_output"
        elif str(row.get("ACD_status", "")).strip() not in {"ok", ""} and not str(
            row.get("ACD_status", "")
        ).startswith("ok"):
            issue = str(row.get("ACD_status", "")).strip()
        rows.append(
            {
                "Note": str(row.get("Note", "")).strip(),
                "acd_merge_status": status,
                "ACD_status": row.get("ACD_status"),
                "ACD_score": row.get("ACD_score"),
                "stage3_acd_issue": issue,
            }
        )
    summary = pd.DataFrame(rows)
    meta = pd.DataFrame(
        [
            {
                "stage3_acd_status_row": "__STAGE3_ACD_SUMMARY__",
                "ACD_version": MODULE_REVISION,
                "stage3_acd_issue": (
                    f"analysis_root={analysis_root}; workbooks={n_workbooks}; rows={len(sd)}"
                ),
            }
        ]
    )
    return summary, meta


def assess_acd_merge_result(
    sd: pd.DataFrame,
    *,
    include_acd: bool,
    global_status: str,
    messages: Sequence[str],
) -> str:
    if not include_acd:
        return STAGE3_ACD_STATUS_OK
    if global_status in MERGE_STATUS_FAILED:
        return STAGE3_ACD_STATUS_FAILED
    if sd is None or sd.empty or "acd_merge_status" not in sd.columns:
        return STAGE3_ACD_STATUS_FAILED
    statuses = sd["acd_merge_status"].astype(str)
    if statuses.isin(MERGE_STATUS_FAILED).any():
        return STAGE3_ACD_STATUS_FAILED
    missing = statuses.eq("note_not_in_acd_output").sum()
    ok_scores = 0
    if "ACD_score" in sd.columns:
        ok_scores = int(sd["ACD_score"].notna().sum())
    if missing > 0 or ok_scores == 0:
        return STAGE3_ACD_STATUS_DEGRADED
    if any("failed" in str(m).lower() for m in messages):
        return STAGE3_ACD_STATUS_DEGRADED
    return STAGE3_ACD_STATUS_OK


def enforce_acd_fail_closed(result: AcdStage3MergeResult) -> None:
    if result.status != STAGE3_ACD_STATUS_FAILED:
        return
    msg = "; ".join(result.messages) if result.messages else "Stage 3 ACD failed"
    statuses: set[str] = set()
    if "acd_merge_status" in result.diagnostics.columns:
        statuses = set(result.diagnostics["acd_merge_status"].astype(str))
    if "no_per_note_workbooks_found" in statuses:
        raise AcdWorkbooksNotFound(msg)
    if "acd_computation_failed" in statuses:
        raise AcdComputationFailed(msg)
    raise AcdStage3Error(msg)
