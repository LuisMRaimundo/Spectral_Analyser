# ACD vs EWSD invariance (generated)

Toy inputs unless a later section says otherwise. ACD is F-057 (`sum_k r_k D1_k` after ERB merge). EWSD is frozen F-048 / F-049 on the same amplitudes with Excel-like `r = (0.80, 0.15, 0.05)` and `φ = log`. Synthetic blocks are fixtures, not corpus measurements.

## Axiomatic comparison (Hurley & Rickard 2009; Hill / Jost replication)

EWSD rows state a failure only when a passing test in `tests/phase_32/` demonstrates it. EWSD fails **Scaling** and **Babies**, and only those two.

| Property | ACD (F-057 / D1) | EWSD (F-048 score) |
|---|---|---|
| Scaling | Holds | Fails (level-dependent `log1p` shares) |
| Babies (−60 dB extras) | Holds (D1 change < 1 % at −80 dB × 50) | Fails (−24.9 % / −93.9 %) |
| Cloning (disjoint replica) | Holds (D_q doubles) | Holds (ratio = 2.000000) |
| Dalton / Robin Hood | Holds (D1 increases) | not claimed |
| Rising Tide | Holds (diversity dual of the 2009 sparsity axiom) | not claimed |
| Bill Gates | Holds (D1 → 1) | not claimed |

## Gain sweep (synthetic note)

| gain | ACD_score | EWSD_score_total | EWSD_score_acoustic_balanced |
|---:|---:|---:|---:|
| 1e-03 | 2.81309673828 | 0.00162122417007 | 0.00178574708059 |
| 1e-02 | 2.81309673828 | 0.016173726546 | 0.0178076199323 |
| 1e-01 | 2.81309673828 | 0.158032562074 | 0.173316132409 |
| 1e+00 | 2.81309673828 | 1.30949552836 | 1.40123204231 |
| 1e+01 | 2.81309673828 | 5.94081914078 | 6.09052248634 |
| 1e+02 | 2.81309673828 | 13.4888714416 | 13.5916958244 |
| 1e+04 | 2.81309673828 | 29.8473026076 | 29.8978960674 |

## Gain sweep (research-export D3 fixture amplitudes)

| gain | ACD_score | EWSD_score_total | EWSD_score_acoustic_balanced |
|---:|---:|---:|---:|
| 1e-03 | 2.58011032245 | 0.00166987388932 | 0.0017333726186 |
| 1e-02 | 2.58011032245 | 0.0166484664203 | 0.0172775398282 |
| 1e-01 | 2.58011032245 | 0.161678359018 | 0.167427537621 |
| 1e+00 | 2.58011032245 | 1.28132954346 | 1.31086948703 |
| 1e+01 | 2.58011032245 | 5.20300047252 | 5.23985146102 |
| 1e+02 | 2.58011032245 | 11.0652429276 | 11.0890263064 |
| 1e+04 | 2.58011032245 | 23.686143037 | 23.6978385808 |

## FFT-tier sidelobe model (synthetic; bin width `fs/n_fft`)

non-discriminating (synthetic sidelobe model; both metrics flat). See the real-note Stage 1 tier sweep below, where bin width, resolved-peak count, and Phase 8 `peak_amplitude_sum` normalisation vary together.

| n_fft | ACD_score | EWSD_score_total | EWSD_score_acoustic_balanced | note |
|---:|---:|---:|---:|---|
| 4096 | 2.85423806505 | 0.624127112416 | 1.02742244019 | non-discriminating (synthetic sidelobe model; both metrics flat) |
| 8192 | 2.82657152004 | 0.624127112416 | 1.02742244019 | non-discriminating (synthetic sidelobe model; both metrics flat) |
| 16384 | 2.81311472527 | 0.624127112416 | 1.02742244019 | non-discriminating (synthetic sidelobe model; both metrics flat) |

## Peak-picking threshold extras on H (synthetic)

Column `extra_component_level_dB_re_max` is the level of twelve added components relative to the loudest original peak. First row is the same fixture with **no extras**; EWSD and ACD bases are computed, not hard-coded. Δ% is against each metric's own base.

