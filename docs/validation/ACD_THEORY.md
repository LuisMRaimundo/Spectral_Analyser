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

## IDs

F-051–F-054 were already allocated in this repository. ACD uses F-057–F-060.
