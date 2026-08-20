# CORDAS_2 — EWSD acoustic-balanced corpus report

**Metric (exclusive):** `EWSD_score_acoustic_balanced` (Stage 3 construct F-049)  
**Source:** every `compiled_density_metrics_research.xlsx` under `D:\CORDAS_2`, sheet `Spectral_Density_Metrics`  
**Protocol filter:** `ewsd_primary_analysis_eligible == True`  
**Date of analysis:** 20 August 2026  
**Machine artefacts:** `ewsd_balanced_analysis.json`, `ewsd_balanced_note_rows.csv`, `ewsd_balanced_group_coverage.csv`, `ewsd_balanced_group_descriptives.csv`, `analyze_ewsd_balanced.py`

This report uses **only** the acoustic-balanced EWSD scalar. Identity fields (instrument, collection, string, note, MIDI, register, dynamic) are labels. No other density column was analysed.

---

## 1. What the score is

`EWSD_score_acoustic_balanced` is the cross-instrument Effective Weighted Spectral Density with a **moderated** compartment-wise participation-ratio penalty (α = 0.5). It answers: *how much GUI-weighted harmonic / inharmonic / stochastic energy is present after a partial anti-concentration penalty?*

It is **not** loudness, not RMS, and not interchangeable with `note_density_final` or `EWSD_score_total`. Higher values mean a denser, less single-partial-dominated spectrum under the Stage 3 weight function and the 20 kHz density ceiling.

For bowed strings that is acoustically expected to rise when:

- the sounding pitch is lower (more harmonics fit under the ceiling);
- the string is thicker / lower (richer low-order stack, more bow-noise sidebands);
- the dynamic increases *if* the extra bow force actually recruits partials rather than just scaling the same envelope.

The methods below test those three expectations on this corpus.

---

## 2. Coverage — instrument, collection, string

54 research workbooks were found. Sixty `_Sustains_Stable` audio folders exist; **six have no research workbook**. Eligible note rows: **1497** (1531 loaded, 1523 numeric, 26 ineligible empty rows, all Iowa cello C-string sheet padding).

### 2.1 Inventory of analysed groups

| Instrument | Collection | String | Dynamics present | Eligible *n* | Median EWSD | Bootstrap 95% CI |
|---|---|---|---|---:|---:|---|
| Violin | IOWA | G, D, A, E | pp, mf, ff | 315 | 13.32 | 12.38–14.70 |
| Violin | Orchidea | pooled (not labelled) | — | **0** | — | missing workbooks |
| Viola | IOWA | C, G, D, A | pp, mf, ff | 293 | 14.54 | 13.34–16.68 |
| Viola | Orchidea | pooled | pp, mf, ff | 147 | 16.76 | — |
| Cello | IOWA | C, G, D, A | pp, mf, ff except **G ff** | 270 | 22.93 | 21.78–25.45 |
| Cello | Orchidea | pooled | **ff only** | 49 | 24.61 | 20.53–34.87 |
| Double bass | IOWA | E, A, D, G | pp, mf, ff | 287 | 22.99 | 22.32–24.35 |
| Double bass | Orchidea | pooled | pp, mf, ff | 136 | 24.57 | 21.71–27.30 |

Iowa strings are taken from the leaf folder (`Corda Dó / Sol / Ré / Lá / Mi` and `sC/sG/sD/sA/sE`). Orchidea folders are pooled by dynamic; string is **not eligible** as a factor even though filenames may encode `1c`–`4c`.

### 2.2 Missing research workbooks (audio exists)

1. `IOWA\CELLO\…\IOWA_cello_arco_ff_Corda Sol` — Iowa cello **G string, ff**
2. `Orchidea\ORCH_Vlc\…\ORC_Vlc_arco_pp`
3. `Orchidea\ORCH_Vlc\…\ORC_Vlc_arco_mf`
4. `Orchidea\ORCH_Vln\…\ORCH_arco_Vln_pp`
5. `Orchidea\ORCH_Vln\…\ORCH_arco_Vln_mf`
6. `Orchidea\ORCH_Vln\…\ORCH_arco_Vln_ff`

**Consequence:** every violin statement is Iowa-only. Cello Orchidea is an ff-only slice (*n* = 49) and must not be treated as a matched collection contrast.

---

## 3. Methods (chosen for this kind of acoustic corpus)

