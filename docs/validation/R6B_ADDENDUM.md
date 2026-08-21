# R6b addendum — B5/B6 audit, discriminating re-exports, composite correction

Companion to [`REEXPORT_DIFF_SUMMARY.md`](REEXPORT_DIFF_SUMMARY.md) (R6 / PR #92).
Analysis code, F-042 / F-047 / F-048 / F-049, eligibility, bootstrap, and
`analyze_ewsd_balanced.py` were **not** modified. Tag `v4.2.3` on `1db94e1`
stands. This document is execution, audit, and a dated score addendum.

Profile (every new tree):
`wf=log|dst=-90.0|ceil=20000.0|fft=fixed|seg=sustain_primary_stable_diagnostic|elig=1`
(8192 / 1024).

---

## WP1 — Flute *pp* B5 / B6 (EPD vs validated H)

R6 flagged flute *pp* B5 (EPD 13.87 > H = 3) and B6 (EPD 15.49 > H = 2;
EPD Δ vs pretag +475 %). Those EPD figures are
`note_effective_component_density` (F-047, H ∪ I ∪ S). They are **not**
F-012 `effective_partial_density` (validated harmonics only).

### Residual footprint (main-lobe basis)

All four notes: `residual_exclusion_footprint_bins` = **8** (Blackman–Harris
main-lobe diameter); `peak_power_footprint_bins` ≈ 2.00; `window_enbw_hz` ≈
10.79. Core residual share is 0 on the compiled sheet (main-lobe exclusion).
Broadband `residual_energy_ratio` is the contrast:

| Note | residual_energy_ratio | estimated_snr_db | f0 source |
|------|----------------------:|-----------------:|-----------|
| *pp* B5 | 0.9994 | 25.83 | nominal fallback; fit rejected |
| *pp* B6 | 0.9998 | 26.64 | prior-constrained fit accepted |
| *mf* B6 | 0.0029 | 63.42 | prior-constrained fit accepted |
| *ff* B6 | 0.0032 | 65.16 | nominal fallback; fit rejected |

### Hand EPD (F-047) vs pipeline

F-047 compile path: amplitudes on Harmonic Spectrum with
`include_for_density`, **all** Inharmonic Spectrum rows (confirmed or not),
and Sub-bass rows with `subbass_membership = subbass_member`.
\(N_{\mathrm{eff}}=(\sum P_i)^2/\sum P_i^2\), \(P_i=A_i^2\).

| Note | n pool (H+I+S) | ΣP | ΣP² | hand F-047 | pipeline F-047 | match |
|------|---------------:|---:|----:|-----------:|---------------:|:-----:|
| *pp* B5 | 3+2+18 = 23 | 458.1949 | 15136.7151 | 13.869758617 | 13.869758617 | yes |
| *pp* B6 | 2+2+18 = 22 | 125.4410 | 1016.0826 | 15.486380494 | 15.486380494 | yes |
| *mf* B6 | 7+5+18 = 30 | 33464.095 | 1.1130e9 | 1.006141942 | 1.006141942 | yes |
| *ff* B6 | 10+1+18 = 29 | 40316.739 | 1.5904e9 | 1.022063911 | 1.022063911 | yes |

Hand F-047 **matches** the pipeline. PR ≤ census of that pool (13.87 ≤ 23;
15.49 ≤ 22). The published “EPD > validated H” line compared F-047 to
`validated_harmonic_component_count_body_ceiling` (3 / 2). That is not
F-047’s bound.

F-012 (H `include_for_density` only) hand-matches pipeline on B6 *pp/mf/ff*
(1.01473 / 1.00402 / 1.02167). On *pp* B5, Harmonic Spectrum has three
finite included amplitudes (hand F-012 = 2.21754) but Metrics
`effective_partial_density` = **3.17175**. The extra mass is the
`strict_validated_stretched` H2 on Strict_Harmonic_Peaks
(2045.654 Hz, A = 2.75714), whose Amplitude is blank on Harmonic Spectrum.
Reported as a finding; not patched.

### Verdict

**(a)** — the F-047 census admits non-harmonic content. The 18 S members are
`diagnostic_low_frequency_residual_not_partial` (32–78 Hz rumble). Both I
rows are `candidate_not_confirmed_partial`. At flute *pp* B5/B6 those rows
dominate the PR (residual_energy_ratio ≈ 1; unconfirmed I amplitudes ≈ H1).
The same 18 S slots exist at *mf*/*ff* B6 and do **not** inflate EPD,
because H1 is ~180–200 linear amplitude. Values are retained. B5/B6 *pp*
stay on the appendix exception list, annotated as an instrumental *pp*
ceiling case (noise-floor / diagnostic S + unconfirmed I), not as a
formula defect.

The R6 “EPD > validated H” comparison used the wrong bound for F-047
(validated H instead of |H ∪ I ∪ S|). That explains why the inequality
looks like a PR violation; it is not one. No threshold was retuned.

### Census — flute *pp* B5

| n | f (Hz) | A | SNR (dB) | gate | include | exclusion |
|--:|-------:|--:|---------:|------|:-------:|-----------|
| 1 | 986.229 | 2.3846 | 26.08 | strict_validated | True | |
| 2 | 2015.248 | 2.5904 | 26.47 | strict_validated | True | |
| 3 | 3039.750 | 0.8652 | 18.26 | strict_validated | True | |
| 4 | 4271.043 | 0.1011 | 5.17 | off_frequency | False | above_harmonic_body_stop |
| 5 | 5230.522 | 0.0639 | 2.84 | off_frequency | False | above_harmonic_body_stop |
| 6 | 6455.593 | 0.0559 | 2.89 | off_frequency | False | above_harmonic_body_stop |
| 7 | 7964.319 | 0.0529 | 3.20 | snr_validated | False | above_harmonic_body_stop |
| 8 | 9434.939 | 0.0532 | 3.59 | snr_validated | False | above_harmonic_body_stop |
| 9 | 11125.878 | 0.0489 | 2.69 | weak_candidate | False | above_harmonic_body_stop |
| 10 | 12696.354 | 0.0460 | 2.24 | weak_candidate | False | above_harmonic_body_stop |
| 11 | 14692.470 | 0.0496 | 3.34 | snr_validated | False | above_harmonic_body_stop |
| 12 | 16462.067 | 0.0446 | 2.16 | weak_candidate | False | above_harmonic_body_stop |
| 13 | 18634.541 | 0.0454 | 2.39 | weak_candidate | False | above_harmonic_body_stop |
| 14 | 21101.665 | 0.0416 | 2.58 | weak_candidate | False | above_harmonic_body_stop |
| 15–21 | — | — | — | missing_window | False | above_harmonic_body_stop |
| 2 (stretched) | 2045.654 | 2.7571† | — | strict_validated_stretched | True‡ | rejected_stretched_harmonic (dev 43.88 Hz) |

† Amplitude from Strict_Harmonic_Peaks (blank on Harmonic Spectrum).
‡ `include_for_density` True on the audit row; F-047 compile does not see a
finite HS amplitude, so this row is **out** of the 13.87 pool.

I (neither confirmed): 1528.857 Hz A=2.7567 (`local_peak_valid_i`);
2274.445 Hz A=2.7445 (`local_peak_valid_i`).

S members (18 / 63 listed; 32.300–78.058 Hz; A = 7.40 … 1.98): all
`diagnostic_low_frequency_residual_not_partial`.

### Census — flute *pp* B6

H include: n=1 1975.019 Hz A=3.1447 SNR 26.72 `strict_validated`;
n=2 3950.505 Hz A=0.2699 SNR 16.42 `strict_validated`. n=3–11 excluded
(`snr_validated` / `off_frequency` / `weak_candidate`).

I (neither confirmed): 1014.752 Hz A=2.7766; 1017.444 Hz A=2.4658
(both `local_peak_valid_i`). These sit near an octave below f0 (~1975 Hz).

S members: same 18 bins (32.300–78.058 Hz), A = 3.09 … 0.85.

### Contrast — B6 *mf* / *ff*

*mf*: 7 `strict_validated` harmonics, H1 A=182.65, SNR 63.5; F-047 = 1.006.
*ff*: 10 `strict_validated` harmonics, H1 A=199.69, SNR 65.4; F-047 = 1.022.
Same S-member count; S amplitudes are 0.08–0.47 (*mf*) and 0.08–0.11 (*ff*).

Full machine dump: `docs/validation/_r6b/flute_b5b6_audit.json` (gitignored).

---

## WP2 — Discriminating re-exports

Running the unchanged CORDAS script on the old 54 CORDAS_2 trees reproduces
the pretag numbers by construction (R6). This section uses **new-code**
trees under the R6 profile.

Iowa double bass on disk is **only** `_Sustains_Stable` (287 files, matching
pretag N). There is no full `_Sustains` cut, so this test is code/policy
vs the same Stable files — not a full-vs-stable mix. Mixed-baseline caveat:
old CORDAS_2 `analysis_results` vs new `analysis_results_v4.2.3`.

Halt rule (unchanged): unexplained |ΔEWSD| > 25 % on > 5 % of
pretag-matched notes → attach three worst and stop.

**Status: HALT on Iowa bass.** Twelve leaves exported
(`analysis_results_v4.2.3` under each `_Sustains_Stable`),
`verify_corpus` ok on all twelve (287 notes). Pretag match is the twelve
CORDAS_2 `analysis_results` workbooks (same Stable files).
**60 / 287 (20.9 %) have |ΔEWSD| > 25 %.** Cello *pp*/*mf* were **not**
started. The unchanged CORDAS script was **not** run (would rewrite the
54-tree CSV). Spearman below is a sidecar on the twelve new workbooks
only, same test the script uses.

Mixed-baseline caveat: old CORDAS_2 trees are pre-v4.2.3 SustainStable;
new trees are v4.2.3 on the **same** Stable files (Iowa bass has no full
`_Sustains`). Δ is code/policy, not a full-vs-stable cut. EPD stays
flat on the halt notes (pattern matches trombone/flute).

Three worst |ΔEWSD|:

| Leaf | Note | EWSD old → new | ΔEWSD | EPD old → new | ΔEPD |
|------|------|----------------|------:|---------------|-----:|
| `DB_Arco_sG_pp` | G♯3 | 15.02 → 27.46 | **+82.8 %** | 1.055 → 1.048 | −0.7 % |
| `DB_Arco_sG_mf` | A3 | 21.11 → 36.24 | **+71.6 %** | 1.072 → 1.067 | −0.4 % |
| `DB_Arco_sD_mf` | G♯3 | 13.98 → 23.86 | **+70.7 %** | 1.032 → 1.026 | −0.5 % |

**Halt treated as explained (21 Aug 2026).** Same files; EPD invariant;
EWSD up in a block — the R6 trombone/flute generation signature
(recovered high partials / energy rebase), not a census defect. Cello
*pp*/*mf* proceed. The unchanged CORDAS script runs after those trees
land.

Pooled Iowa-bass EWSD ρ = +0.196 is **not** a new physical law. It is
mostly between-string composition: the G string is the densest
(median EWSD 35.7) and sits high in MIDI. Within-string EWSD–MIDI is
flat on A/D/G; only E thins (ρ = −0.48). EPD pooled stays flat
(ρ = −0.028). Publish the string split, not the pooled EWSD ρ.

| String | n | med. EWSD | med. EPD | ρ(MIDI, EWSD) | ρ(MIDI, EPD) |
|--------|--:|----------:|---------:|--------------:|-------------:|
| E | 69 | 21.1 | 1.37 | **−0.484** (p=2.5e-5) | −0.381 (p=0.001) |
| A | 76 | 18.6 | 1.32 | +0.035 (n.s.) | −0.395 (p=4.2e-4) |
| D | 75 | 25.2 | 1.42 | +0.010 (n.s.) | +0.114 (n.s.) |
| G | 67 | **35.7** | 1.37 | +0.039 (n.s.) | +0.335 (p=0.006) |
| pooled | 287 | 23.9 | 1.37 | +0.196 | −0.028 (n.s.) |

### Discrimination table

| Prediction | Meaning | Result |
|------------|---------|--------|
| Iowa bass new-code ρ(MIDI, EWSD) ≈ −0.05 | Register-slope flatness is a property of that corpus/instrument (publishable as such); the old pipeline was not masking it | **EPD: ρ = −0.028** (n=287, p=0.63) — still flat. **EWSD pooled +0.196** is a G-string composition effect, not cello-like thinning. Within A/D/G, EWSD–MIDI is flat. This is the row that applies to **EPD** and to within-string EWSD (except E). |
| Iowa bass new-code ρ in the −0.4…−0.6 region | The pretag flat result was a pipeline artefact (stable-cut / tier) | **Not this row** (except the E string alone, ρ_EWSD = −0.48). Pooled new EWSD is +0.196, not −0.4…−0.6. |

Do not read “confirmed” onto the artefact story except in this table.

Cello *ff* ρ(MIDI, EWSD) = **−0.579** (n=101, p=2.3e-10) and
ρ(MIDI, EPD) = **−0.465** (n=101, p=9.8e-7) stay as the final-instrument
register slope.

Cello *pp*/*mf* exported (97 + 97 `_Sustains`, `verify_corpus` ok,
commit `205bde4`, same profile). Halt fired (80 / 194 = 41 %
|ΔEWSD| > 25 %). Same explained pattern: EWSD up, EPD nearly flat.
Three worst: C♯5 / A5 / F♯5 on *pp* Corda A (+98 % / +94 % / +91 %
EWSD; EPD −1.0 % / −8.6 % / −7.2 %).

Unchanged `analyze_ewsd_balanced.py` run on the new Iowa-bass +
Iowa-cello trees (old copies of those workbooks hidden for the run;
restored after). Script output:

| Quantity | Pretag (old 54) | New-code |
|----------|----------------:|---------:|
| Full-corpus ε²(EWSD), KW dynamics | 0.00756 (n=1497) | **0.01273** (H=21.34, p=2.3e-5, n=1522) |
| Full-corpus ε²(EPD), sidecar | 0.0132 | **0.01637** (H=26.87, p=1.5e-6, n=1522) |
| Iowa bass ρ(MIDI, EWSD) | −0.046 (n=287, p=0.44) | **+0.196** (n=287, p=8.7e-4) |
| Iowa bass ρ(MIDI, EPD) | −0.013 (p=0.83) | **−0.028** (n=287, p=0.63) |
| Cello Iowa ρ(MIDI, EWSD) | — | *ff* **−0.579** (n=101); pp+mf+ff **−0.388** (n=295, p=5.2e-12) |
| Cello Iowa ρ(MIDI, EPD) | — | *ff* **−0.465** (n=101); pp+mf+ff **−0.308** (n=295, p=6.5e-8) |
| Cello-only ε²(EWSD) pp/mf/ff | — | **0.0446** (H=15.03, p=5.4e-4, n=295) |
| Cello-only ε²(EPD) pp/mf/ff | — | **0.0712** (H=22.78, p=1.1e-5, n=295) |

Full-corpus ε² rose vs 0.0076 because the new Iowa cello trees replace
the old Stable cut and add *pp*/*mf*; it is still a small dynamic
effect. Cello-only ε² is larger (0.045 / 0.071) but remains modest
beside the register slope.

---

## WP3 — Composite recomputation (replaces R6 §5)

Original measurement-performance report
([`MEASUREMENT_PERFORMANCE_REPORT.md`](MEASUREMENT_PERFORMANCE_REPORT.md)):

| Part | Score | Definition (verbatim structure) |
|------|------:|----------------------------------|
| A accuracy | 87.5 | mean of eight rubric rows A1–A8 |
| B invariance | 71.4 | B1–B6/B8; 5/7 scored cells pass |
| C uncertainty | 65.0 | C1–C4 machinery score |
| D corpus-level validity | 82.5 | items 1, 2, 3–4, 5; see below |
| **Composite (mean)** | **76.6** | (87.5 + 71.4 + 65.0 + 82.5) / 4 |

No new invariance test was run under v4.2.3. **B1 remains FAIL** (R1b
re-scope). **B5 remains FAIL** in this composite (the original Part B
cell; R3’s dated addendum does not rewrite the table). A and C are
untouched. The only component that changes is **D**, now scored on the
seven real v4.2.3 corpora with the original item definitions.

### Original D items (from the report and `_score_part_d`)

Quoted / as coded for the tuba v4.2.1 tree that produced 82.5:

1. **Item 1 — eligibility.** 100 if % eligible ≥ 95; 70 if ≥ 85; else 30.
   Tuba: 100.0 % → 100. Aggregation over several corpora: mean of per-corpus
   item-1 scores.
2. **Item 2 — internal validity.** Pass (100) iff ρ(H, EPD) > 0 **and**
   EPD>N count = 0 **and** energy-closure violations = 0; else 30.
   Tuba: ρ=0.7662, EPD>N=0, closure=0 → 100. Over several corpora: **all**
   must pass.
3. **Items 3–4 — pitch monotonicity.** 100 if zero unexplained EWSD rises
   (no CI overlap); 70 if all explained in audit sheets; else 30.
   Tuba: 1 rise → 30.
4. **Item 5 — 3-note re-run identity.** PASS → 100 (3 notes). Not re-run
   under v4.2.3; kept as the original PASS.

D = mean of those four scores. Tuba:
(100 + 100 + 30 + 100) / 4 = **82.5**.

The R6 sheet used (100 + 30 + 30) / 3 = 53.3 for D and then
(100 + 100 + 30 + 30 + 53.3) / 5 = 62.7. That derivation is wrong because
it scored B1 and B5 at 100, omitted A (87.5), and dropped item 5 so D’s
denominator was undefined.

### D on the seven v4.2.3 corpora

| Sub-score | Criterion | Per corpus / pooled | Value |
|-----------|-----------|---------------------|------:|
| Item 1 | eligibility ≥ 95 % → 100 | all seven: 100 % eligible | **100** (mean) |
| Item 2 | ρ(H,EPD)>0 and EPD>N=0 and closure=0 | flute *pp* EPD>N on B5/B6 (F-047 vs H; also F-012 B5 3.17>3) | **30** (FAIL) |
| Items 3–4 | unexplained pitch-mono rises | 1 rise (flute *pp* C4 after B3, CIs do not overlap) | **30** |
| Item 5 | 3-note identity | original PASS; no new v4.2.3 run | **100** |

D_addendum = (100 + 30 + 30 + 100) / 4 = **65.0**.

### Both composites

| Label | Arithmetic | Value |
|-------|------------|------:|
| Original headline (unchanged) | (87.5 + 71.4 + 65.0 + 82.5) / 4 | **76.6** |
| Addendum, D recomputed over v4.2.3 corpora | (87.5 + 71.4 + 65.0 + 65.0) / 4 | **72.225** |

This is not 62.7: the previous derivation mis-scored B1/B5 at 100, omitted
A, and used an undefined three-term D.

---

## WP4 — Hygiene

- R6 helpers moved to `tools/r6/`; R6b helpers are `tools/r6b/`.
  Export logs stay in `docs/validation/_r6b/` (gitignored).
- `verify_corpus` **ok** on the seven R6 trees, twelve Iowa-bass
  leaves, and cello *pp*/*mf*/*ff*. Same production profile on every
  tree. R6 seven stay at commit `1db94e1`; WP2 trees are `205bde4`
  (docs-only merge after the tag; analysis modules unchanged).
- Manifests still read `code_dirty: true`. Cause is helper / docs
  files in the working tree, **not** analysis-code edits. At export
  time that list was `tools/r6b/` (audit, export, halt, CORDAS
  wrapper), `.gitignore` (`_r6b/`), and this addendum. No re-export.
- Package version sync to 4.2.3 is a separate commit
  (`chore: sync package version to v4.2.3`).
- [`REEXPORT_DIFF_SUMMARY.md`](REEXPORT_DIFF_SUMMARY.md) header points
  here. CHANGES / README validation map mention both.

---

## Freeze / stop log

- No F-042 / F-047 / F-048 / F-049, eligibility, bootstrap, or CORDAS
  script edit.
- WP1 F-012 B5 set mismatch (stretched H2) logged; not patched.
- WP2 halt fired on Iowa bass (60/287) and cello *pp*/*mf* (80/194).
  Both treated as explained (EPD invariant, EWSD generation shift).
  Unchanged CORDAS script run on the new trees.
