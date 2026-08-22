# References

This file is the canonical bibliography for all theoretical anchors used in the Spectral_Analyser codebase. Inline `References` blocks in individual modules use short form; full APA-7 entries live here. The dissertation that consumes this software should cite from this file.

## Spectral analysis and DFT/window theory
- Harris, F. J. (1978). On the use of windows for harmonic analysis with the discrete Fourier transform. *Proceedings of the IEEE, 66*(1), 51–83.
- Heinzel, G., Rüdiger, A., & Schilling, R. (2002). *Spectrum and spectral density estimation by the Discrete Fourier transform (DFT), including a comprehensive list of window functions and some new at-top windows* (Technical report). Max-Planck-Institut für Gravitationsphysik.

## Inharmonicity and string acoustics
- Fletcher, H. (1962). Normal vibration frequencies of a stiff piano string. *Journal of the Acoustical Society of America, 36*(1), 203–209.
- Fletcher, N. H., & Rossing, T. D. (1998). *The physics of musical instruments* (2nd ed.). Springer.

## Psychoacoustics
- Sethares, W. A. (2005). *Tuning, timbre, spectrum, scale* (2nd ed.). Springer.
- Fechner, G. T. (1860). *Elemente der Psychophysik*. Breitkopf und Härtel.
- Stevens, S. S. (1955). The measurement of loudness. *Journal of the Acoustical Society of America, 27*(5), 815–829.
- Zwicker, E., Flottorp, G., & Stevens, S. S. (1957). Critical band width in loudness summation. *Journal of the Acoustical Society of America, 29*(5), 548–557.
- Zwicker, E., & Fastl, H. (1990). *Psychoacoustics: Facts and models*. Springer.
- Moore, B. C. J., & Glasberg, B. R. (1983). Suggested formulae for calculating auditory-filter bandwidths and excitation patterns. *Journal of the Acoustical Society of America, 74*(3), 750–753.
- Glasberg, B. R., & Moore, B. C. J. (1990). Derivation of auditory filter shapes from notched-noise data. *Hearing Research, 47*(1–2), 103–138.
- Moore, B. C. J., Glasberg, B. R., & Baer, T. (1997). A model for the prediction of thresholds, loudness, and partial loudness. *Journal of the Audio Engineering Society, 45*(4), 224–240.
- Zwicker, E., & Fastl, H. (2007). *Psychoacoustics: Facts and models* (3rd ed.). Springer.
- International Organization for Standardization. (2017a). *Acoustics — Methods for calculating loudness — Part 1: Zwicker method* (ISO 532-1:2017).
- International Organization for Standardization. (2017b). *Acoustics — Methods for calculating loudness — Part 2: Moore-Glasberg method* (ISO 532-2:2017).
- Hill, M. O. (1973). Diversity and evenness: A unifying notation and its consequences. *Ecology, 54*(2), 427–432.
- Jost, L. (2006). Entropy and diversity. *Oikos, 113*(2), 363–375.
- Hurley, N., & Rickard, S. (2009). Comparing measures of sparsity. *IEEE Transactions on Information Theory, 55*(10), 4723–4741.
- Parncutt, R. (1989). *Harmony: A psychoacoustical approach*. Springer.
- Parncutt, R., & Strasburger, H. (1994). Applying psychoacoustics in composition: “Harmonic” progressions of “nonharmonic” sonorities. *Perspectives of New Music, 32*(2), 88–129.
- Huron, D. (1989). Voice segregation in selected polyphonic keyboard works by Johann Sebastian Bach (Doctoral dissertation). University of Nottingham.
- Plomp, R., & Levelt, W. J. M. (1965). Tonal consonance and critical bandwidth. *Journal of the Acoustical Society of America, 38*(4), 548–560.

## Timbre and MIR descriptors
- Pollard, H. F., & Jansson, E. V. (1982). A tristimulus method for the specification of musical timbre. *Acustica, 51*(3), 162–171.
- Peeters, G., Giordano, B. L., Susini, P., Misdariis, N., & McAdams, S. (2011). The Timbre Toolbox: Extracting audio descriptors from musical signals. *Journal of the Acoustical Society of America, 130*(5), 2902–2916.

## Detection theory and signal detection
- Rohling, H. (1983). Radar CFAR thresholding in clutter and multiple target situations. *IEEE Transactions on Aerospace and Electronic Systems, AES-19*(4), 608–621.

## Statistical inference and resampling
- Lin, J. (1991). Divergence measures based on the Shannon entropy. *IEEE Transactions on Information Theory, 37*(1), 145–151.
- Gelman, A., Carlin, J. B., Stern, H. S., Dunson, D. B., Vehtari, A., & Rubin, D. B. (2013). *Bayesian data analysis* (3rd ed.). CRC Press.
- Efron, B., & Tibshirani, R. J. (1993). *An introduction to the bootstrap*. Chapman & Hall/CRC.

## Scientific software methodology
- Hatton, L. (1997). The T-experiments: Errors in scientific software. *IEEE Computational Science and Engineering, 4*(2), 27–38.
- Soergel, D. A. W. (2015). Rampant software errors may undermine scientific results. *F1000Research, 3*, 303.

## Module-to-reference mapping

| Module | References used |
|---|---|
| `spectral_normalization.py` | Harris (1978); Heinzel et al. (2002) |
| `inharmonicity_model.py` | Fletcher (1962); Fletcher & Rossing (1998) |
| `harmonic_peak_validation.py` (CFAR acceptance) | Rohling (1983) |
| `density_uncertainty.py` (bootstrap CI / UQ) | Efron & Tibshirani (1993) |
| `subbass_policy.py` | Zwicker & Fastl (1990) |
| `constants.py` (`DENSITY_WEIGHT_FUNCTION_DEFAULT`) | Fechner (1860); Stevens (1955); Zwicker & Fastl (1990) |
| `dissonance_models.py` (`SetharesDissonance`) | Sethares (2005) |
| `mir_descriptors.py` | Plomp & Levelt (1965); Zwicker, Flottorp & Stevens (1957); Parncutt (1989); Zwicker & Fastl (2007); Glasberg & Moore (1990); Pollard & Jansson (1982); Peeters et al. (2011) |
| `tools/spectral_density_hill.py` | Glasberg & Moore (1990); Moore & Glasberg (1983); Hill (1973); Jost (2006); Hurley & Rickard (2009); Moore, Glasberg & Baer (1997); ISO 532-2:2017 |
| `adaptive_density_engine.py` | Lin (1991); Gelman et al. (2013) |
| `metric_contract.py` | Hatton (1997); Soergel (2015) |
| `temporal_segmentation.py` | Peeters et al. (2011) |
