# Export Column Dictionary

**Package version:** 4.2.0. Export schema repairs: `docs/validation/EXPORT_SCHEMA_AUDIT_REPAIR.md`.
Normative export rules: `docs/DENSITY_EXPORT_SCHEMA.md` §R.6–R.10. Implementation manual: `docs/TECHNICAL_MANUAL_COMPLETE.md` §5.2.1 and §14.3.
Export schema version: `spectral_analysis_schema_2026_08`.

This dictionary covers exported workbook sheets for:

- `compiled_density_metrics.xlsx` (Stage 2 compile),
- `compiled_density_metrics_research.xlsx` (research post-export).

For compactness and auditability:

1. each sheet has an **exhaustive column-name list** (all exported names in current code path);
2. key interpretation rows are provided in table format;
3. legacy/debug-only fields are explicitly tagged.

**Per-note fatness lookup:** read `note_effective_component_density` on `Density_Metrics` — see
`docs/validation/NOTE_FATNESS_AND_DENSITY_GUIDE.md`.

### Column-name traps (v4.0.3 — same header, different meaning)

| Column | Where | Meaning |
|--------|-------|---------|
| `density_weighted_sum` | compiled | Alias of per-note balance density (`density_metric_raw_per_note_balance`) |
| `density_weighted_sum` | research `Spectral_Density_Metrics` | Body-ceiling richness (`richness_weighted_body_density_*`) |
| `harmonic_density_weight` | research `Metadata` | Phase-2 corpus weight (H/I/S distinct since v4.0.3) |
| `harmonic_density_weight` | `Analysis_Settings_By_Note` | GUI base multiplier (1 / 0.5 / 0.25), **not** Phase-2 |
| `harmonic_density_weight` | research main sheet | Per-note ratio-derived column, **not** Phase-2 |

Full table: `docs/DENSITY_EXPORT_SCHEMA.md` §R.8. Low-f₀ Stage 1 columns: §R.9.
Re-export guidance: `docs/validation/EXPORT_SCHEMA_AUDIT_REPAIR.md` § Re-export required.

### Per-note v4.1.0 identity columns (`spectral_analysis.xlsx` Metrics / Analysis_Metadata)

Provenance (Phase E): `analysis_version` is package metadata + `git describe --always --dirty`. Companion fields `package_version`, `code_commit`, `code_dirty`, `git_describe` sit on `Analysis_Metadata` and research `Stage3_Summary`. `export_schema_version` is the single `analysis_policy` token. Use `python verify_export.py <workbook>` for comparability. Default φ is `log` (`DENSITY_WEIGHT_FUNCTION_DEFAULT`); `weight_function` is on Stage 1/2/3 rows and inside `analysis_parameter_profile_id`. A corpus run writes `run_manifest.json` (Phase H) with commit, constants hash, profile id, input SHA-256 hashes, and wall time.

| Column | Meaning |
|--------|---------|
| `f0_fit_discrepancy_cents` | `1200 log2(f0_refit / f0_joint)` |
| `f0_refit_applied`, `f0_refit_hz` | Low-order H1–H8 refit used as match centre |
| `harmonic_body_stop_hz` | Validation/count cut |
| `density_effective_ceiling_hz` | Global 20 kHz ceiling |
| `density_fragile` | CI or ±10 ms perturbation > 10 % |
| `tolerance_limb` | `cents` / `spacing_cap` / `bin_floor` (Harmonic Spectrum) |
| `sample_note_tag` / `sample_id` | Take identity on per-row partial sheets |
| `partial_pitch_name` | Nearest pitch + cents of that partial |
| `harmonic_slot_candidate_count` | Matching diagnostic (legacy name: `harmonic_slot_matched_count`) |
| `harmonic_validated_count` | `include_for_density = TRUE` count |
| `effective_partial_density` / `linear_sum_amplitude_*` | Validated partials only; ungated copies `*_ungated` |
| `inharmonic_status` | Confirmation outcome on residual candidates (Phase A) |
| `cfar_detected_i` / `cfar_margin_db_i` | F-043 on the residual candidate (same `P_fa` as harmonics) |
| `local_peak_valid_i` / `prominence_db_i` | Local maximum + saddle prominence ≥ 6 dB |
| `temporal_persistence_i` / `persistence_fraction` | Sustain-frame persistence (Phase B) |
| `frequency_jitter_cents` / `magnitude_jitter_db` | Std of per-frame frequency (cents) and magnitude (dB) |
| `sustain_frame_count` | STFT frames covering the sustain (or whole file) |
| `sustain_frame_count_independent` | `sustain_frame_count / (n_fft / hop)` |
| `hop_duration_s` | Hop period `hop_length / sr` |
| `window_duration_s` | Analysis window `n_fft / sr` |
| `frame_duration_s` | Deprecated alias of `hop_duration_s` (`deprecated_alias_of: hop_duration_s`) |
| `harmonic_validated_weak_count` | `validated_weak` rows (weak CFAR margin, persistence ≥ 0.9) |
| `harmonic_validated_strict_count` | `harmonic_validated_count` minus the weak class |
| `tolerance_continuity_override_count` | Isolated cap misses re-included by neighbour continuity |
| `subbass_bound_formula` / `subbass_bound_f0_used_hz` | F-020 `min(0.5*f0, 80)` and the f0 used |
| `ci_resampling_unit` / `ci_n_resampled` / `ci_bootstrap_iterations` / `ci_seed` | What the CI resamples (estimator unchanged) |
| `ci_width_flag` / `ci_width_note` | `wide` when relative width > 25 %; cause `low_independent_frames` and/or `high_partial_correlation` |
| `not_leakage_i` / `leakage_guarding_harmonic_order` | Outside accepted-harmonic main-lobe/sidelobe footprint |
| `not_stretched_harmonic_i` | Outside F-007 comb when stretch is applied |
| `inharmonic_confirmed_count` | Count of `confirmed_inharmonic_partial` rows |
| `subbass_upper_bound_hz` | F-020 ceiling `min(0.5 f0, 80)` |
| `subbass_member_count` | Sub-bass rows with `subbass_membership = subbass_member` |
| `floor_rows_rejected_count` | Residual candidates with `inharmonic_status = rejected_floor` |
| `subbass_membership` | `subbass_member` or `lf_diagnostic_not_member` on the Sub-bass sheet |
| `expected_false_harmonic_slots` | `harmonic_slot_expected_count × CFAR_PFA` (budget, not a count) |
| `accepted_slots_above_body_stop` | Included slots above the body stop; must be 0 after gating |
| `included_above_body_stop_count` | Same invariant as `accepted_slots_above_body_stop` (must be 0) |
| `validated_harmonics_above_body_stop_count` | CFAR-validated (or include-true) then excluded by the body stop; **not** included |
| `energy_basis` | `psd_per_hz` after D6; pre-fix per-bin workbooks are not comparable |
| `window_enbw_hz` | Window equivalent noise bandwidth (Hz) |
| `peak_footprint_bins` | ENBW in bins used for the peak-power estimate (alias of `peak_power_footprint_bins`) |
| `peak_power_footprint_bins` | ENBW in bins used for the peak-power estimate only |
| `residual_exclusion_footprint_bins` | Main-lobe diameter in bins used to keep skirts out of the residual (BH-4 = 8) |
| `residual_region_hz_total` | One-sided Hz remaining after exclusion-footprint union |
| `excluded_region_hz_total` | One-sided Hz removed by the exclusion footprints |
| `analysis_band_hz` | `f_max − f_min`; invariant: residual + excluded == analysis band |
| `fft_policy` | `fixed` (default, comparable) or `adaptive_tier` |
| `segment_policy` | Always `sustain_primary_stable_diagnostic` (WP3). Primary = sustain cut |
| `stable_segment_ewsd` | EWSD of the stable sibling. NaN if missing (`nan_not_zero_v1`) |
| `full_stable_ewsd_ratio` | `full_ewsd / stable_ewsd`. Flagged when > 1.3 |
| `stable_segment_frames_independent` | Independent-frame count of the stable sibling. NaN if missing |
| `stable_segment_unrepresentative` | True when EWSD ratio > 1.3 or centroid ratio > 2.0. Flag only |
| `ewsd_primary_analysis_eligible` | False when independent frames < 8 or `harmonic_validated_count ≤ 2` |
| `degenerate_partial_set` | True when `harmonic_validated_count ≤ 2`. CI is NaN, never 0.0 |
| `harmonic_acceptance_suspect` | Accepted count exceeds body-stop order + expected false slots |
| `cfar_marginal_count` | Rows with `0 ≤ cfar_margin_db < HARMONIC_MIN_CFAR_MARGIN_DB` |

