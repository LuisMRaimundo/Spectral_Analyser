# Roughness kernel generations — archived-export migration

Three implementations have shipped under this package as **v4.4.0**.
`package_version` alone cannot tell them apart. Use `git_commit` /
`code_commit` (research Metadata / Analysis_Metadata) and the column
layout below. There is no per-column `metric_version` or `formula_id`
on the MIR roughness fields; F-037 lives in
`docs/METRIC_FORMULA_INDEX.md` and `metric_contract.py`, not in the
workbook cells.

The change between generations is **frequency-dependent**. It is not a
constant rescaling. Rank orderings across a multi-register corpus
differ. Do not multiply an archived column by a factor to “update” it.

## Generations

| Gen | Kernel | Current as of | Column behaviour |
|---:|---|---|---|
| 1 | `x = df / (0.25 f + 24.7)` (legacy conflated). Misattributed as Aures (1985). | Package ≤ 4.4.0 before commit `d615ebe` (PR #96, round 3). | Column `roughness_aures_1985` only. |
| 2 | `x = df / (0.25 · ERB(f))`, `ERB = 0.108 f + 24.7`. Renamed to Parncutt. | `d615ebe` through `c474c64` (round 3 merge; before round-4 Task 1). | Both `roughness_parncutt_kernel` and `roughness_aures_1985` written with the **same** ERB-basis number. |
| 3 | `x = df / (0.25 · Zwicker CB(f))` proposed default. `bandwidth_basis="erb"` still reproduces gen 2. | This branch, from `c474c64` (Task 1) plus the retired alias (this document). | Live value is `roughness_parncutt_kernel`. `roughness_aures_1985` is **NaN** on new exports. The Python name raises `NotImplementedError`. |

Primary-source confirmation of gen 3 against Plomp & Levelt (1965) is
**outstanding**. See [`ROUGHNESS_BANDWIDTH_BASIS.md`](ROUGHNESS_BANDWIDTH_BASIS.md).
The default may change after the author reads the published figures.

## How to identify an archived workbook

1. Read `package_version`. If it is not `4.4.0`, the file predates this
   trio; treat the roughness column as gen 1 unless a later commit is
   recorded.
2. Read `git_commit` / `code_commit`:
   - before `d615ebe` → gen 1
   - `d615ebe` … parent of `c474c64` → gen 2
   - `c474c64` and later → gen 3 numerics; after the alias-hardening
     commit the old column is NaN on **re-export**
3. If commit metadata is missing, inspect columns:
   - only `roughness_aures_1985` present → gen 1
   - both columns present and numerically equal → gen 2 (or a gen-3
     export from Task 1 before the alias was retired)
   - `roughness_parncutt_kernel` finite and `roughness_aures_1985` NaN
     → gen 3 after alias retirement
4. Magnitude check (20-partial 1/n at D3 ≈ 146.83 Hz): gen 1 ≈ 1.41,
   gen 2 ≈ 0.048, gen 3 ≈ 0.119. A factor of ~10–30 between gens is
   expected and **not** a load error.

Do not compare `roughness_aures_1985` from an archived file to
`roughness_parncutt_kernel` from a new run.

## Downstream consumers (audit, 2026-08-22)

No analysis outputs were modified. Sites that **would silently change**
if Stage 1 is re-run are flagged.

| Site | Role | Silent-change flag |
|---|---|---|
| `mir_descriptors.compute_mir_descriptors_from_spectrum` | Writes both keys. Live value is `roughness_parncutt_kernel`. Retired key is NaN. | **Yes** for the retired key (NaN vs old number). Live key changes with the kernel default (Task 1). |
| `mir_descriptors._roughness_aures_1985` | Retired callable. | No — now **raises**. |
| `proc_audio.py` (~11552) | Stage 1 MIR key list, including segmented suffixes. Copies whatever `compute_mir_descriptors_from_spectrum` returns. | **Yes** on re-analysis: new `roughness_parncutt_kernel` numerics; retired column becomes NaN. |
| `compile_metrics.py` `PHASE5_DESCRIPTOR_BASE_COLUMNS` (~660) | Stage 2 copies Stage 1 columns onto `Density_Metrics`. Not in `PCA_FEATURE_COLUMNS`. | **Yes** if Stage 1 is re-run, then compiled. Compile-only of archived workbooks keeps archived numbers. |
| `tools/export_research_density_workbook.py` | Stage 3 research export. No roughness-specific logic. | Pass-through only. Silent iff Stage 1/2 already changed. |
| PCA (`compile_metrics.PCA_FEATURE_COLUMNS`) | Density / discrete / entropy features only. Roughness is **not** a PCA input. | No. |
| Stage 3 ACD / EWSD (`tools/acd_research_integration.py`, `tools/ewsd_*.py`) | Independent of F-037. | No. |
| `dissonance_export.build_dissonance_correlation_matrix` | Sethares / Hutchinson–Knopoff, not the MIR kernel. | No. |
| Figure-generation scripts | None consume the roughness column. Validation figures are written by `tools/validation/roughness_bandwidth_basis.py` from the live kernel. | No archived-figure rewrite. |
| `tests/phase_5/test_descriptor_ranges.py` | Range checks. | Tests updated; not an analysis output. |
| `tests/phase_12/test_mir_descriptors_additional.py` | Schema + alias. | Tests updated. |
| `tests/phase_12/test_metric_contract_additional.py` | Registry includes both names. | Schema only. |
| `tests/perf/test_per_note_processing_budget.py` | Uses `_roughness_parncutt_kernel` only. | Numerics follow the default basis. |
| `metric_contract.py`, `metrics_dictionary.json` | Contract / dictionary. | Documentation. |
| `docs/METRIC_FORMULA_INDEX.md` F-037 | Formula row. | Documentation. |
| `docs/TECHNICAL_MANUAL_COMPLETE.md` §11 | Still described the gen-1 formula under the old name (updated in the alias commit). | Documentation was stale. |
| `docs/EXPORT_COLUMN_DICTIONARY.md` | Lists both headers in the compiled-sheet inventory. | Schema listing only. |
| `CHANGES.md` / `REFERENCES.md` / `pipeline.md` / `README.md` | Historical notes. | No outputs. |

## Recompute policy

Do not recompute the 49-note corpus until the author has signed off the
bandwidth basis in [`ROUGHNESS_BANDWIDTH_BASIS.md`](ROUGHNESS_BANDWIDTH_BASIS.md).
