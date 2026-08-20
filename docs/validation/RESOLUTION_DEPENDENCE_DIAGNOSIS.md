# Resolution dependence of EWSD at adaptive-FFT tier boundaries

Evidence: IOWA tenor trombone *ff* SustainStable, commit `5b1a1c7`.
Stage 1–3 rerun with `window=blackmanharris`, `zero_padding=2`, `hop = n_fft/8`.
Raw JSON: `docs/validation/_d61_raw/diagnosis.json` (local; not a CI artefact).

## D6.1.1 — The step follows the window, not the note

Observed corpus step G3 → G♯3 (`5b1a1c7` adaptive tiers): EWSD 91.6 → 66.3.

| Note | n_fft / hop | EWSD_acoustic | core_H_ratio | D_H | D_S |
|------|-------------|--------------:|-------------:|----:|----:|
| G3 (native) | 8192 / 1024 | 91.64 | 0.979 | 2.973 | 0.630 |
| G3 (swap) | 4096 / 512 | 71.13 | 0.919 | 2.670 | 0.335 |
| G♯3 (native) | 4096 / 512 | 66.31 | 0.905 | 2.626 | 0.370 |
| G♯3 (swap) | 8192 / 1024 | 82.76 | 0.970 | 2.874 | 0.691 |

G3 at 4096 moves toward the G♯3-native numbers; G♯3 at 8192 moves toward the G3-native numbers. Acceptance: the step follows the window.

## D6.1.2 — G3 n_fft sweep (hop = n_fft/8)

| n_fft | EWSD_acoustic | core_H_ratio | D_H | D_S | H energy ΣA² | S rows | Complete bins |
|------:|--------------:|-------------:|----:|----:|-------------:|-------:|--------------:|
| 2048 | 50.80 | 0.794 | 2.367 | 0.192 | 2572 | 8 | 2048 |
| 4096 | 71.13 | 0.919 | 2.670 | 0.335 | 10592 | 23 | 4096 |
| 8192 | 91.64 | 0.979 | 2.973 | 0.630 | 45067 | 53 | 8192 |
| 16384 | 118.46 | 0.995 | 3.273 | 1.075 | 190280 | 113 | 16384 |

Harmonic *slot* count stays 103. Peak energy ΣA² scales as N² (coherent gain). Sub-bass *row* count and D_S scale with bin count. EPD was not on the compiled Density_Metrics sheet in this extraction path; the review workbook still showed EPD flat across the G3/G♯3 boundary.

## Terms that scale with bin count

- Residual / sub-bass energy and D_S: more bins above the floor at larger N.
- Peak ΣA²: coherent gain (N²), not a physical energy.
- `core_harmonic_energy_ratio` and EWSD move because r_k and D_k both change.
- Partial-only EPD does not use residual bins.

## Fix (this PR)

Energy sums use Heinzel PSD `S(f) = |X|² / (f_s Σw²)` integrated over Hz; peak energy is `|X|² / (Σw)²`. Residual excludes the window ENBW footprint. D_k amplitudes are n_fft-normalised to `FIXED_N_FFT_DEFAULT` (8192). `fft_policy=fixed` is the default for comparable corpora.

## D6.5.3 — Body-stop order after the PSD fix

Pre-fix `harmonic_body_stop_order` on trombone *ff* jumped across adjacent notes (32 at C3, 80 at A♯2, 85 at F♯2). That diagnostic is a CFAR/body-stop order, not an energy sum.

Four-note re-export after D6.2 (`fft_policy=fixed`, 8192/1024):

| Note | harmonic_body_stop_order | validated_above_stop |
|------|-------------------------:|---------------------:|
| G3 | 71 | 0 |
| G♯3 | 52 | 0 |
| B4 | 20 | 0 |
| C5 | 21 | 1 |

The stop does **not** stabilise. Follow-up: per-note stop diagnostics (`harmonic_body_stop_order`, `accepted_slots_above_body_stop`, `included_above_body_stop_count`).

## D6.6 — Four-note trombone *ff* after the fix

`fft_policy=fixed` (all 8192/1024) vs `adaptive_tier` (G3 8192, G♯3/B4 4096, C5 2048).

