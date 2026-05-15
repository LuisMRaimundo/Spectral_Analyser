"""
Canonical publication-facing pipeline contract (Stage 1 + Stage 2).

This module is the single source of truth for *which* modules and artefacts
define publication-grade acoustic metrics. Other entry points must either
delegate here or declare themselves legacy/diagnostic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

PIPELINE_CONTRACT_VERSION: Final[str] = (
    "SSA_CANONICAL_PIPELINE_2026_05_STAGE1_PROC_AUDIO_STAGE2_COMPILE_METRICS"
)

CANONICAL_STAGE1_MODULE: Final[str] = "proc_audio"
CANONICAL_STAGE1_CLASS: Final[str] = "AudioProcessor"
CANONICAL_STAGE2_MODULE: Final[str] = "compile_metrics"
CANONICAL_STAGE2_FUNCTION: Final[str] = "compile_density_metrics_with_pca"

CANONICAL_PER_NOTE_WORKBOOK: Final[str] = "spectral_analysis.xlsx"
CANONICAL_COMPILED_WORKBOOK: Final[str] = "compiled_density_metrics.xlsx"


@dataclass(frozen=True)
class PipelineContract:
    contract_version: str = PIPELINE_CONTRACT_VERSION
    stage1_module: str = CANONICAL_STAGE1_MODULE
    stage1_class: str = CANONICAL_STAGE1_CLASS
    stage2_module: str = CANONICAL_STAGE2_MODULE
    stage2_function: str = CANONICAL_STAGE2_FUNCTION
    per_note_workbook: str = CANONICAL_PER_NOTE_WORKBOOK
    compiled_workbook: str = CANONICAL_COMPILED_WORKBOOK
    publication_output_allowed: bool = True


def get_canonical_pipeline_contract() -> PipelineContract:
    """Return the frozen canonical pipeline contract (no runtime mutation)."""
    return PipelineContract()
