# Formula Extraction Exhaustiveness Audit

## 1. Purpose

This read-only audit asks whether the **current formula-extraction corpus** (Passes 1–10 plus `FORMULA_EXTRACTION_INDEX.md`) is **exhaustive** relative to **project-owned** Python modules that contain **mathematical or algorithmic numeric logic**. External libraries (NumPy, SciPy, librosa, pandas, …) are treated as **black boxes**; their internals are out of scope.

The audit **does not** add new formulas or tables; it only records **coverage gaps** and a recommended follow-up pass structure.

## 2. Method

1. **Inventory of extraction corpus** — Read `FORMULA_EXTRACTION_INDEX.md` and the ten pass tables to list which **files / functions / themes** are already captured.  
2. **Repository scan** — Enumerate top-level `*.py` and selected first-party subtrees (`audio_analysis/`, `tools/` where they contain analysis math). **Excluded from primary “scientific pipeline” scope:** `tests/` (test-only), and obvious **GUI / orchestration wiring** unless they embed numeric policy.  
3. **Heuristic detection** — For each candidate module, list top-level `def` symbols and flag modules with substantial **arithmetic, powers, logs, dB, ratios, clipping, thresholds, energy sums, or classification logic** (via file skim and `grep` for patterns such as `np.log`, `**`, `percentile`, `sum(`, `dissonance`, `entropy`, `stft`, `normaliz`).  
4. **Classification** — Each gap is tagged **COVERED**, **PARTIALLY COVERED**, **NOT COVERED**, **LOW PRIORITY**, or **IGNORE** (per instructions).

**Limitation:** Without a line-by-line formal pass over every function, “exhaustive” means **systematic module-level coverage against the extraction index**, not a proof that every arithmetic operator in the repo is catalogued.

## 3. Covered areas

The following are **already represented** in the formula-extraction documents (quality varies from full formulas to “call graph” pointers):

| Area | Pass / doc | Notes |
|------|----------------|--------|
| Six flagship `density.py` metrics (entropy, \(D_{\mathrm{eff}}\), \(N_{\mathrm{eff}}\), d3/d10/d17/d24 path, `apply_density_metric`, rolloff-compensated harmonic density) | Pass 1 | Large parts of `density.py` **outside** this set are still uncovered. |
| `WeightFunction` / `get_weight_function` | Pass 2 | |
| `band_partial_metric_sum`, `partial_metric_sums_h_i_s_total`, `compute_discrete_spectral_metrics_bundle` | Pass 3 | |
| `identify_nonharmonic_residual_rows` (masking) | Pass 4 | |
| `harmonic_alignment` cents / tolerance / collapse / energy ratios | Pass 5 | |
| `peak_component_counts` peak-list Hz windows | Pass 6 | |
| `low_frequency_policy` margins, adaptive cutoff, row labels | Pass 7 | |
| `spectral_leakage_guards` | Pass 8 | |
| `_add_canonical_and_global_density_columns`, `_compute_weighted_density_columns_for_wide_df` | Pass 9 | Rest of `compile_metrics.py` is mostly **not** extracted. |
| Selected `proc_audio` STFT/RMS/Parseval/edge weights / `_estimate_f0_global_robust` / component energy | Pass 10 | **Small slice** of a very large module. |

## 4. Missing or under-covered formula-bearing areas