| extra_component_level_dB_re_max | ACD_score | ACD_Δ% | EWSD_score_total | EWSD_Δ% | EWSD_score_acoustic_balanced | EWSD_bal_Δ% |
|---:|---:|---:|---:|---:|---:|---:|
| (none) | 2.81309673828 | +0.0000 | 1.30949552836 | +0.0000 | 1.40123204231 | +0.0000 |
| -20 | 3.10973571096 | +10.5449 | 0.753263456594 | -42.4768 | 1.21250138177 | -13.4689 |
| -40 | 2.81813667049 | +0.1792 | 0.392052086566 | -70.0608 | 0.767919229454 | -45.1969 |
| -60 | 2.81316885152 | +0.0026 | 0.363009062429 | -72.2787 | 0.727112304153 | -48.1091 |
| -80 | 2.81309767692 | +0.0000 | 0.3601806664 | -72.4947 | 0.72307693454 | -48.3971 |
| -100 | 2.81309674985 | +0.0000 | 0.359898588752 | -72.5162 | 0.722673859604 | -48.4258 |

## Monotonicity in genuine content

Twelve extras at 0 dB re max are as loud as the loudest original component. That is an amplitude manipulation, not a detection-threshold manipulation. A rise in ACD is the expected result.

| extra_component_level_dB_re_max | ACD_score | ACD_Δ% | EWSD_score_total | EWSD_Δ% | EWSD_score_acoustic_balanced | EWSD_bal_Δ% |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 10.0902795389 | +258.6894 | 5.15199893199 | +293.4339 | 5.27062776737 | +276.1424 |

## Stated tolerances (synthetic)

- ACD gain sweep: flat to `1e-10`.
- ACD FFT-tier sidelobe model: relative 5 % (ERB merge absorbs intra-filter leakage). Row is non-discriminating; both metrics are flat. Real-note Stage 1 tier tolerance: `4% relative` on `ACD_score`.
- ACD extras at −80 dB or weaker: relative 1 %.
- EWSD columns are the frozen F-048/F-049 values on the same vectors; they are not required to be invariant. Demonstrated failures: Scaling and Babies only.

## Real-note invariance — D3, ORC_Vlc_arco_mf _Sustains (49-note cello corpus)

Note `D3` from `ORC_Vlc_arco_mf _Sustains (49-note cello corpus)`. These rows are Stage 1 **measurements** (loaded audio → production peak picker / FFT tier / Phase 8 `peak_amplitude_sum`), not toy amplitude fixtures. Corpus audio was not mounted; audio is a 0.85 s synthesized D3 (f0 = 146.83 Hz) with two inharmonic partials, run through the production Stage 1 path. Set `ACD_REAL_NOTE_AUDIO` to the corpus D3 take to replace this stand-in. ACD_score in this cache is the historical D2 / moving_centroid measurement; the current default is D1 / fixed_erb_grid. Side-by-side FFT-tier numbers: `docs/validation/ACD_MERGE_STRATEGY.md`.

ACD FFT-tier tolerance asserted at `4%` relative (winning merge strategy max |Δ%| + 1 pp, rounded up; not above 5%). Historical ACD_score rows below are D2 / moving_centroid; current default is D1 / fixed_erb_grid (`docs/validation/ACD_MERGE_STRATEGY.md`).

### Gain sweep (audio scaled before Stage 1)

Gain is applied to the loaded waveform, then Stage 1 is run at n_fft=8192, db_min=-80.0.

