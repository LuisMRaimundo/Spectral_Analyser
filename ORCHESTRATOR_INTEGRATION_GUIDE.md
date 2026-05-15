# Pipeline orchestrator - Integration Guide
## Optional batch preprocessing + canonical `proc_audio` analysis

**Package version:** 3.7.0 (`soundspectranalyse`)  
**Document revision:** 1.3  
**Date:** May 2026

---

## Overview

The **integrated pipeline orchestrator** (`pipeline_orchestrator_integrated.py`) runs the **canonical** per-note pipeline (**`proc_audio.AudioProcessor` → `spectral_analysis.xlsx` → `compile_metrics.compile_density_metrics_with_pca` → `compiled_density_metrics.xlsx`**) and may **optionally** run **Phase 1** batch preprocessing (`batch_audio_analyzer` / **`super_audio_analyzer.py`**) to produce **`batch_summary.xlsx`**.

When batch output is available, the orchestrator **loads empirical global energy shares (H+I+S)** and derives **`harmonic_weight` / `inharmonic_weight` as model coefficients** (**α = H/(H+I)**, **β = I/(H+I)** on the musical band — **not** raw 0–100 percentage columns when sub-bass is non-zero). Those coefficients influence **legacy combined-metric** paths inside `proc_audio`; they do **not** redefine **`effective_partial_density`**.

**Compiled workbook:** the same run produces **`compiled_density_metrics.xlsx`** with sheet **`Density_Metrics`** (`effective_partial_density`, energy sums/ratios, `harmonic_order_count`, `spectral_entropy`). Dissonance and PCA live on **separate** sheets — see **`docs/DENSITY_EXPORT_SCHEMA.md`**.

**Entry point in production:** invoke **`python run_orchestrator.py`** (or **`soundspectranalyse`** after editable install). That wrapper delegates to the same `RobustOrchestrator` class described here; you do **not** need the legacy Tk script for the integrated workflow.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   PIPELINE ORCHESTRATOR                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  PHASE 1 (OPTIONAL): BATCH       │
        │  ────────────────────────          │
        │  • batch_audio_analyzer.py         │
        │  • Uses super_audio_analyzer.py    │
        │  • Generates batch_summary.xlsx    │
        │  • Empirical H+I+S + JSON sidecars │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  PHASE 2: LOAD BATCH PROFILE       │
        │  (skipped if no batch_summary)     │
        │  • Read batch_summary.xlsx         │
        │  • Build note/file → H,I,S map     │
        │  • Derive H/(H+I) model weights    │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  CANONICAL STAGE 1: proc_audio      │
        │  • AudioProcessor per WAV          │
        │  • spectral_analysis.xlsx per note │
        │  • effective_partial_density, etc. │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  CANONICAL STAGE 2: compile_metrics │
        │  • compile_density_metrics_with_pca│
        │  • compiled_density_metrics.xlsx   │
        └───────────────────────────────────┘
```

---

## Workflow

### Step-by-Step Process

1. **Input**: List of audio files to analyze

2. **Phase 1 - Optional batch preprocessing**:
   - Creates `BatchAudioAnalyzer` instance when batch mode is enabled
   - Runs batch analysis using `super_audio_analyzer.py`
   - Generates `batch_summary.xlsx` with harmonic/inharmonic/subbass energy information

3. **Phase 2 - Load batch profile (if present)**:
   - Reads `batch_summary.xlsx` when available
   - Filters out summary rows (TIER, MEAN, MEDIAN)
   - Creates mapping:
     - `Note` → validated global energy profile
     - `file_name` → same

4. **Canonical Stage 1 - `proc_audio`**:
   - For each audio file:
     - Extracts note from filename
     - Looks up validated **batch global energy profile** (H+I+S) when available
     - Derives **model coefficients** passed to `AudioProcessor` as `harmonic_weight` / `inharmonic_weight`: **α = H/(H+I)**, **β = I/(H+I)** on the musical band (same rule as `gui_model_weight_policy` / `docs/DENSITY_EXPORT_SCHEMA.md`) — **not** the same as raw **`harmonic_energy_percentage`** / **`inharmonic_energy_percentage`** display columns when sub-bass is non-zero
     - Creates `AudioProcessor` instance and calls `apply_filters_and_generate_data()` with those weights (legacy combined-metric path); **`effective_partial_density`** is **not** driven by these sliders
   - Saves per-note `spectral_analysis.xlsx` and runs compilation to **`compiled_density_metrics.xlsx`**

---

## Usage

### Command-Line Usage

```bash
python pipeline_orchestrator_integrated.py \
    audio_file1.wav audio_file2.wav audio_file3.wav \
    --super-analyzer "C:\path\to\super_audio_analyzer.py" \
    --batch-output "batch_results" \
    --main-output "main_analysis_results"
