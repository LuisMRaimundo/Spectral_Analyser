# Post-freeze backlog

Defects found after the v4.2.0 freeze. Do **not** fix these on the
frozen instrument unless a later tagged release is planned. Scope of
the closure programme was WP1–WP6 only.

## Local trombone G3 `core_H` n_fft sensitivity

`tests/phase_25/test_residual_footprint.py` live G3 / G♯3 checks
(`test_g3_core_h_ratio_within_three_percent_across_n_fft`,
`test_g3_gs3_core_h_does_not_follow_the_window`) still fail on the
author machine: `core_H` at n_fft=4096 vs 8192 differs by about 20 %
(WP1 measured 0.9909 vs 0.9961 on a related pair; the 3 % live
tolerance is tighter than the remaining window step).

CI machines skip these tests because
`D:\METAIS\TROMBONE\...\IOWA_Trb.T_ff.G3_SustainStable.aif` is absent.
They are **not** a WP4 CI failure. Production policy is `fft_policy=fixed`
at 8192 / 1024, so freeze-comparable corpora do not mix those windows.

## Listener study still scaffold

`tools/perceptual_pairs.py`, `tools/perceptual_agreement.py`, and
`docs/validation/PERCEPTUAL_PROTOCOL.md` are a protocol only. No
listening data were collected. EWSD remains an acoustic construct
until that study is run.

## One re-export per corpus after the tag

The freeze-ready tag is `v4.2.0`. The runbook
(`docs/REEXPORT_RUNBOOK.md`) was not executed in WP5/WP6. Each corpus
still needs **one** Stage 1–3 re-export under that tag, then
`python -m tools.verify_corpus <out>`. Do not iterate Stage 1 on the
same corpus after that export unless a new tag is cut.
