# GitHub Export Manifest

## 1. Export source and destination

- **Source project:** `C:\Users\lmr20\Desktop\SoundSpectrAnalyse-main_6`
- **Destination:** `C:\Users\lmr20\Desktop\Git Hub`
- **Git commands were not run** (no commit, push, init, or other Git CLI).
- **Original source project was not modified** by this export script (read-only copy from source; writes only under the destination folder).

## 2. Included content

Copied categories:

- First-party **source code** (repository-root `*.py`, `audio_analysis/`, `tools/`, `scripts/`, excluding generated batch/output trees such as `batch_results/`).
- **Configuration:** `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `requirements-pins.txt`, `metrics_dictionary.json`, `run.bat`, `.gitignore` (destination).
- **Tests:** full `tests/` tree including `tests/formula_validation/`, excluding forbidden/binary/cache patterns.
- **Formula-validation documentation:** `docs/formula_validation/`, `docs/formula_extraction/`, and related technical docs under `docs/`.
- **Technical documentation:** selected root Markdown files (see allowlist in export script) and `docs/` (obsolete audit Markdown filenames excluded).
- **CI workflow:** `.github/workflows/` when present.
- **Proprietary notice:** `NOTICE.md` (destination root).
- **Citation metadata:** `CITATION.cff` (citation only; **no** reuse permission).

**File count (regular files under destination, after purge):** 224

## 3. Excluded content

Excluded by policy from the copy:

- Virtual environments (`.venv/`, `venv/`, …) and Python caches (`__pycache__/`, `.pytest_cache/`, …).
- Build artefacts (`build/`, `dist/`, `*.egg-info/`).
- Logs, temporary files, backups, local analysis/export/output trees (`batch_results/`, `output/`, `analysis_results/`, etc.).
- Generated spreadsheets, audio, archives, plots (`*.xlsx`, `*.wav`, `*.zip`, `*.png`, …) and `*.csv` (no tiny template CSVs were required for this export).
- **Benchmark reference WAVs** under 	ests/benchmarks/audio/ were omitted; some benchmark tests may skip or require regenerating those fixtures locally.
- Named **obsolete audit / cleanup** Markdown reports at repository root (see export script `OBSOLETE_MD` set).
- **Root Markdown not in the include list** was **not copied automatically**; see **§6 Review** below.

## 4. Validation status

- **Latest working-folder validation (source tree, after repository naming sync):** **813 passed**, **39 skipped** in a full `pytest` run with dev dependencies installed (`psutil` required for one performance test).
- **Previous recorded status document included in this export:** `VALIDATION_STATUS_812_PASSED_PASSES_1_15.md` (812 passed, 39 skipped at time of recording).
- **Formula-validation suite:** **149 passed** (Passes **1–15** completed).

**Recommendation:** Re-run `python -m pytest -q` inside a fresh virtual environment **after** cloning or copying this export folder, before any publication or release tagging.

## 5. Copyright status

- **No open-source licence** is granted by this export.
- **`NOTICE.md`** governs proprietary use and denial of default permissions.
- **`CITATION.cff`** is for citation metadata only and **does not** grant permission to reuse, redistribute, or modify the software.

## 6. Manual next steps

1. Create a virtual environment and install dependencies (`pip install -e ".[dev]"` or equivalent).
2. **Run tests** in the export folder (`python -m pytest -q`).
3. **Review** Git status and diffs manually when you initialise a repository.
4. **Initialise Git** manually if desired (not done here).
5. **Push** to the private GitHub remote manually (not done here).

## 7. Root Markdown — not copied (for human review)

The following `*.md` files existed at the **source** repository root but were **not** on the automatic include list (either obsolete-by-policy, superseded validation snapshots, or ambiguous):

- `PIPELINE_FUNCTIONING_REPORT.md`
- `VALIDATION_STATUS_728_PASSED.md`
- `VALIDATION_STATUS_746_PASSED.md`
- `VALIDATION_STATUS_766_PASSED.md`

## 8. Post-copy path/token scan (informational)

Matches for legacy path/script strings in **selected text files** under the destination (may include intentional **CHANGELOG** rename history — **do not auto-edit**):


### robust_orchestrator_v2_16

- `CHANGELOG.md`


### robust_orchestrator_integrated

- `CHANGELOG.md`

