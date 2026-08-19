# CANONICAL_PIPELINE_AND_EXPORT_SEMANTICS — Normative pipeline reference

> **Status:** normative for pipeline and export semantics (package **v4.1.0**). Skeleton
> sections marked `TODO(author)` remain for full Stage-1/2 inventories; §3–4, §9, §A, and §11
> are maintained for current behaviour.

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

Stage 1 publishes `f0_used_for_density_hz` after the robust / nominal-guided fit
(`f0_acceptance_mode`). Before the policy-v2 harmonic match, H1–H8 are matched
with the cents limb only (SNR ≥ 20 dB, prominence ≥ 12 dB). An
amplitude-weighted least-squares f0 (and B) is fitted on those peaks. When
`|1200 log2(f0_refit / f0_joint)| > 15` cents the refit becomes the match
centre (`f0_refit_applied = True`). See TECHNICAL_MANUAL §5.2.1 and F-053.

## 4. Harmonics

A candidate is a harmonic when a local peak falls inside the policy-v2
half-width around the Inharmonicity_Fit prediction
`n · f0 · √(1 + B n²)` (B off ⇒ ideal comb). The half-width is
`tol_hz(n) = max(bin, min(n·f0·τ_n/1200, β·f0))` with `β = 0.30`.
`include_for_density` is cleared above `harmonic_body_stop_hz` (validation
cut). Strict acceptance still requires CFAR + saddle prominence (F-043).
First-pass B (including 0) is the second-pass stretch when ≥ 3 low-order
peaks were used; a global peak-centre B is not allowed to invent stretch
on a harmonic instrument.

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
parts; worksheet-level AutoFilter is used on data sheets.

**Stage 3 (EWSD-R v18).** Inside `tools/export_research_density_workbook.build_workbook`,
after the research frame is assembled, `tools/ewsd_research_integration` discovers
per-note `spectral_analysis.xlsx` files under the analysis folder, recomputes EWSD with
`individual_exact` mode, and left-joins scores on `Note` into `Spectral_Density_Metrics`.
H/I/S ratios are read from each note's Metrics sheet (`auto_excel_required`); rows without
valid ratios are not silently filled with H=I=S=1. Use `ewsd_primary_analysis_eligible`
for thesis-facing statistics; prefer `EWSD_score_acoustic_balanced` for cross-instrument
bibliographic distance. See `docs/DENSITY_EXPORT_SCHEMA.md` §R.4 and
`docs/TECHNICAL_MANUAL_COMPLETE.md` §7.8.

For the full schema of the research workbook see `docs/DENSITY_EXPORT_SCHEMA.md` §R.

**Export row identity (v4.0.2–v4.0.3).** Stage 2 and Stage 3 delegate join and hygiene
helpers to `export_row_identity.py`:

- `assign_sample_ids` / `compute_sample_id` — authoritative per-row primary key on
  `Density_Metrics`.
- `attach_sample_id_from_density` — copies `sample_id` onto satellite compiled sheets
  (v4.0.3: NaN placeholder columns treated as unpopulated).
- `merge_keys_for_frames` — research merge prefers `sample_id` when IDs align, else `Note`.
- `drop_dead_columns` — omits never-populated columns at Excel write.
- `dedupe_identical_columns` — drops byte-identical `*_2` suffix columns (v4.0.3: also
  after header uniquification in research export).

## 11. Export schema version map (v4.0.0–v4.1.0)

| Version | Scope | Key behaviour |
|---------|-------|----------------|
| v4.0.0 | Schema repair | `sample_id` PK; diagnostic column prefixes; three-density naming; `Primary_Statistics_Eligible`; `Stage3_Summary` |
| v4.0.1 | Research formatting | Red data bars on `EWSD_score_acoustic_balanced` |
| v4.0.2 | Export hygiene | `merge_keys_for_frames`; dead-column pruning; satellite `sample_id` propagation |
| v4.0.3 | Metadata + dedupe | Distinct Phase-2 H/I/S in research `Metadata`; `Diagnostic_Metrics.sample_id` fill; post-uniquify dedupe; numeric `zero_padding` per note |
| v4.1.0 | Low-f₀ harmonic identity | Spacing-capped match; f0/B refit; body-stop count cut; noise-gated mass; `density_fragile`; `density_effective_ceiling_hz` = global 20 kHz |

**Re-export:** v4.0.3 schema refresh requires Stage 2 + Stage 3. v4.1.0 harmonic
identity requires Stage 1 + 2 + 3. See
`docs/validation/EXPORT_SCHEMA_AUDIT_REPAIR.md` § Re-export required.

**Column traps:** same header, different meaning — `docs/DENSITY_EXPORT_SCHEMA.md` §R.8.

## 10. Audit CLI

<!-- TODO(author): document `tools/audit_compiled_workbook.py` — invocation, exit codes,
     and the checks it performs. -->

## A. Naming caveat: spectral fatness vs. classical density

This section is referenced from `density.py` and `compile_metrics.py`.

**Primary fatness scalar (F-047):** `note_effective_component_density` on `Density_Metrics`
and research `Spectral_Density_Metrics` — pooled participation ratio over harmonic +
inharmonic + sub-bass components. Use this column when the research question is “how many
effective partials carry energy on this note?”

**Harmonic-only fatness (F-045):** `harmonic_effective_partial_count`.

**Legacy name:** `effective_partial_density` is retained for historical continuity on
`Density_Metrics`. The name `effective_partial` **diverges conceptually** from
"classical" spectral-density framings associated with Krimphoff et al. (1994) and
Peeters et al. (2011): these metrics operate on identified partials (harmonic plus
nonharmonic peaks above the noise floor), weighted by the project's amplitude/energy
policy, rather than on a continuous power spectrum.

Authors citing this codebase should not equate `effective_partial_density` or
`note_effective_component_density` with Krimphoff-Peeters spectral density without
explicit qualification. For weighted H/I/S content use `note_density_final` (§2.1);
for cross-instrument comparative density use `EWSD_score_acoustic_balanced` (§R.4).

Practical lookup: `docs/validation/NOTE_FATNESS_AND_DENSITY_GUIDE.md`.

<!-- TODO(author): add bibliographic anchors (APA-7) and confirm the section-letter
     designator A (or renumber to a §11 form if preferred for sequential citation). -->