`Inharmonic Spectrum` keeps every candidate. `Confirmed_Inharmonic_Partials`
is the survivor sheet. Only `*_validated_count` / `*_confirmed_count` are
partial counts. `harmonic_slot_candidate_count`, `subbass_member_count`,
and `floor_rows_rejected_count` are diagnostics, not partial counts.

---

## 1) Compiled workbook (`compiled_density_metrics.xlsx`)

## 1.1 `Density_Metrics` (exhaustive canonical slim export list)

Columns (exact names):

`Note`, `density_metric_raw`, `energy_weighted_component_density_diagnostic`, `density_metric_normalized`, `weighted_harmonic_density_contribution`, `weighted_inharmonic_density_contribution`, `weighted_subbass_density_contribution`, `component_harmonic_energy_ratio`, `component_inharmonic_energy_ratio`, `component_subbass_energy_ratio`, `density_metric_raw_per_note_balance`, `density_weights_source`, `acoustic_f0_status`, `f0_used_for_density_source`, `harmonic_occupancy_detected_order_count`, `expected_harmonic_slot_count`, `detected_harmonic_slot_count`, `harmonic_slot_expected_count`, `harmonic_slot_matched_count`, `harmonic_slot_coverage_ratio`, `body_weighted_effective_density`, `low_mid_energy_ratio`, `harmonic_body_density`, `harmonic_body_density_normalized`, `residual_body_contribution_capped`, `spectral_body_thickness_index`, `salient_harmonic_order_count_up_to_body_ceiling`, `expected_harmonic_order_count_up_to_body_ceiling`, `salient_harmonic_coverage_up_to_body_ceiling`, `salient_harmonic_mass_up_to_body_ceiling`, `salient_harmonic_order_count_up_to_density_ceiling_hz`, `expected_harmonic_order_count_up_to_density_ceiling_hz`, `salient_harmonic_coverage_up_to_density_ceiling_hz`, `salient_harmonic_mass_up_to_density_ceiling_hz`, `salient_odd_harmonic_count_up_to_body_ceiling`, `salient_even_harmonic_count_up_to_body_ceiling`, `odd_even_harmonic_energy_ratio`, `salient_inharmonic_log_bin_count_up_to_body_ceiling`, `salient_subbass_particle_count`, `salient_inharmonic_log_bin_count_up_to_density_ceiling_hz`, `salient_subbass_particle_count_up_to_density_ceiling_hz`, `final_note_density_count_based`, `final_note_density_salience_weighted`, `note_density_final`, `harmonic_density_component`, `inharmonic_density_component`, `subbass_density_component`, `harmonic_density_weight`, `inharmonic_density_weight`, `subbass_density_weight`, `density_summation_mode`, `density_salience_threshold_db`, `density_frequency_ceiling_hz`, `core_harmonic_energy_ratio`, `core_residual_energy_ratio`, `core_subbass_energy_ratio`, `harmonic_effective_power_density_normalized`, `Harmonic Partials sum`, `Inharmonic Partials sum`, `Sub-bass sum`, `harmonic_amplitude_sum`, `harmonic_amplitude_sum_tier_normalized`, `inharmonic_amplitude_sum`, `inharmonic_amplitude_sum_tier_normalized`, `subbass_amplitude_sum`, `subbass_amplitude_sum_tier_normalized`, `harmonic_energy_sum_tier_normalized`, `inharmonic_energy_sum_tier_normalized`, `subbass_energy_sum_tier_normalized`, `tier_consistency_status`, `Total sum`, `source_file_name`, `weight_function`, `density_extraction_status`, `density_component_basis`, `density_weight_basis`, `harmonic_spectrum_source`, `inharmonic_spectrum_source`, `subbass_spectrum_source`, `harmonic_spectrum_count`, `inharmonic_spectrum_count`, `subbass_spectrum_count`, `spectral_centroid_hz`, `spectral_spread_hz`, `spectral_skewness`, `spectral_kurtosis`, `spectral_irregularity`, `tristimulus_1_fundamental`, `tristimulus_2_low_harmonics_2_to_4`, `tristimulus_3_high_harmonics_5_plus`, `spectral_flatness`, `spectral_rolloff_hz_85`, `spectral_rolloff_hz_95`, `roughness_aures_1985`, `erb_weighted_spectral_density`, `spectral_centroid_hz_on_sustain_segment`, `spectral_spread_hz_on_sustain_segment`, `spectral_skewness_on_sustain_segment`, `spectral_kurtosis_on_sustain_segment`, `spectral_irregularity_on_sustain_segment`, `tristimulus_1_fundamental_on_sustain_segment`, `tristimulus_2_low_harmonics_2_to_4_on_sustain_segment`, `tristimulus_3_high_harmonics_5_plus_on_sustain_segment`, `spectral_flatness_on_sustain_segment`, `spectral_rolloff_hz_85_on_sustain_segment`, `spectral_rolloff_hz_95_on_sustain_segment`, `roughness_aures_1985_on_sustain_segment`, `erb_weighted_spectral_density_on_sustain_segment`, `spectral_centroid_hz_on_attack`, `spectral_centroid_hz_on_sustain`, `spectral_centroid_hz_on_release`, `spectral_spread_hz_on_attack`, `spectral_spread_hz_on_sustain`, `spectral_spread_hz_on_release`, `spectral_skewness_on_attack`, `spectral_skewness_on_sustain`, `spectral_skewness_on_release`, `spectral_kurtosis_on_attack`, `spectral_kurtosis_on_sustain`, `spectral_kurtosis_on_release`, `spectral_irregularity_on_attack`, `spectral_irregularity_on_sustain`, `spectral_irregularity_on_release`, `tristimulus_1_fundamental_on_attack`, `tristimulus_1_fundamental_on_sustain`, `tristimulus_1_fundamental_on_release`, `tristimulus_2_low_harmonics_2_to_4_on_attack`, `tristimulus_2_low_harmonics_2_to_4_on_sustain`, `tristimulus_2_low_harmonics_2_to_4_on_release`, `tristimulus_3_high_harmonics_5_plus_on_attack`, `tristimulus_3_high_harmonics_5_plus_on_sustain`, `tristimulus_3_high_harmonics_5_plus_on_release`, `spectral_flatness_on_attack`, `spectral_flatness_on_sustain`, `spectral_flatness_on_release`, `spectral_rolloff_hz_85_on_attack`, `spectral_rolloff_hz_85_on_sustain`, `spectral_rolloff_hz_85_on_release`, `spectral_rolloff_hz_95_on_attack`, `spectral_rolloff_hz_95_on_sustain`, `spectral_rolloff_hz_95_on_release`, `roughness_aures_1985_on_attack`, `roughness_aures_1985_on_sustain`, `roughness_aures_1985_on_release`, `erb_weighted_spectral_density_on_attack`, `erb_weighted_spectral_density_on_sustain`, `erb_weighted_spectral_density_on_release`, `harmonic_density_component_on_attack`, `harmonic_density_component_on_sustain`, `harmonic_density_component_on_release`, `inharmonic_density_component_on_attack`, `inharmonic_density_component_on_sustain`, `inharmonic_density_component_on_release`, `subbass_density_component_on_attack`, `subbass_density_component_on_sustain`, `subbass_density_component_on_release`, `inharmonicity_coefficient_B`, `inharmonicity_fit_residual_std_cents`, `inharmonicity_fit_status`, `inharmonicity_fit_method`, `inharmonicity_model_applied`, `inharmonicity_fit_source`, `inharmonicity_validation_warning`, `mir_descriptors_available`, `mir_descriptors_source`, `mir_descriptors_missing_reason`.

