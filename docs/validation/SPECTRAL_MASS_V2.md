# F-061 spectral_mass v1 → v2

Exported `spectral_mass` and `spectral_mass_count` change. Formula
version **1.0 → 2.0**. Column names are unchanged.

## Why

v1 used the energy-weighted pooled Hill numbers:

    count = sqrt(ACD_D0 * ACD_score)

Pooled D0 lets inharmonic and sub-bass entities enter the count at
entity weight. On the cello corpus that was about 30% of counted
entities against ~2% of energy (I+S contribution to the count up to
15%).

## v2

    count_k = sqrt(D0_k * D1_k)
    count   = sum_k r_k * count_k
    lambda  = E_total / count
    spectral_mass = count * lambda ** 0.15

`MASS_COUNT_BLEND` (0.5) still applies *within* each compartment.
`MASS_LEVEL_EXPONENT` (0.15) is unchanged. Cross-compartment
contributions are bounded by energy share.

## New Stage 3 columns (additive)

`ACD_D0_harmonic`, `ACD_D0_inharmonic`, `ACD_D0_subbass`,
`ACD_D1_harmonic`, `ACD_D1_inharmonic`, `ACD_D1_subbass`,
`ACD_energy_total`. Existing ACD scores, ratios, D2 columns, and
merged counts are not recomputed.

## Backfill

`tools/backfill_spectral_mass.py` requires the three `ACD_D1_*`
columns. Workbooks from v1 Stage 3 are refused with a message to
re-export (or re-analyse from audio); the v1 pooled formula is not applied silently.

External explanatory documents dated before v2 (including
`Spectral_Mass_F061_Calculation.docx`) describe the v1 pooled-D0 count;
the worked example (F#4 = 21.0413) is a v1 value.

v2 worked example (synthetic per-compartment split of the same F#4
energy): $D0_H=24$, $D1_H=1.10$, $r_H=0.96$, $D0_I=40$, $D1_I=2.5$,
$r_I=0.03$, $D0_S=15$, $D1_S=1.8$, $r_S=0.01$, $E=10589.223$ →
`spectral_mass` = 16.5305.
