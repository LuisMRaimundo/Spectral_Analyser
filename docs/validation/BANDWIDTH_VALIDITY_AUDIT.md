# Bandwidth validity audit

Two bandwidth formulae were applied outside the range their sources
fitted (Zwicker CB above the Bark scale; Hutchinson–Knopoff CBW below
~200 Hz). This document treats that as a **class of defect**.

A **guard** here means the implementation refuses or NaNs the value
outside the source range. Comments and documented constants are not
guards.

ACD helpers in `tools/spectral_density_hill.py` and EWSD in
`tools/ewsd_pure.py` are frozen. Guards that would change those
exports are listed under Task 5 and were **not** applied.

## Expressions

| File / function | Expression | Source and fitted range | Pipeline evaluation range | Guard? |
|---|---|---|---|---|
| `mir_descriptors.critical_bandwidth_zwicker_hz` | `25+75(1+1.4(f/1000)^2)^0.69` | Zwicker & Fastl (2007), fit to the Zwicker, Flottorp & Stevens (1957) / Bark lineage, ~20 Hz–15.5 kHz | Peak lists through 20 kHz (20-partial series at f0=1 kHz) | **Yes (this task).** NaN above `CB_ZWICKER_VALID_MAX_HZ=15500`. F-037 drops pairs whose higher member exceeds that ceiling. Diagnostic: `roughness_pairs_excluded_above_validity`. |
| `mir_descriptors.erb_bandwidth_hz` | `0.108 f + 24.7` | Glasberg & Moore (1990), notched-noise ERB, roughly 100 Hz–15 kHz | Optional `bandwidth_basis="erb"` on the same 20 Hz–20 kHz peak lists | **No numeric guard.** Constants `ERB_VALID_MIN_HZ` / `ERB_VALID_MAX_HZ` are documented only. A NaN/clip guard would change optional-ERB roughness. **Task 5.** |
| `mir_descriptors._erb_rate_hz` | `21.4 log10(1+0.00437 f)` | Moore & Glasberg (1983) ERB-rate, same mid-frequency notched-noise range | `erb_weighted_spectral_density` on full peak lists | **No.** A guard would change that exported column. **Task 5.** |
| `tools/spectral_density_hill.py` `erb_bandwidth_hz` | `0.108 f + 24.7` (local copy; not imported from `mir_descriptors`) | Glasberg & Moore (1990), ~100 Hz–15 kHz | ACD merge on H/I/S peaks, typically 20 Hz–20 kHz | **No.** Frozen ACD numerics. **Task 5** (must not land without an ACD formula-version bump, which this round forbids). |
| `tools/spectral_density_hill.py` `erb_rate` | `21.4 log10(1+0.00437 f)` | Moore & Glasberg (1983) | `fixed_erb_grid` binning of the same peaks | **No.** Frozen ACD. **Task 5.** |
| `dissonance_models.HutchinsonKnopoffDissonance.cbw` | `1.72 f^0.65` | Hutchinson & Knopoff (1978) Fig. 2; the power-law fit degrades below ~200 Hz | S-region / sub-bass peaks down to ~20–50 Hz; also mid-register pairs | **Optional only.** `low_frequency_basis="zwicker_below_200hz"` exists; default remains `hk1978` (CHANGES.md open item). Applying the hybrid as default would change exported H&K columns. **Task 5 / author decision.** |
| `dissonance_models.SetharesDissonance._s` / `VassilakisDissonance` | `s = 0.24 / (0.0207 f + 18.96)` | Sethares (2005) eq. 3.9, a fit of Plomp–Levelt curves (musical range, typically ~100 Hz–2 kHz) | Pairwise on validated partials to 20 kHz | **No.** A frequency ceiling would change Sethares / Vassilakis exports. **Task 5.** |
| `density.py` `_hz_to_bark` | `13 arctan(0.00076 f) + 3.5 arctan((f/7500)^2)` | Zwicker / Traunmüller Bark approximation, ~20 Hz–15.5 kHz | Perceptual-density / masking helpers; production proximity path is Hz, not Bark | **No.** Production density path uses Hz (`proximity_axis="hz"`). Bark remains on unused/legacy perceptual helpers. A guard would change those helpers if they are still exported. **Task 5** if any Bark-axis export is live. |
| `constants.py` `NUM_CRITICAL_BANDS` / `BARK_TO_HZ_*` | 24 Bark bands; piecewise Hz-per-Bark slopes | Zwicker 24-band table, 0–24 Bark ≈ 20 Hz–15.5 kHz | Masking-threshold helpers | **No range check** on the inverse conversion. Legacy path. **Task 5** if those columns still ship. |

## Applied in this task

- Zwicker CB: NaN above 15.5 kHz + pair exclusion on F-037.
- Documented ERB valid-range constants (no numeric change).

## Deferred to Task 5 (guard would change exported numbers)

- `erb_bandwidth_hz` / `_erb_rate_hz` in `mir_descriptors` (optional ERB roughness; `erb_weighted_spectral_density`).
- `erb_bandwidth_hz` / `erb_rate` in `tools/spectral_density_hill.py` (ACD F-057–F-060; **frozen** this round).
- Hutchinson–Knopoff default (`hk1978` → hybrid). Author decision; see `HK_SUBBASS_BANDWIDTH.md`.
- Sethares / Vassilakis `s(f)` outside the Plomp–Levelt fitting band.
- Live Bark-axis density / masking exports, if any remain on the compiled sheet.
