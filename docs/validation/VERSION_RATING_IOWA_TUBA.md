# Version rating — IOWA tuba *pp* and repo epochs

> **DEPRECATED (WP6 / v4.2.0).** This 1–100 expert-judgement scorecard is
> archival. It is **not** the freeze acceptance record. Measurable
> acceptance for Phases A–I, D1–D6, and WP1–WP6 is
> [`UPGRADE_PROGRAMME_STATUS.md`](UPGRADE_PROGRAMME_STATUS.md). Do not
> quote these scores as a current rating of the tagged instrument.

Expert judgement on a **1–100** scale. Not a formula, not a listener test, and
not a full 37-note Stage 2/3 recompile under the latest code.

**Date:** 19 August 2026  
**Latest code:** commit `70525e3` on `main` (exclusive assignment +
validated-partial gating; `export_schema_version` =
`spectral_analysis_schema_2026_08`)  
**Package tag:** v4.1.0 (`pyproject.toml`). Installed wheels may still stamp
`analysis_version = 4.0.3`.

## Headline scores

| Version | Acoustics | Accuracy | Software | **Overall** |
|---------|----------:|---------:|---------:|------------:|
| Análise 1 · original · 8 Aug | 73 | 72 | 84 | **75** |
| Análise 2 · uncapped · 18 Aug · v4.0.3 | 64 | 62 | 84 | **68** |
| Análise 3 · v4.1.0 policy v2 · 19 Aug | 86 | 87 | 90 | **87** |
| **Current · `70525e3` · exclusive + gating** | **91** | **92** | **93** | **92** |

Weights: **50%** acoustics / musicology, **30%** accuracy and robustness,
**20%** software.

**Current (`70525e3`) is the first version that is safe to quote on A2.**
Included set is H1–H8. `effective_partial_density` is 3.77 (was 24.6 on
Análise 2). Sethares uses 8 partials / 28 pairs (was 41 / 820). Amplitude
inharmonic share is 0% (was 15.6%). Peak-bin invariant passes. Pitch labels
are A2 / A3 / E4 / A4 / C♯5 / E5 / G5 / A5, not “A2” on every harmonic row.

## What was scored

### IOWA tuba *pp* result folders (do not mix)

