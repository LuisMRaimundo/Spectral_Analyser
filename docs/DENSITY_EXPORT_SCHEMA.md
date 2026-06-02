# DENSITY_EXPORT_SCHEMA — Authoritative export schema

> **Status:** scaffolded skeleton. Normative content is to be authored by the project author.
> This file is the authoritative reference for the schema of `compiled_density_metrics.xlsx`
> and of the research workbook produced by `tools/export_research_density_workbook.py`.

## 1. Scope and authority

This document is normative for export-column semantics. Where it conflicts with any
historical document under `docs/` (e.g. `EXPORT_COLUMN_DICTIONARY.md`), this document prevails.

<!-- TODO(author): state the precedence rule explicitly and date it. -->

## 2. `Density_Metrics` sheet

<!-- TODO(author): list every column emitted on the `Density_Metrics` sheet, with type,
     unit, range, and the source function in `density.py` / `compile_metrics.py` that
     produces it. -->

### 2.1 `note_density_final` (principled per-note scalar density)

Emitted on `Density_Metrics` (and mirrored on research `Spectral_Density_Metrics`).

- **Definition:**
  `note_density_final = component_harmonic_energy_ratio · harmonic_density_sum`
  `+ component_inharmonic_energy_ratio · inharmonic_density_sum`
  `+ component_subbass_energy_ratio · subbass_density_sum`.
- **Source:** `compile_metrics._compute_note_density_final` (column-name resolution +
  NaN-propagating composition); research mirror in
  `tools/export_research_density_workbook.build_spectral_density_metrics`.
- **Weights:** the per-note **measured** energy ratios from `Component_Balance`
  (sum to 1). It does **not** use the Bayesian adaptive weights
  (`harmonic_density_weight` / `inharmonic_density_weight` / `subbass_density_weight`).
- **Weight function:** the GUI amplitude weight function (linear / log / quadratic / …)
  is already baked into each `*_density_sum` term; it is not re-applied here.
- **Units / scale:** model units, **absolute** (not corpus-normalized). Input audio is
  RMS-referenced, so values describe spectral shape at a reference level. Cross-instrument
  comparison is valid only under an **identical analysis profile** (same weight function,
  density ceiling, threshold, tier strategy).
- **Missing-value policy:** if **any** of the six inputs is NaN for a row, the result is
  NaN (missing values are never treated as zero).
- **Relation to existing columns:** algebraically identical in form to
  `density_metric_raw_per_note_balance`, but sourced explicitly from the canonical
  `*_density_sum` + `component_*_energy_ratio` columns and exported as a distinct,
  clearly-named primary column. It does **not** replace or modify `density_metric_raw`,
  `density_metric_normalized`, or `final_note_density_salience_weighted`.
- **Uncertainty (companion columns):** each note carries a non-parametric
  bootstrap confidence interval for `note_density_final`:
  `note_density_final_ci_low`, `note_density_final_ci_high`,
  `note_density_final_rel_uncertainty` (std/|point|), and
  `note_density_final_uncertainty_sources`. Computed transform-aware by
  `density_uncertainty.bootstrap_note_density_final`: per-partial contributions
  are resampled within each band **and** the component energy ratios are
  recomputed inside each resample from the bootstrapped band energies
  (`propagate_ratio_uncertainty=True`), so both the band-sum and the ratio
  uncertainty are propagated jointly. `note_density_final_uncertainty_sources`
  records `partials+ratios` for this full UQ (or `partials` / `unavailable`).
  NaN when the per-note workbook is unreadable.
- **n_fft / window sensitivity (opt-in):** the resolution component of the UQ
  is provided as a separate, opt-in study tool —
  `tools/note_density_nfft_sensitivity.py` (built on
  `density_uncertainty.nfft_sensitivity`) — which re-analyses a note across FFT
  sizes and reports the dispersion of `note_density_final`. It is intentionally
  **not** a per-note column in the main pipeline because re-analysis at multiple
  resolutions multiplies per-note runtime.

### 2.2 Corpus comparability verdict

`Analysis_Metadata` carries a single authoritative `corpus_comparable_for_statistics`
boolean (True only for a single primary-comparable profile), plus
`corpus_comparability_status`, `corpus_profile_count`, and
`corpus_primary_comparable_row_count`. `Canonical_Primary_Filtered` is
hard-restricted to one analysis profile (the dominant one when several
primary-comparable profiles are present), so primary statistics are never
aggregated across profiles.

### 2.3 `note_effective_component_density` (acoustic fatness — F-047)