| gain | ACD_score | ACD_Δ% | ACD_magnitude_per_component | ACD_mag_Δ% | ACD_D2 | ACD_D2_Δ% | EWSD_score_total | EWSD_Δ% | EWSD_score_acoustic_balanced | EWSD_bal_Δ% |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1e-03 | 1.90528712792 | +0.0000 | 51179.2297245 | -0.0000 | 1.90528712792 | +0.0000 | 17.9061687536 | +0.0000 | 18.0839484773 | +0.0000 |
| 1e-02 | 1.90528712743 | -0.0000 | 51179.2302677 | -0.0000 | 1.90528712743 | -0.0000 | 17.9061688269 | +0.0000 | 18.0839485504 | +0.0000 |
| 1e-01 | 1.9052871263 | -0.0000 | 51179.2303478 | +0.0000 | 1.9052871263 | -0.0000 | 17.9061687425 | -0.0000 | 18.0839484646 | -0.0000 |
| 1e+00 | 1.90528712764 | +0.0000 | 51179.2303091 | +0.0000 | 1.90528712764 | +0.0000 | 17.9061687517 | +0.0000 | 18.0839484735 | +0.0000 |
| 1e+01 | 1.90528712736 | -0.0000 | 51179.2303361 | +0.0000 | 1.90528712736 | -0.0000 | 17.9061688193 | +0.0000 | 18.0839485409 | +0.0000 |
| 1e+02 | 1.90528712746 | -0.0000 | 51179.2303289 | +0.0000 | 1.90528712746 | -0.0000 | 17.9061687456 | -0.0000 | 18.0839484691 | -0.0000 |
| 1e+04 | 1.90528712731 | -0.0000 | 51179.2303312 | +0.0000 | 1.90528712731 | -0.0000 | 17.9061687012 | -0.0000 | 18.083948424 | -0.0000 |

### FFT tier (real Stage 1; unique n_fft selected for C2–C6)

Each n_fft is a value `_assign_tier_for_file` actually selects on the 49-note cello range. Bin width, peak census, and Phase 8 `peak_amplitude_sum` vary together. Historical ACD_score here is D2 / moving_centroid. Current gate is 4% relative (winning-strategy max |Δ%| + 1 pp, rounded up; not above 5%). See `ACD_MERGE_STRATEGY.md`.

| n_fft | ACD_score | ACD_Δ% | ACD_magnitude_per_component | ACD_mag_Δ% | ACD_D2 | ACD_D2_Δ% | EWSD_score_total | EWSD_Δ% | EWSD_score_acoustic_balanced | EWSD_bal_Δ% |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 16384 | 1.83285262914 | -3.8018 | 267075.737652 | +421.8440 | 1.83285262914 | -3.8018 | 31.5702076037 | +76.3091 | 31.9893361953 | +76.8935 |
| 8192 | 1.90528712764 | +0.0000 | 51179.2303091 | +0.0000 | 1.90528712764 | +0.0000 | 17.9061687517 | +0.0000 | 18.0839484735 | +0.0000 |
| 4096 | 1.85733965096 | -2.5165 | 11789.5897977 | -76.9641 | 1.85733965096 | -2.5165 | 13.5699499185 | -24.2163 | 13.7001953309 | -24.2411 |
| 2048 | 1.89374622384 | -0.6057 | 2722.83817638 | -94.6798 | 1.89374622384 | -0.6057 | 11.2381393276 | -37.2387 | 11.5203459651 | -36.2952 |

### Peak-picking threshold (production `db_min` sweep)

Stage 1 `db_min` / `density_salience_threshold_db`. Production default is -80.0 dB.

| db_min | ACD_score | ACD_Δ% | ACD_magnitude_per_component | ACD_mag_Δ% | ACD_D2 | ACD_D2_Δ% | EWSD_score_total | EWSD_Δ% | EWSD_score_acoustic_balanced | EWSD_bal_Δ% |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| -20 | 1.90528716394 | +0.0000 | 51179.2298192 | -0.0000 | 1.90528716394 | +0.0000 | 24.4079208885 | +36.3101 | 24.8077177494 | +37.1809 |
| -40 | 1.90528712764 | +0.0000 | 51179.2303091 | +0.0000 | 1.90528712764 | +0.0000 | 22.2887913831 | +24.4755 | 22.6162257393 | +25.0624 |
| -60 | 1.90528712764 | +0.0000 | 51179.2303091 | +0.0000 | 1.90528712764 | +0.0000 | 18.2268519849 | +1.7909 | 18.4155821663 | +1.8339 |
| -80 | 1.90528712764 | +0.0000 | 51179.2303091 | +0.0000 | 1.90528712764 | +0.0000 | 17.9061687517 | +0.0000 | 18.0839484735 | +0.0000 |
| -100 | 1.90528712764 | +0.0000 | 51179.2303091 | +0.0000 | 1.90528712764 | +0.0000 | 17.7413484823 | -0.9205 | 17.9135000406 | -0.9425 |
