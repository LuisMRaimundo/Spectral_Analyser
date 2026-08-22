# Column triage decisions (author eyes)

Residue of the four-branch rule on the 202 class-`metric` `COL:` columns.
Nothing here was assigned an F-id or reclassified by guess.

## Contents

1. [spectral_body_thickness_index](#1-spectral_body_thickness_index)
2. [Energy-ratio triples: plain vs core](#2-energy-ratio-triples-plain-vs-core)
3. [Soma_A_linear_total vs total_component_energy](#3-soma_a_linear_total-vs-total_component_energy)

---

## 1. `spectral_body_thickness_index`

| Candidate | Why it almost fits | What is missing |
|-----------|--------------------|-----------------|
| (c) metric / F-041 | `METRIC_FORMULA_INDEX.md` already records F-041 as `0.45 z(BWED) + 0.25 z(LMER) + 0.20 z(HBDN) + 0.10 z(RBCC)` | The four-branch rule sends a bespoke z-scored composite to this document instead of treating F-041 as automatically citable. |
| (d) diagnostic | It is an editorial blend of four other columns, two of which are themselves deprecated or pending | Whether the index remains a headline metric or becomes a chart-only diagnostic is an author call. |

Left as class `metric` with stamp `COL:spectral_body_thickness_index`. F-041 is not restamped here.

---

## 2. Energy-ratio triples: plain vs core

Columns: `harmonic_energy_ratio`, `inharmonic_energy_ratio`, `subbass_energy_ratio`,
`core_harmonic_energy_ratio`, `core_residual_energy_ratio`, `core_subbass_energy_ratio`.

| Candidate | Why it almost fits | What is missing |
|-----------|--------------------|-----------------|
| (c) / F-018 | F-018 already defines `component_*_energy_ratio` as `r_k = E_k / (E_H+E_I+E_S)` | The 202-list triples are **not** those `component_*` columns. Phase-12 tests show `harmonic_energy_ratio` and `component_harmonic_energy_ratio` can differ on the same row. |
| one family id | `tools/ewsd_core.py` lists both triples as distinct `AUTO_RATIO_PRIORITY` sources | The two triples are not the same compartments: core is H / **residual** / S; plain is H / **inharmonic** / S. |
| fallback identity | `compile_metrics._prepare_df_for_density_export` copies `harmonic_energy_ratio` → `core_harmonic_energy_ratio` (and residual/subbass) **only when the core column is absent** | That is a compile-time fill, not a documented identity of the live Stage-1 values. |

No single denominator is documented for both triples together. Left as class `metric` with `COL:` stamps.

---

## 3. `Soma_A_linear_total` vs `total_component_energy`

`compile_metrics._prepare_df_for_density_export` copies

- `linear_sum_amplitude_harmonic` → `Soma_A_linear_harmonicos`
- `linear_sum_amplitude_inharmonic_partial` → `Soma_A_linear_inarmonicos`
- `linear_sum_amplitude_subbass_band` → `Soma_A_linear_subbass`

and sets `Soma_A_linear_total` to the sum of those three with **NaN treated as 0**.

The Task-0 research fixture (`cleanup_after_3.xlsx`) does not export the Soma
or `linear_sum_amplitude_*` columns (they live on compiled `Density_Metrics`).
Identity is therefore taken from the compile path, which is an assignment, not
an independent computation: H/I/S Soma cells are copies of the English twins;
`Soma_A_linear_total` is their NaN→0 sum. That sum is **not**
`total_component_energy` (linear amplitude vs energy).

The four `Soma_A_linear_*` columns are therefore classed `deprecated` as
Portuguese-named duplicates of the English linear-amplitude twins / their NaN→0
sum. `total_component_energy` stays class `diagnostic` (branch d). No rename.
