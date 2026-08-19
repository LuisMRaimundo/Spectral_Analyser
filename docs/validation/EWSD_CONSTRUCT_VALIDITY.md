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