Key interpretation rows:

| Column | Sheet | Meaning | Formula/source | Unit | Recommended use | Caution |
|---|---|---|---|---|---|---|
| `density_metric_raw` | `Density_Metrics` | Canonical weighted density | $w_HD_H+w_ID_I+w_SD_S$ | model units | primary compiled density ranking | depends on weight profile and weight function |
| `density_metric_raw_per_note_balance` | `Density_Metrics` | Per-note energy-ratio weighted density | $r_HD_H+r_ID_I+r_SD_S$ | model units | per-note balance diagnostics | not corpus-profile comparable metric |
| `note_density_final` | `Density_Metrics` (+ research `Spectral_Density_Metrics`) | Principled per-note scalar density: measured `component_*_energy_ratio` × per-band `*_density_sum` (GUI weight function already applied inside the sums) | $r_HD_H+r_ID_I+r_SD_S$ | model units | per-note density combining GUI weight + measured component balance | absolute (not corpus-normalized); cross-instrument only under an identical profile; NaN if any input is NaN |
| `note_density_final_ci_low` / `note_density_final_ci_high` | `Density_Metrics` (+ research) | Bootstrap CI bounds for `note_density_final` | percentiles of transform-aware bootstrap | model units | per-note uncertainty band | NaN if per-note workbook unreadable |
| `note_density_final_rel_uncertainty` | `Density_Metrics` (+ research) | Relative uncertainty of `note_density_final` | $\sigma_{boot}/|point|$ | ratio | per-note UQ magnitude | NaN if point≈0 or workbook unreadable |
| `note_density_final_uncertainty_sources` | `Density_Metrics` (+ research) | Which uncertainty sources were propagated | bootstrap config | category | `partials+ratios` (full UQ), `partials`, or `unavailable` | not a numeric metric |
| `note_effective_component_density` | `Density_Metrics` | **Acoustic fatness (F-047):** effective number of energy-bearing spectral components pooled over harmonic + inharmonic + sub-bass. **Primary noise-robust density** (A4 / B7: EPD stays flat with SNR). | $(\sum_i A_i^2)^2 / \sum_i A_i^4$ over all H+I+S components | count (≥1) | **primary fatness scalar**; instrument-discriminating; basis for chord/aggregate density | not loudness; not interchangeable with `note_density_final` or EWSD |
| `note_balanced_component_density` | `Density_Metrics` (+ research, immediately left of `EWSD_score_acoustic_balanced`) | **Balanced component density (F-056, provenance defined):** Hill $q=1$ of energy shares on a pool stricter than F-047. **Superseded by ACD_score (rho = 0.999 on validation corpora); retained for workbook compatibility.** | $D_1=\exp(-\sum p_i\ln p_i)$, $p_i=P_i/\sum P$, $P_i=A_i^2$; empty/$\sum P=0\to$ NaN | count (≥1) or NaN | evenness-aware companion to F-047; not a substitute for EPD | empty pool is NaN, never 0.0; not interchangeable with EWSD |
| `note_balanced_component_density_pool_count` | `Density_Metrics` (+ research) | Census of the F-056 pool after the stricter filter | integer count of admitted rows | count | report beside D1 | not the F-047 HIS census |
| `estimated_snr_db` | `Metrics` / research `Spectral_Density_Metrics` | Note-level spectral cleanliness: power-weighted mean of validated-harmonic `snr_db` (peak vs local floor, already computed) | $\sum_n P_n\,\mathrm{snr}_n/\sum_n P_n$ | dB | report beside EWSD for cross-dynamic comparisons (B7) | not a laboratory SNR meter; not a substitute for EPD |
| `note_effective_component_density_ci_low` / `ci_high` | `Density_Metrics` (+ research) | Bootstrap CI bounds for F-047 | resample amplitudes; recompute the same participation ratio | count (≥1) | fatness uncertainty band | algebra unchanged; NaN if fewer than 2 partials |
| `note_effective_component_density_rel_uncertainty` | `Density_Metrics` (+ research) | Relative uncertainty of F-047 | $\sigma_{boot}/|point|$ | ratio | per-note UQ magnitude | NaN if point≈0 |
| `ci_basis_frame_count` / `ci_basis_partial_count` | `Density_Metrics` (+ research, `Uncertainty_Summary`) | Sample size sitting beside every CI | independent sustain frames; pooled partial count | count | report with the interval | frames < 10 → `ci_basis_frames_insufficient` |
| `harmonic_effective_partial_count` | `Density_Metrics` | Energy-distribution density ("fatness"): effective number of harmonic partials carrying energy | $(\sum_n A_n^2)^2 / \sum_n A_n^4$ over harmonic peaks | count (≥1) | timbre/richness ranking; **register-robust** instrument comparison | not a loudness measure |
| `harmonic_energy_above_fundamental_ratio` | `Density_Metrics` | Fraction of harmonic energy not in the fundamental | $1-A_1^2/\sum_n A_n^2$ | ratio [0,1] | spectral spread / brightness; separates timbres at matched pitch | 0 ⇒ energy concentrated at f0 |
| `harmonic_energy_centroid_order` | `Density_Metrics` | Energy-weighted mean harmonic order (brightness) | $\sum_n n A_n^2 / \sum_n A_n^2$ | harmonic order | brightness in order units | depends on f0 accuracy |
| `density_weights_source` | `Density_Metrics` | Weight provenance | compile policy | category | profile traceability | do not treat as numeric metric |
| `tier_consistency_status` | `Density_Metrics` | Tier normalization completeness status | compile checks | category | data-quality filter | indicates export completeness, not acoustics |
| `inharmonicity_fit_source` | `Density_Metrics` | Inharmonicity diagnostics provenance | extraction fallback logic | category | identify full vs partial fit export | partial status can coexist with valid `B` |
| `obs_wS_artifact_flag` | (Phase 1 CSV path, summarized in Validation) | conservative artifact flag | obs-vs-energy diagnostics | bool | artifact interpretation | absence of flag does not prove physical subbass |
| `mir_descriptors_available` | `Density_Metrics` | MIR propagation status | Phase 7 availability logic | bool | filter MIR-ready rows | false means missing export path/data |

