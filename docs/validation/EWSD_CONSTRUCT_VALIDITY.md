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

## Explicit non-claims

- No assertion that EWSD equals listener "fatness" or "brightness".
- No cross-corpus absolute calibration without profile matching.
- Register–score correlation documents harmonic capacity, not a defect to remove silently.

## References in codebase

- Pure math: `tools/ewsd_pure.py`
- Bootstrap UQ: `tools/ewsd_uncertainty.py`
- Sensitivity CLI: `tools/ewsd_sensitivity_report.py`
- Validation ledger: `docs/validation/FORMULA_VALIDATION_STATUS.md` (F-048, F-049)
