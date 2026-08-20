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
