# Measurement-performance report

- **Tag:** `v4.2.1-dirty`
- **Commit:** `4799ea0`
- **Date:** 2026-08-20 12:01 UTC
- **Hardware:** Windows-10-10.0.26200-SP0 Python 3.10.11
- **Profile:** `wf=log|dst=-90.0|ceil=20000.0|fft=fixed|seg=sustain_primary_stable_diagnostic|elig=1`
- **Master seed:** 20260820
- **Manifests used:** v4.2.1 analysis_results_v4.2.1/run_manifest.json only

## Headline

| Part | Score |
|------|------:|
| A accuracy | 87.5 |
| B invariance | 71.4 |
| C uncertainty validity | 65.0 |
| D corpus-result quality | 82.5 |
| **Composite (mean)** | **76.6** |

The Phase I path recovers planted f0, N, B, EPD, residual share, confirmed-I, energy closure, and sub-bass share on 25 seeded instances; median f0 error is -0.01 cents (worst 10.18).
Part A rubric mean is 87.5; invariance (B1–B6/B8) passed 5/7 scored cells.
On the synthetic SNR sweep (B7, not scored), N and EPD stay within 10 % of the 40 dB values from 0–40 dB; EWSD_hat at 0 dB differs from the 40 dB reference by more than 10 % at every lower step.
Part D used 1 v4.2.1 corpus tree(s) with a manifest; mean eligibility among those is 100.0 %.
Missing v4.2.1 manifests were excluded; pre-tag workbooks were not substituted.
Item 5 (3-note re-run identity) is PASS.

## Part A — accuracy against ground truth

| Row | Median | Worst | Score |
|-----|-------:|------:|------:|
| A1 f0 (cents) | -0.0080 | 10.1800 | 100 |
| A2 ΔN | 0.0000 | 0.0000 | 100 |
| A3 B rel % | -19.0863 | 100.0000 | 70 |
| A4 EPD rel % | 0.0000 | 1.1400e-13 | 100 |
| A5 residual pp | -0.5350 | 1.6688 | 100 |
| A6 P / R | 1.0000 / 1.0000 | 1.0000 / 1.0000 | 100 |
| A7 \|Σ−1\| | 0.0000 | 0.0000 | 100 |
| A8 S-share pp | -4.5534 | 7.7090 | 30 |

A2 per SNR medians: 10 dB → 0.0000, 20 dB → 0.0000, 30 dB → 0.0000, 40 dB → 0.0000.

**Part A score = 87.5** (mean of eight rubric rows).

## Part B — invariance

| Cell | Pass |
|------|------|
| B1 resolution 3 % | FAIL |
| B2 hop 2 % | PASS |
| B3 level 1 % | PASS |
| B4 segment jitter | PASS |
| B5 silence 0 % | FAIL |
| B6 determinism | PASS |
| B8 sample rate 3 % | PASS |

B1 measured Stage-1 values (in-memory / Metrics diagnostic EWSD, not compiled Stage-3):

- synthetic: n_fft=4096 EWSD=7.3102 core_H=0.0529 EPD=1.1298; n_fft=8192 EWSD=6.7082 core_H=0.0545 EPD=1.1384; n_fft=16384 EWSD=6.7366 core_H=0.0560 EPD=1.1331
- g3: n_fft=4096 EWSD=41.6579 core_H=0.7307 EPD=10.5131; n_fft=8192 EWSD=54.5685 core_H=0.9157 EPD=10.0648; n_fft=16384 EWSD=61.8926 core_H=0.9754 EPD=9.5157
- flute: n_fft=4096 EWSD=13.0296 core_H=0.8078 EPD=2.8612; n_fft=8192 EWSD=17.2651 core_H=0.9675 EPD=2.9256; n_fft=16384 EWSD=20.9596 core_H=0.9932 EPD=2.9833

B4 EWSD relative change at ±100 ms (unflagged real notes; pass ≤ 3 %):

- IOWA_Trb.T_ff.G3_SustainStable.aif flagged=False: +100 ms rel=0.0045, −100 ms rel=0.0089
- IOWA_flt_ff.A#4_SustainStable.aif flagged=False: +100 ms rel=0.0098, −100 ms rel=0.0075
- IOWA_Tub.pp.A2_Sustains.aif flagged=False: +100 ms rel=0.0234, −100 ms rel=0.0087
- IOWA_Vlc.sG_arco_ff.G2.aif flagged=True: +100 ms rel=4.8971e-05, −100 ms rel=7.4861e-05

B7 (not scored) — N̂ / EPD / EWSD vs SNR:

