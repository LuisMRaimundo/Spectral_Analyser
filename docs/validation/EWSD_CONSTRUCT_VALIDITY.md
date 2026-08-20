# EWSD acoustic construct validity (Tier B)

Scope: **acoustic/objective checks only** — no perceptual or listener-validation claims.

## Metric hierarchy (recap)

| Construct | Column | Acoustic meaning |
|-----------|--------|------------------|
| Weighted spectral density | `note_density_final` | H/I/S weighted partial sums |
| Effective partial count ("fatness") | `note_effective_component_density` | Pooled participation ratio on energy |
| Comparative weighted density | `EWSD_score_acoustic_balanced` | Density × moderated anti-concentration penalty |

EWSD strict (`EWSD_score_total`) and balanced companion are **not interchangeable** with `note_density_final`.

## Automated checks (violin 49-note reference corpus)

Executed in `tests/phase_11/test_ewsd_construct_validity.py` and
`tests/phase_11/test_ewsd_uncertainty.py` on committed fixture
`tests/phase_11/fixtures/ewsd_corpus_reference.json` (source:
`ewsd_ratio_respecting_results.xlsx`, `frequency_ceiling_hz = 20000`).

| Check | Expectation | Rationale |
|-------|-------------|-----------|
| Compartment algebra | Reconstructed totals match export to `< 1e-10` | Formula closure |
| Strict vs balanced | Spearman ρ high but scores not identical | Distinct constructs |
| α rank stability (0.5 vs 1.0) | Spearman ρ ≥ 0.90 across notes | Default α=0.5 preserves ordering |
| Bootstrap CI | Point estimate inside 95% CI | Sampling uncertainty bounded |
| Live corpus recompute | Matches reference at 20 kHz ceiling | Pipeline reproducibility |

## Alpha sensitivity

Run:

```bash
python tools/ewsd_sensitivity_report.py --reference-xlsx path/to/ewsd_ratio_respecting_results.xlsx
```

Or on a live analysis folder:

```bash
python tools/ewsd_sensitivity_report.py --analysis-root path/to/analysis_results --frequency-ceiling-hz 20000
```

The report documents Spearman rank stability across α ∈ {0.25, 0.5, 0.75, 1.0} and register–score correlations (physical capacity effects).

## Cross-instrument acoustic comparison protocol

1. Identical Stage 1+2 profile (`analysis_parameter_profile_id`).
2. Same `density_frequency_ceiling_hz` (typically 20000 Hz).
3. Pitch-matched cells (`Note` / register windows).
4. Matched dynamic class per row.
5. Filter `ewsd_primary_analysis_eligible == True`.
6. Report `EWSD_score_acoustic_balanced` with bootstrap CI columns.

## Pre-phase Stage 1 workbooks (exclusive assignment / gating)

Runs exported **before** the exclusive-assignment + validated-partial gating
phase (`CHANGES.md`, export schema `spectral_analysis_schema_2026_08`) may
contain:

- the same floor peak assigned to several high-*n* slots
  (`include_for_density = TRUE` on more than one `peak_bin_index`);
- ungated linear-amplitude sums and `effective_partial_density` that include
  near-floor inharmonic / sub-bass residual rows.

Those workbooks are **not comparable** to post-phase exports on
`effective_partial_density`, amplitude pies, Sethares, or validated harmonic
counts. Cross-run comparison requires a Stage 1 re-export (then Stage 2 + 3).
F-042 / F-047 / F-048 / F-049 algebra is unchanged; only the input domain
(`validated_partials_only`) changed. Confirmed-inharmonic I compartment:
`docs/validation/UPGRADE_PROGRAMME_STATUS.md` Phase A.

## CI interpretation

The exported interval is a bootstrap of the stated **resampling unit**,
not a laboratory measurement-error bar. `ci_resampling_unit` is
`partials` for F-047 / `note_density_final` (the amplitude vector is
redrawn with replacement). `ci_n_resampled` is that vector’s length;
`ci_bootstrap_iterations` and `ci_seed` identify the draw.

A long, smooth series with many highly correlated partials can produce a
**wide** interval (`ci_width_flag = wide` when relative width > 25 %)
even when the take is high-SNR. That is expected when the unit is
`partials` and N > 30 (`ci_width_note` includes
`high_partial_correlation`). A short sustain
(`sustain_frame_count_independent < 10`) is noted as
`low_independent_frames`. Neither note changes the point estimate or
the F-047 algebra.

## Declared analysis window

EWSD and the harmonic **census** that enters it are defined at the
declared Stage-1 window (`n_fft`, hop, `fft_policy`). Changing the
window changes which orders validate and the PSD residual floor.
Cross-resolution EWSD equality is not a construct requirement.
Comparability uses one declared window (`fft_policy=fixed`, default
8192/1024). See `RESOLUTION_DEPENDENCE_DIAGNOSIS.md` § R1b.

## Measured conditioning properties

Two measured conditioners sit beside each other. Neither is a defect
in the F-048/F-049 algebra.

### B1 — analysis window (live G3, Stage-3 compiled)

From `MEASUREMENT_PERFORMANCE_REPORT.md` / R1 on `v4.2.2` (`64a2282`):

| n_fft / hop | core_H | EWSD | EPD |
|-------------|-------:|-----:|----:|
| 4096 / 512 | 0.7878 | 72.72 | 10.513 |
| 8192 / 1024 | 0.9222 | 91.31 | 10.065 |
| 16384 / 2048 | 0.9760 | 118.04 | 9.516 |

R1b: the same 71 8192-validated orders give held core_H 0.9675 / 0.9910
/ 0.9970 and held EWSD 70.65 / 91.69 / 119.44. EWSD still follows the
window after the census is frozen.

### B7 — SNR (synthetic 8-partial tone, Phase I recover)

From `MEASUREMENT_PERFORMANCE_REPORT.md` (seed 20260820):

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

N̂ and EPD stay constant; EWSD rises with spectral cleanliness. Report
SNR beside EWSD for cross-dynamic comparisons.

## Resolution dependence

Adaptive-tier Stage 1 (`n_fft` 8192 → 4096 → 2048 at G3/G♯3 and B4/C5)
computed residual and compartment energies as periodogram bin sums. Halving
the window changed `core_harmonic_energy_ratio` and D_k while EPD (partials
only) stayed flat, so EWSD stepped ~28 % at the boundary
(`docs/validation/RESOLUTION_DEPENDENCE_DIAGNOSIS.md`).

After D6, energy is PSD per Hz (`energy_basis = psd_per_hz`). Pre-fix
adaptive-tier workbooks are **not comparable across tier boundaries**.
`verify_export.py` marks a workbook `not comparable (per_bin_energy_basis)`
when `energy_basis` is present and is not `psd_per_hz`. Use
`fft_policy=fixed` (default 8192/1024) for any corpus intended for
cross-note comparison.

## Explicit non-claims

- No assertion that EWSD equals listener "fatness" or "brightness".
- No cross-corpus absolute calibration without profile matching.
- Register–score correlation documents harmonic capacity, not a defect to remove silently.

## References in codebase

- Pure math: `tools/ewsd_pure.py`
- Bootstrap UQ: `tools/ewsd_uncertainty.py`
- Sensitivity CLI: `tools/ewsd_sensitivity_report.py`
- Validation ledger: `docs/validation/FORMULA_VALIDATION_STATUS.md` (F-048, F-049)
