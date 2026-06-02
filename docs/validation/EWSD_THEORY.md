# EWSD metric hierarchy (acoustic constructs)

This memo positions Stage 3 EWSD relative to other density exports. **Acoustic
only** — no perceptual claims.

## Primary scalars per note (register + dynamic row)

| Construct | Column | Formula ID | Acoustic question |
|-----------|--------|------------|-------------------|
| Weighted spectral density | `note_density_final` | F-042 | How much GUI-weighted H/I/S content? |
| Effective partial count ("fatness") | `note_effective_component_density` | F-047 | How many energy-bearing partials (pooled PR)? |
| Strict anti-concentration EWSD | `EWSD_score_total` | F-048 | Weighted density × full \((N_{eff}/N)\) penalty per compartment |
| Cross-instrument EWSD | `EWSD_score_acoustic_balanced` | F-049 | Same with moderated penalty \(\alpha=0.5\) |
| EWSD uncertainty | `EWSD_score_acoustic_balanced_ci_*` | F-050 | Bootstrap band on F-049 |

## Non-interchangeability

- `note_density_final` **does not** apply the compartment-wise participation-ratio penalty.
- `note_effective_component_density` uses **energy** (\(A^2\)) pooling; EWSD penalties use **weight-function strengths** within each compartment — intentional alignment with \(D_k\).
- Do not rank instruments on `note_density_final` alone under mixed profiles; use **`EWSD_score_acoustic_balanced`** with eligibility gates.

## Cross-instrument acoustic protocol

1. Identical Stage 1+2 profile (`analysis_parameter_profile_id`).
2. Fixed `density_frequency_ceiling_hz` (typically 20000 Hz).
3. Pitch-matched comparison windows.
4. Matched dynamic per row.
5. Filter `ewsd_primary_analysis_eligible == True`.
6. Report `EWSD_score_acoustic_balanced` with bootstrap CI columns.

## Validation artefacts

| Tier | Evidence |
|------|----------|
| A | `tools/ewsd_pure.py`, golden vectors, 49-note corpus regression |
| B | Bootstrap UQ, `tools/ewsd_sensitivity_report.py`, construct doc |
| C | `tools/ewsd_stage3_contract.py`, `Stage3_Diagnostics` sheet, CI gate |

See also: `docs/validation/EWSD_CONSTRUCT_VALIDITY.md`, `docs/validation/FORMULA_VALIDATION_STATUS.md`.
