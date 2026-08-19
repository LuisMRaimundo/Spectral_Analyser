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

Pre-fix `harmonic_body_stop_order` on trombone *ff* jumped across adjacent notes (32 at C3, 80 at A♯2, 85 at F♯2). That diagnostic is a CFAR/body-stop order, not an energy sum, so D6.2 does not change the stop rule. A full 33-note re-export is a PR artefact (`tools/reexport_corpus.py`), not a unit test. If the stop still jumps after that re-export, open a follow-up issue with the per-note stop diagnostics (`harmonic_body_stop_order`, `accepted_slots_above_body_stop`, `included_above_body_stop_count`).