EWSD on musical notes is **right-skewed, heteroscedastic, and unbalanced** (skew = 1.24, excess kurtosis = 2.22, cello Orchidea *n* = 49 vs viola *n* = 440). Parametric ANOVA on raw scores would be the wrong instrument. The stack is:

| Step | Method | Why it belongs here |
|---|---|---|
| Location | Median + 2000-resample percentile bootstrap CI; 20% trimmed mean; MAD | Robust to the C2 cello floor spikes |
| Shape | Skew, excess kurtosis, CV | Documents why means are pulled high |
| Omnibus | Kruskal–Wallis *H* + ε² = (*H* − *k* + 1)/(*n* − *k*) | Distribution-free group difference; ε² is the rank analogue of η² |
| Pairwise | Mann–Whitney *U*, Holm correction, Cliff’s δ | Effect size that does not assume equal variance; thresholds 0.147 / 0.33 / 0.474 (Romano et al. 2006) |
| Pitch law | Spearman ρ(MIDI, EWSD) inside instrument × collection | Monotone spectral-thinning with rising *f*₀; the main acoustic regularity of harmonic instruments under a fixed Hz ceiling |
| Dynamic | One-sided MWU + Cliff’s δ inside instrument × collection | Tests the bow-force → partial-recruitment hypothesis without pooling instruments |
| String | KW on Iowa instrument×string cells; median table by string × dynamic | Only Iowa folders isolate string |
| Dominance | Sequential Type-I SS on **ranks** (instrument → collection → dynamic → register) | Partition of rank variance without assuming Gaussian errors |
| Anomalies | Within-cell MAD *z* ≥ 3.5 | Flags floor-harvest / open-string extremes, not global *z*-scores |

Cliff’s δ direction in the narrative follows the **medians** (positive = first group denser). Magnitude uses |δ|.

---

## 4. Global distribution

| Statistic | Eligible corpus (*n* = 1497) |
|---|---:|
| Mean | 21.83 |
| Median (95% CI) | **19.35** (18.80–19.92) |
| 20% trimmed mean | 19.68 |
| Q25–Q75 (IQR) | 12.16–27.66 (15.50) |
| SD / MAD | 12.91 / 11.23 |
| CV | 0.59 |
| Min–max | 1.93–96.74 |
| Skew / excess kurtosis | 1.24 / 2.22 |

The mean sits ~2.5 points above the median. Extreme cello C2 values (max 96.74) inflate the mean; the trimmed mean tracks the median. All inferential claims below use ranks / medians.

---

## 5. Instrument families

### 5.1 Location

| Instrument | *n* | Median | 95% CI | Mean | Trimmed 20% | IQR |
|---|---:|---:|---|---:|---:|---:|
| Violin | 315 | 13.32 | 12.38–14.70 | 15.48 | 13.90 | 10.53 |
| Viola | 440 | 15.67 | 13.54–16.83 | 17.95 | 15.29 | 14.20 |
| Cello | 319 | 23.18 | 21.95–25.45 | 27.26 | 25.29 | 18.49 |
| Double bass | 423 | 23.24 | 22.52–24.62 | 26.49 | 24.33 | 14.37 |

Two acoustic families, not four:

- **High strings** — violin ≈ viola (medians 13.3 and 15.7).
- **Low strings** — cello ≈ double bass (medians 23.18 and 23.24).

The cello and bass intervals overlap completely. Violin and viola intervals are close; the viola CI upper bound (16.83) still sits well below the cello CI lower bound (21.95).

### 5.2 Omnibus and pairwise

Kruskal–Wallis on instrument: **H = 297.12, *p* = 4.2×10⁻⁶⁴, ε² = 0.197** (medium rank effect).

| Contrast | Medians | Holm *p* | \|Cliff’s δ\| | Magnitude |
|---|---|---|---:|---|
| Cello vs double bass | 23.18 vs 23.24 | 0.82 | 0.01 | negligible, n.s. |
| Viola vs violin | 15.67 vs 13.32 | 0.12 | 0.08 | negligible, n.s. |
| Cello vs viola | 23.18 vs 15.67 | 2.3×10⁻²⁵ | 0.45 | **medium** |
| Double bass vs viola | 23.24 vs 15.67 | 8.7×10⁻³³ | 0.47 | **large** |
| Cello vs violin | 23.18 vs 13.32 | 1.4×10⁻³² | 0.55 | **large** |
| Double bass vs violin | 23.24 vs 13.32 | 6.6×10⁻⁴³ | 0.60 | **large** |

