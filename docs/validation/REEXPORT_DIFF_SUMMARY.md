# Re-export diff summary (`v4.2.3`)

Batch: 20 August 2026, 18:07–19:47 UTC. Code commit **`1db94e1`**
(`v4.2.3`). Production profile
`wf=log|dst=-90.0|ceil=20000.0|fft=fixed|seg=sustain_primary_stable_diagnostic|elig=1`
on every new manifest. `verify_corpus` **ok** on all seven trees.

Pretags in `pretag_evidence/` are SustainStable Test-tree at `6b0e51a`.
Every Δ below **mixes** the R-era code/policy change **and** the
full-`_Sustains` vs Stable cut. That mix is the explanation attached to
every |Δ| > 10 % row. The bootstrap / F-047 / F-048 / F-049 algebra was
not retuned.

Cello *ff* uses `_Sustains` leaves under
`D:\CORDAS_3\CELLO\IOWA_Cello_Arco\CELLO\IOWA_cello_arco_ff`
(C, G, D, A). No pretag research workbook for that cut.

## 1. One commit, one profile

| Corpus | n | `code_commit` | `fft` / n_fft / hop | `seg` | `verify_corpus` |
|--------|--:|---------------|---------------------|-------|-----------------|
| trombone pp | 33 | `1db94e1` | fixed / 8192 / 1024 | sustain_primary_stable_diagnostic | ok |
| trombone mf | 33 | `1db94e1` | fixed / 8192 / 1024 | sustain_primary_stable_diagnostic | ok |
| trombone ff | 33 | `1db94e1` | fixed / 8192 / 1024 | sustain_primary_stable_diagnostic | ok |
| flute pp | 37 | `1db94e1` | fixed / 8192 / 1024 | sustain_primary_stable_diagnostic | ok |
| flute mf | 38 | `1db94e1` | fixed / 8192 / 1024 | sustain_primary_stable_diagnostic | ok |
| flute ff | 39 | `1db94e1` | fixed / 8192 / 1024 | sustain_primary_stable_diagnostic | ok |
| cello ff | 101 | `1db94e1` | fixed / 8192 / 1024 | sustain_primary_stable_diagnostic | ok |

`code_dirty` is true on all seven: the working tree held R6 runner /
gitignore files. That is **not** an analysis-code edit. Package field
is still `4.2.1` (same as the `v4.2.2` tag-only convention);
`git_describe` is `v4.2.3-dirty`.

Halt threshold (|Δ EWSD| > 25 % on > 5 % of matched notes) **fired** on
all six pretag-matched corpora. The batch was completed at the user's
request to finish R6. Three worst notes per corpus are below. EPD is
flat on those notes except flute *pp* B6.

## 2. Diff vs pretag (EWSD / EPD / SNR)

Pattern: **EPD nearly unchanged**; **EWSD up** (recovered high
partials + full cut + energy rebase). No remaining G3→G♯3 *tier* step
on trombone pp/mf (19.98 / 19.83 and 39.55 / 38.32). Trombone *ff*
G3→G♯3 is 93.94 → 76.00 (register thinning, both at n_fft=8192).

| Corpus | matched | \|Δ EWSD\| > 25 % | Three worst EWSD Δ (EPD Δ) |
|--------|--------:|------------------:|----------------------------|
| trombone pp | 32 | 9 (28 %) | C♯4 +46 % (+0.9 %); F4 +43 % (−0.3 %); A♯3 +42 % (+0.5 %) |
| trombone mf | 33 | 13 (39 %) | C5 +60 % (−5.1 %); F♯4 +36 % (+0.8 %); B3 +34 % (−3.4 %) |
| trombone ff | 33 | 8 (24 %) | C5 +50 % (−7.4 %); F♯4 +30 % (−5.3 %); C4 +29 % (−4.9 %) |
| flute pp | 37 | 32 (86 %) | B6 +354 % (**EPD +475 %**); F6 +229 % (−1.6 %); G♯6 +172 % (−2.2 %) |
| flute mf | 38 | 32 (84 %) | G6 +175 % (+1.0 %); A♯6 +160 % (−6.9 %); G♯6 +156 % (−3.2 %) |
| flute ff | 39 | 35 (90 %) | A♯6 +185 % (−3.6 %); B6 +183 % (−3.9 %); G6 +172 % (−1.7 %) |