| Note | EWSD fixed | EWSD adaptive | D_H fixed | D_H adaptive |
|------|----------:|--------------:|----------:|-------------:|
| G3 | 91.46 | 91.46 | 2.973 | 2.973 |
| G♯3 | 79.51 | 63.88 | 2.874 | 2.926 |
| B4 | 24.26 | 18.46 | 2.650 | 2.652 |
| C5 | 22.59 | 13.09 | 2.630 | 2.653 |

Within **fixed**, G3→G♯3 EWSD steps 13 % but EPD also steps 12 % (musical, not a window artefact). B4→C5 EWSD steps 6.9 %. `compare_runs` boundary guard passes. Fixed vs adaptive still disagrees on EWSD / `core_H` / D_S at 4096 and 2048 (`pair_fail`); D_H agrees within 2 %. Use `fft_policy=fixed` for cross-note comparison. Full 33-note artefact is the same command on `_Sustains_Stable`.

## WP1 — Residual exclusion footprint (post-fix)

Peak power still uses ENBW. Residual exclusion uses the window main-lobe
(`RESIDUAL_EXCLUSION_FOOTPRINT` = 8 bins for Blackman–Harris 4-term).
One-sided invariant: `residual_region_hz_total + excluded_region_hz_total
== analysis_band_hz`.

Descriptor-level G3 / G♯3 swap on the same IOWA trombone *ff* takes
(`window=blackmanharris`, hop = n_fft/8, `freq` 20–20 000 Hz).
**Artefact (corrected R1b):** this table is `compute_acoustic_density_descriptors`
/ `analysis_band_regions_hz` on a peak-table extraction (`tests/phase_25`
family), **not** compiled Stage-3 `core_harmonic_energy_ratio`. The
0.9969 / 0.9993 pair (0.24 % step) is that descriptor
`harmonic_energy_ratio`. It must not be read as the export. R1 Stage-3
G3 `core_H` is 0.9222 @8192 vs 0.7878 @4096 (14.6 %). Census-held
discrete Power_raw on the same files is 0.9910 / 0.9675 (see § R1b).

| Note | n_fft / hop | descriptor `harmonic_energy_ratio` | residual_ratio | residual_hz | excluded_hz |
|------|-------------|-----------------------------------:|---------------:|------------:|------------:|
| G3 | 8192 / 1024 | 0.9969 | 0.0031 | 15 597 | 4 383 |
| G3 | 4096 / 512 | 0.9993 | 0.0007 | 11 220 | 8 760 |
| G♯3 | 4096 / 512 | 0.9963 | 0.0037 | 11 711 | 8 269 |
| G♯3 | 8192 / 1024 | 0.9898 | 0.0102 | 15 846 | 4 134 |

Descriptor G3 steps 0.24 % when the window halves; G♯3 steps 0.65 %.
That descriptor residual share is < 1.1 % (was 5–25 % and monotone in
bin width). `residual_region_hz_total` is ≤ 19 980 Hz (was 36 364 Hz
on a 20 kHz band). The Hz-region invariant is what WP1 closed. It is
**not** Stage-3 energy-partition invariance.

## P1 — Live G3 swap on `aa24de8` (20 August 2026) — **FAIL**

Re-run from audio on the post-WP6 tree (`aa24de8`, `git describe`
`v4.2.0-2-gaa24de8`). Command (runbook flags):

```bash
python -m tools.p1_g3_swap --out docs/validation/_p1_g3_swap
```

which invokes `run_orchestrator.py` Stage 1–3 with `--fft-policy fixed`,
`window` default, φ=`log`, twice:

| Window | n_fft / hop |
|--------|-------------|
| production | 8192 / 1024 |
| swap | 4096 / 512 |

Audio: `D:\METAIS\TROMBONE\IOWA_Trombone - Test\TenorTrombone\IOWA_Trombone_ff\_Sustains_Stable\IOWA_Trb.T_ff.G3_SustainStable.aif`  
SHA-256: `91dbf93da5082954145669c2cf7819bbcdc1eb0bf94a08bd982331c42ca9d20a`  
Profile id (both runs): `wf=log|dst=-90.0|ceil=20000.0|fft=fixed|seg=sustain_primary_stable_diagnostic|elig=1`  
Manifest: `_p1_g3_swap/g3_8192/run_manifest.json` and `g3_4096/run_manifest.json`.  
Raw table: `_p1_g3_swap/p1_g3_swap.json` (local; not committed).