**Acoustic reading.** After the α = 0.5 penalty, the four orchestral strings collapse to the classical high/low cut. Viola is not a “small cello” on this score; it is a violin-family instrument. Cello is not a “small bass”; it sits on the bass-family density plateau. That is consistent with overlapping *C2–C4* tessitura and comparable harmonic room under 20 kHz.

---

## 6. Collection (IOWA vs Orchidea)

Kruskal–Wallis on the seven observed instrument×collection cells: **H = 302.60, *p* = 2.3×10⁻⁶², ε² = 0.199** — almost the same ε² as instrument alone. Collection itself is a **0.3%** slice of rank variance (Section 10).

Matched collection contrasts (Holm):

| Pair | Medians | Holm *p* | \|δ\| |
|---|---|---|---|
| Cello Iowa vs Orchidea | 22.93 vs 24.61 | 1.00 | 0.07 negligible |
| Double bass Iowa vs Orchidea | 22.99 vs 24.57 | 0.58 | 0.11 negligible |
| Viola Iowa vs Orchidea | 14.54 vs 16.76 | 0.58 | 0.11 negligible |

Orchidea sits slightly higher in every matched pair, but none survives Holm, and cello Orchidea is ff-only. **Collection is not a driver of EWSD in this corpus.** Instrument family and pitch are.

Violin has no Orchidea scores at all, so a violin collection effect cannot be estimated.

---

## 7. Register and pitch — the dominant acoustic law

### 7.1 Register (sheet labels)

Kruskal–Wallis on the five sheet registers (Very low / Low / Middle / High / Very high):  
**H = 917.85, *p* = 2.3×10⁻¹⁹⁷, ε² = 0.612**.

That is a **large** effect — three times the instrument ε². Sheet-register medians:

| Instrument | Very low | Low | Middle | High | Very high |
|---|---:|---:|---:|---:|---:|
| Violin | — | — | 33.72 (*n*=15) | 23.11 | 10.59 |
| Viola | — | — | 36.53 | 18.86 | 8.39 |
| Cello | — | 42.36 | 29.95 | 20.12 | 10.64 |
| Double bass | 37.42 | 22.62 | 23.30 | 21.18 | 11.94 (*n*=3) |

Very-high notes of cello, viola and violin converge near **8–11**. The instrument gap is almost entirely a **tessitura** gap: bass and cello populate Very low / Low; violin and viola populate Very high.

### 7.2 MIDI bands (pitch-matched view)

| Band | Violin | Viola | Cello | Double bass |
|---|---:|---:|---:|---:|
| C0–B1 | — | — | — | 37.42 (*n*=58) |
| C2–B2 | — | — | 42.36 (*n*=58) | 22.62 (*n*=153) |
| C3–B3 | 33.72 (*n*=15) | 36.53 (*n*=87) | 29.95 (*n*=110) | 23.30 (*n*=147) |
| C4–B4 | 23.11 (*n*=77) | 18.86 (*n*=146) | 20.12 (*n*=99) | 21.18 (*n*=62) |
| C5–B5 | 13.36 (*n*=122) | 9.84 (*n*=132) | 10.78 (*n*=51) | 11.94 (*n*=3) |
| C6+ | 7.44 (*n*=101) | 6.21 (*n*=75) | 6.66 (*n*=1) | — |

Pitch-matched, the four instruments **converge**. In C4–B4 the four medians sit in a 18.9–23.1 window. The cello C2–B2 cell (42.4) is the open-C / low-C region, not a “cello is denser” law that survives matching.

### 7.3 Spearman ρ(MIDI, EWSD)

| Instrument | Collection | *n* | ρ | *p* |
|---|---|---:|---:|---|
| Viola | IOWA | 293 | **−0.969** | 1.2×10⁻¹⁷⁹ |
| Viola | Orchidea | 147 | **−0.951** | 1.5×10⁻⁷⁵ |
| Cello | Orchidea | 49 | **−0.891** | 1.0×10⁻¹⁷ |
| Cello | IOWA | 270 | **−0.858** | 1.2×10⁻⁷⁹ |
| Violin | IOWA | 315 | **−0.840** | 4.2×10⁻⁸⁵ |
| Double bass | Orchidea | 136 | **−0.618** | 1.2×10⁻¹⁵ |
| Double bass | IOWA | 287 | **−0.046** | 0.44 n.s. |

