# Evidence-anchored rating — post-closure build (tag `v4.2.0`)

Judgement document with rules, 20 August 2026. Not a listener test, not a
marketing scorecard, and **not** the freeze acceptance record.

**Rated tree:** `main` at `aa24de8` (WP6 merge). Git tag `v4.2.0` points at
`8652810` (WP5 merge, two commits earlier). The dossier on `aa24de8` is
included in the `v4.2.0` column; the code identity is the tag.

F-042 / F-047 / F-048 / F-049 algebra is unchanged across this line
(`CHANGES.md` WP1–WP6; `CANONICAL_DENSITY_FORMULA_VERSION` still
`v5_apply_density_metric_adapted_v6_2_psd`).

---

## Commit mapping (corrected)

| Column in this document | Git identity | What that commit actually is |
|-------------------------|--------------|------------------------------|
| **v4.0.3 / run-2** | Análise 2, 18 Aug 2026 (`docs/validation/VERSION_RATING_IOWA_TUBA.md`) | Uncapped high-*n* match on SustainStable. Floor harvest. |
| **v4.1.0 / Análise 3** | 19 Aug 2026, policy v2 (`745c259` / Análise 3 tree) | Spacing cap + body stop. Exclusive assignment **not** yet on. |
| **`70525e3`** | `70525e3` — *Assign each spectral peak to one harmonic slot…* | Exclusive assignment + validated-partial gating **only**. Phases A–I are **later**. |
| **`6b0e51a`** | Merge of PR #76 | Phases A–I **plus** D6 (PSD energy / `D_k` n_fft-norm / `fft_policy=fixed`). Residual exclusion still ENBW. **D1–D5 not yet in.** |
| **`v4.2.0`** | Tag `v4.2.0` = `8652810`; dossier `aa24de8` | D1–D5 (`ec0a99a`) + WP1–WP6. |

