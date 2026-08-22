# Auditory Component Density — derivation memo

ACD v1.0 (F-057–F-060). Acoustic construct only.

## Why not `N_eff / N`

The frozen EWSD identity

```
EWSD_k = D_k · r_k · (N_eff,k / N_k)  =  r_k · mean(φ) · N_eff,k
```

holds when `D_k = sum φ(A_i)` (for example `φ = log1p`). The third factor
is an effective count. Putting the raw peak count `N` in the denominator
violates the replication principle (Hill, 1973; Jost, 2006; Hurley &
Rickard, 2009): concatenating a disjoint copy of a spectrum should
**double** the diversity number, but `N_eff / N` is unchanged because both
the numerator and the denominator double. Adding near-zero peaks (a lower
peak-picking threshold or a longer FFT) inflates `N` and collapses the
score. That is a property of the peak picker, not of the sound.

## Replacement

1. Shares `p_i = A_i^2 / sum A^2` — exact gain invariance.
2. Report Hill `D2 = 1 / sum p_i^2` (`N_eff`) directly, not `N_eff / N`.
3. Merge peaks inside one ERB (`ERB(f) = 0.108 f + 24.7`; Glasberg & Moore,
   1990) so `N` is bounded by auditory filters.
4. Emit the pair `(D2, λ)` with `λ = energy / D2` so a sparse loud sound is
   not interchangeable with a dense quiet one.

`r_k` is `energy_k / sum energy`. It is not read from Excel.

## Hurley & Rickard (2009) — diversity dual of sparsity

Hurley and Rickard state Rising Tide and Dalton for a **sparsity** measure.
Hill \(D_q\) is the diversity dual, so both directions invert: adding a
constant to every component *increases* \(D_2\), and a Robin Hood transfer
*increases* \(D_2\). The implementation is correct. A reader checking the
2009 paper should not read the sign as an error.

Verified on energy shares of \(A\):

```
A = [4, 1, 1]  ->  D2 = 1.2558
A + 2          ->  D2 = 2.0000
A + 20         ->  D2 = 2.9494
```

## IDs

F-051–F-054 were already allocated in this repository. ACD uses F-057–F-060.

## Why the headline count is D1, not D2

D2 is a dominance statistic, not a count. For a 1/n rolloff —
approximately what a bowed string produces — energy shares go as
1/n^2 and D2 converges to the analytic limit

```
lim N→∞ D2 = (ζ(2))^2 / ζ(4)
           = (π²/6)² / (π⁴/90)
           = 2.500
```

Derivation: p_n = n^{-2} / H_N^{(2)}, so
D2 = (H_N^{(2)})^2 / H_N^{(4)}. The p-series limits are the
Riemann zeta values ζ(2) = π²/6 and ζ(4) = π⁴/90.

Numbers below are produced by `tests/phase_32/acd_d1_promotion_tables.py`
on an unmerged 1/n amplitude series (A_n = 1/n).

| N partials | D0 | D1 | D2 | Dinf |
|---:|---:|---:|---:|---:|
| 4 | 4.000 | 2.435 | 1.879 | 1.424 |
| 12 | 12.000 | 3.617 | 2.263 | 1.565 |
| 40 | 40.000 | 4.466 | 2.426 | 1.620 |
| 60 | 60.000 | 4.644 | 2.450 | 1.628 |

A fifteen-fold change in partial count moves D2 by 29%.
Jost (2006) argues that D1 = exp(H) is uniquely justified when no
weighting of components is preferred a priori: each component is
weighted by its share exactly once.

Across N ∈ {8,…,40} and spectral slope ∈ {0.5,…,2.0}
(A_n = n^{-slope}) the measured dynamic ranges are:

| order | max/min |
|---|---:|
| D0 | 5.0× |
| D1 | 15.0× |
| D2 | 9.7× |

Headline `ACD_score` is therefore `sum_k r_k D1_k`. The previous
D2-based value is retained as `ACD_score_D2_dominance`.
`ACD_D0_minus_D1` is the count of components present but not
carrying effective weight — a texture descriptor, not a diagnostic.