| File | Function / context | Formula-bearing expression | Why it may matter | Already covered? | Recommended action |
|------|---------------------|-----------------------------|-------------------|------------------|----------------------|
| `density.py` | `calculate_harmonic_density` / `calculate_inharmonic_density` | Band-weighted or list-based density reductions | Published “density” semantics beyond `apply_density_metric` | **NOT COVERED** | Pass 11 — harmonic/inharmonic density paths |
| `density.py` | `physical_spectral_density`, `perceptual_spectral_density`, `calculate_perceptual_spectral_density` | Multi-factor scores, weights from constants | Alternative density narratives in exports | **NOT COVERED** | Pass 11 — perceptual / physical density |
| `density.py` | `_critical_band_masking`, `apply_spectral_masking_filter`, `estimate_noise_floor*` | dB offsets, band sums, masking curves | Affects filtered spectra feeding peaks | **NOT COVERED** | Pass 11 — masking & noise floor |
| `density.py` | `calculate_spectral_complexity`, `calculate_harmonic_richness`, `_calculate_harmonic_completeness_phase2` | Aggregated complexity / completeness scalars | Descriptor metrics in reports | **PARTIALLY COVERED** (conceptually related to entropy / order counts) | Pass 11 — complexity / richness |
| `density.py` | `compute_harmonic_effective_power_density`, `compute_harmonic_effective_power_mass` | Power-law / mass budgets on harmonic lists | Distinct from discrete D3–D24 | **NOT COVERED** | Pass 11 — effective power density & mass |
| `density.py` | `aggregate_low_frequency_residual_peak_power`, `compute_subbass_protection_tolerance_hz` | \(A^2\) aggregates, tolerance Hz | Couples to Pass 7 / subbass policy in `proc_audio` | **PARTIALLY COVERED** (policy elsewhere; aggregation formula not in tables) | Pass 11 — subbass aggregate power |
| `density.py` | `partial_density_effective_components` / `_bundle` | Blended \(D_{\mathrm{eff}}\)-style bundles with ground noise | `proc_audio` calls into this | **NOT COVERED** | Pass 11 — effective partial-density bundle |
| `density.py` | `calculate_combined_density_metric` | \(\alpha,\beta\) log-space combination `log1p` / `expm1` | Combined harmonic–inharmonic scalar | **NOT COVERED** | Pass 11 — combined density |
| `density.py` | `_hz_to_bark`, `spectral_density` (if used numerically) | Bark mapping, bin occupancy | Psychoacoustic scaling in some paths | **NOT COVERED** | Pass 11 or **LOW PRIORITY** if unused in default pipeline |
| `density.py` | `apply_density_metric_df` | Column-wise application of `apply_density_metric` | Thin wrapper but documents column contracts | **LOW PRIORITY** | Reference in Pass 11 notes only |
| `density.py` | `compare_with_sethares_dissonance` | Comparison / scaling vs Sethares input | Cross-metric audit | **NOT COVERED** | **LOW PRIORITY** unless thesis compares models |
| `dissonance_models.py` | `DissonanceModel` hierarchy (`pure_tones_dissonance`, `total_dissonance`, `same_timbre_dissonance`, curve sampling) | Pairwise summation, interval sweeps `np.linspace` | Core psychoacoustic model layer | **NOT COVERED** | **Pass 12 — dissonance models** |
| `proc_audio.py` | `calculate_dissonance_metrics` and coupling to `dissonance_models` | Curves, scaling, model selection | User-facing “dissonance” output | **NOT COVERED** | Pass 12 — tie to Pass 10 only at API boundary |
| `proc_audio.py` | `_parabolic_peak`, `_refine_peak_index`, `_saddle_prominence_db`, `_local_peak_metrics` | Interpolation, dB prominence | Peak list quality drives all downstream Hz logic | **NOT COVERED** | **Pass 13 — peak detection & prominence** |
| `proc_audio.py` | `_correct_f0_candidate_against_prior` | Integer ratio / cent search around prior | f₀ publication semantics | **NOT COVERED** | Pass 13 — f₀ prior correction |
| `proc_audio.py` | `frequency_to_note_name`, `calculate_fundamental_frequency` (note → Hz) | 12-TET formula \(440\cdot 2^{(n-69)/12}\) | Nominal f₀ from filename | **PARTIALLY COVERED** (same math as `compile_metrics.note_to_fundamental_freq` family) | Pass 13 or compile pass |
| `proc_audio.py` | `linear_export_batch_alignment_k`, display scaling branches | Linear calibration factors | Export amplitude semantics | **NOT COVERED** | **LOW PRIORITY** unless auditing export alignment |
| `compile_metrics.py` | `extract_density_component_sum`, `extract_density_components_from_per_note_workbook` | Sheet/column resolution + sums | Feeds Pass 9 inputs | **NOT COVERED** | **Pass 14 — compile-time density extraction** |
| `compile_metrics.py` | `apply_frequency_dependent_normalization`, `get_frequency_dependent_alpha` | Piecewise \(\alpha(f_0)\), \(\sum n^{-\alpha}\) integral-style scaling | Register-dependent density correction | **NOT COVERED** | Pass 14 |
| `compile_metrics.py` | `apply_weighted_index`, `_robust_normalize_series`, `_minmax` | IQR / percentile / PDF-style indices | Secondary spreadsheet analytics | **PARTIALLY COVERED** (normalisation theme overlaps Pass 9) | Pass 14 — document distinct from canonical density |
| `compile_metrics.py` | `note_to_midi`, `note_to_fundamental_freq` | 12-TET mapping | Compile-time note ordering / f₀ | **NOT COVERED** | Pass 14 |
| `compile_metrics.py` | `extract_dissonance_metrics`, `_append_dissonance_excel_sheets` | Aggregation of curve summaries | Bridge to dissonance outputs | **NOT COVERED** | Pass 12 / 14 boundary |
| `compile_metrics.py` | `_compute_optional_pca_sheets` | PCA on numeric block (sklearn black box) | Exploratory compile artefact | **IGNORE** (third-party algorithm body) | Document data matrix only if needed |
| `harmonic_validation.py` | `validate_harmonic_series_matched`, `_slot_count_aliases` | RMS of signed cents errors; slot arithmetic | Audit layer on top of Pass 5 | **PARTIALLY COVERED** (delegates to `compute_harmonic_alignment_metrics`) | Short Pass 11 addendum or extend Pass 5 table |
| `audio_analysis/super_audio_analyzer.py` | `finalize_batch_power_mass_summary` | Percent renormalisation \(\times 100/\sum p\) | Batch power mass semantics | **NOT COVERED** | Pass 14 — batch mass summaries |
| `data_integrity.py` | `robust_normalize_array`, `OutlierDetector`, `log_transform_normalize` | Percentiles, MAD, min–max, `log1p` scaling | QA / cleaning, not core timbre metrics | **LOW PRIORITY** | Optional **Pass 15 — data integrity normalisation** |
| `debug_counts.py` | `validate_debug_count_invariants` | Integer bookkeeping | Audit only | **IGNORE** | — |
| `interface.py`, `pipeline_orchestrator_*.py` | GUI / wiring | Parameter pass-through | No direct numeric semantics | **IGNORE** | — |
| `post_compile_research_export.py`, `tools/export_research_density_workbook.py` | Research exports | Mostly I/O + column rename | **LOW PRIORITY** unless thesis cites workbook algebra | **IGNORE** unless extended |

