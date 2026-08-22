# ACD `erb_fraction` sensitivity

The previous sweep placed tones 8 ERB apart, which cannot merge at any `erb_fraction <= 1.5`. That test could not fail, so the claim "usable range at least [0.5, 1.5]" is **unsupported and discarded**.

This document uses a 40-partial 1/n series at f0 = 146.83 Hz, where adjacent partials first fall inside one ERB at partial 8 (`146.83 <= 0.108 f + 24.7` gives `f >= 1131 Hz`). Merge strategy is the Task 1 default **`fixed_erb_grid`**. Default `erb_fraction` remains 1.0.

## Reference merged counts (both strategies)

| erb_fraction | moving centroid | fixed grid |
|---:|---:|---:|
| 0.25 | 38 | 40 |
| 0.5 | 26 | 32 |
| 0.75 | 19 | 26 |
| 1 | 16 | 22 |
| 1.5 | 12 | 17 |
| 2 | 9 | 14 |

## Harmonic series at f0 = 146.83 Hz (`fixed_erb_grid`)

Unmerged D1 = 4.466. D1 == N=40 does not hold at any tested fraction: a 1/n law already concentrates energy, so D1 is a dominance-weighted count, not the raw partial census.

| erb_fraction | merged_count | D0 | D1 | D2 |
|---:|---:|---:|---:|---:|
| 0.25 | 40 | 40.000 | 4.466 | 2.426 |
| 0.5 | 32 | 32.000 | 4.427 | 2.425 |
| 0.75 | 26 | 26.000 | 4.384 | 2.425 |
| 1 | 22 | 22.000 | 4.320 | 2.425 |
| 1.5 | 17 | 17.000 | 4.191 | 2.423 |
| 2 | 14 | 14.000 | 4.050 | 2.420 |

## K-recovery on this series

- `merged_count == 40` (every partial still resolved): [0.25, 0.25].
- `D1` within 1 % of the unmerged 1/n value 4.466: [0.25, 0.5].
- `D1 == 40` within 1 %: **never**, including at `erb_fraction = 0.25` where nothing merges.

`merged_count` is the more sensitive parameter: from `erb_fraction = 0.25` to `2.0` it changes by 65.0%, while D1 changes by 9.3%. D2 is nearly flat (2.426 → 2.420), which is the saturation documented in `ACD_THEORY.md`.

## Register dependence (fixed 40-partial 1/n, `erb_fraction = 1.0`)

Merging is register-dependent by design: upper partials of low notes are unresolved and should merge. That effect will appear in any corpus result as an apparent correlation between density and pitch.

| f0 (Hz) | merged_count | D1 | D2 |
|---:|---:|---:|---:|
| 65.4 | 20 | 4.250 | 2.424 |
| 146.8 | 22 | 4.320 | 2.425 |
| 261.6 | 22 | 4.320 | 2.425 |
| 523.3 | 23 | 4.334 | 2.425 |
| 1046.5 | 23 | 4.342 | 2.425 |

D1 rises from 4.250 at 65.4 Hz to 4.342 at 1046.5 Hz (+2.2%) at fixed harmonic structure. The low-note merged count is smaller because more upper partials share an ERB-rate bin.

## Synthesised D3 through Stage 1

Same synthesised D3 as the merge-strategy sweep, scored under `fixed_erb_grid` at production `n_fft = 8192`.

| erb_fraction | merged_H+I+S | ACD_score (D1) | ACD_D1 | ACD_D2 |
|---:|---:|---:|---:|---:|
| 0.25 | 108 | 2.98168185063 | 2.98168185063 | 1.95640441614 |
| 0.5 | 72 | 2.94911798292 | 2.94911798292 | 1.93042203567 |
| 0.75 | 54 | 2.93796158992 | 2.93796158992 | 1.92475585729 |
| 1 | 45 | 2.93155096578 | 2.93155096578 | 1.917334178 |
| 1.5 | 33 | 2.88827744216 | 2.88827744216 | 1.91082582866 |
| 2 | 28 | 2.84941236851 | 2.84941236851 | 1.90951886175 |

## Cross-reference

Default `ERB_FRACTION_DEFAULT = 1.0` is unchanged. See `docs/CONSTANTS_PROVENANCE.md` and `docs/validation/ACD_MERGE_STRATEGY.md`.