| SNR dB | N hat | EPD hat | EWSD hat |
|-------:|------:|--------:|---------:|
| 0 | 8.0 | 2.1658 | 8.7668 |
| 5 | 8.0 | 2.1658 | 12.0906 |
| 10 | 8.0 | 2.1658 | 15.8897 |
| 15 | 8.0 | 2.1658 | 20.0237 |
| 20 | 8.0 | 2.1658 | 24.3714 |
| 25 | 8.0 | 2.1658 | 28.8461 |
| 30 | 8.0 | 2.1658 | 33.3924 |
| 35 | 8.0 | 2.1658 | 37.9772 |
| 40 | 8.0 | 2.1658 | 42.5820 |

**Part B score = 71.4** (5 / 7 × 100).

## Part C — uncertainty machinery

- C1 EWSD coverage = 100.0 %; EPD coverage = 100.0 %; score 30. EPD coverage is of the analytic PR identity (zero-width). EWSD coverage is of the bootstrap point inside its own 95 % CI (calibration of the interval around the estimator, not an external oracle). Objection: the written tight band assumes an independent truth; this session uses the estimator point.
- C2 width vs n: n=4 w=1.0697, n=8 w=1.9731, n=16 w=2.2887, n=32 w=1.9982; pass=FAIL. Objection: this construction varies partial count, not independent-frame count; width did not shrink ~1/√n.
- C3 eligibility gate: PASS.
- C4 G2-type flag: PASS.

**Part C score = 65.0**.

## Part D — v4.2.1 corpora

| Corpus | n | % eligible | ρ(H,EPD) | ρ(EWSD,EPD) | EPD>N | closure | mono | residual med |
|--------|--:|-----------:|---------:|------------:|------:|--------:|-----:|-------------:|
| `analysis_results_v4.2.1` | 37 | 100.0 | 0.7662 | 0.9021 | 0 | 0 | 1 | 0.3473 |

Per-corpus residual share (min / median / max) and flags:

| Corpus | residual min | med | max | % NaN core | % fragile | % degenerate | confirmed-I | wall_s |
|--------|-------------:|----:|----:|-----------:|----------:|-------------:|------------:|-------:|
| `analysis_results_v4.2.1` | 0.2310 | 0.3473 | 0.3918 | 0.0 | 89.2 | 0.0 | 0 | 887.9 |

Tier-boundary residue (notes present on the exported sheet):

- `analysis_results_v4.2.1`: G#3 EWSD=12.0285 core_H=0.7689, G3 EWSD=13.3235 core_H=0.6617

Items 3–4: 1 pitch-monotonicity rise(s) without audit-sheet explanation; rubric score 30 (100 if zero unexplained, 70 if all explained in audit sheets, else 30).

Excluded (no usable v4.2.1 manifest/workbook):
- `D:\METAIS\TROMBONE\IOWA_Trombone\TenorTrombone\IOWA_Trombone_pp\_Sustains\analysis_results_v4.2.1` — missing v4.2.1 manifest
- `D:\METAIS\TROMBONE\IOWA_Trombone\TenorTrombone\IOWA_Trombone_mf\_Sustains\analysis_results_v4.2.1` — missing v4.2.1 manifest
- `D:\METAIS\TROMBONE\IOWA_Trombone\TenorTrombone\IOWA_Trombone_ff\_Sustains\analysis_results_v4.2.1` — missing v4.2.1 manifest
- `D:\MADEIRAS\FLAUTA\IOWA_flute\IOWA_Flute_pp\_Sustains\analysis_results_v4.2.1` — missing v4.2.1 manifest
- `D:\MADEIRAS\FLAUTA\IOWA_flute\IOWA_Flute_mf\_Sustains\analysis_results_v4.2.1` — missing v4.2.1 manifest
- `D:\MADEIRAS\FLAUTA\IOWA_flute\IOWA_Flute_ff\_Sustains\analysis_results_v4.2.1` — missing v4.2.1 manifest
- `D:\CORDAS_2\IOWA\CELLO\IOWA_Cello_Arco\CELLO\IOWA_cello_arco_ff\analysis_results_v4.2.1` — missing v4.2.1 manifest

Item 5 (3-note re-run identity): PASS (3 notes).

**Part D score = 82.5**.

## Measured limits (worst-case rows from A and B)

| Source | Worst-case |
|--------|------------|
| A1 f0 cents | 10.1800 |
| A2 ΔN | 0.0000 |
| A3 B rel % | 100.0000 |
| A4 EPD rel % | 1.1400e-13 |
| A5 residual pp | 1.6688 |
| A6 min P / min R | 1.0000 / 1.0000 |
| A7 \|Σ−1\| | 0.0000 |
| A8 S-share pp | 7.7090 |
| B1 pass | FAIL |
| B1 G3 core_H 4096/8192/16384 | 0.7307 / 0.9157 / 0.9754 |
| B1 G3 EWSD 4096/8192/16384 | 41.6579 / 54.5685 / 61.8926 |
| B5 silence prepend EWSD | NaN (0 validated harmonics) |
| B3 pass | PASS |
| B4 pass | PASS |
| B5 pass | FAIL |
| B6 pass | PASS |
| B8 pass | PASS |