## 1.2 `Canonical_Metrics`

Exhaustive canonical column set:

`Note`, `source_file_name`, `tier`, `component_harmonic_energy_ratio`, `component_inharmonic_energy_ratio`, `component_subbass_energy_ratio`, `component_total_inharmonic_energy_ratio`, `model_harmonic_weight`, `model_inharmonic_weight`, `effective_partial_count`, `effective_partial_density`, `canonical_density_v5_adapted`, `canonical_density`, `density_normalized_global`, `density_per_component`, `rolloff_compensated_harmonic_density`, `harmonic_effective_power_density`, `harmonic_inharmonic_ratio`, `spectral_entropy`, `harmonic_completeness`, `f0_final_hz`, `acoustic_f0_status`, `f0_epistemic_status`, `valid_for_primary_statistics`, `density_confidence`, `qc_status`, `is_primary_comparable_profile`, `analysis_parameter_profile_id`, `primary_comparable_profile_definition`, `segment_policy`, `stable_segment_ewsd`, `full_stable_ewsd_ratio`, `stable_segment_frames_independent`, `stable_segment_unrepresentative`, `ewsd_primary_analysis_eligible`, `degenerate_partial_set`, `adaptive_subfundamental_cutoff_hz`, `subfundamental_margin_percent`, `percentage_subfundamental_cutoff_hz`, `leakage_guard_cutoff_hz`, `min_floor_hz`, `max_fraction_of_f0`, `effective_subfundamental_margin_percent`, `subfundamental_guard_valid`, `subfundamental_guard_policy`, `low_frequency_policy_version`, `adaptive_subfundamental_cutoff_source`, `physical_low_frequency_lower_hz`, `physical_low_frequency_upper_hz`, `subfundamental_cutoff_selection_rule`, `subfundamental_cutoff_selected_by`.

## 1.3 `Legacy_Aliases` and strict aliases

Strict alias columns:

`density_weighted_sum_alias_of`, `harmonic_energy_ratio`, `harmonic_peak_count_deprecated_legacy_alias`, `inharmonic_bin_count_deprecated_legacy_alias`, `inharmonic_candidate_count_deprecated_legacy_alias`, `inharmonic_energy_ratio`, `inharmonic_peak_count_deprecated_legacy_alias`, `subbass_energy_ratio`, `subbass_peak_count_deprecated_legacy_alias`, `total_detected_peak_count_deprecated_legacy_alias`.

## 1.4 Compile-level omitted fields (not exported in public compiled output)

`Analysis Type`, `Combined Density Metric`, `Combined Density Metric_Norm`, `Combined Density Metric_Norm2`, `Dynamic Density Score`, `Filtered Density Metric`, `Filtered Density Metric_Norm`, `Spectral Density Metric`, `Spectral Density Metric_Norm`, `Spectral Entropy`, `Spectral Entropy_Norm`, `Total Metric`, `Total Metric_Norm`, `__source_file_path`.

