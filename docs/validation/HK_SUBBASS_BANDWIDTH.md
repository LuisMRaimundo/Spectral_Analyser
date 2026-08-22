# Hutchinson–Knopoff sub-bass bandwidth

`HutchinsonKnopoffDissonance.cbw` remains `1.72 · f^0.65` by default
(`low_frequency_basis="hk1978"`). At 50 Hz that is ~21.7 Hz against
a Zwicker critical band near 100 Hz. The 1978 fit is known to degrade
below ~200 Hz; sub-bass is a first-class H/I/S partition in this
pipeline, so the S-region dissonance share is distorted by the same
mechanism as the round-3 ERB roughness kernel.

An optional `low_frequency_basis="zwicker_below_200hz"` switches to
Zwicker CB below 200 Hz. 
**Default arithmetic is unchanged.** Whether the hybrid should become the
default is an author decision (CHANGES.md open item).

The four previously noted defects in this file were not touched.

## Bandwidth table (20–500 Hz)

| f (Hz) | HK `1.72 f^0.65` | Zwicker CB | Zwicker / HK |
|---:|---:|---:|---:|
| 20 | 12.06 | 100.03 | 8.30 |
| 30 | 15.69 | 100.07 | 6.38 |
| 40 | 18.92 | 100.12 | 5.29 |
| 50 | 21.87 | 100.18 | 4.58 |
| 65.4 | 26.04 | 100.31 | 3.85 |
| 80 | 29.68 | 100.46 | 3.38 |
| 100 | 34.32 | 100.72 | 2.93 |
| 110 | 36.51 | 100.87 | 2.76 |
| 146.83 | 44.05 | 101.55 | 2.31 |
| 200 | 53.85 | 102.87 | 1.91 |
| 250 | 62.26 | 104.47 | 1.68 |
| 300 | 70.09 | 106.40 | 1.52 |
| 400 | 84.50 | 111.22 | 1.32 |
| 500 | 97.69 | 117.26 | 1.20 |

## Synthetic S-region (cello C2 stand-in)

Partials at 32.7, 41.2, 49.0, 55.0, 61.7 Hz with amplitudes 1/n.
Corpus audio was not used for this row.

- HK 1978 total dissonance: `0.479543`
- Hybrid (Zwicker below 200 Hz): `1.01439`
- Hybrid / HK: `2.115`

## Corpus S-region

Not reachable (`ACD_REAL_NOTE_AUDIO` unset; default cello path
absent). No live S-region difference is reported.

## Outstanding judgement

Keep `hk1978` until the author decides whether sub-bass H&K should
use Zwicker CB below 200 Hz. Changing the default would move
S-region dissonance on every note with energy below that cutoff.
