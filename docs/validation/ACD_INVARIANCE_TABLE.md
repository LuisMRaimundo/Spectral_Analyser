# ACD vs EWSD invariance (generated)

Toy inputs only. ACD is F-057 (`sum_k r_k D2_k` after ERB merge). EWSD is frozen F-048 / F-049 on the same amplitudes with Excel-like `r = (0.80, 0.15, 0.05)` and `φ = log`. Not a corpus measurement.

## Gain sweep (synthetic note)

| gain | ACD_score | EWSD_score_total | EWSD_score_acoustic_balanced |
|---:|---:|---:|---:|
| 1e-03 | 2.37712879901 | 0.00162122417007 | 0.00178574708059 |
| 1e-02 | 2.37712879901 | 0.016173726546 | 0.0178076199323 |
| 1e-01 | 2.37712879901 | 0.158032562074 | 0.173316132409 |
| 1e+00 | 2.37712879901 | 1.30949552836 | 1.40123204231 |
| 1e+01 | 2.37712879901 | 5.94081914078 | 6.09052248634 |
| 1e+02 | 2.37712879901 | 13.4888714416 | 13.5916958244 |
| 1e+04 | 2.37712879901 | 29.8473026076 | 29.8978960674 |

## Gain sweep (research-export D3 fixture amplitudes)

| gain | ACD_score | EWSD_score_total | EWSD_score_acoustic_balanced |
|---:|---:|---:|---:|
| 1e-03 | 2.31175289568 | 0.00166987388932 | 0.0017333726186 |
| 1e-02 | 2.31175289568 | 0.0166484664203 | 0.0172775398282 |
| 1e-01 | 2.31175289568 | 0.161678359018 | 0.167427537621 |
| 1e+00 | 2.31175289568 | 1.28132954346 | 1.31086948703 |
| 1e+01 | 2.31175289568 | 5.20300047252 | 5.23985146102 |
| 1e+02 | 2.31175289568 | 11.0652429276 | 11.0890263064 |
| 1e+04 | 2.31175289568 | 23.686143037 | 23.6978385808 |

## FFT-tier sidelobe model (synthetic; bin width `fs/n_fft`)

| n_fft | ACD_score | EWSD_score_total | EWSD_score_acoustic_balanced |
|---:|---:|---:|---:|
| 4096 | 2.37714246093 | 0.624127112416 | 1.02742244019 |
| 8192 | 2.37714246093 | 0.624127112416 | 1.02742244019 |
| 16384 | 2.37714246093 | 0.624127112416 | 1.02742244019 |

## Peak-picking threshold extras on H (synthetic; 12 extras at half the linear floor)

| threshold_dB_re_max | ACD_score | EWSD_score_total | EWSD_score_acoustic_balanced |
|---:|---:|---:|---:|
| 0.0 | 7.09771655445 | 5.15199893199 | 5.27062776737 |
| -20.0 | 2.45747556082 | 0.753263456594 | 1.21250138177 |
| -40.0 | 2.37792869029 | 0.392052086566 | 0.767919229454 |
| -60.0 | 2.37713679755 | 0.363009062429 | 0.727112304153 |
| -80.0 | 2.37712887899 | 0.3601806664 | 0.72307693454 |
| -100.0 | 2.37712879981 | 0.359898588752 | 0.722673859604 |

## Stated tolerances

- ACD gain sweep: flat to `1e-10`.
- ACD FFT-tier sidelobe model: relative 5 % (ERB merge absorbs intra-filter leakage).
- ACD extras at −80 dB or weaker: relative 1 %.
- EWSD columns are the frozen F-048/F-049 values on the same vectors; they are not required to be invariant.