Emitted on `Density_Metrics` and research `Spectral_Density_Metrics`.

- **Definition:** pooled participation ratio
  \(N_{\mathrm{eff}}^{\mathrm{HIS}} = (\sum_i A_i^2)^2 / \sum_i A_i^4\) over all
  harmonic, inharmonic, and sub-bass components identified for the note.
- **Source:** `compile_metrics._energy_distribution_density`; research mirror in
  `tools/export_research_density_workbook.build_spectral_density_metrics`.
- **Units / scale:** effective partial count (≥ 1). Level-normalized input; **not**
  loudness.
- **Non-interchangeability:** distinct from `note_density_final` (§2.1, weighted
  density) and from EWSD scores (§R.4, anti-concentration weighted density).
- **Harmonic-only variant:** `harmonic_effective_partial_count` (F-045).
- **Practical guide:** `docs/validation/NOTE_FATNESS_AND_DENSITY_GUIDE.md`.

## 2b. Per-note `Harmonic_Inclusion_Audit` sheet (in each `spectral_analysis.xlsx`)

Read-only diagnostic sheet written per note by
`proc_audio._save_spectral_data_to_excel`. One row per harmonic order, exposing exactly
why each candidate is included in or excluded from the density computation. No metric,
threshold, ceiling, or validation rule is changed by this sheet — it is observational.

Columns: `harmonic_number`, `expected_frequency_hz`, `extracted_frequency_hz`,
`frequency_deviation_hz`, `frequency_deviation_cents`, `magnitude_db`, `power_raw`,
`snr_db`, `prominence_db`, `cfar_margin_db`, `cfar_detected`, `local_peak_valid`,
`candidate_status`, `include_for_density`, `included_in_strict_peaks`,
`included_in_body_density_5khz`, `exclusion_reason`, `search_ceiling_hz`,
`body_density_ceiling_hz`.

**CFAR noise-significance gate.** Harmonic acceptance no longer relies on a fixed
SNR margin alone. At each refined peak bin a cell-averaging CFAR (constant
false-alarm-rate) test is applied
(`harmonic_peak_validation.cfar_peak_detection`): the bin power must exceed a
threshold derived from a stated false-alarm probability (`pfa`, default `1e-2`)
against a locally-estimated noise floor (training cells around the peak, guard
cells excluded, the strongest training cells trimmed so neighbouring partials do
not inflate the floor). `cfar_margin_db = 10·log10(peak_power / threshold)` and
`cfar_detected = cfar_margin_db ≥ 0`. A candidate is promoted to
`strict_validated` (and hence `include_for_density`) only when it is CFAR-detected
**and** clears the saddle-prominence criterion — replacing the previous purely
ad-hoc fixed-dB SNR rule with an adaptive, detection-theoretic criterion that
mirrors the significance gate already used for the inharmonicity coefficient.

`exclusion_reason` is computed by
`harmonic_peak_validation._harmonic_inclusion_audit_exclusion_reason` (literal 3.0 dB
SNR / prominence thresholds; literal 5000.0 Hz body ceiling) and is one of:
`included`, `above_body_density_ceiling_5khz (...)`, `off_frequency (...)`,
`snr_below_3dB (...)`, `prominence_below_3dB (...)`, `not_local_maximum`,
`rejected_by_validation (status=...)`. The count of `included` rows equals
`harmonic_density_included_count` in `Analysis_Metadata`.

Note: `exclusion_reason` is a **human-readable descriptive label** and is
deliberately kept stable for cross-version comparison; the authoritative
acceptance decision is `candidate_status` / `include_for_density`, gated by the
**CFAR detection + saddle prominence** criteria above. A candidate with
`snr_db ≥ 3` and `prominence_db ≥ 3` that nonetheless fails the CFAR test
(`cfar_detected = False`, `cfar_margin_db < 0`) is therefore reported as
`rejected_by_validation (...)` rather than an SNR/prominence reason — inspect
`cfar_margin_db` to see the detection-theoretic margin directly.

## 3. `Per_Note_Processing_Metadata` sheet

<!-- TODO(author): list every metadata column written per note. -->

## 4. `Canonical_Metrics` sheet

<!-- TODO(author): canonical-metric column inventory, with reference to
     `validate_canonical_metrics.py`. -->

## 5. `Diagnostic_Metrics` sheet

<!-- TODO(author): diagnostic-metric column inventory. -->

## 6. `Debug_Counts` sheet

