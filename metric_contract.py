"""
Epistemic contract for exported metrics. Each metric carries an explicit
record of its formula, input domain, unit/scale, amplitude and power
bases, normalisation scope, physical interpretation, validity boundary,
and ontological family. The intent is to make downstream use auditable
and to prevent silent re-interpretation of metric semantics.

References
----------
- Hatton, L. (1997). The T-experiments: Errors in scientific software.
  IEEE Computational Science and Engineering, 4(2), 27–38.
- Soergel, D. A. W. (2015). Rampant software errors may undermine
  scientific results. F1000Research, 3, 303.

See REFERENCES.md at the repository root for canonical APA-7 entries.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class MetricDefinition:
    """Epistemic contract for one exported metric."""

    name: str
    formula: str
    input_domain: str
    unit_or_scale: str
    amplitude_basis: str
    power_basis: str
    normalization_scope: str
    physical_interpretation: str
    not_valid_for: str
    ontology_family: str


def _density_weighted_formula() -> str:
    return "D_H*w_H + D_I*w_I + D_S*w_S"


def build_metric_contracts() -> Dict[str, MetricDefinition]:
    """Central dictionary for density-related exported quantities."""
    density_raw = MetricDefinition(
        name="density_metric_raw",
        formula=_density_weighted_formula(),
        input_domain="Per-note D_H/D_I/D_S and component ratios w_H/w_I/w_S",
        unit_or_scale="dimensionless (weight-function dependent)",
        amplitude_basis="Amplitude_raw (linear/log-amplitude branch)",
        power_basis="Power_raw = Amplitude_raw^2 (component-ratio derivation)",
        normalization_scope="none (raw per-note value)",
        physical_interpretation=(
            "Model-derived composite density that combines harmonic, inharmonic "
            "and sub-bass component densities using component-energy ratios."
        ),
        not_valid_for=(
            "Direct loudness or absolute energy comparisons across recordings with "
            "different gain policies."
        ),
        ontology_family="composite_metric",
    )
    density_alias = MetricDefinition(
        name="density_weighted_sum",
        formula=_density_weighted_formula(),
        input_domain="Same as density_metric_raw",
        unit_or_scale="dimensionless",
        amplitude_basis=density_raw.amplitude_basis,
        power_basis=density_raw.power_basis,
        normalization_scope="none (alias)",
        physical_interpretation=(
            "Legacy alias of density_metric_raw. Kept for compatibility only."
        ),
        not_valid_for="Treating as an independent metric from density_metric_raw.",
        ontology_family="legacy_only",
    )
    return {
        density_raw.name: density_raw,
        density_alias.name: density_alias,
    }


_CONTRACTS = build_metric_contracts()


def get_metric_definition(name: str) -> MetricDefinition | None:
    return _CONTRACTS.get(str(name))


def as_export_fields(name: str) -> Dict[str, str]:
    """Flatten one metric definition for workbook row export."""
    d = get_metric_definition(name)
    if d is None:
        return {}
    out: Dict[str, str] = {}
    src = asdict(d)
    for k, v in src.items():
        out[f"metric_contract_{k}"] = str(v)
    return out


def density_metric_basis_label(weight_function: str) -> str:
    wf = str(weight_function or "").strip().lower() or "linear"
    if wf == "log":
        return "log-amplitude"
    if wf == "power":
        return "power"
    return "amplitude"


def classify_f0_epistemic_status(
    *,
    f0_fit_accepted: bool,
    acoustic_f0_status: str,
    f0_validation_mode: str = "",
) -> Tuple[str, bool]:
    """Return (tri-state status, valid_for_primary_statistics)."""
    status = str(acoustic_f0_status or "").strip().lower()
    mode = str(f0_validation_mode or "").strip().lower()
    accepted = bool(f0_fit_accepted)
    if accepted and mode == "nominal_guided_f0_validation":
        return ("nominal_guided_acoustically_verified", True)
    if accepted and ("accepted" in status or "verified" in status or "robust" in status):
        return ("free_fit_acoustically_verified", True)
    if "rejected" in status or "fallback" in status or "nominal" in status or not accepted:
        return ("nominal_fallback_not_verified", False)
    return ("nominal_fallback_not_verified", False)