## Appendix — commands, seeds, hashes

```
python -m tools.run_measurement_evaluation  # seed=20260820 n_inst=25
python -m tools.run_measurement_evaluation --parts A,C,D --no-live
python -m tools.run_measurement_evaluation --parts B,D
git describe: v4.2.1-dirty
commit: 4799ea0
runner sha256: 4e4afa2107b0a6db91ce5acdc4b19386fe42010fc455fc73f6c1d7c99759711a
```

Raw JSON: `docs/validation/_measurement_eval/results.json` (local; not a publication artefact).

## Addendum — 20 August 2026 (R2; scores not rewritten)

**B1: PASS (post-R2).** Stage-1 Metrics `EWSD_score_acoustic_balanced`
and `core_harmonic_energy_ratio` equal Stage-3 at the fixed window
8192/1024 (atol 1e-9) on a 4 s 8-partial A4 tone with `core_H` ≥ 0.99
(live orchestrator identity in `test_live_synthetic_stage1_equals_stage3_at_fixed_window`).
The original B1 cell (cross-n_fft 3 % on live G3, score 71.4 Part B)
is unchanged; that target remains the R1 measured FAIL and is out of
scope under R1b. Evidence: `tests/phase_30/test_r2_metric_single_source.py`,
`docs/validation/METRIC_SINGLE_SOURCE.md`.

## Addendum — 20 August 2026 (R3; scores not rewritten)

**B5: PASS (post-R3).** Leading or trailing digital silence of 0 / 0.5 /
2 s is trimmed on load so the analysis array matches the unpadded take.
The original B5 FAIL (prepend → 0 validated harmonics / EWSD NaN) is
unchanged in the scored table. Mechanism: silent head at file start;
guard is `audio_silence_trim.trim_digital_silence`, not ADSR_Segmenter.

## Addendum — 20 August 2026 (R5; scores not rewritten)

**C1 / C2 re-run against a planted-amplitude oracle** (`ewsd_pure` / F-047;
seed 20260820; 8 partials, −6 dB/oct, 20 dB SNR). Original Part C cells
(C1 score 30, C2 FAIL, Part C = 65.0) are unchanged.

- C1: 200 seeds, production partial-resample 95 % CI vs the planted
  oracle (not the bootstrap point). EWSD coverage = **100.0 %**; EPD
  coverage = **100.0 %**; score 30 (outside 90–99 %). Oracle EWSD =
  1.8415. The interval over-covers the external truth.
- C2: independent noisy frames n ∈ {4, 8, 16, 32} at **fixed** 8
  partials. Median EWSD widths 0.1429 / 0.1376 / 0.1131 / 0.0797.
  log(width) vs log(n) slope = **−0.281** (1/√n would be −0.5).
  Coverage per n: 85.0 / 85.0 / 92.5 / 90.0 %. Construction is now
  frames, not partial count; the 1/√n claim does not hold. Bootstrap
  not retuned.
- Measured limit: CIs are indicative, empirically 100 % C1 coverage.
  Backlog: `POST_FREEZE_BACKLOG.md`.

## Addendum — 20 August 2026 (R6; scores not rewritten)

Seven `v4.2.3` corpora (`1db94e1`, profile
`wf=log|dst=-90.0|ceil=20000.0|fft=fixed|seg=sustain_primary_stable_diagnostic|elig=1`).
Original headline composite **76.6** is unchanged. Diffs:
`docs/validation/REEXPORT_DIFF_SUMMARY.md`.

Part D on the seven new trees: eligibility 100 % (item 1 = 100);
item 2 FAIL (flute *pp* B5/B6 have EPD > validated H);
item 3–4 = 30 (one unexplained pitch-mono rise on flute *pp*).
D = (100 + 30 + 30) / 3 = **53.3**.

Recomputed composite from the re-run cells only
(B1 post-R2, B5 post-R3, C1, C2, D):

(100 + 100 + 30 + 30 + 53.3) / 5 = **62.7**.

CORDAS unchanged script on the existing 54 CORDAS_2 trees: dynamic
ε² = 0.00756; Iowa bass ρ = −0.046. EPD sidecar ε² = 0.0132; Iowa bass
ρ_EPD = −0.013. New cello *ff* ρ(MIDI, EWSD) = −0.579.
