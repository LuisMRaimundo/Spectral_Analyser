# EWSD weight-function φ sensitivity

Source: `D:\METAIS\TUBA\Tuba\Tuba_Yowa\IOWA_tuba_pp\_Sustains_Stable\analysis_results_4`
Notes: 37
Default φ: `log` (log-amplitude loudness proxy).

Spearman ρ of `EWSD_score_acoustic_balanced` ranks across amplitude-family φ.
Discrete D3/D10/D17/D24 keys are excluded (they are not φ transforms).

## Pairwise rank agreement

| φ_a | φ_b | Spearman ρ | n notes |
|-----|-----|------------|---------|
| linear | log | 0.9590 | 37 |
| linear | sqrt | 0.9794 | 37 |
| linear | cbrt | 0.9478 | 37 |
| linear | squared | 0.9369 | 37 |
| linear | cubic | 0.7890 | 37 |
| linear | exponential | 0.9905 | 37 |
| linear | inverse log | 0.1143 | 37 |
| log | sqrt | 0.9924 | 37 |
| log | cbrt | 0.9960 | 37 |
| log | squared | 0.8779 | 37 |
| log | cubic | 0.7572 | 37 |
| log | exponential | 0.9500 | 37 |
| log | inverse log | 0.3039 | 37 |
| sqrt | cbrt | 0.9865 | 37 |
| sqrt | squared | 0.9004 | 37 |
| sqrt | cubic | 0.7677 | 37 |
| sqrt | exponential | 0.9670 | 37 |
| sqrt | inverse log | 0.2406 | 37 |
| cbrt | squared | 0.8632 | 37 |
| cbrt | cubic | 0.7551 | 37 |
| cbrt | exponential | 0.9353 | 37 |
| cbrt | inverse log | 0.3374 | 37 |
| squared | cubic | 0.9227 | 37 |
| squared | exponential | 0.9222 | 37 |
| squared | inverse log | 0.0754 | 37 |
| cubic | exponential | 0.7696 | 37 |
| cubic | inverse log | 0.1003 | 37 |
| exponential | inverse log | 0.0806 | 37 |

Minimum pairwise Spearman ρ (all amplitude-family φ): **0.0754**
Minimum pairwise Spearman ρ (compressive family linear/log/sqrt/cbrt): **0.9478**

EWSD ordering is **not** φ-invariant across all amplitude-family φ (minimum pairwise ρ = 0.075). Among compressive φ (linear, log, sqrt, cbrt) ρ ≥ 0.948.
