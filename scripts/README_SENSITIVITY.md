## Sensitivity Analysis

This script explores how the harmonic/inharmonic/subbass energy metrics vary with
analysis parameters. It is intended for robustness checks of the "fatness" model.

**Package version:** 3.7.0 (`soundspectranalyse`) — April 2026  

### Run

```
python scripts/sensitivity_analysis.py --signal-type harmonic --output-dir sensitivity_results
```

Optional: analyze a real file instead of a synthetic signal:

```
python scripts/sensitivity_analysis.py --audio path\to\file.wav --output-dir sensitivity_results
```

Skip plots if needed:

```
python scripts/sensitivity_analysis.py --signal-type harmonic --output-dir sensitivity_results --no-plots
```

### Outputs
- `sensitivity_results.csv`: per-run metrics with parameter values
- `sensitivity_params.json`: parameter grid used for the sweep
- `plots/`: boxplots of each metric vs parameter