| Run | Path | Code / window | Date |
|-----|------|----------------|------|
| Análise 1 | `…\IOWA_tuba_pp\_Sustains\analysis_results_1\` | original, full `_Sustains` | 8 Aug 2026 |
| Análise 2 | `…\IOWA_tuba_pp\_Sustains_Stable\analysis_results_2\` | former / uncapped, SustainStable | 18 Aug 2026 21:49 |
| Análise 3 | `…\IOWA_tuba_pp\_Sustains_Stable\analysis_results\` | v4.1.0 policy v2, SustainStable | 19 Aug 2026 07:30 |
| Current | `…\IOWA_tuba_pp\_Sustains_Stable\analysis_results_phase13\` | `70525e3`, A2 re-export | 19 Aug 2026 |

A2 take (Análise 2 critique):  
`…\analysis_results_2\IOWA_Tub.pp.A2_SustainStable`  
Audio: `…\_Sustains_Stable\IOWA_Tub.pp.A2_SustainStable.aif`  
Phase-13 workbook: `…\analysis_results_phase13\A2\spectral_analysis.xlsx`

### Sources

- A2 run-2 vs phase-13 re-export
- `analysis_results_2` duplicate-bin scan (11 of 37 notes)
- `CHANGES.md`, TECHNICAL_MANUAL §5.2.1 / §5.4 / §14.4
- Schema notes in `docs/DENSITY_EXPORT_SCHEMA.md` §R.8–R.10

This is expert judgement on that record. Stage 2/3 numbers on disk for the
full tuba corpus are still Análise 3 unless re-exported.

## IOWA tuba *pp* — four versions compared

| Version | What it would have you believe about tuba *pp* |
|---------|------------------------------------------------|
| Análise 1 · original · 8 Aug | Same ears as v4.0.x. Join keys work. Low C still harvests floor into the harmonic list on the full `_Sustains` set. |
| Análise 2 · uncapped · 18 Aug · v4.0.3 | A2 H109–111 share 12 094 Hz. C1 reports 183 included harmonics. 11 notes have duplicated included bins. EPD 24.6 vs ~3.8 real harmonics. Worst of the four for this corpus. |
| Análise 3 · v4.1.0 policy v2 · 19 Aug | C1 33 / 68.1. A2 included set is H1–H8. H110 still `strict_validated` above the stop. EPD still ~23; amplitude pie still ~78 / 4 / 18. |
| Current · `70525e3` | A2: 8 included, EPD 3.77, dissonance 8, I = 0, invariant passed. Pitch names are the partials. Floor no longer enters F-012 or Sethares. |

Análise 2 scores **below** Análise 1 even though the software family is the
same (v4.0.3). Acoustics and accuracy drop because SustainStable + uncapped
high-*n* matching published C1 at 183 and A2 as 11 “harmonics”. C1 is the
worst run-2 note (226 included rows). Análise 1 is less spectacularly wrong
on those two notes, so it rates higher even though it lacks policy v2.

## Repo epochs (longer line)

Same weights as the four-run table.

| Epoch | Acoustics | Accuracy | Software | Overall |
|-------|----------:|---------:|---------:|--------:|
| Early pipeline | 38 | 32 | 42 | **37** |
| Phases 1–7 | 56 | 54 | 62 | **57** |
| May 29–30 closure | 70 | 68 | 72 | **70** |
| v3.9 EWSD | 73 | 71 | 76 | **73** |
| v4.0.x | 73 | 72 | 84 | **75** |
| Cap + stop (pre-main polish) | 74 | 76 | 86 | **77** |
| v4.1.0 main / Análise 3 | 86 | 87 | 90 | **87** |
| Exclusive + gating (`70525e3`) | 91 | 92 | 93 | **92** |

## A2 evidence for the +5 from v4.1.0 to current

| Consumer | Análise 2 | Análise 3 (v4.1.0) | Current `70525e3` |
|----------|-----------|--------------------|-------------------|
| Included harmonics | 11 (1–8 + 109–111) | 8 (H1–H8) | 8 (H1–H8) |
| `effective_partial_density` | 24.60 | 22.9 | **3.77** |
| `dissonance_partial_count` | 41 | 8 | 8 |
| Amplitude pie H / I / S (%) | 69.5 / 15.6 / 14.9 | 77.8 / 3.8 / 18.4 | **88.6 / 0.0 / 11.4** |
| Peak-bin invariant | fail (bin 4493 ×3) | pass (no triple) | pass |
| H109–111 reason | included, same bin | `above_harmonic_body_stop` | above stop; 3 distinct bins |

On the live A2 take, exclusive assignment finds three different nearby floor
bins (12 011.6 / 12 094.3 / 12 191.7 Hz), all inside \(\beta\cdot f_0\). They
are labelled `above_harmonic_body_stop`, not `rejected_by_tolerance`. The
synthetic test (one peak forced onto three *n*) still yields one assignment
and `rejected_by_tolerance` on the losers.

## How to read the 87 → 92 jump

Almost none of it is a new fatness formula. v4.1.0 already had the right comb
and the body stop. Current stops the remaining floor leak into F-012, the
amplitude pie, and Sethares, and makes peak ownership exclusive.

## Why current is not 100

- Spacing cap alone still accepts H110 (\(|\Delta|\approx 11\,\mathrm{Hz} <
  \beta\cdot f_0 \approx 33\,\mathrm{Hz}\)). The body stop is what keeps it
  out of density. If the stop were off, one floor peak would return.
- Amplitude S is ~11% because F-020 members keep linear mass. Energy S is
  ~0. That pie still is not the energy pie.
- Workbooks can still stamp `analysis_version` 4.0.3.
  `component_energy_pie.png` remains a copy of the amplitude pie.
  `canonical_density` still follows the stop-trimmed list.
- There is no confirmed-inharmonic class yet (inharmonic share gated to 0
  by design).
- The full tuba corpus is not yet re-exported under `70525e3`. Stage 2/3
  numbers on disk are still Análise 3.

The leftover ~8 points are stamp/alias hygiene, the missing
confirmed-inharmonic class, stop-bounded `canonical_density`, and the fact
that H110 is still a validated-looking row above the stop.

## Cross-run rule

Workbooks exported **before** exclusive assignment + validated-partial
gating are **not comparable** to post-phase exports on
`effective_partial_density`, amplitude pies, Sethares, or validated
harmonic counts. See `docs/validation/EWSD_CONSTRUCT_VALIDITY.md`
(pre-phase Stage 1 workbooks). Cross-run comparison requires a Stage 1
re-export, then Stage 2 + 3.

F-042 / F-047 / F-048 / F-049 algebra is unchanged; only the input domain
(`validated_partials_only`) changed.

## Related documentation

- `CHANGES.md` — exclusive assignment and gating change log
- `docs/TECHNICAL_MANUAL_COMPLETE.md` §5.2.1 / §5.4 / §14.4
- `docs/DENSITY_EXPORT_SCHEMA.md` §R.8–R.10
- `docs/validation/EWSD_CONSTRUCT_VALIDITY.md`
- `docs/validation/NOTE_FATNESS_AND_DENSITY_GUIDE.md`
