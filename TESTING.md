# Testing policy

SoundSpectrAnalyse uses [pytest](https://docs.pytest.org/) as the canonical
test runner. The test suite is partitioned with a single custom marker:

| Marker | Meaning |
| --- | --- |
| `slow` | Tests that are computationally expensive or unsuitable for the default fast suite (typically O(N²) dissonance models, multi-process consistency, or wall-clock micro-benchmarks). |

The marker is registered in `pyproject.toml` under
`[tool.pytest.ini_options].markers`, so using it never triggers a
`PytestUnknownMarkWarning`.

## Formula-validation tests

**Location:** `tests/formula_validation/` — one pytest module per completed pass (Passes **1–15**), aligned with `docs/formula_extraction/` and `docs/formula_validation/` plans.

**Run (quiet):**

```bash
python -m pytest tests/formula_validation/ -q
```

**Meaning (cautious):** these tests support **internal consistency** between the documented mathematical formulas and the tested Python implementations for the **selected numerical fixtures** in each validation plan. They do **not**, by themselves, prove scientific optimality, universal correctness, or full acoustic validity of the models. Counts and pass coverage for a recorded cycle are summarised in **`VALIDATION_STATUS_812_PASSED_PASSES_1_15.md`**; methodology in **`METHODOLOGICAL_NOTE_FORMULA_VALIDATION.md`**.

## How to run

### Default non-slow suite

```bash
pytest -m "not slow"
```

This is the contract every contributor and CI step is expected to honour.
It exercises every fast unit, integration, and regression test.

### Full suite (including slow tests)

```bash
pytest
```

Run this when you are explicitly validating performance / parallel /
multi-process behaviour and you can afford a few minutes of wall-clock
time.

### Only the slow tests

```bash
pytest -m slow
```

### Discover slow tests without running them

```bash
pytest -m slow --collect-only
```

## Known slow tests

The following tests are tagged `@pytest.mark.slow`. They are kept in the
repository but excluded from the default fast suite:

- `tests/test_integration_audio.py::TestIntegrationWithRealAudio::test_parallel_vs_sequential_consistency`
  – Generates four synthetic WAVs and asserts identical results between
  sequential and parallel execution. Hits the `O(N²)` Sethares dissonance
  path multiple times per file.
- `tests/test_performance_benchmarks.py::TestParallelProcessing::test_parallel_speedup_exists`
  – Compares sequential vs parallel wall-clock over a CPU-count-scaled
  batch of synthetic WAVs.
- `tests/test_edge_frame_correction.py::TestRealAudioCorrection::test_first_note_density_improvement`
  – Runs the full first-note edge-frame correction pipeline twice on
  synthetic audio and compares densities.

If you add a new slow test, decorate it with `@pytest.mark.slow` and
extend this list. Do **not** silently ignore individual tests at runtime
— mark them so other contributors can opt in or out explicitly.

## Adding a new marker

1. Register it in `pyproject.toml` →
   `[tool.pytest.ini_options].markers`.
2. Document it in this file.
3. Apply `@pytest.mark.<name>` to the relevant test(s).

## CI guidance

Continuous integration should:

- always run `pytest -m "not slow"` (mandatory gate);
- optionally run `pytest -m slow` on a nightly job or a manual trigger.

Both modes are first-class supported.

## Pipeline stabilisation / compiled workbook invariants

After changes to Stage 2 exports or low-frequency policy, run:

```bash
pytest tests/test_final_pipeline_invariants.py tests/test_low_frequency_policy.py tests/test_validate_canonical_metrics.py
```

**CLI audit** on an existing compiled workbook:

```bash
python tools/audit_compiled_workbook.py path/to/compiled_density_metrics.xlsx
```

Optional second argument: one per-note `spectral_analysis.xlsx` for Harmonic Spectrum interpolation checks.

### Per-note component balance chart semantics

After edits to `proc_audio` pie titles, filenames, or `Analysis_Metadata` chart keys, run:

```bash
pytest tests/test_component_balance_pies.py
```

Narrative reference: **`docs/CANONICAL_PIPELINE_AND_EXPORT_SEMANTICS.md`** (per-note chart table) and **`docs/DENSITY_EXPORT_SCHEMA.md`** §J.

### Research workbook export (`compiled_density_metrics_research.xlsx`)

After changes to **`tools/export_research_density_workbook.py`** or **`post_compile_research_export.py`**, run:

```bash
pytest tests/test_research_density_export.py tests/test_post_compile_research_export.py -v
```

The suite includes a **zip** check that the output has **no** `xl/tables/*.xml` parts (Excel repair regression guard).

See **`docs/CANONICAL_PIPELINE_AND_EXPORT_SEMANTICS.md`** §9 and **`README.md`** (research export CLI).

**Environment-driven integration test** (optional):

```powershell
$env:SSA_COMPILED_WORKBOOK="C:\path\to\compiled_density_metrics.xlsx"
$env:SSA_PER_NOTE_WORKBOOK="C:\path\to\spectral_analysis.xlsx"
pytest tests/test_final_pipeline_invariants.py
```

See **`docs/CANONICAL_PIPELINE_AND_EXPORT_SEMANTICS.md`** §8 for CMD examples.