```

### Python API Usage

```python
from pathlib import Path
from pipeline_orchestrator_integrated import RobustOrchestrator

# Define audio files
audio_files = [
    Path("audio1.wav"),
    Path("audio2.wav"),
    Path("audio3.wav")
]

# Create orchestrator
orchestrator = RobustOrchestrator(
    audio_files=audio_files,
    super_analyzer_path=Path("audio_analysis/super_audio_analyzer.py"),
    batch_output_dir=Path("batch_results"),
    main_analysis_output_dir=Path("main_analysis_results"),
    excel_summary_path=None  # Will generate new, or provide path to existing
)

# Run complete pipeline
results = orchestrator.run_complete_pipeline()

# Check results
print(f"Status: {results['status']}")
print(f"Phases: {results['phases']}")
```

### Using Existing Excel Summary

If you already have a `batch_summary.xlsx` file, you can skip preprocessing:

```python
orchestrator = RobustOrchestrator(
    audio_files=audio_files,
    super_analyzer_path=Path("super_audio_analyzer.py"),
    batch_output_dir=Path("batch_results"),
    main_analysis_output_dir=Path("main_analysis_results"),
    excel_summary_path=Path("existing_batch_summary.xlsx")  # Use existing
)
```

---

## File Matching Logic

The orchestrator matches audio files to Excel data using:

1. **Filename Match**: Direct match of `file_name` column
2. **Note Extraction**: Extracts note from filename (e.g., "A4", "C#3")
3. **Note Match**: Matches extracted note to `Note` column in Excel

**Example Matching**:
- File: `"STEINWAY GRAND SOFT_A4.wav"` → Note: `"A4"` → Matches Excel row with `Note="A4"`
- File: `"CelC2_10.72sec.wav"` → Note: `"C2"` → Matches Excel row with `Note="C2"`

---

## Output Structure

### Batch Results (Phase 1)
```
batch_results/
├── batch_summary.xlsx          # Excel with harmonic/inharmonic %
├── batch_results.json          # Detailed JSON results
├── batch_statistics.txt        # Summary statistics
└── [note_folders]/             # Individual note results
    ├── super_analysis_results.json
    ├── complete_spectrum.csv
    └── ...
```

### Main Analysis Results (Phase 3)
```
main_analysis_results/
├── orchestrator_results.json   # Pipeline execution log
└── [note_folders]/             # Individual note results
    ├── spectral_analysis.json
    ├── density_metrics.xlsx
    └── ...
```

---

## Key Features

### 1. Robust Error Handling
- Continues processing even if individual files fail
- Comprehensive logging at each phase
- Graceful fallback mechanisms

### 2. Automatic File Matching
- Intelligent note extraction from filenames
- Multiple matching strategies (filename, note)
- Warning if match not found (skips file)

### 3. Percentage Application
- Converts percentages (0-100%) to weights (0.0-1.0)
- Applies weights to `AudioProcessor.apply_filters_and_generate_data()`
- Ensures energy conservation

### 4. Progress Tracking
- Detailed logging at each step
- Phase-by-phase status reporting
- Success/failure counts

---

## Integration with Main Code

### How Percentages Are Applied

The percentages from `batch_summary.xlsx` are applied as **weights** in the main spectral analysis:

```python
# From Excel: harmonic_energy_percentage = 75.42%
# Converted to weight: harmonic_weight = 0.7542

