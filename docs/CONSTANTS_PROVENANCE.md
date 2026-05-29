# Numeric Constants Provenance Registry

This file documents the provenance of every numeric constant exported by
`constants.py`. Each entry records the constant name, its value, its
provenance class, and either a primary-source citation (full APA-7 entry
in `REFERENCES.md`) or a brief justification when the constant is an
internal default or a derived quantity.

Provenance classes:
- `primary_source` - value traceable to a peer-reviewed or standards publication
- `derived` - algebraically derived from another sourced constant
- `internal_default` - implementation choice without external authority; documented and tunable
- `convention` - values fixed by widespread engineering convention

## Spectral-analysis and FFT constants

- `DEFAULT_N_FFT` (`4096`) - `convention` - Power-of-two FFT default for efficient radix-2 DFT.
- `DEFAULT_HOP_LENGTH` (`1024`) - `convention` - Quarter-hop STFT default for Hann analysis workflows.
- `DEFAULT_PLOT_DPI` (`300`) - `convention` - Publication-grade raster export default.
- `DEFAULT_ZERO_PADDING` (`1`) - `convention` - No extra zero-padding by default.
- `MAX_ZERO_PADDING` (`8`) - `convention` - Common upper bound for analysis-only interpolation.
- `WINDOW_CHAR_FFT_PADDING` (`8`) - `convention` - Typical high-resolution zero-padding factor for window-shape measurement.
- `MAIN_LOBE_THRESHOLD_DB` (`-3.0`) - `convention` - Half-power criterion for main-lobe width.
- `SIDE_LOBE_EXCLUDE_REGION_BINS` (`4.0`) - `internal_default` - Pipeline-specific exclusion span around the peak.

## Energy-conservation and smoothing controls

- `ENERGY_CONSERVATION_TOLERANCE` (`0.1`) - `internal_default` - Operational QA tolerance for energy checks.
- `ENERGY_CONSERVATION_TOLERANCE_STRICT` (`0.02`) - `internal_default` - Tight QA gate for reference tests.
- `ENERGY_CONSERVATION_WARNING_THRESHOLD` (`0.05`) - `internal_default` - Warning-only threshold chosen for this codebase.
- `SMOOTHING_WINDOW_PERCENTAGE` (`0.05`) - `internal_default` - Heuristic smoothing span.
- `SMOOTHING_MIN_WINDOW_LENGTH` (`11`) - `convention` - Odd Savitzky-Golay window length convention.
- `SMOOTHING_POLYORDER` (`3`) - `convention` - Standard low-order Savitzky-Golay polynomial.
- `SMOOTHING_NOISE_FLOOR_PERCENTILE` (`15.0`) - `internal_default` - Heuristic percentile gate.
- `SMOOTHING_NOISE_FLOOR_MULTIPLIER` (`1.3`) - `internal_default` - Heuristic threshold scaling.

## Psychoacoustic and masking constants

- `SUBBASS_AGGREGATE_CUTOFF_HZ` (`80.0`) - `convention` - Audio-engineering sub-bass boundary convention.
- `NUM_CRITICAL_BANDS` (`24`) - `primary_source` - Bark-band count from Zwicker psychoacoustic framing (Zwicker & Fastl, 1990).
- `CRITICAL_BAND_MASKING_STRONG_THRESHOLD` (`0.5`) - `primary_source` - Bark-distance masking regime split anchored in critical-band literature (Zwicker & Fastl, 1990; Moore & Glasberg, 1983).
- `CRITICAL_BAND_MASKING_MODERATE_THRESHOLD` (`1.0`) - `primary_source` - Bark-distance masking regime split anchored in critical-band literature (Zwicker & Fastl, 1990; Moore & Glasberg, 1983).
- `CRITICAL_BAND_MASKING_WEAK_THRESHOLD` (`2.0`) - `primary_source` - Bark-distance masking regime split anchored in critical-band literature (Zwicker & Fastl, 1990; Moore & Glasberg, 1983).
- `MASKING_WITHIN_BAND_OFFSET_DB` (`-10.0`) - `internal_default` - Tuned masking offset in this implementation.
- `MASKING_ADJACENT_BAND_OFFSET_DB` (`-15.0`) - `internal_default` - Tuned masking offset in this implementation.
- `MASKING_ADJACENT_BAND_SLOPE_DB` (`-10.0`) - `internal_default` - Tuned masking slope in this implementation.
- `MASKING_NEARBY_BAND_OFFSET_DB` (`-20.0`) - `internal_default` - Tuned masking offset in this implementation.
- `MASKING_NEARBY_BAND_SLOPE_DB` (`-5.0`) - `internal_default` - Tuned masking slope in this implementation.
- `MASKING_FAR_BAND_OFFSET_DB` (`-30.0`) - `internal_default` - Tuned masking offset in this implementation.
- `MASKING_FAR_BAND_SLOPE_DB` (`-2.0`) - `internal_default` - Tuned masking slope in this implementation.
- `MASKING_ABSOLUTE_THRESHOLD_DB` (`-80.0`) - `convention` - Practical numerical/audibility floor convention in audio analysis.
- `FREQ_MIN_HZ` (`20.0`) - `convention` - Standard nominal lower audible bound.
- `FREQ_MAX_HZ` (`20000.0`) - `convention` - Standard nominal upper audible bound.
- `FREQ_MID_LOW_HZ` (`1000.0`) - `convention` - Common low/mid split in audio descriptors.
- `FREQ_MID_HIGH_HZ` (`runtime-configured`) - `convention` - Common mid/high split in audio descriptors.
- `EQUAL_LOUDNESS_LOW_WEIGHT_MIN` (`0.5`) - `internal_default` - Tuned lower clamp for project-specific weighting.
- `EQUAL_LOUDNESS_HIGH_WEIGHT_MAX` (`1.0`) - `convention` - Unit-gain cap convention.
- `EQUAL_LOUDNESS_HIGH_WEIGHT_DECAY` (`0.5`) - `internal_default` - Tuned decay constant for this implementation.
- `EQUAL_LOUDNESS_HIGH_FREQ_RANGE` (`1runtime-configured`) - `internal_default` - Tuned frequency span for this implementation.