<!-- TODO(author): cross-reference with `peak_component_counts.py` and the
     observation-cap policy. -->

## 7. `Legacy_Compatibility` sheet

<!-- TODO(author): document SDM, FDM, CDM, "Density Metric", and
     "Weighted Combined Metric" lineage. -->

## 8. Dissonance / PCA separation

<!-- TODO(author): explain why dissonance descriptors and PCA scores live on separate
     sheets, and the redaction rules that apply when external corpora are used. -->

## 9. Redaction notes

<!-- TODO(author): list every column that may be redacted in public exports, and the
     policy that governs redaction. -->

## R. Research workbook (`compiled_density_metrics_research.xlsx`)

This section is referenced from `compile_metrics.py` and from
`tools/export_research_density_workbook.py`. It documents the read-only post-process
that produces the research workbook.

### R.1 `Spectral_Density_Metrics` (research-only sheet)

The research workbook merges the `Legacy_Compatibility` sheet from the compiled workbook
and adds one editorial column:

`density_weighted_sum_cdm_mean` = (`density_weighted_sum` + `Combined Density Metric`) / 2

Soft column highlights (blue / yellow / lavender) are applied to `density_weighted_sum`,
`Combined Density Metric`, and `density_weighted_sum_cdm_mean` for side-by-side reading.
The column is editorial; it does not enter Stage-2 compilation.

### R.2 AutoFilter and Table policy

The research workbook uses worksheet-level AutoFilter on data sheets and does not embed
formal `xl/tables/table*.xml` parts (Microsoft Excel compatibility constraint). README
and Dashboard sheets are not auto-filtered.

### R.3 Column-header sanitisation

Exported column headers are sanitised: blank names are forbidden; duplicate names are
suffixed `_2`, `_3`, … in document order.

### R.4 Stage 3 EWSD-R v18 columns (`Spectral_Density_Metrics`)

Stage 3 runs automatically during research export (default `include_ewsd=True`).

| Column | Role |
|---|---|
| `EWSD_score_total` | Strict EWSD: $\sum_k r_k D_k (N_{\mathrm{eff},k}/N_k)$ |
| `EWSD_score_acoustic_balanced` | Companion: same with penalty exponent $\alpha=0.5$ |
| `EWSD_score_total_ci_low` / `_ci_high` / `_rel_uncertainty` | Bootstrap 95% CI for strict EWSD |
| `EWSD_score_acoustic_balanced_ci_low` / `_ci_high` / `_rel_uncertainty` | Bootstrap 95% CI for balanced EWSD |
| `ewsd_uncertainty_sources` | `partials+ratios`, `partials`, or `unavailable` |
| `ewsd_primary_analysis_eligible` | Thesis gate — filter to `True` for final statistics |
| `ewsd_mode` | Must be `individual_exact` for primary use |
| `ewsd_H_ratio`, `ewsd_I_ratio`, `ewsd_S_noise_ratio` | Per-note H/I/S ratios used |
| `ewsd_his_ratio_source` | Which Excel ratio column set was selected |
| `ewsd_weight_function_canonical` | Weight function applied to component sums |
| `ewsd_acoustic_balance_alpha` | Penalty exponent (default 0.5) |
| `ewsd_stage3_version` | Embedded EWSD core version tag (`EWSD-R v18`) |
| `ewsd_merge_status` | `merged_individual_exact`, `no_per_note_workbooks_found`, etc. |

Implementation: `tools/ewsd_pure.py`, `tools/ewsd_core.py`, `tools/ewsd_uncertainty.py`, `tools/ewsd_research_integration.py`.
Highlight: `EWSD_score_total` uses pale orange fill (research workbook only).
**Conditional formatting:** `EWSD_score_acoustic_balanced` carries red **data bars** (min–max, `#C00000`) on `Spectral_Density_Metrics`.
Construct validity: `docs/validation/EWSD_CONSTRUCT_VALIDITY.md`; sensitivity CLI: `tools/ewsd_sensitivity_report.py`.
Stage 3 sheets: `Stage3_Diagnostics` (per-note merge audit); `Stage3_Summary` (run-level metadata — not mixed with note rows).

### R.5 Conditional formatting (`Spectral_Density_Metrics`)

Applied by `tools/export_research_density_workbook._apply_sdm_conditional` (research export only):

| Column | Rule |
|--------|------|
| `harmonic_energy_ratio` | Three-color scale (red → yellow → green, 0–1) |
| `EWSD_score_acoustic_balanced` | Red **data bars** (automatic min/max within column) |
| `f0_fit_accepted` | Green / amber cell fill for TRUE / FALSE |
| `debug_counts_invariant_status` | Green when `passed` |

