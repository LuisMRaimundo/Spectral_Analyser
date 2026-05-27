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

<!-- TODO(author): expand R.1–R.3 with any further constraints required by the
     publication workflow; add R.4 ff. as needed. -->