## Harmonic, inharmonicity, and validation constants

- `HARMONIC_DETECTION_THRESHOLD_DB` (`-60.0`) - `convention` - Common peak-picking floor in spectral analysis.
- `SNR_THRESHOLD_DB` (`6.0`) - `convention` - Standard detectability margin convention.
- `DISSONANCE_PAIRWISE_PARTIAL_CAP` (`80`) - `convention` - Computational cap convention for pairwise roughness models.
- `HARMONIC_TOLERANCE_BASE` (`0.1`) - `convention` - Baseline tolerance convention for robust harmonic matching.
- `HARMONIC_TOLERANCE_ADAPTIVE_FACTOR` (`0.1`) - `convention` - Adaptive tolerance scaling convention for robust matching.
- `HARMONIC_MAX_CHECK` (`100`) - `convention` - Practical harmonic-order cap convention.
- `HARMONIC_MATCH_TOLERANCE_CENTS` (`35.0`) - `convention` - Standard cents-domain matching tolerance convention.
- `HARMONIC_VALIDATION_MAX_HARMONICS` (`1024`) - `convention` - Power-of-two validation cap convention.
- `HARMONIC_VALIDATION_WARN_MEDIAN_ABS_CENTS` (`25.0`) - `internal_default` - QA warning threshold tuned for this pipeline.
- `HARMONIC_VALIDATION_WARN_MAX_ABS_CENTS` (`80.0`) - `internal_default` - QA warning threshold tuned for this pipeline.
- `HARMONIC_VALIDATION_WARN_MISSING_RATIO` (`0.55`) - `internal_default` - QA warning threshold tuned for this pipeline.
- `HARMONIC_VALIDATION_WARN_NON_HARMONIC_CANDIDATE_RATIO` (`0.35`) - `internal_default` - QA warning threshold tuned for this pipeline.
- `HARMONIC_VALIDATION_WARN_RMS_CENTS` (`30.0`) - `internal_default` - QA warning threshold tuned for this pipeline.
- `HARMONIC_ALIGNMENT_EXCELLENT_MIN_ORDER_MATCH_RATIO` (`0.85`) - `internal_default` - Project-specific status threshold.
- `HARMONIC_ALIGNMENT_EXCELLENT_MAX_WEIGHTED_MEAN_ABS_CENTS` (`10.0`) - `internal_default` - Project-specific status threshold.
- `HARMONIC_ALIGNMENT_EXCELLENT_MAX_P95_ABS_CENTS` (`18.0`) - `internal_default` - Project-specific status threshold.
- `HARMONIC_ALIGNMENT_GOOD_MIN_ORDER_MATCH_RATIO` (`0.7`) - `internal_default` - Project-specific status threshold.
- `HARMONIC_ALIGNMENT_GOOD_MAX_WEIGHTED_MEAN_ABS_CENTS` (`18.0`) - `internal_default` - Project-specific status threshold.
- `HARMONIC_ALIGNMENT_EXCELLENT_MAX_MEAN_ABS_CENTS` (`10.0`) - `internal_default` - Project-specific status threshold.
- `HARMONIC_ALIGNMENT_GOOD_MAX_MEAN_ABS_CENTS` (`18.0`) - `internal_default` - Project-specific status threshold.
- `INHARMONICITY_FIT_ORDER_CAP` (`40`) - `convention` - Practical order cap convention for stable fitting.
- `INHARMONICITY_FIT_CENTS_WINDOW` (`80.0`) - `convention` - Common local fit window convention in cents domain.
- `INHARMONICITY_B_ENABLE_THRESHOLD` (`1e-05`) - `internal_default` - Numerical enable threshold chosen for this codebase.
- `FIXED_FREQ_MAX_HZ` (`20000.0`) - `derived` - Set equal to `FREQ_MAX_HZ` for comparability contract.
- `HARMONIC_COMPLETENESS_WEIGHT_BASE` (`1.0`) - `convention` - Base coefficient for `1/n` completeness weighting.
- `HARMONIC_COMPLETENESS_MAX_HARMONICS` (`100`) - `derived` - Explicitly matched to `HARMONIC_MAX_CHECK`.

