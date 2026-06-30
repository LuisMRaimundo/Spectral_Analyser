# Spectral_Analyser v51 Release Notes

## Scientific consolidation scope

Version 51 consolidates Phases 1-6 into a single reproducible analytical profile for per-note spectral density analysis. The release finalizes the separation of observation from prior, harmonizes low-frequency policy, normalizes FFT-tier comparability, introduces explicit inharmonicity parameterization, extends MIR descriptor coverage with temporal segmentation, and documents parameter provenance at the constant/signature-default level.

## Methodological changes by phase

### Phase 1: Observation-prior decoupling and deterministic traversal

Per-note outputs now expose pure observation weights (`pure_observation_w_h`, `pure_observation_w_i`, `pure_observation_w_s`) as canonical evidence channels, while prior-smoothed blends are retained only as documented legacy compatibility fields. Adaptive updates consume observation-only values, aligning with probabilistic learning practice that separates likelihood evidence from posterior updating dynamics (Bishop, 2006; Bottou, 2010). File traversal is deterministic by nominal f0 to improve reproducibility of adaptive trajectories.

### Phase 2: Unified sub-bass semantics and profile-path correctness

A single operational sub-bass definition is enforced via `SubBassPolicy.upper_bound_hz = min(0.5*f0, 80 Hz)`, reducing semantic drift across extraction, protection, and compilation stages. Stage-2 corpus profile weighting now consistently applies all three weights (harmonic/inharmonic/sub-bass), and compiled outputs expose explicit provenance (`density_weights_source`) and an invariant per-note comparator (`density_metric_raw_per_note_balance`) for methodological transparency (Zwicker & Fastl, 1990).

### Phase 3: FFT-tier normalization and diagnostic coherence

Absolute amplitude/power sums now include tier-normalized companions to preserve cross-note comparability under different FFT lengths. Diagnostic density aliasing was repaired by promoting unit-coherent effective-component diagnostics and retaining legacy alias labels as compatibility-only metadata. This reduces risk of conflating scale-dependent accumulators with participation-ratio descriptors (Cogan, 1984; Edwards & Thouless, 1972).

### Phase 4: Inharmonicity as a modeled parameter

Harmonic assignment now supports stiff-string stretching by fitting inharmonicity coefficient `B` in `f_n = n f0 sqrt(1 + B n^2)` before harmonic mask construction. Adaptive per-partial tolerance also incorporates FFT-bin spacing constraints, reducing deterministic quantization misclassification as inharmonic noise. The model remains backward-compatible for harmonic instruments where `B` is near zero (Fletcher, 1962; Fletcher, Blackham, & Stratton, 1962; Galembo & Askenfelt, 1994; Järveläinen, Karjalainen, & Tolonen, 2001; McAulay & Quatieri, 1986; Serra & Smith, 1990).

### Phase 5: Extended MIR descriptors and temporal segmentation

Descriptor coverage was expanded toward MPEG-7/Timbre Toolbox comparability, including spectral moments, irregularity, tristimulus, flatness, rolloff, roughness, and ERB-weighted metrics, plus attack/sustain/release segmentation and log-attack-time output. This supports richer timbral profiling beyond sustain-biased analyses and improves external comparability to contemporary descriptor literature (Aures, 1985; Krimphoff, McAdams, & Winsberg, 1994; Moore & Glasberg, 1983; Peeters, 2004; Peeters et al., 2011; Pollard & Jansson, 1982).

### Phase 6: Parameter provenance and workbook consolidation

All numeric constants and phase-touched signature defaults are now indexed in `docs/parameter_provenance.md`. Constants lacking bibliographic evidence are explicitly marked `TODO: bibliographic justification required`, and a single import-time warning exposes remaining provenance debt. Strict alias fields are moved to `Legacy_Aliases` so primary sheets remain analytically narrow without breaking backward compatibility paths.

## Downstream migration notes

