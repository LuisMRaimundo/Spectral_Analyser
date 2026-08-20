# Pre-tag findings summary

Every row is **pre-tag; to be reproduced under the freeze tag**.
Source artefacts live in `docs/validation/pretag_evidence/` unless
noted. Non-citable for publication.

## Trombone dynamic ordering (pp &lt; mf &lt; ff)

| Item | Value |
|------|-------|
| Finding | Per-note `EWSD_score_acoustic_balanced`: pp &lt; mf &lt; ff |
| Count | **32 / 32** notes present in all three dynamics (E2–C5; trombone *pp* has no B4) |
| Source | `pretag_evidence/trombone_{pp,mf,ff}_compiled_density_metrics_research.xlsx` |
| Commit | `6b0e51a` |
| Status | pre-tag; to be reproduced under the freeze tag |

Boundary notes (same workbooks):

| Note | pp | mf | ff |
|------|---:|---:|---:|
| G3 | 19.34 | 40.75 | 91.46 |
| G♯3 | 14.55 | 29.70 | 63.87 |
| C5 | 7.23 | 7.70 | 12.93 |

## Flute pp &lt; {mf ≈ ff}

| Item | Value |
|------|-------|
| Finding | pp &lt; min(mf, ff) on **36 / 37** pitch-matched notes; mf &lt; ff on **22 / 38** mf–ff pairs (16 / 38 have mf &gt; ff) |
| Source | `pretag_evidence/flute_{pp,mf,ff}_compiled_density_metrics_research.xlsx` |
| Commit | `6b0e51a` |
| Status | pre-tag; to be reproduced under the freeze tag |

The single pp miss among the 37 common notes is recorded in the
workbooks (not dropped). mf and ff do not form a strict ladder; that
is the “mf ≈ ff” claim.

Boundary notes:

| Note | pp | mf | ff |
|------|---:|---:|---:|
| C5 | 6.14 | 10.29 | 10.09 |
| F6 | 2.57 | 3.23 | 3.71 |

## Cello G2 stable / full contrast

| Item | Value |
|------|-------|
| Finding | Full sustain 43 H, 551 Hz, EWSD 50.2; stable 16 H, 140 Hz, EWSD 12.3; 1.75 independent frames on the stable cut |
| Source | `SEGMENTATION_CASE_STUDY_G2.md` (the two workbooks were **not** placed in `pretag_evidence/`) |
| Status | pre-tag; to be reproduced under the freeze tag |

## Trombone / flute tier-boundary steps

| Item | Value |
|------|-------|
| Finding | G3 → G♯3 and B4 → C5 (trombone) and C5 / F6 (flute) are the notes the runbook names as FFT-tier boundaries. On these `6b0e51a` SustainStable exports the research sheet has no `n_fft` column; EWSD still drops at G3→G♯3 and B4→C5 (see trombone table above). |
| Source | trombone and flute workbooks in `pretag_evidence/` |
| Status | pre-tag; to be reproduced under the freeze tag |

## Automatic vs manual segmentation (26 notes)

| Item | Value |
|------|-------|
| Finding | 26 notes; log-spectral r ≥ 0.999; median centroid Δ 0.9 % (claim from the rating prompt) |
| Source | **not located** — no comparison sheet in the repo, `pretag_evidence/`, `D:\CORDAS_2`, or the Desktop rating folder |
| Status | pre-tag; to be reproduced under the freeze tag; artefact missing |

## CORDAS predictions (for P6 rerun)

| Item | Value |
|------|-------|
| Dynamic KW ε² | **0.0076** (H = 13.30, p = 0.0013) |
| Iowa double bass ρ(MIDI, EWSD) | **−0.046** (n = 287, p = 0.44 n.s.; rating prompt rounded −0.05) |
| Source | `pretag_evidence/cordas/EWSD_acoustic_balanced_CORDAS_report.md` §7.3 and §9 |
| Script | `D:\CORDAS_2\reports\analyze_ewsd_balanced.py` (unchanged; not copied) |
| Status | pre-tag; to be reproduced under the freeze tag |
