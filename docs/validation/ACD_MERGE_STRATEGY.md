# ACD merge strategy — fixed ERB grid vs moving centroid

Stage 1 peak lists from the same synthesised D3 (f0 = 146.83 Hz, two inharmonics) used in the real-note FFT-tier sweep. Each workbook is scored under both merge strategies; Stage 1 is not re-run per strategy. ACD here is still the D2-based score (`q = 2`) so the numbers are comparable to the earlier ±3.8 % wander.

## Decision

Default merge strategy: **`fixed_erb_grid`**.

`fixed_erb_grid` reduced the measured wander from 4.19% to 3.26% and is therefore the default. The moving-centroid strategy remains available as `merge_strategy="moving_centroid"`.

Neither strategy reduced the tier wander below ~2 %. Hard assignment (a peak belongs to one cluster or one ERB-rate bin) is the limiting factor. The identified next step is roex-overlap weighting — smooth partial assignment by auditory-filter overlap rather than hard binning. That is a docstring stub only; it is not implemented here.

Enforced relative tolerance: **5%** (winning-strategy max |Δ%| plus 1 percentage point, rounded up).

## Tier sweep (synthesised D3 through Stage 1)

### `moving_centroid`

Base ACD (`n_fft = 8192`): 2.88069057853. Max |Δ%| = 4.19.

| n_fft | ACD_score | ACD_Δ% | ACD_D2 | merged_H | merged_I | merged_S |
|---:|---:|---:|---:|---:|---:|---:|
| 16384 | 2.76008680072 | -4.1866 | 1.83285262914 | 22 | 5 | 1 |
| 8192 | 2.88069057853 | +0.0000 | 1.90528712764 | 22 | 6 | 1 |
| 4096 | 2.82042769126 | -2.0920 | 1.85733965096 | 22 | 5 | 1 |
| 2048 | 2.86441848368 | -0.5649 | 1.89374622384 | 23 | 6 | 1 |

### `fixed_erb_grid` (winner)

Base ACD (`n_fft = 8192`): 2.93155096578. Max |Δ%| = 3.26.

| n_fft | ACD_score | ACD_Δ% | ACD_D2 | merged_H | merged_I | merged_S |
|---:|---:|---:|---:|---:|---:|---:|
| 16384 | 2.83588119035 | -3.2635 | 1.86775959465 | 33 | 6 | 4 |
| 8192 | 2.93155096578 | +0.0000 | 1.917334178 | 33 | 8 | 4 |
| 4096 | 2.86086052972 | -2.4114 | 1.86481283118 | 33 | 7 | 3 |
| 2048 | 2.90216132673 | -1.0025 | 1.89564015053 | 34 | 8 | 1 |

## Perturbation guard (clean 1/n series)

Forty-partial 1/n series at f0 = 146.83 Hz; +1 dB applied to one partial at a time in 7–14 (where adjacent partials first fall inside one ERB). `fixed_erb_grid` `merged_count` is invariant. On this clean series both strategies move D2 by a fraction of a percent and neither flips the count; instability, if present, shows on the Stage 1 peak lists above.

