# EWSD acoustic construct & sensitivity report

Source: `C:\Users\lmr20\Desktop\ORC_Vlc_arco_mf\_Sustains\ewsd_ratio_respecting_results.xlsx`
Rows: 49 (finite scores: 49)

## Alpha rank stability (acoustic-balanced recomputation)

Spearman ρ between note ranks at different penalty exponents α.

| α_a | α_b | Spearman ρ | n notes |
|-----|-----|------------|---------|
| 0.25 | 0.5 | 0.9953 | 49 |
| 0.25 | 0.75 | 0.9868 | 49 |
| 0.25 | 1.0 | 0.9801 | 49 |
| 0.5 | 0.75 | 0.9962 | 49 |
| 0.5 | 1.0 | 0.9917 | 49 |
| 0.75 | 1.0 | 0.9981 | 49 |

## Construct checks (acoustic, non-perceptual)

- Strict vs balanced Spearman ρ: **0.9917**
- Strict ≠ balanced (numerically): **True**
- Register (MIDI) vs balanced Spearman ρ: **-0.9156**
- Mean compartment penalty vs strict Spearman ρ: **0.6037**

Interpretation: high α-a vs α-b rank stability supports using α=0.5 for
cross-instrument comparison; register correlation documents physical capacity
effects rather than perceptual validation.