## Density and MIR-adjacent constants

- `SPARSITY_THRESHOLD_RELATIVE` (`0.01`) - `internal_default` - Heuristic occupancy threshold.
- `SPARSITY_BANDWIDTH_FACTOR` (`4.0`) - `convention` - Four-sigma effective-span convention.
- `SPECTRAL_CONCENTRATION_DEFAULT_PEAKS` (`5`) - `convention` - Top-k summary convention.
- `PERCEPTUAL_DENSITY_POWER_EXPONENT` (`0.3`) - `internal_default` - Project-specific weighting exponent.
- `PERCEPTUAL_DENSITY_OCCUPANCY_WEIGHT` (`0.5`) - `internal_default` - Project-specific blend weight.
- `PERCEPTUAL_DENSITY_UNIFORMITY_WEIGHT` (`0.3`) - `internal_default` - Project-specific blend weight.
- `PERCEPTUAL_DENSITY_COMPLETENESS_WEIGHT` (`0.2`) - `internal_default` - Project-specific blend weight.
- `PERCEPTUAL_DENSITY_LOG_SCALE_FACTOR` (`3.0`) - `internal_default` - Project-specific nonlinearity scaling.
- `ATTACK_TIME_THRESHOLD` (`0.9`) - `convention` - 90%-rise threshold convention for attack-time style descriptors.
- `SPECTRAL_ROLLOFF_PERCENTILE` (`0.85`) - `primary_source` - Timbre Toolbox rolloff percentile convention (Peeters et al., 2011).

## Normalization and metric scaling constants

- `NORMALIZATION_TARGET_RMS_DB` (`-20.0`) - `convention` - Common analysis loudness target convention.
- `NORMALIZATION_MIN_AMPLITUDE` (`1e-20`) - `derived` - Matched to `EPSILON_AMPLITUDE` to avoid `log(0)`.
- `MAX_ABS_DENSITY` (`20.0`) - `internal_default` - Project-specific clipping guard.
- `MAX_SCALED_DENSITY` (`2000.0`) - `internal_default` - Project-specific clipping guard.
- `MAX_COMBINED_DENSITY` (`1000.0`) - `internal_default` - Project-specific clipping guard.
- `DENSITY_METRIC_WEIGHT_D` (`0.3`) - `internal_default` - Project-specific blend weight.
- `DENSITY_METRIC_WEIGHT_S` (`0.2`) - `internal_default` - Project-specific blend weight.
- `DENSITY_METRIC_WEIGHT_E` (`0.2`) - `internal_default` - Project-specific blend weight.
- `DENSITY_METRIC_WEIGHT_C` (`0.3`) - `internal_default` - Project-specific blend weight.
- `TOTAL_METRIC_SCALE` (`10.0`) - `convention` - Conventional 0-10 reporting scale.

## Runtime and numerical-stability constants

