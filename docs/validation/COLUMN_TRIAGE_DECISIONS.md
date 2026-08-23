# Column triage decisions

Residue of the four-branch rule on the 202 class-`metric` `COL:` columns.
Closed 2026-08-22 on `cleanup/repo-hygiene`.

## Contents

1. [spectral_body_thickness_index](#1-spectral_body_thickness_index) — closed
2. [Energy-ratio triples: plain vs core](#2-energy-ratio-triples-plain-vs-core) — closed
3. [Soma_A_linear_total vs total_component_energy](#3-soma_a_linear_total-vs-total_component_energy) — closed

---

## 1. `spectral_body_thickness_index`

**Resolution (2026-08-22):** class stays `metric`. Stamped **F-041**. Contract
carries: "Z-scored composite; corpus-relative — a note's value changes with
corpus composition. Not valid in any cross-corpus table or comparison."

---

## 2. Energy-ratio triples: plain vs core

**Resolution (2026-08-22):** the triples are **distinct**. Each gets its own
family F-id. Denominators as read in code:

| Triple | F-id | What the code writes | Denominator |
|--------|------|----------------------|-------------|
| `{harmonic,inharmonic,subbass}_energy_ratio` | **F-069** | After discrete H/I/S peak-PSD shares of `tot_energy`, WP1 overwrites H and S from `acoustic_density_core` PSD descriptors (`h_energy` / `s_energy` over `h+r+s`). I remains the discrete inharmonic peak-PSD share of `tot_energy` (`H+I+S` peak energies) unless later overwritten. | Mixed: H and S use PSD region total `h+r+s`; I uses discrete `tot_energy = h_energy+ih_energy+sub_energy` |
| `core_{harmonic,residual,subbass}_energy_ratio` | **F-070** | Export aliases of `component_{harmonic,inharmonic,subbass}_energy_ratio` (`proc_audio` Metrics row). Residual = the inharmonic *component* share, not the acoustic-core residual descriptor. | Single-pass `Hn+In+Sn` (`component_energy_denominator = "H+I+S"`, quantity `power_sum_amplitude_squared`) |

Compile-time fill (`core_*` copied from plain/residual only when core is
absent) is not an identity of live Stage-1 values. Neither triple is F-018
(`component_*` as defined; F-070 *exports* those component shares under the
`core_*` names).

---

## 3. `Soma_A_linear_total` vs `total_component_energy`

**Resolution (2026-08-22):**

- The four `Soma_A_linear_*` columns remain `deprecated` as Portuguese-named
  copies of `linear_sum_amplitude_*` / their NaN→0 sum. No rename.
- `total_component_energy` is class `diagnostic`. Contract and dictionary
  carry: "MISNOMER: computes an amplitude sum (NaN coerced to 0), not energy.
  Do not use as E in any calculation; spectral_mass and ACD derive energy
  independently."
- Open item (CHANGES.md): rename at next major version; replace NaN→0
  coercion with NaN propagation at the same time. Computation unchanged now.
