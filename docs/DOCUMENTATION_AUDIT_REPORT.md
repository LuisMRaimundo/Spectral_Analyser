# Documentation audit report

**Repository:** SoundSpectrAnalyse-main_6  
**Audit date:** 2026-05-13  
**Scope:** Markdown documentation at repository root, under `docs/`, under `audio_analysis/`, and selected `scripts/` / `tests/` READMEs. **Excluded from the original audit scan:** `.venv/`, `.pytest_cache/`, `soundspectranalyse.egg-info/` (third-party / generated). The historical **`Backup/`** tree was excluded then and **removed entirely** in May 2026 housekeeping (see “Files deleted”).

**Method:** full-text scan for legacy canonical claims (e.g. `super_audio_analyzer` as sole Stage 1, `super_analysis_results.json` as required compile input, `minimum_harmonic_partial` as f0 source, bin centre as exported acoustic frequency, ambiguous nonharmonic counts, `not_available_at_compile_stage` as normal for valid f0, silent zeroing of missing metrics, equating sub-bass with subfundamental residual). Each file classified and updated where noted.

---

## Summary counts

| Classification | Count (approx.) |
|----------------|-----------------|
| current_keep | 6 |
| current_update_minor | 12 |
| obsolete_update_required → addressed in this pass | 5 |
| obsolete_archive | 0 (archived narrative removed from tree May 2026) |
| obsolete_delete_candidate | 0 |
| uncertain_manual_review | 2 |

---

## Per-file register

Legend: **Cursor updated** = Y if this audit pass edited the file; **Manual review** = Y if a human should still skim for project-specific wording.

| File | Classification | Reason | Obsolete / risky claims found | Recommended action | Cursor updated | Manual review |
|------|------------------|--------|--------------------------------|--------------------|----------------|---------------|
| `README.md` | current_update_minor | Primary entry; needed explicit canonical Stage 1/2 and audit CLI | Opening implied batch-centred flow without naming `compile_density_metrics_with_pca` | Align intro with canonical pipeline + link new semantics doc | Y | N |
| `TECHNICAL_MANUAL.md` | current_update_minor | Long-form reference; a few diagrams still said `compile_density_metrics(` | Sequence diagram called `compile_density_metrics` without `_with_pca`; mermaid Phase labels could imply super-only path | Fix API name in diagram; clarify optional batch | Y | N |
| `docs/DENSITY_EXPORT_SCHEMA.md` | obsolete_update_required → fixed | §L/§M still described Phase 1 JSON as “canonical public” primary for rolloff/HEpd | Implied `super_analysis_results.json` was default canonical source for public columns | Document primary path = `spectral_analysis.xlsx`; JSON = optional fallback | Y | N |
| `docs/CANONICAL_PIPELINE_AND_EXPORT_SEMANTICS.md` | current_keep | **New** normative summary aligned to code/tests | — | Maintain when pipeline contract changes | Y | N |
| `docs/CURRENT_DOCUMENTATION_INDEX.md` | current_keep | **New** index | — | Keep in sync | Y | N |
| `docs/DOCUMENTATION_AUDIT_REPORT.md` | current_keep | This report | — | Update on future doc passes | Y | N |
| `docs/BATCH_ANALYSIS_AUDIT.md` | current_update_minor | Accurate for batch code but could be read as “only pipeline” | Describes `SuperAudioAnalyzer` per file without front-matter canonical disclaimer | Add banner: batch = optional Phase 1; Stage 1 = `proc_audio` | Y | Y |
| `docs/BATCH_ANALYSIS_FIELD_MAP.md` | current_update_minor | Short map; “Bin centre” row easy to over-read | Table said `Frequency (Hz)` = bin centre without harmonic interpolation caveat | Add note + pointer to semantics doc | Y | N |
| `PIPELINE_FUNCTIONING_REPORT.md` | obsolete_archive → **stub only** | Contradicted production (claimed “no batch preprocessing”); missed audit/f0/subfundamental | Oversimplified Stage 2; no Debug_Counts / missing-metric policy | Long narrative removed from tree May 2026; stub points to current docs + git history | Y | N |
| `ORCHESTRATOR_INTEGRATION_GUIDE.md` | obsolete_update_required → fixed | Title and ASCII still “Super → Main” as if exclusive | Implied percentages “applied” without emphasising H/(H+I) model coefficients | Rewrite overview + architecture labels | Y | Y |
| `QUICK_START_ORCHESTRATOR.md` | current_keep | Already references `run_orchestrator` + compiled output | None material | Optional cross-link | N | N |
| `TROUBLESHOOTING_ORCHESTRATOR.md` | current_keep | Scoped to Tk v2_16 | None in scope | None | N | N |
| `API_REFERENCE.md` | current_update_minor | Listed `compile_density_metrics` as headline API | Suggested non-`_with_pca` as primary compile entry | Point to `compile_density_metrics_with_pca` | Y | N |
| `TESTING.md` | current_update_minor | Missing pipeline audit commands | — | Add stabilisation pytest block | Y | N |
| `audio_analysis/README_SUPER_ANALYZER.md` | current_update_minor | Legacy tool doc; risk of being cited as canonical | Already had v6 note; still marketing-heavy “state-of-the-art” | Strengthen **LEGACY** banner + canonical link | Y | Y |
| `audio_analysis/BATCH_CONFIG_README.md` | current_keep | Paths relative to GUI | References `super_audio_analyzer_gui.py` as path anchor | Acceptable for legacy GUI | N | N |
| `audio_analysis/BATCH_PROCESSING_README.md` | current_keep | Describes batch tree including `super_analysis_results.json` as output | None if read as batch-only | Add one-line pointer to canonical pipeline doc | Y | N |
| `scripts/README_SENSITIVITY.md` | uncertain_manual_review | Not scanned line-by-line in this pass | Unknown | Spot-check if cited in papers | N | Y |
| `tests/benchmarks/README.md` | current_keep | Corpus harness | None assumed | None | N | N |
| `metrics_dictionary.json` | uncertain_manual_review | Machine-readable; `source` fields cite `super_audio_analyzer` for legacy provenance | Not a “canonical pipeline” claim | Decide if provenance strings need “legacy” prefix in a future pass | N | Y |
| `Backup/**/*.md` | obsolete_delete | Historical snapshots | Not maintained as current docs | **Removed** from working tree May 2026 (Markdown / text only) | N | N |

