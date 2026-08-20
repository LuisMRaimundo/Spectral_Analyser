# Post-freeze backlog

Defects found after the v4.2.0 freeze. Do **not** fix these on the
frozen instrument unless a later tagged release is planned. Scope of
the closure programme was WP1–WP6 only.

## Local trombone G3 `core_H` n_fft sensitivity

**Confirmed P1, 20 August 2026, commit `aa24de8`.** Same dated run as
`RESOLUTION_DEPENDENCE_DIAGNOSIS.md` § P1. Live Stage 1–3 G3 swap
(`IOWA_Trb.T_ff.G3_SustainStable.aif`, SHA-256 `91dbf93d…d20a`,
profile `wf=log|dst=-90.0|ceil=20000.0|fft=fixed|seg=sustain_primary_stable_diagnostic|elig=1`):

| n_fft / hop | `core_harmonic_energy_ratio` | `core_residual_energy_ratio` | EWSD |
|-------------|-----------------------------:|-----------------------------:|-----:|
| 8192 / 1024 | 0.9222 | 0.0778 | 91.31 |
| 4096 / 512 | 0.7878 | 0.2122 | 72.72 |

`core_H` relative Δ = 14.6 %. 3 % tolerance: **FAIL**. The WP1 diagnosis
table (0.9969 vs 0.9993) does **not** describe this export. Synthetic
WP1 tests (`tests/phase_25`, no live audio) still pass. CI skips the
live G3 tests when the AIF is absent; that skip is not a WP4 failure.

Production policy (`fft_policy=fixed` at 8192/1024) avoids mixing the
windows. It does not make the swap invariant. P5/P6 are blocked until
this is resolved.

**R1, 20 August 2026, tag `v4.2.2` = `64a2282`.** Same G3 file, full
Stage 1–3, compiled `Spectral_Density_Metrics` only:
`core_H` 0.7878 / 0.9222 / 0.9760 and EWSD 72.72 / 91.31 / 118.04 at
n_fft 4096 / 8192 / 16384. 3 % tolerance: **FAIL**. Flute A♯4 fails
on EWSD and `core_H`. The 1.2 s synthetic tone has `core_H` = 1.0 on
the Stage-3 sheet but no `EWSD_score_acoustic_balanced` /
`effective_partial_density` columns (EWSD NaN on `Stage3_Diagnostics`).
WP1 is **FAILED** on the canonical Stage-3 path. R2–R6 stopped.

## Listener study still scaffold

`tools/perceptual_pairs.py`, `tools/perceptual_agreement.py`, and
`docs/validation/PERCEPTUAL_PROTOCOL.md` are a protocol only. No
listening data were collected. EWSD remains an acoustic construct
until that study is run.

## One re-export per corpus after the tag

The freeze-ready tag is `v4.2.1` (supersedes `v4.2.0`; that tag is
kept). Each citation corpus still needs **one** Stage 1–3 re-export
under `v4.2.1`, then `python -m tools.verify_corpus <out>`. Do not
iterate Stage 1 on the same corpus after that export unless a new tag
is cut. Pre-tag baselines: `docs/validation/pretag_evidence/`.