- Use canonical observation fields (`pure_observation_w_*`) for inference; treat legacy smoothed/alias fields as compatibility-only.
- For FFT-comparable absolute sums, consume `*_tier_normalized` columns.
- Distinguish weighting regimes with `density_weights_source`; use `density_metric_raw_per_note_balance` for per-note-only analyses.
- Treat segmented descriptor suffixes (`_on_attack`, `_on_sustain`, `_on_release`, `_on_sustain_segment`) as distinct temporal constructs.
- Retrieve strict aliases from `Legacy_Aliases`; avoid reintroducing them into primary inferential models.

## Verification status in this release cycle

- Full automated phase suite: passed (`15 passed, 1 skipped`).
- Clarinet corpus harmonicity benchmark (`mean inharmonicity_coefficient_B < 1e-5`): test present but corpus-gated; skipped when `CLARINET_SUSTAINS_DIR` is unset.
- Sub-bass observation guard (`obs_w_S < 0.05`) and enumeration-order invariance: phase regression tests passed in the Phase 6 suite.

## References (APA)

- Aures, W. (1985). Ein Berechnungsverfahren der Rauhigkeit. *Acustica, 58*(5), 268-281.
- Bishop, C. M. (2006). *Pattern recognition and machine learning*. Springer.
- Bottou, L. (2010). Large-scale machine learning with stochastic gradient descent. In Y. Lechevallier & G. Saporta (Eds.), *Proceedings of COMPSTAT'2010* (pp. 177-186). Springer. https://doi.org/10.1007/978-3-7908-2604-3_16
- Cogan, R. (1984). *New images of musical sound*. Harvard University Press.
- Edwards, J. T., & Thouless, D. J. (1972). Numerical studies of localization in disordered systems. *Journal of Physics C: Solid State Physics, 5*(8), 807-820. https://doi.org/10.1088/0022-3719/5/8/007
- Fletcher, H. (1962). *The physics of musical instruments*. Dover.
- Fletcher, H., Blackham, E. D., & Stratton, R. (1962). Quality of piano tones. *The Journal of the Acoustical Society of America, 34*(6), 749-761.
- Galembo, A., & Askenfelt, A. (1994). Signal representation and estimation of spectral parameters by inharmonic comb filtering. *IEEE Transactions on Speech and Audio Processing, 2*(2), 197-203.
- Järveläinen, H., Karjalainen, M., & Tolonen, T. (2001). Computationally efficient analysis of beating and inharmonicity in musical tones. *Journal of the Audio Engineering Society, 49*(7/8), 695-708.
- Krimphoff, J., McAdams, S., & Winsberg, S. (1994). Caractérisation du timbre des sons complexes. II. Analyses acoustiques et quantification psychophysique. *Journal de Physique IV*, 4(C5), 625-628.
- McAulay, R. J., & Quatieri, T. F. (1986). Speech analysis/synthesis based on a sinusoidal representation. *IEEE Transactions on Acoustics, Speech, and Signal Processing, 34*(4), 744-754.
- Moore, B. C. J. (2012). *An introduction to the psychology of hearing* (6th ed.). Brill.
- Moore, B. C. J., & Glasberg, B. R. (1983). Suggested formulae for calculating auditory-filter bandwidths and excitation patterns. *The Journal of the Acoustical Society of America, 74*(3), 750-753.
- Peeters, G. (2004). *A large set of audio features for sound description (similarity and classification) in the CUIDADO project*. IRCAM.
- Peeters, G., Giordano, B., Susini, P., Misdariis, N., & McAdams, S. (2011). The Timbre Toolbox: Extracting audio descriptors from musical signals. *The Journal of the Acoustical Society of America, 130*(5), 2902-2916.
- Pollard, H. F., & Jansson, E. V. (1982). A tristimulus method for the specification of musical timbre. *Acta Acustica united with Acustica, 51*(3), 162-171.
- Serra, X., & Smith, J. O. (1990). Spectral modeling synthesis: A sound analysis/synthesis system based on a deterministic plus stochastic decomposition. *Computer Music Journal, 14*(4), 12-24.
- Zwicker, E., & Fastl, H. (1990). *Psychoacoustics: Facts and models*. Springer.
