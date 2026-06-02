# Manual Coverage Report

## Scope

Documentation-only pass synchronized to the current repository state after Phase 8, constants-provenance registry completion, and formula-validation suite introduction.

Generated deliverables:

1. `docs/TECHNICAL_MANUAL_COMPLETE.md`
2. `docs/METRIC_FORMULA_INDEX.md`
3. `docs/GUI_OPTION_REFERENCE.md`
4. `docs/EXPORT_COLUMN_DICTIONARY.md`
5. `docs/MANUAL_COVERAGE_REPORT.md`

---

## Files inspected

- `proc_audio.py`
- `acoustic_density_core.py`
- `density.py`
- `compile_metrics.py`
- `pipeline_orchestrator_gui.py`
- `adaptive_density_engine.py`
- `subbass_policy.py`
- `low_frequency_policy.py`
- `inharmonicity_model.py`
- `spectral_normalization.py`
- `mir_descriptors.py`
- `temporal_segmentation.py`
- `note_parser.py`
- `constants.py`
- `tools/export_research_density_workbook.py`
- `metrics_dictionary.json`
- `docs/CONSTANTS_PROVENANCE.md`
- `docs/validation/FORMULA_VALIDATION_STATUS.md`
- `docs/parameter_provenance.md` (legacy Phase-6 ledger retained for historical context)
- `CHANGES_PHASE_7.md`
- `interface.py` (legacy GUI reference surface; archived to `Backup/root_modules/`)

Keyword sweep executed for:

- `density_`, `harmonic`, `inharmonic`, `subbass`, `weighted`, `entropy`, `roughness`, `dissonance`, `sethares`
- `spectral_`, `tristimulus`, `centroid`, `flatness`, `rolloff`, `skewness`, `kurtosis`, `irregularity`, `ERB`, `Bark`
- `f0`, `inharmonicity`, `tier_normalized`, `Validation_Summary`, `obs_w`, `pure_observation`, `phase2`
- `PCA`, `UMAP`, `t-SNE`, `anomaly`, `LogAttackTime`, `attack`, `sustain`, `release`

---

## Metrics documented

Documented metric families include:

- STFT/magnitude/power/bin-frequency definitions.
- F0 provenance and cents deviation.
- Harmonic/inharmonic/subbass decomposition and occupancy.
- Subbass policy boundary and low-frequency diagnostics.
- Inharmonicity `B` fit model and fit-status semantics.
- Density components (`D_H`, `D_I`, `D_S`) and weighted raw metrics.
- Per-note energy-ratio weighting and profile-based weighting.
- Adaptive Phase 1 observation and Phase 2 profile application.
- Tier normalization factors and normalized sum columns.
- Spectral entropy and effective density constructs.
- MIR descriptors (centroid, spread, skewness, kurtosis, irregularity, tristimulus, flatness, rolloff, roughness proxy, ERB density).
- Temporal segmentation (attack/sustain/release and log attack time).
- Validation/warning and legacy-alias semantics.

---

## GUI options documented

Documented GUI option surfaces:

- Tk orchestrator (`pipeline_orchestrator_gui.py`) complete core controls.
- PyQt reference GUI (`interface.py`) exploratory/legacy controls (archived to `Backup/root_modules/`).

Covered controls:

- weight function, density mode, component weights;
- salience threshold, density ceiling;
- STFT parameters and tier mode;
- tolerance and adaptive tolerance;
- dissonance model options;
- compile, PCA, t-SNE, UMAP, anomaly controls;
- manual model-weight override and contamination.

---

## Exported sheets documented

Compiled workbook sheets documented:

- `Density_Metrics`
- `Canonical_Metrics`
- `Canonical_Primary_Filtered`
- `Diagnostic_Metrics`
- `Legacy_Compatibility`
- `Legacy_Aliases`
- `Debug_Counts`
- `Validation_Metrics`
- `Validation_Summary`
- `Per_Note_Processing_Metadata`
- `Analysis_Metadata`
- optional PCA and dissonance sheets

Research workbook sheets documented:

- `Spectral_Density_Metrics`
- `Primary_Statistics_Eligible`
- `Component_Balance`
- `Validation_Summary`
- `Charts_Data`
- `Legacy_Compatibility`
- `Analysis_Settings_By_Note`
- `Metadata`
- `Dashboard`
- `README`

---

## Exported columns not documented

No intentionally skipped exported columns in the explicitly enumerated lists for:

- `Density_Metrics` (compiled minimal display export list),
- `Canonical_Metrics`,
- research `Spectral_Density_Metrics`,
- research `Component_Balance`,
- research `Validation_Summary`,
- research `Charts_Data`.

Notes:

- Some compiled workbook auxiliary sheets (`Compiled Metrics`, `Compiled_Metrics_All`, optional debug/correlation variants) are highly dynamic supersets; manual references them at sheet level and documents the canonical/primary column families directly.

---

## Intentionally excluded direct external-package calls

Excluded from formula-level documentation unless wrapped/modified by project logic:

- direct `numpy` reducers/array ops (`mean`, `sum`, `sqrt`, etc.) when used as primitives;
- direct `scipy` filter/transform function internals;
- direct `pandas` I/O and dataframe utility calls;
- direct sklearn implementation internals (`PCA`, `TSNE`, `IsolationForest`, `UMAP`) where project only configures/invokes them.

Included where project-level transformation/wrapping is present.

---

## Current caveats

1. Formula-validation coverage is proportionate by design (F1–F6), not exhaustive over every helper expression.
2. Research workbook currently does not expose full inharmonicity field family present in compiled `Density_Metrics`.
3. Legacy and canonical GUI surfaces overlap but are not fully identical; Tk orchestrator remains canonical.

---

## Second-pass status table

| Item | Status | Notes |
|---|---|---|
| Expand `metrics_dictionary.json` beyond Phase 5 only | resolved | registry now includes canonical/diagnostic/validation and phase 1/2/3/4/7 families documented in manual |
| Document dynamic auxiliary sheets (`Compiled Metrics`, `Compiled_Metrics_All`, optional debug/correlation/PCA/dissonance sheets) | resolved | added explicit generation-rule section in `EXPORT_COLUMN_DICTIONARY.md` |
| Add compiled/research crosswalk across `Density_Metrics`, `Spectral_Density_Metrics`, `Component_Balance`, `Validation_Summary`, `Analysis_Settings_By_Note` | resolved | added crosswalk table with omission reasons |
| Explicitly document research workbook inharmonicity family gap | resolved | documented in `EXPORT_COLUMN_DICTIONARY.md` and manual limitations section |
| Add manual section: known documentation and provenance limitations | resolved | added `19A. Known documentation and provenance limitations` in manual |
| Keep dynamic-sheet caveat explicit | intentionally unresolved | full column enumeration is intentionally not stable due to runtime-conditional generation |
| Stage 3 EWSD-R v18 in research export | resolved | `tools/ewsd_core.py`, `tools/ewsd_research_integration.py`, `tests/phase_11/`, manual §7.8, schema §R.4 |
| Full inharmonicity family in research workbook | requires code/export change | export mapping in `tools/export_research_density_workbook.py` still omits `inharmonicity_*` set |
| Constants provenance registry completion | resolved | `docs/CONSTANTS_PROVENANCE.md` now classifies constants as `primary_source` / `derived` / `convention` / `internal_default` |
| Formula-validation baseline (F1–F6) | resolved | `tests/formula_validation/` and `docs/validation/FORMULA_VALIDATION_STATUS.md` added |