---

## 2) Research workbook (`compiled_density_metrics_research.xlsx`)

## 2.1 `Spectral_Density_Metrics` (exhaustive column inventory)

`Instrument`, `Note`, `MIDI`, `Pitch_Class`, `Octave`, `Register`, `Dynamic`, `Technique`, `metadata_inference_status`, `metadata_missing_reason`, `f0_nominal_hz`, `f0_final_hz`, `f0_source`, `f0_final_source`, `acoustic_f0_status`, `f0_used_for_density_hz`, `f0_used_for_density_source`, `f0_used_for_harmonic_validation_hz`, `f0_fit_accepted`, `f0_fit_rejection_reason`, `f0_epistemic_status`, `f0_validation_mode`, `nominal_prior_hz`, `f0_candidate_hz`, `f0_deviation_cents`, `low_order_match_count`, `odd_harmonic_match_count`, `even_harmonic_match_count`, `median_abs_error_cents`, `p90_abs_error_cents`, `harmonic_comb_score`, `f0_validation_max_hz`, `arithmetic_validation_status`, `acoustic_validation_status`, `f0_detuning_cents_from_nominal`, `density_metric_raw`, `density_metric_raw_source_sheet`, `energy_weighted_component_density_diagnostic`, `density_metric_normalized`, `density_weighted_sum`, `density_log_weighted`, `Total sum`, `effective_partial_density`, `body_weighted_effective_density`, `low_mid_energy_ratio`, `harmonic_body_density`, `expected_harmonic_slots_up_to_body_ceiling`, `harmonic_body_density_normalized`, `residual_body_contribution`, `residual_body_contribution_capped`, `salient_harmonic_order_count_up_to_body_ceiling`, `expected_harmonic_order_count_up_to_body_ceiling`, `salient_harmonic_coverage_up_to_body_ceiling`, `salient_harmonic_mass_up_to_body_ceiling`, `salient_harmonic_order_count_up_to_density_ceiling_hz`, `expected_harmonic_order_count_up_to_density_ceiling_hz`, `salient_harmonic_coverage_up_to_density_ceiling_hz`, `salient_harmonic_mass_up_to_density_ceiling_hz`, `salient_odd_harmonic_count_up_to_body_ceiling`, `salient_even_harmonic_count_up_to_body_ceiling`, `odd_even_harmonic_energy_ratio`, `salient_inharmonic_log_bin_count_up_to_body_ceiling`, `salient_subbass_particle_count`, `salient_inharmonic_log_bin_count_up_to_density_ceiling_hz`, `salient_subbass_particle_count_up_to_density_ceiling_hz`, `final_note_density_count_based`, `final_note_density_salience_weighted`, `note_density_final`, `note_effective_component_density`, `note_effective_component_density_ci_low`, `note_effective_component_density_ci_high`, `note_effective_component_density_rel_uncertainty`, `ci_basis_frame_count`, `ci_basis_partial_count`, `ci_basis_frames_insufficient`, `EWSD_score_total`, `EWSD_score_acoustic_balanced`, `ewsd_mode`, `ewsd_primary_analysis_eligible`, `ewsd_his_ratio_source`, `ewsd_H_ratio`, `ewsd_I_ratio`, `ewsd_S_noise_ratio`, `ewsd_weight_function_canonical`, `ewsd_acoustic_balance_alpha`, `ewsd_stage3_version`, `ewsd_merge_status`, `harmonic_density_component`, `inharmonic_density_component`, `subbass_density_component`, `harmonic_density_weight`, `inharmonic_density_weight`, `subbass_density_weight`, `density_summation_mode`, `valid_for_primary_statistics`, `is_primary_comparable_profile`, `analysis_parameter_profile_id`, `primary_comparable_profile_definition`, `density_confidence`, `f0_confidence`, `harmonic_assignment_confidence`, `spectral_stability_confidence`, `qc_status`, `outlier_ratio_max_to_mean`, `outlier_policy_applied`, `density_winsorized`, `density_median_based`, `density_trimmed_mean`, `sethares_status`, `sethares_value_status`, `sethares_curve_status`, `sethares_plot_status`, `density_weighted_sum_alias_of`, `density_weighted_sum_semantic_status`, `density_salience_threshold_db`, `density_frequency_ceiling_hz`, `harmonic_occupancy_detected_order_count`, `harmonic_occupancy_ratio`, `expected_harmonic_slot_count`, `detected_harmonic_slot_count`, `harmonic_slot_expected_count`, `harmonic_slot_matched_count`, `harmonic_slot_coverage_ratio`, `harmonic_effective_power_density_normalized`, `residual_log_frequency_occupancy`, `core_harmonic_energy_ratio`, `core_residual_energy_ratio`, `core_subbass_energy_ratio`, `residual_energy_ratio`, `spectral_entropy`, `harmonic_density_sum`, `inharmonic_density_sum`, `subbass_density_sum`, `weighted_harmonic_density_contribution`, `weighted_inharmonic_density_contribution`, `weighted_subbass_density_contribution`, `harmonic_energy_sum`, `inharmonic_energy_sum`, `subbass_energy_sum`, `total_component_energy`, `harmonic_energy_ratio`, `inharmonic_energy_ratio`, `subbass_energy_ratio`, `component_harmonic_energy_ratio`, `component_inharmonic_energy_ratio`, `component_subbass_energy_ratio`, `harmonic_order_count`, `harmonic_alignment_status`, `harmonic_alignment_coverage_ratio`, `mean_abs_harmonic_deviation_cents`, `max_abs_harmonic_deviation_cents`, `debug_counts_invariant_status`, `publication_output_allowed`, `spectral_body_thickness_index`, `harmonic_amplitude_sum`, `inharmonic_amplitude_sum`, `subbass_amplitude_sum`, `amplitude_mass_chart_file`, `energy_ratio_chart_file`, `density_metric_raw_norm_for_chart`, `density_weighted_sum_norm_for_chart`, `Total sum_norm_for_chart`, `effective_partial_density_norm_for_chart`, `body_weighted_effective_density_norm_for_chart`, `low_mid_energy_ratio_norm_for_chart`, `harmonic_body_density_normalized_norm_for_chart`, `residual_body_contribution_capped_norm_for_chart`, `spectral_body_thickness_index_norm_for_chart`, `harmonic_occupancy_ratio_norm_for_chart`, `harmonic_slot_coverage_ratio_norm_for_chart`, `residual_log_frequency_occupancy_norm_for_chart`, `core_residual_energy_ratio_norm_for_chart`, `residual_energy_ratio_norm_for_chart`, `spectral_entropy_norm_for_chart`, `final_note_density_count_based_norm_for_chart`, `final_note_density_salience_weighted_norm_for_chart`.

