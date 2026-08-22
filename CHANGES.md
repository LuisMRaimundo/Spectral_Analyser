# v4.6.0 addendum — F-061 spectral_mass

Derived Stage 3 column. No ACD or EWSD numeric change.
Candidates tested on the 47-note clarinet corpus (inversion = level overturns
a >10% richness advantage):
  A: D1 * lambda^0.30  (Stevens sone-law exponent)      — 14.2% inversions
  B: D1 * lambda^0.15                                    — 6.3% inversions
  C: D0 * lambda^0.15  (all components count fully)      — 0.1% inversions
  D: sqrt(D0*D1) * lambda^0.15                           — 1.3% inversions (SELECTED)
C won the inversion criterion outright; D was selected over C because the
geometric-mean count halves D0's exposure to sub-audibility components and to
erb_fraction sensitivity, at the cost of 1.2 points of inversion rate.
Key empirical finding motivating the D0 ingredient: F#4 has D0 = 24.9 merged
components but D1 = 1.15 — dominance is not sparsity.

`spectral_mass` sits immediately right of
`EWSD_score_acoustic_balanced` with blue data bars. Backfill existing
workbooks with `tools/backfill_spectral_mass.py` (writes
`<name>_massfilled.xlsx`, never overwrites). Tests live in
`tests/phase_34/`.

# v4.6.0 addendum — front-door documentation

README, technical manual header / §11, and
`UPGRADE_PROGRAMME_STATUS.md` now state package 4.6.0 and point at the
round-4/5 validation notes. The density-era freeze record (`v4.2.1`)
is unchanged.

# v4.6.0 — dissonance export repairs

`hutchinson_knopoff_dissonance` is now Hutchinson & Knopoff (1978) eq. (3).
The previous mean-pair quantity is
`hutchinson_knopoff_legacy_mean_pair_scaled`. Sethares no longer overrides
the base signature; default `metric_mode` is `minamp_norm`.
`dissonance_metric_mode` is exported on every row.
`analyze_real_timbre(save_directory=None)` no longer crashes. Hygiene:
lazy HK g-table, symmetric `find_local_minima`, unused imports and dead
harmonicity flags removed. Tests live in `tests/phase_33/`.
Migration: `docs/validation/DISSONANCE_MIGRATION.md`.

# v4.5.0 — per-column formula versions

Package version is 4.5.0 so the three F-037 generations that shared
4.4.0 are no longer ambiguous. Every compiled/MIR export column has a
`formula_id` and `formula_version`. MIR value columns export companion
stamps. CI rejects unstamped export columns.
`tools/build_corpus_manifest.py` records `source_sha256` (same helper
as Stage 3) for a later move of the Desktop corpus. Tests live in
`tests/phase_33/`.

# v4.4.0 addendum — Parncutt 1.2-CB cutoff (open item)

`roughness_parncutt_kernel` accepts `cutoff_cb` (H&K-style hard zero).
Default remains `None`. `x_cutoff=20` is numerical only; the aggregate
error bound is `|R(20)−R(∞)| ≤ (∑a)² κ` in
`ROUGHNESS_BANDWIDTH_BASIS.md`. **Open item:** should `cutoff_cb=1.2`
become the default? That would move F-037.

# v4.4.0 addendum — bandwidth validity (Zwicker 15.5 kHz ceiling)

Zwicker CB returns NaN above 15.5 kHz. F-037 drops pairs whose higher
member exceeds that ceiling and exports
`roughness_pairs_excluded_above_validity`. The f0 = 1000 Hz 20-partial
row changes (~31.5% of the uncapped total was undefined). Other
bandwidth expressions are audited in
`docs/validation/BANDWIDTH_VALIDITY_AUDIT.md`; guards that would change
ACD / ERB-weighted density / Sethares / default H&K are deferred.
H&K default remains `hk1978`; cello C2–C6 register from committed
metadata is in `HK_SUBBASS_BANDWIDTH.md`.

# v4.4.0 addendum — roughness basis signed off on provenance

`zwicker_cb` is the provenance-consistent F-037 default: Plomp & Levelt
(1965) used Zwicker, Flottorp & Stevens (1957) critical bands, not ERB.
The previous “PL ref” column was an identity check and is labelled as
such. Overlay on P&L Fig. 10 is outstanding but non-blocking.

# v4.4.0 addendum — H&K sub-bass bandwidth (open item)

`HutchinsonKnopoffDissonance.cbw` is still `1.72 · f^0.65` by default.
Optional `low_frequency_basis="zwicker_below_200hz"` is available and
does not change default arithmetic. At 50 Hz the 1978 fit is ~21.7 Hz
against a Zwicker CB near 100 Hz. **Open item:** should the hybrid
become the default for the S-region? Author decision required.
Comparison: `docs/validation/HK_SUBBASS_BANDWIDTH.md`. The four
previously noted defects in `dissonance_models.py` were not touched.

# v4.4.0 addendum — roughness alias retired

`_roughness_aures_1985` now raises `NotImplementedError`. New Stage 1
exports write NaN in `roughness_aures_1985`. Use
`roughness_parncutt_kernel`. Archived values used a mis-specified
bandwidth and are not comparable; the change is not a rescaling.
See `docs/validation/ROUGHNESS_MIGRATION.md` and export map §11.

# v4.4.0 — Phase 33: roughness Zwicker bandwidth basis

Proposed default `bandwidth_basis="zwicker_cb"` for F-037. Round-3
`0.25·ERB` is too narrow below 500 Hz (classical CB flattens near
100 Hz). `erb` remains selectable. Primary-source confirmation against
Plomp & Levelt (1965) figures is **outstanding**; the default may
change. Tests live in `tests/phase_33/`. Artefact:
`docs/validation/ROUGHNESS_BANDWIDTH_BASIS.md`. ACD / EWSD numerics
unchanged.

# v4.4.0 addendum — CI hang-killer and live_audio marker

`pytest-timeout` (300 s) and `@pytest.mark.live_audio` keep local-path
and Stage 1 sweeps out of the default suite. Formula-ID uniqueness is
gated on CI. Default `addopts` is `-m "not live_audio"`.

# v4.4.0 addendum — roughness kernel attribution

`mir_descriptors` pairwise roughness is Parncutt / Plomp–Levelt, not
Aures (1985). Aures is a filterbank temporal-envelope model and is not
implemented. The denominator `0.25 f + 24.7` conflated Parncutt’s 0.25
CB normalisation with the Glasberg & Moore ERB slope; the corrected
form is `x = df / (0.25 * (0.108 f + 24.7))`. At 1 kHz the kernel
maximum moves from df ≈ 275 Hz to df ≈ 33 Hz. On a 40-partial 1/n
series at 146.83 Hz the score falls to 5.2% of the old value; on a
110 Hz harmonic stack (phase-5 fixture) to 0.43%. A 1 kHz pair at
df = 33 Hz rises 3.45× (kernel now near its maximum). Column renamed
to `roughness_parncutt_kernel`; `roughness_aures_1985` is a one-version
deprecated alias. Not imported into `tools/spectral_density_hill.py`.
The 49-note corpus was not recomputed here.

# v4.4.0 addendum — ACD erb_fraction on a harmonic series

The 8-ERB “usable range at least [0.5, 1.5]” claim is discarded: that
grid cannot merge at any tested fraction. Re-measured on a 40-partial
1/n series at 146.83 Hz under `fixed_erb_grid`. `merged_count == 40`
only at `erb_fraction = 0.25`; D1 stays within 1% of the unmerged 1/n
value only on `[0.25, 0.5]`. `merged_count` is more sensitive than D1.
Register dependence (same series, f0 in C2–C6) is reported in
`docs/validation/ACD_ERB_FRACTION_SENSITIVITY.md`. Default remains 1.0.

# v4.4.0 addendum — ACD merge stability and D1 headline

Default ERB merge is now `fixed_erb_grid` (order-independent ERB-rate
bins). On the synthesised D3 Stage 1 tier sweep it cut ACD wander from
3.80% (`moving_centroid`) to 2.74%. Neither strategy fell below ~2%;
hard assignment is the remaining limit and a roex-overlap stub is
documented, not implemented. FFT-tier gate is 4% relative (measured max
plus 1 pp, rounded up; not above 5%). Decision:
`docs/validation/ACD_MERGE_STRATEGY.md`.

Headline `ACD_score` is now `sum_k r_k D1_k` (F-057). D2 saturates at
`(π²/6)²/(π⁴/90) = 2.500` on a 1/n series; a 15× change in partial
count moves D2 by 29%. Dynamic range over N ∈ [8, 40] and slope ∈
[0.5, 2.0]: D0 5.0×, D1 15.0×, D2 9.7×. The previous D2-based score is
`ACD_score_D2_dominance`. `ACD_D0_minus_D1` is a texture descriptor.
Goldens in `tests/phase_32/golden/acd_golden.json` were regenerated
because the headline order changed from D2 to D1; well-separated
K-recovery values themselves are unchanged (D1 == D2 == K).

# v4.4.0 — Phase 13: Auditory Component Density + EWSD diagnostics

ACD (F-057–F-060) is an additive companion. F-048 / F-049 / F-050
**numerical outputs for valid rows are unchanged.** Formula IDs F-051–F-054
are already allocated (harmonic matching / body-stop); ACD takes the next
free IDs. Tests live in `tests/phase_32/` because `tests/phase_13/` already
holds exclusive-assignment tests.

ACD keeps the EWSD decomposition (ratio × typical magnitude × effective
count) but uses energy shares, reports `N_eff` (`D2`) directly, merges
peaks within one ERB, and emits the ordered pair `(ACD_score,
ACD_magnitude_per_component)`. `r_k` is derived from compartment energy,
not Excel. Sub-bass is not aggregated. Invariance figures:
`docs/validation/ACD_INVARIANCE_TABLE.md` (generated by the test).

Part B (additive diagnostics only):

- B1 companion point under bootstrap energy ratios
- B2 bootstrap bias + BCa intervals
- B3 F-050 labelled `partial_multiset_sensitivity`
- B4 seed from `source_sha256`
- B5 exception / `_empty_row` family fields are NaN
- B6 balanced total requires three families
- B7 eligibility uses `his_ratio_input_sum`
- B8 measured f0 preferred
- B9 corpus φ homogeneity flag
- B10 `d10` double-penalty documented; thesis-safe membership is an **open item**
- B11 comment on `strengths * ratio` (weighted_mass only)

Open governance items (not resolved here): F-049 wording clash between
`README.md` / `metric_contract.py` and `acoustic_alignment_metric_policy`;
`alpha = 0.50`; `d10` in `THESIS_SAFE_WEIGHT_FUNCTIONS`.

# v4.3.0 — Balanced component density (F-056)

Hill $q=1$ `note_balanced_component_density` on a pool stricter than
F-047 (confirmed I; exclude
`diagnostic_low_frequency_residual_not_partial` and unconfirmed rows).
Exported immediately left of `EWSD_score_acoustic_balanced`. F-049 is
diagnostic only; level-dependent; not for cross-note comparison.
F-042 / F-047 / F-048 / F-049 algebra is unchanged.

# R6b — Audit, discriminating re-exports, composite correction

