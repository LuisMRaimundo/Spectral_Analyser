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
- `derived_from_window` - geometry taken from the analysis-window main lobe (Harris, 1978)

## Spectral-analysis and FFT constants

- `DEFAULT_N_FFT` (`4096`) - `convention` - Power-of-two FFT default for efficient radix-2 DFT.
- `DEFAULT_HOP_LENGTH` (`1024`) - `convention` - Quarter-hop STFT default for Hann analysis workflows.
- `FFT_POLICY_DEFAULT` (`fixed`) - `convention` - Comparable-corpus FFT policy. One n_fft/hop for every note; `adaptive_tier` remains behind an explicit flag and sets `is_primary_comparable_profile = False`.
- `FIXED_N_FFT_DEFAULT` (`8192`) - `convention` - Default window for cross-note comparable corpora (`fft_policy=fixed`).
- `FIXED_HOP_LENGTH_DEFAULT` (`1024`) - `convention` - Hop for the fixed policy (`n_fft/8` at 8192).
- `MIN_INDEPENDENT_FRAMES` (`8`) - `internal_default` - WP3 eligibility floor. Below this, `ewsd_primary_analysis_eligible` is False.
- `STABLE_REPRESENTATIVENESS_MAX_RATIO` (`1.3`) - `internal_default` - Flag `stable_segment_unrepresentative` when full/stable EWSD exceeds this ratio.
- `STABLE_CENTROID_MAX_RATIO` (`2.0`) - `internal_default` - Flag `stable_segment_unrepresentative` when max/min spectral centroid exceeds this ratio.
- `SEGMENT_POLICY_DEFAULT` (`sustain_primary_stable_diagnostic`) - `internal_default` - Sustain cut is primary; stable sibling is diagnostic only.
- `ELIGIBILITY_POLICY_VERSION` (`1`) - `internal_default` - Profile-id `elig` token for the WP3 gate (not the per-note boolean).
- `ENERGY_BASIS_PSD_PER_HZ` (`psd_per_hz`) - `convention` - Energy sums are Heinzel PSD integrated over Hz (Harris, 1978; Heinzel et al., 2002).
- `HANN_ENBW_BINS` (`1.5`) - `primary_source` - Hann equivalent noise bandwidth in bins (Harris, 1978; Heinzel, Rüdiger & Schilling, 2002). Runtime ENBW is computed from the analysis window.
- `RESIDUAL_EXCLUSION_FOOTPRINT` (`8.0`) - `derived_from_window` - Residual-exclusion diameter in bins for a Blackman–Harris 4-term window (first nulls at ±4; Harris, 1978). Peak-power still uses ENBW. Runtime width follows the analysis window via `residual_exclusion_footprint_bins`.
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
- `_ROUGHNESS_ERB_SLOPE` (`0.108`) / `_ROUGHNESS_ERB_INTERCEPT_HZ` (`24.7`) - `primary_source` - Glasberg & Moore (1990) ERB used **only** as `bandwidth_basis="erb"` in `mir_descriptors`. Independent of `tools/spectral_density_hill.py`.
- `PL_CB_FRACTION` (`0.25`) - `primary_source` - Plomp & Levelt (1965) / Parncutt (1989): peak at ~0.25 critical bandwidths.
- `PL_ROUGHNESS_CUTOFF_CB` (`1.2`) - `primary_source` - Hutchinson & Knopoff (1978) hard zero of `g` beyond 1.2 CB. Optional `cutoff_cb` on F-037; default `None` (no cutoff). Open item whether this should become the default.
- `CB_ZWICKER_A/B/C/EXP` (`25`, `75`, `1.4`, `0.69`) - `primary_source` - Zwicker & Fastl (2007) `CB(f)=25+75(1+1.4(f/1000)^2)^0.69`, a fit to the Zwicker, Flottorp & Stevens (1957) critical-band lineage that Plomp & Levelt (1965) used for the 25%-of-CB result. Default `bandwidth_basis="zwicker_cb"` is **provenance-consistent**: applying P&L's 0.25 factor to Glasberg & Moore (1990) ERB is a unit mismatch with the source. Overlay on P&L Fig. 10 is outstanding but non-blocking corroboration. See [`docs/validation/ROUGHNESS_BANDWIDTH_BASIS.md`](validation/ROUGHNESS_BANDWIDTH_BASIS.md).
- `CB_ZWICKER_VALID_MAX_HZ` (`15500`) - `primary_source` - Upper end of the Bark scale / Zwicker CB lineage. `critical_bandwidth_zwicker_hz` returns NaN above this; F-037 drops pairs whose higher member exceeds it.
- `ERB_VALID_MIN_HZ` / `ERB_VALID_MAX_HZ` (`100`, `15000`) - `primary_source` - Glasberg & Moore (1990) approximate fitted range. Documented only; not a numeric guard (a guard would change optional `bandwidth_basis="erb"` and ACD ERB merge). See Task 5 list in [`BANDWIDTH_VALIDITY_AUDIT.md`](validation/BANDWIDTH_VALIDITY_AUDIT.md).
- `BANDWIDTH_BASIS_DEFAULT` (`zwicker_cb`) - `primary_source` - Provenance-consistent default (P&L 1965 × Zwicker CB lineage). Not an ERB-based default.
- `HK_CBW_COEFF` / `HK_CBW_EXP` (`1.72`, `0.65`) - `primary_source` - Hutchinson & Knopoff (1978) Fig. 2. Default of `HutchinsonKnopoffDissonance.cbw`.
- `HK_LOW_FREQUENCY_CUTOFF_HZ` (`200`) - `internal_default` - Switch point for optional `low_frequency_basis="zwicker_below_200hz"`. Default remains `hk1978` pending author decision.
- `HARMONIC_TOLERANCE_BASE` (`0.1`) - `convention` - Baseline tolerance convention for robust harmonic matching.
- `HARMONIC_TOLERANCE_ADAPTIVE_FACTOR` (`0.1`) - `convention` - Adaptive tolerance scaling convention for robust matching.
- `HARMONIC_MAX_CHECK` (`100`) - `convention` - Practical harmonic-order cap convention.
- `HARMONIC_MATCH_TOLERANCE_CENTS` (`35.0`) - `convention` - Standard cents-domain matching tolerance convention.
- `HARMONIC_TOLERANCE_SPACING_CAP_FRACTION` (`0.30`) - `derived` - β cap so the cents window cannot exceed 30 % of the inter-harmonic spacing (policy v2).
- `HARMONIC_TOLERANCE_POLICY_VERSION` (`2`) - `internal_default` - Version stamp for the spacing-capped tolerance policy.
- `HARMONIC_BODY_STOP_MARGIN_DB` (`3.0`) - `internal_default` - Envelope-to-floor margin that ends the harmonic body (real tails sit 6–10 dB up; harvest sits at 0–3 dB).
- `HARMONIC_BODY_STOP_CONSECUTIVE` (`5`) - `internal_default` - Consecutive at-floor orders required to trigger the body stop.
- `HARMONIC_BODY_STOP_PLATEAU_SLOPE_DB_PER_ORDER` (`1.0`) - `internal_default` - Max |envelope slope| (dB/order) still treated as a plateau; decaying tails do not fire the stop.
- `HARMONIC_BODY_STOP_ENABLED` (`True`) - `internal_default` - Default-on harmonic-body noise-floor stop (validation cut only).
- `F0_REFIT_LOW_ORDER_MAX` (`8`) - `internal_default` - First-pass orders for the iterative f0 refit.
- `F0_REFIT_SNR_MIN_DB` (`20.0`) - `internal_default` - Minimum SNR to keep a first-pass peak.
- `F0_REFIT_PROMINENCE_MIN_DB` (`12.0`) - `internal_default` - Minimum prominence to keep a first-pass peak.
- `F0_REFIT_DISCREPANCY_CENTS` (`15.0`) - `internal_default` - Apply the refit when |refit − joint| exceeds this.
- `DENSITY_NOISE_GATE_ENABLED` (`True`) - `internal_default` - Core peak-power integrals subtract the floor; `canonical_density` still follows the stop-trimmed harmonic list.
- `DENSITY_NOISE_GATE_POLICY` (`subtract_floor_clip_0`) - `internal_default` - Subtract the smoothed floor and clip at 0.
- `DENSITY_CI_DEFAULT_ON` (`True`) - `internal_default` - Per-note bootstrap CI is exported by default.
- `DENSITY_CI_N_BOOT` (`1200`) - `internal_default` - Bootstrap resample count.
- `DENSITY_CI_SEED` (`0`) - `internal_default` - Fixed bootstrap seed.
- `UNCERTAINTY_REL_FLAG_PCT` (`25.0`) - `internal_default` - Relative-uncertainty threshold for the `Uncertainty_Summary` flag.
- `CI_BASIS_INDEPENDENT_FRAME_MIN` (`10`) - `internal_default` - Independent-frame floor below which a CI is flagged as under-powered.
- `INCLUDE_LF_DIAGNOSTIC_IN_AMPLITUDE_PIE` (`False`) - `internal_default` - When false, F-020 diagnostic LF rows are excluded from the validated-partial amplitude pie.
- `EXPORT_COMPLETE_SPECTRUM_PITCH_NAMES` (`False`) - `internal_default` - Omit per-bin `Note` names on Complete Spectrum unless the GUI restores them.
- `LOW_FREQUENCY_DIAGNOSTIC_UPPER_HZ` (`200.0`) - `internal_default` - Export ceiling for LF diagnostic rows above F-020 (`min(f0, 200)`).
- `DENSITY_WEIGHT_FUNCTION_DEFAULT` (`log`) - `convention` - Default φ for D_k / EWSD. Log-amplitude is a first-order loudness proxy (Fechner, 1860; Stevens, 1955; Zwicker & Fastl, 1990). Other φ remain available for audit; they change the Stage 2/3 `analysis_parameter_profile_id`.
- `REEXPORT_REL_DELTA_FLAG_PCT` (`4.0`) - `internal_default` - Stage 3 re-export flag: a note is listed when `|Δ| / |baseline|` of `EWSD_score_acoustic_balanced` exceeds this percent.
- `CONSTRUCT_N_ABS_TOL` (`1`) - `convention` - Synthetic-corpus recovery: accepted harmonic count N within ±1 of the planted count.
- `CONSTRUCT_B_REL_TOL` (`0.20`) - `convention` - Synthetic-corpus recovery of stiff-string B. 0.55 was a temporary accommodation of a since-removed low-order quantisation bias (n=1 WLS leverage). Restored to 20 % after excluding n=1 from the (a, c) step.
- `CONSTRUCT_EPD_REL_TOL` (`0.10`) - `convention` - Synthetic-corpus recovery: EPD (F-047 / participation ratio) within ±10 % of the planted validated set.
- `DENSITY_WINDOW_PERTURBATION_MS` (`10.0`) - `internal_default` - ±window shift used for density fragility.
- `DENSITY_FRAGILE_CI_PCT` (`10.0`) - `internal_default` - CI relative-width threshold for `density_fragile`.
- `DENSITY_FRAGILE_PERTURBATION_PCT` (`10.0`) - `internal_default` - Window-perturbation spread threshold for `density_fragile`.
- `LOW_F0_BIN_TO_F0_MAX_RATIO` (`0.125`) - `derived` - Escalate n_fft when bin spacing exceeds f0/8.
- `CFAR_PFA` (`1e-2`) - `internal_default` - Same cell-averaging CFAR false-alarm probability for harmonic acceptance (F-043) and confirmed-inharmonic tests.
- `HARMONIC_MIN_CFAR_MARGIN_DB` (`3.0`) - `internal_default` - Minimum CFAR margin (dB) for `include_for_density`. Rows with `0 ≤ cfar_margin_db < 3` are `cfar_marginal`.
- `HARMONIC_CONTINUITY_RULE_ENABLED` (`False`) - `internal_default` - Optional continuity cut after a rejected-slot streak. Off by default.
- `HARMONIC_CONTINUITY_REJECT_STREAK` (`3`) - `internal_default` - Consecutive rejected slots before the continuity rule freezes higher accepts.
- `HARMONIC_CONTINUITY_PERSISTENCE_OVERRIDE` (`0.9`) - `internal_default` - Persistence that may override a continuity freeze.
- `INHARMONIC_MIN_PROMINENCE_DB` (`6.0`) - `internal_default` - Minimum saddle prominence for a residual candidate to confirm as an inharmonic partial. Chosen above typical Blackman–Harris main-lobe curvature (~0–2 dB) and below the 12 dB first-pass harmonic prominence, so isolated residual peaks can confirm without admitting floor ripple.
- `PARTIAL_PERSISTENCE_MIN_FRACTION` (`0.7`) - `internal_default` - Minimum fraction of sustain frames that must contain a peak within `tol_hz` for `include_for_density` / confirmed-I.
- `PARTIAL_PERSISTENCE_STRONG_FRACTION` (`0.9`) - `internal_default` - Persistence that may override a weak CFAR margin (`validated_weak`) or an isolated `rejected_by_tolerance` slot inside a continuous accepted run.
- `TOLERANCE_CONTINUITY_OVERRIDE_FACTOR` (`1.25`) - `internal_default` - Isolated tolerance rejects may re-enter when `|dev| < 1.25 × cap` and both neighbours are included.
- `CI_WIDTH_PARTIAL_CORRELATION_N` (`30`) - `internal_default` - When the CI resampling unit is `partials` and N exceeds this, a wide interval is noted as `high_partial_correlation`. The estimator is unchanged.
- `FRAME_PEAK_MIN_ABOVE_MEDIAN_DB` (`6.0`) - `internal_default` - Per-frame peak must exceed that frame's median magnitude by this many dB before it counts as present. Keeps floor ripple from persisting.
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
- `INHARMONICITY_FIT_CENTS_WINDOW` (`80.0`) - `convention` - Common local fit window convention in cents domain. Default unchanged pending the B5 window sweep (open item).
- `INHARMONICITY_B_ENABLE_THRESHOLD` (`1e-05`) - `internal_default` - Numerical enable threshold chosen for this codebase. Stretch is enabled on `|B|`, not on a non-negativity clamp.
- `f0_refit_band_ratio` (`2.0`) - `internal_default` - Joint `(f0, B)` sanity band is one octave each way (`[f0/2, 2 f0]`), not a quarter-tone. Code and comment now agree.
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

