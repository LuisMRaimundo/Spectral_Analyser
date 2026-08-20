# Metric single-source (R2)

One exported EWSD and one exported `core_harmonic_energy_ratio` at the
declared window (`fft_policy=fixed`, default 8192/1024). Detection
still depends on that window (R1b). This page is the path table, not a
cross-resolution claim.

| Path | module.function | Columns | Consumers |
|------|-----------------|---------|-----------|
| Descriptor H/I/S | `acoustic_density_core.compute_acoustic_density_descriptors` | `harmonic_energy_ratio`, `residual_energy_ratio`, `subbass_energy_ratio` | Stage-1 extras / pies. **Not** export `core_H` after R2. |
| Diagnostic density | same | `energy_weighted_component_density_diagnostic` | Metrics diagnostic only. **Not** EWSD. |
| Component H/I/S | `proc_audio` ΣA² single pass | `component_*_energy_ratio` | Export `core_*`; Stage-3 SDM `core_*`. |
| Stage-1 `core_H` | `AudioProcessor._build_main_metrics_export_row` | `core_harmonic_energy_ratio` | compile, eval, `verify_export`. |
| Stage-1 EWSD | `tools.canonical_note_metrics.stamp_stage1_ewsd` | `EWSD_score_acoustic_balanced` | Metrics, eval B1, `verify_export`. |
| Stage-3 `core_H` | `tools.export_research_density_workbook` | `core_harmonic_energy_ratio` | compiled `Spectral_Density_Metrics`. |
| Stage-3 EWSD | `tools.ewsd_research_integration.compute_ewsd_dataframe_from_analysis_root` | `EWSD_score_acoustic_balanced` | SDM, `Stage3_Diagnostics`. |
| Density sums | `compile_metrics.extract_density_component_sum` | `*_density_sum` | Density_Metrics / SDM. |

Invariant `metric_single_source` (`data_integrity`, `verify_export`):
Stage-1 `core_H` equals `component_harmonic_energy_ratio`; Stage-1 EWSD
equals Stage-3 EWSD when both are finite (atol 1e-9).