**Correction.** The prompt’s five columns are kept. D1–D5 (`ec0a99a`, PR #75)
sit **between** `6b0e51a` and the tag. They are scored in the `v4.2.0`
column, not as a sixth epoch. Phases A–I are in `6b0e51a`, not in `70525e3`.
The earlier 1–100 sheet (`VERSION_RATING_IOWA_TUBA.md`) stopped at
`70525e3` and is deprecated.

---

## Mandatory preamble

**Fraction of on-disk corpora produced by v4.2.0.** Zero. A search for
`analysis_results_v4.2.0` under `D:\METAIS`, `D:\MADEIRAS`, and `D:\CORDAS_2`
returned no directories. `docs/REEXPORT_RUNBOOK.md` and
`docs/POST_FREEZE_BACKLOG.md` state that the one-re-export-per-corpus step
was **not** run in WP5/WP6. Every live workbook cited below is a **pre-tag**
artefact.

**Evidence actually examined.** Repository documents:
`UPGRADE_PROGRAMME_STATUS.md`, `CONSTRUCT_VALIDATION_SYNTHETIC.md`,
`TROMBONE_AS2_DEFECT_FIX_DIFF.md`, `RESOLUTION_DEPENDENCE_DIAGNOSIS.md`,
`SEGMENTATION_CASE_STUDY_G2.md`, `POST_FREEZE_BACKLOG.md`,
`REEXPORT_RUNBOOK.md`, `TUBA_PP_REEXPORT_DIFF.md`,
`EWSD_CONSTRUCT_VALIDITY.md`, `CONSTANTS_PROVENANCE.md`, `REFERENCES.md`,
`FORMULA_VALIDATION_STATUS.md`, `CHANGES.md`, `README.md`,
`EXPORT_COLUMN_DICTIONARY.md`. Code/tests:
`tests/phase_14`–`phase_28`, `tests/phase_11` EWSD goldens,
`tests/phase_23`, `tests/phase_24`, `tests/phase_25`,
`verify_export.py`, `tools/verify_corpus.py`, `production_policy.py`.
This session: `pytest --collect-only` → **1441** tests;
`tests/phase_27` + `phase_21` + `phase_18` + `phase_11` goldens +
`phase_26` → 55 passed; `tests/phase_28` → 6 passed. **Not** run: the
full 1441-test suite. CI on `main` after PR #82 was **in progress** at
writing; the PR #81 and #80 push runs were **cancelled**; PR #79 failed
(pre-WP4). Exported artefact read: `D:\CORDAS_2\reports\EWSD_acoustic_balanced_CORDAS_report.md`
(54 pre-tag research workbooks). Limits: no v4.2.0 Stage 1 tree; no
live flute residual workbook; no trombone 32-note dynamic table in the
repo; local G3 live tests are recorded as failing, not re-run here.

**Unknown-unknowns discount.** A build previously self-rated **92 / 96**
at `70525e3` (`VERSION_RATING_IOWA_TUBA.md`) still had the G3/G♯3
window-step defect (`RESOLUTION_DEPENDENCE_DIAGNOSIS.md`: EWSD 91.6 →
66.3 following n_fft, not the note). This kind of score measures
**known** defects only. Every dimension below is reduced by **5 points**
after caps, stated as `−5 UU`. That discount is a floor, not a claim
that five points cover the next invisible defect.

**Two standing ceilings (not softened).** (a) EWSD is an acoustic
construct only — `README.md`, `EWSD_CONSTRUCT_VALIDITY.md`,
`PERCEPTUAL_PROTOCOL.md` (scaffold, no data). (b) Any corpus not
re-exported under `v4.2.0` is **non-citable**, whatever this score says.

---

## Caps applied

No dimension may exceed **90** while any item on its evidence list is
failing, pending, or unverified.

| Dimension | Cap trigger on `v4.2.0` |
|-----------|-------------------------|
| Software | Full-suite CI on the tagged `main` not verified green (pending / cancelled). Live G3 tests fail locally (`POST_FREEZE_BACKLOG.md`). |
| Acoustics | Live G3 `core_H` 4096 vs 8192 still ~20 % (`POST_FREEZE_BACKLOG.md`). Live flute residual **not assessable**. Zero v4.2.0 corpus re-exports. |
| Musicology | Trombone pp&lt;mf&lt;ff “32/32” **not found** in repo or artefacts examined. CORDAS workbooks are pre-tag. Perceptual study absent → additional ceiling **80**. |
| Bibliographic | Sethares implemented (`dissonance_models.py`) but **absent** from `REFERENCES.md`. Perceptual standard exists and is not followed. |
| Statistics | CORDAS report unused CI columns; no v4.2.0 rerun to test the predictions. |
| Documentation | `UPGRADE_PROGRAMME_STATUS.md` WP6 row still says “in this PR” after merge `aa24de8`. |

Documentation is scored on its own, then **folded into software** as
`SW_used = 0.80 × SW + 0.20 × Docs` (after the −5 UU). Overall weights
use `SW_used`, not the standalone software column.

---

## Dimension 1 — Software engineering

**Evidence list.** 1441 collected tests (`pytest --collect-only`, this
session). CI matrix 3.10 / 3.11 (`.github/workflows/ci.yml`). Peak-bin
uniqueness: `data_integrity.validate_unique_peak_bin_assignment`,
`tests/phase_18`. Residual-region closure: `tests/phase_25`.
`accepted_slots_above_body_stop = 0`: D1/WP2 table and Phase C.
Provenance: `analysis_provenance.py`, `verify_export.py` (run-2 →
`not comparable (pre-exclusive-assignment)`, Phase E). Profile ids:
`production_policy.build_analysis_parameter_profile_id` (`fft`/`seg`/`elig`).
Corpus check: `tools/verify_corpus.py` (`tests/phase_27`). Schema:
`tests/phase_19`. Manifest + runbook: `run_manifest.py`,
`docs/REEXPORT_RUNBOOK.md`. WP4: eight density CI failures fixed
(`CHANGES.md` WP4, PR #80).

| Version | Raw | Cap | −5 UU | Score |
|---------|----:|----:|------:|------:|
| v4.0.3 / run-2 | 68 | — | 63 | **63** |
| v4.1.0 / Análise 3 | 76 | — | 71 | **71** |
| `70525e3` | 80 | — | 75 | **75** |
| `6b0e51a` | 86 | — | 81 | **81** |
| `v4.2.0` | 88 | 90 | 83 | **83** |

v4.0.3 already had a large phase-1–12 suite and v4.0.3 schema hygiene
(`CHANGES.md` export-schema sweep) but no exclusive-assignment invariant,
no `verify_export`, no run manifest, no production-policy profile id.
v4.1.0 adds low-f₀ policy tests (`tests/acoustic_validity`). `70525e3`
adds exclusive assignment. `6b0e51a` adds A–I + D6 tests
(`tests/phase_14`–`21`, `tests/phase_24`). `v4.2.0` adds
`verify_corpus`, manifest FFT/segment fields, WP4 gate opt-out, and
phase_27/28. It does **not** get 90: tagged-`main` CI is unverified,
and the live G3 tests remain red on the author machine.

---

## Dimension 2 — Acoustical validity

**Evidence list.** Run-2 / Análise 3 / `70525e3` A2 table:
`VERSION_RATING_IOWA_TUBA.md` (archival numbers, used only as that
era’s measured A2). D6.1 swap:
`RESOLUTION_DEPENDENCE_DIAGNOSIS.md` (G3 91.64 @8192 vs 71.13 @4096).
D6.2 synthetic tone+pink energy ratios within 2 %:
`tests/phase_24`, status table. WP1 synthetic: single sinusoid residual
share &lt; 1 % at 2048–16384; tone+pink within 2 % of GT; region
invariant (`tests/phase_25`). WP1 live swap table (same file, § WP1):
G3 `core_H` 0.9969 vs 0.9993 (0.24 %); residual share &lt; 1.1 %.
A♯2 census: 78 → 89 → **92** (`TROMBONE_AS2_DEFECT_FIX_DIFF.md`).
Tuba A2: 8 validated, EPD **3.77**, EWSD **16.11**. Phase I: all 12
constructs, N ±1, B ±10 %, EPD ±10 %, confirmed-I exact
(`CONSTRUCT_VALIDATION_SYNTHETIC.md`). Live G3 3 % tolerance: **fails**
(`POST_FREEZE_BACKLOG.md`). Live flute residual: **not assessable**
(no v4.2.0 flute workbook). Trombone A♯2 residual *share* is not in
the WP2 table — only census / EPD / EWSD — so “plausible *ff* brass
residual” is **not assessable** as a residual-energy claim.

| Version | Raw | Cap | −5 UU | Score |
|---------|----:|----:|------:|------:|
| v4.0.3 / run-2 | 52 | — | 47 | **47** |
| v4.1.0 / Análise 3 | 68 | — | 63 | **63** |
| `70525e3` | 74 | — | 69 | **69** |
| `6b0e51a` | 78 | 90 | 73 | **73** |
| `v4.2.0` | 84 | 90 | 79 | **79** |

v4.0.3 A2: 11 included harmonics (H1–8 + 109–111), EPD 24.60, peak-bin
fail (bin 4493 ×3). v4.1.0: included set H1–H8 but EPD still ~22.9 and
H110 still `strict_validated` above the stop. `70525e3`: EPD 3.77,
I share 0 %, invariant pass — first A2 that is safe to quote **as a
census**, not as a resolution-invariant energy partition. `6b0e51a`
fixes PSD/`D_k` on synthetics and documents that the live G3 step
still follows the window. `v4.2.0` WP1 moves the descriptor-level
swap (residual &lt; 1.1 %, step no longer follows the window) and
restores A♯2 to 92 validated. The live 3 % `core_H` G3 test still
fails; that is why acoustics cannot clear 90.

---

## Dimension 3 — Musicological usefulness

**Evidence list (what the *tool* enables).** Production policy:
sustain primary, stable diagnostic (`production_policy.py`,
`SEGMENTATION_CASE_STUDY_G2.md`: 43 vs 16 harmonics, 551 vs 140 Hz,
EWSD 50.2 vs 12.3, 1.75 frames). Eligibility + mixed-profile
`stage3_issue` (`tests/phase_26`). Cross-instrument protocol:
`EWSD_CONSTRUCT_VALIDITY.md` § cross-instrument (same profile id,
pitch-matched, eligible only). CORDAS report
(`D:\CORDAS_2\reports\EWSD_acoustic_balanced_CORDAS_report.md`): 1497
eligible rows, Iowa violin pp&lt;mf&lt;ff (small δ), register ε² = 0.61
— **pre-tag workbooks, SustainStable trees, not v4.2.0, not citable
for a paper**. Trombone “pp&lt;mf&lt;ff 32/32” and “flute pp&lt;{mf≈ff}”:
**not assessable** — no such table in the repository or in the
artefacts opened for this rating. Cello/strings: pending v4.2.0
re-export (`POST_FREEZE_BACKLOG.md`, runbook). Perceptual ceiling: 80.

| Version | Raw | Cap | −5 UU | Score |
|---------|----:|----:|------:|------:|
| v4.0.3 / run-2 | 42 | — | 37 | **37** |
| v4.1.0 / Análise 3 | 55 | — | 50 | **50** |
| `70525e3` | 58 | 80 | 53 | **53** |
| `6b0e51a` | 64 | 80 | 59 | **59** |
| `v4.2.0` | 72 | 80 | 67 | **67** |

v4.0.3 enables a false texture story (C1 at 183 harmonics). v4.1.0
enables a safer A2 comb but still leaks floor into EPD/pie. `70525e3`
enables quotable tuba A2 census. `6b0e51a` enables *policy* for
comparable FFT but live corpora remain tier-mixed unless re-run.
`v4.2.0` enables the intended workflow (fixed 8192/1024, sustain
primary, eligibility, `verify_corpus`) and documents why a stable G2
cut must not be the note score. It does **not** yet enable a citable
cross-instrument or cross-dynamic finding: that waits on the runbook
re-exports. Musicology is scored on enablement, then cut by the
acoustic-only EWSD disclaimer.

---

## Dimension 4 — Bibliographic / methodological alignment

**Evidence list.** Heinzel PSD/ENBW: `spectral_energy.py`,
`CONSTANTS_PROVENANCE.md` (`ENERGY_BASIS_PSD_PER_HZ`, `HANN_ENBW_BINS`),
`REFERENCES.md` (Harris 1978; Heinzel et al. 2002), formula F2.
Fletcher 1962: `inharmonicity_model.py`, F3,
`tests/phase_4/test_inharmonicity_recovers_known_B.py`. CFAR: F7,
`harmonic_peak_validation.py`, `tests/phase_11/test_cfar_detection.py`.
Participation ratio: F5, `density.py`. Aures roughness:
`mir_descriptors.py`, `REFERENCES.md` (Aures 1985). Sethares:
`dissonance_models.SetharesDissonance` (Sethares 2005 in the class
docstring) — **not** listed in `REFERENCES.md`. Provenance-classed
constants: `docs/CONSTANTS_PROVENANCE.md`. Missing standard: listener
validation (`PERCEPTUAL_PROTOCOL.md` scaffold only).

| Version | Raw | Cap | −5 UU | Score |
|---------|----:|----:|------:|------:|
| v4.0.3 / run-2 | 62 | — | 57 | **57** |
| v4.1.0 / Análise 3 | 68 | — | 63 | **63** |
| `70525e3` | 70 | — | 65 | **65** |
| `6b0e51a` | 78 | — | 73 | **73** |
| `v4.2.0` | 80 | 90 | 75 | **75** |

The jump at `6b0e51a` is Heinzel energy actually becoming the live
basis (D6.2), not a new citation. `v4.2.0` adds the main-lobe residual
footprint (`RESIDUAL_EXCLUSION_FOOTPRINT`, Harris 1978, class
`derived_from_window`). The ceiling is the unimplemented perceptual
standard plus the Sethares bibliography hole.

---

## Dimension 5 — Statistical / uncertainty treatment

**Evidence list.** Phase D: bootstrap CIs by default
(`tests/phase_17`). D4: unit / n / iterations / seed exported
(`tests/phase_23`; WP2 A2 CI `partials` / 25 / `wide`). WP3:
degenerate CI is NaN, never 0.0 (`production_policy.apply_degenerate_ci_nan`,
`tests/phase_26`). Eligibility: frames &lt; 8 or harmonics ≤ 2
(`MIN_INDEPENDENT_FRAMES`). Independent-frame accounting:
`ci_basis_frame_count`, `CI_BASIS_INDEPENDENT_FRAME_MIN` (10) for the
wide-flag path. `verify_corpus` fails a 0.0 degenerate CI
(`tests/phase_27`). CORDAS report §13: score-only; CI columns unused;
the 26 “ineligible” rows are empty sheet padding, **not** the WP3
gate. Rerun prediction (not executed): CORDAS `_Sustains_Stable` trees
will produce `ewsd_primary_analysis_eligible=False` and
`stable_segment_unrepresentative=True` on G2-like cuts
(`SEGMENTATION_CASE_STUDY_G2.md`); Iowa cello C2 MAD outliers
(§11 of that report) are harvest-risk and must be re-judged after a
fixed-8192 Stage 1; mixed n_fft / mixed profile ids must fail
`verify_corpus` / `stage3_issue`.

| Version | Raw | Cap | −5 UU | Score |
|---------|----:|----:|------:|------:|
| v4.0.3 / run-2 | 38 | — | 33 | **33** |
| v4.1.0 / Análise 3 | 42 | — | 37 | **37** |
| `70525e3` | 45 | — | 40 | **40** |
| `6b0e51a` | 72 | — | 67 | **67** |
| `v4.2.0` | 78 | 90 | 73 | **73** |

The large step is Phase D (in `6b0e51a`’s A–I bundle), not D6.
`v4.2.0` adds honesty (NaN, eligibility, corpus verifier) and does
not add a v4.2.0-corpus demonstration that those gates fire on
CORDAS. Machinery is scored, not interval width.

---

## Dimension 6 — Documentation and auditability (folded into software)

**Evidence list.** Can a reader reconstruct a number from tag +
manifest + dictionary? In principle yes for a **new** run:
`run_manifest.json` (commit, constants hash, profile id, FFT fields),
`docs/EXPORT_COLUMN_DICTIONARY.md`, `docs/METRIC_FORMULA_INDEX.md`,
`verify_export.py` / `verify_corpus.py`. In practice **no exported
v4.2.0 number exists** to reconstruct. `CHANGES.md` has one entry per
WP. Closure dossier: status table, G2 case study, backlog, freeze
rule in `README.md`. Stale cell: WP6 status still “in this PR”.
Deprecated 1–100 sheet is labelled DEPRECATED.

| Version | Raw | Cap | −5 UU | Score |
|---------|----:|----:|------:|------:|
| v4.0.3 / run-2 | 64 | — | 59 | **59** |
| v4.1.0 / Análise 3 | 72 | — | 67 | **67** |
| `70525e3` | 74 | — | 69 | **69** |
| `6b0e51a` | 80 | — | 75 | **75** |
| `v4.2.0` | 86 | 90 | 81 | **81** |

---

## Aggregation

`SW_used = 0.80 × Software + 0.20 × Documentation` (both after −5 UU).

Overall = `0.30 SW_used + 0.30 Acoustics + 0.20 Musicology + 0.10 Bibliographic + 0.10 Statistics`.

| Version | SW | Docs | SW_used | Ac. | Mu. | Bib. | St. | Arithmetic | **Overall** |
|---------|---:|-----:|--------:|----:|----:|-----:|----:|------------|------------:|
| v4.0.3 / run-2 | 63 | 59 | 62.2 | 47 | 37 | 57 | 33 | 0.30×62.2 + 0.30×47 + 0.20×37 + 0.10×57 + 0.10×33 = 18.66+14.10+7.40+5.70+3.30 | **49** |
| v4.1.0 / Análise 3 | 71 | 67 | 70.2 | 63 | 50 | 63 | 37 | 0.30×70.2 + 0.30×63 + 0.20×50 + 0.10×63 + 0.10×37 = 21.06+18.90+10.00+6.30+3.70 | **60** |
| `70525e3` | 75 | 69 | 73.8 | 69 | 53 | 65 | 40 | 0.30×73.8 + 0.30×69 + 0.20×53 + 0.10×65 + 0.10×40 = 22.14+20.70+10.60+6.50+4.00 | **64** |
| `6b0e51a` | 81 | 75 | 79.8 | 73 | 59 | 73 | 67 | 0.30×79.8 + 0.30×73 + 0.20×59 + 0.10×73 + 0.10×67 = 23.94+21.90+11.80+7.30+6.70 | **72** |
| `v4.2.0` | 83 | 81 | 82.6 | 79 | 67 | 75 | 73 | 0.30×82.6 + 0.30×79 + 0.20×67 + 0.10×75 + 0.10×73 = 24.78+23.70+13.40+7.50+7.30 | **77** |

The archival `70525e3` overall of **92**
(`VERSION_RATING_IOWA_TUBA.md`) is not reused. That number treated
unknown-unknowns as leftover stamp hygiene. The D6.1 table is the
load-bearing counter-example.

---

## Summary table (versions × dimensions × overall)

| Version | Software (folded) | Acoustics | Musicology | Bibliographic | Statistics | **Overall** |
|---------|------------------:|----------:|-----------:|--------------:|-----------:|------------:|
| v4.0.3 / run-2 | 62 | 47 | 37 | 57 | 33 | **49** |
| v4.1.0 / Análise 3 | 70 | 63 | 50 | 63 | 37 | **60** |
| `70525e3` | 74 | 69 | 53 | 65 | 40 | **64** |
| `6b0e51a` | 80 | 73 | 59 | 73 | 67 | **72** |
| **`v4.2.0`** | **83** | **79** | **67** | **75** | **73** | **77** |

---

## What moved and why (one step, one exhibit)

**v4.0.3 → v4.1.0 (+11).** Body stop + spacing cap put A2 on H1–H8
(`VERSION_RATING_IOWA_TUBA.md` A2 table: included 11 → 8). EPD stayed
~23; the stop was a count cut, not a consumer gate.

**v4.1.0 → `70525e3` (+4).** Exclusive assignment + validated-partial
gating: A2 EPD 22.9 → **3.77**, I amplitude 3.8 % → **0 %**, peak-bin
pass (`VERSION_RATING_IOWA_TUBA.md` A2 evidence table). First quotable
tuba A2 census.

**`70525e3` → `6b0e51a` (+8).** A–I (confirmed-I, persistence, high-*n*
guards, default CIs, `verify_export`, schema hygiene, φ, orchestrator
manifest, Phase I table) plus D6 PSD/`fft_policy=fixed`. Load-bearing
exhibit: `RESOLUTION_DEPENDENCE_DIAGNOSIS.md` D6.1.1 — the G3/G♯3
EWSD step **follows the window**. The previous 92 hid that.

**`6b0e51a` → `v4.2.0` (+5).** D1–D5 (A♯2 78 → 92) + WP1 main-lobe
residual (G3 residual share 5–25 % → &lt; 1.1 %,
`RESOLUTION_DEPENDENCE_DIAGNOSIS.md` WP1 table) + WP3 policy + WP4 CI
contract fixes + WP5 `verify_corpus` / runbook / tag + WP6 dossier.
Load-bearing exhibit: WP1 swap table in that same file. The remaining
gap is **zero v4.2.0 corpus re-exports** and the still-red live G3
3 % test.

---

## Doctoral percentile (informed estimate, not a measurement)

No listener validation exists. These ranges are comparanda, not a
census of doctorates or of PyPI audio libraries.

**Class A — research software accompanying music/acoustics doctorates.**
Typical state: unversioned MATLAB/Python scripts, no CI, no provenance
stamp, no formula index, no fail-closed export contract. This tree has
1441 collected tests, a 3.10/3.11 CI workflow, single-source version
stamping, a provenance-classed constant registry, a metric contract, a
phase-lettered `CHANGES.md`, and a freeze tag with a runbook. That
combination is rare in the class. **Percentile range: 90–97.** The
upper bound is not 99: CI on the tag is unverified here, and the
instrument has not yet produced a v4.2.0 citable corpus.

**Class B — published research software in audio/MIR generally.**
Comparanda: librosa (JOSS, public API, large test suite, community
regression), Essentia (papers + C++/Python, established evaluation
practice). `v4.2.0` is stronger than much *research-paper* companion
code on auditability (manifest, `verify_export`, `verify_corpus`,
formula F-numbers). It is weaker than those libraries on public
release discipline (merge CI cancelled/pending), on perceptual or
MIR-task evaluation (explicitly scaffold-only), and on independent
external use. **Percentile range: 60–78.** A journal software review
would still ask for a green CI badge on the tag and for at least one
frozen corpus export.

---

## Gaps marked, not filled

- Trombone dynamic 32/32 and flute pp&lt;{mf≈ff}: **not assessable**.
- Live flute residual “no longer pinned”: **not assessable**.
- A♯2 residual energy share: **not assessable** (census only).
- Full 1441-test pass on 3.10/3.11 for `aa24de8`: **pending**.
- v4.2.0 Stage 1–3 corpora: **zero**.

## Addendum — 20 August 2026 (P1–P3; scores not rewritten)

P1 live G3 swap on `aa24de8` **failed** the 3 % `core_H` tolerance
(0.9222 @8192 vs 0.7878 @4096, Δ 14.6 %). Evidence:
`RESOLUTION_DEPENDENCE_DIAGNOSIS.md` § P1,
`POST_FREEZE_BACKLOG.md`, `UPGRADE_PROGRAMME_STATUS.md` WP1 row now
**FAILED live**. The acoustics cap and the “WP1 live swap” claim are
**not** cleared. P5 (pretag archive) and P6 (runbook re-exports) were
**not** run. P4 (`v4.2.1`) was **not** cut.

P3 cleared two documentation gaps only: Sethares (2005) is in
`REFERENCES.md`; A♯2 post-fix `core_residual_energy_ratio` = 0.0959
is in `TROMBONE_AS2_DEFECT_FIX_DIFF.md` (pre column historical).

P4/P5 (same day, user override of the P1-fail stop): package **4.2.1**;
`v4.2.1` is the freeze reference (`v4.2.0` kept). Pre-tag trombone
32/32 and flute 36/37 + 22/38 are now **assessable** from
`docs/validation/pretag_evidence/` and `PRETAG_FINDINGS_SUMMARY.md`,
still **non-citable**. G2 pair, cello five-column sheet, and the
26-note segmentation comparison were not placed. P6 re-exports and
re-scoring, if wanted, remain separate exercises. The acoustics cap
from the live G3 fail is **not** cleared.

This rating is superseded by `UPGRADE_PROGRAMME_STATUS.md` for all engineering claims; the pass/fail table there is authoritative.