Key interpretation rows (EWSD — Stage 3):

| Column | Sheet | Meaning | Formula/source | Unit | Recommended use | Caution |
|---|---|---|---|---|---|---|
| `EWSD_score_total` | `Spectral_Density_Metrics` | Strict EWSD with full anti-concentration penalty $(N_{\mathrm{eff}}/N)^1$ per H/I/S compartment. **Superseded as a mass/fullness measure by spectral_mass (F-061); retained as the validated developmental ancestor (see methods documentation).** | `tools/ewsd_core.compute_ewsd` + left-join | model units | strict companion anti-concentration index | requires per-note component spectra; NaN if workbooks missing |
| `EWSD_score_acoustic_balanced` | `Spectral_Density_Metrics` | EWSD companion with moderated penalty $(N_{\mathrm{eff}}/N)^{0.5}$. **Superseded as a mass/fullness measure by spectral_mass (F-061); retained as the validated developmental ancestor (see methods documentation).** | `add_acoustic_alignment_columns` | model units | diagnostic bibliographic-distance companion | same inputs as strict EWSD; filter with `ewsd_primary_analysis_eligible`; research export adds red **data bars** (conditional formatting) |
| `smoothed_w_h_legacy` / `smoothed_w_i_legacy` / `smoothed_w_s_legacy` | Phase-1 / compiled diagnostics | Prior-mixed observation weights retained for workbook compatibility | legacy smoother on `pure_observation_w_*` | weight | archive / old-run comparison | already marked legacy; **do not use in new analyses** |
| `hutchinson_knopoff_legacy_mean_pair_scaled` | `Dissonance_Metrics` | Pre-4.6.0 mean-pair H&K export | legacy mean of pair-normalised *g* terms | model units | **legacy diagnostic; not the Hutchinson–Knopoff index; see DISSONANCE_MIGRATION.md** | do not treat as eq. (3) |
| `d10` (weight function) | Stage 1–3 `weight_function` | `Σlog1p·N_eff/N` then F-048 applies a second `N_eff/N` | `ewsd_weight_function_d10` | EWSD units | old-run reproducibility only | **double-corrected; open item in CHANGES.md; not recommended** |
| `ewsd_primary_analysis_eligible` | `Spectral_Density_Metrics` | Thesis safety gate | row-quality rule in `add_quality_columns` | bool | filter final publication statistics | `False` rows remain exported for audit |
| `ewsd_merge_status` | `Spectral_Density_Metrics` | Stage 3 merge provenance | integration layer | category | diagnose missing EWSD (`no_per_note_workbooks_found`, etc.) | not a timbre metric |

## 2.2 `Component_Balance`

`Instrument`, `Note`, `MIDI`, `Register`, `Dynamic`, `harmonic_density_sum`, `inharmonic_density_sum`, `subbass_density_sum`, `Total sum`, `component_harmonic_energy_ratio`, `component_inharmonic_energy_ratio`, `component_subbass_energy_ratio`, `core_harmonic_energy_ratio`, `core_residual_energy_ratio`, `core_subbass_energy_ratio`, `weighted_harmonic_density_contribution`, `weighted_inharmonic_density_contribution`, `weighted_subbass_density_contribution`, `density_metric_raw`, `harmonic_amplitude_sum`, `inharmonic_amplitude_sum`, `subbass_amplitude_sum`, `density_weighted_sum`, `density_log_weighted`, `amplitude_mass_chart_file`, `energy_ratio_chart_file`, `component_energy_ratio_sum`, `core_energy_ratio_sum`, `density_metric_raw_recomputed`, `density_metric_raw_difference`, `total_sum_recomputed`, `total_sum_difference`, `component_balance_status`.

## 2.3 `Validation_Summary`

`Instrument`, `Note`, `MIDI`, `Register`, `f0_nominal_hz`, `f0_final_hz`, `f0_source`, `f0_final_source`, `f0_fit_accepted`, `acoustic_f0_status`, `f0_fit_quality`, `f0_fit_residual_std_hz`, `f0_fit_rejection_reason`, `f0_detuning_cents_from_nominal`, `harmonic_alignment_status`, `harmonic_alignment_coverage_ratio`, `harmonic_alignment_energy_coverage_ratio`, `mean_abs_harmonic_deviation_cents`, `max_abs_harmonic_deviation_cents`, `rms_harmonic_deviation_cents`, `debug_counts_invariant_status`, `debug_counts_invariant_failures`, `input_schema_validation_status`, `publication_output_allowed`, `arithmetic_validation_status`, `acoustic_validation_status`, `validation_summary_status`.

## 2.4 `Charts_Data`

`Note`, `MIDI`, `spectral_body_thickness_index`, `body_weighted_effective_density`, `low_mid_energy_ratio`, `harmonic_body_density_normalized`, `core_residual_energy_ratio`, `spectral_entropy`, `salient_harmonic_order_count_up_to_body_ceiling`, `expected_harmonic_order_count_up_to_body_ceiling`, `salient_harmonic_coverage_up_to_body_ceiling`, `salient_harmonic_order_count_up_to_density_ceiling_hz`, `expected_harmonic_order_count_up_to_density_ceiling_hz`, `salient_harmonic_coverage_up_to_density_ceiling_hz`, `salient_inharmonic_log_bin_count_up_to_body_ceiling`, `salient_subbass_particle_count`, `final_note_density_count_based`, `final_note_density_salience_weighted`, `final_note_density_salience_weighted_norm_for_chart`, `harmonic_density_component`, `inharmonic_density_component`, `subbass_density_component`, `harmonic_density_weight`, `inharmonic_density_weight`, `subbass_density_weight`, `density_summation_mode`, `density_salience_threshold_db`, `density_frequency_ceiling_hz`, `harmonic_occupancy_ratio`, `residual_log_frequency_occupancy`, `effective_partial_density`, `spectral_body_thickness_index_norm_for_chart`, `body_weighted_effective_density_norm_for_chart`, `low_mid_energy_ratio_norm_for_chart`, `harmonic_body_density_normalized_norm_for_chart`, `core_residual_energy_ratio_norm_for_chart`, `spectral_entropy_norm_for_chart`, `harmonic_occupancy_ratio_norm_for_chart`, `residual_log_frequency_occupancy_norm_for_chart`, `effective_partial_density_norm_for_chart`, `density_metric_raw`, `density_metric_raw_norm_for_chart`, `density_weighted_sum`, `density_weighted_sum_norm_for_chart`, `weighted_harmonic_density_contribution`, `weighted_inharmonic_density_contribution`, `weighted_subbass_density_contribution`, `core_harmonic_energy_ratio`, `core_subbass_energy_ratio`, `component_harmonic_energy_ratio`, `component_inharmonic_energy_ratio`, `component_subbass_energy_ratio`.