- `MAX_SIGNAL_LENGTH` (`20000000`) - `internal_default` - Operational memory-protection cap.
- `SIGNAL_TRUNCATION_FACTOR` (`5`) - `internal_default` - Operational truncation heuristic.
- `LARGE_SIGNAL_THRESHOLD` (`5000000`) - `internal_default` - Operational "large signal" threshold.
- `FFT_DOWNGRADE_FACTOR` (`4`) - `internal_default` - Operational fallback heuristic.
- `FFT_MIN_SIZE` (`1024`) - `convention` - Minimum power-of-two FFT convention.
- `EPSILON` (`1e-12`) - `convention` - Standard numerical-stability epsilon magnitude.
- `EPSILON_POWER` (`1e-12`) - `derived` - Explicitly equal to `EPSILON`.
- `EPSILON_AMPLITUDE` (`1e-20`) - `convention` - Standard amplitude-floor convention.
- `EPSILON_FREQUENCY` (`1e-06`) - `convention` - Practical frequency-floor convention.
- `CLIP_MIN` (`0.0`) - `convention` - Lower bound for normalized clipping.
- `CLIP_MAX` (`1.0`) - `convention` - Upper bound for normalized clipping.
- `KAISER_DEFAULT_BETA` (`6.5`) - `convention` - Widely used moderate-sidelobe Kaiser setting (Harris, 1978).
- `GAUSSIAN_DEFAULT_STD_FACTOR` (`8.0`) - `convention` - Common `N/8` Gaussian-window spread convention.

## Bark conversion constants

### `BARK_COEFFICIENT_*` family
- `BARK_COEFFICIENT_1` (`13.0`) - `primary_source` - Bark conversion coefficient from Zwicker-style analytic mapping (Zwicker & Fastl, 1990).
- `BARK_COEFFICIENT_2` (`0.00076`) - `primary_source` - Bark conversion coefficient from Zwicker-style analytic mapping (Zwicker & Fastl, 1990).
- `BARK_COEFFICIENT_3` (`3.5`) - `primary_source` - Bark conversion coefficient from Zwicker-style analytic mapping (Zwicker & Fastl, 1990).
- `BARK_COEFFICIENT_4` (`7500.0`) - `primary_source` - Bark conversion coefficient from Zwicker-style analytic mapping (Zwicker & Fastl, 1990).

### `BARK_TO_HZ_*` family
- `BARK_TO_HZ_LOW_THRESHOLD` (`2.0`) - `primary_source` - Piecewise Bark-to-Hz approximation anchored in Zwicker psychoacoustic scaling (Zwicker & Fastl, 1990).
- `BARK_TO_HZ_MID_THRESHOLD` (`10.0`) - `primary_source` - Piecewise Bark-to-Hz approximation anchored in Zwicker psychoacoustic scaling (Zwicker & Fastl, 1990).
- `BARK_TO_HZ_LOW_FREQ_BASE` (`200.0`) - `primary_source` - Piecewise Bark-to-Hz approximation anchored in Zwicker psychoacoustic scaling (Zwicker & Fastl, 1990).
- `BARK_TO_HZ_LOW_FREQ_SLOPE` (`100.0`) - `primary_source` - Piecewise Bark-to-Hz approximation anchored in Zwicker psychoacoustic scaling (Zwicker & Fastl, 1990).
- `BARK_TO_HZ_HIGH_FREQ_BASE` (`1000.0`) - `primary_source` - Piecewise Bark-to-Hz approximation anchored in Zwicker psychoacoustic scaling (Zwicker & Fastl, 1990).
- `BARK_TO_HZ_HIGH_EXP_FACTOR` (`3.0`) - `primary_source` - Piecewise Bark-to-Hz approximation anchored in Zwicker psychoacoustic scaling (Zwicker & Fastl, 1990).

## Validation bounds and publication-policy numerics

- `TOLERANCE_DEFAULT` (`5.0`) - `internal_default` - Project-specific default tolerance.
- `TOLERANCE_MIN` (`0.0`) - `convention` - Non-negative tolerance bound convention.
- `TOLERANCE_MAX` (`100.0`) - `internal_default` - Project-specific upper tolerance bound.
- `FREQ_VALIDATION_MIN` (`0.0`) - `derived` - Equal to `TOLERANCE_MIN` (same non-negative floor).
- `FREQ_VALIDATION_MAX` (`20000.0`) - `derived` - Equal to `FREQ_MAX_HZ`.
- `AMP_VALIDATION_MIN_DB` (`-120.0`) - `convention` - Typical practical floor for dB-domain validation.
- `AMP_VALIDATION_MAX_DB` (`20.0`) - `convention` - Typical practical ceiling for dB-domain validation.

## Phase-7 occupancy-ratio symmetry constants

- `STRENGTH_OCCUPANCY_WEIGHT_HARMONIC` (`1.0`) - `convention` - Neutral equal-weight symmetry convention used by Phase-7 policy.
- `STRENGTH_OCCUPANCY_WEIGHT_INHARMONIC` (`1.0`) - `convention` - Neutral equal-weight symmetry convention used by Phase-7 policy.
- `STRENGTH_OCCUPANCY_WEIGHT_SUBBASS` (`1.0`) - `convention` - Neutral equal-weight symmetry convention used by Phase-7 policy.
