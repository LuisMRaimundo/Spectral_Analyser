# GUI Option Reference

This document covers visible options in:

- canonical operational GUI: `pipeline_orchestrator_gui.py` (Tk),
- legacy/reference GUI: `interface.py` (PyQt; not the default launcher).

---

## A. Tk Orchestrator (`pipeline_orchestrator_gui.py`)

## A1. Density controls

| UI label | Internal parameter | Default | Allowed values | Used in | Effect | Scope |
|---|---|---:|---|---|---|---|
| Density mode | `density_summation_mode` | `his_note_adaptive` | `his_note_adaptive`, `harmonic_only`, `inharmonic_only`, `subbass_only`, `his_weighted` | Stage 1 acoustic density core | selects component-combination policy | Stage 1 metrics, Stage 2 compile input |
| Harmonic weight | `harmonic_density_weight` | `1.0` | float >= 0 | acoustic density computation | multiplier for H term in weighted summaries | Stage 1 |
| Inharmonic/noise weight | `inharmonic_density_weight` | `0.5` | float >= 0 | acoustic density computation | multiplier for I term | Stage 1 |
| Subbass/particle weight | `subbass_density_weight` | `0.25` | float >= 0 | acoustic density computation | multiplier for S term | Stage 1 |
| Salience threshold (dB) | `density_salience_threshold_db` | `-45.0` | float | salient-count and salience-weighted metrics | gates salient partial/bin population | Stage 1, comparability |
| Density ceiling (Hz) | `density_frequency_ceiling_hz` | `5000.0` | float > 0 | salient metrics | upper bound for density salience families | Stage 1, comparability |

Notes:

- Primary comparable profile is operationally `wf=log`, threshold `-45 dB`, ceiling `5000 Hz`.
- GUI defaults are not fully primary-comparable by default (`wf` default is first combo label).

## A2. STFT and filtering controls

| UI label | Internal parameter | Default | Allowed values | Used in | Effect | Scope |
|---|---|---:|---|---|---|---|
| Window type | `win` | `blackmanharris` | `hann`, `hamming`, `blackmanharris`, `bartlett`, `kaiser`, `gaussian` | STFT pipeline | modifies leakage/resolution tradeoff | Stage 1 |
| Kaiser beta | `kaiser_beta` | `6.5` | float | window constructor | shape parameter for Kaiser window | Stage 1 |
| Gaussian std | `gaussian_std` | auto | float or auto | window constructor | Gaussian width parameter | Stage 1 |
| 90-tier granular clustering | `smart` | `True` | bool | tier policy | enables tier-dependent STFT regime | Stage 1 |
| N_FFT (fixed mode) | fixed-mode `n_fft` | `4096` | int > 0 | STFT | FFT length when `smart=False` | Stage 1 |
| Hop length (fixed mode) | fixed-mode `hop_length` | `1024` | int > 0 | STFT | frame stride when `smart=False` | Stage 1 |
| Zero padding (fixed mode) | fixed-mode `zero_padding` | `2` | int >= 0 | FFT prep | zero-padding multiplier when fixed mode | Stage 1 |
| Time averaging | `avg` | `mean` | `mean`, `median`, `max` | frame aggregation | affects frame-to-scalar collapse | Stage 1 |
| Peak detection magnitude min/max (dB) | `db_min`, `db_max` | `-90`, `0` | floats | candidate filtering | magnitude gating range | Stage 1 |
| Frequency range (Hz) | `freq_min`, `freq_max` | `20`, `20000` | floats | candidate filtering | frequency-gating of candidates | Stage 1 |
| Harmonic tolerance (Hz) | `tolerance` | `5.0` | float | harmonic assignment | base absolute tolerance | Stage 1 |
| Use adaptive tolerance | `use_adaptive_tolerance` | `True` | bool | harmonic assignment | enables tolerance expansion by bin spacing | Stage 1 |

## A3. Secondary and analysis controls

