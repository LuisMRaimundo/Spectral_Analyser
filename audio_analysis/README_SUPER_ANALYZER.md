# Super Audio Analyzer - State-of-the-Art Edition

> **LEGACY / OPTIONAL PHASE 1 — NOT CANONICAL STAGE 1**  
> This README documents the **Super Audio Analyzer** CLI in `audio_analysis/`, which powers **optional** batch preprocessing and writes **`super_analysis_results.json`**. The **canonical** acoustic analysis path for publication metrics is **`proc_audio.AudioProcessor` → `spectral_analysis.xlsx` → `compile_metrics.compile_density_metrics_with_pca` → `compiled_density_metrics.xlsx`**. Read **`docs/CANONICAL_PIPELINE_AND_EXPORT_SEMANTICS.md`** and **`docs/CURRENT_DOCUMENTATION_INDEX.md`** before citing this folder as “the” pipeline.

> **Pipeline note (v6):** The **canonical** public spectral-fatness scalar after full orchestration is **`effective_partial_density`** on workbook sheet **`Density_Metrics`** — see repo **`docs/DENSITY_EXPORT_SCHEMA.md`**. Older GUI / feature Markdown that used to live beside this README was retired from the working tree; use **git history** if you need that text.

## Overview

The **Super Audio Analyzer** is a top-level, state-of-the-art unified audio analysis system that combines the main codebase features with advanced algorithms and **internal consistency checks** (no external symbolic engine).

## Key Features

### 🎯 Advanced Analysis Capabilities

1. **90-Tier Granular Clustering System**
   - Frequency-optimized FFT settings per tier
   - Adaptive tolerance based on psychoacoustic JND
   - Security margin calculation (C¹ continuous)
   - Blackman-Harris window alignment

2. **Multi-Method Fundamental Frequency Detection**
   - Autocorrelation (librosa)
   - YIN algorithm
   - Peak detection in magnitude spectrum
   - Robust median-based combination

3. **Advanced Harmonic/Inharmonic Separation**
   - Adaptive tolerance (psychoacoustic JND: 1.5% of frequency)
   - Security margin based on fundamental frequency
   - Frequency-dependent tolerance scaling
   - Logarithmic combination preserving dynamic range in the **combined** density metric; per-partial **amplitude weight** in the GUIs defaults to **Linear**

4. **Comprehensive Spectral Metrics**
   - Harmonic density and energy
   - Inharmonic density and energy
   - Combined density metric
   - Spectral entropy
   - Harmonic-to-inharmonic ratio
   - Harmonic completeness

5. **Dissonance Analysis**
   - Pairwise dissonance calculation
   - Multiple dissonance models (extensible)
   - Frequency ratio analysis

