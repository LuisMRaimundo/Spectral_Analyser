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
    effective_partial_density = MetricDefinition(
        name="effective_partial_density",
        formula="(Σ P_i)^2 / Σ P_i^2 with P_i = A_i^2 (Hill q=2 / inverse Herfindahl)",
        input_domain="validated_partials_only",
        unit_or_scale="dimensionless participation ratio",
        amplitude_basis="Amplitude_raw of include_for_density=True harmonics",
        power_basis="P_i = Amplitude_raw^2",
        normalization_scope="validated harmonic partials only (Fix 2)",
        physical_interpretation=(
            "Effective number of harmonic partials after exclusive slot "
            "assignment and include_for_density gating. Floor / unconfirmed "
            "inharmonic rows are excluded; ungated copy is effective_partial_density_ungated."
        ),
        not_valid_for="Ungated peak-candidate lists or Complete Spectrum bins.",
        ontology_family="partial_count_descriptor",
    )
    linear_sum_amplitude = MetricDefinition(
        name="linear_sum_amplitude_*",
        formula="Σ Amplitude_raw over validated partials of each family",
        input_domain="validated_partials_only",
        unit_or_scale="linear amplitude (arbitrary units)",
        amplitude_basis="Amplitude_raw",
        power_basis="not used (linear sum, not energy)",
        normalization_scope="validated_partials_only (Fix 2); ungated copies keep *_ungated",
        physical_interpretation=(
            "Diagnostic linear-amplitude mass for H/I/S pies. Inharmonic rows "
            "enter only when inharmonic_status is confirmed_inharmonic_partial. "
            "Sub-bass includes only F-020 compartment members."
        ),
        not_valid_for="Treating as energy or as an ungated peak-candidate sum.",
        ontology_family="diagnostic_amplitude_mass",
    )
    sethares_dissonance = MetricDefinition(
        name="sethares_dissonance",
        formula="Sethares pairwise roughness on (frequency, amplitude) pairs",
        input_domain="validated_partials_only",
        unit_or_scale="model units (Sethares)",
        amplitude_basis="Amplitude_raw of include_for_density=True harmonics",
        power_basis="not used",
        normalization_scope="validated harmonic partials only (Fix 2)",
        physical_interpretation=(
            "Dissonance from validated harmonic partials after exclusive "
            "assignment plus confirmed inharmonic partials. Source note "
            "states the validated list, not the residual-candidate count."
        ),
        not_valid_for="Retained nonharmonic / floor-candidate lists.",
        ontology_family="sensory_dissonance",
    )
    inharmonic_density_sum = MetricDefinition(
        name="inharmonic_density_sum",
        formula="D_I = Σ_{i ∈ I} φ(A_i)  (F-014; φ unchanged)",
        input_domain="confirmed_inharmonic_partials",
        unit_or_scale="dimensionless (weight-function dependent)",
        amplitude_basis="Amplitude_raw of inharmonic_status=confirmed_inharmonic_partial",
        power_basis="Power_raw = Amplitude_raw^2",
        normalization_scope="confirmed_inharmonic_partials (Phase A)",
        physical_interpretation=(
            "Inharmonic compartment density. I is the confirmed-inharmonic "
            "partial class (CFAR, prominence, persistence, leakage, F-007 "
            "comb). Floor / leakage / stretched-comb residuals are excluded."
        ),
        not_valid_for="Ungated residual-candidate lists or Complete Spectrum bins.",
        ontology_family="component_density",
    )
    inharmonic_status = MetricDefinition(
        name="inharmonic_status",
        formula=(
            "confirmed iff cfar ∧ local_peak ∧ persistence ∧ not_leakage "
            "∧ not_stretched_harmonic; else rejected_floor / "
            "rejected_leakage / rejected_stretched_harmonic / "
            "candidate_not_confirmed_partial"
        ),
        input_domain="residual spectral candidates after harmonic exclusion",
        unit_or_scale="categorical status",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per candidate",
        physical_interpretation=(
            "Confirmation outcome for one residual candidate. Only "
            "confirmed_inharmonic_partial rows enter the I compartment."
        ),
        not_valid_for="Treating residual-candidate rows as confirmed partials.",
        ontology_family="validation_status",
    )
    inharmonic_confirmed_count = MetricDefinition(
        name="inharmonic_confirmed_count",
        formula="count(inharmonic_status = confirmed_inharmonic_partial)",
        input_domain="confirmed_inharmonic_partials",
        unit_or_scale="count",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation="Number of confirmed inharmonic partials.",
        not_valid_for="Equating with residual-candidate or floor-row counts.",
        ontology_family="partial_count_descriptor",
    )
    persistence_fraction = MetricDefinition(
        name="persistence_fraction",
        formula="n_frames_with_peak_within_tol_hz / sustain_frame_count",
        input_domain="per-frame sustain peaks",
        unit_or_scale="ratio [0, 1]",
        amplitude_basis="per-frame linear magnitude",
        power_basis="not used",
        normalization_scope="sustain frames of this note",
        physical_interpretation=(
            "Fraction of sustain STFT frames that contain a detected peak "
            "within search_tol_hz of the time-averaged candidate frequency. "
            "Required ≥ PARTIAL_PERSISTENCE_MIN_FRACTION for include_for_density."
        ),
        not_valid_for="Time-averaged spectra or Complete Spectrum bins.",
        ontology_family="validation_status",
    )
    return {
        density_raw.name: density_raw,
        density_alias.name: density_alias,
        effective_partial_density.name: effective_partial_density,
        linear_sum_amplitude.name: linear_sum_amplitude,
        sethares_dissonance.name: sethares_dissonance,
        inharmonic_density_sum.name: inharmonic_density_sum,
        inharmonic_status.name: inharmonic_status,
        inharmonic_confirmed_count.name: inharmonic_confirmed_count,
        persistence_fraction.name: persistence_fraction,
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
