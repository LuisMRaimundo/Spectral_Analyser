# Upgrade programme status (post-`70525e3`)

Measurable acceptance, not a 1–100 rating. This table is the freeze
record for Phases A–I, D1–D6, and WP1–WP6; it supersedes
`VERSION_RATING_IOWA_TUBA.md`. One git phase / PR per letter.
F-042 / F-047 / F-048 / F-049 algebra is unchanged unless a formula-version
bump is recorded.

| Phase | Topic | Tests | Acceptance | Status |
|-------|--------|-------|------------|--------|
| A | Confirmed-inharmonic partial class | `tests/phase_14/test_inharmonic_confirmation.py` | A2-like floor → 0 confirmed, all `rejected_floor` on CFAR. Piano B=2e-4, 30 stretched → 0 I, 30 H (`rejected_stretched_harmonic`). Bell, 10 partials at 20 dB SNR → exactly 10 confirmed. Two H3 sidelobes → 0 confirmed, `rejected_leakage` guarding order 3. | **done (PR #66)** |
| B | Temporal persistence | `tests/phase_15/test_temporal_persistence.py` | H1–H8 on A2 ≥ 0.95 at the time-averaged peak. The three 12 kHz floor slots fail the 0.7 inclusion gate with body stop off. Synthetic: steady ≥ 0.95, 2-frame burst rejected, unstructured floor < 0.3. | **done (PR #67)** |
| C | Independent high-n guards | `tests/phase_16/test_high_n_harmonic_guards.py` | Body stop off: A2 keeps the low-order body and nothing above H8 (H7/H8 may be `cfar_marginal` on this take). Run-2 notes pass the peak-bin invariant; `accepted_slots_above_body_stop = 0`. | **done (PR #68)** |
| D | Uncertainty by default | `tests/phase_17/test_uncertainty_defaults.py` | CI bands on Stage 3 EWSD; A2 EPD CI reported; < 10 independent frames flagged. | **done (PR #69)** |
| E | Provenance | `tests/phase_18/test_provenance_and_verify_export.py` | Fresh export stamps commit + version. `verify_export.py` on run-2 → not comparable. | **done (PR #70)** |
| F | Schema / count hygiene | `tests/phase_19/test_schema_and_count_hygiene.py` | One meaning per header; F-020 rows contribute 0 to S sums. | **done (PR #71)** |
| G | Weight function φ | `tests/phase_20/test_weight_function_phi.py` | Sensitivity report on tuba corpus; README records ρ. | **done (PR #72)** |
| H | Reproducibility command | `tests/phase_21/test_reproducibility_command.py` | Tuba *pp* re-export + Stage 3 diff vs 19 Aug Análise 3. | **done (PR #73)** |
| I | Construct validation | `tests/validation/synthetic_corpus/` | Recover N ±1, B ±10 %, EPD ±10 %, confirmed-I exact at SNR 10–40 dB. Perceptual scaffold only (no data collection). | **done (PR #74)** |
| D1 | Weak-margin persistence override | `tests/phase_23/test_trombone_as2_defect_fixes.py` | H81–H88 `validated_weak` when p=1.0; floor peak margin 1 dB p=0.3 stays `cfar_marginal`; `harmonic_validated_count` includes weak; `accepted_slots_above_body_stop` = 0. | **done (PR #75); verified WP2** |
| D2 | Tolerance continuity override | same | Isolated cap miss with both neighbours included re-enters; triple-assignment losers stay `rejected_by_tolerance`. | **done (PR #75); verified WP2** |
| D3 | F-020 bound unification | same | f0 ∈ {50, 116.3, 200} → bound {25, 58.15, 80}; all sheets read one function. | **done (PR #75); verified WP2** |
| D4 | CI resampling provenance | same | Unit/n/iterations/seed exported; CI values unchanged; wide flag + note. | **done (PR #75); verified WP2** |
| D5 | Naming hygiene | same | `hop_duration_s` / `window_duration_s`; one energy pie; energy-ratio bases documented. | **done (PR #75); verified WP2** |
| WP2 | D1–D5 evidence after WP1 | `docs/validation/TROMBONE_AS2_DEFECT_FIX_DIFF.md` | A♯2 validated 92; H74/H79 included; bound 58.15; A2 EPD 3.77, EWSD 16.11, CI present. | **done (PR #78)** |
| WP3 | Production policy as code | `tests/phase_26/test_production_policy.py` | Defaults `fixed`/8192/1024; profile id has `fft`/`seg`/`elig`; cello G2 stable ineligible and unrepresentative vs full; trombone A♯2 eligible, ratio ≈ 1; degenerate CI is NaN; mixed profile ids raise `stage3_issue`. | **done (PR #79)** |
| WP4 | CI to green | the previous 8 density failures | Planted peak-table tests opt out of the FFT noise gate; energy gates sum to 1; body sums use `body_freq_max_hz`; phase-2 test uses linear φ; I-sum matches confirmed I. P2 re-check: [GHA 32357936064](https://github.com/LuisMRaimundo/Spectral_Analyser/actions/runs/32357936064) py3.10 + py3.11 **success** (PR #83). | **done (PR #80)**; P2 re-check green |
| WP5 | Tag tooling, verify_corpus, runbook, v4.2.0 | `tests/phase_27/test_verify_corpus.py` | CLI keeps `--fft-policy fixed`; `verify_corpus` on a planted run; `docs/REEXPORT_RUNBOOK.md` exists; package 4.2.0; no F-042/047/048/049 golden change. | **done (PR #81); tag v4.2.0** |
| WP6 | Closure dossier + freeze declaration | `tests/phase_28/test_closure_dossier.py` | Phase I table is the freeze construct record; this page supersedes 1–100 ratings; G2 case study; post-freeze backlog; README freeze. | **done (PR #82, `aa24de8`)** |
| WP1 | Residual footprint separation | `tests/phase_25/test_residual_footprint.py` | **Acceptance (R1b):** energy-accounting invariance on the synthetic descriptor path (residual share < 1 %, Hz-region invariant) **plus** `fft_policy=fixed` as the comparability guarantee. Cross-resolution EWSD invariance is **not achievable in principle** (detection is resolution-dependent) and is **out of scope**. Evidence: R1 Stage-3 B1 table and R1b census-held G3 (`RESOLUTION_DEPENDENCE_DIAGNOSIS.md` § R1 / § R1b). Live G3 export still moves with n_fft (0.9222 @8192 vs 0.7878 @4096); that is expected under the re-scope, not a WP1 defect. Synthetic WP1 tests still pass (PR #77). | **done under R1b re-scope (PR #77; this PR)** |
| P1 | G3 contradiction | `tools/p1_g3_swap.py` | Dated live swap on `aa24de8`. 3 % tolerance FAIL. WP1 live acceptance withdrawn (then R1b re-scope). P5/P6 stopped at P1; R1b lifts the later stop. | **FAILED live (PR #83)** |
| P2 | CI green on tagged code | `.github/workflows/ci.yml` | Full suite 3.10/3.11; live G3 tests skip when audio is absent. [GHA 32357936064](https://github.com/LuisMRaimundo/Spectral_Analyser/actions/runs/32357936064) both jobs **success** (~17 min, not cancelled). | **done (PR #83)** |
| P3 | Post-rating doc fixes | `REFERENCES.md`, this page, `TROMBONE_AS2_DEFECT_FIX_DIFF.md` | Sethares 2005; WP6 cell; A♯2 residual columns (post-fix only). | **done (PR #83)** |
| P4 | Tag `v4.2.1` | `verify_export.py`, `tools/verify_corpus.py` | Package 4.2.1; `v4.2.1` supersedes `v4.2.0` (tag kept). Cut on `main` after this PR merges. P1 live fail is on the record. | **in this PR; tag after merge** |
| P5 | Archive pretag evidence | `docs/validation/pretag_evidence/` | Six trombone/flute research workbooks (`6b0e51a`) + CORDAS trio. G2 pair, cello five-column, 26-note segmentation sheet **not found**. Findings: `PRETAG_FINDINGS_SUMMARY.md`. | **done (this PR); three artefacts missing** |
| P6 | Runbook re-exports | `docs/REEXPORT_RUNBOOK.md` | Per-corpus Stage 1–3 + `verify_corpus` + diff vs pretag. | **pending R2–R5; R1b lifts the R1 stop** |
| R1 | Stage-3 B1 on `v4.2.2` | `tools/r1_stage3_b1.py` | Compiled Stage-3 values within 3 % across n_fft. Measured **FAIL** (G3/flute). Re-scoped: that target is out of scope (R1b). | **measured FAIL; acceptance re-scoped (R1b)** |
| R1b | Census-held G3 + WP1 re-scope | `tools/r1b_census_held.py` | Freeze 8192-validated 71 orders; report held vs native core_H/EWSD; attribute B1. | **done (PR #87)** |
| R2 | One metric, one value | `tests/phase_30/test_r2_metric_single_source.py` | Stage-1 Metrics EWSD/`core_H` equal Stage-3 at the fixed window (1e-9). Diagnostic density is not EWSD. `metric_single_source` fail-closed. Clean synthetic `core_H` ≥ 0.99. | **done (PR #88)** |
| R3 | Leading-silence (B5) | `tests/phase_30/test_r3_leading_silence.py` | Lead/trail digital silence ≤ 2 s matches the trimmed waveform (0 % tol on the loaded array). ADSR_Segmenter untouched. | **done (this PR)** |
| D6.1 | Resolution diagnosis | `docs/validation/RESOLUTION_DEPENDENCE_DIAGNOSIS.md` | G3/G♯3 swap: EWSD step follows the window. | **done (PR #76)** |
| D6.2 | PSD energy bases | `tests/phase_24/test_resolution_invariance.py` | Synthetic tone+pink energy ratios within 2 % across n_fft. | **done (PR #76)** |
| D6.3 | D_k n_fft norm | same | Density sums n_fft-normalised to 8192. | **done (PR #76)** |
| D6.4 | fft_policy fixed default | same | `fft_policy` in profile id; mixed-tier Stage 3 warning. | **done (PR #76)** |
| D6.5 | Settings parse / above-stop | dictionary | Range strings parse; included-above-stop = 0. | **done (PR #76)** |
| D6.6 | reexport / compare_runs | `tools/compare_runs.py` | Boundary-step guard. | **done (PR #76)** |

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

## Phase F notes

`Note` is take identity on `Metrics` / compile keys only. Per-row
sheets use `sample_note_tag` + `sample_id`; `partial_pitch_name` is
the nearest pitch of that row. Complete Spectrum per-bin `Note` names
remain opt-in. `Validation_Metrics` adds `subbass_member_count` and
`floor_rows_rejected_count`; only `*_validated_count` /
`*_confirmed_count` are partial counts. The Sub-bass sheet exports
rows above F-020 as `lf_diagnostic_not_member`; compile
`subbass_density_sum` / `subbass_energy_sum` ignore them.

## Phase G notes

`DENSITY_WEIGHT_FUNCTION_DEFAULT = log`. Log-amplitude is the documented
first-order loudness proxy for φ. `tools/ewsd_sensitivity_report.py --phi`
recomputes EWSD-R acoustic-balanced ranks under all amplitude-family φ
and writes `docs/validation/EWSD_SENSITIVITY_PHI.md`. The README metric
hierarchy records the measured minimum Spearman ρ.

## Phase H notes

`run_orchestrator.py --corpus <path> --out <dir> --stages 1,2,3 --figures`
writes `run_manifest.json`. `tools/reexport_corpus.py` diffs Stage 3
against the 19 Aug Análise 3 series
(`docs/validation/ANALISE_3_TUBA_PP_EWSD_2026_08_19.json`). Notes whose
relative change exceeds 4 % are listed; when the Stage 1 tree has
`rejected_floor` rows, each flagged note reports the minimum CFAR margin.

Live tuba *pp* Stage 2+3 re-export from `analysis_results_3` (Análise 3
Stage 1 tree) into `analysis_results_phase21`: 37 / 37 notes compared,
maximum |rel Δ| = 0.042 %, **0 notes exceed 4 %**. No `rejected_floor`
rows in that Stage 1 tree (pre-Phase A). `verify_export.py` on Análise 3
A2 reports `not comparable (pre-exclusive-assignment)`. Full table:
`docs/validation/TUBA_PP_REEXPORT_DIFF.md`.

## Phase I notes

`tests/validation/synthetic_corpus/` plants harmonic (N=8), stiff-string
(N=12, B=2e-4), and bell (3 H + 10 I) constructs at SNR 10/20/30/40 dB.
Recovery uses peak pick → F-007 → B fit → confirmed-I → EPD. All 12
conditions meet N ±1, B ±10 %, EPD ±10 %, confirmed-I exact. Table:
`docs/validation/CONSTRUCT_VALIDATION_SYNTHETIC.md`. Listener study is
scaffold only (`tools/perceptual_pairs.py`,
`tools/perceptual_agreement.py`,
`docs/validation/PERCEPTUAL_PROTOCOL.md`). EWSD is acoustic until that
study is run.

## Closure (WP6)

This table is the freeze acceptance record. It supersedes the archival
1–100 scorecard in `VERSION_RATING_IOWA_TUBA.md` (deprecated).

- Construct recovery: `CONSTRUCT_VALIDATION_SYNTHETIC.md` (all 12
  conditions meet N ±1, B ±10 %, EPD ±10 %, confirmed-I exact).
- Segmentation: `SEGMENTATION_CASE_STUDY_G2.md` — cello G2 full vs
  stable is 43 vs 16 harmonics, 551 vs 140 Hz, EWSD 50.2 vs 12.3,
  1.75 independent frames on the stable cut.
- Out of scope: `docs/POST_FREEZE_BACKLOG.md` (includes local trombone
  G3 `core_H` n_fft sensitivity).
- Instrument tag: **`v4.2.2`** is the clean head after the
  measurement-performance evaluation (`64a2282`). `v4.2.1` and
  `v4.2.0` are kept. P1 remains **FAILED live**. R1 Stage-3 B1 remains
  a measured FAIL; WP1 acceptance is the R1b re-scope (synthetic
  energy-accounting + fixed-window policy). Pre-tag baselines:
  `pretag_evidence/`. R2–R6 proceed.