Soft column fills (header + data): `density_weighted_sum`, `note_density_final`, `EWSD_score_total` (see §R.1).

Primary thesis table sheet: **`Primary_Statistics_Eligible`** (replaces legacy `Primary_Statistics_Filtered` name; eligibility gate, not QC-warning exclusion).

### R.6 Dead-column pruning and merge keys (v4.0.2)

**Policy:** columns that are never populated in a given run are omitted from Excel output
rather than exported as all-blank placeholders.

**Stage 2:** `compile_metrics._drop_dead_columns` (delegates to
`export_row_identity.drop_dead_columns`) runs on `Density_Metrics`, curated status sheets,
`Debug_Counts`, and `Per_Note_Processing_Metadata`. `sample_id` is copied from
`Density_Metrics` onto satellite sheets via `_attach_sample_id_from_density`.

**Stage 3:** `tools/export_research_density_workbook.build_workbook` prunes dead columns on
all major data sheets after assembly. Satellite sheet merge uses
`export_row_identity.merge_keys_for_frames` — prefer `sample_id` when IDs match the anchor,
otherwise merge on `Note`.

**Re-export:** Stage 3 alone fixes research workbooks produced before v4.0.2 when the
compiled workbook already contains the data on `Diagnostic_Metrics` /
`Per_Note_Processing_Metadata`. Stage 2 recompile is required to prune compiled-sheet dead
columns and attach `sample_id` on satellite sheets.

### R.7 Metadata weights, sample_id, dedupe, zero_padding (v4.0.3)

**Research `Metadata` sheet:** `harmonic_density_weight`, `inharmonic_density_weight`, and
`subbass_density_weight` are corpus-level **Phase-2 application weights**. Each key resolves
through its own fallback chain (`phase2_harmonic_application_weight`, etc.) — not a shared
lookup that returns the harmonic weight for all three.

**Compiled `Diagnostic_Metrics.sample_id`:** empty or all-NaN placeholder columns are treated
as unpopulated; authoritative IDs are copied from `Density_Metrics` via
`export_row_identity.attach_sample_id_from_density` before Excel write.

**Research duplicate headers:** after merge uniquification adds `_2` suffixes,
`dedupe_identical_columns` runs again in `_sanitize_dataframe_columns` so byte-identical
suffix columns are dropped.

**`Analysis_Settings_By_Note.zero_padding`:** per-note numeric values are preferred
(including derivation from `n_fft_effective / n_fft` when present) before falling back to
the tier-dependent label string.

**Re-export (v4.0.3):** re-run **Stage 2 + Stage 3** on existing audio to refresh compiled
and research workbooks. Stage 3 alone updates research `Metadata` weights and research-sheet
dedupe; Stage 2 is required for `Diagnostic_Metrics.sample_id` on compiled output.

### R.8 Known ambiguous column names (documented, not yet renamed in export)

These headers still appear in current exports. **Do not join or compare across workbooks on
name alone** — read the sheet and the canonical name in
[`docs/validation/EXPORT_SCHEMA_AUDIT_REPAIR.md`](validation/EXPORT_SCHEMA_AUDIT_REPAIR.md).

| Column name | Workbook / sheet | Actual meaning |
|-------------|------------------|----------------|
| `density_weighted_sum` | compiled `Density_Metrics` / `Legacy_Aliases` | Per-note energy-ratio sum (`density_metric_raw_per_note_balance`) |
| `density_weighted_sum` | research `Spectral_Density_Metrics` | Body-ceiling richness sum (`richness_weighted_body_density_*`) |
| `density_metric_raw` | compiled | Phase-2 corpus-profile weighted density |
| `harmonic_density_weight` | research `Metadata` | Phase-2 corpus application weight (v4.0.3+) |
| `harmonic_density_weight` | `Analysis_Settings_By_Note` | GUI **base** multiplier (typically 1 / 0.5 / 0.25), not Phase-2 |
| `harmonic_density_weight` | research `Spectral_Density_Metrics` | Per-note energy-ratio–derived weight column, not Phase-2 |
| Same names as `Density_Metrics` | `Diagnostic_Metrics` (subset) | Often log/diagnostic scale — prefixed columns (`diagnostic_*`) where renamed; others may still collide |

Planned follow-up (not in v4.0.3): rename ambiguous public columns to explicit canonical
names only; unify publication redaction across all sheets.