| n_fft / hop | `core_harmonic_energy_ratio` | `core_residual_energy_ratio` | `harmonic_density_sum` | `EWSD_score_acoustic_balanced` |
|-------------|-----------------------------:|-----------------------------:|-----------------------:|-------------------------------:|
| 8192 / 1024 | 0.9222 | 0.0778 | 2.973 | 91.31 |
| 4096 / 512 | 0.7878 | 0.2122 | 2.971 | 72.72 |

`core_H` relative Δ = **14.6 %**. 3 % tolerance: **FAIL**.

`harmonic_density_sum` is stable (2.973 vs 2.971). The jump is in the
**exported energy partition** (`core_*_energy_ratio`) and in EWSD
(91.31 → 72.72), the same window-following pattern as D6.1.1
(91.64 → 71.13 on `5b1a1c7`).

The WP1 table immediately above (0.9969 vs 0.9993, residual &lt; 1.1 %)
is **stale relative to the compiled/research export**. That table is
consistent with a descriptor-level *region* / synthetic extraction
(`tests/phase_25` sinusoid residual &lt; 1 % still holds). It is **not**
the live Stage 1–3 `core_harmonic_energy_ratio` on this G3 take under
`aa24de8`. The backlog entry that the live 3 % test is red is the
correct description of the **export** path.

**Hypothesis.** WP1 separated residual *exclusion width* (main-lobe vs
ENBW) and closed the Hz-region invariant. Live *energy* in
`core_residual_energy_ratio` still grows when the hop/window halves
(more independent residual bins above the floor). Synthetic planted
peaks do not exercise that path. Production policy (`fft_policy=fixed`
at 8192/1024) avoids mixing the two windows; it does not make the
swap invariant.

This dated run is the single source for the backlog and the WP1 status
row. P5/P6 re-exports are **stopped** until this export-level
invariance is resolved.

## R1 — Stage-3 B1 on `v4.2.2` (20 August 2026) — **FAIL**

Clean head `64a2282`, annotated tag `v4.2.2` (does not move `v4.2.0` or
`v4.2.1`). The evaluation B1 cell on `4799ea0` used Stage-1 in-memory
diagnostic EWSD. This run uses the full Stage 1–3 export and reads only
`compiled_density_metrics_research.xlsx` / `Spectral_Density_Metrics`.

```bash
python -m tools.r1_stage3_b1 --out docs/validation/_r1_stage3_b1
```

`--fft-policy fixed`, hop = n_fft/8, φ=`log`. Raw table:
`_r1_stage3_b1/r1_stage3_b1.json` (local; not committed).