---

## Obsolete claims removed or neutralised (conceptual)

1. **“Canonical compiler”** wording that omitted **`compile_density_metrics_with_pca`** — README, TECHNICAL_MANUAL diagram, API_REFERENCE updated.  
2. **Rolloff / HEpd “canonical = super JSON first”** — `DENSITY_EXPORT_SCHEMA` §L/§M reframed: **`spectral_analysis.xlsx` primary**; JSON discovery **optional / diagnostic**.  
3. **Orchestrator guide implying SuperAudioAnalyzer drives all analysis** — overview and architecture labels clarified: optional batch; **`proc_audio`** is canonical Stage 1.  
4. **Step-by-step pipeline report contradicting batch-capable orchestrator** — long narrative removed from tree; root stub points to current docs / git history.  
5. **Bin-centre row in field map** — clarified vs interpolated harmonic exports.

---

## Checklist (documentation must not present)

| Claim | Status after pass |
|--------|-------------------|
| `super_audio_analyzer.py` as the **only** canonical Stage 1 | **Addressed** — canonical path stated in README, semantics doc, orchestrator guide, batch audit banner. Super analyzer remains documented as **legacy / optional** where it truly is the implementation of batch Phase 1. |
| f0 from **minimum harmonic partial** | **Not introduced** in updated docs; semantics doc states nominal prior + fit/fallback. **Manual:** search **git history** if a paper cites retired text that lived under the old `Backup/` tree. |
| Nonharmonic candidates as **confirmed** inharmonic partials | **Addressed** in `CANONICAL_PIPELINE_AND_EXPORT_SEMANTICS.md`. |
| Sub-bass / subfundamental / DC as the **same** object | **Addressed** — explicit distinction in semantics doc; `DENSITY_EXPORT_SCHEMA` already separated energy vs policy (cross-check §A–C). |
| Missing metrics **silently** as zero | **Addressed** — semantics doc + `TESTING.md` pointers; TECHNICAL_MANUAL `fillna` line clarified as internal normalisation context, not compiled missing-metric policy. |

---

## Tests / checks run (documentation task)

- Repository-wide grep (Markdown) for `super_audio_analyzer`, `super_analysis_results.json`, `compile_density_metrics(`, `nonharmonic_peak_candidate`, `not_available_at_compile_stage`, `minimum_harmonic`, and related phrases.  
- `python -m pytest tests/test_final_pipeline_invariants.py -q` after prior session (not re-run in this doc-only message; recommend CI).  

---

## Remaining documentation warnings

