# Dissonance export migration (package 4.6.0)

These columns change meaning. A 4.5.0 workbook is **not** a rescaling of a
4.6.0 workbook. Rank orderings move.

| Column | 4.5.0 and earlier | 4.6.0 |
|---|---|---|
| `hutchinson_knopoff_dissonance` | Mean of pair-normalised `a_i a_j g_ij / (a_i²+a_j²)` × 10. Not H&K eq. (3). | Hutchinson & Knopoff (1978) eq. (3): `Σ_{i<j} a_i a_j g_ij / Σ a²`. |
| `hutchinson_knopoff_legacy_mean_pair_scaled` | (absent) | The previous quantity, kept so archived comparisons remain possible. |
| `sethares_dissonance` | `mean_pair_scaled` (`Σ d_ij / n_pairs × 10`). Falls as peak count rises. | `minamp_norm` (`Σ d_ij / Σ min(a_i,a_j)`). |
| `vassilakis_dissonance` | Same `mean_pair_scaled` default via the shared base. | Same default change to `minamp_norm`. |
| `dissonance_metric_mode` | (absent) | Mode used for the Sethares/Vassilakis export (`minamp_norm` unless overridden). |
| `*_formula_version` | 4.5.0 first stamp, or none | Affected columns stamped **4.6.0**. |

The Sethares per-class override (`calculate_dissonance_metric(self, df)` only)
is deleted. All three models accept the base keyword arguments. Calling with
`metric_mode="minamp_norm"` no longer raises `TypeError` on Sethares.

`analyze_real_timbre(..., save_directory=None)` no longer writes
`dissonance_metrics.csv`.

See `docs/validation/DISSONANCE_METRIC_MODE.md` for the four-mode table and
the demonstrated peak-count dependence. Formula versions:
`metric_formula_versions.DISSONANCE_FORMULA_VERSION`.