Near-perfect monotone thinning on viola; very strong on violin and cello. **Iowa double bass is the structural exception:** ρ ≈ 0. That is not a measurement failure. The bass string table (Section 8) shows the *highest* string (G) is the *densest*, so string identity and pitch cancel inside a compressed MIDI range (roughly E1–G4). Orchidea bass, pooled across strings, recovers a medium-strong negative ρ (−0.62).

---

## 8. Iowa string (eligible only on Iowa)

Kruskal–Wallis on 16 Iowa instrument×string cells: **H = 512.06, *p* = 1.6×10⁻⁹⁹, ε² = 0.433** (*n* = 1165). String is the second-largest designed factor after register.

### 8.1 Median EWSD by string × dynamic

**Violin (G D A E)** — lowest string densest; ff raises G/D/A; E string stays thin.

| String | pp | mf | ff |
|---|---:|---:|---:|
| G | 16.31 (*n*=29) | 17.81 (25) | **23.55** (25) |
| D | 12.01 (25) | 14.09 (25) | 18.90 (24) |
| A | 9.51 (25) | 11.66 (24) | 16.18 (23) |
| E | 7.71 (28) | 10.34 (30) | 8.48 (32) |

**Viola (C G D A)** — C string is a different instrument acoustically.

| String | pp | mf | ff |
|---|---:|---:|---:|
| C | 20.90 (25) | 25.59 (24) | **27.66** (23) |
| G | 17.32 (24) | 16.96 (25) | 16.92 (26) |
| D | 14.46 (21) | 9.93 (26) | 11.36 (25) |
| A | 7.57 (24) | 7.38 (24) | 7.53 (26) |

**Cello (C G D A)** — C and G sit on a high plateau (mf/ff ~38); D and A sit near 19–20 and barely move with dynamic. **G ff is missing.**

| String | pp | mf | ff |
|---|---:|---:|---:|
| C | 27.68 (23) | **38.60** (26) | 37.29 (26) |
| G | 25.12 (25) | 38.27 (21) | *missing* |
| D | 20.24 (24) | 19.98 (25) | 19.98 (25) |
| A | 19.18 (25) | 18.57 (25) | 19.33 (25) |

**Double bass (E A D G)** — **G (highest string) is densest.** E (lowest) is mid-pack and dynamically flat.

| String | pp | mf | ff |
|---|---:|---:|---:|
| G | 29.58 (25) | 28.09 (17) | **31.87** (25) |
| D | 21.82 (25) | 24.70 (25) | 26.85 (25) |
| A | 17.90 (25) | 18.69 (25) | 21.14 (26) |
| E | 22.19 (23) | 22.77 (23) | 20.66 (23) |

### 8.2 Acoustic reading of the string tables

1. **Violin / viola / cello** obey the textbook string-family gradient: lowest string → highest EWSD. That is the same physical mechanism as the MIDI law (more harmonic room + thicker core).
2. **Viola C** (~21–28) approaches **cello D/A** (~19–20) and is far above viola A (~7.5). Treating “viola” as one timbre in a density study is misleading; the C string is a low-string object.
3. **Cello C/G mf–ff (~38)** are the densest designed cells in the Iowa corpus. They also produce the MAD outliers (open C2).
4. **Iowa bass inverts the string gradient.** G > D > E ≈ A. Possible acoustic contributors, all score-internal: (a) orchestral-bass G is still a low *f*₀ with a long partial stack; (b) the E string is often darker / more fundamental-dominated (lower EWSD after the PR penalty); (c) Iowa bass pitch span per string is narrow, so string identity dominates MIDI. This is why Iowa bass Spearman is null.

---

## 9. Dynamic

Pooled across instruments, dynamics differ statistically but the effect is tiny:

- KW: **H = 13.30, *p* = 0.0013, ε² = 0.0076**
- Medians: pp 18.60 · mf 19.41 · ff 20.24
- ff vs pp: Holm *p* = 0.001, |δ| = 0.13 **negligible**
- mf vs pp: Holm *p* = 0.029, |δ| = 0.09 **negligible**
- ff vs mf: n.s.

Rank-variance share of dynamic: **0.7%**.

Within instrument × collection (one-sided MWU, Cliff’s δ):

