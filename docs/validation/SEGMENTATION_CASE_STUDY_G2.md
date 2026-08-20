# Segmentation case study — cello G2 (full sustain vs stable)

WP3 / WP6 evidence that the stable-sustain cut is **diagnostic**, never
the primary EWSD. ADSR_Segmenter was not modified. Numbers are the
accepted G2 pair used by `tests/phase_26/test_production_policy.py`.

| Cut | Harmonics | Centroid Hz | EWSD (acoustic-balanced) | Independent frames |
|-----|----------:|------------:|-------------------------:|-------------------:|
| Full sustain (primary) | 43 | 551 | 50.2 | ≥ 8 (eligible) |
| `_SustainStable` (diagnostic) | 16 | 140 | 12.3 | 1.75 |

- Full / stable EWSD ratio = 50.2 / 12.3 ≈ **4.08** (above the 1.3
  representativeness cap).
- Full / stable centroid ratio = 551 / 140 ≈ **3.94** (above the 2.0
  centroid cap).
- Stable is therefore `stable_segment_unrepresentative = True`.
- Stable is also `ewsd_primary_analysis_eligible = False` because
  independent frames (1.75) are below `MIN_INDEPENDENT_FRAMES` (8).
- Degenerate-partial is false (16 harmonics > 2). The ineligibility
  reason is the frame count, not a two-partial set.

## Policy

Sustain is the primary analysis cut. A `_SustainStable` sibling or ADSR
JSON sidecar fills diagnostic columns only (`stable_segment_ewsd`,
`full_stable_ewsd_ratio`, `stable_segment_frames_independent`,
`stable_segment_unrepresentative`). Missing siblings are NaN
(`nan_not_zero_v1`), never 0.0. Values are never substituted.

Quoting the stable G2 EWSD (12.3) as the note score would understate
the full sustain by a factor of four and report a spectrum whose
centroid has dropped from 551 Hz to 140 Hz. That is why the freeze
profile is `seg=sustain_primary_stable_diagnostic`.
