# Per-note fatness, density, and EWSD — practical guide

Acoustic constructs only. No perceptual claims.

## Quick answer: one number for “fatness”

| Question | Column | Workbook / sheet |
|----------|--------|------------------|
| How many effective partials carry energy on this note? | **`note_effective_component_density`** | `compiled_density_metrics.xlsx` → `Density_Metrics`; or `compiled_density_metrics_research.xlsx` → `Spectral_Density_Metrics` |
| Harmonic-only fatness | `harmonic_effective_partial_count` | same sheets |
| Weighted spectral content (not fatness) | `note_density_final` | same sheets |
| Cross-instrument comparative density (not fatness) | `EWSD_score_acoustic_balanced` | research workbook only |

**Formula (F-047):** \(N_{\mathrm{eff}}^{\mathrm{HIS}} = (\sum_i A_i^2)^2 / \sum_i A_i^4\) over pooled harmonic + inharmonic + sub-bass components.

Higher values → energy spread across more partials (“fatter” acoustically). Lower values → energy concentrated in fewer partials. This is **not** loudness.

## Workflow

1. Run the full pipeline on a folder of note recordings (Stage 1 → 2; Stage 3 runs automatically after compile).
2. Open `analysis_results/compiled_density_metrics.xlsx` (or the research workbook).
3. Locate the row by **`Note`** (and matching **`Dynamic`** when comparing dynamics).
4. Read **`note_effective_component_density`**.

### Python lookup

```python
import pandas as pd

path = r"path/to/analysis_results/compiled_density_metrics.xlsx"
df = pd.read_excel(path, sheet_name="Density_Metrics")

row = df[(df["Note"] == "A4") & (df["Dynamic"] == "mf")].iloc[0]
print(row["note_effective_component_density"])
```

## What not to interchange

| Column | Why it is not fatness |
|--------|------------------------|
| `note_density_final` | GUI-weighted H/I/S **density** sum; no participation-ratio pooling |
| `EWSD_score_total` / `EWSD_score_acoustic_balanced` | Weighted density × compartment anti-concentration penalties |
| `Total sum`, amplitude sums | Raw mass, not effective partial count |
| `effective_partial_density` | Legacy naming; prefer `note_effective_component_density` for the unified scalar |

See `docs/validation/EWSD_THEORY.md` for the full metric hierarchy.

## Filters for thesis statistics

- **`valid_for_primary_statistics == True`** — gate compiled/research rows used in primary analysis.
- **`ewsd_primary_analysis_eligible == True`** — gate EWSD columns only (Stage 3).
- Match **`Register`**, **`Dynamic`**, and **`analysis_parameter_profile_id`** when comparing notes or instruments.

Bootstrap CI columns exist for **`note_density_final`** and **`EWSD_score_acoustic_balanced`**, not for `note_effective_component_density`.

## Related documentation

- `docs/EXPORT_COLUMN_DICTIONARY.md` — column semantics
- `docs/METRIC_FORMULA_INDEX.md` — F-045 (harmonic fatness), F-047 (unified fatness), F-048–F-050 (EWSD)
- `docs/validation/EWSD_CONSTRUCT_VALIDITY.md` — acoustic construct checks
