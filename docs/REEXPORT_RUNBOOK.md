# Re-export runbook (v4.2.1)

One full Stage 1–3 re-export per corpus after the freeze-ready tag
(`v4.2.1` supersedes `v4.2.0` as the reference; do not delete
`v4.2.0`). Write outputs to `analysis_results_v4.2.1`. Compare against
`docs/validation/pretag_evidence/` (non-citable).

Production policy (WP3): `fft_policy=fixed`, `n_fft=8192`, `hop=1024`,
`seg=sustain_primary_stable_diagnostic`, `elig=1` (policy version, not
the per-note boolean). Default φ is `log`. F-042 / F-047 / F-048 / F-049
algebra is unchanged.

## 1. Full corpus re-export (Stage 1 + 2 + 3)

From the repository root, with the tagged `v4.2.1` checkout:

```bash
python run_orchestrator.py --corpus "<CORPUS_AUDIO>" --out "<OUT_DIR>" --stages 1,2,3 --figures --fft-policy fixed --fixed-n-fft 8192 --fixed-hop-length 1024
```

`--fft-policy fixed` is already the default. Passing it keeps the
invocation explicit. The run writes `run_manifest.json` beside the
compiled workbooks.

Example local corpora (paths are machine-local; do not commit outputs):

```bash
python run_orchestrator.py --corpus "D:\METAIS\TUBA\Tuba\Tuba_Yowa\IOWA_tuba_pp\_Sustains" --out "D:\METAIS\TUBA\Tuba\Tuba_Yowa\IOWA_tuba_pp\_Sustains\analysis_results_v4.2.1" --stages 1,2,3 --figures --fft-policy fixed

python run_orchestrator.py --corpus "D:\METAIS\TROMBONE\IOWA_Trombone\TenorTrombone\IOWA_Trombone_pp\_Sustains" --out "D:\METAIS\TROMBONE\IOWA_Trombone\TenorTrombone\IOWA_Trombone_pp\_Sustains\analysis_results_v4.2.1" --stages 1,2,3 --figures --fft-policy fixed

python run_orchestrator.py --corpus "D:\METAIS\TROMBONE\IOWA_Trombone\TenorTrombone\IOWA_Trombone_mf\_Sustains" --out "D:\METAIS\TROMBONE\IOWA_Trombone\TenorTrombone\IOWA_Trombone_mf\_Sustains\analysis_results_v4.2.1" --stages 1,2,3 --figures --fft-policy fixed

python run_orchestrator.py --corpus "D:\METAIS\TROMBONE\IOWA_Trombone\TenorTrombone\IOWA_Trombone_ff\_Sustains" --out "D:\METAIS\TROMBONE\IOWA_Trombone\TenorTrombone\IOWA_Trombone_ff\_Sustains\analysis_results_v4.2.1" --stages 1,2,3 --figures --fft-policy fixed

python run_orchestrator.py --corpus "D:\MADEIRAS\FLAUTA\IOWA_flute\IOWA_Flute_pp\_Sustains" --out "D:\MADEIRAS\FLAUTA\IOWA_flute\IOWA_Flute_pp\_Sustains\analysis_results_v4.2.1" --stages 1,2,3 --figures --fft-policy fixed

python run_orchestrator.py --corpus "D:\MADEIRAS\FLAUTA\IOWA_flute\IOWA_Flute_mf\_Sustains" --out "D:\MADEIRAS\FLAUTA\IOWA_flute\IOWA_Flute_mf\_Sustains\analysis_results_v4.2.1" --stages 1,2,3 --figures --fft-policy fixed

python run_orchestrator.py --corpus "D:\MADEIRAS\FLAUTA\IOWA_flute\IOWA_Flute_ff\_Sustains" --out "D:\MADEIRAS\FLAUTA\IOWA_flute\IOWA_Flute_ff\_Sustains\analysis_results_v4.2.1" --stages 1,2,3 --figures --fft-policy fixed
```

Use the full `_Sustains` cut as the primary corpus. `_Sustains_Stable`
siblings stay diagnostic only (WP3). Do not substitute stable EWSD for
the primary score. The archived pretag workbooks in
`docs/validation/pretag_evidence/` are SustainStable Test-tree
exports (`6b0e51a`). A P6 Δ vs those files therefore mixes the
tag/policy change with the full-vs-stable cut; say so on the audit
sheet. Cello *ff* and the other CORDAS folders on this machine are
mostly `_Sustains_Stable` only — list each leaf and do not silently
promote stable EWSD to the primary score.

## 2. Stage 2 + 3 re-export from an existing Stage 1 tree

When Stage 1 workbooks are already current (same commit / same FFT
policy) and only compilation or research export must be rebuilt:

```bash
python -m tools.reexport_corpus --stage1-root "<STAGE1_ROOT>" --out "<OUT_DIR>" --stages 2,3 --figures --fft-policy fixed --baseline docs/validation/ANALISE_3_TUBA_PP_EWSD_2026_08_19.json
```

`--corpus` on this wrapper implies Stage 1–3. Do not pass `--corpus`
when the intent is Stage 2+3 only.

## 3. Verify the run

Per-workbook provenance (Phase E):

```bash
python verify_export.py "<OUT_DIR>\compiled_density_metrics_research.xlsx"
python verify_export.py "<OUT_DIR>\<NOTE>\spectral_analysis.xlsx"
```

Corpus-level production policy (this WP):

```bash
python -m tools.verify_corpus "<OUT_DIR>"
```

`verify_corpus` fails closed when:

- `run_manifest.json` is missing or incomplete
- `analysis_parameter_profile_id` lacks `fft` / `seg` / `elig`
- `fft_policy` is not `fixed`, or `n_fft` / hop are not 8192 / 1024
- the run is not a primary-comparable profile (default φ + fixed FFT)
- a compiled workbook mixes profile ids
- a degenerate ineligible note exports CI `rel_uncertainty = 0.0`

Research-only adaptive-tier trees may use `--allow-noncomparable`.
Those runs are not freeze-comparable.

## 4. Boundary guard (optional)

```bash
python -m tools.compare_runs "<RUN_A>" "<RUN_B>" --metrics EWSD_score_acoustic_balanced,core_harmonic_energy_ratio,harmonic_density_sum,subbass_density_sum,effective_partial_density --boundaries G3:G#3,B4:C5
```

## 5. Freeze rule

After `v4.2.1` is tagged on `main`: **one** full re-export per corpus,
then freeze. Do not iterate Stage 1 on the same corpus after that tag
unless a later tagged release is cut. Attach `verify_corpus` output
beside each `run_manifest.json`.
