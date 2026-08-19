# Construct validation — synthetic corpus

Planted constructs recovered through the Stage 1 evidence path
(peak pick → F-007 assignment → stiff-string B fit → confirmed-I → EPD).
SNR is the per-partial peak-to-floor ratio (dB), white floor.

Acceptance: N ±1, B ±10 %, EPD ±10 %, confirmed-I exact.

| construct | SNR dB | N true | N hat | B true | B hat | EPD true | EPD hat | I true | I hat |
|-----------|-------:|-------:|------:|-------:|------:|---------:|--------:|-------:|------:|
| harmonic_snr10_white | 10 | 8 | 8 | 0.00e+00 | 6.94e-05 | 3.501 | 3.501 | 0 | 0 |
| harmonic_snr20_white | 20 | 8 | 8 | 0.00e+00 | 6.94e-05 | 3.501 | 3.501 | 0 | 0 |
| harmonic_snr30_white | 30 | 8 | 8 | 0.00e+00 | 6.94e-05 | 3.501 | 3.501 | 0 | 0 |
| harmonic_snr40_white | 40 | 8 | 8 | 0.00e+00 | 6.94e-05 | 3.501 | 3.501 | 0 | 0 |
| stiff_snr10_white | 10 | 12 | 12 | 2.00e-04 | 2.17e-04 | 4.513 | 4.513 | 0 | 0 |
| stiff_snr20_white | 20 | 12 | 12 | 2.00e-04 | 2.17e-04 | 4.513 | 4.513 | 0 | 0 |
| stiff_snr30_white | 30 | 12 | 12 | 2.00e-04 | 2.17e-04 | 4.513 | 4.513 | 0 | 0 |
| stiff_snr40_white | 40 | 12 | 12 | 2.00e-04 | 2.17e-04 | 4.513 | 4.513 | 0 | 0 |
| bell_snr10_white | 10 | 3 | 3 | 0.00e+00 | 0.00e+00 | 7.812 | 7.812 | 10 | 10 |
| bell_snr20_white | 20 | 3 | 3 | 0.00e+00 | 0.00e+00 | 7.812 | 7.812 | 10 | 10 |
| bell_snr30_white | 30 | 3 | 3 | 0.00e+00 | 0.00e+00 | 7.812 | 7.812 | 10 | 10 |
| bell_snr40_white | 40 | 3 | 3 | 0.00e+00 | 0.00e+00 | 7.812 | 7.812 | 10 | 10 |

## Notes

SNR is the per-partial peak-to-floor ratio (dB) on a white floor, so the
weakest planted partial remains at the stated margin. Recovery uses the
Stage 1 evidence path: peak pick, F-007 assignment, stiff-string B fit,
confirmed-I (Phase A), and EPD (participation ratio of the validated set).

Waveforms for the same constructs are available from
`tests.validation.synthetic_corpus.generate.synthesize_waveform` (optional
audio export). They are not required for the table above.

Listener judgements are out of scope. See
`docs/validation/PERCEPTUAL_PROTOCOL.md`.
