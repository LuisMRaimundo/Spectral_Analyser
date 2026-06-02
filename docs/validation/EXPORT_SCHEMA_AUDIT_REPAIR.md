# Export schema audit repair (v4.0.0+) + research formatting (v4.0.1) + export hygiene (v4.0.2) + metadata/sample_id (v4.0.3)

Addresses the architecture-level incongruences identified in the compiled/research
workbook audit (duplicate Note keys, `density_weighted_sum` semantic overload, phase-2
vs per-note weight conflation, Diagnostic column collisions, merge `_2` duplicates).

## Primary join key

| Column | Use |
|--------|-----|
| **`sample_id`** | **Primary key for joins** — stable per row; survives duplicate `Note` labels (e.g. two G#4 samples) |
| `Note` | Display / pitch label only — **not** safe as sole join key when duplicates exist |

Computed in Stage 2 `Density_Metrics` and propagated to satellite compiled sheets and
research exports (v4.0.2).

### Merge key selection (v4.0.2)

Research export (`merge_workbook_frames`) uses `merge_keys_for_frames`:

1. **`sample_id`** when both anchor and satellite carry the same authoritative IDs
   (full overlap with the anchor frame).
2. **`Note`** otherwise — including when satellite sheets pre-date `sample_id` or were
   written without it.

Satellite sheets must **not** receive synthetic `sample_id` values before merge; doing so
was the root cause of all-blank research columns (e.g. `f0_used_for_density_hz`, `n_fft`)
despite populated source sheets.

## Dead-column pruning (v4.0.2)

Columns that are entirely NaN or blank-like text are **dropped at write time** — they
are not retained as schema placeholders.

| Scope | Sheets affected |
|-------|-----------------|
| Stage 2 compile | `Density_Metrics`, `Canonical_Metrics`, `Diagnostic_Metrics`, `Debug_Counts`, `Per_Note_Processing_Metadata`, `Legacy_Compatibility` |
| Stage 3 research | `Spectral_Density_Metrics`, `Primary_Statistics_Eligible`, `Analysis_Settings_By_Note`, `Legacy_Compatibility`, `Charts_Data`, `Component_Balance`, `Validation_Summary` |

Protected columns (never dropped): `Note`, `sample_id`. All-zero numeric columns are kept.

Implementation: `export_row_identity.drop_dead_columns`.

## Metadata weight propagation (v4.0.3)

Research `Metadata` exports `harmonic_density_weight`, `inharmonic_density_weight`, and
`subbass_density_weight` as **corpus-level Phase-2 application weights**. Each key resolves
through its own fallback chain (`phase2_harmonic_application_weight`, etc.) — not through a
shared loop that always returned the harmonic value.

## Diagnostic `sample_id` (v4.0.3)

Satellite compiled sheets may carry an empty `sample_id` column (all NaN). These are now
treated as unpopulated; `attach_sample_id_from_density` in `export_row_identity.py` copies
authoritative IDs from `Density_Metrics` before Excel write.

## Research duplicate columns (v4.0.3)

After merge uniquification adds `_2` suffixes, `dedupe_identical_columns` runs again so
byte-identical suffix columns are removed before Excel write.

## Three density quantities (do not interchange)

| Canonical name | Legacy / companion column | Weights used | Sheet |
|----------------|---------------------------|--------------|-------|
| **`density_raw_phase2_profile_weighted`** | `density_metric_raw` | Phase-2 corpus application profile (H/I/S) | compiled |
| **`density_component_ratio_weighted_sum`** | `density_metric_raw_per_note_balance`, `density_weighted_sum` (compiled) | Per-note `component_*_energy_ratio` | compiled |
| **`richness_weighted_body_density`** | research `density_weighted_sum` | GUI weights × body-ceiling component sums | research |

Compiled `density_weighted_sum_alias_of` now correctly points to
`density_metric_raw_per_note_balance`, not `density_metric_raw`.

## Phase-2 vs per-note weights

| Column | Meaning |
|--------|---------|
| `phase2_harmonic_application_weight` (+ I/S) | Corpus-level adaptive profile applied to `density_metric_raw` |
| `component_harmonic_energy_ratio` (+ I/S) | Per-note **observed** energy ratios |
| `harmonic_density_weight` (Diagnostic sheet) | Renamed to `per_note_harmonic_energy_ratio_diagnostic` on export |

Global `Analysis_Metadata` no longer copies row-0 per-note weights into
`harmonic_density_weight` when phase-2 keys are present.

## Diagnostic vs Density_Metrics collisions

On `Diagnostic_Metrics`, raw-power / wide-frame variants are prefixed, e.g.
`diagnostic_harmonic_energy_sum_raw_power`,
`diagnostic_harmonic_full_spectrum_energy_sum_20khz_raw`.

## Research workbook

- **`Primary_Statistics_Eligible`** replaces `Primary_Statistics_Filtered` (eligibility gate, not QC exclusion).
- **`Stage3_Summary`** holds the former `__STAGE3_SUMMARY__` row; `Stage3_Diagnostics` is note-level only.
- **`sample_row_count`**, **`unique_midi_count`**, **`notes_count_semantics`** clarify row vs pitch counts.
- Identical merge duplicate columns (`*_2`) are dropped before Excel export when values match.
- **`EWSD_score_acoustic_balanced`:** red Excel **data bars** on `Spectral_Density_Metrics` (v4.0.1).

## Re-export required

| Target fix | Minimum re-run |
|------------|----------------|
| Schema aliases, diagnostic renames, `sample_id` PK | Stage 2 + 3 with **v4.0.0+** |
| EWSD red data bars | Stage 3 with **v4.0.1+** |
| Blank research columns (bad merge) | Stage 3 with **v4.0.2+** (or Stage 2+3 for compiled `sample_id`) |
| Metadata H/I/S weights, `_2` dedupe, research `zero_padding` | Stage 3 with **v4.0.3+** |
| `Diagnostic_Metrics.sample_id` on **compiled** workbook | Stage 2 with **v4.0.3+** |

Existing workbooks on disk retain old semantics until recompiled. For a full refresh after
v4.0.3, re-run **Stage 2 and Stage 3** on the corpus.

## Known ambiguous columns (still exported under legacy names)

v4.0.3 fixes Metadata weight **values** but does not yet rename all overloaded headers.
See **§R.8** in `docs/DENSITY_EXPORT_SCHEMA.md` and the three-density table above.
Prefer explicit columns: `density_metric_raw`, `density_metric_raw_per_note_balance`,
`richness_weighted_body_density_body_ceiling`, `phase2_*_application_weight`,
`component_*_energy_ratio`.

See also: `docs/DENSITY_EXPORT_SCHEMA.md`, `docs/EXPORT_COLUMN_DICTIONARY.md`, `CHANGES.md`.