## 5. High-priority gaps

These are the **scientifically central** omissions relative to what the pipeline actually publishes:

1. **Remainder of `density.py`** — harmonic/inharmonic density calculators, perceptual/physical density, masking/noise floor, complexity/richness, effective power density/mass, subbass aggregates, combined density log combination, partial-density bundles.  
2. **`dissonance_models.py` (full model math)** — pairwise dissonance, timbre-shifted curves, local minima; currently **absent** from extraction passes.  
3. **`proc_audio.py` peak physics** — parabolic refinement, saddle prominence, local peak metrics; these **determine** which Hz/amplitudes enter almost every downstream formula.  
4. **`compile_metrics.py` density extraction & register normalisation** — `extract_density_*`, `apply_frequency_dependent_normalization`, weighted index / robust normalisation; **distinct** from the narrow Pass 9 helpers already extracted.  
5. **Batch power-mass renormalisation** — `finalize_batch_power_mass_summary` in `super_audio_analyzer.py` for batch % semantics.

## 6. Low-priority omissions

- **`apply_density_metric_df`**, **export alignment factors**, **plot_\*** helpers in `density.py` / `proc_audio.py` — documentation of display or Excel layout, not core measurement math.  
- **`data_integrity.py`** normalisers — valuable for QA papers, not for core spectral “timbre” claims.  
- **`compare_with_sethares_dissonance`** — thin comparison helper unless explicitly cited.  
- **PCA / t-SNE** paths in compile or orchestrator — rely on third-party implementations; at most document **input matrix construction**, not eigen-decomposition.

## 7. Recommendation

**Yes — additional formula-extraction passes are needed** if the goal is near-complete coverage of project-owned **published** metrics (density family, dissonance, compile-time corrections, and peak detection that feeds them).

### Proposed pass numbering (documentation only; no tables created here)

| Pass | Working title | Primary targets |
|------|----------------|-----------------|
| **Pass 11** | `density.py` extended metrics | Masking/noise floor; physical/perceptual density; harmonic/inharmonic list densities; complexity/richness/completeness; effective power density/mass; subbass aggregates; `calculate_combined_density_metric`; partial-density bundles; optional Bark |
| **Pass 12** | Dissonance models & export coupling | `dissonance_models.py`; `proc_audio.calculate_dissonance_metrics`; `compile_metrics.extract_dissonance_metrics` / sheet bridge (interfaces only; model internals stay project-owned) |
| **Pass 13** | Peak detection & f₀ refinement | `proc_audio` parabolic / prominence / SNR gates; `_correct_f0_candidate_against_prior`; nominal note→Hz helpers |
| **Pass 14** | Compile-time extraction & batch mass | `compile_metrics` density extraction + `apply_frequency_dependent_normalization` + weighted index / robust series; `note_to_midi` / `note_to_fundamental_freq`; `finalize_batch_power_mass_summary` |
| **Pass 15** (optional) | Data integrity normalisation | `data_integrity.py` only if QA / robustness is part of the thesis |

Until those passes exist, the current corpus should be described as **strong on the v5/v6 density spine and alignment gates**, but **not exhaustive** for the whole repository.

---

*Audit produced by static repository scan; no production code, tests, or formula-extraction tables were modified.*
