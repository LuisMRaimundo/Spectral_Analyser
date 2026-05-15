# Quick Start Guide — canonical orchestrator

**Supported path:** `run_orchestrator.py` (or `soundspectranalyse` after `pip install -e .`). Everything below assumes that entry point. Calling `pipeline_orchestrator_integrated.py` directly is equivalent when you list audio files explicitly.

**Output:** per-note **`spectral_analysis.xlsx`** plus aggregated **`compiled_density_metrics.xlsx`** (sheet **`Density_Metrics`** = `effective_partial_density` + energy columns — see **`docs/DENSITY_EXPORT_SCHEMA.md`**).

## Option 1: Use wrapper script (recommended) ✅

The wrapper script (`run_orchestrator.py`) automatically finds audio files:

```powershell
# Process all WAV files in current directory
python run_orchestrator.py

# Process files in a specific directory
python run_orchestrator.py --audio-dir "E:\DOUTORAMENTO_22\INSTRUMENTOS\Instrumentos_espectro_versão 3\McGill University\PERCUSSION\PIANOS\CONCERT HALL STEINWAY SOFT"

# Use existing Excel summary (skip preprocessing)
python run_orchestrator.py `
    --audio-dir "E:\DOUTORAMENTO_22\INSTRUMENTOS\..." `
    --excel-summary "audio_analysis\batch_results\batch_summary.xlsx"
```

## Option 2: Direct Orchestrator (Requires File Arguments)

You must provide audio files as arguments:

```powershell
# Process specific files
python pipeline_orchestrator_integrated.py file1.wav file2.wav file3.wav

# With full paths
python pipeline_orchestrator_integrated.py `
    "E:\DOUTORAMENTO_22\INSTRUMENTOS\...\STEINWAY GRAND SOFT_A4.wav" `
    "E:\DOUTORAMENTO_22\INSTRUMENTOS\...\STEINWAY GRAND SOFT_B4.wav"

# Use existing Excel (skip preprocessing)
python pipeline_orchestrator_integrated.py file1.wav file2.wav `
    --excel-summary "audio_analysis\batch_results\batch_summary.xlsx"
```

## Recommended: Use Wrapper Script

The wrapper script is easier because it:
- ✅ Automatically finds audio files in directories
- ✅ Doesn't require listing every file
- ✅ Has better error messages
- ✅ Handles file discovery automatically

## Example Commands

### Example 1: Process All Files in Directory
```powershell
cd "C:\path\to\SoundSpectrAnalyse-main_6"
python run_orchestrator.py --audio-dir "E:\path\to\your\audio\folder"
```

### Example 2: Use Existing Excel (Skip Preprocessing)
```powershell
python run_orchestrator.py `
    --audio-dir "E:\DOUTORAMENTO_22\INSTRUMENTOS\..." `
    --excel-summary "audio_analysis\batch_results\batch_summary.xlsx" `
    --batch-output "batch_results" `
    --main-output "main_analysis_results"
```

### Example 3: Process Specific Files
```powershell
python pipeline_orchestrator_integrated.py `
    "path\to\file1.wav" `
    "path\to\file2.wav" `
    "path\to\file3.wav"
```
