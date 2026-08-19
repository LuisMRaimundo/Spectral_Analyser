# Low-f₀ fixtures

IOWA tuba *pp* `_Sustains_Stable` exports and audio:

- `C1/` — `spectral_analysis.xlsx` (main / pre-4.1.0), `C1.aif`
  (keep the note in the filename; `audio.aif` is refused by the parser)
- `Ds1/` — D#1
- `C2/`

Trombone *pp* E2–C5 `_Sustains_Stable` batch:

- `trombone_pp/<Note>/spectral_analysis.xlsx` (main)
- `trombone_pp/<Note>/expected_main.json` (`canonical_density`, compiled
  `note_density_final`, research EWSD)
- `trombone_pp/<Note>/C5.aiff` (C5) or `<Note>.aif`
- `trombone_pp/acceptance_v2.json` — measured max `|Δcanonical_density|`

Fixture tests re-analyse the audio using settings replayed from each
main workbook (`window`, `weight_function`, `n_fft`, `zero_padding`,
`hop_length`, salience).
