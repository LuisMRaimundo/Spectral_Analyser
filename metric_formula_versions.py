"""Per-column formula_id / formula_version stamps.

F-048 / F-049 already carried formula IDs. MIR descriptors did not, and
three incompatible F-037 generations shipped under package 4.4.0.
Every exported column now has a stamp. Bump a column's
``formula_version`` when its arithmetic changes.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

PACKAGE_FORMULA_VERSION = "4.5.0"
DISSONANCE_FORMULA_VERSION = "4.6.0"
SPECTRAL_MASS_FORMULA_VERSION = "2.0"

MIR_VALUE_COLUMNS: Tuple[str, ...] = (
    "spectral_centroid_hz",
    "spectral_spread_hz",
    "spectral_skewness",
    "spectral_kurtosis",
    "spectral_irregularity",
    "tristimulus_1_fundamental",
    "tristimulus_2_low_harmonics_2_to_4",
    "tristimulus_3_high_harmonics_5_plus",
    "spectral_flatness",
    "spectral_rolloff_hz_85",
    "spectral_rolloff_hz_95",
    "roughness_parncutt_kernel",
    "roughness_aures_1985",
    "roughness_pairs_excluded_above_validity",
    "erb_weighted_spectral_density",
)

MIR_STAMPS: Dict[str, Tuple[str, str]] = {
    "spectral_centroid_hz": ("F-027", PACKAGE_FORMULA_VERSION),
    "spectral_spread_hz": ("F-028", PACKAGE_FORMULA_VERSION),
    "spectral_skewness": ("F-029", PACKAGE_FORMULA_VERSION),
    "spectral_kurtosis": ("F-030", PACKAGE_FORMULA_VERSION),
    "spectral_irregularity": ("F-031", PACKAGE_FORMULA_VERSION),
    "tristimulus_1_fundamental": ("F-032", PACKAGE_FORMULA_VERSION),
    "tristimulus_2_low_harmonics_2_to_4": ("F-033", PACKAGE_FORMULA_VERSION),
    "tristimulus_3_high_harmonics_5_plus": ("F-034", PACKAGE_FORMULA_VERSION),
    "spectral_flatness": ("F-035", PACKAGE_FORMULA_VERSION),
    "spectral_rolloff_hz_85": ("F-036", PACKAGE_FORMULA_VERSION),
    "spectral_rolloff_hz_95": ("F-036", PACKAGE_FORMULA_VERSION),
    "roughness_parncutt_kernel": ("F-037", PACKAGE_FORMULA_VERSION),
    "roughness_aures_1985": ("F-037", PACKAGE_FORMULA_VERSION),
    "roughness_pairs_excluded_above_validity": ("F-037", PACKAGE_FORMULA_VERSION),
    "erb_weighted_spectral_density": ("F-039", PACKAGE_FORMULA_VERSION),
}

DISSONANCE_VALUE_COLUMNS: Tuple[str, ...] = (
    "sethares_dissonance",
    "hutchinson_knopoff_dissonance",
    "vassilakis_dissonance",
    "hutchinson_knopoff_legacy_mean_pair_scaled",
    "selected_dissonance_value",
    "dissonance_metric_mode",
)

DISSONANCE_STAMPS: Dict[str, Tuple[str, str]] = {
    "sethares_dissonance": ("F-062", DISSONANCE_FORMULA_VERSION),
    "hutchinson_knopoff_dissonance": ("F-063", DISSONANCE_FORMULA_VERSION),
    "vassilakis_dissonance": ("F-064", DISSONANCE_FORMULA_VERSION),
    "hutchinson_knopoff_legacy_mean_pair_scaled": (
        "COL:hutchinson_knopoff_legacy_mean_pair_scaled",
        DISSONANCE_FORMULA_VERSION,
    ),
    "selected_dissonance_value": ("F-065", DISSONANCE_FORMULA_VERSION),
    "dissonance_metric_mode": ("COL:dissonance_metric_mode", DISSONANCE_FORMULA_VERSION),
}

# Reused index IDs for citable COL: residue (not new numbers).
TRIAGE_REUSED_STAMPS: Dict[str, Tuple[str, str]] = {
    "spectral_entropy": ("F-011", PACKAGE_FORMULA_VERSION),
    "inharmonicity_coefficient_B": ("F-008", PACKAGE_FORMULA_VERSION),
    "pure_observation_w_h": ("F-023", PACKAGE_FORMULA_VERSION),
    "pure_observation_w_i": ("F-023", PACKAGE_FORMULA_VERSION),
    "pure_observation_w_s": ("F-023", PACKAGE_FORMULA_VERSION),
    "harmonic_density_weight": ("F-068", PACKAGE_FORMULA_VERSION),
    "inharmonic_density_weight": ("F-068", PACKAGE_FORMULA_VERSION),
    "subbass_density_weight": ("F-068", PACKAGE_FORMULA_VERSION),
    "odd_even_harmonic_energy_ratio": ("F-066", PACKAGE_FORMULA_VERSION),
    "low_mid_energy_ratio": ("F-067", PACKAGE_FORMULA_VERSION),
    "spectral_body_thickness_index": ("F-041", PACKAGE_FORMULA_VERSION),
    "harmonic_energy_ratio": ("F-069", PACKAGE_FORMULA_VERSION),
    "inharmonic_energy_ratio": ("F-069", PACKAGE_FORMULA_VERSION),
    "subbass_energy_ratio": ("F-069", PACKAGE_FORMULA_VERSION),
    "core_harmonic_energy_ratio": ("F-070", PACKAGE_FORMULA_VERSION),
    "core_residual_energy_ratio": ("F-070", PACKAGE_FORMULA_VERSION),
    "core_subbass_energy_ratio": ("F-070", PACKAGE_FORMULA_VERSION),
}

SPECTRAL_MASS_VALUE_COLUMNS: Tuple[str, ...] = (
    "spectral_mass",
    "spectral_mass_count",
    "spectral_mass_count_blend",
    "spectral_mass_level_exponent",
)

SPECTRAL_MASS_STAMPS: Dict[str, Tuple[str, str]] = {
    "spectral_mass": ("F-061", SPECTRAL_MASS_FORMULA_VERSION),
    "spectral_mass_count": ("F-061", SPECTRAL_MASS_FORMULA_VERSION),
    "spectral_mass_count_blend": ("F-061", SPECTRAL_MASS_FORMULA_VERSION),
    "spectral_mass_level_exponent": ("F-061", SPECTRAL_MASS_FORMULA_VERSION),
}

_INDEX_ROW = re.compile(
    r"^\|\s*(F-\d+)\s*\|.*?\| `([^`]+)`\s*\|",
    re.MULTILINE,
)
_ROOT = Path(__file__).resolve().parent


def mir_stamp_fields() -> Dict[str, str]:
    """Companion export fields for every MIR value column."""
    out: Dict[str, str] = {}
    for col, (fid, ver) in MIR_STAMPS.items():
        out[f"{col}_formula_id"] = fid
        out[f"{col}_formula_version"] = ver
    return out


def dissonance_stamp_fields() -> Dict[str, str]:
    """Companion export fields for dissonance value columns."""
    out: Dict[str, str] = {}
    for col, (fid, ver) in DISSONANCE_STAMPS.items():
        out[f"{col}_formula_id"] = fid
        out[f"{col}_formula_version"] = ver
    return out


# Citable triage columns that ship value+companion stamps on research SDM.
TRIAGE_COMPANION_VALUE_COLUMNS: Tuple[str, ...] = (
    "odd_even_harmonic_energy_ratio",
    "low_mid_energy_ratio",
    "harmonic_density_weight",
    "inharmonic_density_weight",
    "subbass_density_weight",
)


def triage_companion_stamp_fields() -> Dict[str, str]:
    """Companion stamps for F-066 / F-067 / F-068 research-export columns."""
    out: Dict[str, str] = {}
    for col in TRIAGE_COMPANION_VALUE_COLUMNS:
        fid, ver = TRIAGE_REUSED_STAMPS[col]
        out[f"{col}_formula_id"] = fid
        out[f"{col}_formula_version"] = ver
    return out


def _index_column_map() -> Dict[str, str]:
    text = (_ROOT / "docs" / "METRIC_FORMULA_INDEX.md").read_text(encoding="utf-8")
    mapping: Dict[str, str] = {}
    for fid, cols in _INDEX_ROW.findall(text):
        for col in re.split(r"[,/]| and ", cols):
            name = col.strip().strip("`")
            if name and not name.startswith("*"):
                mapping.setdefault(name, fid)
    return mapping


def _contract_stamps() -> Dict[str, Tuple[str, str]]:
    from metric_contract import build_metric_contracts

    out: Dict[str, Tuple[str, str]] = {}
    for name, definition in build_metric_contracts().items():
        fid = str(getattr(definition, "formula_id", "") or "").strip()
        ver = str(getattr(definition, "formula_version", "") or "").strip()
        if not fid:
            found = re.findall(r"F-\d+", definition.formula)
            fid = found[0] if found else f"COL:{name}"
        if not ver:
            ver = PACKAGE_FORMULA_VERSION
        out[name] = (fid, ver)
    return out


def exported_column_names() -> List[str]:
    from compile_metrics import DENSITY_METRICS_MAIN_COLUMNS, PHASE5_ALL_DESCRIPTOR_COLUMNS

    names = list(DENSITY_METRICS_MAIN_COLUMNS)
    for col in PHASE5_ALL_DESCRIPTOR_COLUMNS:
        if col not in names:
            names.append(col)
    for col in MIR_VALUE_COLUMNS:
        if col not in names:
            names.append(col)
        names.append(f"{col}_formula_id")
        names.append(f"{col}_formula_version")
    for col in DISSONANCE_VALUE_COLUMNS:
        if col not in names:
            names.append(col)
        names.append(f"{col}_formula_id")
        names.append(f"{col}_formula_version")
    for col in SPECTRAL_MASS_VALUE_COLUMNS:
        if col not in names:
            names.append(col)
    names.append("spectral_mass_formula_id")
    names.append("spectral_mass_formula_version")
    for col in TRIAGE_COMPANION_VALUE_COLUMNS:
        if col not in names:
            names.append(col)
        names.append(f"{col}_formula_id")
        names.append(f"{col}_formula_version")
    return names


def column_stamp(column: str) -> Tuple[str, str]:
    if column in MIR_STAMPS:
        return MIR_STAMPS[column]
    if column in DISSONANCE_STAMPS:
        return DISSONANCE_STAMPS[column]
    if column in SPECTRAL_MASS_STAMPS:
        return SPECTRAL_MASS_STAMPS[column]
    if column in TRIAGE_REUSED_STAMPS:
        return TRIAGE_REUSED_STAMPS[column]
    base = mir_segment_base(column)
    if (
        base != column
        and base in MIR_STAMPS
        and not column.startswith("roughness_aures_1985")
    ):
        return MIR_STAMPS[base]
    if column.endswith("_formula_id"):
        return ("META", PACKAGE_FORMULA_VERSION)
    if column.endswith("_formula_version"):
        return ("META", PACKAGE_FORMULA_VERSION)
    contracts = _contract_stamps()
    if column in contracts:
        return contracts[column]
    index = _index_column_map()
    if column in index:
        return (index[column], PACKAGE_FORMULA_VERSION)
    return (f"COL:{column}", PACKAGE_FORMULA_VERSION)


SURFACE_CLASSES = ("metric", "diagnostic", "metadata", "provenance", "deprecated")

# Segment suffix is a convention, not a new formula. Check the longer
# ``sustain_segment`` token before ``sustain``.
_MIR_SEGMENT_SUFFIXES: Tuple[str, ...] = (
    "_on_attack",
    "_on_release",
    "_on_sustain_segment",
    "_on_sustain",
)

# The 202 class-metric COL: residue from CLEANUP_REPO_HYGIENE_REPORT.md §3.
TRIAGE_COL_METRIC_202: Tuple[str, ...] = (
    "Soma_A_linear_harmonicos",
    "Soma_A_linear_inarmonicos",
    "Soma_A_linear_subbass",
    "Soma_A_linear_total",
    "bin_to_f0_ratio",
    "body_weighted_effective_density",
    "canonical_density_v5_adapted",
    "component_strength_h",
    "component_strength_i",
    "component_strength_s",
    "core_harmonic_energy_ratio",
    "core_residual_energy_ratio",
    "core_subbass_energy_ratio",
    "density_confidence",
    "density_effective_ceiling_hz",
    "density_fragile",
    "density_frequency_ceiling_hz",
    "density_metric_per_harmonic",
    "density_normalization_denominator",
    "density_normalization_scope",
    "density_normalized_global",
    "density_per_component",
    "density_perturbation_spread_pct",
    "density_salience_threshold_db",
    "density_source_formula",
    "density_summation_mode",
    "detected_harmonic_slot_count",
    "detected_salient_harmonic_order_count_up_to_body_ceiling",
    "diagnostic_effective_components_h",
    "diagnostic_effective_components_r",
    "diagnostic_effective_components_s",
    "discrete_metric_d10",
    "discrete_metric_d17",
    "discrete_metric_d24",
    "discrete_metric_d3",
    "dissonance_metric_mode",
    "effective_components_weighted_diagnostic",
    "effective_partial_density",
    "erb_weighted_spectral_density_on_attack",
    "erb_weighted_spectral_density_on_release",
    "erb_weighted_spectral_density_on_sustain",
    "erb_weighted_spectral_density_on_sustain_segment",
    "estimated_snr_db",
    "expected_harmonic_order_count_up_to_body_ceiling",
    "expected_harmonic_order_count_up_to_density_ceiling_hz",
    "expected_harmonic_slot_count",
    "expected_harmonic_slots_up_to_body_ceiling",
    "f0_confidence",
    "f0_final_source",
    "f0_used_for_density_source",
    "final_note_density_count_based",
    "final_note_density_salience_weighted",
    "harmonic_assignment_confidence",
    "harmonic_body_density",
    "harmonic_body_density_normalized",
    "harmonic_body_stop_hz",
    "harmonic_body_stop_order",
    "harmonic_candidate_count_20khz",
    "harmonic_density_component",
    "harmonic_density_component_on_attack",
    "harmonic_density_component_on_release",
    "harmonic_density_component_on_sustain",
    "harmonic_density_weight",
    "harmonic_effective_power_component_count",
    "harmonic_effective_power_density",
    "harmonic_effective_power_density_component_count",
    "harmonic_effective_power_density_normalized",
    "harmonic_effective_power_density_normalized_by_harmonic_count",
    "harmonic_effective_power_mass",
    "harmonic_effective_power_mean",
    "harmonic_effective_power_rms",
    "harmonic_energy_ratio",
    "harmonic_energy_sum",
    "harmonic_energy_sum_tier_normalized",
    "harmonic_occupancy_detected_order_count",
    "harmonic_order_count",
    "harmonic_region_occupancy_count",
    "harmonic_slot_coverage_ratio",
    "harmonic_slot_expected_count",
    "harmonic_slot_matched_count",
    "hutchinson_knopoff_dissonance",
    "inharmonic_density_component",
    "inharmonic_density_component_on_attack",
    "inharmonic_density_component_on_release",
    "inharmonic_density_component_on_sustain",
    "inharmonic_density_weight",
    "inharmonic_energy_ratio",
    "inharmonic_energy_sum",
    "inharmonic_energy_sum_tier_normalized",
    "inharmonicity_coefficient_B",
    "inharmonicity_fit_method",
    "inharmonicity_fit_residual_std_cents",
    "inharmonicity_fit_source",
    "inharmonicity_model_applied",
    "linear_amplitude_batch_alignment_factor",
    "linear_amplitude_fraction_inharmonic_of_HI",
    "linear_amplitude_fraction_nonharmonic_of_total",
    "linear_sum_amplitude_harmonic",
    "linear_sum_amplitude_inharmonic_partial",
    "linear_sum_amplitude_subbass_band",
    "low_mid_energy_ratio",
    "mir_descriptors_available",
    "mir_descriptors_missing_reason",
    "mir_descriptors_source",
    "odd_even_harmonic_energy_ratio",
    "outlier_policy_applied",
    "outlier_ratio_max_to_mean",
    "probable_harmonic_component_count_body_ceiling",
    "probable_harmonic_component_energy_sum_body_ceiling",
    "pure_observation_w_h",
    "pure_observation_w_i",
    "pure_observation_w_s",
    "residual_body_contribution",
    "residual_body_contribution_capped",
    "rolloff_compensated_harmonic_density",
    "rolloff_compensated_harmonic_density_alpha",
    "rolloff_compensated_harmonic_density_component_count",
    "rolloff_harmonic_partial_count",
    "roughness_aures_1985_on_attack",
    "roughness_aures_1985_on_release",
    "roughness_aures_1985_on_sustain",
    "roughness_aures_1985_on_sustain_segment",
    "roughness_parncutt_kernel_on_attack",
    "roughness_parncutt_kernel_on_release",
    "roughness_parncutt_kernel_on_sustain",
    "roughness_parncutt_kernel_on_sustain_segment",
    "salient_even_harmonic_count_up_to_body_ceiling",
    "salient_harmonic_coverage_ratio_up_to_body_ceiling",
    "salient_harmonic_coverage_up_to_body_ceiling",
    "salient_harmonic_coverage_up_to_density_ceiling_hz",
    "salient_harmonic_mass_up_to_body_ceiling",
    "salient_harmonic_mass_up_to_density_ceiling_hz",
    "salient_harmonic_order_count_up_to_body_ceiling",
    "salient_harmonic_order_count_up_to_density_ceiling_hz",
    "salient_inharmonic_log_bin_count_up_to_body_ceiling",
    "salient_inharmonic_log_bin_count_up_to_density_ceiling_hz",
    "salient_odd_harmonic_count_up_to_body_ceiling",
    "salient_subbass_particle_count",
    "salient_subbass_particle_count_up_to_density_ceiling_hz",
    "selected_dissonance_value",
    "sethares_dissonance",
    "spectral_body_thickness_index",
    "spectral_centroid_hz_on_attack",
    "spectral_centroid_hz_on_release",
    "spectral_centroid_hz_on_sustain",
    "spectral_centroid_hz_on_sustain_segment",
    "spectral_entropy",
    "spectral_flatness_on_attack",
    "spectral_flatness_on_release",
    "spectral_flatness_on_sustain",
    "spectral_flatness_on_sustain_segment",
    "spectral_irregularity_on_attack",
    "spectral_irregularity_on_release",
    "spectral_irregularity_on_sustain",
    "spectral_irregularity_on_sustain_segment",
    "spectral_kurtosis_on_attack",
    "spectral_kurtosis_on_release",
    "spectral_kurtosis_on_sustain",
    "spectral_kurtosis_on_sustain_segment",
    "spectral_rolloff_hz_85_on_attack",
    "spectral_rolloff_hz_85_on_release",
    "spectral_rolloff_hz_85_on_sustain",
    "spectral_rolloff_hz_85_on_sustain_segment",
    "spectral_rolloff_hz_95_on_attack",
    "spectral_rolloff_hz_95_on_release",
    "spectral_rolloff_hz_95_on_sustain",
    "spectral_rolloff_hz_95_on_sustain_segment",
    "spectral_skewness_on_attack",
    "spectral_skewness_on_release",
    "spectral_skewness_on_sustain",
    "spectral_skewness_on_sustain_segment",
    "spectral_spread_hz_on_attack",
    "spectral_spread_hz_on_release",
    "spectral_spread_hz_on_sustain",
    "spectral_spread_hz_on_sustain_segment",
    "spectral_stability_confidence",
    "subbass_density_component",
    "subbass_density_component_on_attack",
    "subbass_density_component_on_release",
    "subbass_density_component_on_sustain",
    "subbass_density_weight",
    "subbass_energy_ratio",
    "subbass_energy_sum",
    "subbass_energy_sum_tier_normalized",
    "theoretical_harmonic_order_count_up_to_body_ceiling",
    "total_component_energy",
    "tristimulus_1_fundamental_on_attack",
    "tristimulus_1_fundamental_on_release",
    "tristimulus_1_fundamental_on_sustain",
    "tristimulus_1_fundamental_on_sustain_segment",
    "tristimulus_2_low_harmonics_2_to_4_on_attack",
    "tristimulus_2_low_harmonics_2_to_4_on_release",
    "tristimulus_2_low_harmonics_2_to_4_on_sustain",
    "tristimulus_2_low_harmonics_2_to_4_on_sustain_segment",
    "tristimulus_3_high_harmonics_5_plus_on_attack",
    "tristimulus_3_high_harmonics_5_plus_on_release",
    "tristimulus_3_high_harmonics_5_plus_on_sustain",
    "tristimulus_3_high_harmonics_5_plus_on_sustain_segment",
    "valid_for_primary_statistics",
    "validated_harmonic_component_count_body_ceiling",
    "validated_harmonics_above_body_stop_count",
    "vassilakis_dissonance",
)

_TRIAGE_PROVENANCE = frozenset(
    {
        "density_source_formula",
        "density_summation_mode",
        "density_normalization_scope",
        "density_normalization_denominator",
        "density_salience_threshold_db",
        "density_frequency_ceiling_hz",
        "density_effective_ceiling_hz",
        "outlier_policy_applied",
        "f0_final_source",
        "f0_used_for_density_source",
        "inharmonicity_fit_method",
        "inharmonicity_fit_source",
        "inharmonicity_model_scope",
        "harmonic_assignment_method",
        "mir_descriptors_source",
        "mir_descriptors_missing_reason",
        "dissonance_metric_mode",
        "linear_amplitude_batch_alignment_factor",
    }
)
_TRIAGE_DIAGNOSTIC_EXPLICIT = frozenset(
    {
        "density_fragile",
        "density_confidence",
        "f0_confidence",
        "harmonic_assignment_confidence",
        "spectral_stability_confidence",
        "mir_descriptors_available",
        "valid_for_primary_statistics",
        "inharmonicity_model_applied",
        "fit_converged",
        "outlier_ratio_max_to_mean",
        "estimated_snr_db",
        "density_perturbation_spread_pct",
        "bin_to_f0_ratio",
        "inharmonicity_fit_residual_std_cents",
    }
)
_TRIAGE_DEPRECATED = frozenset(
    {
        "roughness_aures_1985_on_attack",
        "roughness_aures_1985_on_release",
        "roughness_aures_1985_on_sustain",
        "roughness_aures_1985_on_sustain_segment",
        "canonical_density_v5_adapted",
        "body_weighted_effective_density",
        "final_note_density_count_based",
        "final_note_density_salience_weighted",
        "effective_partial_density",
        "density_metric_per_harmonic",
        "density_normalized_global",
        "density_per_component",
        "rolloff_compensated_harmonic_density",
        "rolloff_compensated_harmonic_density_alpha",
        "rolloff_compensated_harmonic_density_component_count",
        "rolloff_harmonic_partial_count",
        "discrete_metric_d10",
        "Soma_A_linear_harmonicos",
        "Soma_A_linear_inarmonicos",
        "Soma_A_linear_subbass",
        "Soma_A_linear_total",
    }
)
# Closed 2026-08-22 (see docs/validation/COLUMN_TRIAGE_DECISIONS.md).
TRIAGE_DECISION_PENDING: frozenset = frozenset()
_TRIAGE_DIAGNOSTIC_EXACT = frozenset(
    {
        "harmonic_order_count",
        "harmonic_candidate_count_20khz",
        "component_strength_h",
        "component_strength_i",
        "component_strength_s",
        "diagnostic_effective_components_h",
        "diagnostic_effective_components_r",
        "diagnostic_effective_components_s",
        "effective_components_weighted_diagnostic",
        "total_component_energy",
        "discrete_metric_d3",
        "discrete_metric_d17",
        "discrete_metric_d24",
        "harmonic_body_density",
        "harmonic_body_density_normalized",
        "harmonic_body_stop_hz",
        "harmonic_body_stop_order",
    }
)
_TRIAGE_DIAGNOSTIC_PREFIXES: Tuple[str, ...] = (
    "salient_",
    "expected_",
    "detected_",
    "theoretical_",
    "validated_",
    "probable_",
    "harmonic_slot_",
    "harmonic_occupancy_",
    "harmonic_region_",
    "harmonic_effective_power_",
    "harmonic_density_component",
    "inharmonic_density_component",
    "subbass_density_component",
    "harmonic_energy_sum",
    "inharmonic_energy_sum",
    "subbass_energy_sum",
    "linear_sum_amplitude_",
    "linear_amplitude_fraction_",
    "residual_body_contribution",
)

_DEPRECATED_NAMES = frozenset(
    {
        "density_weighted_sum",
        "density_weighted_sum_cdm_mean",
        "Combined Density Metric",
        "Density Metric",
        "Total Metric",
        "energy_weighted_component_density_diagnostic",
        "hutchinson_knopoff_legacy_mean_pair_scaled",
        "roughness_aures_1985",
        "note_balanced_component_density",
        "smoothed_w_h_legacy",
        "smoothed_w_i_legacy",
        "smoothed_w_s_legacy",
        "ewsd_weight_function_d10",
    }
)
_PROVENANCE_NAMES = frozenset(
    {
        "package_version",
        "code_commit",
        "code_dirty",
        "analysis_version",
        "git_commit",
        "git_describe",
        "git_status_reason",
        "ACD_version",
        "ewsd_stage3_version",
        "ACD_erb_fraction",
        "ACD_merge_strategy",
        "export_schema_version",
        "density_formula_version",
        "obs_w_formula_version",
    }
)
_METADATA_NAMES = frozenset(
    {
        "Note",
        "MIDI",
        "Instrument",
        "Technique",
        "Dynamic",
        "Register",
        "Pitch_Class",
        "Octave",
        "sample_id",
        "source_file_name",
        "source_file",
    }
)


def mir_segment_base(name: str) -> str:
    """Strip ``_on_{attack,release,sustain,sustain_segment}`` if present."""
    for suffix in _MIR_SEGMENT_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def classify_export_column(name: str, formula_id: str = "") -> str:
    """Assign ``metric|diagnostic|metadata|provenance|deprecated``."""
    low = str(name).lower()
    if (
        name in _DEPRECATED_NAMES
        or name in _TRIAGE_DEPRECATED
        or "legacy" in low
        or low.endswith("_cdm_mean")
    ):
        return "deprecated"
    if (
        name in _PROVENANCE_NAMES
        or name in _TRIAGE_PROVENANCE
        or formula_id == "META"
        or low.endswith("_formula_id")
        or low.endswith("_formula_version")
    ):
        return "provenance"
    if name in _METADATA_NAMES or low.endswith("_file") or low.endswith("_chart_file"):
        return "metadata"
    if (
        name in _TRIAGE_DIAGNOSTIC_EXPLICIT
        or name in _TRIAGE_DIAGNOSTIC_EXACT
        or any(name.startswith(prefix) for prefix in _TRIAGE_DIAGNOSTIC_PREFIXES)
    ):
        return "diagnostic"
    if any(
        tok in low
        for tok in (
            "_ci_",
            "rel_uncertainty",
            "_status",
            "_flag",
            "eligible",
            "warning",
            "debug_counts",
            "bootstrap",
            "pairs_excluded",
            "uncertainty_sources",
        )
    ) or name in {
        "ACD_score_D2_dominance",
        "ACD_D2",
        "ACD_Dinf",
        "ACD_evenness_D2_over_D0",
    }:
        return "diagnostic"
    return "metric"


def build_column_registry() -> Dict[str, Dict[str, str]]:
    registry: Dict[str, Dict[str, str]] = {}
    for col in exported_column_names():
        fid, ver = column_stamp(col)
        registry[col] = {
            "formula_id": fid,
            "formula_version": ver,
            "class": classify_export_column(col, fid),
        }
    return registry


def write_column_surface_dictionary(path: Path | None = None) -> Path:
    """Persist per-column surface class into ``metrics_dictionary.json``."""
    dest = path or (_ROOT / "metrics_dictionary.json")
    payload = json.loads(dest.read_text(encoding="utf-8"))
    registry = build_column_registry()
    payload["column_surface"] = {
        name: {
            "class": row["class"],
            "formula_id": row["formula_id"],
            "formula_version": row["formula_version"],
        }
        for name, row in registry.items()
    }
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest


def write_audit_markdown(path: Path | None = None) -> Path:
    registry = build_column_registry()
    dest = path or (_ROOT / "docs" / "validation" / "COLUMN_VERSIONING_AUDIT.md")
    lacked = [
        name
        for name, row in registry.items()
        if row["formula_id"].startswith("COL:")
    ]
    lines = [
        "# Column formula-version audit",
        "",
        f"Package formula-version generation: **{PACKAGE_FORMULA_VERSION}**.",
        "Before this generation, only a few fields (`density_formula_version`,",
        "`obs_w_formula_version`, EWSD/ACD formula-ID strings) carried a",
        "per-column version. MIR descriptors, including three incompatible",
        "F-037 kernels, shipped under `package_version=4.4.0` with no",
        "per-column stamp.",
        "",
        f"- Exported columns inventoried: **{len(registry)}**",
        f"- Columns that lacked a contracted F-id (first-stamped as `COL:<name>`): "
        f"**{len(lacked)}**",
        "- MIR value columns now export `<name>_formula_id` and",
        "  `<name>_formula_version` from `metric_contract` / `MIR_STAMPS`.",
        "- CI: `tests/phase_33/test_column_formula_versions.py` fails if any",
        "  compiled/MIR export column is missing a non-empty stamp.",
        "",
        "A `COL:<name>` id is a first-generation stamp, not a claim that the",
        "column has a numbered formula in `METRIC_FORMULA_INDEX.md`. Bump",
        "`formula_version` when that column's arithmetic changes.",
        "",
        "## Registry",
        "",
        "| Column | formula_id | formula_version |",
        "|---|---|---|",
    ]
    for name in sorted(registry):
        row = registry[name]
        lines.append(
            f"| `{name}` | `{row['formula_id']}` | `{row['formula_version']}` |"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sidecar = dest.with_suffix(".json")
    sidecar.write_text(
        json.dumps(
            {"package_formula_version": PACKAGE_FORMULA_VERSION, "columns": registry},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return dest