1. **`metrics_dictionary.json`** still contains **provenance strings** mentioning `super_audio_analyzer` for specific legacy-derived columns — accurate as code lineage, not as “canonical pipeline”. Optional follow-up: prefix with `legacy:` in `source` fields.  
2. **`TECHNICAL_MANUAL.md`** is large; only targeted sections were edited — **periodic** review for any remaining “Phase 1 canonical” wording in distant sections.  
3. **`audio_analysis/README_SUPER_ANALYZER.md`** remains long marketing text for the legacy CLI; it is clearly bannered but still **not** the document to cite for publication metrics.

---

## Files updated (this pass)

`README.md`, `TECHNICAL_MANUAL.md`, `docs/DENSITY_EXPORT_SCHEMA.md`, `docs/BATCH_ANALYSIS_AUDIT.md`, `docs/BATCH_ANALYSIS_FIELD_MAP.md`, `ORCHESTRATOR_INTEGRATION_GUIDE.md`, `API_REFERENCE.md`, `TESTING.md`, `audio_analysis/README_SUPER_ANALYZER.md`, `audio_analysis/BATCH_PROCESSING_README.md`, `PIPELINE_FUNCTIONING_REPORT.md` (stub), `docs/CANONICAL_PIPELINE_AND_EXPORT_SEMANTICS.md`, `docs/CURRENT_DOCUMENTATION_INDEX.md`, `CHANGELOG.md`, `docs/DOCUMENTATION_AUDIT_REPORT.md` (this file).

## Files archived

None in-tree (May 2026 housekeeping removed the former `docs/archive_obsolete/` copy; use git history).

## Files deleted

All `*.md` / `*.txt` documentation that lived under **`Backup/**`**, the entire **`Backup/`** directory tree (empty after document removal), and **`docs/archive_obsolete/**`**.

## Files needing manual review

- `ORCHESTRATOR_INTEGRATION_GUIDE.md` (long guide; confirm internal cross-links and examples match your deployment paths).  
- `audio_analysis/README_SUPER_ANALYZER.md` (legacy marketing tone).  
- `scripts/README_SENSITIVITY.md`, `metrics_dictionary.json` (optional provenance cleanup).

---

## Supplement (2026-05-14): research export & computational inventory

Documentation-only follow-up (no pipeline contract change):

| File | Update |
|------|--------|
| `docs/CURRENT_DOCUMENTATION_INDEX.md` | Research export tool: Excel **Table**-free output; link **`docs/COMPUTATIONAL_METRICS_CODE_REVIEW_REPORT.md`**. |
| `README.md` | Research export: AutoFilter vs Table, header sanitisation; link computational metrics report. |
| `CHANGELOG.md` | `[Unreleased]` documentation bullets for the above. |
| `docs/CANONICAL_PIPELINE_AND_EXPORT_SEMANTICS.md` | New **§9** — research workbook semantics and Excel XML behaviour. |
| `API_REFERENCE.md` | `export_research_workbook` summary. |
| `TESTING.md` | `pytest tests/test_research_density_export.py` (+ post-compile) and zip/table guard note. |
| `tools/export_research_density_workbook.py` | Module docstring: Excel compatibility and CLI metadata. |
| `TECHNICAL_MANUAL.md` | §5.3 subsection — research workbook + Excel Table-free note. |
| `docs/COMPUTATIONAL_METRICS_CODE_REVIEW_REPORT.md` | *(new file, prior session)* — indexed here. |

## Supplement (2026-05-17): legacy density export & research compromise column

| File | Update |
|------|--------|
| `docs/DENSITY_EXPORT_SCHEMA.md` | Expanded **§F1** (`Legacy_Density_Metrics`, default ON); new **§R** (research `density_weighted_sum_cdm_mean`, highlights, WCM vs mean). |
| `CHANGELOG.md` | `[Unreleased]` **Added** — legacy sheet + research mean/highlights. |
| `README.md`, `TECHNICAL_MANUAL.md` §5.3–5.4, `API_REFERENCE.md` | Stage 1 legacy sheet; research merge/highlights; v5 masking GUI not restored. |
| `docs/CANONICAL_PIPELINE_AND_EXPORT_SEMANTICS.md` | §1 Stage 1 output; §9 research semantics. |
| `docs/CURRENT_DOCUMENTATION_INDEX.md`, `TESTING.md` | Index + `test_legacy_density_export.py`. |
| `tools/export_research_density_workbook.py` | Module docstring §R cross-link. |
| `metrics_dictionary.json` | v1.3.2 — SDM, FDM, CDM, WCM, `density_weighted_sum_cdm_mean`. |
