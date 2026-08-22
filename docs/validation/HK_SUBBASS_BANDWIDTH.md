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

## Corpus register (metadata, audio not required)

49-note cello `ORC_Vlc_arco_mf` C2–C6 from
`tests/phase_11/fixtures/ewsd_corpus_reference.json`. Audio is unmounted; this is the
committed note list only. Every note can carry S-region energy
below 200 Hz. Notes whose **f0** itself sits in the degraded HK
range are the ones where the defect is first-class:

- N = 49
- f0 < 200 Hz (HK fit known to degrade): 20 (41%)
- f0 < 100 Hz (CB ~ half of measured): 8 (16%)

Notes with f0 < 200 Hz:

| Note | f0 (Hz) |
|---|---:|
| C2 | 65.41 |
| C#2 | 69.30 |
| D2 | 73.42 |
| D#2 | 77.78 |
| E2 | 82.41 |
| F2 | 87.31 |
| F#2 | 92.50 |
| G2 | 98.00 |
| G#2 | 103.83 |
| A2 | 110.00 |
| A#2 | 116.54 |
| B2 | 123.47 |
| C3 | 130.81 |
| C#3 | 138.59 |
| D3 | 146.83 |
| D#3 | 155.56 |
| E3 | 164.81 |
| F3 | 174.61 |
| F#3 | 185.00 |
| G3 | 196.00 |

Trombone material cited in the runbook (E2–C5) is not in this
JSON. E2 ≈ 82.4 Hz is inside the same degraded band; C1 tuba
(≈ 32.7 Hz) is worse. Default remains `hk1978`.

## Corpus S-region (live audio)

Not reachable (`ACD_REAL_NOTE_AUDIO` unset; default cello path
absent). No live S-region difference is reported.

## Outstanding judgement

Keep `hk1978` until the author decides whether sub-bass H&K should
use Zwicker CB below 200 Hz. Changing the default would move
S-region dissonance on every note with energy below that cutoff.
