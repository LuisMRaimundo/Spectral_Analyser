# Batch Processing Guide

> **Cross-reference (v6 pipeline):** Phase-1 batch outputs **optionally** feed **`run_orchestrator.py`** → canonical **`proc_audio.AudioProcessor`** → per-note **`spectral_analysis.xlsx`** → **`compile_metrics.compile_density_metrics_with_pca`** → **`compiled_density_metrics.xlsx`**. The slim public density sheet is **`Density_Metrics`** (`effective_partial_density`, energy ratios, …) — see **`docs/DENSITY_EXPORT_SCHEMA.md`** and **`docs/CANONICAL_PIPELINE_AND_EXPORT_SEMANTICS.md`**.

## Overview

The Super Audio Analyzer now supports **batch processing** of up to 50 audio files simultaneously with parallel processing for efficiency.

## Features

- ✅ **Parallel Processing**: Uses multiple CPU cores for faster analysis
- ✅ **Up to 50 Files**: Process multiple files in one batch
- ✅ **Automatic Organization**: Each file gets its own output subdirectory
- ✅ **Summary Statistics**: Aggregated metrics across all files
- ✅ **Error Handling**: Continues processing even if some files fail
- ✅ **Progress Tracking**: Real-time progress updates

## Usage Methods

### Method 1: Command Line

```bash
python batch_audio_analyzer.py file1.wav file2.wav file3.wav --output-dir batch_results
```

Or with a directory:

```bash
python batch_audio_analyzer.py *.wav --output-dir batch_results
```

### Method 2: Python Script

```python
from pathlib import Path
from batch_audio_analyzer import BatchAudioAnalyzer

# Select files
audio_files = [
    Path("audio1.wav"),
    Path("audio2.wav"),
    Path("audio3.wav"),
    # ... up to 50 files
]

# Create batch analyzer
batch_analyzer = BatchAudioAnalyzer(
    audio_files=audio_files,
    output_dir=Path("batch_results"),
    max_workers=4,  # Use 4 parallel workers
    harmonic_tolerance=0.02,
    use_90_tier=True
)

# Run analysis
results = batch_analyzer.run_batch_analysis()
```

### Method 3: GUI

1. Open the Super Audio Analyzer GUI
2. Go to the **"Batch Processing"** tab
3. Click **"Select Multiple Audio Files..."**
4. Choose up to 50 audio files
5. (Optional) Set output directory
6. Click **"Run Batch Analysis"**

## Output Structure

```
batch_results/
├── batch_results.json          # Detailed results for all files
├── batch_summary.xlsx          # Summary table (Excel format with separated columns)
├── batch_statistics.txt        # Statistics report
├── 01_file1/
│   ├── super_analysis_results.json
│   ├── harmonic_components.csv
│   ├── inharmonic_components.csv
│   └── super_comprehensive_analysis.png
├── 02_file2/
│   └── ...
└── ...
```

## Output Files

### batch_results.json
Complete results for all files, including:
- Individual file results
- Summary statistics
- Error information (if any)

### batch_summary.xlsx
Excel spreadsheet with key metrics for each file (separated columns):
- File name
- Fundamental frequency
- Harmonic energy percentage
- Inharmonic energy percentage
- Harmonic/inharmonic counts
- And more...

### batch_statistics.txt
Aggregated statistics:
- Mean, std, min, max, median for each metric
- Success/failure counts
- Overall summary

## Performance

- **Parallel Processing**: Uses `ProcessPoolExecutor` for true parallelism
- **Auto Worker Detection**: Automatically uses optimal number of workers
- **Memory Efficient**: Processes files one at a time per worker
- **Progress Tracking**: Real-time updates on completion status

## Limitations

- **Maximum 50 Files**: Hard limit to prevent resource exhaustion
- **Memory**: Each worker loads one file at a time
- **Time**: Depends on file size and number of workers

## Example

See `batch_example.py` for a complete example.

## Troubleshooting

**Q: Some files failed to process**
- Check `batch_results.json` for error messages
- Verify audio files are valid and readable
- Check disk space and permissions

**Q: Processing is slow**
- Increase `max_workers` (but not more than CPU cores)
- Check if files are very large
- Consider processing in smaller batches

**Q: Out of memory errors**
- Reduce `max_workers`
- Process files in smaller batches
- Close other applications