Audit notes for the three largest per corpus:

- **Trombone:** loud / mid-high notes gain EWSD; EPD stays inside 8 %.
  Full sustain vs Stable + D1/D2 recovered partials. SNR on the worst
  three is 50–64 dB (`estimated_snr_db`).
- **Flute F6 / G♯6 / G6 / A♯6 / B6:** EWSD rises sharply; EPD stays
  near 1 except **flute pp B6** (EPD 2.69 → 15.49). B6 is the one EPD
  break; also `EPD > validated H` (H=2, EPD=15.49) with B5 (H=3,
  EPD=13.87). Treat B5/B6 *pp* as appendix outliers, not as a density
  ladder.
- **Boundaries (new, fixed 8192):** trombone pp G3/G♯3 = 19.98 / 19.83;
  mf 39.55 / 38.32; ff 93.94 / 76.00. Flute C5/F6 = 9.71 / 8.46 (pp),
  17.35 / 7.71 (mf), 17.05 / 9.13 (ff).

## 3. CORDAS predictions (unchanged script)

`D:\CORDAS_2\reports\analyze_ewsd_balanced.py` was run **unchanged** on
the existing 54 CORDAS_2 research workbooks (not re-exported in this
batch).

| Prediction | Pretag | This run (same script, same trees) | EPD sidecar (same KW/Spearman, not a script edit) |
|------------|-------:|-----------------------------------:|--------------------------------------------------|
| Dynamic KW ε² | 0.0076 | **0.00756** (H=13.30, p=0.0013, n=1497) | **0.0132** (H=19.71, p=5.2e-5, n=1350) |
| Iowa bass ρ(MIDI, ·) | −0.046 | **−0.046** (n=287, p=0.44) | **−0.013** (p=0.83) |
| Orchidea bass ρ (context) | −0.62 | **−0.618** | not recomputed |

**Finding.** On the CORDAS_2 trees the dynamic effect stays negligible
on both EWSD and EPD. Iowa bass ρ does **not** move toward Orchidea
−0.62. The artefact explanation is **not** confirmed on that corpus.

**New cello *ff* (`v4.2.3`, 101 eligible notes):**
ρ(MIDI, EWSD) = **−0.579** (p=2.3e-10); ρ(MIDI, EPD) = **−0.465**
(p=9.8e-7). That is a publishable register slope on the final
instrument for cello *ff* alone. Dynamic ε² cannot be recomputed from
*ff* only (cello pp/mf `_Sustains` exist on disk but were not in the
seven-corpus list).

## 4. Eligibility and flags (thesis appendix)

All seven new corpora: **100 %** `ewsd_primary_analysis_eligible`.
**No** `stable_segment_unrepresentative` flags. The expected low-string
G2 / top *pp* flute ineligible cluster **did not appear** on the full
`_Sustains` + sustain-primary policy.

Appendix exceptions (not swept):

| Note | Corpus | Flag |
|------|--------|------|
| B5 | flute pp | EPD (13.87) > validated H (3) |
| B6 | flute pp | EPD (15.49) > validated H (2); EPD Δ vs pretag +475 % |
| C4 after B3 | flute pp | one pitch-mono rise whose CIs do not overlap (item 3–4) |

## 5. Outputs (machine-local, not committed)

- `...\analysis_results_v4.2.3\run_manifest.json` beside each corpus
- `docs/validation/_r6_reexport/finish.json`, `halt_*.json`, `summary.json`
