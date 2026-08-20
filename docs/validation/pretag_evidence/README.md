# Pre-tag evidence archive

These artefacts were produced under pre-tag commits (`6b0e51a`,
`ec0a99a`). They are **non-citable** for publication. They are archived
here only as baselines for the post-retag re-exports
(`docs/REEXPORT_RUNBOOK.md`).

Do not treat a number on these workbooks as a `v4.2.1` result. Findings
extracted from them are in
[`docs/validation/PRETAG_FINDINGS_SUMMARY.md`](../PRETAG_FINDINGS_SUMMARY.md);
every row there is labelled “pre-tag; to be reproduced under the freeze
tag”.

## Index

| File | Commit | Corpus | Dynamic | Date |
|------|--------|--------|---------|------|
| `trombone_pp_compiled_density_metrics_research.xlsx` | `6b0e51a` | IOWA tenor trombone, `_Sustains_Stable` (Test tree) | pp | 19 Aug 2026 |
| `trombone_mf_compiled_density_metrics_research.xlsx` | `6b0e51a` | IOWA tenor trombone, `_Sustains_Stable` (Test tree) | mf | 19 Aug 2026 |
| `trombone_ff_compiled_density_metrics_research.xlsx` | `6b0e51a` | IOWA tenor trombone, `_Sustains_Stable` (Test tree) | ff | 19 Aug 2026 |
| `flute_pp_compiled_density_metrics_research.xlsx` | `6b0e51a` | IOWA flute, `_Sustains_Stable` (Test tree) | pp | 19 Aug 2026 |
| `flute_mf_compiled_density_metrics_research.xlsx` | `6b0e51a` | IOWA flute, `_Sustains_Stable` (Test tree) | mf | 19 Aug 2026 |
| `flute_ff_compiled_density_metrics_research.xlsx` | `6b0e51a` | IOWA flute, `_Sustains_Stable` (Test tree) | ff | 19 Aug 2026 |
| `cordas/EWSD_acoustic_balanced_CORDAS_report.md` | pre-tag (`D:\CORDAS_2` trees) | CORDAS_2 (54 research workbooks) | mixed | 20 Aug 2026 |
| `cordas/ewsd_balanced_analysis.json` | same | CORDAS_2 | mixed | 20 Aug 2026 |
| `cordas/ewsd_balanced_note_rows.csv` | same | CORDAS_2 | mixed | 20 Aug 2026 |

Provenance on the six brass/woodwind workbooks:
`package_version` 4.1.0, `git_describe`
`v0.1.0-validated-2026-05-15-242-g6b0e51a`. Residual exclusion is
still ENBW (D1–D5 / WP1 are later).

## Not placed

These items named by the remediation prompt were **not** found on disk
as standalone files (user did not drop them into this folder; a search
of `D:\CORDAS_2`, `D:\METAIS`, and the Desktop rating folder did not
yield a matching artefact):

| Missing artefact | Notes |
|------------------|-------|
| Cello five-column comparison sheet | Not located. G2 contrast numbers remain in `SEGMENTATION_CASE_STUDY_G2.md`. |
| Two G2 workbooks (stable / full) | No `_Sustains` (full) G2 pair found beside the CORDAS `_Sustains_Stable` trees. Iowa cello G *ff* has no research workbook. |
| Automatic-vs-manual segmentation comparison (26 notes) | Not located. |

If those files are supplied later, add a row to this index and a
source-artefact pointer in `PRETAG_FINDINGS_SUMMARY.md`. Do not treat
the case-study markdown numbers as a substitute workbook.
