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
    formula_id: str = ""
    formula_version: str = ""
    notes: str = ""


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
        notes=(
            "superseded for analytical use by ACD_score (F-057) / spectral_mass "
            "(F-061); retained for workbook compatibility"
        ),
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
        formula=(
            "Sethares pairwise roughness; default metric_mode=minamp_norm "
            "(Σ d_ij / Σ min(a_i,a_j)). mean_pair_scaled is retained as an "
            "opt-in. Shared base implementation with Vassilakis (no Liskov override)."
        ),
        input_domain="validated_partials_only",
        unit_or_scale="model units (Sethares, minamp_norm)",
        amplitude_basis="Amplitude_raw of include_for_density=True harmonics",
        power_basis="not used",
        normalization_scope="validated harmonic partials only (Fix 2)",
        physical_interpretation=(
            "Dissonance from validated harmonic partials after exclusive "
            "assignment plus confirmed inharmonic partials. Default is "
            "invariant to peak count and global amplitude scale."
        ),
        not_valid_for="Retained nonharmonic / floor-candidate lists.",
        ontology_family="sensory_dissonance",
        formula_id="COL:sethares_dissonance",
        formula_version="4.6.0",
    )
    roughness_parncutt_kernel = MetricDefinition(
        name="roughness_parncutt_kernel",
        formula=(
            "F-037: x = |f_i-f_j| / (0.25 * CB(f_lo)); default CB = Zwicker "
            "25+75(1+1.4(f/1000)^2)^0.69 (Zwicker & Fastl, 2007). "
            "bandwidth_basis='erb' keeps 0.25*ERB(f)=0.25*(0.108f+24.7). "
            "g(x)=x*exp(1-x) (Parncutt 1989 / Plomp & Levelt 1965). "
            "Pairs with max(f_i,f_j) > CB_ZWICKER_VALID_MAX_HZ=15500 are excluded. "
            "Default is provenance-consistent (P&L used the Zwicker CB lineage, "
            "not ERB). Fig. 10 overlay is outstanding non-blocking corroboration."
        ),
        input_domain="peak-picked linear amplitudes and frequencies",
        unit_or_scale="pairwise kernel units",
        amplitude_basis="Amplitude_raw (linear)",
        power_basis="not used (amplitude product)",
        normalization_scope="per spectrum",
        physical_interpretation=(
            "Pairwise spectral roughness. Provenance-consistent default peaks "
            "at ~0.25 Zwicker CB (~40 Hz at 1 kHz). Independent of ACD ERB helpers."
        ),
        not_valid_for="Citing as Aures (1985); importing into spectral_density_hill.",
        ontology_family="sensory_dissonance",
        formula_id="F-037",
        formula_version="4.5.0",
    )
    roughness_aures_1985 = MetricDefinition(
        name="roughness_aures_1985",
        formula=(
            "Retired name. Calling the function raises NotImplementedError. "
            "New exports write NaN. Use roughness_parncutt_kernel (F-037). "
            "Archived values used a mis-specified bandwidth and are not comparable."
        ),
        input_domain="retired; see roughness_parncutt_kernel",
        unit_or_scale="pairwise kernel units (archived only)",
        amplitude_basis="Amplitude_raw (linear)",
        power_basis="not used (amplitude product)",
        normalization_scope="per spectrum",
        physical_interpretation=(
            "Retired column. Not a live alias of roughness_parncutt_kernel."
        ),
        not_valid_for="Any new analysis; archived values are not comparable.",
        ontology_family="sensory_dissonance",
        notes=(
            "retired key, NaN-filled, misattributed citation; successor is "
            "roughness_parncutt_kernel (F-037); scheduled for removal from new "
            "exports at next major version"
        ),
    )
    roughness_pairs_excluded_above_validity = MetricDefinition(
        name="roughness_pairs_excluded_above_validity",
        formula=(
            "Count of unordered pairs (i,j) whose higher frequency exceeds "
            "CB_ZWICKER_VALID_MAX_HZ = 15500 (Bark-scale ceiling of the "
            "Zwicker CB fit). Those pairs are omitted from F-037."
        ),
        input_domain="peak-picked frequencies (same list as F-037)",
        unit_or_scale="pair count",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per spectrum",
        physical_interpretation=(
            "Diagnostic: how much of the pairwise roster sits above the "
            "defined Zwicker CB range."
        ),
        not_valid_for="Treating as a roughness magnitude.",
        ontology_family="diagnostic_count",
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
    expected_false_harmonic_slots = MetricDefinition(
        name="expected_false_harmonic_slots",
        formula="harmonic_slot_expected_count × CFAR_PFA",
        input_domain="harmonic slots searched",
        unit_or_scale="count (expected)",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation=(
            "False-alarm budget for harmonic slot tests at the stated P_fa. "
            "Not a measured partial count."
        ),
        not_valid_for="Equating with validated or candidate harmonic counts.",
        ontology_family="validation_status",
    )
    accepted_slots_above_body_stop = MetricDefinition(
        name="accepted_slots_above_body_stop",
        formula="count(include_for_density ∧ n > body_stop_order)",
        input_domain="gated harmonic candidates",
        unit_or_scale="count",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation=(
            "Included harmonic slots above the (diagnostic) body stop. "
            "Must be 0 after gating."
        ),
        not_valid_for="Density integrals or un-gated candidate lists.",
        ontology_family="validation_status",
    )
    note_effective_component_density_ci = MetricDefinition(
        name="note_effective_component_density_ci",
        formula="bootstrap percentiles of (Σ A²)² / Σ A⁴ on resampled amplitudes",
        input_domain="validated H+I+S partial amplitudes (F-047 algebra unchanged)",
        unit_or_scale="count (≥1) interval",
        amplitude_basis="linear amplitude (resampled)",
        power_basis="A² (participation ratio; not recomputed as a new formula)",
        normalization_scope="per note",
        physical_interpretation=(
            "Non-parametric CI for note_effective_component_density. "
            "The point estimate remains F-047; only the amplitude vector "
            "is resampled."
        ),
        not_valid_for="Changing F-047 algebra or treating the CI as a new fatness formula.",
        ontology_family="uncertainty",
    )
    ci_basis_frame_count = MetricDefinition(
        name="ci_basis_frame_count",
        formula="sustain_frame_count_independent",
        input_domain="Per_Note_Processing_Metadata",
        unit_or_scale="count",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation=(
            "Independent-frame sample size sitting beside every exported CI. "
            "Flagged when below CI_BASIS_INDEPENDENT_FRAME_MIN (10)."
        ),
        not_valid_for="Equating with raw STFT hop count or partial count.",
        ontology_family="uncertainty",
    )
    ci_basis_partial_count = MetricDefinition(
        name="ci_basis_partial_count",
        formula="count of pooled validated H+I+S amplitudes used in the CI",
        input_domain="validated partials",
        unit_or_scale="count",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation=(
            "Number of partial amplitudes resampled for the accompanying CI."
        ),
        not_valid_for="Treating as an effective-count or fatness scalar.",
        ontology_family="uncertainty",
    )
    harmonic_slot_candidate_count = MetricDefinition(
        name="harmonic_slot_candidate_count",
        formula="count of harmonic slots that found a candidate peak",
        input_domain="harmonic slots searched",
        unit_or_scale="count (matching diagnostic)",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation=(
            "Matching diagnostic (legacy alias: harmonic_slot_matched_count). "
            "Not a validated-partial count."
        ),
        not_valid_for="Equating with harmonic_validated_count or a partial count.",
        ontology_family="validation_status",
    )
    harmonic_validated_count = MetricDefinition(
        name="harmonic_validated_count",
        formula="count(include_for_density = TRUE)",
        input_domain="validated_partials_only",
        unit_or_scale="count",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation=(
            "Number of validated harmonic partials, including "
            "validated_weak (weak-margin persistence override)."
        ),
        not_valid_for="Equating with harmonic_slot_candidate_count.",
        ontology_family="partial_count_descriptor",
    )
    harmonic_validated_weak_count = MetricDefinition(
        name="harmonic_validated_weak_count",
        formula="count(candidate_status = validated_weak ∧ include_for_density)",
        input_domain="validated_partials_only",
        unit_or_scale="count",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation=(
            "Detected harmonics admitted by persistence ≥ 0.9 despite a "
            "CFAR margin below 3 dB."
        ),
        not_valid_for="Treating as a different fatness formula.",
        ontology_family="validation_status",
    )
    harmonic_validated_strict_count = MetricDefinition(
        name="harmonic_validated_strict_count",
        formula="harmonic_validated_count − harmonic_validated_weak_count",
        input_domain="validated_partials_only",
        unit_or_scale="count",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation=(
            "Pre-override include_for_density count (margin ≥ 3 dB, or "
            "tolerance-continuity includes)."
        ),
        not_valid_for="Equating with harmonic_validated_count after D1.",
        ontology_family="validation_status",
    )
    tolerance_continuity_override_count = MetricDefinition(
        name="tolerance_continuity_override_count",
        formula="count(tolerance_limb = spacing_cap_continuity)",
        input_domain="harmonic slots after exclusive assignment",
        unit_or_scale="count",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation=(
            "Isolated rejected_by_tolerance slots re-included because both "
            "neighbours are validated and |dev| < 1.25 × cap."
        ),
        not_valid_for="Changing F-051 exclusive assignment of shared bins.",
        ontology_family="validation_status",
    )
    ci_resampling_unit = MetricDefinition(
        name="ci_resampling_unit",
        formula="partials | frames | frames_blocked",
        input_domain="bootstrap configuration (estimator unchanged)",
        unit_or_scale="category",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation="What the accompanying CI resamples.",
        not_valid_for="Treating as a change to F-047 algebra.",
        ontology_family="uncertainty",
    )
    subbass_member_count = MetricDefinition(
        name="subbass_member_count",
        formula="count(subbass_membership = subbass_member) at or below F-020",
        input_domain="subbass_compartment_members",
        unit_or_scale="count",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation=(
            "F-020 compartment members on the Sub-bass sheet. "
            "Not a validated-partial count."
        ),
        not_valid_for="Equating with *_validated_count or *_confirmed_count.",
        ontology_family="validation_status",
    )
    floor_rows_rejected_count = MetricDefinition(
        name="floor_rows_rejected_count",
        formula="count(inharmonic_status = rejected_floor)",
        input_domain="residual spectral candidates after harmonic exclusion",
        unit_or_scale="count",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation="Residual candidates rejected as floor by CFAR.",
        not_valid_for="Equating with inharmonic_confirmed_count or a partial count.",
        ontology_family="validation_status",
    )
    subbass_upper_bound_hz = MetricDefinition(
        name="subbass_upper_bound_hz",
        formula="min(0.5 * f0, 80)  (F-020)",
        input_domain="per-note F-020 policy bound",
        unit_or_scale="Hz",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation=(
            "Operational S-compartment ceiling. Rows above it are "
            "lf_diagnostic_not_member and contribute 0 to S sums."
        ),
        not_valid_for="Treating as a partial count or as the diagnostic-export ceiling.",
        ontology_family="policy_bound",
    )
    energy_basis = MetricDefinition(
        name="energy_basis",
        formula="psd_per_hz = Σ P_bin × Δf  (peak: P_peak × ENBW_hz)",
        input_domain="periodogram bin power and analysis window",
        unit_or_scale="token",
        amplitude_basis="not used",
        power_basis="PSD integrated over Hz",
        normalization_scope="per note / per window",
        physical_interpretation=(
            "Declares that Stage 2/3 energy sums are power spectral density "
            "integrated over Hertz, not raw bin-power sums."
        ),
        not_valid_for="Comparing pre-fix per-bin energy workbooks across n_fft tiers.",
        ontology_family="provenance",
    )
    window_enbw_hz = MetricDefinition(
        name="window_enbw_hz",
        formula="ENBW_bins × (sr / n_fft); ENBW_bins = N Σw² / (Σw)²",
        input_domain="analysis window samples",
        unit_or_scale="Hz",
        amplitude_basis="not used",
        power_basis="equivalent noise bandwidth",
        normalization_scope="per note",
        physical_interpretation="Window equivalent noise bandwidth used for peak energy.",
        not_valid_for="Treating as a density or a partial count.",
        ontology_family="analysis_parameter",
    )
    included_above_body_stop_count = MetricDefinition(
        name="included_above_body_stop_count",
        formula="count(include_for_density and n > harmonic_body_stop_order)",
        input_domain="harmonic slots after body stop",
        unit_or_scale="count",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation=(
            "Included (density) harmonics above the body stop. Invariant: 0. "
            "validated_harmonics_above_body_stop_count is CFAR-validated-then-excluded, not this."
        ),
        not_valid_for="Equating with validated_harmonics_above_body_stop_count.",
        ontology_family="validation_status",
    )
    peak_power_footprint_bins = MetricDefinition(
        name="peak_power_footprint_bins",
        formula="ENBW_bins = N Σw² / (Σw)²",
        input_domain="analysis window samples",
        unit_or_scale="bins",
        amplitude_basis="not used",
        power_basis="equivalent noise bandwidth",
        normalization_scope="per note",
        physical_interpretation="ENBW used only for the peak-power estimate. Residual exclusion is residual_exclusion_footprint_bins.",
        not_valid_for="Using as the residual-exclusion width.",
        ontology_family="analysis_parameter",
    )
    residual_exclusion_footprint_bins = MetricDefinition(
        name="residual_exclusion_footprint_bins",
        formula="RESIDUAL_EXCLUSION_FOOTPRINT (BH-4 ±4 bins) or window first-null diameter",
        input_domain="analysis window type",
        unit_or_scale="bins",
        amplitude_basis="not used",
        power_basis="main-lobe exclusion diameter",
        normalization_scope="per note",
        physical_interpretation="Width removed around each validated harmonic (and confirmed I) before residual energy is summed.",
        not_valid_for="Using as the peak-power ENBW.",
        ontology_family="analysis_parameter",
    )
    residual_region_hz_total = MetricDefinition(
        name="residual_region_hz_total",
        formula="analysis_band_hz − excluded_region_hz_total",
        input_domain="analysis band and exclusion-footprint union",
        unit_or_scale="Hz",
        amplitude_basis="not used",
        power_basis="one-sided Hz",
        normalization_scope="per note",
        physical_interpretation="Hz remaining after validated-peak exclusion. Invariant: residual + excluded == analysis_band.",
        not_valid_for="Treating as a bin count times Δf without the exclusion union.",
        ontology_family="analysis_parameter",
    )
    excluded_region_hz_total = MetricDefinition(
        name="excluded_region_hz_total",
        formula="union of residual-exclusion footprints clipped to the analysis band",
        input_domain="validated harmonic and confirmed-I frequencies",
        unit_or_scale="Hz",
        amplitude_basis="not used",
        power_basis="one-sided Hz",
        normalization_scope="per note",
        physical_interpretation="Hz removed from the residual by the exclusion footprints.",
        not_valid_for="Adding overlapping footprints without a union.",
        ontology_family="analysis_parameter",
    )
    fft_policy = MetricDefinition(
        name="fft_policy",
        formula="fixed | adaptive_tier",
        input_domain="corpus FFT sizing policy",
        unit_or_scale="token",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per run",
        physical_interpretation=(
            "fixed uses one n_fft/hop for every note (default for comparable corpora). "
            "adaptive_tier follows the f0 tier table and is not primary-comparable."
        ),
        not_valid_for="Mixing adaptive_tier notes across a tier boundary without psd_per_hz.",
        ontology_family="analysis_parameter",
    )
    segment_policy = MetricDefinition(
        name="segment_policy",
        formula="sustain_primary_stable_diagnostic",
        input_domain="sustain cut plus optional stable sibling",
        unit_or_scale="token",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation=(
            "Primary analysis uses the sustain cut. A stable-sustain sibling "
            "is diagnostic only and never replaces the primary EWSD."
        ),
        not_valid_for="Substituting stable-segment EWSD for the primary value.",
        ontology_family="analysis_parameter",
    )
    stable_segment_ewsd = MetricDefinition(
        name="stable_segment_ewsd",
        formula="EWSD of the stable-sustain sibling (diagnostic)",
        input_domain="stable sibling metrics when present",
        unit_or_scale="EWSD units",
        amplitude_basis="same as primary EWSD",
        power_basis="same as primary EWSD",
        normalization_scope="per note",
        physical_interpretation="Stable-cut EWSD. NaN when no sibling metrics (nan_not_zero_v1).",
        not_valid_for="Replacing the primary EWSD or filling missing siblings with 0.",
        ontology_family="diagnostic",
    )
    full_stable_ewsd_ratio = MetricDefinition(
        name="full_stable_ewsd_ratio",
        formula="full_ewsd / stable_ewsd",
        input_domain="paired full and stable EWSD",
        unit_or_scale="ratio",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation=(
            "Representativeness ratio. Flagged when > STABLE_REPRESENTATIVENESS_MAX_RATIO (1.3)."
        ),
        not_valid_for="Rescaling the primary EWSD.",
        ontology_family="diagnostic",
    )
    stable_segment_frames_independent = MetricDefinition(
        name="stable_segment_frames_independent",
        formula="stable sustain_frame_count / (n_fft / hop)",
        input_domain="stable sibling",
        unit_or_scale="count",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation="Independent-frame count of the stable sibling. NaN if missing.",
        not_valid_for="Treating as the primary sustain_frame_count_independent.",
        ontology_family="diagnostic",
    )
    stable_segment_unrepresentative = MetricDefinition(
        name="stable_segment_unrepresentative",
        formula="full_stable_ewsd_ratio > 1.3 OR centroid ratio > 2.0",
        input_domain="paired full and stable descriptors",
        unit_or_scale="boolean",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation="Flag only. Does not change any exported value.",
        not_valid_for="Dropping or rewriting the primary EWSD.",
        ontology_family="validation_status",
    )
    ewsd_primary_analysis_eligible = MetricDefinition(
        name="ewsd_primary_analysis_eligible",
        formula=(
            "existing quality gates AND sustain_frame_count_independent >= 8 "
            "AND harmonic_validated_count > 2"
        ),
        input_domain="Stage 3 quality columns plus WP3 production gates",
        unit_or_scale="boolean",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation="Thesis-safe EWSD row. False on short or degenerate takes.",
        not_valid_for="Treating ineligible rows as 0.0 EWSD.",
        ontology_family="validation_status",
    )
    estimated_snr_db = MetricDefinition(
        name="estimated_snr_db",
        formula="power-weighted mean of validated-harmonic snr_db (peak dB − local floor dB)",
        input_domain="include_for_density harmonic slots; snr_db already on the peak table",
        unit_or_scale="dB",
        amplitude_basis="not used",
        power_basis="Power_raw weights; snr_db is peak vs local floor",
        normalization_scope="per note",
        physical_interpretation=(
            "Note-level spectral cleanliness. EWSD rises with this "
            "conditioner (B7); report it beside EWSD for cross-dynamic work."
        ),
        not_valid_for="Substituting for EPD or treating as a laboratory SNR meter.",
        ontology_family="conditioning",
    )
    degenerate_partial_set = MetricDefinition(
        name="degenerate_partial_set",
        formula="harmonic_validated_count <= 2",
        input_domain="validated harmonics",
        unit_or_scale="boolean",
        amplitude_basis="not used",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation=(
            "Too few validated harmonics for a CI. Rel_uncertainty is NaN, never 0.0."
        ),
        not_valid_for="Reporting a zero-width CI as certainty.",
        ontology_family="validation_status",
    )
    note_balanced_component_density = MetricDefinition(
        name="note_balanced_component_density",
        formula=(
            "F-056 provenance: defined. "
            "P_i = A_i ** 2; p_i = P_i / sum(P)  # skip components with P_i == 0; "
            "D1 = exp( - sum(p_i * ln(p_i)) ). "
            "Empty pool or sum(P) == 0 -> NaN; single component -> D1 = 1.0. "
            "Pool: validated harmonic components (include_for_density == True) "
            "UNION confirmed inharmonic components "
            "UNION sub-bass components whose membership/interpretation status marks them "
            "as partials. EXCLUDE any row whose Acoustic_Interpretation_Status equals "
            "\"diagnostic_low_frequency_residual_not_partial\" and any unconfirmed row. "
            "(Note: this pool is stricter than the F-047 pool. Do not change F-047.)"
        ),
        input_domain=(
            "stricter H+I+S pool than F-047: include_for_density harmonics, "
            "confirmed inharmonics, sub-bass partials; exclude diagnostic residual "
            "and unconfirmed rows"
        ),
        unit_or_scale="Hill number q=1 (effective component count)",
        amplitude_basis="Amplitude_raw (linear); no dB conversion",
        power_basis="P_i = Amplitude_raw^2 (energy shares)",
        normalization_scope="per-note energy shares of the F-056 pool",
        physical_interpretation=(
            "Exponential of Shannon entropy of component energy shares "
            "(Hill q=1). Scale-invariant; 1 <= D1 <= pool count when defined."
        ),
        not_valid_for=(
            "Empty pool (NaN, never 0.0); unconfirmed or "
            "diagnostic_low_frequency_residual_not_partial rows; substituting for F-047."
        ),
        ontology_family="partial_count_descriptor",
        notes=(
            "superseded by ACD_score (rho = 0.999 on validation corpora); "
            "retained for workbook compatibility"
        ),
    )
    note_balanced_component_density_pool_count = MetricDefinition(
        name="note_balanced_component_density_pool_count",
        formula="count of F-056 pool rows after the stricter filter (integer)",
        input_domain="same F-056 pool as note_balanced_component_density",
        unit_or_scale="count (integer)",
        amplitude_basis="not used (census of admitted rows)",
        power_basis="not used",
        normalization_scope="per note",
        physical_interpretation="Number of components admitted to the F-056 pool.",
        not_valid_for="Equating with the F-047 HIS census or with D1 itself.",
        ontology_family="partial_count_descriptor",
    )
    ewsd_score_acoustic_balanced = MetricDefinition(
        name="EWSD_score_acoustic_balanced",
        formula=(
            "F-049: sum_k r_k D_k (N_eff,k / N_k)^alpha, alpha=0.5. "
            "diagnostic only; level-dependent; not for cross-note comparison. "
            "Companion sensitivity columns are F-050 "
            "(partial_multiset_sensitivity). F-048 is the strict EWSD point."
        ),
        input_domain="Stage 3 H/I/S compartments (computation unchanged)",
        unit_or_scale="EWSD units",
        amplitude_basis="same as F-049 / tools.ewsd_core (unchanged)",
        power_basis="same as F-049 (unchanged)",
        normalization_scope="per note",
        physical_interpretation=(
            "Acoustic-balanced EWSD companion. "
            "diagnostic only; level-dependent; not for cross-note comparison."
        ),
        not_valid_for=(
            "Cross-note comparison or treating as a primary density. "
            "Do not change its computation."
        ),
        ontology_family="legacy_only",
        notes=(
            "superseded as a mass/fullness measure by spectral_mass (F-061); "
            "retained as the validated developmental ancestor (see methods documentation)"
        ),
    )
    acd_score = MetricDefinition(
        name="ACD_score",
        formula=(
            "F-057: r_k = energy_k / sum_j energy_j (derived); "
            "ACD = sum_k r_k * D1_k after optional ERB merge. "
            "Report only as a pair with ACD_magnitude_per_component. "
            "Previous D2-based value is ACD_score_D2_dominance."
        ),
        input_domain="Per-note H/I/S linear amplitudes and frequencies (uniform filter)",
        unit_or_scale="Hill number q=1 (effective ERB-merged component count)",
        amplitude_basis="Amplitude_raw (linear); no dB conversion",
        power_basis="P_i = Amplitude_raw^2 (energy shares and r_k)",
        normalization_scope="per note, compartments energy-weighted",
        physical_interpretation=(
            "Effective number of ERB-merged components (D1). Scale-invariant. "
            "Not interpretable without ACD_magnitude_per_component."
        ),
        not_valid_for=(
            "Empty note (NaN, never 0.0); substituting for EWSD F-048/F-049; "
            "reading r_k from Excel AUTO_RATIO_PRIORITY columns."
        ),
        ontology_family="partial_count_descriptor",
    )
    acd_magnitude = MetricDefinition(
        name="ACD_magnitude_per_component",
        formula="F-058: LAM = sum_k energy_k / ACD_score (D1-based; energy = ACD_score * LAM)",
        input_domain="same ACD compartments as ACD_score",
        unit_or_scale="linear energy per effective component",
        amplitude_basis="Amplitude_raw (linear)",
        power_basis="sum of A^2 over usable compartments",
        normalization_scope="per note",
        physical_interpretation=(
            "Typical component energy given ACD_score. "
            "Not interpretable without ACD_score."
        ),
        not_valid_for="Using as a standalone loudness or density score.",
        ontology_family="partial_count_descriptor",
    )
    acd_hill_profile = MetricDefinition(
        name="ACD_D2",
        formula=(
            "F-059: energy-weighted compartment Hill profile "
            "D_q = (sum p_i^q)^(1/(1-q)); D1 = exp(-sum p ln p); Dinf = 1/max(p). "
            "p_i = A_i^2 / sum A^2 after ERB merge."
        ),
        input_domain="ERB-merged compartment amplitudes",
        unit_or_scale="Hill numbers and evenness D2/D0",
        amplitude_basis="Amplitude_raw (linear)",
        power_basis="energy shares",
        normalization_scope="per note (energy-weighted over compartments)",
        physical_interpretation="Hill profile of the same representation as ACD_score.",
        not_valid_for="Empty compartment (NaN, never silent 0.0).",
        ontology_family="partial_count_descriptor",
    )
    acd_score_d2_dominance = MetricDefinition(
        name="ACD_score_D2_dominance",
        formula=(
            "Diagnostic companion to F-057: sum_k r_k * D2_k after the same "
            "ERB merge. Previous headline score; retained so D2 is not lost."
        ),
        input_domain="same ACD compartments as ACD_score",
        unit_or_scale="Hill number q=2 (dominance)",
        amplitude_basis="Amplitude_raw (linear)",
        power_basis="P_i = Amplitude_raw^2",
        normalization_scope="per note, compartments energy-weighted",
        physical_interpretation=(
            "D2-based ACD. Saturates near 2.5 on a 1/n series. Diagnostic, "
            "not the headline count."
        ),
        not_valid_for="Treating as the headline component count.",
        ontology_family="partial_count_descriptor",
    )
    acd_d0_minus_d1 = MetricDefinition(
        name="ACD_D0_minus_D1",
        formula="ACD_D0 - ACD_D1 (energy-weighted compartment Hill numbers)",
        input_domain="same ACD compartments as ACD_score",
        unit_or_scale="component count (present minus effective weight)",
        amplitude_basis="Amplitude_raw (linear)",
        power_basis="energy shares",
        normalization_scope="per note",
        physical_interpretation=(
            "Components present but not carrying effective weight. "
            "Texture descriptor, not a diagnostic."
        ),
        not_valid_for="Using as a fail-closed status flag.",
        ontology_family="partial_count_descriptor",
    )
    acd_erb_merge = MetricDefinition(
        name="ACD_count_merged_harmonic",
        formula=(
            "F-060: default merge_strategy=fixed_erb_grid "
            "(bin_index = floor(erb_rate(f) / erb_fraction)); "
            "moving_centroid joins if f_next - f_centroid <= erb_fraction * ERB(f_centroid). "
            "ERB(f) = 0.108 f + 24.7; E(f) = 21.4 log10(1 + 0.00437 f). "
            "Merged A = sqrt(sum A^2). roex-overlap weighting is a stub only."
        ),
        input_domain="(frequency_hz, Amplitude_raw) pairs",
        unit_or_scale="count after merge; erb_fraction provenance",
        amplitude_basis="Amplitude_raw",
        power_basis="energy-preserving merge",
        normalization_scope="per compartment",
        physical_interpretation="Auditory-filter peak clustering before Hill numbers.",
        not_valid_for="Importing mir_descriptors 0.25*f+24.7 (not ERB).",
        ontology_family="partial_count_descriptor",
    )
    spectral_mass = MetricDefinition(
        name="spectral_mass",
        formula=(
            "F-061: spectral_mass = (ACD_D0 * ACD_score)**MASS_COUNT_BLEND "
            "* ACD_magnitude_per_component**MASS_LEVEL_EXPONENT "
            "with MASS_COUNT_BLEND=0.5 and MASS_LEVEL_EXPONENT=0.15. "
            "presence constitutes richness; loudness modulates it but must not overturn it"
        ),
        input_domain=(
            "Derived from ACD_D0, ACD_score, ACD_magnitude_per_component "
            "when ACD_status == 'ok'"
        ),
        unit_or_scale="count × bounded level (derived)",
        amplitude_basis="same ACD linear amplitudes as F-057 / F-058 (unchanged)",
        power_basis="same ACD energy shares as F-057 / F-058 (unchanged)",
        normalization_scope="per note",
        physical_interpretation=(
            "How much is sounding: compromise component count times a "
            "bounded per-component size. "
            "presence constitutes richness; loudness modulates it but must not overturn it"
        ),
        not_valid_for=(
            "Level-inclusive by design. Valid within level-controlled "
            "corpora (uniform recording conditions). Not valid for comparison across recording "
            "sessions, microphone distances, or gain settings. Decomposes exactly into "
            "spectral_mass_count and a size factor."
        ),
        ontology_family="mass_descriptor",
        formula_id="F-061",
        formula_version="1.0",
    )
    ewsd_d10_double_penalty = MetricDefinition(
        name="ewsd_weight_function_d10",
        formula=(
            "d10: D = sum(log1p(A)) * (N_eff_energy / N) then F-048 multiplies by "
            "penalty = N_eff_phi / N on log1p shares. Double anti-concentration with "
            "incompatible share definitions. Arithmetic frozen. Membership in "
            "THESIS_SAFE_WEIGHT_FUNCTIONS is an open item."
        ),
        input_domain="EWSD weight_function == d10",
        unit_or_scale="EWSD units (not commensurate with log)",
        amplitude_basis="same as F-048",
        power_basis="energy N_eff inside D; phi-weight N_eff in the penalty",
        normalization_scope="per compartment",
        physical_interpretation="Documented double correction only. Do not change the algebra.",
        not_valid_for="Cross-note comparison against log-weighted EWSD.",
        ontology_family="legacy_only",
        notes="double-corrected; open item in CHANGES.md; not recommended",
    )
    return {
        density_raw.name: density_raw,
        density_alias.name: density_alias,
        effective_partial_density.name: effective_partial_density,
        linear_sum_amplitude.name: linear_sum_amplitude,
        sethares_dissonance.name: sethares_dissonance,
        roughness_parncutt_kernel.name: roughness_parncutt_kernel,
        roughness_aures_1985.name: roughness_aures_1985,
        roughness_pairs_excluded_above_validity.name: roughness_pairs_excluded_above_validity,
        inharmonic_density_sum.name: inharmonic_density_sum,
        inharmonic_status.name: inharmonic_status,
        inharmonic_confirmed_count.name: inharmonic_confirmed_count,
        persistence_fraction.name: persistence_fraction,
        expected_false_harmonic_slots.name: expected_false_harmonic_slots,
        accepted_slots_above_body_stop.name: accepted_slots_above_body_stop,
        note_effective_component_density_ci.name: note_effective_component_density_ci,
        ci_basis_frame_count.name: ci_basis_frame_count,
        ci_basis_partial_count.name: ci_basis_partial_count,
        harmonic_slot_candidate_count.name: harmonic_slot_candidate_count,
        harmonic_validated_count.name: harmonic_validated_count,
        harmonic_validated_weak_count.name: harmonic_validated_weak_count,
        harmonic_validated_strict_count.name: harmonic_validated_strict_count,
        tolerance_continuity_override_count.name: tolerance_continuity_override_count,
        ci_resampling_unit.name: ci_resampling_unit,
        subbass_member_count.name: subbass_member_count,
        floor_rows_rejected_count.name: floor_rows_rejected_count,
        subbass_upper_bound_hz.name: subbass_upper_bound_hz,
        energy_basis.name: energy_basis,
        window_enbw_hz.name: window_enbw_hz,
        peak_power_footprint_bins.name: peak_power_footprint_bins,
        residual_exclusion_footprint_bins.name: residual_exclusion_footprint_bins,
        residual_region_hz_total.name: residual_region_hz_total,
        excluded_region_hz_total.name: excluded_region_hz_total,
        included_above_body_stop_count.name: included_above_body_stop_count,
        fft_policy.name: fft_policy,
        segment_policy.name: segment_policy,
        stable_segment_ewsd.name: stable_segment_ewsd,
        full_stable_ewsd_ratio.name: full_stable_ewsd_ratio,
        stable_segment_frames_independent.name: stable_segment_frames_independent,
        stable_segment_unrepresentative.name: stable_segment_unrepresentative,
        ewsd_primary_analysis_eligible.name: ewsd_primary_analysis_eligible,
        degenerate_partial_set.name: degenerate_partial_set,
        estimated_snr_db.name: estimated_snr_db,
        note_balanced_component_density.name: note_balanced_component_density,
        note_balanced_component_density_pool_count.name: note_balanced_component_density_pool_count,
        ewsd_score_acoustic_balanced.name: ewsd_score_acoustic_balanced,
        acd_score.name: acd_score,
        acd_magnitude.name: acd_magnitude,
        acd_hill_profile.name: acd_hill_profile,
        acd_score_d2_dominance.name: acd_score_d2_dominance,
        acd_d0_minus_d1.name: acd_d0_minus_d1,
        acd_erb_merge.name: acd_erb_merge,
        spectral_mass.name: spectral_mass,
        ewsd_d10_double_penalty.name: ewsd_d10_double_penalty,
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