## Auditory Component Density (ACD v1.0)

- `ERB_SLOPE` (`0.108`) - `primary_source` - Glasberg & Moore (1990) ERB(f) = 0.108 f + 24.7.
- `ERB_INTERCEPT_HZ` (`24.7`) - `primary_source` - Glasberg & Moore (1990).
- `ERB_RATE_SCALE` (`21.4`) - `primary_source` - Moore & Glasberg (1983) ERB-rate E(f) = 21.4 log10(1 + 0.00437 f).
- `ERB_RATE_COEFF` (`0.00437`) - `primary_source` - Moore & Glasberg (1983).
- `ENERGY_EPS` (`1e-30`) - `internal_default` - Numerical floor for empty/degenerate energy in Hill shares.
- `ERB_FRACTION_DEFAULT` (`1.0`) - `internal_default` - Merge bandwidth in ERB units; exposed as `erb_fraction`, not hard-coded at call sites. Sensitivity is measured on a 40-partial 1/n series (not 8-ERB spacing): [`docs/validation/ACD_ERB_FRACTION_SENSITIVITY.md`](validation/ACD_ERB_FRACTION_SENSITIVITY.md). The earlier “[0.5, 1.5] usable range” claim is discarded.
- `MERGE_STRATEGY_DEFAULT` (`fixed_erb_grid`) - `internal_default` - Default ERB merge after the Stage 1 FFT-tier comparison. `fixed_erb_grid` reduced wander from 3.80 % to 2.74 %; neither strategy fell below ~2 %. Decision: [`docs/validation/ACD_MERGE_STRATEGY.md`](validation/ACD_MERGE_STRATEGY.md).

