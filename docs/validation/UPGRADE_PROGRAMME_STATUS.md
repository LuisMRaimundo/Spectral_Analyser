# Upgrade programme status (post-`70525e3`)

Measurable acceptance, not a 1–100 rating. One git phase / PR per letter.
F-042 / F-047 / F-048 / F-049 algebra is unchanged unless a formula-version
bump is recorded.

| Phase | Topic | Tests | Acceptance | Status |
|-------|--------|-------|------------|--------|
| A | Confirmed-inharmonic partial class | `tests/phase_14/test_inharmonic_confirmation.py` | A2-like floor → 0 confirmed, all `rejected_floor` on CFAR. Piano B=2e-4, 30 stretched → 0 I, 30 H (`rejected_stretched_harmonic`). Bell, 10 partials at 20 dB SNR → exactly 10 confirmed. Two H3 sidelobes → 0 confirmed, `rejected_leakage` guarding order 3. | **done (PR #66)** |
| B | Temporal persistence | `tests/phase_15/test_temporal_persistence.py` | H1–H8 on A2 ≥ 0.95 at the time-averaged peak. The three 12 kHz floor slots fail the 0.7 inclusion gate with body stop off. Synthetic: steady ≥ 0.95, 2-frame burst rejected, unstructured floor < 0.3. | **done (PR #67)** |
| C | Independent high-n guards | `tests/phase_16/test_high_n_harmonic_guards.py` | Body stop off: A2 keeps the low-order body and nothing above H8 (H7/H8 may be `cfar_marginal` on this take). Run-2 notes pass the peak-bin invariant; `accepted_slots_above_body_stop = 0`. | **done (PR #68)** |
| D | Uncertainty by default | `tests/phase_17/test_uncertainty_defaults.py` | CI bands on Stage 3 EWSD; A2 EPD CI reported; < 10 independent frames flagged. | **done (PR #69)** |
| E | Provenance | `tests/phase_18/test_provenance_and_verify_export.py` | Fresh export stamps commit + version. `verify_export.py` on run-2 → not comparable. | **in this PR** |
| F | Schema / count hygiene | `tests/phase_19/` | One meaning per header; F-020 rows contribute 0 to S sums. | pending |
| G | Weight function φ | `tests/phase_20/` | Sensitivity report on tuba corpus; README records ρ. | pending |
| H | Reproducibility command | `tests/phase_21/` | Tuba *pp* re-export + Stage 3 diff vs 19 Aug Análise 3. | pending |
| I | Construct validation | `tests/validation/synthetic_corpus/` | Recover N ±1, B ±10 %, EPD ±10 %, confirmed-I exact at SNR 10–40 dB. Perceptual scaffold only (no data collection). | pending |

## Phase A notes

Module: `inharmonic_confirmation.py`. Constants: `CFAR_PFA`,
`INHARMONIC_MIN_PROMINENCE_DB`, `PARTIAL_PERSISTENCE_MIN_FRACTION`.
New sheet: `Confirmed_Inharmonic_Partials`. Persistence uses a default
fraction of 1.0 when the Phase B frame table is absent; A2 floor
rejection is CFAR, not persistence.

## Phase B notes

Module: `temporal_persistence.py`. Constant:
`FRAME_PEAK_MIN_ABOVE_MEDIAN_DB`. Persistence uses the per-frame peak
table against the time-averaged peak frequency. On IOWA tuba A2
(SustainStable, 1.08 s) H1–H8 persist ≥ 0.95 at that frequency. The
12 094 Hz residual line is temporally present (p ≈ 0.6) but still
fails the 0.7 inclusion gate; unstructured synthetic floor remains
< 0.3. Body-stop labelling does not overwrite a persistence reject.

## Phase C notes

Module: `harmonic_high_n_guards.py`. Constants:
`HARMONIC_MIN_CFAR_MARGIN_DB`, `HARMONIC_CONTINUITY_*`. The body stop
is documented as load-bearing in `TECHNICAL_MANUAL_COMPLETE.md` §5.2.1.
Guard order: spacing cap → CFAR margin → persistence → optional
continuity → body stop. Continuity is off by default. With the body
stop off, A2 includes H1–H6 and nothing above H8; H7/H8 can be
`cfar_marginal` on the 1.08 s take at n_fft=4096.

## Phase D notes

Module: `density_uncertainty.py` (`bootstrap_effective_component_density`,
`ci_basis_counts`, `build_uncertainty_summary`). Chart policy:
`publication_chart_policy.write_stage3_ewsd_ci_chart`. Constants:
`UNCERTAINTY_REL_FLAG_PCT` (25), `CI_BASIS_INDEPENDENT_FRAME_MIN` (10).
F-047 point estimate is unchanged. Research workbook writes
`Uncertainty_Summary` and, when charts are on,
`ewsd_acoustic_balanced_ci.png`. A2-like H1–H8 workbooks report an EPD
CI; a note with fewer than 10 independent frames is flagged.

## Phase E notes

Module: `analysis_provenance.py`. CLI: `verify_export.py`.
`component_energy_pie.png` is computed from `*_energy_sum`.
Amplitude pie title is `Validated-partial amplitude balance`; F-020
diagnostic rows are excluded unless
`INCLUDE_LF_DIAGNOSTIC_IN_AMPLITUDE_PIE`. Header-contract invariant is
fail-closed. A v4.0.3 / run-2 workbook is
`not comparable (pre-exclusive-assignment)`.
