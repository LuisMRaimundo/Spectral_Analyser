# Before / after — trombone A♯2 *ff* and tuba A2 *pp*

Stage 1 re-exports under the D1–D5 defect-fix branch. F-042 / F-047 /
F-048 / F-049 algebra is unchanged. EWSD is a Stage 3 column; it is not
recomputed here. The Phase H corpus re-export remains the post-merge
deliverable.

Before values for trombone A♯2 are the `5b1a1c7` review figures. Tuba A2
before values are the exclusive-gating (`70525e3` / Análise 3) A2 take
where comparable.

## Trombone A♯2 *ff* SustainStable

Audio: `IOWA_Trb.T_ff.A#2_SustainStable.aif`  
After workbook: `analysis_results_d1/A#2/spectral_analysis.xlsx`  
f0 used = 116.293 Hz.

| Field | Before (`5b1a1c7`) | After (D1–D5) |
|-------|-------------------:|--------------:|
| `harmonic_validated_count` | 78 | **89** |
| `harmonic_validated_weak_count` | — | **18** |
| `harmonic_validated_strict_count` | 78 | **71** |
| `tolerance_continuity_override_count` | — | 0 |
| `subbass_upper_bound_hz` | 80 | **58.15** |
| `subbass_bound_formula` | — | `min(0.5*f0, 80)` |
| `subbass_member_count` | (80 Hz members) | 3 |
| `effective_partial_density` | (review EPD on 78 H) | 12.87 |
| `note_density_final` | Stage 2 | not re-run |
| `EWSD_score_acoustic_balanced` | Stage 3 | not re-run |
| CI unit / n | not exported | `partials` / 89 |
| CI width flag / note | 68.8 % wide | `wide` / `high_partial_correlation` |
| `accepted_slots_above_body_stop` | 0 | 0 |

H81–H85, H87–H88 are `validated_weak` (persistence ≥ 0.98, margin < 3 dB).
H86 is `snr_validated` (not CFAR-detected) and stays out. H89 and H93 also
meet the override. H74 and H79 are included; on this take they enter via
D1 (`validated_weak`) rather than D2 (they were not `rejected_by_tolerance`
after the current slot match). D2 still applies when both neighbours are
validated and the reject is a spacing-cap miss.

`subbass_energy_sum` = 0.0451 (F-020 members). Diagnostic rows above 58.15 Hz
are `lf_diagnostic_not_member`.

One energy pie: `component_energy_pie.png` (Validated-partial energy balance).
`hop_duration_s` = 0.0232 s; `window_duration_s` = 0.0929 s at sr = 44100,
n_fft = 4096. `frame_duration_s` is the deprecated hop alias.

## Tuba A2 *pp* SustainStable

Audio: `IOWA_Tub.pp.A2_SustainStable.aif`  
After: `analysis_results_d1_a2/A2/spectral_analysis.xlsx`

| Field | Before (gated A2) | After (D1–D5) |
|-------|------------------:|--------------:|
| `harmonic_validated_count` | 8 (H1–H8; H7/H8 could be `cfar_marginal`) | **7** |
| `harmonic_validated_weak_count` | — | 1 |
| `tolerance_continuity_override_count` | — | 0 |
| `subbass_upper_bound_hz` | 55 (F-020) | **54.997** |
| `effective_partial_density` | 3.77 | 3.81 |
| `accepted_slots_above_body_stop` | 0 | 0 |
| CI unit / n | not exported | `partials` / 7 |

High-*n* floor remains excluded. The body stop and the 0.7 persistence
gate still keep the 12 kHz harvest out. D1 adds at most one weak-margin
body partial; it does not reopen the floor.
