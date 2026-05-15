# Batch Analysis Configuration Guide

> **v6 note:** Global batch **H+I+S** fractions in `batch_summary.xlsx` are **not** identical to **`model_harmonic_weight` / `model_inharmonic_weight`** passed to the main analyser (**H/(H+I)** and **I/(H+I)** on the musical band). See **`docs/BATCH_ANALYSIS_AUDIT.md`** and **`docs/BATCH_ANALYSIS_FIELD_MAP.md`**.

## Overview

The batch analysis system supports two modes for harmonic/inharmonic weights:

1. **Auto-Extract Mode** (default): Extracts weights from each file's actual energy distribution
2. **Fixed Mode**: Uses fixed weights for all files (configured in `batch_config.json`)

## Configuration File: `batch_config.json`

### Location
Place `batch_config.json` in the same directory as `batch_audio_analyzer.py` or specify the path when running.

### Structure

```json
{
  "batch_analysis_config": {
    "weight_mode": "auto_extract",
    "fixed_weights": {
      "harmonic_weight": 0.90,
      "inharmonic_weight": 0.10
    },
    "analysis_parameters": {
      "harmonic_tolerance": 0.02,
      "use_90_tier": true,
      "use_adaptive_tolerance": true,
      "window": "blackmanharris",
      "sample_rate": 44100
    }
  }
}
```

### Weight Modes

#### 1. Auto-Extract Mode (`"weight_mode": "auto_extract"`)

**When to use:**
- Mixed instrument collections
- Different instrument types (strings, brass, woodwinds, percussion)
- When you want weights to reflect actual spectral characteristics per file

**How it works:**
- Each file's harmonic/inharmonic weights are extracted from its actual energy distribution
- Weights reflect the true spectral characteristics of each file
- Best for comparative analysis where you want accurate per-file metrics

**Example:**
- File 1 (Trumpet): 99.5% harmonic, 0.5% inharmonic
- File 2 (Piano): 85% harmonic, 15% inharmonic
- File 3 (Drum): 60% harmonic, 40% inharmonic

Each file uses its own extracted weights.

#### 2. Fixed Mode (`"weight_mode": "fixed"`)

**When to use:**
- Homogeneous instrument collections (all same type)
- When you need consistent comparison across files
- When you want to normalize analysis parameters

**How it works:**
- All files use the same fixed weights from `fixed_weights` section
- Provides consistent comparison baseline
- Useful for statistical analysis across similar instruments

**Recommended fixed weights (heuristic defaults for homogeneous collections):**

| Instrument Type | Harmonic Weight | Inharmonic Weight | Reasoning |
|----------------|-----------------|-------------------|-----------|
| **Musical Instruments** (piano, violin, trumpet, etc.) | 0.90 | 0.10 | Stable notes have 85-95% harmonic energy |
| **Percussion** (drums, cymbals) | 0.50 | 0.50 | Balanced harmonic/inharmonic content |
| **Mixed Collection** | 0.85 | 0.15 | Intermediate for diverse instruments |

### Configuration Examples

#### Example 1: Musical Instruments (Fixed Weights)

```json
{
  "batch_analysis_config": {
    "weight_mode": "fixed",
    "fixed_weights": {
      "harmonic_weight": 0.90,
      "inharmonic_weight": 0.10
    }
  }
}
```

**Use case:** Analyzing a collection of trumpet notes, all using the same weight baseline.

#### Example 2: Auto-Extract (Per-File Weights)

```json
{
  "batch_analysis_config": {
    "weight_mode": "auto_extract"
  }
}
```

**Use case:** Mixed collection with different instrument types where you want accurate per-file metrics.

#### Example 3: Percussion (Fixed Weights)

```json
{
  "batch_analysis_config": {
    "weight_mode": "fixed",
    "fixed_weights": {
      "harmonic_weight": 0.50,
      "inharmonic_weight": 0.50
    }
  }
}
```

**Use case:** Analyzing drum samples or percussive sounds.

## Using Configuration File

### From Command Line

```bash
# Use default config (batch_config.json in current directory)
python batch_audio_analyzer.py *.wav

# Use custom config file
python batch_audio_analyzer.py *.wav --config my_config.json

# Override config with command-line arguments
python batch_audio_analyzer.py *.wav --config batch_config.json --harmonic-tolerance 0.03
```

### From GUI

1. Place `batch_config.json` in the same directory as `super_audio_analyzer_gui.py`
2. The GUI will automatically detect and use the config file
3. Settings in the GUI Parameters tab will override config file settings

### Overriding Config

Command-line arguments and GUI settings take precedence over config file:

```bash
# Force fixed weights from command line
python batch_audio_analyzer.py *.wav \
  --weight-mode fixed \
  --harmonic-weight 0.95 \
  --inharmonic-weight 0.05
```

## Heuristic weight guidance

Based on acoustic physics and psychoacoustic principles (internal documentation only):

1. **Musical Instruments (Fixed: 0.90/0.10)**
   - Stable musical notes from instruments (piano, violin, trumpet) have harmonic energy typically 85-95%
   - Fixed weights of 0.90/0.10 provide consistent comparison while allowing some variation
   - Best for homogeneous collections

2. **Auto-Extract (Recommended for Mixed Collections)**
   - Each instrument type has different harmonic/inharmonic characteristics
   - Auto-extraction ensures weights reflect actual spectral content
   - Best for accurate per-file analysis

3. **Percussion (Fixed: 0.50/0.50)**
   - Percussive sounds have more balanced harmonic/inharmonic content
   - Use 0.50/0.50 for drums, cymbals, etc.

## Troubleshooting

### Issue: Weights seem wrong for musical instruments

**Solution:** Check if you're using fixed mode with incorrect weights. For musical instruments, use:
- `weight_mode: "auto_extract"` (recommended), OR
- `weight_mode: "fixed"` with `harmonic_weight: 0.90`, `inharmonic_weight: 0.10`

### Issue: Results vary too much between files

**Solution:** Use fixed mode with appropriate weights for your instrument type to normalize comparison.

### Issue: Config file not being used

**Solution:** 
1. Ensure `batch_config.json` is in the same directory as the script
2. Check JSON syntax is valid
3. Verify `weight_mode` is set to `"fixed"` or `"auto_extract"`

## Best Practices

1. **For homogeneous collections:** Use fixed mode with instrument-appropriate weights
2. **For mixed collections:** Use auto-extract mode
3. **For research/comparison:** Use fixed mode to normalize analysis parameters
4. **For accurate per-file metrics:** Use auto-extract mode

## Technical Details

- Config file is loaded at batch analyzer initialization
- Config parameters are merged with command-line/GUI arguments (arguments take precedence)
- If config file is missing, defaults to auto-extract mode
- Fixed weights must sum to approximately 1.0 (normalized automatically if needed)