| UI label | Internal parameter | Default | Allowed values | Used in | Effect | Scope |
|---|---|---:|---|---|---|---|
| Dissonance model | `diss` | `sethares` | listed model slugs and `ALL` options | dissonance path | selects dissonance scalar model | Stage 1 + export sheets |
| Amplitude weighting function | `wf` | combo default | UI labels mapped via `resolve_weight_key_from_user_label` | density sum transforms | selects $\phi(A)$ (linear/log/sqrt/etc.) | Stage 1 + Stage 2 comparability |
| Auto-compile Stage 2 | `compile` | `True` | bool | orchestrator | triggers compile after Stage 1 | workflow |
| Use t-SNE (advanced) | `use_tsne` | `False` | bool | compile stage | computes `TSNE1/TSNE2` when possible | Stage 2 exploratory |
| Use UMAP (advanced) | `use_umap` | `False` | bool | compile stage | computes `UMAP1/UMAP2` when possible | Stage 2 exploratory |
| Detect anomalies | `detect_anomalies` | `False` | bool | compile stage | isolation-forest anomaly labels | Stage 2 diagnostic |
| Anomaly contamination | `anomaly_contamination` | `auto` | `auto` or 0..1 | anomaly detector | expected anomaly fraction | Stage 2 diagnostic |
| Manual inharmonic β override | `manual_model_weight_override`, `i_weight` | off / 5% | bool + 0..100 | model weight policy | overrides α/β model coefficients in legacy model-weight path | Stage 1 legacy-weighting context |

---

## B. PyQt GUI (`interface.py`) — reference/legacy surface

This GUI is still useful for manual experiments but is not the canonical launcher.

### B1. Shared analysis controls

| UI label (PyQt) | Internal key | Default | Effect |
|---|---|---:|---|
| Min/Max frequency | `freq_min`, `freq_max` path in params | `20`, `20000` | spectral candidate range |
| Min/Max dB | `db_min`, `db_max` | `-90`, `0` | magnitude thresholding |
| Adaptive tolerance checkbox | adaptive tolerance flag | `True` | harmonic tolerance expansion |
| Harmonic tolerance | tolerance field | `5.0` | harmonic assignment width |
| N_FFT / Hop length / zero padding | STFT params | `4096`, empty hop auto, `1` | STFT regime |
| Window type | window selector | multiple | leakage/resolution profile |
| Time averaging | average mode | `mean` | frame aggregation |
| Amplitude weighting function | weight function combobox | UI-mapped labels | density transform |
| Dissonance model | model combobox | includes sethares variants | dissonance model select |

### B2. Extended exploratory controls (PyQt-specific)

| UI label | Default | Effect |
|---|---:|---|
| Use PCA | enabled | toggles PCA analysis path |
| PCA include dissonance | disabled | includes dissonance fields in PCA feature set |
| Use t-SNE | disabled | nonlinear 2D embedding |
| Use UMAP | disabled | nonlinear manifold embedding |
| Anomaly detection | disabled | anomaly labels |
| Contamination | `auto` | anomaly model prior |
| Include dissonance in visual outputs | enabled | controls dissonance visualization context |
| 3D spectrogram | enabled | visualization only |
| Interactive curves | enabled | visualization only |
| Dimension scatterplots | enabled | visualization only |
| Scale visualization (`Cents`/`Ratio`/`Both`) | selectable | display transform for specific views |

---

## C. Option interpretation and comparability guidance

- **Weight function (`wf`) is comparability-critical.**  
  Primary profile requires `log`.

- **Salience threshold and ceiling are comparability-critical.**  
  Primary profile requires `-45 dB` and `5000 Hz`.

- **Tier mode affects low-level STFT settings.**  
  In tier mode, fixed `n_fft/hop/zero_padding` entries are not directly applied per note.

- **t-SNE/UMAP/anomaly are exploratory outputs.**  
  They do not redefine base density formulas.

- **Manual model-weight override is a control-layer behavior, not a new metric formula.**

---

## D. Non-claims

- GUI labels do not imply physical validity of any specific metric.
- “Subbass” in H/I/S is a low-frequency residual diagnostic partition, not an automatic claim of audible instrument subbass.
- Phase-2 corpus weights are not per-note physical energy fractions.
