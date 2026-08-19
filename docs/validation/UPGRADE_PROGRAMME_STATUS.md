# Upgrade programme status (post-`70525e3`)

Measurable acceptance, not a 1–100 rating. One git phase / PR per letter.
F-042 / F-047 / F-048 / F-049 algebra is unchanged unless a formula-version
bump is recorded.

| Phase | Topic | Tests | Acceptance | Status |
|-------|--------|-------|------------|--------|
| A | Confirmed-inharmonic partial class | `tests/phase_14/test_inharmonic_confirmation.py` | A2-like floor → 0 confirmed, all `rejected_floor` on CFAR. Piano B=2e-4, 30 stretched → 0 I, 30 H (`rejected_stretched_harmonic`). Bell, 10 partials at 20 dB SNR → exactly 10 confirmed. Two H3 sidelobes → 0 confirmed, `rejected_leakage` guarding order 3. | **in this PR** |
| B | Temporal persistence | `tests/phase_15/` | H1–H8 on A2 ≥ 0.95; three 12 kHz floor bins < 0.3 even with body stop off. Steady partial accepted, 2-frame burst rejected. | pending |
| C | Independent high-n guards | `tests/phase_16/` | Body stop off, A2 still H1–H8. Run-2 duplicate notes pass invariant; `accepted_slots_above_body_stop = 0`. | pending |
| D | Uncertainty by default | `tests/phase_17/` | CI bands on Stage 3 EWSD; A2 EPD CI reported; < 10 independent frames flagged. | pending |
| E | Provenance | `tests/phase_18/` | Fresh export stamps commit + version. `verify_export.py` on run-2 → not comparable. | pending |
| F | Schema / count hygiene | `tests/phase_19/` | One meaning per header; F-020 rows contribute 0 to S sums. | pending |
| G | Weight function φ | `tests/phase_20/` | Sensitivity report on tuba corpus; README records ρ. | pending |
| H | Reproducibility command | `tests/phase_21/` | Tuba *pp* re-export + Stage 3 diff vs 19 Aug Análise 3. | pending |
| I | Construct validation | `tests/validation/synthetic_corpus/` | Recover N ±1, B ±10 %, EPD ±10 %, confirmed-I exact at SNR 10–40 dB. Perceptual scaffold only (no data collection). | pending |

## Phase A notes

Module: `inharmonic_confirmation.py`. Constants: `CFAR_PFA`,
`INHARMONIC_MIN_PROMINENCE_DB`, `PARTIAL_PERSISTENCE_MIN_FRACTION`.
New sheet: `Confirmed_Inharmonic_Partials`. Persistence uses a default
fraction of 1.0 when the Phase B frame table is absent; A2 floor
rejection is CFAR, not persistence.