processor.apply_filters_and_generate_data(
    harmonic_weight=0.7542,      # From Excel
    inharmonic_weight=0.2458,    # From Excel (100% - 75.42%)
    # ... other parameters
)
```

These weights are used in:
- Harmonic/inharmonic component separation
- Density metric calculations
- Combined metric computation

---

## Example: Complete Workflow

### Input Files
```
audio/
├── piano_A4.wav
├── piano_B4.wav
├── piano_C5.wav
└── piano_D5.wav
```

### Phase 1 Output (batch_summary.xlsx)
```
| file_name      | Note | harmonic_energy_percentage | inharmonic_energy_percentage |
|----------------|------|---------------------------|------------------------------|
| piano_A4.wav   | A4   | 75.42                     | 0.95                         |
| piano_B4.wav   | B4   | 78.03                     | 0.34                         |
| piano_C5.wav   | C5   | 76.19                     | 0.93                         |
| piano_D5.wav   | D5   | 79.39                     | 0.52                         |
```

### Phase 3 Processing
For each file:
1. Extract note: `piano_A4.wav` → `A4`
2. Lookup: `A4` → `harmonic: 75.42%, inharmonic: 0.95%`
3. Apply: `harmonic_weight=0.7542, inharmonic_weight=0.0095`
4. Run: `AudioProcessor.apply_filters_and_generate_data(...)`

---

## Error Handling

### Common Issues and Solutions

1. **Excel Summary Not Found**
   - **Cause**: Preprocessing phase failed
   - **Solution**: Check batch_analyzer.log for errors
   - **Fallback**: Provide existing Excel file path

2. **No Match Found for File**
   - **Cause**: Note extraction failed or note not in Excel
   - **Solution**: Check filename format, verify Excel contains note
   - **Behavior**: File is skipped with warning

3. **Percentage Application Failed**
   - **Cause**: Invalid percentage values or NaN
   - **Solution**: Check Excel data quality
   - **Behavior**: Uses default weights (95%/5%)

---

## Logging

The orchestrator creates comprehensive logs:

- **File**: `orchestrator.log`
- **Console**: Real-time progress updates
- **Levels**: INFO (normal), WARNING (issues), ERROR (failures)

### Log Example
```
2026-04-04 10:00:00 - INFO - Orchestrator initialized with 88 audio files
2026-04-04 10:00:01 - INFO - PHASE 1: PREPROCESSING - Running Super Audio Analyzer
2026-04-04 10:03:15 - INFO - Batch analysis complete: 88/88 successful
2026-04-04 10:03:16 - INFO - PHASE 2: Loading Harmonic/Inharmonic Percentages from Excel
2026-04-04 10:03:17 - INFO - Created percentage mapping for 88 entries
2026-04-04 10:03:18 - INFO - PHASE 3: Main Spectral Analysis with Applied Percentages
2026-04-04 10:03:19 - INFO - Processing: piano_A4.wav
2026-04-04 10:03:19 - INFO -   Applying percentages: Harmonic: 75.42%, Inharmonic: 0.95%
2026-04-04 10:03:25 - INFO -   [OK] Completed: piano_A4.wav
```

---

## Benefits

### 1. Consistency
- Same harmonic/inharmonic distribution in both analyses
- Eliminates discrepancies between preprocessing and main analysis

### 2. Automation
- Single command runs entire pipeline
- No manual intervention required

### 3. Traceability
- Complete audit trail in logs
- Results include source percentages

### 4. Flexibility
- Can use existing Excel file (skip preprocessing)
- Can process subset of files
- Configurable output directories

---

## Technical Details

### Dependencies
- `pandas`: Excel reading/writing
- `numpy`: Numerical operations
- `pathlib`: File path handling
- `batch_audio_analyzer`: Batch processing
- `proc_audio`: Main spectral analysis

### Performance
- **Preprocessing**: ~3-5 minutes for 88 files (parallel processing)
- **Percentage Loading**: <1 second
- **Main Analysis**: ~2-4 minutes per file (sequential)

### Memory Usage
- Moderate: Processes files sequentially
- Batch processing uses parallel workers (configurable)

---

## Future Enhancements

1. **Parallel Main Analysis**: Process multiple files simultaneously
2. **Percentage Validation**: Verify percentages sum to 100%
3. **Visualization**: Generate comparison charts
4. **Configuration File**: YAML/JSON config for parameters
5. **Resume Capability**: Resume from last successful file

---

## Questions & Answers

**Q: What if a file doesn't have a matching note in Excel?**  
A: The file is skipped with a warning. Check filename format and Excel contents.

**Q: Can I use different percentages for different files?**  
A: Yes! Each file gets its own percentages from the Excel file based on note matching.

**Q: What if preprocessing fails?**  
A: You can provide an existing Excel file path to skip preprocessing.

**Q: How are percentages converted to weights?**  
A: Simple division: `weight = percentage / 100.0`. Values are validated to be 0.0-1.0.

**Q: Does this modify the original audio files?**  
A: No, all processing is read-only on audio files. Only output files are created.

---

## Support

For issues or questions:
1. Check `orchestrator.log` for detailed error messages
2. Verify Excel file format matches expected structure
3. Ensure all dependencies are installed
4. Check file paths are correct and accessible

---

**Documentation revision:** 1.1  
**Last updated:** April 2026
