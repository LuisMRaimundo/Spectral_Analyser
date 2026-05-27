# CHANGES_PHASE_7

## Scope
- Phase 7 final scientific export audit only: export completeness, diagnostic transparency, residual anomaly flagging, and metadata hygiene.
- No GUI cosmetic changes.
- No changes to mathematical definitions of `density_metric_raw`, `density_metric_raw_per_note_balance`, `harmonic_density_sum`, `inharmonic_density_sum`, or `subbass_density_sum`.

## Touched Files And Methodological Reason

- `compile_metrics.py`
  - Added full inharmonicity diagnostic export fields to `Density_Metrics`: `inharmonicity_model_applied`, `inharmonicity_fit_source`, and warning tokenization.
  - Added conservative source labeling:
    - `per_note_inharmonicity_fit_sheet` when fit diagnostics are complete.
    - `partial_export_missing_status` when `B` exists but fit status/residual is absent.
  - Added explicit inharmonicity validation warnings for:
    - clarinet-note `B > 1e-5`,
    - missing fit status,
    - missing residual.
  - Fixed per-note metrics sheet detection for MIR extraction so descriptor values in `Metrics` are propagated.
  - Added MIR availability transparency columns: `mir_descriptors_available`, `mir_descriptors_source`, `mir_descriptors_missing_reason`.
  - Added consistent `f0_final_source` propagation (`unknown` fallback when unavailable).
  - Added workbook-level `Validation_Summary` sheet with required Phase 7 scientific summary fields (comparability, Phase 2 weights, tier summary, inharmonicity stats, obs_wS artifact counts, MIR availability summary).

- `pipeline_orchestrator_gui.py`
  - Added `compute_obs_ws_artifact_diagnostics(...)` to explicitly separate model-density residual behavior from physical sub-bass energy evidence.
  - Extended Phase 1 discovery export history to include:
    - pure observation triplet columns,
    - sub-bass energy diagnostics,
    - interpretation and artifact flags/reasons.
  - Kept raw `obs_wS` untouched (no clamping, no forced reduction), and added explicit interpretation field:
    - `model_density_residual_not_physical_subbass_energy` when conservative artifact criteria are met.

- `tools/export_research_density_workbook.py`
  - Added conservative `Technique` inference from filename/path tokens (including `ord`).
  - Added row-level metadata transparency fields:
    - `metadata_inference_status`,
    - `metadata_missing_reason`.
  - Ensured `f0_final_source` is always exported (`unknown` when absent).
  - Reworked git metadata probing to avoid fatal-looking behavior outside a repo:
    - `git_commit=unavailable_not_a_git_repository` when applicable,
    - added `git_status_reason`.
  - Hardened chart path handling to avoid dtype ambiguity by ensuring explicit string placeholders for missing chart paths.

- `tests/phase_7/test_inharmonicity_diagnostics_export.py`
  - New regression coverage for complete and partial inharmonicity exports, including fit-source semantics.

- `tests/phase_7/test_obs_ws_artifact_flag.py`
  - New regression coverage for conservative `obs_wS_artifact_flag` behavior and preservation of original `obs_wS`.

- `tests/phase_7/test_mir_descriptor_export_or_availability.py`
  - New regression coverage for MIR descriptor value propagation and explicit unavailable-state export.

- `tests/phase_7/test_research_export_metadata_cleanliness.py`
  - New regression coverage for instrument/dynamic/technique inference, chart path dtype safety, and non-git metadata handling.

- `tests/phase_7/test_final_validation_summary.py`
  - New regression coverage for required final validation summary fields in compiled workbook.

## Scientific Interpretation Note
- `obs_wS` is a model-density observation term, not a direct physical sub-bass energy ratio. When sub-bass energy-ratio evidence is near zero and sub-bass energy is negligible relative to harmonic energy, `obs_wS` should be interpreted as model residual structure and not as physical sub-bass content.