| Cell | Contrast that matters | δ magnitude | Medians |
|---|---|---|---|
| Iowa violin | pp < mf < ff | small (ff>pp \|δ\|=0.31) | 11.18 → 13.31 → 16.18 |
| Iowa cello | mf > pp | small | 22.27 → 25.45; ff does not exceed mf |
| Iowa bass | ff > pp | small | 21.55 → 25.52 |
| Orchidea bass | mf > pp | small | 21.51 → 26.74 |
| Iowa viola | none | negligible | 15.89 / 14.86 / 13.58 (slightly *down*) |
| Orchidea viola | none | negligible | ~16.8 / 16.8 / 16.4 |

**Acoustic reading.** Dynamic is not a global density driver on F-049. It appears where bow force actually recruits partials on a given string (Iowa violin G/D/A; cello C/G). On viola A and cello D/A the envelope scales without changing the participation-ratio structure, so EWSD stays flat. That is a feature of the construct (anti-concentration penalty), not a bug in the samples.

---

## 10. Rank-variance partition (Type I on ranks)

Order: instrument → collection → dynamic → register.

| Factor | % of rank SS |
|---:|---:|
| Register | **26.5** |
| Instrument | **19.9** |
| Dynamic | 0.7 |
| Collection | 0.3 |
| Residual | **52.6** |

Residual is large because string (Iowa-only, not in this sequential model), note-to-note residual, and the instrument×register confounding remain. The designed message is still clear: **pitch/register first, instrument family second, collection and dynamic essentially null.**

The instrument 19.9% is partly a tessitura proxy (Section 7.2). After pitch matching, family differences shrink sharply.

---

## 11. Outliers (MAD *z* ≥ 3.5 within instrument × collection × dynamic)

26 notes (1.7% of eligible). They concentrate on **Iowa cello C**, especially C2 / C♯2 (EWSD up to 96.74, *z* ≈ 4.6–5.9). These are the same open-string / floor-adjacent cells that the tuba validation already treated as harvest-risk. They do **not** move Kruskal–Wallis or Cliff’s δ (rank methods). They do move raw means; that is why medians and trimmed means are the reported locations.

---

## 12. Conclusions (score-only, this corpus)

1. **Two families.** Cello ≡ double bass (median ≈ 23.2, δ ≈ 0). Viola ≡ violin (13.3–15.7, δ = 0.08, n.s.). Low vs high family: medium-to-large δ (0.45–0.60).
2. **Pitch is the law.** Register ε² = 0.61; Spearman ρ from −0.84 to −0.97 on violin, viola, cello. Pitch-matched C4–B4 medians of all four instruments sit in a ~4-point band.
3. **Iowa string is real and eligible.** ε² = 0.43. Violin/viola/cello: lowest string densest. Viola C behaves like a low string. Cello C/G mf–ff are the densest designed Iowa cells.
4. **Iowa bass is the exception.** G string densest; MIDI–EWSD ρ ≈ 0. Do not pool Iowa bass notes across strings if the scientific question is pitch.
5. **Collection is not a factor.** Iowa vs Orchidea contrasts are negligible where both exist. Violin Orchidea and cello Orchidea pp/mf are missing and must be filled before any collection claim on those instruments.
6. **Dynamic is statistically detectable and scientifically small** (ε² = 0.008), except Iowa violin (ordered pp < mf < ff, still only a small δ).

### Practical use of the score on CORDAS_2

- Cross-instrument ranking should be **pitch-matched** (or register-stratified). Unmatched medians mostly restate tessitura.
- Iowa analyses that care about string must stay on the per-string folders; Orchidea cannot support a string factor from these workbooks.
- Do not interpret a higher Iowa cello C2 as “better” or “worse” — it is the expected open-C density plus residual floor risk.
- The missing six workbooks should be generated with the same Stage 1+2 profile before any paper-style collection comparison that includes violin or cello Orchidea.

---

## 13. Caveats

- Score-only. No listening, no other Stage 3 columns, no CI-column meta-analysis (`EWSD_score_acoustic_balanced_ci_*` unused).
- Eligibility gate followed the project protocol; the 26 “ineligible” rows here are empty sheet rows, not rejected notes.
- Orchidea string IDs in filenames were not mapped.
- Iowa cello G ff is absent; cello C/G vs D/A contrast at ff is incomplete.
- Violin Orchidea is entirely absent; all violin findings are Iowa.
- Sequential rank SS is Type I and order-dependent; register would absorb still more if entered first (it is already the largest term).
- Cliff’s δ uses Romano thresholds; they are conventional, not acoustic cut-points.
- Corpus is arco / ordinario sustains only.
