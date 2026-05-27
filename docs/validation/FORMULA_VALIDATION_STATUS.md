# Formula Validation Status

This file records the canonical form of each formula tested by
`tests/formula_validation/`. The tests verify that the implementation
matches the canonical form at the symbolic-structure level. Numerical
correctness is verified separately under `tests/phase_*`.

The status of each formula is one of:

- **canonicalised_and_tested** — canonical form documented here and verified by a test under `tests/formula_validation/`.
- **canonicalised_only** — canonical form documented here but not yet verified by a structural test.
- **not_yet_canonicalised** — formula exists in the implementation but has no canonical-form documentation.

## F1 — Canonical H/I/S weighted density formula

- **Canonical form**: `density_metric_raw = D_H * w_H + D_I * w_I + D_S * w_S`
- **Module**: `metric_contract.py` (declaration); `density.py`, `compile_metrics.py` (application).
- **Version tag**: `density_formula_version = "v5_apply_density_metric_adapted_v6_1"`.
- **Test**: `tests/formula_validation/test_density_formula_canonical.py`.
- **Status**: canonicalised_and_tested.

## F2 — FFT-length normalisation factor (Phase 8)

- **Canonical form**:
  - `peak_amplitude_sum`: factor = `N_ref / N`
  - `peak_power_sum`: factor = `(N_ref / N)^2`
  - `broadband_amplitude_l2`: factor = `sqrt(N_ref / N)`
  - `broadband_power_l2`: factor = `N_ref / N`
- **Module**: `spectral_normalization.py` (function `n_fft_normalization_factor`).
- **Reference**: Harris (1978); Heinzel et al. (2002). See `REFERENCES.md`.
- **Test**: `tests/formula_validation/test_n_fft_normalization_factor_canonical.py`.
- **Status**: canonicalised_and_tested.

## F3 — Stiff-string inharmonicity fit (Fletcher 1962)

- **Canonical form**: `f_n = n * f0 * sqrt(1 + B * n^2)`.
- **Module**: `inharmonicity_model.py` (function `fit_inharmonicity_coefficient`).
- **Reference**: Fletcher (1962); Fletcher & Rossing (1998). See `REFERENCES.md`.
- **Test**: `tests/formula_validation/test_stiff_string_fit_canonical.py`.
- **Status**: canonicalised_and_tested.

## F4 — Sub-bass upper bound (Zwicker & Fastl 1990)

- **Canonical form**: `upper_bound_hz = min(f0_hz * 0.5, 80.0)`.
- **Module**: `subbass_policy.py` (`SubBassPolicy.upper_bound_hz`).
- **Reference**: Zwicker & Fastl (1990). See `REFERENCES.md`.
- **Test**: `tests/formula_validation/test_subbass_policy_canonical.py`.
- **Status**: canonicalised_and_tested.

## F5 — Effective partial density (participation ratio / inverse Herfindahl)

- **Canonical form**: `D_eff = (sum_i P_i)^2 / sum_i(P_i^2)`.
- **Module**: `density.py` (documented in module-level docstring or canonical-formula constant).
- **Interpretation**: scale-invariant in power; equivalent to the inverse Herfindahl concentration index of the power-component vector.
- **Test**: `tests/formula_validation/test_effective_partial_density_canonical.py`.
- **Status**: canonicalised_and_tested.

## F6 — Jensen–Shannon divergence (Lin 1991)

- **Canonical form**:
```
  m = 0.5 * (p + q)
  JS(p, q) = 0.5 * (KL(p, m) + KL(q, m))
```
- **Module**: `adaptive_density_engine.py` (function `_js_divergence`).
- **Reference**: Lin (1991). See `REFERENCES.md`.
- **Test**: `tests/formula_validation/test_js_divergence_canonical.py`.
- **Status**: canonicalised_and_tested.

## Coverage notes

This suite is proportionate, not exhaustive. The six formulae covered are those that are either explicitly version-tagged or the subject of an explicit phase entry in `CHANGES.md`. Internal helper formulae are governed by the numerical regression tests under `tests/phase_*` rather than by symbolic-structure tests, since the cost of false positives from over-specified AST tests is greater than the benefit at that level of granularity.

Future passes may canonicalise additional formulae as they become version-tagged or methodologically significant. The status of each addition should be recorded in this file before any corresponding test is added.