Addendum `docs/validation/R6B_ADDENDUM.md`. Flute *pp* B5/B6 F-047
hand-matches; verdict (a) (diagnostic S + unconfirmed I at the *pp*
ceiling). Iowa bass + cello *pp*/*mf* re-exported under the R6
profile; halt |ΔEWSD| treated as an explained generation shift (EPD
flat). New-code Iowa bass EPD–MIDI stays flat; EWSD pooled +0.20 is
G-string composition. Composite: headline 76.6 unchanged; D-updated
72.225. No analysis-module or CORDAS-script edit.

# R6 — Runbook re-exports on v4.2.3

Seven corpora (trombone/flute pp-mf-ff, cello ff from
`D:\CORDAS_3\CELLO`) re-exported at `1db94e1` / tag `v4.2.3`. One
profile, `verify_corpus` ok. Diff vs pretag + CORDAS predictions +
dated Part D addendum: `docs/validation/REEXPORT_DIFF_SUMMARY.md`.
No F-042/047/048/049 change.

# R5 — Planted-amplitude oracle for C1/C2

C1/C2 now use an external EWSD/EPD oracle from planted amplitudes
(`ewsd_pure` / F-047), not the bootstrap point inside its own interval.
C2 varies independent frame count at fixed partials and SNR. Measured
C1 coverage is 100 % (over-cover); C2 log-log slope is −0.281. The
bootstrap was not retuned. Dated addendum; original scores unchanged.

# R4 — EPD-primary density and estimated_snr_db

EPD (`note_effective_component_density`) is the primary noise-robust
density; EWSD is the energy-weighted complement (B7). Stage-1/3 export
`estimated_snr_db` (power-weighted mean of validated-harmonic peak-vs-floor
`snr_db`). Dictionary + `metric_contract`. Pretag trombone/flute
dynamic-ordering annotated as partly SNR-mediated.

# R3 — Leading/trailing digital-silence trim

Files with ≤ 2 s of leading or trailing digital zeros now match the
trimmed take on load (`audio_silence_trim.py`). ADSR_Segmenter is not
modified. Eval B5 prepend NaN (0 validated harmonics) was the silent
head locking analysis to file start.

# R2 — One metric, one value at the fixed window

Stage-1 Metrics `core_harmonic_energy_ratio` is the component ΣA²
partition. Stage-1 `EWSD_score_acoustic_balanced` is stamped from the
same `compute_ewsd` path Stage-3 uses. The diagnostic density column
is not EWSD. `metric_single_source` is fail-closed in `data_integrity`
and `verify_export`. Path table: `docs/validation/METRIC_SINGLE_SOURCE.md`.

# R1b — Census-held G3 and WP1 re-scope

Freeze the 8192-validated 71 harmonic orders and recompute G3
core_H / EWSD at 4096 and 16384 (`tools/r1b_census_held.py`).

- Held Power_raw core_H 0.9675 / 0.9910 / 0.9970 (inside 3 %).
- Held EWSD 70.65 / 91.69 / 119.44 tracks native Stage-3 EWSD.
- B1 failure is partition / n_fft-scaled density, not census dropout.
- WP1 acceptance: synthetic energy-accounting + `fft_policy=fixed`.
  Cross-resolution EWSD invariance is out of scope.
- 0.24 % table is descriptor `harmonic_energy_ratio`, not Stage-3 core_H.
- Synthetic Stage-3 EWSD NaN is `ci_basis_frame_count` 2.56 < 8.

# R1 — Stage-3 B1 on tag v4.2.2 (FAIL)

Clean tree at `64a2282` tagged `v4.2.2` (`v4.2.0` / `v4.2.1` not
moved). B1 re-run through Stage 1–3 compiled research output, not
Stage-1 diagnostic EWSD.

- G3 `core_H` 0.7878 / 0.9222 / 0.9760 and EWSD 72.72 / 91.31 / 118.04
  at n_fft 4096 / 8192 / 16384 (3 % **FAIL**; matches P1 at 8192/4096).
- Flute A♯4 fails on EWSD and `core_H`; EPD stays inside 3 %.
- Synthetic Stage-3 sheet has `core_H` = 1.0 but no EWSD/EPD columns.
- WP1 remains **FAILED** on the canonical path. R2–R6 stopped.
- Harness: `tools/r1_stage3_b1.py`. Evidence:
  `RESOLUTION_DEPENDENCE_DIAGNOSIS.md` § R1.

# Measurement-performance evaluation

Recorded how accurately and stably the frozen instrument measures, and
the quality of the one available v4.2.1 corpus export. Rubric scores
only; F-042 / F-047 / F-048 / F-049 algebra is unchanged.

- Runner: `tools/run_measurement_evaluation.py` (seed 20260820).
- Report: `docs/validation/MEASUREMENT_PERFORMANCE_REPORT.md`.
  A 87.5, B 71.4, C 65.0, D 82.5, composite 76.6 on commit `4799ea0`.
- Part D used tuba pp `analysis_results_v4.2.1` only. Trombone, flute,
  and cello v4.2.1 trees were excluded (no manifest). P1 live G3
  resolution swap remains FAILED (B1).
- Raw session JSON stays local (`docs/validation/_measurement_eval/`).

# v4.2.1 supersedes v4.2.0 as the freeze reference

Scope of validity unchanged. Tag `v4.2.0` is not moved or deleted.
Package version is **4.2.1**. Pre-tag workbooks are archived under
`docs/validation/pretag_evidence/` (non-citable). P1 live G3 `core_H`
swap remains FAILED. P6 runbook re-exports are the next step after
this tag is cut on `main`.

# Post-rating remediation

P1–P3 only. F-042 / F-047 / F-048 / F-049 algebra is unchanged.
P5/P6 re-exports and the `v4.2.1` retag are **stopped**: the live G3
export swap failed the 3 % `core_H` tolerance.

- P1 (20 Aug 2026, `aa24de8`): G3 Stage 1–3 at 8192/1024 vs 4096/512.
  `core_harmonic_energy_ratio` 0.9222 vs 0.7878 (Δ 14.6 %). EWSD
  91.31 vs 72.72. Same dated run in
  `RESOLUTION_DEPENDENCE_DIAGNOSIS.md` § P1,
  `POST_FREEZE_BACKLOG.md`, and the WP1 status row (**FAILED live**).
  Synthetic WP1 tests still pass. Reproducer: `tools/p1_g3_swap.py`.
- P3: Sethares (2005) added to `REFERENCES.md` and the formula index;
  WP6 cell marked merged (`aa24de8`); A♯2 residual columns on the
  WP2 diff (post-fix only; pre historical).
- P2: GHA [32357936064](https://github.com/LuisMRaimundo/Spectral_Analyser/actions/runs/32357936064)
  py3.10 + py3.11 success (~17 min, not cancelled). Live G3 tests
  remain skip-if-missing-audio.

# WP6 — Closure dossier and freeze declaration

The upgrade programme is closed. F-042 / F-047 / F-048 / F-049 algebra
is unchanged. Tag `v4.2.0` marks the freeze-ready instrument (WP1–WP5).

- `docs/validation/UPGRADE_PROGRAMME_STATUS.md` is the acceptance
  record for A–I / D1–D6 / WP1–WP6 and supersedes the 1–100 scorecard.
- `docs/validation/VERSION_RATING_IOWA_TUBA.md` is archived as
  **DEPRECATED**.
- Phase I synthetic recovery remains
  `docs/validation/CONSTRUCT_VALIDATION_SYNTHETIC.md`.
- `docs/validation/SEGMENTATION_CASE_STUDY_G2.md` records cello G2
  full vs stable (43 vs 16 harmonics, 551 vs 140 Hz, EWSD 50.2 vs
  12.3, 1.75 frames).
- `docs/POST_FREEZE_BACKLOG.md` files the local trombone G3 `core_H`
  n_fft sensitivity and the un-run listener study.
- README Status is **Frozen at v4.2.0**. One re-export per corpus
  after the tag; no further Stage 1 iteration on a frozen corpus.
- Tests: `tests/phase_28/test_closure_dossier.py`.

# WP5 — Tag tooling, verify_corpus, runbook, v4.2.0

Freeze-ready tooling after WP1–WP4. F-042 / F-047 / F-048 / F-049
algebra is unchanged. EWSD golden vectors and the density formula
version (`v5_apply_density_metric_adapted_v6_2_psd`) were re-checked
and did not move beyond 1e-9, so no formula-version bump.

- `run_orchestrator.py` and `tools/reexport_corpus.py` already accept
  `--corpus`, `--fft-policy fixed`, and write `run_manifest.json`.
  The manifest now also records `fft_policy`, `fixed_n_fft`,
  `fixed_hop_length`, `segment_policy`, and `eligibility_policy`.
- `tools/verify_corpus.py` checks a run directory: profile id tokens
  (`fft` / `seg` / `elig`), fixed 8192/1024, primary-comparable
  profile, mixed profile ids, and degenerate CI `0.0`. Complements
  per-workbook `verify_export.py`.
- `docs/REEXPORT_RUNBOOK.md` lists the exact one-re-export-per-corpus
  commands. Those commands are not run in this WP.
- Package version is **4.2.0** (`pyproject.toml`, `CITATION.cff`).
- Tests: `tests/phase_27/test_verify_corpus.py`.

# WP4 — CI green: sparse-table noise gate and stale density contracts

The eight pre-existing CI failures all touched density/export, so they
were fixed rather than quarantined. F-042 / F-047 / F-048 / F-049
algebra is unchanged.

- `compute_acoustic_density_descriptors(..., apply_noise_gate=False)`
  lets planted peak-table tests skip the FFT floor subtract. Live Stage 1
  keeps the default gate. The floor operator on a short peak list treated
  neighbouring peaks as floor (single-tone EPD → 0; energy gates → 1+1+1).
- Energy gates with no measurable band energy are `1/3` each (a valid
  distribution), never `1+1+1`.
- Body energy sums honour `body_freq_max_hz` (`_body_freq_max_hz`),
  not the 20 kHz `BODY_DENSITY_MAX_HZ` cap.
- Phase-2 export test locks `weight_function=linear` so it tests the
  0.6/0.3/0.1 profile, not default φ=`log`.
- Inharmonic body-sum test matches confirmed-I rows, not every
  residual-sheet candidate (Phase A).

# WP3 — Production policy as code

Comparable-corpus defaults, segment pairing, and eligibility are now
enforced in `production_policy.py`. F-042 / F-047 / F-048 / F-049
algebra is unchanged.

- FFT default remains `fft_policy=fixed`, `n_fft=8192`, `hop=1024`
  (provenance reclassified as `convention`). `adaptive_tier` stays
  behind an explicit flag and sets `is_primary_comparable_profile=False`.
- `analysis_parameter_profile_id` carries `fft`, `seg`, and `elig`
  (`seg=sustain_primary_stable_diagnostic`, `elig=1` is the policy
  version, not the per-note boolean).
- Sustain is primary. A `_SustainStable` sibling or ADSR JSON sidecar
  fills diagnostic columns only (`stable_segment_ewsd`,
  `full_stable_ewsd_ratio`, `stable_segment_frames_independent`,
  `stable_segment_unrepresentative`). Missing siblings are NaN
  (`nan_not_zero_v1`), never 0.0. Values are never substituted.
- Eligibility: `ewsd_primary_analysis_eligible=False` when
  `sustain_frame_count_independent < MIN_INDEPENDENT_FRAMES` (8) or
  `harmonic_validated_count ≤ 2`. Then `degenerate_partial_set=True`
  and CI `rel_uncertainty` is NaN, never 0.0.
- Stage 3 emits `stage3_issue` when a compiled workbook mixes
  `analysis_parameter_profile_id` values.
- Tests: `tests/phase_26/test_production_policy.py`.

# WP2 — D1–D5 verified on main after WP1

D1–D5 (PR #75) remain on `main`. Post-WP1 (`38cb535`) re-export of trombone
A♯2 *ff* and tuba A2 *pp* is in `docs/validation/TROMBONE_AS2_DEFECT_FIX_DIFF.md`.
A♯2: `harmonic_validated_count = 92` (≥ 86), H74/H79 included via D1
weak-margin override, `subbass_upper_bound_hz = 58.15`. Tuba A2: 8
validated, EPD 3.77, EWSD 16.11, CI columns present. F-042 / F-047 /
F-048 / F-049 algebra is unchanged.

# Residual exclusion uses the window main-lobe, not ENBW

WP1 of the closure programme. F-042 / F-047 / F-048 / F-049 algebra is
unchanged. Peak-power still uses ENBW; residual exclusion uses
`RESIDUAL_EXCLUSION_FOOTPRINT` (8 bins for Blackman–Harris 4-term, ±4).

- Two exported footprints: `peak_power_footprint_bins` (ENBW) and
  `residual_exclusion_footprint_bins` (main-lobe diameter).
- Residual region = analysis band minus the exclusion union of every
  validated harmonic and every confirmed inharmonic. Leakage guard and
  `outside_harmonic_window_candidate_energy_ratio` use the same width.
- `residual_region_hz_total + excluded_region_hz_total == analysis_band_hz`
  (fail closed, one-sided).
- Tests: `tests/phase_25/test_residual_footprint.py`.

# Post-A–I defect fixes: weak-margin persistence override, tolerance continuity override, sub-bass bound unification, CI provenance, naming hygiene

Defects from the IOWA trombone A♯2 *ff* SustainStable review of `5b1a1c7`.
F-042 / F-047 / F-048 / F-049 algebra is unchanged.

- **D1** Weak CFAR margin + strong persistence → `validated_weak` and
  `include_for_density`. New constant `PARTIAL_PERSISTENCE_STRONG_FRACTION`
  (0.9). Counts: `harmonic_validated_weak_count`;
  `harmonic_validated_count` includes the weak class;
  `harmonic_validated_strict_count` is the previous definition. Body stop
  still applies after the override; `accepted_slots_above_body_stop` stays 0.
- **D2** Isolated `rejected_by_tolerance` inside a continuous accepted run
  may re-enter when both neighbours are included, persistence ≥ 0.9, and
  `|dev| < TOLERANCE_CONTINUITY_OVERRIDE_FACTOR × cap` (1.25). Limb
  `spacing_cap_continuity`. Export `tolerance_continuity_override_count`
  and `frequency_refinement_method` / `refined_frequency_hz`. Triple-assignment
  losers stay rejected.
- **D3** `subbass_upper_bound_hz` is computed once from F-020
  (`SubBassPolicy.resolve_f020_bound`). Export `subbass_bound_formula =
  min(0.5*f0, 80)` and `subbass_bound_f0_used_hz`. Member counts use that
  bound.
- **D4** CI provenance only: `ci_resampling_unit`, `ci_n_resampled`,
  `ci_bootstrap_iterations`, `ci_block_length_frames`, `ci_seed`,
  `ci_width_flag`, `ci_width_note`. Estimator unchanged.
  `CI_WIDTH_PARTIAL_CORRELATION_N` (30) names the wide-interval cause.
- **D5** `hop_duration_s` + `window_duration_s`; `frame_duration_s` remains
  a deprecated alias. One energy pie (`component_energy_pie.png`) titled
  Validated-partial energy balance. Dictionary states the incompatible
  bases of the three “energy ratio” columns.

- **Tests:** `tests/phase_23/test_trombone_as2_defect_fixes.py`

# Resolution-invariant energy and density bases; fixed-FFT default for comparable corpora; tier policy documented

D6 from the IOWA trombone *ff* E2–C5 review of `5b1a1c7`. F-042 / F-047 /
F-048 / F-049 algebra is unchanged. `density_formula_version` is
`v5_apply_density_metric_adapted_v6_2_psd` because D_k amplitudes are
n_fft-normalised (same φ, corrected basis).

- **D6.1** Diagnosis: the G3→G♯3 EWSD step follows the window, not the note
  (`docs/validation/RESOLUTION_DEPENDENCE_DIAGNOSIS.md`). Peak ΣA² scales as
  N²; sub-bass row count scales with N.
- **D6.2** Energy sums are Heinzel PSD `S(f)=|X|²/(f_s Σw²)` integrated over
  Hz; peak energy is `|X|²/(Σw)²`. Residual excludes the ENBW footprint.
  Export `energy_basis=psd_per_hz`, `window_enbw_hz`, `peak_footprint_bins`,
  `residual_region_hz_total`.
- **D6.3** D_k uses `n_fft_normalization_factor` onto `FIXED_N_FFT_DEFAULT`
  (8192). Sub-bass remains F-020 members only.
- **D6.4** `fft_policy ∈ {fixed, adaptive_tier}`; **fixed** (8192/1024) is
  the default for corpus runs. `fft_policy` is in
  `analysis_parameter_profile_id`; mixed-tier corpora are not primary.
  Stage 3 emits a `stage3_issue` when a corpus mixes n_fft.
- **D6.5** Research exporter reads `harmonic_search_range_hz` /
  `Magnitude Range (dB)`. `included_above_body_stop_count` invariant is 0;
  `validated_harmonics_above_body_stop_count` is CFAR-validated then excluded.
- **D6.6** `tools/reexport_corpus.py --corpus --fft-policy` and
  `tools/compare_runs.py`.
- Constants: `FIXED_N_FFT_DEFAULT` (8192), `FIXED_HOP_LENGTH_DEFAULT` (1024),
  `HANN_ENBW_BINS` (1.5), `FFT_POLICY_DEFAULT` (`fixed`).
- **Tests:** `tests/phase_24/test_resolution_invariance.py`

# Phase 22 / Phase I — Construct validation + perceptual scaffold

The pipeline recovers planted N, B, EPD, and confirmed-I on a synthetic
corpus. Listener data are not collected.

- `tests/validation/synthetic_corpus/` plants harmonic, stiff-string, and
  bell constructs at SNR 10/20/30/40 dB and recovers them through the
  Stage 1 evidence path. Acceptance: N ±1, B ±10 %, EPD ±10 %,
  confirmed-I exact. Table:
  `docs/validation/CONSTRUCT_VALIDATION_SYNTHETIC.md`.
- `tools/perceptual_pairs.py` / `tools/perceptual_agreement.py` write the
  pairwise judgement schema and score a filled CSV against EWSD rank.
  Protocol: `docs/validation/PERCEPTUAL_PROTOCOL.md`. README states that
  EWSD is acoustic until that study is run.
- **Tests:** `tests/validation/synthetic_corpus/test_construct_recovery.py`,
  `tests/phase_22/test_perceptual_scaffold.py`

# Phase 21 / Phase H — Reproducibility as one command

One command regenerates a corpus run and writes an audit manifest.

- `python run_orchestrator.py --corpus <path> --out <dir> --stages 1,2,3 --figures`
  writes `run_manifest.json` (commit, versions, constants hash, parameter
  profile id, input SHA-256 hashes, wall time).
- `python -m tools.reexport_corpus` re-runs Stage 2/3 from existing Stage 1
  workbooks and diffs `EWSD_score_acoustic_balanced` against a previous
  series (default: 19 Aug Análise 3). Notes above
  `REEXPORT_REL_DELTA_FLAG_PCT` (4 %) are listed with `rejected_floor`
  CFAR margins when those rows are in the Stage 1 workbooks.
- **Tests:** `tests/phase_21/test_reproducibility_command.py`

# Phase 20 / Phase G — Weight function φ provenance

φ is a documented convention, not a free GUI-only choice.

- `DENSITY_WEIGHT_FUNCTION_DEFAULT = "log"` (provenance class `convention`):
  log-amplitude as a first-order loudness proxy (Fechner 1860; Stevens 1955;
  Zwicker & Fastl 1990). Stage 1 / Stage 2 / orchestrator defaults follow it.
- `weight_function` is on every Stage 1/2/3 row; `analysis_parameter_profile_id`
  already encodes `wf=…`.
- `tools/ewsd_sensitivity_report.py --phi` recomputes EWSD under all
  amplitude-family φ and writes Spearman ranks to
  `docs/validation/EWSD_SENSITIVITY_PHI.md`.
- **Tests:** `tests/phase_20/test_weight_function_phi.py`

# Phase 19 / Phase F — Schema and count hygiene

One meaning per header, and F-020 diagnostic rows contribute 0 to S sums.

- Per-row sheets keep `sample_note_tag` / `sample_id` / `partial_pitch_name`
  and drop overloaded `Note`. Complete Spectrum pitch names stay off
  (`EXPORT_COMPLETE_SPECTRUM_PITCH_NAMES`).
- `Validation_Metrics` / `Metrics` / `Analysis_Metadata` export
  `subbass_upper_bound_hz` (F-020), `subbass_member_count`, and
  `floor_rows_rejected_count`. Only `*_validated_count` /
  `*_confirmed_count` are partial counts.
- The Sub-bass sheet now includes the LF diagnostic band above F-020
  (capped at `min(f0, LOW_FREQUENCY_DIAGNOSTIC_UPPER_HZ)`). Those rows
  are `lf_diagnostic_not_member` and are excluded from
  `subbass_density_sum` and `subbass_energy_sum`.
- `*_ungated` twins remain the audit copies; compile S defaults to
  F-020 members.
- **Tests:** `tests/phase_19/test_schema_and_count_hygiene.py`

# Phase 18 / Phase E — Provenance that cannot be wrong

`analysis_version` and `export_schema_version` come from one module
(`analysis_provenance.py`): package metadata plus
`git describe --always --dirty`. Callers no longer hard-code `4.1.0`.

- Export `code_commit`, `code_dirty`, `package_version` on
  `Analysis_Metadata` and `Stage3_Summary`. Figure titles carry the commit.
- `component_energy_pie.png` is drawn from `*_energy_sum`, not copied
  from the amplitude pie. Amplitude title:
  `Validated-partial amplitude balance`. F-020 diagnostic LF rows are
  excluded from the S wedge unless `include_lf_diagnostic_in_amplitude_pie`.
- `data_integrity.validate_header_contract_consistency` fails closed when
  the same header has two metric-contract identities.
- CLI: `python verify_export.py <workbook>` prints commit, versions,
  invariants, H/I/S counts, and comparability. Run-2 / v4.0.3 workbooks
  report `not comparable (pre-exclusive-assignment)`.
- **Tests:** `tests/phase_18/test_provenance_and_verify_export.py`

# Phase 17 / Phase D — Uncertainty by default

Bootstrap CIs ship on every Stage 2/3 run without a GUI opt-in.

- F-044 (`note_density_final`) and F-050 (`EWSD_score_acoustic_balanced`)
  remain default-on.
- F-047 (`note_effective_component_density`) now has a companion CI:
  resample pooled H+I+S amplitudes and recompute the same participation
  ratio. Algebra is unchanged.
- `ci_basis_frame_count` and `ci_basis_partial_count` sit beside each
  CI; fewer than 10 independent frames sets
  `ci_basis_frames_insufficient`.
- Research sheet `Uncertainty_Summary` flags relative uncertainty
  above 25 %.
- Stage 3 EWSD publication chart (`ewsd_acoustic_balanced_ci.png`)
  draws the CI band; titles carry note tag, run id, commit, version.
- Stage 1 export no longer fails when `Acoustic_Interpretation_Status`
  is already present on confirmed inharmonic rows.
- **Tests:** `tests/phase_17/test_uncertainty_defaults.py`

# Phase 16 / Phase C — Independent high-n harmonic guards

The spacing cap cannot stop floor harvest at high n. Persistence and a
minimum CFAR margin are independent of the body stop; the stop remains
the load-bearing high-n cut.

- `expected_false_harmonic_slots = harmonic_slot_expected_count × CFAR_PFA`.
- `accepted_slots_above_body_stop` must be 0 after gating.
- `harmonic_acceptance_suspect` when accepted count exceeds
  (body-stop order + expected false slots).
- `HARMONIC_MIN_CFAR_MARGIN_DB` (3 dB): `0 ≤ cfar_margin_db < 3` →
  `cfar_marginal`, excluded from density. `cfar_marginal_count` per note.
- Continuity rule off by default (`HARMONIC_CONTINUITY_RULE_ENABLED`).
  After 3 consecutive rejects, later accepts need persistence ≥ 0.9.
- Application order: cap / exclusive assignment → CFAR margin →
  persistence → optional continuity → body stop.
- **Tests:** `tests/phase_16/test_high_n_harmonic_guards.py`

# Phase 15 / Phase B — Temporal persistence

The STFT time axis is a first-class acceptance criterion.

- Per-frame local maxima on the sustain segment (`temporal_persistence.py`;
  full file if segmentation is off). Peak table: frame, bin, magnitude.
- `persistence_fraction` = fraction of sustain frames with a *detected*
  peak (per-frame local max ≥ 6 dB above that frame’s median) within
  `tol_hz` of the time-averaged peak frequency; also
  `frequency_jitter_cents` and `magnitude_jitter_db`. Band-max harvesting
  is not used: a ±β·f0 window at high n almost always contains a noise
  maximum.
- Harmonic `include_for_density` requires
  `persistence_fraction ≥ PARTIAL_PERSISTENCE_MIN_FRACTION` (0.7).
  Failing test: `exclusion_reason = low_temporal_persistence (p=…)`.
- Inharmonic confirmation uses the same fraction (no longer defaults to 1.0
  when the frame table exists).
- `Per_Note_Processing_Metadata`: `sustain_frame_count`,
  `sustain_frame_count_independent`, `frame_duration_s`.
- Body-stop labelling does not overwrite a persistence reject.
- **Tests:** `tests/phase_15/test_temporal_persistence.py`

# Phase 14 / Phase A — Confirmed-inharmonic partial class

Residual rows after harmonic exclusion are candidates, not the I
compartment. `inharmonic_confirmation.py` applies the same evidential
standard as harmonic acceptance:

- CFAR (F-043) at `CFAR_PFA` (`1e-2`); export `cfar_detected_i`,
  `cfar_margin_db_i`.
- Local peak + prominence ≥ `INHARMONIC_MIN_PROMINENCE_DB` (6 dB).
- Temporal persistence ≥ `PARTIAL_PERSISTENCE_MIN_FRACTION` (0.7);
  missing frame table defaults to 1.0 until Phase B.
- Not in the main-lobe/sidelobe footprint of an accepted harmonic
  (`spectral_leakage_guards`); export `leakage_guarding_harmonic_order`.
- Not on the F-007 comb when the inharmonicity model is applied
  (`rejected_stretched_harmonic` → reassign to H as
  `strict_validated_stretched`).

Confirmed rows (`inharmonic_status = confirmed_inharmonic_partial`) form
I for F-014, `inharmonic_energy_sum`, pies, Sethares, and EWSD D_I.
`Inharmonic Spectrum` keeps all candidates plus test columns;
`Confirmed_Inharmonic_Partials` holds survivors only. F-042 / F-047 /
F-048 / F-049 algebra is unchanged.

- **Tests:** `tests/phase_14/test_inharmonic_confirmation.py`
- **Docs:** CONSTANTS_PROVENANCE, EXPORT_COLUMN_DICTIONARY, METRIC_FORMULA_INDEX F-014,
  `docs/validation/UPGRADE_PROGRAMME_STATUS.md`

# Exclusive harmonic assignment; validated-partial gating; column semantics

Stage 1 corrections after the IOWA tuba *pp* A2 (run 2) audit. Metric *formulas*
F-042 / F-047 / F-048 / F-049 are unchanged; their **input domain** is now
validated partials only.

- **F-051 exclusive assignment:** each `peak_bin_index` may satisfy at most one
  slot (`apply_exclusive_harmonic_assignment`). Conflicts resolve by minimum
  |Δcents|, then lower *n*. Tolerance rejects are written as
  `exclusion_reason = rejected_by_tolerance (dev=… Hz > cap=… Hz)` with
  `tolerance_limb = spacing_cap` and are not relabelled `above_harmonic_body_stop`.
- **Fail-closed invariant:** `peak_bin_index` unique among
  `include_for_density=True` and among `{strict_validated, snr_validated}`
  (`data_integrity.validate_unique_peak_bin_assignment`). Failure sets
  `debug_counts_invariant_status = failed`.
- **F-012 gating (Fix 2):** `effective_partial_density`, `linear_sum_amplitude_*`,
  Sethares, and amplitude pies use `is_validated_partial` (`include_for_density`
  for harmonics; inharmonic rows enter only as `confirmed_inharmonic_partial`,
  see Phase 14 / Phase A). Ungated copies keep `*_ungated`.
- **Column semantics:** per-row sheets use `sample_note_tag` + `sample_id` +
  `partial_pitch_name`. `Note` remains the take identity on summary sheets only.
  Complete Spectrum pitch names are off by default (`export_complete_spectrum_pitch_names`).
- **Counts / ranges:** `harmonic_slot_candidate_count` (matching diagnostic;
  formerly `harmonic_slot_matched_count`) and `harmonic_validated_count`.
  Analysis Parameters export `harmonic_search_range_hz` and
  `low_frequency_diagnostic_range_hz`. Sub-bass rows above F-020 are
  `physical_low_frequency_residual` and contribute 0 to `subbass_energy_sum`.
- **Export schema:** `spectral_analysis_schema_2026_08`.
- **Tests:** `tests/phase_13/test_exclusive_assignment_and_validated_gating.py`.
- **Docs:** `DENSITY_EXPORT_SCHEMA` §R.8 / §R.10, `EXPORT_COLUMN_DICTIONARY`,
  `EWSD_CONSTRUCT_VALIDITY` (pre-phase runs are not comparable without re-export).

# Documentation alignment — full v4.1.0 sweep

Synchronized user-facing documentation and citation metadata with package **v4.1.0**
(low-f₀ harmonic identity). Core peak-power integrals are noise-gated over 0–20 kHz;
`canonical_density` still follows the validated / stop-trimmed harmonic list.

- **`TECHNICAL_MANUAL_COMPLETE.md`:** §5.2.1 honesty on gated vs stop-trimmed integrals; new **§14.4** Stage 1 audit columns; re-export requires Stage 1 + 2 + 3.
- **`METRIC_FORMULA_INDEX.md`:** F-051–F-055 (spacing cap, comb centre, f0 refit, body stop, noise gate).
- **`CANONICAL_PIPELINE_AND_EXPORT_SEMANTICS.md`:** §3 f0, §4 harmonics, §11 version map v4.1.0.
- **`DENSITY_EXPORT_SCHEMA.md` / `EXPORT_COLUMN_DICTIONARY.md`:** §R.9 identity columns.
- **`GUI_OPTION_REFERENCE.md`:** body stop is a validation/count cut; density ceiling stays 20 kHz.
- **`MANUAL_COVERAGE_REPORT.md` / `NOTE_FATNESS_AND_DENSITY_GUIDE.md`:** v4.1.0 scope and F-051+ links.
- **`pipeline.md` / `pipeline_runtime.md`:** Stage 1 policy v2 / f0 refit / stop-as-count.
- **`metrics_dictionary.json` / `CITATION.cff` / `README.md`:** package 4.1.0; documentation map.

# Low-f₀ harmonic validation — f0 refit and noise-gated density (v4.1.0)

Policy v1 integrated noise-floor mass at *pp*. Policy v2 (spacing cap) plus
the noise gate correct that: every density integral subtracts the smoothed
floor and clips at 0 over 0–20 kHz. The body stop remains a validation cut
and no longer sets `density_effective_ceiling_hz`.

An iterative low-order f0 (and B) refit (H1–H8, cents limb, SNR ≥ 20 dB /
prominence ≥ 12 dB, amplitude-weighted LS) is applied when it disagrees
with the joint fit by more than 15 cents, so a drifted centre cannot reject
real mid-order partials. When that first pass has at least three peaks, its
B (including 0) is the second-pass stretch; a global peak-centre B is not
allowed to invent stretch on a harmonic instrument.

# Low-f₀ harmonic validation — spacing-capped tolerance, body stop, fragility (v4.1.0)

Fixes false high-n harmonic validation on low-register notes (IOWA tuba *pp*
C1 reported 226 “validated” harmonics, most of them the 2–20 kHz noise floor).

- **Spacing-capped tolerance (policy v2):** `tol_hz(n) = max(bin, min(n·f0·tol_cents(n)/1200, β·f0))` with `β = 0.30`. The half-width is centred on the Inharmonicity_Fit prediction `n·f0·√(1+B n²)` when stretch is enabled, not on the ideal comb. Audit column `tolerance_limb ∈ {cents, spacing_cap, bin_floor}`.
- **Harmonic-body noise-floor stop:** when the validated envelope stays within 3 dB of the noise floor for 5 consecutive orders *and* the envelope slope is a plateau (≤ 1 dB/order), higher orders are excluded from the validated set (`include_for_density`). The stop is a validation cut only: density integrals still run over 0–20 kHz. A decaying tail that sits 6–10 dB above the floor does not fire the stop. `density_effective_ceiling_hz` is the global ceiling.
- **Fragility flag:** default-on bootstrap CI plus ±10 ms window perturbation; `density_fragile` when CI width or perturbation spread exceeds 10 %. Carried through Stage 3 and the research export.
- **Low-f₀ resolution guard:** escalate `n_fft` when `bin > f0/8` if the sustain allows; else `low_f0_resolution_warning`.
- **GUI/CLI:** β, body-stop toggle/margin, and CI on/off next to the density ceiling control.
- **Tests:** `tests/acoustic_validity/test_low_f0_harmonic_validation.py` and helper-level `tests/phase_12/test_low_f0_harmonic_validation.py`.
- **Docs:** TECHNICAL_MANUAL §5.2.1; `Analysis_Metadata` carries policy version, β, stop parameters, and CI settings.

# Export schema hygiene — metadata weights, sample_id, dedupe (v4.0.3)

Fixes remaining export/schema bugs identified in the architecture audit after v4.0.2:

- **Metadata H/I/S weights:** research `Metadata` sheet now maps each weight key to its
  own Phase-2 fallback (`phase2_inharmonic_application_weight`, etc.) instead of always
  returning the harmonic weight for all three keys.
- **`Diagnostic_Metrics.sample_id`:** NaN placeholder columns are treated as unpopulated;
  authoritative IDs are copied from `Density_Metrics` via shared `attach_sample_id_from_density`.
- **Research `_2` columns:** `_sanitize_dataframe_columns` runs `dedupe_identical_columns`
  after uniquifying headers so identical merge suffix columns are dropped.
- **`Analysis_Settings_By_Note.zero_padding`:** per-note numeric values are preferred
  (including `n_fft_effective / n_fft` derivation) before falling back to the tier label.
- **Tests:** `tests/phase_11/test_export_schema_v403.py`.
- **Docs:** `DENSITY_EXPORT_SCHEMA` §R.7–R.8, `EXPORT_SCHEMA_AUDIT_REPAIR` re-export table,
  `EXPORT_COLUMN_DICTIONARY` column traps, README outputs table.

# Documentation alignment — full v4.0.3 sweep

Synchronized all user-facing documentation to package **v4.0.3**:

- **`TECHNICAL_MANUAL_COMPLETE.md`:** version header; new **§14.3** export schema/join keys; GUI
  weight vs Phase-2 distinction in §15; §19A items 7–8 (open column renames, redaction); §21 cross-links.
- **`CANONICAL_PIPELINE_AND_EXPORT_SEMANTICS.md`:** **§11** export version map; `export_row_identity` in §9.
- **`MANUAL_COVERAGE_REPORT.md`:** v4.0.3 scope, keyword sweep, status table rows.
- **`GUI_OPTION_REFERENCE.md`:** **§A5** export weight naming table.
- **`NOTE_FATNESS_AND_DENSITY_GUIDE.md`:** `sample_id` join note; export doc links.
- **`pipeline.md` / `pipeline_runtime.md`:** `export_row_identity.py` on compile/export path.
- **`metrics_dictionary.json`:** `registry_version` 4.0.3; `export_schema_versions` block.
- **`README.md`:** documentation map + re-export note.

# Export hygiene — research merge fix + dead-column pruning (v4.0.2)

Fixes blank columns in research exports when satellite compiled sheets lacked matching
`sample_id` values, and enforces removal of never-populated columns from compiled and
research workbooks.

- **`merge_keys_for_frames`** (`export_row_identity.py`): merge on `sample_id` only when
  anchor and satellite IDs overlap; otherwise fall back to `Note`. Research export no
  longer synthesizes mismatched `sample_id` values on satellite sheets before merge.
- **`drop_dead_columns`**: shared helper drops all-NaN / all-blank text columns (never
  all-zero numerics). Applied to compiled `Density_Metrics`, `Canonical_Metrics`,
  `Debug_Counts`, `Per_Note_Processing_Metadata`, and all major research data sheets.
- **`sample_id` propagation**: Stage 2 attaches authoritative `sample_id` from
  `Density_Metrics` onto `Canonical_Metrics`, `Diagnostic_Metrics`, `Debug_Counts`, and
  `Per_Note_Processing_Metadata` before Excel write.
- **Tests:** `tests/phase_11/test_research_export_merge_satellite_sheets.py`,
  extended `test_export_row_identity.py`, updated EWSD skip test for pruned columns.
- **Docs:** README, CHANGES, `EXPORT_SCHEMA_AUDIT_REPAIR.md`, `DENSITY_EXPORT_SCHEMA` §R.6.

# Research export — EWSD data-bar formatting + documentation (v4.0.1)

- **`EWSD_score_acoustic_balanced`:** red Excel **data bars** on research `Spectral_Density_Metrics` (conditional formatting, min–max scale, `#C00000`).
- **Research export script:** `tools/export_research_density_workbook.py` v1.1.3.
- **Tests:** `tests/phase_11/test_research_export_includes_ewsd.py` asserts data-bar rule on export.
- **Docs:** README, CHANGES, `DENSITY_EXPORT_SCHEMA` §R.5, TECHNICAL_MANUAL research sheets, `EXPORT_COLUMN_DICTIONARY`, `MANUAL_COVERAGE_REPORT`, `metrics_dictionary.json`.

# Export schema audit repair (v4.0.0)

Fixes architecture-level workbook incongruences (audit 2026-06):

- **`sample_id`** primary join key; duplicate `Note` labels no longer collapse on merge when `sample_id` is present.
- **Density semantics:** `density_raw_phase2_profile_weighted`, `density_component_ratio_weighted_sum`, research `richness_weighted_body_density`; corrected `density_weighted_sum_alias_of`.
- **Weights:** `phase2_*_application_weight` vs `component_*_energy_ratio`; metadata no longer promotes row-0 per-note weights globally.
- **Diagnostic_Metrics:** prefixed collision columns (`diagnostic_*_raw_power`, etc.).
- **Research:** `Primary_Statistics_Eligible`, `Stage3_Summary` (note-only `Stage3_Diagnostics`), dedupe identical `_2` merge columns, clarified row counts.
- **Doc:** `docs/validation/EXPORT_SCHEMA_AUDIT_REPAIR.md`.

# Documentation sweep — v3.9.0 metric hierarchy and fatness guide (2026-06-02)

Aligns user-facing docs with EWSD v18.1 Tier A–C and the acoustic fatness scalar:

- **README:** version 3.9.0; metric hierarchy table; Stage 3 diagnostics + bootstrap CI; link to fatness guide.
- **New:** `docs/validation/NOTE_FATNESS_AND_DENSITY_GUIDE.md` — practical steps to read `note_effective_component_density`.
- **CANONICAL_PIPELINE §A:** primary fatness scalar is `note_effective_component_density` (F-047); `effective_partial_density` retained for legacy continuity.
- **TECHNICAL_MANUAL §7.7.1:** documents F-047 pooled participation ratio.
- **DENSITY_EXPORT_SCHEMA §2.3:** `note_effective_component_density` normative entry.
- **pipeline.md / pipeline_runtime.md:** Stage 3 module inventory (pure math, UQ, contract).

# Stage 3 EWSD-R v18.1 — Tier C (fail-closed contract + diagnostics sheet)

- **Contract module:** `tools/ewsd_stage3_contract.py` — typed failures, `Stage3MergeResult`, status ok/degraded/failed.
- **Research export:** `Stage3_Diagnostics` sheet; optional `ewsd_fail_closed=True` blocks export on hard Stage 3 failure.
- **Pipeline contract:** version `SSA_CANONICAL_PIPELINE_2026_06_STAGE1_STAGE2_STAGE3_EWSD_v18_1_UQ`.
- **CI:** explicit EWSD validation gate in `.github/workflows/ci.yml`.
- **Theory memo:** `docs/validation/EWSD_THEORY.md`.
- **Version:** 3.9.0.

# Stage 3 EWSD-R v18.1 — Tier B (bootstrap UQ + sensitivity + construct validity)

- **Bootstrap UQ:** `tools/ewsd_uncertainty.py` propagates partial + ratio uncertainty into
  `EWSD_score_*_ci_low/high`, `*_rel_uncertainty`, `ewsd_uncertainty_sources` (research export).
- **Sensitivity CLI:** `tools/ewsd_sensitivity_report.py` — alpha rank stability and acoustic construct checks.
- **Construct validity doc:** `docs/validation/EWSD_CONSTRUCT_VALIDITY.md`.
- **Tests:** `tests/phase_11/test_ewsd_uncertainty.py`, extended export CI assertions.

# Stage 3 EWSD-R v18.1 — Tier A validation (pure math + golden + corpus)

- **New module:** `tools/ewsd_pure.py` — numpy-only reference implementation (F-048/F-049).
- **Refactor:** `tools/ewsd_core.py` delegates compartment math to `ewsd_pure`; version tag `EWSD-R v18.1`.
- **Golden vectors:** `tests/phase_11/fixtures/ewsd_golden/` (8 cases) + independent reference cross-check.
- **Corpus regression:** committed `tests/phase_11/fixtures/ewsd_corpus_reference.json` (49 violin notes);
  live recompute test when `EWSD_CORPUS_ROOT` or default analysis folder is present (`frequency_ceiling_hz=20000`).
- **Validation status:** F-048/F-049 marked **validated** in `docs/validation/FORMULA_VALIDATION_STATUS.md`.

# Stage 3 EWSD-R v18 integration in research export (2026-06-02)

Integrates Effective Weighted Spectral Density (EWSD-R v18) into the canonical
research workbook export so bibliography-facing density comparisons no longer
require a separate post-processing GUI step.

- **New modules:** `tools/ewsd_core.py` (EWSD-R v18 computation core),
  `tools/ewsd_research_integration.py` (Stage 3 discovery, compute, left-join).
- **Pipeline hook:** `post_compile_research_export.run_research_workbook_export`
  now triggers EWSD inside `tools/export_research_density_workbook.build_workbook`.
  Per-note `spectral_analysis.xlsx` workbooks under the analysis folder are
  recomputed with `individual_exact` mode; H/I/S ratios are read from each
  note's Metrics sheet (`auto_excel_required`) — no silent H=I=S=1 defaults.
- **Research columns added to `Spectral_Density_Metrics`:**
  `EWSD_score_total`, `EWSD_score_acoustic_balanced`, `ewsd_mode`,
  `ewsd_primary_analysis_eligible`, `ewsd_his_ratio_source`, `ewsd_H_ratio`,
  `ewsd_I_ratio`, `ewsd_S_noise_ratio`, `ewsd_weight_function_canonical`,
  `ewsd_acoustic_balance_alpha`, `ewsd_stage3_version`, `ewsd_merge_status`.
- **Publication gate:** use only rows with `ewsd_primary_analysis_eligible == True`
  for final thesis statistics. For cross-instrument bibliographic distance,
  prefer `EWSD_score_acoustic_balanced`; keep `EWSD_score_total` as strict EWSD.
- **Tests:** `tests/phase_11/test_research_export_includes_ewsd.py`.
- **Tier A validation (v18.1):** `tools/ewsd_pure.py`, golden vectors in
  `tests/phase_11/fixtures/ewsd_golden/`, committed 49-note corpus reference in
  `tests/phase_11/fixtures/ewsd_corpus_reference.json`, tests
  `test_ewsd_golden_vectors.py`, `test_ewsd_pure_matches_core.py`,
  `test_ewsd_corpus_regression.py`.
- **Docs:** README, `CHANGES.md`, `TECHNICAL_MANUAL_COMPLETE.md`,
  `EXPORT_COLUMN_DICTIONARY.md`, `DENSITY_EXPORT_SCHEMA.md` §R,
  `CANONICAL_PIPELINE_AND_EXPORT_SEMANTICS.md` §9, `METRIC_FORMULA_INDEX.md`,
  `pipeline.md`, `pipeline_runtime.md`.

## Documentation sweep — orchestrator, contract, metadata (2026-06-02)

Aligns remaining entry points and metadata with the three-stage pipeline:

- **Orchestrator / entry points:** `run_orchestrator.py`, `pipeline_orchestrator_integrated.py`,
  `pipeline_orchestrator_gui.py`, `main.py` — Stage 3 post-compile EWSD messaging.
- **Contract:** `pipeline_contract.py` — Stage 3 constants, EWSD module paths,
  contract version `SSA_CANONICAL_PIPELINE_2026_06_STAGE1_PROC_AUDIO_STAGE2_COMPILE_STAGE3_EWSD`.
- **Metadata:** `metrics_dictionary.json` (EWSD columns), `docs/GUI_OPTION_REFERENCE.md` §A4,
  `docs/parameter_provenance.md`, `docs/validation/FORMULA_VALIDATION_STATUS.md` F7/F8,
  `installers/README.md`.

# Density energy gate: full-spectrum region basis + non-harmonic terminology (2026-05-29)

Resolves the "band-vs-peak" inconsistency between the inharmonic density weight
(`wI`) and the reported inharmonic energy, generalised for ANY instrument.

Root issue (terminology + basis): the code conflated two physically distinct
things under "inharmonic" — (a) partial INHARMONICITY (discrete non-`n·f0`
tonal peaks: piano stretch, bells; coefficient B) and (b) the inter-harmonic
RESIDUAL (broadband bow/breath/attack noise + any non-`n·f0` content). The v57
density gate also used BODY-ceiling-truncated band energies, which made the
non-harmonic energy share arbitrary and instrument-dependent (bright/noisy tones
carry most residual energy ABOVE the body ceiling, so the gate silently
collapsed toward a peak-only basis).

- **`acoustic_density_core.py` energy gate → v58
  (`v58_full_spectrum_region_energy_gate`).** The gate now weights each band's
  structural strength by the FULL-SPECTRUM, total-power-normalised region energy
  triple (`harmonic_energy_ratio` / `residual_energy_ratio` /
  `subbass_energy_ratio`). The three region powers partition every spectral bin,
  so they conserve energy (sum to total power) and are instrument-agnostic:
  discrete inharmonic peaks (piano/bell) and broadband noise (bowed/wind) both
  land in the non-harmonic residual band and both correctly contribute to
  perceived spectral density. New audit fields
  `component_strength_energy_gate_{harmonic,non_harmonic_residual,subbass}` and
  `density_band_energy_basis` are exported; the legacy
  `component_strength_energy_gate_{h,i,s}` names are retained as aliases.
- **Terminology corrected.** The density middle band is now documented as the
  NON-HARMONIC / inter-harmonic RESIDUAL, not "inharmonic". Partial
  inharmonicity (coefficient B + inharmonic-peak energy) is a SEPARATE physics
  descriptor and is no longer conflated with the density gate. The component
  energy-ratio pie is relabelled as the peak/physics view, explicitly distinct
  from the density residual basis.
- Test expectations and README/docs updated `v57 → v58`. Full suite green
  (112 passed, 2 skipped), including the subbass-suppression regression and the
  strength-formula-units contract.

# Unified single-scalar note density across H+I+S (2026-05-30)

Adds `note_effective_component_density` — ONE per-note density that spans all
three bands (harmonic + inharmonic + sub-bass), separates instruments, and is
designed as the per-note basis for downstream chord/aggregate density.

- **Definition.** Energy-weighted participation ratio (effective number of
  energy-bearing spectral components) pooled over the validated harmonic peaks,
  inharmonic peaks, and sub-bass particles using raw amplitudes:
  `N_eff = (Σ Aᵢ²)² / Σ Aᵢ⁴`. One scalar; covers harmonics + inharmonics +
  sub-noise; computed in `compile_metrics._energy_distribution_density`
  (Density_Metrics column).
- **Why this one.** It is timbre-discriminating (Orchidea pooled means
  Trombone 5.08 > Cello 2.74 > Clarinet 1.82; clarinet lowest at matched pitch),
  far less register-bound than `note_density_final` (pooled r≈−0.63 vs −0.96),
  and **aggregates for chords**: applying the same formula to the pooled partials
  of several notes yields the chord's effective component count, with coincident
  partials fusing (modelling masking) rather than double-counting. 131/131 notes
  populated across the three corpora.
- `note_density_final` and the harmonic-only "fatness" columns are retained
  unchanged; this is the unified cross-band density for aggregate work.

# Energy-distribution density — timbral "fatness" restored (2026-05-30)

Adds register-robust, energy-based density descriptors that separate timbres,
addressing the finding that `note_density_final` (log-weighted, per-note
normalised) behaves as a partial-COUNT measure dominated by register: across
130 Orchidea notes it correlated r≈−0.96 with pitch and barely separated the
three instruments at matched pitch (mean spread 0.11). The historical objective
of the code — *more harmonics carrying considerable energy ⇒ denser* — is
recovered as explicit first-class columns rather than by mutating the validated
`note_density_final`.

- **New compiled `Density_Metrics` columns** (computed in
  `compile_metrics._energy_distribution_density` from the validated harmonic
  peaks of each note's Harmonic Spectrum sheet, so no Stage-1 re-run is needed):
  - `harmonic_effective_partial_count` — participation ratio
    `(Σ Aₙ²)² / Σ Aₙ⁴` (effective number of partials carrying energy).
  - `harmonic_energy_above_fundamental_ratio` — fraction of harmonic energy not
    in the fundamental (0 = concentrated at f0; →1 = spread across partials).
  - `harmonic_energy_centroid_order` — energy-weighted mean harmonic order
    (brightness in harmonic-order units).
  - `effective_partial_density` — full-spectrum participation ratio (surfaced).
- **Validated on the cello/clarinet/trombone Orchidea corpora.** Pooled Neff
  Trombone 5.04 > Cello 2.64 > Clarinet 1.80; energy-above-f0 0.82 / 0.54 / 0.31.
  At matched pitch the new density separates the instruments ~16× more than
  `note_density_final` (mean spread 1.69 vs 0.11 for Neff), with the
  acoustically-correct ordering (brass spread > bowed string > closed-tube reed).
- Note: `note_density_final` is intentionally unchanged (count/register density,
  with its bootstrap CI / UQ contract intact); the new columns are the
  complementary energy-distribution density.

# Robust f0 global-fit order-clipping bugfix (2026-05-29)

Fixes the high f0-rejection rate (and consequent suppression of the
inharmonicity-B fit) on low-pitched, harmonic-rich tones (cello C2–C4).

- **`_estimate_f0_global_robust` (proc_audio.py) now FILTERS partials to
  rounded order `[1, max_n]` instead of CLIPPING the order to `max_n`.** The
  weighted least-squares estimator `f0 = Σ(w·n·f)/Σ(w·n²)` was fed every
  detected strict peak (cello C2 carries ~100+ peaks up to order ~300), but the
  order label was clipped to `max_n=15`. Each high-order partial was therefore
  relabelled as order 15, so e.g. a 6500 Hz partial contributed 6500/15 ≈ 433 Hz
  to the f0 estimate, dragging it far above the truth (C2: 65 Hz → ~114 Hz,
  |Δf0| ≈ 48 Hz). The acceptance gate (|Δf0| ≤ 2 % f0) then correctly rejected
  the garbage fit on almost every low note (`f0_fit_accepted=False`), which also
  starved the downstream inharmonicity (B) estimation. Low-order partials are
  both reliably labelable and the least inharmonic, so they are the correct
  basis for the pure `f = n·f0` model; the fix restricts the fit to them.
  Verified on synthetic cello combs: C2/F2/A2 now estimate within |Δf0| < 0.5 Hz
  (fit_quality ≈ 0.011 ≪ 0.10 gate) and are accepted. All 21 f0 / inharmonicity
  / FFT-invariance / ground-truth regression tests pass.

# density_metric_raw_per_note_balance reconciliation (2026-05-29)

Closes the last cross-sheet scale residual found while auditing the cello run.
`density_metric_raw_per_note_balance` (the per-note, energy-ratio-weighted
comparator `r_H·D_H + r_I·D_I + r_S·D_S`) was computed on the canonical
log-weighted band density in the `Density_Metrics` sheet (cello C2 = 3.22) but
on the raw wide-frame band sums in the harvested `Diagnostic_Metrics` sheet
(cello C2 = 173624). The single-source-of-truth reconciliation in
`compile_metrics._write_compiled_excel` only propagated `density_metric_raw` /
`density_metric_normalized`, leaving this column on the stale raw basis.

- **`density_metric_raw_per_note_balance` added to
  `_CANONICAL_DENSITY_COLS_TO_PROPAGATE`.** The reconciliation now overwrites the
  wide frame with the canonical `Density_Metrics` value, so every derived sheet
  reports the same log-weighted figure. Reconciled-column count goes 9 → 10.
  Verified on the cello corpus: `Density_Metrics` and `Diagnostic_Metrics` now
  both report `density_metric_raw_per_note_balance` = 3.2199 (matching the
  `density_metric_raw` = 2.75 log basis); the raw 173624 leak is gone.
  `tests/phase_2/test_phase2_profile_actually_applied.py` and
  `tests/phase_6/test_density_metrics_excel_export_phase2_profile.py` still pass
  (they read the authoritative `Density_Metrics` value, unchanged).

# note_density_final scale-consistency fix (2026-05-29)

Fixes a cross-sheet scale inconsistency in `note_density_final` surfaced on the
cello run, plus log-noise polish:

- **note_density_final no longer uses the raw display-sum fallback
  (`compile_metrics._resolve_note_density_sum_column`).** The resolver had a
  third-priority fallback to the legacy display columns `Harmonic Partials sum`
  / `Inharmonic Partials sum` / `Sub-bass sum`. In the per-note `Metrics` sheet
  (and therefore in the harvested wide compiled frame) those columns carry a RAW
  partial sum on a different scale than the GUI-weighted band density
  `*_density_sum` (cello C2: `Harmonic Partials sum` = 174178 raw vs
  `harmonic_density_sum` = 3.22 log). The fallback produced a wrong-scale
  `note_density_final` (173624) in the wide-frame-derived `Diagnostic_Metrics`
  sheet, while the canonical `Density_Metrics` sheet and the research workbook —
  which carry the true `*_density_sum` columns — stayed correct (3.22). The
  fallback is removed: `note_density_final` is now computed **only** from the
  canonical weighted band sums, so it is correct wherever present and simply
  absent from the diagnostic sheet (which lacks those columns) rather than wrong.
  Verified end-to-end: `Density_Metrics` and research `note_density_final` =
  3.2199, 26/26 non-NaN; `Diagnostic_Metrics` no longer carries the column.
- **Wide-frame skip logged as INFO, not WARNING.** When the wide compiled frame
  cannot compute `note_density_final` (no canonical `*_density_sum` columns —
  the expected, correct outcome), the message is now an INFO noting it is
  computed authoritatively in `Density_Metrics`; a WARNING is kept only for any
  other (unexpected) context.

Known, deferred (documented for transparency): the wide-frame / `Diagnostic_Metrics`
density family (`density_metric_raw`, `weighted_*_density_contribution`) is still
computed from the raw `Harmonic Partials sum` and therefore reported on a raw
scale in that diagnostic sheet, inconsistent with the canonical `Density_Metrics`
values. Publication outputs (`Density_Metrics`, research `Spectral_Density_Metrics`)
are unaffected. A full reconciliation of the per-note `Metrics` `Partials sum`
semantics with the canonical weighted band sums is planned as a dedicated phase.

Full suite: 112 passed, 2 skipped.

---

# Adaptive observation energy-anchoring + CFAR log fix (2026-05-29)

Fixes a real defect surfaced by a cello (IOWA arco mf, C string) run and a
stale log string:

- **Energy-anchored adaptive observation (`obs_w_formula_version`
  `v56_occupancy_ratio` → `v57_energy_anchored_occupancy`).** The per-note
  adaptive observation that feeds `AdaptiveDensityEngine` (and hence
  `density_metric_raw` / the Phase-2 profile) was computed purely from
  structural *occupancy + density-per-slot*, each normalised by the band's
  expected slot count. Because bands have wildly different expected counts
  (harmonic ~ hundreds of orders; sub-bass ~ a handful of bins), at permissive
  salience thresholds a spectrally narrow, energetically negligible band could
  saturate its occupancy on the noise floor and dominate the learned profile.
  Observed: cello **C2 sub-bass carried 3.6e-5 of the spectral energy yet drew
  `pure_observation_w_s = 0.52`**, and the wide inharmonic band out-weighted the
  99.7%-energy harmonic band. Fix (`acoustic_density_core.py`): each band's
  structural strength is now weighted by its **measured energy share**
  (`component_strength_energy_gate_{h,i,s}`, exported for audit), so a band with
  ~0 energy contributes ~0 to the observation while richness still modulates the
  weight among energetically-present bands. This makes the adaptive observation
  physically coherent with the measured component energy ratios that
  `note_density_final` already uses. New regression:
  `tests/phase_6/test_subbass_observation_cap.py::test_energy_anchoring_suppresses_noise_floor_subbass_band`.
- **CFAR log string corrected (`proc_audio.py`).** The per-note harmonic summary
  no longer announces the obsolete "SNR ≥ 3 dB" criterion; it now states the
  active gate: "(CFAR detection [Pfa-based] + saddle prominence ≥ 3 dB)".

Note: `note_density_final` (energy-ratio based) is unaffected by the first fix —
it never used the adaptive weights. Full suite: 112 passed, 2 skipped.

---

# Methodological closure: CFAR acceptance, primary-by-default, full UQ (2026-05-29)

Closing the final three methodological inconsistencies flagged in the doctoral
re-evaluation:

- **Harmonic acceptance is now detection-theoretic (CFAR).** The ad-hoc fixed
  3 dB SNR margin is replaced by a cell-averaging CFAR test
  (`harmonic_peak_validation.cfar_peak_detection`): at each refined peak bin the
  power must exceed a threshold derived from a stated false-alarm probability
  (`pfa`, default `1e-2`) against a locally-estimated, peak-trimmed noise floor.
  A candidate becomes `strict_validated` only when CFAR-detected **and** clearing
  saddle prominence — the same significance-gate philosophy already applied to
  the inharmonicity coefficient `B`. New audit columns `cfar_margin_db` /
  `cfar_detected` in `Harmonic_Inclusion_Audit`. Calibrated to preserve the
  validated acoustic chain (dense low-register recovery, FFT invariance,
  ground-truth accuracy all green).
- **Primary comparable profile is the analysis default.** The orchestrator GUI
  now defaults the amplitude weighting to `Logarithmic` (the PRIMARY profile,
  `wf=log`), so even an isolated single run is cross-instrument comparable by
  default; any other choice downgrades the run to EXPLORATORY (logged and
  flagged). Per-note `Analysis_Metadata` already self-declares
  `is_primary_comparable_profile` / `analysis_parameter_profile_id`.
- **Full uncertainty quantification.** `bootstrap_note_density_final` gains
  `propagate_ratio_uncertainty` (default used by the pipeline = True): component
  energy ratios are recomputed inside each resample from the bootstrapped band
  energies, so the uncertainty of BOTH the band sums and the ratios is propagated
  jointly. New column `note_density_final_uncertainty_sources`
  (`partials+ratios`). The window/n_fft sensitivity is exposed as an opt-in study
  tool `tools/note_density_nfft_sensitivity.py` (re-analysis at multiple FFT
  sizes is intentionally kept out of the hot path).

Full suite: 111 passed, 2 skipped.

---

# Scientific-robustness closure blocks (2026-05-29)

Closing the three open robustness gaps surfaced by the earlier phases:

- **Block 1 — joint (f0, B) inharmonicity fit.** `inharmonicity_model.fit_inharmonicity_coefficient`
  now estimates `f0` and `B` jointly (linear OLS on `f_n^2 = a·n^2 + c·n^4`,
  `f0=sqrt(a)`, `B=c/a`, iterative order reassignment) with a **t-test
  significance gate** on the `n^4` term (keeps `B` only when `|t|>=2`). The
  inharmonicity fit is now fed **local-maximum peak centers** (parabolic sub-bin,
  `acoustic_density_core._local_maxima_peak_centers`) instead of the raw
  significant-bin cloud. This closes the end-to-end B-magnitude under-recovery:
  `tests/phase_11` now asserts recovery of a known `B=3e-4` within `[0.4x,2.5x]`
  and `B≈0` (no false positive) on a pure-harmonic stack. New export:
  `inharmonicity_fit_f0_hz`. FORMULA_VALIDATION_STATUS.md F3 updated (resolved).
- **Block 2 — refuse cross-profile aggregation.** `Canonical_Primary_Filtered`
  is now hard-restricted to a single analysis profile
  (`_restrict_primary_subset_to_single_profile`; dominant profile kept, others
  dropped), and a single authoritative `corpus_comparable_for_statistics`
  boolean is written to `Analysis_Metadata`. Primary statistics can no longer be
  silently computed across mixed profiles.
- **Block 3 — uncertainty emitted with the metric.** Each compiled note now
  carries a per-note non-parametric bootstrap CI for `note_density_final`
  (`note_density_final_ci_low`, `note_density_final_ci_high`,
  `note_density_final_rel_uncertainty`), computed transform-aware via
  `density_uncertainty.bootstrap_note_density_final` (guarded; NaN if a per-note
  workbook is unreadable). Surfaced on both `Density_Metrics` and research
  `Spectral_Density_Metrics`.

Full suite: 106 passed, 2 skipped.

---

# Scientific-robustness phases (2026-05-29)

Three phased additions to harden acoustic/scientific robustness:

- **Phase 1 — cross-profile comparability guard.** `compile_metrics._corpus_comparability_audit`
  surfaces a corpus verdict (`corpus_comparability_status`, profile count,
  primary-comparable row count) into `Analysis_Metadata` and WARNS when a
  compiled workbook mixes analysis profiles or is single-but-EXPLORATORY.
  Density metrics are only comparable within one primary profile;
  `Canonical_Primary_Filtered` remains the physically isolated comparable subset.
  Tests: `tests/phase_11/test_corpus_comparability_guard.py`.
- **Phase 2 — end-to-end ground-truth accuracy.** New
  `tests/phase_11/test_ground_truth_accuracy.py` synthesises signals with known
  content and asserts the full pipeline recovers harmonic **frequencies** (<25
  cents) and **amplitude ratios** (1/n within 35%), and produces **no false
  inharmonicity** on a pure-harmonic stack. FINDING: end-to-end recovery of a
  non-zero inharmonicity **B magnitude** is unreliable (the fit is anchored to
  the stretch-absorbing robust-fitted f0; a joint f0–B fit is required). Logged
  as an open limitation in `docs/validation/FORMULA_VALIDATION_STATUS.md` (F3).
- **Phase 3 — uncertainty quantification.** New `density_uncertainty.py`
  (`bootstrap_density_ci`, `nfft_sensitivity`) gives a non-parametric bootstrap
  CI for `note_density_final` (resampling per-partial contributions; ratios held
  fixed) and an n_fft/window sensitivity band (CV, relative range). Tests:
  `tests/phase_11/test_density_uncertainty.py`, including an end-to-end check
  that `note_density_final` is bounded-stable across n_fft on a fixed signal.

Full suite: 102 passed, 2 skipped.

---

# Code + documentation synchronization (2026-05-29)

## Functional changes

- **`note_density_final`** (new primary per-note scalar density) on the compiled
  `Density_Metrics` sheet and the research `Spectral_Density_Metrics` sheet:
  `r_H·harmonic_density_sum + r_I·inharmonic_density_sum + r_S·subbass_density_sum`,
  where `r_*` are the per-note **measured** `component_*_energy_ratio` values (not the
  Bayesian adaptive weights) and each `*_density_sum` already carries the GUI amplitude
  weight function. NaN-propagating. Source: `compile_metrics._compute_note_density_final`.
  Highlighted light blue on the research sheet.
- **`Harmonic_Inclusion_Audit`** read-only per-note sheet in each `spectral_analysis.xlsx`:
  one row per harmonic order with `exclusion_reason` and the SNR/prominence/ceiling/
  deviation diagnostics that explain density inclusion/exclusion.
- **Harmonic validation correctness:** f0-adaptive saddle-prominence window (±f0/2),
  removal of the asymmetric `n>10` gate, candidate re-alignment to the fitted f0, and
  a tolerance-scaled refine radius (restores FFT-tier amplitude invariance). Fixes the
  dense low-register (cello) under-counting.
- **Performance:** `mir_descriptors._roughness_aures_1985` vectorised with a
  critical-band window (per-note runtime ~333 s → ~20 s on cello C2; result unchanged
  to ~1e-7).
- **Module decomposition:** extracted the pure peak-validation cluster from
  `proc_audio.py` into the new `harmonic_peak_validation.py` (re-exported by
  `proc_audio`). Note: `harmonic_validation.py` is a DISTINCT pre-existing module
  (`validate_harmonic_series_matched`) and is unchanged.
- **New test guards:** `tests/perf/` (roughness + per-note budget) and
  `tests/acoustic_validity/` (instrument-family harmonic-richness contracts).
- **Cleanup:** unused modules archived to `Backup/` and removed from `pyproject.toml`
  py-modules (`interface`, `export_paths`, `public_audio_identifiers`,
  `reference_signal_utils`, `runtime_versions`, `audio_analysis/batch_example.py`,
  `scripts/harmonic_count_audit.py`). See `Backup/README.md`.

## Documentation updated for the above

- `metrics_dictionary.json`: added `note_density_final` (canonical).
- `docs/METRIC_FORMULA_INDEX.md`: added F-042 (`note_density_final`).
- `docs/EXPORT_COLUMN_DICTIONARY.md`: interpretation row + column-inventory entries for
  `note_density_final`.
- `docs/DENSITY_EXPORT_SCHEMA.md`: normative §2.1 (`note_density_final`) and §2b
  (per-note `Harmonic_Inclusion_Audit`).
- `pipeline.md`: added `harmonic_peak_validation.py`, corrected the `harmonic_validation.py`
  description, and added an "Archived modules (moved to `Backup/`)" section.
- `docs/GUI_OPTION_REFERENCE.md`, `docs/TECHNICAL_MANUAL_COMPLETE.md`,
  `docs/MANUAL_COVERAGE_REPORT.md`: annotated `interface.py` as archived to `Backup/`.

---

# Documentation synchronization to current code state (2026-05-27)

## Files touched and rationale

- `docs/TECHNICAL_MANUAL_COMPLETE.md`
  Updated provenance and limitations sections to reflect current canonical documentation sources: constants registry (`docs/CONSTANTS_PROVENANCE.md`) and formula-validation status (`docs/validation/FORMULA_VALIDATION_STATUS.md`), replacing stale TODO-era framing. Also corrected FFT-tier normalization equations to match the current Phase-8 `quantity_kind` contract (`peak_amplitude_sum: N_ref/N`, `peak_power_sum: (N_ref/N)^2`) and documented backward-compatible broadband-L2 branches explicitly.

- `docs/MANUAL_COVERAGE_REPORT.md`
  Synchronized scope/caveat language with current repository state; added explicit resolved rows for constants-provenance registry completion and formula-validation baseline (F1-F6).

- `docs/parameter_provenance.md`
  Added a current-state note clarifying this file is now a historical Phase-6 ledger for signature defaults, while constants provenance is canonicalized in `docs/CONSTANTS_PROVENANCE.md`.

- `pipeline.md`
  Updated Phase-6 provenance row to reference the current constants-provenance registry path and removed stale generator-path wording. Updated P3 normalization row to the current Phase-8 peak-sum normalization law.

- `pipeline_runtime.md`
  Updated runtime-path P3 normalization row to the current Phase-8 peak-sum normalization law (`N_ref/N` and `(N_ref/N)^2`) instead of the legacy broadband-L2 form.

- `docs/METRIC_FORMULA_INDEX.md`
  Corrected F-021 and F-022 to the current Phase-8 tier-normalization formulas for exported peak-amplitude and peak-power sums.

- `README.md`, `pipeline_runtime.md`
  Applied terminology/notation consistency polish only (e.g., `tier-normalized`, `normalization`, `N_ref`) with no change to technical claims, formulas, or export semantics.

- `metrics_dictionary.json`
  Bumped `registry_version` to `phase_8_docs_sync_v1` to mark documentation/registry synchronization to the current code state.

## Scope and non-scope

- No computational logic changed.
- No `.py` implementation module modified.
- No tests modified.
- Documentation and metadata synchronization only.

# README.md technical body restoration (2026-05-27)

## Files touched and rationale

- `README.md`
  Inserted the technical scaffolding sections (Status; What this software does; Installation; Usage; Outputs; Scientific governance) at named positions, between the pre-existing authorial sections. The opening paragraph, Theoretical anchoring, License, Citation, and Acknowledgements sections were preserved byte-for-byte. The README now functions as a doctoral-grade entry document and links to `REFERENCES.md`, `CITATION.cff`, `CHANGES.md`, `docs/TECHNICAL_MANUAL_COMPLETE.md`, `docs/EXPORT_COLUMN_DICTIONARY.md`, `docs/METRIC_FORMULA_INDEX.md`, `docs/CONSTANTS_PROVENANCE.md`, `docs/validation/FORMULA_VALIDATION_STATUS.md`, `tests/formula_validation/`, and `LICENSE`.

## Scope and non-scope

- No `.py` file modified.
- No test modified.
- No file under `docs/` modified.
- No authorial content altered.
- `REFERENCES.md`, `pyproject.toml`, `CITATION.cff`, and `LICENSE` untouched.

# Proportionate formula-validation suite (2026-05-27)

## Files touched and rationale

- `tests/formula_validation/` (new directory, six tests plus conftest)
  Six AST-based formula-extraction tests covering the canonical form of: the H/I/S weighted density formula (F1), the Phase-8 FFT-length normalisation factor (F2), the stiff-string inharmonicity fit (F3), the sub-bass upper bound (F4), the effective partial density (F5), and the Jensen-Shannon divergence (F6). The suite complements the numerical regression tests under `tests/phase_*`: those detect drift in numerical outputs, these detect drift in the symbolic structure of the formulae themselves.

- `docs/validation/FORMULA_VALIDATION_STATUS.md` (new)
  Per-formula record of canonical form, module, reference, test path, and status. This document is the citation target for any methodology-chapter reference to the formula-validation suite.

## Scope and non-scope

- No existing test modified.
- No `.py` module under the implementation tree modified.
- The suite is deliberately proportionate (six formulae), not a full mirror of the earlier `Spectral_Analyser` formula_validation suite, because v55 has scientific modules (`adaptive_density_engine.py`, `inharmonicity_model.py`, `subbass_policy.py`, `spectral_normalization.py`, etc.) that have no counterpart in that earlier layout. A direct mirror would be incoherent.
- Tests are conservative: they assert structural invariants (presence of `sqrt`, polynomial degree, additive structure) rather than exact AST identity, to avoid firing on legitimate refactoring.

# Authorial completion of README.md and CITATION.cff; LICENSE file and pyproject.toml license synchronisation (2026-05-27)

## Files touched and rationale

- `README.md`
  Filled the four `[AUTHOR: ...]` placeholder blocks with content supplied by the author (opening framing paragraph, dissertation reference sentence, full proprietary licence summary, FCT funding citation, and acknowledgements). Technical sections were not altered.

- `CITATION.cff`
  Filled author identity (Luís Raimundo, NOVA University of Lisbon), version and release date, proprietary licence reference (`LicenseRef-Proprietary`), and added a structured `references` entry citing the FCT doctoral grant DOI `10.54499/2020.08817.BD`. ORCID and project URL fields were omitted as the author has not supplied them.

- `LICENSE`
  Created at the repository root with the full proprietary copyright notice supplied by the author.

- `pyproject.toml`
  `license = {text = "Scientific Research Use"}` was replaced with `license = {text = "Proprietary - All Rights Reserved"}` to synchronise the package metadata with the LICENSE file and the README. The `"License :: Other/Proprietary License"` classifier was added if absent. No other field was modified.

## Scope and non-scope

- No `.py` file modified.
- No test modified.
- No file under `docs/` modified.
- `REFERENCES.md` not modified.
- `py-modules` list in `pyproject.toml` not modified.
- No licence was selected on the author's behalf — the proprietary posture was supplied by the author.

# Constants provenance registry and pyproject.toml module manifest completion (2026-05-27)

## Files touched and rationale

- `docs/CONSTANTS_PROVENANCE.md`
  Created per-constant provenance registry classifying every numeric constant in `constants.py` as `primary_source`, `derived`, `convention`, or `internal_default`. Honest classification preferred over fabricated provenance.

- `constants.py`
  Extended `_PROVENANCE_SOURCED_CONSTANTS` to cover every constant classified as `primary_source`, `derived`, or `convention` in the registry. Softened the unsourced-constants notification from `RuntimeWarning` to `logging.INFO`, in keeping with the fact that `internal_default` constants are a documented design choice rather than a defect. Module-level docstring updated to reference `docs/CONSTANTS_PROVENANCE.md` and `REFERENCES.md`.

- `REFERENCES.md`
  Extended only if a new primary source was cited that was not already present.

- `pyproject.toml`
  Completed the `py-modules` manifest to include all 48 top-level Python modules. Previously, 23 modules — including all of the new scientific modules (`adaptive_density_engine`, `inharmonicity_model`, `metric_contract`, `mir_descriptors`, `spectral_normalization`, `subbass_policy`, `temporal_segmentation`, etc.) — were absent from the manifest and would not have been packaged into an installed wheel.

## Scope and non-scope

- No numeric constant value was altered.
- No constant was renamed or removed.
- No test was modified.
- No computational logic was changed.
- No exported metric or schema was changed.

# Bibliographic provenance pass — REFERENCES.md and inline docstring references (2026-05-27)

## Files touched and rationale

- `REFERENCES.md`
  Created canonical APA-7 bibliography at repository root; serves as the single source of truth for the theoretical anchors used in the scientific modules and as the bridge document between source code and dissertation.

- `inharmonicity_model.py`, `mir_descriptors.py`, `adaptive_density_engine.py`, `metric_contract.py`, `temporal_segmentation.py`
  Added short-form inline `References` blocks to module-level docstrings, mirroring the convention already used in `spectral_normalization.py` and `subbass_policy.py`. No computational logic, signatures, or exported metrics were modified.

## Scope and non-scope

- No tests modified.
- No exported metric names, schemas, or formula versions altered.
- `spectral_normalization.py` and `subbass_policy.py` were intentionally left untouched as they already carry correct inline references.

# Phase 8 - FFT-Length Normalization for Peak Sums (2026-05-26)

## Files touched and rationale

- `spectral_normalization.py`  
  Refactored `n_fft_normalization_factor(...)` to make scaling assumptions explicit via `quantity_kind`, adding peak-sum laws (`peak_amplitude_sum -> N_ref/N`, `peak_power_sum -> (N_ref/N)^2`) and preserving legacy `kind="amplitude"/"power"` as deprecated aliases to the broadband-L2 laws for backward compatibility.

- `compile_metrics.py`  
  Updated tier-normalization mapping to use peak-sum semantics for production exported sums (`harmonic/inharmonic/subbass_amplitude_sum` and `harmonic/inharmonic/subbass_energy_sum`) and switched all normalization call sites to `quantity_kind=`; this removes FFT-length bias from the compiled `*_tier_normalized` peak-sum columns.

- `pipeline_orchestrator_gui.py`  
  Updated the fallback normalization call used by Phase-1 diagnostics to the explicit peak-power law (`quantity_kind="peak_power_sum"`), avoiding legacy deprecation usage and keeping Phase-1 derived tier-normalized sub-bass energy aligned with the new Phase-8 semantics.

- `tests/phase_8/test_normalization_factor_peak_amplitude.py`  
  Added unit regression for `peak_amplitude_sum` factors at `n_fft=4096` and `n_fft=16384`.

- `tests/phase_8/test_normalization_factor_peak_power.py`  
  Added unit regression for `peak_power_sum` factors at `n_fft=4096` and `n_fft=16384`.

- `tests/phase_8/test_peak_amplitude_invariance_in_pipeline.py`  
  Added critical integration regression: synthetic sinusoid processed through real Stage-1/Stage-2 paths at two FFT lengths, asserting `harmonic_amplitude_sum_tier_normalized` invariance within 5%.

- `tests/phase_8/test_legacy_kind_keyword_still_works.py`  
  Added backward-compatibility regression ensuring legacy `kind=` still returns prior broadband-L2 scaling and emits `DeprecationWarning`.

- `tests/phase_8/test_phase_3_test_still_passes.py`  
  Added compatibility regression asserting the existing Phase-3 invariance test still passes under legacy alias behavior.

## Acoustic / methodological justification

- Peak-bin sums and broadband L2 quantities have different N-dependence under the DFT/window model; applying broadband-L2 normalization (`sqrt(N_ref/N)` for amplitude-like quantities) to peak-amplitude sums leaves a systematic cross-tier bias.
- For fixed-window harmonic peaks, coherent gain causes peak magnitudes to scale linearly with N, so peak-amplitude sums require `N_ref/N` and peak-power sums require `(N_ref/N)^2` for cross-tier comparability.

## Cross-tier discontinuity measurement (synthetic benchmark)

- Synthetic 1 kHz sinusoid benchmark (Stage 1 + Stage 2, `n_fft=4096` vs `8192`):  
  pre-Phase-8 (legacy broadband amplitude factor) step discontinuity = **29.903588%**;  
  post-Phase-8 (peak-amplitude factor) step discontinuity = **0.868704%**.

## References (APA)

- Harris, F. J. (1978). On the use of windows for harmonic analysis with the discrete Fourier transform. *Proceedings of the IEEE, 66*(1), 51-83.
- Heinzel, G., Rudiger, A., & Schilling, R. (2002). *Spectrum and spectral density estimation by the Discrete Fourier transform (DFT), including a comprehensive list of window functions and some new at-top windows* (Technical report). Max-Planck-Institut fur Gravitationsphysik.

# Phase 7.1 - Version Tagging, Compiled Exposure, and Warning Cleanup (2026-05-26)

## Files touched and rationale

- `acoustic_density_core.py`  
  Added `OBS_W_FORMULA_VERSION_CURRENT = "v56_occupancy_ratio"` and exported `obs_w_formula_version` with the pure-observation triplet so v56 audit cross-version `obs_w*` comparisons have explicit semantics; switched the canonical runtime sub-bass bound call site from `deprecated_subbass_upper_bound_hz_from_ratio(...)` to `SubBassPolicy.upper_bound_hz(...)` to remove the per-run deprecation warning flagged by the v56 audit while preserving numeric behavior.

- `pipeline_orchestrator_gui.py`  
  Added `obs_w_formula_version` to Phase 1 discovery diagnostics and `phase1_discovered_density_profiles.csv` rows so the same v56 audit traceability tag present per note is propagated into corpus-level adaptive history exports.

- `compile_metrics.py`  
  Extended compiled allow-lists and extraction plumbing to ingest/export `obs_w_formula_version`, `pure_observation_w_{h,i,s}`, `component_strength_{h,i,s}`, and `legacy_component_strength_{h,i,s}_v55` from per-note `Metrics` into `Density_Metrics`; classification logic was updated so these Phase-7 fields are visible in `Diagnostic_Metrics` and remain excluded from `Canonical_Metrics`, addressing the v56 workbook column-audit visibility gap.

- `tests/phase_7_1/test_formula_version_tagged.py`  
  Added regression ensuring `compute_acoustic_density_descriptors(...)` always tags outputs with `obs_w_formula_version == "v56_occupancy_ratio"`.

- `tests/phase_7_1/test_phase7_fields_in_compiled.py`  
  Added compile-path regression ensuring the nine Phase-7 observation/strength fields are present and populated in `Density_Metrics` and available in `Diagnostic_Metrics`.

- `tests/phase_7_1/test_no_operational_deprecation_warning.py`  
  Added runtime warning regression asserting no operational `DeprecationWarning` referencing `SubBassPolicy.upper_bound_hz` is emitted during descriptor computation.

- `tests/phase_7_1/test_numeric_invariance.py`  
  Added invariance regression that emulates the pre-7.1 deprecated-call path and asserts numeric outputs are bit-identical to the direct-policy path, guarding against silent semantic drift.

## Phase 7.1B - Per-note Metrics Serialization Gap (2026-05-26)

- `proc_audio.py`  
  Fixed the per-note `Metrics` writer gap by explicitly serializing `pure_observation_w_{h,i,s}`, `component_strength_{h,i,s}`, `legacy_component_strength_{h,i,s}_v55`, and `obs_w_formula_version` from the in-memory `compute_acoustic_density_descriptors(...)` output state into the per-note `Metrics` sheet row.

- `pipeline_orchestrator_gui.py`  
  Extended `_extract_note_density_feedback_diagnostics(...)` and `phase1_discovered_density_profiles.csv` history rows to carry the same Phase-7.1 field family (`obs_w_formula_version`, `component_strength_*`, `legacy_component_strength_*_v55`) alongside `pure_observation_w_*`, so Phase 1 CSV exports no longer drop these values.

- `tests/phase_7_1/test_phase7_fields_in_compiled.py`  
  Clarified scope as a unit/plumbing test (synthetic workbook fixture path), keeping it as valid narrow coverage.

- `tests/phase_7_1b/test_per_note_metrics_writes_all_phase7_fields.py`  
  Added integration regression that runs Stage 1 on a synthetic WAV, opens on-disk per-note `Metrics`, and verifies all ten Phase-7.1 fields are present/populated with expected semantics.

- `tests/phase_7_1b/test_compiled_has_phase7_fields_populated.py`  
  Added integration regression that runs synthetic Stage 1 + Stage 2 and asserts on-disk `compiled_density_metrics.xlsx` `Density_Metrics` contains all ten Phase-7.1 fields populated for all rows.

- `tests/phase_7_1b/test_phase1_csv_has_phase7_fields_populated.py`  
  Added integration regression validating Phase 1 discovery CSV generation path writes non-NaN `pure_observation_w_*` and propagates the full Phase-7.1 field family, including `obs_w_formula_version`.

# Phase 1 - Decouple Prior from Observation and Fix File Ordering (2026-05-26)

## Files touched and rationale

- `acoustic_density_core.py`  
  Added explicit Phase 1 changelog note, introduced pure observation outputs (`pure_observation_w_h`, `pure_observation_w_i`, `pure_observation_w_s`), preserved legacy prior-smoothed outputs (`smoothed_w_h_legacy`, `smoothed_w_i_legacy`, `smoothed_w_s_legacy`), and changed canonical compatibility aliases (`harmonic_density_weight`, `inharmonic_density_weight`, `subbass_density_weight`) to expose pure observation. Replaced hard-coded `0.55/0.45` with named deprecated constants for traceability and auditability of prior-contaminated behavior.

- `pipeline_orchestrator_gui.py`  
  Added deterministic Phase 1 file ordering utility (`build_phase1_file_iteration_order`) that sorts by parsed note f0 via `canonical_note_from_filename` + `librosa.note_to_hz`, with unparseable names sorted last by filename. Added orchestrator entry-point parameter `enable_adaptive_path_randomization: bool = False` and deterministic seed logging, with default behavior remaining sorted-by-f0. Updated adaptive feedback extraction to prioritize pure observation fields and ensured adaptive engine updates consume pure observations.

- `adaptive_density_engine.py`  
  Added explicit `update()` docstring assertion that `observation` must be pure data ratio input (not prior-mixed), clarifying methodological contract between Stage 1 evidence and online Bayesian-style update.

- `tests/phase_1/conftest.py`  
  Added test bootstrap path setup so Phase 1 tests import project modules consistently.

- `tests/phase_1/test_no_prior_contamination.py`  
  Added regression test proving note-level pure observation output is invariant to strongly different priors for identical spectral evidence.

- `tests/phase_1/test_deterministic_ordering.py`  
  Added regression test proving Phase 1 folder iteration order is monotonic in nominal f0 and deterministic for unparseable note tokens.

## Acoustic / methodological justification

- Observation and prior should be separated in online learning pipelines: the likelihood term should reflect current data, while prior influence should be applied in the posterior update step. Mixing prior into the observation channel causes biased updates and can over-propagate early-run conditions across later notes.
- Deterministic f0-ordered traversal improves reproducibility and interpretability of adaptive trajectories in per-note spectral pipelines; optional seeded randomization provides controlled robustness checks without changing default publication behavior.

## References (APA)

- Bottou, L. (2010). Large-scale machine learning with stochastic gradient descent. In Y. Lechevallier & G. Saporta (Eds.), *Proceedings of COMPSTAT'2010* (pp. 177-186). Springer. https://doi.org/10.1007/978-3-7908-2604-3_16
- Bishop, C. M. (2006). *Pattern recognition and machine learning*. Springer.

# Phase 2 - Unify Sub-Bass Semantics and Fix Phase-2 Application Path (2026-05-26)

## Files touched and rationale

- `subbass_policy.py`  
  Added canonical `SubBassPolicy.upper_bound_hz(f0_hz, sr_hz, n_fft)` implementing `min(f0_hz * 0.5, 80.0)` as the single operational sub-bass definition.

- `constants.py`  
  Kept legacy constant compatibility and added deprecated shim `deprecated_subbass_aggregate_cutoff_hz(...)` that routes to `SubBassPolicy` and emits one deprecation warning per process.

- `acoustic_density_core.py`  
  Replaced operational use of legacy `subbass_upper_ratio` with `SubBassPolicy` resolution while retaining a deprecated ratio shim (`deprecated_subbass_upper_bound_hz_from_ratio`) for backward compatibility and testability.

- `low_frequency_policy.py`  
  Kept `calculate_adaptive_subfundamental_cutoff_hz(...)` as a deprecated compatibility shim with one-time warning, internally mapped to `SubBassPolicy` so legacy callers converge on the same cutoff value.

- `proc_audio.py`  
  Replaced all operational sub-bass fallback call sites that used fixed aggregate constants or legacy low-frequency cutoff routine with unified `SubBassPolicy` via `_current_subbass_upper_bound_hz()`.

- `run_real_corpus_validation.py`  
  Updated validation-side cutoff derivation to use `SubBassPolicy`, removing direct dependency on legacy adaptive cutoff computation.

- `pipeline_orchestrator_gui.py`  
  Fixed Phase-2 application path by forwarding `subbass_weight` in Stage-2 `compile_kw` so discovered profile triplets are fully transmitted.

- `compile_metrics.py`  
  Extended `compile_density_metrics_with_pca` and `_compile_density_metrics_impl` with `subbass_weight: float = None` behavior. Updated weighted-density computation so explicit corpus profile (`harmonic_weight`, `inharmonic_weight`, `subbass_weight`) is actually applied when all three are provided; added `density_weights_source` and invariant comparator `density_metric_raw_per_note_balance`.

- `tests/phase_2/conftest.py`  
  Added Phase-2 test import bootstrap.

- `tests/phase_2/test_subbass_policy_single_source.py`  
  Added regression test ensuring legacy entry points resolve to the same sub-bass upper bound for identical `(f0, sr, n_fft)`.

- `tests/phase_2/test_phase2_profile_actually_applied.py`  
  Added regression test ensuring Phase-2 fixed corpus profile is truly applied to `density_metric_raw`, while `density_metric_raw_per_note_balance` remains per-note.

## Acoustic / methodological justification

- A single sub-bass boundary definition prevents semantic drift between Stage-1 extraction, low-frequency guards, and Stage-2 compilation. This improves reproducibility and interpretability of low-frequency component accounting.
- Explicitly surfacing both corpus-profile and per-note-balance raw density scores removes ambiguity about which weighting regime generated a result, preventing silent methodological mismatch in downstream analysis.

## References (APA)

- Zwicker, E., & Fastl, H. (1990). *Psychoacoustics: Facts and models*. Springer.

# Phase 7 - Register-Invariant Strength Formula (2026-05-26)

## Files touched and rationale

- `acoustic_density_core.py`  
  Replaced the Phase-6/v55 incommensurate strength blend (harmonic-order count + residual log-bin count + sub-bass particle count with fixed scalar 0.25) with a register-invariant occupancy-ratio formulation. Added `_expected_residual_bin_count(...)`, denominator guards with `qc_status` append semantics (`register_normalization_denominator_zero_*`), and explicit deprecated exports for the prior v55 strengths:
  `legacy_component_strength_h_v55`, `legacy_component_strength_i_v55`, `legacy_component_strength_s_v55`.  
  Canonical `pure_observation_w_{h,i,s}` now expose the new register-normalized data ratio; `smoothed_w_*_legacy` remain prior-mixed legacy compatibility fields built on top of the new data ratio.

- `constants.py`  
  Added Phase-7 neutral symmetry constants:
  `STRENGTH_OCCUPANCY_WEIGHT_HARMONIC = 1.0`,  
  `STRENGTH_OCCUPANCY_WEIGHT_INHARMONIC = 1.0`,  
  `STRENGTH_OCCUPANCY_WEIGHT_SUBBASS = 1.0`,  
  each documented as Phase-7 equal-weight occupancy defaults. Added the three constants to `_PROVENANCE_SOURCED_CONSTANTS`.

- `compile_metrics.py`  
  Extended compiled `Density_Metrics` allow-lists to carry inharmonicity fit outputs:  
  `inharmonicity_coefficient_B`, `inharmonicity_fit_residual_std_cents`, `inharmonicity_fit_status`, `inharmonicity_fit_method`.  
  Updated per-note extraction to ingest these values from per-note `Metrics` when available and to fall back to the per-note `Inharmonicity_Fit` sheet (first row) otherwise.

- `tests/phase_7/conftest.py`  
  Added phase bootstrap import path setup.

- `tests/phase_7/test_register_invariant_on_synthetic_odd_harmonic.py`  
  Added low/high-register odd-harmonic clarinet-like synthetic regression for harmonic-majority observation constraints.

- `tests/phase_7/test_register_invariance_across_f0.py`  
  Added cross-register invariance regression (`f0` sweep) for `pure_observation_w_h`.

- `tests/phase_7/test_strength_formula_units_match.py`  
  Added dimensionless-scale regression for Phase-7 strength terms (`component_strength_*`) under near-uniform occupancy scenarios.

- `tests/phase_7/test_inharmonicity_columns_in_compiled.py`  
  Added compiled-workbook regression ensuring inharmonicity fit columns propagate into compiled `Density_Metrics`.

- `tests/phase_7/test_clarinet_corpus_wh_is_majority.py`  
  Added corpus-gated clarinet adaptive-profile sanity test (`profile_h >= 0.50`) using `CLARINET_SUSTAINS_DIR`.

- `docs/parameter_provenance.md` and `tools/generate_parameter_provenance.py`  
  Updated provenance ledger generation and entries for the three Phase-7 occupancy symmetry constants.

## Acoustic / methodological justification

- The previous v55 strength formula combined unlike counting alphabets (harmonic order slots vs 100-cent residual bins vs sub-bass particle slots) without normalizing by each alphabet’s available capacity. As f0 rises, this causes systematic register drift independent of actual spectral balance.  
- Register-invariant occupancy normalization enforces commensurate comparison across H/I/S by dividing each density/count term by the number of available slots in that band before combination.  
- Equal occupancy weights (1.0, 1.0, 1.0) are the neutral symmetry point; non-equal settings encode deliberate prior preference and must be explicitly documented.

## References (APA)

- Backus, J. (1974). *The acoustical foundations of music* (2nd ed.). W. W. Norton.
- Benade, A. H. (1976). *Fundamentals of musical acoustics* (2nd ed.). Oxford University Press.
- Cogan, R. (1984). *New images of musical sound*. Harvard University Press.
- Dickens, P., Smith, J., & Wolfe, J. (2007). Improved precision of resonance frequency measurements in musical wind instruments. *The Journal of the Acoustical Society of America, 121*(4), 2020-2026.
- Fletcher, N. H., & Rossing, T. D. (1998). *The physics of musical instruments* (2nd ed.). Springer.
- Bottou, L. (2010). Large-scale machine learning with stochastic gradient descent. In Y. Lechevallier & G. Saporta (Eds.), *Proceedings of COMPSTAT'2010* (pp. 177-186). Springer. https://doi.org/10.1007/978-3-7908-2604-3_16

# Phase 3 - Normalise Amplitudes Across FFT Tiers; Repair Diagnostic Alias (2026-05-26)

## Files touched and rationale

- `spectral_normalization.py`  
  Added canonical FFT-tier normalization helper `n_fft_normalization_factor(n_fft, n_fft_reference=8192, kind=...)` with amplitude (`sqrt(N_ref/N)`) and power (`N_ref/N`) modes.

- `compile_metrics.py`  
  Added `_tier_normalized` companions for cross-note absolute sums in the compiled path:
  `harmonic_amplitude_sum`, `inharmonic_amplitude_sum`, `subbass_amplitude_sum`,
  `harmonic_energy_sum`, `inharmonic_energy_sum`, `subbass_energy_sum`.  
  Added `tier_consistency_status` with explicit row status values including
  `all_tiers_normalised`.  
  Added these normalization/status columns to canonical sheet column sets so exported
  rows expose both raw and normalized forms.

- `acoustic_density_core.py`  
  Replaced mixed-unit diagnostic alias terms with coherent participation-ratio terms:
  `D_H`, `D_R`, `D_S` now all use inverse-Herfindahl (`_effective_count`) over
  harmonic/residual/subbass power arrays, respectively.  
  Added explicit diagnostic term fields:
  `diagnostic_effective_components_h`, `diagnostic_effective_components_r`,
  `diagnostic_effective_components_s`.  
  Added canonical diagnostic output
  `effective_components_weighted_diagnostic` and kept
  `energy_weighted_component_density_diagnostic` as deprecated alias.

- `tests/phase_3/conftest.py`  
  Added Phase-3 test import bootstrap.

- `tests/phase_3/test_tier_normalisation_invariance.py`  
  Added regression test with a synthetic sustained sinusoid analyzed at `n_fft=4096`
  and `n_fft=8192`, asserting tier-normalized agreement within 2%.

- `tests/phase_3/test_diagnostic_unit_coherence.py`  
  Added regression test validating finite, non-negative float outputs for each
  effective-component term and the combined weighted diagnostic.

## Acoustic / methodological justification

- FFT-size changes alter absolute spectral sums in ways that confound cross-note
  comparisons unless a reference normalization is explicitly applied.
- Participation-ratio style diagnostics must combine unit-coherent terms; mixing
  effective-density quantities with integer count surrogates leads to inconsistent
  interpretation and unstable cross-note ranking.

## References (APA)

- Cogan, R. (1984). *New images of musical sound*. Harvard University Press.
- Edwards, J. T., & Thouless, D. J. (1972). Numerical studies of localization in disordered systems. *Journal of Physics C: Solid State Physics, 5*(8), 807-820. https://doi.org/10.1088/0022-3719/5/8/007

# Phase 4 - Parameterise Inharmonicity Instead of Merely Gating It (2026-05-26)

## Files touched and rationale

- `inharmonicity_model.py`  
  Added `fit_inharmonicity_coefficient(...)` with least-squares estimation of stiff-string inharmonicity coefficient `B` in `f_n = n*f0*sqrt(1 + B*n^2)`, including fit status, residual spread, and predicted stretched harmonic grid.

- `constants.py`  
  Added dedicated inharmonicity / adaptive-harmonic-tolerance constants and policy documentation, including references for FFT-bin-aware tolerance floor.

- `acoustic_density_core.py`  
  Integrated inharmonicity fit before harmonic-mask construction.  
  When fit succeeds and `B > 1e-5`, harmonic prediction uses stretched partials; otherwise behavior remains mathematically equivalent to the legacy gate (`B=0` path).  
  Added adaptive per-partial tolerance:
  `max(harmonic_tolerance_cents, 1200 * bin_spacing_hz / (n * f0_hz))`.  
  Exported inharmonicity fit fields and status into descriptor output.

- `proc_audio.py`  
  Added export of inharmonicity fit payload as new workbook sheet `Inharmonicity_Fit` (coefficient, residual, status, method, and stretched predicted frequencies by order).

- `tests/phase_4/conftest.py`  
  Added Phase-4 test import bootstrap.

- `tests/phase_4/test_inharmonicity_zero_for_pure_harmonic.py`  
  Added regression test asserting near-zero `B` for exact harmonic synthetic spectrum.

- `tests/phase_4/test_inharmonicity_recovers_known_B.py`  
  Added regression test for synthetic stiff-string spectrum with known `B=1e-4` and ±20% recovery tolerance.

- `tests/phase_4/test_clarinet_corpus_B_is_small.py`  
  Added clarinet corpus sanity test (`mean B < 1e-5`) gated by `CLARINET_SUSTAINS_DIR` environment variable for environments where corpus audio is available.

## Acoustic / methodological justification

- A fixed ±35-cent harmonic gate can incorrectly label stretched stiff-string partials as inharmonic noise at higher orders.  
- Explicit `B` estimation provides a physically grounded correction that preserves harmonic classification under known inharmonic instruments while remaining backward-compatible for acoustically harmonic cases (`B≈0`).  
- Adaptive tolerance floor tied to FFT-bin spacing prevents deterministic spectral quantization error from being treated as structural inharmonicity.

## References (APA)

- Fletcher, H. (1962). *The physics of musical instruments*. Dover.
- Fletcher, H., Blackham, E. D., & Stratton, R. (1962). Quality of piano tones. *The Journal of the Acoustical Society of America, 34*(6), 749-761.
- Galembo, A., & Askenfelt, A. (1994). Signal representation and estimation of spectral parameters by inharmonic comb filtering. *IEEE Transactions on Speech and Audio Processing, 2*(2), 197-203.
- Järveläinen, H., Karjalainen, M., & Tolonen, T. (2001). Computationally efficient analysis of beating and inharmonicity in musical tones. *Journal of the Audio Engineering Society, 49*(7/8), 695-708.
- McAulay, R. J., & Quatieri, T. F. (1986). Speech analysis/synthesis based on a sinusoidal representation. *IEEE Transactions on Acoustics, Speech, and Signal Processing, 34*(4), 744-754.
- Serra, X., & Smith, J. O. (1990). Spectral modeling synthesis: A sound analysis/synthesis system based on a deterministic plus stochastic decomposition. *Computer Music Journal, 14*(4), 12-24.
- Fletcher, N. H., & Rossing, T. D. (1998). *The physics of musical instruments* (2nd ed.). Springer.

# Phase 5 - Extended Timbral Descriptors and Temporal Segmentation (2026-05-26)

## Files touched and rationale

- `mir_descriptors.py`  
  Added Phase-5 MIR descriptor engine covering spectral moments, irregularity, tristimulus family, flatness, rolloff (85/95), Aures roughness, and ERB-weighted spectral density.

- `temporal_segmentation.py`  
  Added envelope-follower segmentation (`attack`, `sustain`, `release`) with MPEG-7 style log-attack-time output.

- `proc_audio.py`  
  Integrated descriptor extraction into per-note export workflow; added whole-note descriptor fields plus segmented variants (`_on_attack`, `_on_sustain`, `_on_release`) and sustain-focused aliases (`_on_sustain_segment`).  
  Exported segmented density component columns and `log_attack_time_s` into `Metrics`.

- `compile_metrics.py`  
  Extended compiled-sheet allowlists to include Phase-5 descriptor columns and segmented columns so they propagate into `compiled_density_metrics.xlsx`.  
  Updated direct per-note extractor to ingest these columns from per-note `Metrics` and carry them into compiled rows.

- `metrics_dictionary.json`  
  Added citation-backed entries for all new Phase-5 descriptors.

- `tests/phase_5/conftest.py`  
  Added Phase-5 test bootstrap.

- `tests/phase_5/test_descriptor_ranges.py`  
  Added regression test asserting valid descriptor-domain ranges on synthetic spectra.

- `tests/phase_5/test_segmentation_on_pluck_synth.py`  
  Added regression test asserting pluck segmentation behavior (`attack < 50 ms`, sustain dominant).

## Acoustic / methodological justification

- MPEG-7/Timbre-Toolbox-compatible descriptors improve external comparability across studies and instrument families.  
- Attack/sustain/release decomposition prevents sustained-reed assumptions from being baked into descriptors when analyzing percussive/plucked instruments with attack-dominant timbre.

## References (APA)

- Aures, W. (1985). Ein Berechnungsverfahren der Rauhigkeit. *Acustica, 58*(5), 268-281.
- Krimphoff, J., McAdams, S., & Winsberg, S. (1994). Caractérisation du timbre des sons complexes. II. Analyses acoustiques et quantification psychophysique. *Journal de Physique IV*, 4(C5), 625-628.
- Moore, B. C. J., & Glasberg, B. R. (1983). Suggested formulae for calculating auditory-filter bandwidths and excitation patterns. *The Journal of the Acoustical Society of America, 74*(3), 750-753.
- Peeters, G. (2004). *A large set of audio features for sound description (similarity and classification) in the CUIDADO project*. IRCAM.
- Peeters, G., Giordano, B., Susini, P., Misdariis, N., & McAdams, S. (2011). The Timbre Toolbox: Extracting audio descriptors from musical signals. *The Journal of the Acoustical Society of America, 130*(5), 2902-2916.
- Pollard, H. F., & Jansson, E. V. (1982). A tristimulus method for the specification of musical timbre. *Acta Acustica united with Acustica, 51*(3), 162-171.

# Phase 6 - Document Magic Numbers; Final Consolidation (2026-05-26)

## Files touched and rationale

- `docs/parameter_provenance.md`  
  Added a generated provenance ledger that enumerates all numeric constants in `constants.py` and all numeric defaults in function signatures for modules touched in Phases 1-5. Each entry now records canonical name, current value, one-line acoustic meaning, source status, qualitative stability range, and an anchoring test file.

- `constants.py`  
  Added a one-time import warning (`RuntimeWarning`) that lists numeric constants lacking bibliographic provenance and marks them explicitly as `TODO: bibliographic justification required`, fulfilling traceability requirements without silently changing analytical behavior.

- `density.py`  
  Kept `aggregate_subbass_noise_peak_power` because live imports still exist; hardened it into an explicit deprecation wrapper (one-time `DeprecationWarning`) with backward-compatible argument mapping to `aggregate_low_frequency_residual_peak_power`.

- `compile_metrics.py`  
  Added strict alias partitioning (`_split_strict_alias_columns`) and wrote strict aliases to a dedicated `Legacy_Aliases` sheet, while keeping the primary metrics sheet narrower and canonical for downstream analyses.

- `tests/phase_6/conftest.py`  
  Added import bootstrap for Phase 6 tests.

- `tests/phase_6/test_parameter_provenance_doc.py`  
  Added regression test asserting that the parameter provenance document exists and exposes required ledger fields.

- `tests/phase_6/test_legacy_aliases_sheet_split.py`  
  Added regression test proving strict aliases move to `Legacy_Aliases` and are excluded from the primary metrics sheet.

- `tests/phase_6/test_density_wrapper_deprecation.py`  
  Added regression test proving legacy sub-bass wrapper still works but emits `DeprecationWarning`.

- `tests/phase_6/test_density_order_invariance.py`  
  Added regression test showing `density_metric_raw` values are permutation-invariant under row reordering.

- `tests/phase_6/test_subbass_observation_cap.py`  
  Added regression test verifying low sub-bass observation weight (`pure_observation_w_s < 0.05`) for a harmonic-like synthetic note.

- `tools/generate_parameter_provenance.py`  
  Added utility script to regenerate `docs/parameter_provenance.md` deterministically from AST-level extraction of constants/defaults.

## Migration guide for downstream analyses (Phases 1-6)

- **Phase 1**  
  Treat `pure_observation_w_h|w_i|w_s` as canonical observation weights. Legacy blended fields are explicitly labeled legacy/deprecated and should not be used for adaptive updates.

- **Phase 2**  
  Sub-bass semantics are unified under `SubBassPolicy.upper_bound_hz`. In compiled outputs, interpret `density_weights_source` to distinguish explicit corpus profile application (`phase2_corpus_profile`) from per-note weighting. Use `density_metric_raw_per_note_balance` for per-note-only comparators.

- **Phase 3**  
  Cross-note absolute sums should use `_tier_normalized` columns for FFT-size comparability. `effective_components_weighted_diagnostic` is the coherent diagnostic; `energy_weighted_component_density_diagnostic` remains as deprecated alias only.

- **Phase 4**  
  Consume inharmonicity fields (`inharmonicity_coefficient_B`, fit status/residual/method) for harmonicity diagnostics. Clarinet-like harmonic corpora should remain near `B≈0`; stretched instruments are now handled physically rather than by fixed gate alone.

- **Phase 5**  
  New MIR and temporal descriptors are available as whole-note and segmented forms. Segment suffixes (`_on_attack`, `_on_sustain`, `_on_release`, `_on_sustain_segment`) are semantically distinct and should not be collapsed without explicit modeling intent.

- **Phase 6**  
  Strict aliases have moved to the `Legacy_Aliases` sheet; primary analysis should use canonical fields from `Density_Metrics` / `Canonical_Metrics`. Treat import-time provenance warnings as a signal to prioritize bibliographic completion before publication.

## References (APA)

- Fletcher, N. H., & Rossing, T. D. (1998). *The physics of musical instruments* (2nd ed.). Springer.
- Galembo, A., & Askenfelt, A. (1994). Signal representation and estimation of spectral parameters by inharmonic comb filtering. *IEEE Transactions on Speech and Audio Processing, 2*(2), 197-203.
- Järveläinen, H., Karjalainen, M., & Tolonen, T. (2001). Computationally efficient analysis of beating and inharmonicity in musical tones. *Journal of the Audio Engineering Society, 49*(7/8), 695-708.
- McAulay, R. J., & Quatieri, T. F. (1986). Speech analysis/synthesis based on a sinusoidal representation. *IEEE Transactions on Acoustics, Speech, and Signal Processing, 34*(4), 744-754.
- Moore, B. C. J. (2012). *An introduction to the psychology of hearing* (6th ed.). Brill.
- Zwicker, E., & Fastl, H. (1990). *Psychoacoustics: Facts and models*. Springer.

# Phase 34

Tests live in `tests/phase_34/`.