---

## 2.4b `Uncertainty_Summary` (Phase D / phase_17)

One row per note × metric (`note_density_final`, `note_effective_component_density`, `EWSD_score_acoustic_balanced`). Columns: `Note`, `metric`, `rel_uncertainty`, `rel_uncertainty_pct`, `uncertainty_flag` (true when `rel_uncertainty_pct` > 25), `uncertainty_flag_threshold_pct`, `ci_basis_frame_count`, `ci_basis_partial_count`, `ci_basis_frames_insufficient`.

## 2.5 Dynamic auxiliary-sheet rules

The following sheets are dynamic by design and are therefore not stably enumerable across all runs:

| Sheet | Why dynamic | Generation rule | Why exhaustive column listing is unstable |
|---|---|---|---|
| `Compiled Metrics` | fallback/legacy public sheet in reduced export path | produced when the compile path does not build the canonical density-core sheet family | input-dependent sanitizer/filter path can remove or retain columns conditionally |
| `Compiled_Metrics_All` | wide all-columns sheet | written from wide compile frame after omission policy and optional sanitization | varies with optional features, debug columns, run-time availability, and compile options |
| `PCA_Scores` | optional dimensionality reduction output | written only when PCA is enabled and sufficient rows/features exist | feature eligibility and sample count gates alter both presence and column set |
| `PCA_Loadings` | optional dimensionality reduction output | written with PCA outputs | loadings columns depend on selected feature list after validity filtering |
| `PCA_Explained_Variance` | optional dimensionality reduction output | written with PCA outputs | number of components varies by data rank |
| `Dissonance_Metrics` | optional dissonance outputs | emitted only when dissonance fields are available | model availability and compare mode change column set |
| `Dissonance_Model_Comparison` | optional long comparison table | emitted when multi-model comparison data exist | model list and availability are runtime dependent |
| `Dissonance_Model_Correlations` | optional correlation matrix | emitted when enough samples and model outputs exist | correlation matrix dimensionality depends on present models and valid rows |
| `Debug_Counts` | diagnostics tied to active extraction paths | exported when debug count columns are present in compiled frame | debug families expand/contract with pipeline options and schema evolution |
| `Validation_Metrics` | diagnostics tied to active validation paths | exported when validation columns are present in compiled frame | validation token families depend on enabled checks and available source fields |

---

## 2.6 Crosswalk: compiled vs research sheets

| Compiled source sheet/field family | Research destination sheet | Mapped? | If omitted, why |
|---|---|---|---|
| `Density_Metrics` core density (`density_metric_raw`, weighted contributions, component ratios) | `Spectral_Density_Metrics` | yes | n/a |
| `Density_Metrics` arithmetic check inputs | `Component_Balance` | yes (derived and recomputed) | n/a |
| `Validation_Metrics` status and f0/alignment checks | `Validation_Summary` | partial | only selected validation-facing columns are carried; internal debug-only fields are excluded |
| `Per_Note_Processing_Metadata` STFT/tier/settings | `Analysis_Settings_By_Note` | partial | reduced to research-facing setting subset; transient internal fields omitted |
| `Canonical_Metrics` canonical subset | `Spectral_Density_Metrics` | partial | merged where aliases/columns are explicitly mapped; non-mapped canonical extras are omitted |
| `Diagnostic_Metrics` wide diagnostics | `Spectral_Density_Metrics` | partial | only explicitly selected diagnostics included to keep research sheet stable |
| `Legacy_Compatibility` legacy scalars | `Legacy_Compatibility` | yes | n/a |
| Per-note `spectral_analysis.xlsx` component spectra | `Spectral_Density_Metrics` (EWSD columns) | yes (Stage 3) | recomputed by `tools/ewsd_research_integration`; requires Harmonic + Inharmonic sheets; NaN + status if workbooks absent |
| `Density_Metrics` segmented MIR columns | `Spectral_Density_Metrics` | mostly no | research export currently focuses on a reduced descriptor set and chart-ready fields |
| `Density_Metrics` strict alias columns | (none or legacy sheet only) | mostly no | strict aliases are compatibility-only and intentionally not duplicated in research main sheet |
| `Density_Metrics` `obs_wS_artifact_*` family | `Validation_Summary` (aggregate only) | mostly no | research workbook currently does not carry full row-level obs artifact family |

---

## 2.7 Inharmonicity family gap in research workbook

Current state: the research workbook does **not** expose the full inharmonicity diagnostic family from compiled `Density_Metrics`.

Not currently mapped into `Spectral_Density_Metrics`:

- `inharmonicity_coefficient_B`
- `inharmonicity_fit_residual_std_cents`
- `inharmonicity_fit_status`
- `inharmonicity_fit_method`
- `inharmonicity_model_applied`
- `inharmonicity_fit_source`
- `inharmonicity_validation_warning`

Reason: `tools/export_research_density_workbook.py` does not currently include explicit mapping/selection for these columns.

Implication: inharmonicity-specific interpretation should use `compiled_density_metrics.xlsx` until research export mapping is extended.

---

## 3) Usage and caution conventions