## Acoustic-core body split (F-067)

Not exported by `constants.py`; default argument of
`acoustic_density_core.compute_acoustic_density_descriptors`.

- `low_mid_upper_hz` (`2000.0`) - `internal_default` - Body-salience split for F-067 `low_mid_energy_ratio`: share of body-peak salience at or below this frequency. Cross-reference: F-067 in `docs/METRIC_FORMULA_INDEX.md`.

## Spectral mass (F-061)

Constants live in `tools/spectral_mass.py` (derived-column module; not `constants.py`).

- `MASS_COUNT_BLEND` (`0.5`) - `convention` - Geometric-mean blend of presence-count (D0) and share-weighted count (D1). See the candidate-selection record below.
- `MASS_LEVEL_EXPONENT` (`0.15`) - `convention` - Bounded level elasticity. See the candidate-selection record below.

Candidates tested on the 47-note clarinet corpus (inversion = level overturns
a >10% richness advantage):
  A: D1 * lambda^0.30  (Stevens sone-law exponent)      — 14.2% inversions
  B: D1 * lambda^0.15                                    — 6.3% inversions
  C: D0 * lambda^0.15  (all components count fully)      — 0.1% inversions
  D: sqrt(D0*D1) * lambda^0.15                           — 1.3% inversions (SELECTED)
C won the inversion criterion outright; D was selected over C because the
geometric-mean count halves D0's exposure to sub-audibility components and to
erb_fraction sensitivity, at the cost of 1.2 points of inversion rate.
Key empirical finding motivating the D0 ingredient: F#4 has D0 = 24.9 merged
components but D1 = 1.15 — dominance is not sparsity.