6. **Statistical Analysis Suite**
   - Descriptive statistics
   - Normality tests (D'Agostino, Shapiro-Wilk)
   - Correlation analysis (Pearson, Spearman)
   - Frequency-amplitude relationships

7. **Dimensionality Reduction**
   - Principal Component Analysis (PCA)
   - Explained variance analysis
   - Feature extraction

8. **Internal consistency checks**
   - Fundamental frequency bookkeeping vs Nyquist heuristics
   - Harmonic alignment: peak ladder vs n·f₀ in cents (energy-weighted coverage; no bin-mixture percent deviation)
   - Energy split sanity lines (same definitions as batch exports)
   - Neutral audit notes only (no third-party “validation” claims)

### 📊 Advanced Visualization

- High-resolution spectrogram with harmonic overlays
- Harmonic component stem plots
- Inharmonic component scatter plots
- Metrics comparison charts
- Frequency detection method comparison
- Component distribution pie charts (in the **Super Analyzer** comprehensive figure; distinct from canonical **`proc_audio`** per-note exports, which write **`component_amplitude_mass_pie.png`**, **`component_energy_ratio_pie.png`**, and legacy-alias **`component_energy_pie.png`** — see **`docs/CANONICAL_PIPELINE_AND_EXPORT_SEMANTICS.md`**)
- Complete spectrum plots
- Statistical summary visualizations

## Installation

### Requirements

```bash
pip install numpy pandas librosa scipy matplotlib seaborn scikit-learn PyQt5
```

**For GUI Interface:**
- PyQt5 (or PySide6 as alternative)
- matplotlib (for embedded plots)

**Note:** If PyQt5 is not available, the tool will fall back to command-line mode.

### Optional (for advanced features)

```bash
pip install umap-learn  # For UMAP dimensionality reduction
pip install PyQt5       # For GUI interface
```

## Usage

### GUI Mode (Recommended)

Launch the graphical user interface:

```bash
python super_audio_analyzer.py --gui
```

Windows: open a terminal in this folder and run `python super_audio_analyzer.py --gui` (or create a shortcut to that command).

The GUI provides:
- Easy file selection
- 90-tier system toggle
- Interactive parameter configuration
- Real-time progress monitoring
- Embedded visualizations
- Results display and export

### Command-Line Mode

#### Basic Usage

```bash
python super_audio_analyzer.py audio.wav
```

### Advanced Usage with 90-Tier System

```bash
python super_audio_analyzer.py audio.wav --use-90-tier --window blackmanharris
```

### Full Parameter Control

```bash
python super_audio_analyzer.py audio.wav \
    --output-dir ./results \
    --sample-rate 44100 \
    --use-90-tier \
    --harmonic-tolerance 0.03 \
    --harmonic-weight 0.95 \
    --inharmonic-weight 0.05 \
    --window blackmanharris \
    --no-adaptive-tolerance  # Disable adaptive tolerance if needed
```

### Command-Line Arguments

- `audio_file`: Path to audio file (required)
- `--output-dir`: Output directory (default: ./super_analysis_output)
- `--sample-rate`: Target sample rate in Hz (default: 44100)
- `--use-90-tier`: Enable 90-tier granular clustering system
- `--harmonic-tolerance`: Harmonic detection tolerance (default: 0.02 = 2%)
- `--harmonic-weight`: Weight for harmonic component (default: 0.95)
- `--inharmonic-weight`: Weight for inharmonic component (default: 0.05)
- `--window`: Window function (default: blackmanharris)
- `--no-adaptive-tolerance`: Disable adaptive tolerance

## 90-Tier Granular Clustering System

The 90-tier system provides frequency-optimized analysis:

- **Sub Bass (Tiers 1-15)**: Max resolution (16384 FFT), slow decay
- **Bass (Tiers 16-30)**: High resolution (8192-4096 FFT)
- **Low Mids (Tiers 31-45)**: Medium resolution (4096-2048 FFT)
- **Mid Range (Tiers 46-60)**: Balanced resolution (2048 FFT)
- **High Mids (Tiers 61-75)**: Lower resolution (1024 FFT)
- **Highs (Tiers 76-90)**: Minimal resolution (512 FFT)

Each tier has:
- Optimized FFT size (power-of-2 for efficiency)
- Frequency-dependent tolerance
- Adaptive zero-padding
- Blackman-Harris window alignment (Hop = N/8)

## Security Margin Calculation

The security margin is calculated using C¹ continuous logarithmic interpolation:

- **20 Hz**: 35% margin
- **60 Hz**: 25% margin (C¹ continuous)
- **120 Hz**: 15% margin (C¹ continuous)
- **300+ Hz**: 10% margin (constant)

This ensures psychoacoustically correct scaling matching Weber-Fechner law.

## Adaptive Tolerance

The adaptive tolerance system uses psychoacoustic Just Noticeable Difference (JND):

- Base tolerance: Configurable (default: 2% relative)
- Adaptive component: 1.5% of frequency (psychoacoustic JND)
- Maximum cap: 50 Hz
- Formula: `tolerance = min(max(base, freq * 0.015), 50.0)`

## Output Files

The tool generates comprehensive output:

1. **super_analysis_results.json**: Complete analysis results in JSON format
2. **super_comprehensive_analysis.png**: Multi-panel comprehensive visualization
3. **harmonic_components.csv**: Harmonic components data
4. **inharmonic_components.csv**: Inharmonic components data
5. **complete_spectrum.csv**: Complete frequency spectrum data
6. **metrics_summary.txt**: Human-readable metrics summary

## Output Structure

### JSON Results Structure

```json
{
  "metadata": {
    "audio_file": "path/to/audio.wav",
    "analysis_date": "2025-01-XX...",
    "use_90_tier": true,
    "window": "blackmanharris",
    ...
  },
  "frequency_analysis": {
    "fundamental_freq_hz": 440.0,
    "security_margin_percent": 10.0,
    "detection_methods": {...}
  },
  "harmonic_analysis": {
    "n_components": 15,
    "frequencies_hz": [...],
    "amplitudes": [...],
    "harmonic_numbers": [...]
  },
  "inharmonic_analysis": {
    "n_components": 234,
    "frequencies_hz": [...],
    "amplitudes": [...]
  },
  "spectral_metrics": {
    "harmonic_density": 0.123,
    "inharmonic_density": 0.045,
    "combined_density": 0.156,
    "spectral_entropy": 0.789,
    ...
  },
  "dissonance_analysis": {
    "pairwise_dissonance": 0.045
  },
  "statistical_analysis": {
    "harmonic_frequencies": {...},
    "harmonic_amplitudes": {...},
    "frequency_amplitude_correlation": {...}
  },
  "dimensionality_reduction": {
    "pca": {
      "explained_variance_ratio": [...],
      "components": [...]
    }
  },
  "internal_consistency_checks": {
    "internal_consistency_enabled": true,
    "execution_method": "internal_only",
    "audit_notes": [...],
    "results": {...}
  }
}
```

## Internal consistency checks

Phase **[9/9]** runs **internal consistency checks** only: short audit messages are attached under `internal_consistency_checks` in `super_analysis_results.json`. These checks **do not** call any external symbolic engine or REST “validation” API.

## Best Practices

### For Well-Tuned Instruments (Piano, Violin)
```bash
python super_audio_analyzer.py piano.wav \
    --use-90-tier \
    --harmonic-tolerance 0.02 \
    --window blackmanharris
```

### For Less Precise Instruments (Brass, Woodwinds)
```bash
python super_audio_analyzer.py oboe.wav \
    --use-90-tier \
    --harmonic-tolerance 0.03 \
    --harmonic-weight 0.92 \
    --inharmonic-weight 0.08
```

### For Percussion/Inharmonic Sounds
```bash
python super_audio_analyzer.py drum.wav \
    --harmonic-tolerance 0.05 \
    --harmonic-weight 0.80 \
    --inharmonic-weight 0.20
```

## Technical Details

### FFT Optimization

- All FFT sizes rounded to nearest power-of-2 for efficiency
- Tier-based optimization: Higher resolution for lower frequencies
- Zero-padding: Adaptive per tier (1x-2x)

### Window Functions

- **Blackman-Harris**: Recommended for 90-tier system (best side-lobe suppression)
- **Hann**: Good general-purpose window
- **Hamming**: Faster computation, slightly more leakage
- **Kaiser**: Adjustable beta parameter

### Energy Conservation

- Verified with factor 2.0 normalization for librosa.stft
- Energy conservation tolerance: 10% acceptable deviation
- Warning threshold: 5% deviation

## Comparison with Other Tools

| Feature | Super Analyzer | Standard Tools |
|---------|---------------|----------------|
| 90-Tier System | ✅ | ❌ |
| Adaptive Tolerance | ✅ | ❌ |
| Security Margin | ✅ | ❌ |
| Multi-Method F0 Detection | ✅ | ⚠️ Limited |
| Internal consistency checks | ✅ | ❌ |
| Dimensionality Reduction | ✅ | ⚠️ Limited |
| Comprehensive Metrics | ✅ | ⚠️ Limited |

## Performance

- **Processing Time**: ~5-30 seconds per file (depending on length and 90-tier usage)
- **Memory Usage**: ~100-500 MB per file
- **Accuracy**: State-of-the-art signal-processing stack (internal checks only; see `docs/` for export contract)

## Troubleshooting

### "90-tier system not working"
- Ensure audio file is valid
- Check that fundamental frequency is detected
- Verify FFT sizes are power-of-2

### "Memory errors with large files"
- Disable 90-tier system: `--no-use-90-tier` (implicit)
- Reduce sample rate: `--sample-rate 22050`
- Process shorter segments

## Citation

If you use this tool in your research, please cite:

```
Super Audio Analyzer - State-of-the-Art Edition
Version 2.0.0
Combines 90-tier granular clustering, adaptive tolerance,
multi-method frequency detection, and internal consistency checks
```

## License

Scientific Research Use

## Author

AI Assistant (Senior Audio Analysis Engineer)

## Version History

- **2.0.0** (2025-01-XX): State-of-the-Art Edition
  - 90-tier granular clustering system
  - Adaptive tolerance with security margin
  - Multi-method frequency detection
  - Comprehensive statistical analysis
  - Internal consistency checks (no external symbolic engine)
  - Advanced visualization suite