The dirty tree during the original evaluation (`4799ea0`, later
`88489ff` / PR #85) was the evaluation runner and report, the
`Optional` import in `generate.py`, extra recover-dict keys, and
`.gitignore` for `_measurement_eval/`. None of those files change
F-042 / F-047 / F-048 / F-049 algebra. This R1 run used tagged
`64a2282` for the orchestrator; uncommitted files were only the R1
harness.

| Signal | n_fft / hop | `core_harmonic_energy_ratio` | `EWSD_score_acoustic_balanced` | `effective_partial_density` |
|--------|-------------|-----------------------------:|-------------------------------:|----------------------------:|
| G3 (SHA-256 `91dbf93d…d20a`) | 4096 / 512 | 0.7878 | 72.72 | 10.513 |
| G3 | 8192 / 1024 | 0.9222 | 91.31 | 10.065 |
| G3 | 16384 / 2048 | 0.9760 | 118.04 | 9.516 |
| flute A♯4 (`9027c836…d790`) | 4096 / 512 | 0.8388 | 13.71 | 2.861 |
| flute A♯4 | 8192 / 1024 | 0.9685 | 18.00 | 2.926 |
| flute A♯4 | 16384 / 2048 | 0.9932 | 23.34 | 2.983 |
| synthetic A3 8-partial | 4096 / 512 | not on Stage-3 EWSD/EPD columns | — | — |
| synthetic A3 8-partial | 8192 / 1024 | `core_H` = 1.0 on the sheet; EWSD and `effective_partial_density` columns absent (`Stage3_Diagnostics` EWSD is NaN; `note_effective_component_density` = 1.160) | — | — |
| synthetic A3 8-partial | 16384 / 2048 | same missing Stage-3 EWSD/EPD columns | — | — |

3 % vs the 8192 reference: **FAIL** on G3 (core_H Δ 14.6 % at 4096;
EWSD Δ 20.4 % / 29.3 % at 4096 / 16384; EPD Δ 4.5 % / 5.5 %). **FAIL**
on flute A♯4 (core_H Δ 13.4 % at 4096; EWSD Δ 23.8 % / 29.7 %). Flute
EPD stays inside 3 %. Synthetic cannot be scored on the required
Stage-3 columns.

G3 8192/4096 matches the P1 table on `aa24de8` to the reported
rounding (0.9222 / 0.7878, 91.31 / 72.72). The canonical Stage-3 path
is **not** resolution-invariant across n_fft. R1b re-scopes that
result: detection is resolution-dependent in principle; WP1 acceptance
is energy-accounting invariance at a declared window plus
`fft_policy=fixed`.

**Synthetic Stage-3 NaN.** The 1.2 s tone has
`ci_basis_frame_count = 2.5625` and `ci_basis_frames_insufficient =
True` (`MIN_INDEPENDENT_FRAMES = 8`). `ewsd_merge_status =
note_not_in_ewsd_output`; `EWSD_score_acoustic_balanced` is NaN on
`Stage3_Diagnostics`. That is the eligibility / frame-count gate, not
a missing formula.

## R1b — Census-held G3 (20 August 2026)

Frozen list: the 71 `include_for_density` harmonic *orders* from the
R1 `g3_8192` Stage-1 workbook. At 4096 and 16384 the same orders are
taken from that window's Harmonic Spectrum (slots exist; 4096 marks
68–71 `include_for_density=False`). I/S energy is the native
Inharmonic + Sub-bass `Power_raw` at that window. EWSD_held is
`compute_ewsd` with those H rows and HIS weights from the held
partition. Native columns are R1 Stage-3 compiled values.

```bash
python -m tools.r1b_census_held
```

Raw: `docs/validation/_r1_stage3_b1/r1b_census_held.json` (local).

| n_fft / hop | N_validated native | held N | held core_H (Power_raw) | native Stage-3 core_H | held EWSD | native Stage-3 EWSD |
|-------------|-------------------:|-------:|------------------------:|----------------------:|----------:|--------------------:|
| 4096 / 512 | 67 | 71 | 0.9675 | 0.7878 | 70.65 | 72.72 |
| 8192 / 1024 | 71 | 71 | 0.9910 | 0.9222 | 91.69 | 91.31 |
| 16384 / 2048 | 73 | 71 | 0.9970 | 0.9760 | 119.44 | 118.04 |

Relative Δ vs 8192:

| Quantity | 4096 | 16384 |
|----------|-----:|------:|
| Native Stage-3 core_H | 14.57 % | 5.83 % |
| Held Power_raw core_H | 2.37 % | 0.60 % |
| Native Stage-3 EWSD | 20.36 % | 29.27 % |
| Held EWSD | 22.94 % | 30.27 % |

**Attribution.** Native validated counts are 67 / 71 / 73. The four
orders present only at 8192 (68–71) have `Power_raw` ≈ 0.11 against
E_H ≈ 45 067 at 8192 (~2×10⁻⁴ % of E_H) — not a 14 % core_H effect.

| Failure piece | 4096 vs 8192 | 16384 vs 8192 | Verdict |
|---------------|-------------:|--------------:|---------|
| Census-dependence (held Power_raw core_H Δ) | 2.37 % | 0.60 % | inside 3 %; **not** the B1 fail |
| Partition residue (native Stage-3 core_H Δ) | 14.57 % | 5.83 % | **this is the core_H B1 fail** |
| Stage-3 minus held core_H (absolute) | 0.7878 − 0.9675 = −0.180 | 0.9760 − 0.9970 = −0.021 | residual / floor-bin share grows as the window shortens |
| Census-dependence (EWSD: held vs native) | 70.65 ≈ 72.72 | 119.44 ≈ 118.04 | ~0; census does not move EWSD |
| n_fft-scaled density (held EWSD Δ) | 22.94 % | 30.27 % | **this is the entire EWSD B1 fail** |

Cross-resolution EWSD invariance is not achievable once detection and
bin gain depend on the analysis window. Comparability is the declared
window (`fft_policy=fixed` 8192/1024).
