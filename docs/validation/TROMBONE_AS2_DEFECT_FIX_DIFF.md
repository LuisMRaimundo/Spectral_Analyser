# Before / after — trombone A♯2 *ff* and tuba A2 *pp*

D1–D5 landed on `main` in PR #75 (`ec0a99a`). This page is the WP2
verification after WP1 (`38cb535`): Stage 1–3 re-export with
`fft_policy=fixed`, `n_fft=8192`, `hop=1024`, `window=blackmanharris`,
`zero_padding=2`. F-042 / F-047 / F-048 / F-049 algebra is unchanged.

Local artefacts (not committed): `docs/validation/_wp2_raw/`.
Command: `python -m tools.wp2_acceptance_export --out docs/validation/_wp2_raw`.

## Trombone A♯2 *ff* SustainStable

Audio: `IOWA_Trb.T_ff.A#2_SustainStable.aif`  
After workbook: `_wp2_raw/trombone_as2_ff/stage1/A#2/spectral_analysis.xlsx`  
f0 used = 116.300 Hz.

| Field | Before (`5b1a1c7`) | After D1–D5 (PR #75) | After WP1 (`38cb535`) |
|-------|-------------------:|---------------------:|----------------------:|
| `harmonic_validated_count` | 78 | 89 | **92** |
| `harmonic_validated_weak_count` | — | 18 | **14** |
| `harmonic_validated_strict_count` | 78 | 71 | **78** |
| `tolerance_continuity_override_count` | — | 0 | **0** |
| `subbass_upper_bound_hz` | 80 | 58.15 | **58.15** |
| `subbass_bound_formula` | — | `min(0.5*f0, 80)` | `min(0.5*f0, 80)` |
| `effective_partial_density` | — | 12.87 | **12.47** |
| `EWSD_score_acoustic_balanced` | — | not re-run | **87.41** |
| CI unit / n | not exported | `partials` / 89 | `partials` / 168 (Stage 2) |
| `accepted_slots_above_body_stop` | 0 | 0 | **0** |

Acceptance: `harmonic_validated_count ≥ 86` (92). `subbass_upper_bound_hz =
58.15` on Metrics, Validation_Metrics, and Analysis_Metadata.

H74 and H79 are **included**. On this take they enter via D1
(`validated_weak`, `exclusion_reason = included (weak_margin_persistence_override)`,
persistence = 1.0), not D2. They were not `rejected_by_tolerance` after the
current slot match, so `tolerance_continuity_override_count` stays 0. D2 still
applies when both neighbours are validated and the reject is a spacing-cap miss.

One energy pie: `component_energy_pie.png`. `hop_duration_s` = 0.0232 s;
`window_duration_s` = 0.1858 s at sr = 44100, n_fft = 8192.

## Tuba A2 *pp* SustainStable

Audio: `IOWA_Tub.pp.A2_SustainStable.aif`  
After: `_wp2_raw/tuba_a2_pp/stage1/A2/spectral_analysis.xlsx`

| Field | Before (gated A2 / `70525e3`) | After D1–D5 | After WP1 (`38cb535`) |
|-------|------------------------------:|------------:|----------------------:|
| `harmonic_validated_count` | 8 (H1–H8) | 7 | **8** |
| `harmonic_validated_weak_count` | — | 1 | **2** |
| `tolerance_continuity_override_count` | — | 0 | **0** |
| `subbass_upper_bound_hz` | 55 | 54.997 | **55.02** |
| `effective_partial_density` | 3.77 | 3.81 | **3.77** |
| `EWSD_score_acoustic_balanced` | — | not re-run | **16.11** |
| `accepted_slots_above_body_stop` | 0 | 0 | **0** |
| CI unit / n / flag | not exported | `partials` / 7 | `partials` / 25 / `wide` |

High-*n* floor remains excluded. H74 / H79 on tuba A2 are `snr_validated`
and not included (persistence 0.50 / 0.62). D1 adds at most weak-margin
body partials; it does not reopen the 12 kHz harvest.

CI provenance columns present on Stage 2 `Density_Metrics`:
`ci_resampling_unit`, `ci_n_resampled`, `ci_bootstrap_iterations`,
`ci_seed`, `ci_width_flag`, `ci_width_note`.

## Unit-test gate

`tests/phase_23/test_trombone_as2_defect_fixes.py` (including
`test_iowa_trombone_as2_ff_acceptance_if_present` at n_fft=4096) passed on
`38cb535`.
