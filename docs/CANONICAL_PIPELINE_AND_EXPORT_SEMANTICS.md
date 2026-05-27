# CANONICAL_PIPELINE_AND_EXPORT_SEMANTICS — Normative pipeline reference

> **Status:** scaffolded skeleton. Normative content is to be authored by the project author.
> This document is the single source of truth for the canonical Stage-1 / Stage-2 pipeline
> and for export semantics that follow from it.

## 1. Scope and authority

This document is normative. Where any other document under `docs/` or in the repository
root conflicts with this one, this document prevails.

<!-- TODO(author): state the precedence rule explicitly and date it. -->

## 2. Pipeline overview

Stage 1 (`proc_audio.AudioProcessor`) produces per-note `spectral_analysis.xlsx`
plus standard PNGs (spectrogram, amplitude-mass pie, energy-ratio pie, and the legacy-alias
`component_energy_pie.png`).

Stage 2 (`compile_metrics.compile_density_metrics_with_pca`) consumes the per-note
workbooks and produces `compiled_density_metrics.xlsx`.

<!-- TODO(author): expand with the exact preconditions, postconditions, and invariants
     of each stage. -->

## 3. Fundamental frequency (`f0`)

<!-- TODO(author): document the f0 estimation policy, the tolerance bands, and the
     fallback behaviour when estimation fails. -->

## 4. Harmonics

<!-- TODO(author): definition of harmonic partials in this codebase (including the
     inharmonicity-coefficient B model used by `inharmonicity_model.py`). -->

## 5. Nonharmonics

<!-- TODO(author): operational definition of nonharmonic peaks; threshold policy. -->

## 6. Subfundamental band

<!-- TODO(author): subbass policy as implemented in `subbass_policy.py` and
     `low_frequency_policy.py`. -->

## 7. `Debug_Counts` semantics

<!-- TODO(author): document each Debug_Counts column with its operational definition
     and the function that emits it. -->

## 8. Missing metrics policy

<!-- TODO(author): when a metric cannot be computed (insufficient harmonics, silent
     frame, etc.), document the sentinel value, the column flag, and the downstream
     consequence. -->

## 9. Research workbook hook

This section is referenced from `post_compile_research_export.py`. The research workbook
is built as a read-only post-process beside the compiled workbook. The hook is safe to
call after a successful Stage-2 compile; failures inside the hook are logged and do not
affect analysis status. The research workbook is written without formal Excel `Table`
parts; worksheet-level AutoFilter is used on data sheets. For the full schema of that
workbook see `docs/DENSITY_EXPORT_SCHEMA.md` §R.

## 10. Audit CLI

<!-- TODO(author): document `tools/audit_compiled_workbook.py` — invocation, exit codes,
     and the checks it performs. -->

## A. Naming caveat: `effective_partial_density` vs. classical density

This section is referenced from `density.py`.

`effective_partial_density` is the primary public spectral-fatness scalar emitted on the
`Density_Metrics` sheet of `compiled_density_metrics.xlsx`. The name `effective_partial`
is retained for historical-continuity reasons. The metric **diverges conceptually** from
"classical" spectral-density framings associated with Krimphoff et al. (1994) and
Peeters et al. (2011): it operates on identified partials (harmonic plus nonharmonic
peaks above the noise floor), weighted by the project's amplitude/energy policy, rather
than on a continuous power spectrum.

Authors citing this codebase should not equate `effective_partial_density` with
Krimphoff-Peeters spectral density without explicit qualification.

<!-- TODO(author): add bibliographic anchors (APA-7) and confirm the section-letter
     designator A (or renumber to a §11 form if preferred for sequential citation). -->