| Column family | Recommended use | Caution |
|---|---|---|
| `density_metric_raw` and component contributions | primary model-density comparison within matched profile | profile mismatch invalidates direct comparison |
| `note_density_final` | per-note principled scalar density (GUI weight + measured balance) | absolute; cross-instrument only under identical profile |
| `EWSD_score_acoustic_balanced` | cross-instrument bibliographic distance (Stage 3) | filter `ewsd_primary_analysis_eligible`; requires per-note workbooks |
| `EWSD_score_total` | strict anti-concentration EWSD companion | same inputs as balanced score; not interchangeable with `note_density_final` |
| `ewsd_primary_analysis_eligible` | thesis row gate for EWSD statistics | `False` rows exported for audit — do not drop silently |
| `*_per_note_balance` and `component_*_energy_ratio` | per-note explanatory diagnostics | do not substitute for corpus-profile weighting |
| `*_tier_normalized` | cross-tier comparability of raw sums | only valid when `tier_consistency_status` is complete |
| `mir_descriptors_*` and segmented MIR columns | timbral descriptor analysis | verify availability/source flags first |
| `inharmonicity_*` columns | stretch/fitting diagnostics | interpret with instrument-family context |
| `obs_wS_artifact_*` | artifact interpretation support | absence of artifact flag does not prove physical subbass |
| `legacy_*`, strict alias columns | backward compatibility only | avoid as primary research endpoints |

---

## 4) Harmonic-count terminology policy

To avoid acoustic misinterpretation, exported columns follow this policy:

- **Physically valid body-ceiling Hz harmonic-order family**
  - `expected_harmonic_order_count_up_to_body_ceiling`
  - `salient_harmonic_order_count_up_to_body_ceiling`
  - `salient_harmonic_coverage_up_to_body_ceiling`
- **Research aliases (same values, clearer names)**
  - `theoretical_harmonic_order_count_up_to_body_ceiling` = `expected_harmonic_order_count_up_to_body_ceiling`
  - `detected_salient_harmonic_order_count_up_to_body_ceiling` = `salient_harmonic_order_count_up_to_body_ceiling`
  - `salient_harmonic_coverage_ratio_up_to_body_ceiling` = `salient_harmonic_coverage_up_to_body_ceiling`
- **Occupancy descriptor (not strict detected partial-order count)**
  - Canonical name: `harmonic_region_occupancy_count`
  - Deprecated one-cycle alias: `harmonic_occupancy_detected_order_count`
  - Semantics: occupancy/slot-derived descriptor; not guaranteed bounded by `floor(ceiling/f0)`.
- **Diagnostic/debug only (not physical harmonic-order counts)**
  - `harmonic_bin_count`
  - `harmonic_peak_candidate_count`
- **Legacy high-ceiling slot-index field**
  - `legacy_high_ceiling_harmonic_slot_index_count` (legacy `Harmonic Count` / `Harmonic Count (N)` lineage; not a body-ceiling Hz physical harmonic-order count).

## 5) Body density versus full-spectrum spectral activity

- **Body/fatness family (primary research interpretation)**
  - `density_component_body_weighted_sum_body_ceiling` (canonical primary)
  - `harmonic_component_energy_sum_body_ceiling`
  - `inharmonic_component_energy_sum_body_ceiling`
  - `subbass_component_energy_sum_body_ceiling`
  - Legacy aliases retained for compatibility: `density_component_body_weighted_sum_body_ceiling`, `harmonic_component_energy_sum_body_ceiling`, `inharmonic_component_energy_sum_body_ceiling`, `subbass_component_energy_sum`, `density_body_weighted_sum_body_ceiling`
  - Ceiling is explicit in `body_density_frequency_ceiling_hz` (runtime-configured).
- “The primary note-body/fatness density metric is component-based: it is computed from validated harmonic components, nonharmonic peak candidates, and low-frequency/subbass residual candidates. It is not computed by integrating all FFT bins in the body band.”
- **Bin-integrated body-band diagnostics (not fatness metric)**
  - `body_band_harmonic_bin_energy_sum_body_ceiling`
  - `body_band_residual_bin_energy_sum_body_ceiling`
  - `body_band_total_bin_energy_sum_body_ceiling`
  - `density_body_band_bin_integrated_index_body_ceiling`
- **Full-spectrum family (diagnostic / brightness / extension)**
  - `density_full_spectrum_weighted_sum_20khz`
  - `harmonic_full_spectrum_energy_sum_20khz`
  - `inharmonic_full_spectrum_energy_sum_20khz`
  - `high_frequency_spectral_activity_sum`
  - `spectral_extension_index_20khz`
  - `brightness_or_upper_spectral_activity_index_20khz`
  - `full_spectrum_harmonic_candidate_count_20khz`
  - Ceiling is explicit in `full_spectrum_frequency_ceiling_hz` (default 20000 Hz).
- **Interpretation rule**
  - Full-spectrum 20 kHz fields and bin-integrated body-band diagnostics are not body/fatness metrics and must not replace `density_component_body_weighted_sum_body_ceiling` in research interpretation.

## 6) Column-triage deprecations (export still written)

Class `deprecated`. Values are still computed and exported. Do not use in new analyses.

| Column | Successor / note |
|--------|------------------|
| `roughness_aures_1985_on_{attack,release,sustain,sustain_segment}` | `roughness_parncutt_kernel_*` (F-037). Retired key; NaN-filled; misattributed citation. Scheduled for removal from new exports at the next major version. |
| `canonical_density_v5_adapted`, `body_weighted_effective_density`, `final_note_density_count_based`, `final_note_density_salience_weighted`, `effective_partial_density`, `density_metric_per_harmonic`, `density_normalized_global`, `density_per_component`, `rolloff_compensated_harmonic_density`, `rolloff_compensated_harmonic_density_alpha`, `rolloff_compensated_harmonic_density_component_count`, `rolloff_harmonic_partial_count` | ACD (F-057) / `spectral_mass` (F-061). Internal; superseded for analytical use. |
| `discrete_metric_d10` | Double-corrected; open item in `CHANGES.md`; not recommended. |
| `Soma_A_linear_harmonicos`, `Soma_A_linear_inarmonicos`, `Soma_A_linear_subbass` | Portuguese-named copies of `linear_sum_amplitude_harmonic`, `linear_sum_amplitude_inharmonic_partial`, `linear_sum_amplitude_subbass_band`. Do not rename either set. |
| `Soma_A_linear_total` | NaN→0 sum of the three Soma/linear-amplitude twins. Not `total_component_energy`. |

Internal density-machinery columns reclassed `diagnostic` carry the note:
"internal; superseded for analytical use by F-057/F-061". See
`docs/validation/COLUMN_TRIAGE_DECISIONS.md` for columns the rule did not place.
