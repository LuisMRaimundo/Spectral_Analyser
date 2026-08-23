# Adoption checklist — cleanup tree → canonical

This file is the author's manual runbook. This task does **not** adopt,
merge, or push. Do not run these steps unless you have decided to take
this local tree into the canonical repo.

**Local tree:** `E:\PYTHON CODES\Pacore de preparação dos sons\Spectral_Analyser-git_v2.22.08.26`  
**Branch:** `cleanup/repo-hygiene` (local only; never published)  
**Canonical (do not touch from the cleanup agent):** `E:\PYTHON CODES\Pacore de preparação dos sons\Spectral_Analyser-git`  
**Remote:** `https://github.com/LuisMRaimundo/Spectral_Analyser.git`

## Standing STOP (must be resolved before a “suite green” tag)

`tests/phase_32/test_acd_merge_strategy.py::test_merge_strategy_cache_and_tolerance`
is red by policy, not by hygiene.

- Round-3 record (authoritative): wander 2.74 % + 1 pp, rounded up → **0.04**.
  Constant `REAL_NOTE_FFT_TIER_ACD_REL_TOL = 0.04` is correct.
- Official regenerator `test_generate_merge_strategy_tier_sweep` was re-run.
  Winner `fixed_erb_grid` measured max |Δ%| = **3.26345 %**. The cache writer
  stores `enforced_relative_tolerance = ceil(3.26+1)/100 = 0.05`.
- The cache **cannot** satisfy 0.04 without loosening the constant. The
  constant was **not** loosened. Do not hand-edit
  `tests/phase_32/golden/acd_merge_strategy.json`.
- Therefore the local tag `v4.7.0-instrument-final` with the prescribed
  message (“suite green”) was **withheld**. Create it only after this test
  is green, or after you explicitly accept a different tag message.

## Commits on this tree since canonical diverged (`45c40bb`)

`45c40bb` is the last shared `main` commit before F-061 / cleanup work.
Canonical `main` later moved independently (F-061 candidate-record
correction and merge). This list is the cleanup-tree delta only:

| SHA | Subject |
|-----|---------|
| `0968082` | Add F-061 `spectral_mass` as a derived Stage 3 column so mass is not read off acoustic-balanced EWSD. |
| `10b7e35` | Remove unreferenced Backup/ weight and park the PyQt GUI in attic/, without changing exported numbers. |
| `4084693` | Retire expansive weight-function labels from the Tk dropdown and mark superseded columns, without changing computed values. |
| `1f5e675` | Add a Research_Core citation sheet and classify every inventoried export column, without changing existing numeric cells. |
| `b80838a` | Reclassify the 202 COL: residue into provenance, diagnostic, and deprecated, without changing exported numbers. |
| `3c79628` | Assign F-062–F-068 and reuse existing MIR/entropy/B/observation ids so the citable COL: residue has real contracts. |
| `468b980` | Close the three triage decision-doc items with F-041/F-069/F-070 stamps and the `total_component_energy` misnomer, without changing exported metrics. |
| `a3c39dc` | Gate F-062–F-068 companion stamps on the research export and record the 2000 Hz F-067 default. |
| *(this commit)* | Local 4.7.0 bump + this checklist. No remote operations. |

Confirm the final SHA with `git log -1 --format=%H` on
`cleanup/repo-hygiene` after this file lands.

## Task-0 fixture (numeric invisibility)

Baseline (outside the repo):
`E:\PYTHON CODES\Pacore de preparação dos sons\cleanup_baseline.xlsx`

Frozen Stage-2 inputs (do **not** `--rebuild-inputs`):
`E:\PYTHON CODES\Pacore de preparação dos sons\_cleanup_fixture_work`

```
set PYTHONPATH=<this-repo-root>
python -m tools.validation.export_cleanup_fixture ^
  "<parent>\cleanup_after_adopt.xlsx" ^
  --work-dir "<parent>\_cleanup_fixture_work"
python -m tools.validation.diff_workbooks ^
  "<parent>\cleanup_baseline.xlsx" ^
  "<parent>\cleanup_after_adopt.xlsx" ^
  --allow-sheet Research_Core ^
  --allow-column odd_even_harmonic_energy_ratio_formula_id ^
  --allow-column odd_even_harmonic_energy_ratio_formula_version ^
  --allow-column low_mid_energy_ratio_formula_id ^
  --allow-column low_mid_energy_ratio_formula_version ^
  --allow-column harmonic_density_weight_formula_id ^
  --allow-column harmonic_density_weight_formula_version ^
  --allow-column inharmonic_density_weight_formula_id ^
  --allow-column inharmonic_density_weight_formula_version ^
  --allow-column subbass_density_weight_formula_id ^
  --allow-column subbass_density_weight_formula_version
```

Require `numeric_mismatches: 0` and `DIFF_OK`. Whitelisted extras are
`Research_Core`, stamp companion cells, and dictionary / provenance text.

## If and when you adopt into the canonical repo

Work in the **canonical** folder, not this cleanup copy. Pick one of the
two shapes below. Push and GitHub tag only if you intend to publish.

### Option A — fetch / merge this branch into canonical `main`

1. In the cleanup tree: confirm `git status` is clean and
   `git branch --show-current` is `cleanup/repo-hygiene`.
2. In the canonical tree: `git fetch` (or add this folder as a local
   remote: `git remote add cleanup "<cleanup-tree>"` then `git fetch cleanup`).
3. Review `git log main..cleanup/repo-hygiene` against the table above.
4. Reconcile the canonical F-061 candidate-record correction
   (`17a575a` / merge `39dc8a7`) with cleanup's older F-061 text in
   `CHANGES.md` / `spectral_mass.py` — keep the corrected wording.
5. Merge or cherry-pick. Resolve conflicts yourself. Do not force-push
   `main`.
6. Run the fast suite: `pytest tests -q -m "not slow and not live_audio"`.
7. Re-run the Task-0 fixture diff (numeric 0).
8. If you publish: `git push origin main`.
9. Tag only when the suite is actually green:
   `git tag -a v4.7.0-instrument-final -m "Instrument phase complete: all columns classified, all metrics identified, suite green."`
   then `git push origin v4.7.0-instrument-final`.

### Option B — replace canonical working tree with this tree

1. Backup the canonical folder (copy or `git bundle`).
2. Replace the working tree contents with this cleanup tree, keeping the
   canonical `.git` **or** retarget `origin` to
   `https://github.com/LuisMRaimundo/Spectral_Analyser.git`.
3. Same review, F-061 wording reconciliation, suite, fixture, push, and
   tag steps as Option A.

## What this task already did (do not repeat from the cleanup agent)

- No push. No fetch of GitHub. Canonical folder not modified.
- Decision-doc closures committed locally (`468b980`).
- Stamp gate committed locally (`a3c39dc`).
- Package version in this tree set to **4.7.0**.
- Fast suite on this tree (after the 4.7.0 bump): **1595 passed**,
  **1 failed** (`test_merge_strategy_cache_and_tolerance`), 2 skipped,
  3 xfailed, 29 deselected (`slow` / `live_audio`).
- Local annotated tag withheld because the fast suite is not all-green
  (merge-strategy tolerance STOP).
