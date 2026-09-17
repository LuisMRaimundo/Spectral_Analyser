# Spectral_Analyser mathematical reference

**Purpose.** A source-faithful description of what this repository *actually computes*. It is a documentation audit, not a proof of scientific validity. Finding a test file does not mean that test was executed in this audit.

**Renderer.** The project does not configure a dedicated math renderer. This file uses StackEdit-compatible delimiters: inline `$...$` and display `$$...$$`. Existing project docs (for example [METRIC_FORMULA_INDEX.md](METRIC_FORMULA_INDEX.md)) already use the same convention. StackEdit rendering was **not** checked on stackedit.io.

Cross-reference: the compact ID table in [METRIC_FORMULA_INDEX.md](METRIC_FORMULA_INDEX.md) (F-001 … F-070) is a catalogue, not a substitute for the executed algebra below. Where that index states a textbook STFT while the code calls `librosa.stft`, this document follows the code (see [§ Ambiguities](#scientific-ambiguities-and-implementationdocumentation-disagreements)).

---

## Source provenance

| Item | Value |
|------|--------|
| Audit date | 2026-09-17 |
| Repository | `Spectral_Analyser` (`LuisMRaimundo/Spectral_Analyser`) |
| Parent / base commit | `8051982fa32d4e4a31a7d487904df341e6aabd9c` (GitHub `main` before this integration) |
| Working branch used for the audit | `fix/silence-and-inharmonicity-validation` |
| Source identity | This document is included in the same commit as the implementation files whose SHA-256 hashes are listed in [Appendix B](#appendix-b--source-file-sha-256). That commit — not a hash written here in advance — is the source of truth. |
| Destination at start | This file did **not** already exist (no prior copy to retain) |
| This file | Excluded from its own source fingerprint |

SHA-256 hashes of cited implementation files are in [Appendix B](#appendix-b--source-file-sha-256). Installed library versions used for default-dependent claims were read from the isolated environment interpreter (see [§ External-library operations](#external-library-operations)). Previous research corpus analyses were **not** regenerated for this audit.

---

## Scope, exclusions, and how to read

**In scope.** Distinct project-implemented operations with scientific or numerical meaning on the production Stage 1–3 path, plus optional / research kernels that still define exported columns.

**Out of scope (explicit).** Ordinary counters, GUI geometry, progress percentages, and file-management arithmetic, unless they change a scientific result (they generally do not). Third-party *internal* derivations are not reproduced; those calls are listed as **L-*** entries.

**Status labels.**

- **Production** — executed on the CLI/GUI three-stage path with default settings.
- **Optional** — executed only when a flag, mode, or sheet is enabled.
- **Legacy** — still present; not the current comparable-corpus default.
- **Research-only** — offline tools / Stage 3 companions that do not change Stage 1 peak lists.

Each **M-*** entry has sections A–I. Duplicate algebra is consolidated; every implementation site is listed. **L-*** entries cover delegated library calls.

Symbols: $f$ is always in hertz unless stated; $\omega$ is not used. $\ln$ is natural log (`np.log`, `np.log1p`); $\log_{10}$ and $\log_2$ are written explicitly.

---

## Implemented analysis flow (defaults)

1. Load audio (librosa/soundfile), subtract DC, optionally trim leading/trailing digital-silence *pads*. All-digital-silence takes are **not** FFT-analysed; they receive a schema-complete ineligible workbook (NaN metrics).
2. Convert a filename note token to a **nominal** $f_0$ prior (equal temperament, A4 = 440 Hz). This prior is **not** automatically an eligible measurement.
3. RMS-normalise the waveform to $-20\,\mathrm{dB}$, then compute a **centered** STFT via librosa. Production CLI/GUI: window **blackmanharris**, $N=8192$, hop $H=1024$, zero-padding factor $2$ so the FFT length passed to librosa is $16384$.
4. Form a time-aggregated magnitude spectrum; detect and interpolate peaks; assign harmonic orders with a spacing-capped tolerance and exclusive bin ownership; optionally stretch the comb with fitted $B$.
5. Fit Fletcher-style $B$ by weighted least squares. **Physical** $B$ is published only for string-family tokens inferred from `instrument` / `source_file_name` / `note`; otherwise $B$ is NaN and the same number is exported as `spectral_stretch_coefficient`.
6. Partition energy (PSD-scaled) into harmonic / inharmonic / sub-bass; apply $\varphi$ (default **log**) to form band densities; compile `note_density_final` as $\sum_k r_k D_k$.
7. Stage 3 companions: ACD (Hill numbers after ERB merge), spectral mass, EWSD, MIR descriptors, optional dissonance models.

**Current policies (verified from this tree).**

| Policy | Effective production value | Source of truth |
|--------|----------------------------|-----------------|
| Weighting | `log` | `DENSITY_WEIGHT_FUNCTION_DEFAULT` ([constants.py](../constants.py) L275); CLI `--weight-function` default; GUI Logarithmic |
| Window | **blackmanharris** | GUI combobox default; integrated orchestrator Stage 1. **Not** `constants.DEFAULT_WINDOW` (`hann`) |
| FFT policy | `fixed`, $N=8192$, $H=1024$ | `FIXED_N_FFT_DEFAULT`, `FIXED_HOP_LENGTH_DEFAULT`; CLI/GUI entries |
| Filename-note fallback | Intentional | If the acoustic $f_0$ fit is rejected, the nominal note frequency may be retained as `f0_final` with `f0_fit_accepted=False` |
| Digital silence | Ineligible, metrics NaN | `is_digital_silence`; no fabricated spectrum |
| Physical $B$ | String-family only | `apply_inharmonicity_family_scope` using `source_file_name` when instrument is empty |

---

# Formula entries

## Preprocessing and time-domain

### M-001. Digital-silence test

**A. Name and implementation status.** Digital-silence predicate. **Production.**

**B. Source location.** [audio_silence_trim.py](../audio_silence_trim.py) `is_digital_silence`, lines 15–31. Called from [proc_audio.py](../proc_audio.py) `apply_filters_and_generate_data` lines 3242–3261.

**C. Exact code excerpt.**

```python
def is_digital_silence(
    y: np.ndarray,
    *,
    abs_threshold: float = DIGITAL_SILENCE_ABS,
) -> bool:
    arr = np.asarray(y, dtype=np.float64)
    if arr.size == 0:
        return True
    if arr.ndim > 1:
        arr = np.mean(arr, axis=1)
    return not bool(np.any(np.abs(arr) > float(abs_threshold)))
```

**D. Mathematical expression.**

$$
\mathrm{silence}(y)=\begin{cases}
\mathrm{true} & \text{if } y\text{ is empty}\\
\mathrm{true} & \text{if } \nexists\, n:\ |y[n]|>\tau_{\mathrm{abs}}\\
\mathrm{false} & \text{otherwise}
\end{cases}
\qquad \tau_{\mathrm{abs}}=10^{-7}
$$

Multichannel: $y[n]\leftarrow \mathrm{mean}_{\mathrm{ch}} y[n,\mathrm{ch}]$ before the test.

**E. Symbols, units, and assumptions.** $y$: PCM samples (dimensionless float). $\tau_{\mathrm{abs}}$: `DIGITAL_SILENCE_ABS` / `abs_threshold`, same units as $y$.

**F. Plain-language explanation.** The file is treated as “nothing sounding” only when every sample is smaller than a tiny floor (or the buffer is empty).

**G. Scientific explanation.** This is an engineering gate, not a psychoacoustic silence model. It does not estimate noise floor from the recording.

**H. Conditions and downstream use.** True → skip FFT; write ineligible workbook (M-004). False → normal analysis. Empty array is silence.

**I. Verification evidence.** `tests/phase_30/test_digital_silence_corpus.py`, `tests/phase_30/test_r3_leading_silence.py`.

---

### M-002. Leading/trailing digital-silence pad trim

**A. Status.** **Production** (applied to non-all-silent files).

**B. Source.** [audio_silence_trim.py](../audio_silence_trim.py) `trim_digital_silence`, lines 34–80.

**C. Exact code excerpt.**

```python
    min_run = max(1, int(round(float(min_pad_s) * float(sr)))) if sr else 1
    active = np.flatnonzero(np.abs(arr) > float(abs_threshold))
    if active.size == 0:
        return arr, meta
    start = int(active[0])
    end = int(active[-1]) + 1
    if start < min_run:
        start = 0
    if (n - end) < min_run:
        end = n
    out = arr[start:end]
```

**D. Mathematical expression.**

$$
N_{\min}=\max\bigl(1,\mathrm{round}(T_{\min}f_s)\bigr),\quad T_{\min}=0.005\,\mathrm{s}
$$

$$
n_0=\min\{n:|y[n]|>\tau\},\quad n_1=\max\{n:|y[n]|>\tau\}+1
$$

Trim the leading run only if $n_0\ge N_{\min}$; trim the trailing run only if $n-n_1\ge N_{\min}$. All-silent arrays are returned unchanged (M-001 handles eligibility).

**E. Symbols.** $f_s$: `sr` (Hz). $T_{\min}$: `min_pad_s` (s).

**F. Plain language.** Short leading/trailing digital zeros are cut; a completely silent take is kept as zeros.

**G. Scientific.** Heuristic pad removal. Not ADSR segmentation (`audio_silence_trim` does not import the ADSR segmenter).

**H. Downstream.** Changes the number of STFT frames (observed on padded A4 fixtures). Does not invent $f_0$.

**I. Tests.** `tests/phase_30/test_r3_leading_silence.py`.

---

### M-003. DC removal

**A. Status.** **Production.**

**B. Source.** [proc_audio.py](../proc_audio.py) `load_audio_files`, lines 2197–2198.

**C. Exact code excerpt.**

```python
                dc_offset_before = float(np.mean(y))
                y = y - dc_offset_before
```

**D. Mathematical expression.**

$$
y'[n]=y[n]-\frac{1}{N}\sum_{n=0}^{N-1}y[n]
$$

**E. Symbols.** $y$: loaded waveform after channel reduction.

**F. Plain language.** The average value of the waveform is subtracted so a constant bias does not appear as a 0 Hz spike.

**G. Scientific.** Removes the sample mean. Not a high-pass filter.

**H. Downstream.** All subsequent STFT/peak work uses $y'$.

**I. Tests.** `tests/phase_12/test_proc_audio_preprocessing_contract_additional.py`.

---

### M-004. Digital-silence ineligible workbook (undefined metrics)

**A. Status.** **Production** (working-tree fix).

**B. Source.** [proc_audio.py](../proc_audio.py) `_write_digital_silence_ineligible_workbook`, lines 10596–10702 (metrics/metadata).

**C. Exact code excerpt.**

```python
                    "f0_final_hz": float("nan"),
                    "f0_used_for_density_hz": float("nan"),
                    "valid_for_primary_statistics": False,
                    "digital_silence_input": True,
                    "eligibility_exclusion_reason": "digital_silence",
                    "note_density_final": float("nan"),
            ("f0_prior_source", "filename_token_not_used_as_measurement"),
            ("filename_note_fallback_applied_as_measurement", False),
```

**D. Mathematical expression.**

$$
f_{0,\mathrm{final}}=\mathrm{NaN},\quad D=\mathrm{NaN},\quad \mathrm{valid\_for\_primary\_statistics}=\mathrm{false}
$$

$$
f_{0,\mathrm{prior}}=f_{\mathrm{note}}(G)\ \text{(nominal only; not a measurement)}
$$

Empty H/I/S tables still include columns `Frequency (Hz)`, `Amplitude_raw`, `Power_raw`.

**E. Symbols.** $f_{\mathrm{note}}$: M-012 applied to the filename token.

**F. Plain language.** Silence is recorded as “we did not measure this,” while keeping the file identity and schema.

**G. Scientific.** Missing-value policy `nan_not_zero_v1`. Filename fallback is **not** allowed to turn silence into an eligible measured $f_0$.

**H. Downstream.** Stage 2 schema guard accepts the workbook; compile emits an ineligible row; Stage 3 may log `degraded` if chart sidecars are absent.

**I. Tests.** `tests/phase_30/test_digital_silence_corpus.py`.

---

### M-005. RMS level normalisation

**A. Status.** **Production** (immediately before STFT).

**B. Source.** [proc_audio.py](../proc_audio.py) `_normalize_level`, lines 1337–1340. Target: `NORMALIZATION_TARGET_RMS_DB = -20` ([constants.py](../constants.py) L369).

**C. Exact code excerpt.**

```python
    rms = float(np.sqrt(np.mean(np.square(y))) + 1e-12)
    cur_db = 20.0 * np.log10(rms)
    gain = 10.0 ** ((target_rms_db - cur_db) / 20.0)
    return (y * gain).astype(y.dtype, copy=False)
```

**D. Mathematical expression.**

$$
\mathrm{RMS}=\sqrt{\frac{1}{N}\sum y[n]^2}+10^{-12},\quad
L=20\log_{10}(\mathrm{RMS}),\quad
G=10^{(L_{\mathrm{tgt}}-L)/20}
$$

$$
y_{\mathrm{norm}}=G\,y,\qquad L_{\mathrm{tgt}}=-20\,\mathrm{dB}
$$

**E. Symbols.** Linear amplitude domain. $L$ is amplitude dB, not power dB.

**F. Plain language.** The recording is scaled so its RMS sits at a fixed reference level. Density then describes *shape*, not concert loudness.

**G. Scientific.** Heuristic gain staging. The $+10^{-12}$ floor prevents $\log_{10}0$.

**H. Downstream.** STFT (L-001) sees $y_{\mathrm{norm}}$.

**I. Tests.** Indirect via Stage 1 contracts; no isolated formula-validation test identified.

---

## Framing, STFT wrappers, and calibration

### M-006. Analysis FFT length and bin width

**A. Status.** **Production.**

**B. Source.** [proc_audio.py](../proc_audio.py) `fft_analysis` lines 2448–2449; `_calculate_bin_spacing` lines 1320–1322.

**C. Exact code excerpt.**

```python
            n_fft_padded = win_length * zero_padding
```

```python
    n_fft_effective = n_fft * zero_padding
    bin_spacing = sr / n_fft_effective
    return bin_spacing
```

**D. Mathematical expression.**

$$
N_{\mathrm{FFT}}=N_{\mathrm{win}}\cdot Z,\qquad
\Delta f=\frac{f_s}{N_{\mathrm{FFT}}}
$$

Production defaults: $N_{\mathrm{win}}=8192$, $Z=2$, $f_s$ typically $44100\,\mathrm{Hz}$ ⇒ $\Delta f\approx 2.691\,\mathrm{Hz}$. The hop $H=1024$ is **not** in $\Delta f$.

**E. Symbols.** $N_{\mathrm{win}}$: `self.n_fft` / `win_length`. $Z$: `zero_padding`.

**F. Plain language.** Zero-padding interpolates the frequency grid; it does not create new independent frequency information.

**G. Scientific.** Standard DFT bin spacing. Window type does not change $\Delta f$.

**H. Downstream.** Peak interpolation, tolerances (M-016), ENBW in Hz (M-021).

**I. Tests.** `tests/phase_12/test_proc_audio_core_additional.py`.

---

### M-007. Coherent gain of the analysis window

**A. Status.** **Production** (stored; used on a legacy amplitude path).

**B. Source.** [proc_audio.py](../proc_audio.py) `_coherent_gain` about L540; `fft_analysis` L2545–2559.

**C. Exact code excerpt.**

```python
                        cg_val = float(np.mean(w_vec))
                self.coherent_gain_value = cg_val if cg_val > 0.0 else 1.0
```

(Preferred helper, when it succeeds, is the same mean: $G_c=\frac{1}{N}\sum w[n]$.)

**D. Mathematical expression.**

$$
G_c=\frac{1}{N}\sum_{n=0}^{N-1}w[n]
$$

**E. Symbols.** $w[n]$: window samples of length $N_{\mathrm{win}}$.

**F. Plain language.** The average height of the window; dividing by it undoes the window’s amplitude shrinkage at DC/coherent tones.

**G. Scientific.** Standard coherent-gain definition. Distinct from ENBW (M-021), which uses $\sum w^2/(\sum w)^2$.

**H. Downstream.** Legacy filtered-list amplitudes $A=10^{\mathrm{dB}/20}/G_c$ (proc_audio L3552–3559). Physical-peak path (M-008) uses $\sum w$ instead.

**I. Tests.** Window-character tests in `tests/phase_12/test_proc_audio_core_additional.py`.

---

### M-008. One-sided physical peak amplitude

**A. Status.** **Production** (preferred new-metric path).

**B. Source.** [proc_audio.py](../proc_audio.py) `physical_peak_amplitude`, lines 616–620.

**C. Exact code excerpt.**

```python
    sw = _window_sum(window_name, int(n_fft))
    if not (_np.isfinite(sw) and sw > 0.0):
        return _np.asarray(stft_magnitude, dtype=float)
    factor = 2.0 if is_one_sided else 1.0
    return factor * _np.asarray(stft_magnitude, dtype=float) / sw
```

**D. Mathematical expression.**

$$
A_{\mathrm{peak}}\approx \frac{2\,|X[k]|}{\sum_n w[n]}\quad\text{(one-sided)}
$$

**E. Symbols.** $|X[k]|$: STFT magnitude (**amplitude**, not $|X|^2$).

**F. Plain language.** Convert the FFT bin height of a tone toward a physical peak amplitude.

**G. Scientific.** Coherent-tone / one-sided scaling. Not a PSD.

**H. Downstream.** Peak lists used for energy and density when this helper is on the path.

**I. Tests.** Contract tests under `tests/phase_12/`.

---

### M-009. Amplitude dB $\leftrightarrow$ linear

**A. Status.** **Production.**

**B. Source.** Complete-list aggregation [proc_audio.py](../proc_audio.py) L2781, L2816–2823; candidate rows L6089.

**C. Exact code excerpt.**

```python
                amp_t = np.power(10.0, db_S[i] / 20.0)
```

```python
                amp_lin = float(agg_func(amp_t))
                amp_lin = max(amp_lin, EPSILON_AMPLITUDE)
                mag_db = 20.0 * np.log10(amp_lin)
```

**D. Mathematical expression.**

$$
A=10^{\mathrm{dB}/20},\qquad
\mathrm{dB}=20\log_{10}(\max(A,\varepsilon_A))
$$

Spectrogram `db_S` is produced by `librosa.amplitude_to_db(..., ref=1.0)` (L-002): amplitude dB relative to $1$, **not** max-normalised.

**E. Symbols.** $\varepsilon_A$: `EPSILON_AMPLITUDE`.

**F. Plain language.** These are amplitude decibels (factor 20), not power decibels (factor 10).

**G. Scientific.** Mixing 20 and 10 would silently square or sqrt the scale. Entropy and energy use $P=A^2$ separately.

**H. Downstream.** All peak amplitudes, $\varphi$, and $P=A^2$ sums.

**I. Tests.** Phase-8 amplitude invariance tests.

---

### M-010. Edge-frame coverage weights

**A. Status.** **Production** when `center=True` (always in the librosa call).

**B. Source.** [proc_audio.py](../proc_audio.py) `_calculate_edge_frame_weights` L2717–2729; count L2668–2669.

**C. Exact code excerpt.**

```python
        pad_length = n_fft // 2  # Padding length for center=True
        edge_frame_count = max(1, int(np.ceil(pad_length / self.hop_length)))
                real_signal_portion = real_signal_samples / n_fft
                effective_coverage = max(real_signal_portion, 0.5)
            correction = 1.0 / effective_coverage
            weights[i] = min(correction, 2.0)
```

**D. Mathematical expression.**

$$
\rho_i=\max(\text{fraction of window on real samples},\,0.5),\qquad
w_i=\min(1/\rho_i,\,2)
$$

**E. Symbols.** Frame index $i$; weights multiply **linear** amplitude per frame before temporal aggregation.

**F. Plain language.** The first/last frames overlap the zero-pad; they are up-weighted, but never more than $2\times$.

**G. Scientific.** Heuristic compensation for `center=True` padding, not a statistically unbiased estimator.

**H. Downstream.** Time-aggregated spectrum used for peaks.

**I. Tests.** `tests/phase_12/test_proc_audio_core_additional.py`.

---

### M-011. Optional Parseval / energy-conservation audit

**A. Status.** **Optional** diagnostic.

**B. Source.** [proc_audio.py](../proc_audio.py) `_verify_energy_conservation` L924–1061.

**C. Exact code excerpt.**

```python
        energy_time = np.sum(np.abs(y_time) ** 2)
        energy_freq = np.sum(np.abs(S_freq) ** 2)
```

```python
        window_power = float(np.sum(w ** 2))
        window_length = len(w)
        overlap_factor = (window_length / hop_length) if hop_length > 0 else 1.0
        _parseval_denominator = float(window_power * overlap_factor)
            energy_freq_norm = (
                dc_energy + nyquist_energy + 2.0 * other_energy
            ) / _parseval_denominator
        if energy_time > 0:
            energy_ratio = energy_freq_norm / energy_time
        else:
            energy_ratio = float('nan')
        deviation = abs(energy_ratio - 1.0)
```

The denominator is $(\sum w^2)\cdot(N_{\mathrm{win}}/H)$ when $H>0$.

**D. Mathematical expression.**

$$
E_t=\sum_n |y[n]|^2,\qquad
E_f=\frac{E_{\mathrm{DC}}+E_{\mathrm{Nyq}}+2\sum_{k\notin\{\mathrm{DC,Nyq}\}}|S_k|^2}{(\sum w^2)\,(N/H)}
$$

$$
R=E_f/E_t,\quad \text{pass if }|R-1|\le \tau
$$

Default $\tau=0.1$ (`ENERGY_CONSERVATION_TOLERANCE`).

**E. Symbols.** **Power** domain $|S|^2$.

**F. Plain language.** A check that the spectrogram still accounts for most of the waveform energy.

**G. Scientific.** Approximate one-sided Parseval with overlap factor. Not used as a density numerator.

**H. Downstream.** Warnings only.

**I. Tests.** `tests/test_stft_reference_goldens.py` (as referenced in constants).

---

## Frequency, notes, and $f_0$

### M-012. Note name $\to$ nominal frequency (A4 = 440 Hz)

**A. Status.** **Production** (filename / GUI note prior).

**B. Source.** [proc_audio.py](../proc_audio.py) `calculate_fundamental_frequency`, lines 1408–1467. [note_parser.py](../note_parser.py) extracts the token only; it does **not** compute hertz.

**C. Exact code excerpt.**

```python
        freq_A4 = 440.0
        freq_C0 = freq_A4 * 2 ** (-4.75)  # C0 when A4=440
        idx = names.index(pitch)
        h = idx + 12 * octave
        f = freq_C0 * (2 ** (h / 12.0))
```

**D. Mathematical expression.**

$$
f_{C0}=440\cdot 2^{-4.75},\qquad
h=\mathrm{index}(\mathrm{pitch})+12\cdot\mathrm{octave},\qquad
f=f_{C0}\,2^{h/12}
$$

Numeric strings that parse as $f>0$ are returned as hertz unchanged. Invalid notes return $0$.

**E. Symbols.** Twelve-TET pitch-class index: C=0 … B=11. Octave is the parsed integer (C4 ⇒ $h=48$ ⇒ $f\approx 261.63\,\mathrm{Hz}$). Spot check: $f_{C0}\approx 16.3516\,\mathrm{Hz}$.

**F. Plain language.** “A4 in the filename” means 440 Hz as a *label*, not as a measured pitch.

**G. Scientific.** Equal-temperament convention. Not a tuning estimator.

**H. Downstream.** Seeds harmonic matching; may become `f0_final` if the acoustic fit is rejected (intentional fallback). **Not** used as a measured $f_0$ on digital silence (M-004).

**I. Tests.** `tests/phase_12/test_proc_audio_core_additional.py`; parser tests do **not** implement this formula.

---

### M-013. Cents deviation

**A. Status.** **Production.**

**B. Source.** [proc_audio.py](../proc_audio.py) `_nearest_cents_error` L1237–1240. Same algebra: [inharmonicity_model.py](../inharmonicity_model.py) `_cents_err` L70–71 (floor $10^{-12}$).

**C. Exact code excerpt.**

```python
    if measured_hz <= 0.0 or expected_hz <= 0.0:
        return float("nan")
    return float(1200.0 * np.log2(measured_hz / expected_hz))
```

**D. Mathematical expression.**

$$
\Delta c=1200\log_2(f_{\mathrm{meas}}/f_{\mathrm{exp}})\quad(f>0);\quad \mathrm{NaN}\ \mathrm{otherwise}
$$

**E. Units.** Cents. Base-2 logarithm.

**F. Plain language.** How many hundredths of a twelve-tone step the measured tone is from the expected frequency.

**G. Scientific.** Standard interval measure. Signed.

**H. Downstream.** Assignment costs, fit residuals, export `f0_deviation_cents`.

**I. Tests.** Ground-truth cents checks in `tests/phase_11/test_ground_truth_accuracy.py`.

---

### M-014. Robust $f_0$ from assigned harmonics

**A. Status.** **Production.**

**B. Source.** [proc_audio.py](../proc_audio.py) `_estimate_f0_global_robust` L1205–1225.

**C. Exact code excerpt.**

```python
    weights = detected_amplitudes / (np.max(detected_amplitudes) + 1e-10)
    weights = weights ** 2
    numerator = np.sum(weights * n_assignments * detected_freqs)
    denominator = np.sum(weights * n_assignments ** 2)
    if denominator > 1e-10:
        f0_robust = numerator / denominator
    else:
        f0_robust = initial_f0
```

**D. Mathematical expression.**

$$
w_n=\bigl(A_n/\max A\bigr)^2,\qquad
f_0=\frac{\sum w_n\, n\, f_n}{\sum w_n\, n^2}
$$

**E. Symbols.** $A_n$: linear peak amplitudes (**weights are power-like**). $n$: assigned order.

**F. Plain language.** A weighted least-squares $f_0$ that trusts stronger partials more.

**G. Scientific.** Same normal equation as fitting $f_n\approx n f_0$ with weights $w_n$. Not the joint $(f_0,B)$ WLS of M-019.

**H. Downstream.** `f0_final` when the fit is accepted; else filename nominal (policy).

**I. Tests.** `tests/phase_12/test_low_f0_harmonic_validation.py`.

---

### M-015. Low-order $f_0$ (and $B$) refit

**A. Status.** **Production.**

**B. Source.** [harmonic_peak_validation.py](../harmonic_peak_validation.py) `refine_f0_from_low_order_peaks` L743–833. Called from `_generate_harmonic_list` L4424–4454.

**C. Exact code excerpt.**

```python
    w = np.square(a_arr / float(np.max(a_arr)))
    f0_refit = float(np.sum(w * n_arr * f_arr) / denom)
        a_hat = (swxx * swy - swx * swxy) / det
        c_hat = (sw * swxy - swx * swy) / det
                b_refit = float(c_hat / a_hat)
        disc = float(1200.0 * np.log2(f0_refit / joint))
        out["f0_refit_applied"] = bool(abs(disc) > float(discrepancy_cents))
```

**D. Mathematical expression.**

Harmonic WLS as in M-014 on orders 1–8. Joint model $(f/n)^2=f_0^2+f_0^2 B n^2$ solved as 2-parameter WLS; $B=c/a$. Apply the joint $f_0$ when

$$
\bigl|1200\log_2(f_{0,\mathrm{refit}}/f_{0,\mathrm{joint}})\bigr|>15
$$

(default `discrepancy_cents`). Seed band: $f_{0,\mathrm{refit}}\in[0.5,2]\,f_{\mathrm{seed}}$.

**E. Symbols.** $a\sim f_0^2$, $c\sim f_0^2 B$.

**F. Plain language.** Recheck $f_0$ using only the lowest, most reliable partials; if a stiff-string joint fit disagrees by more than 15 cents, prefer the joint value.

**G. Scientific.** Implemented 2×2 closed WLS, not an iterative nonlinear optimiser. Threshold 15 cents is a heuristic.

**H. Downstream.** May replace the working $f_0$ before comb matching.

**I. Tests.** `tests/phase_12/test_low_f0_harmonic_validation.py`.

---

## Peaks, assignment, and inharmonicity

### M-016. Spacing-capped harmonic tolerance

**A. Status.** **Production.**

**B. Source.** [harmonic_peak_validation.py](../harmonic_peak_validation.py) `compute_spacing_capped_tolerance_hz` L76–127. Wrapper: [proc_audio.py](../proc_audio.py) `_spacing_capped_tol_hz` L4042–4090.

**C. Exact code excerpt.**

```python
    bin_cents = (1200.0 * bin_hz / expected_hz) if expected_hz > 0.0 else 0.0
    tol_cents = max(base_cents, bin_cents)
    cents_hz = expected_hz * tol_cents / 1200.0
    cap_hz = beta * f0
    raw = min(cents_hz, cap_hz)
    if bin_hz > 0.0 and raw < bin_hz:
        return float(bin_hz), TOLERANCE_LIMB_BIN_FLOOR
```

Default `base_cents=35`, $\beta=0.30$.

**D. Mathematical expression.**

$$
\tau_c(n)=\max\bigl(\tau_{\mathrm{base}},\,1200\,\Delta f/(n f_0)\bigr)
$$

$$
\mathrm{tol}_{hz}(n)=\max\bigl(\Delta f,\,\min(n f_0\,\tau_c(n)/1200,\,\beta f_0)\bigr)
$$

**E. Symbols.** $\tau_{\mathrm{base}}$: `HARMONIC_MATCH_TOLERANCE_CENTS`. $\beta$: `HARMONIC_TOLERANCE_SPACING_CAP_FRACTION`.

**F. Plain language.** The allowed mismatch around harmonic $n$ grows with bin width but cannot exceed 30% of $f_0$, so neighbouring harmonics do not steal each other’s peaks.

**G. Scientific.** Policy / matching heuristic, not a physical bandwidth.

**H. Downstream.** Exclusive assignment (M-017), inharmonic confirmation.

**I. Tests.** `tests/phase_12/test_low_f0_harmonic_validation.py`, `tests/phase_23/test_trombone_as2_defect_fixes.py`.

---

### M-017. Exclusive harmonic assignment (export path)

**A. Status.** **Production.** Iterative/greedy — no closed form.

**B. Source.** [harmonic_peak_validation.py](../harmonic_peak_validation.py) `apply_exclusive_harmonic_assignment` L252–340.

**C. Exact code excerpt.**

```python
    # Pass 1 — F-051 before any include/status is retained.
    for row in out:
        cap = _tol_hz(row)
        dev = _dev_hz(row)
        if np.isfinite(cap) and np.isfinite(dev) and dev > cap:
            row["include_for_density"] = False
            row["candidate_status"] = "rejected_by_tolerance"
            row["exclusion_reason"] = _rejected_by_tolerance_reason(dev, cap)
            row["above_harmonic_body_stop"] = False
```

```python
        def _conflict_key(i: int) -> Tuple[float, int]:
            row = out[i]
            cents = _abs_cents_deviation(
                row.get("extracted_frequency_hz", row.get("Frequency (Hz)")),
                row.get("expected_frequency_hz"),
            )
            return (cents, _order(row))

        ranked = sorted(idxs, key=_conflict_key)
        winner_idx = ranked[0]
        winner_n = _order(out[winner_idx])
        for idx in ranked[1:]:
            row = out[idx]
            cap = _tol_hz(row)
            dev = _dev_hz(row)
            row["include_for_density"] = False
            row["above_harmonic_body_stop"] = False
            row["peak_bin_index"] = float("nan")
            if np.isfinite(cap) and np.isfinite(dev) and dev > cap:
                row["candidate_status"] = "rejected_by_tolerance"
                row["exclusion_reason"] = _rejected_by_tolerance_reason(dev, cap)
            else:
                row["candidate_status"] = "peak_already_assigned"
                row["exclusion_reason"] = (
                    f"peak_already_assigned (bin={pbi}, winner_n={winner_n})"
                )
```

**D. Mathematical expression.** Not a single equation.

1. Reject a row if $|\Delta f|>\mathrm{tol}_{hz}(n)$ (M-016).
2. If several orders claim the same `peak_bin_index`, keep the pair with smallest $(|\Delta c|, n)$; others become `peak_already_assigned` with NaN bin.

**This is not** the Hungarian assignment used inside the $B$ fitter (M-020).

**E. Symbols.** Rows are harmonic-order candidates.

**F. Plain language.** Each FFT peak may support at most one harmonic number.

**G. Scientific.** Deterministic conflict rule. Different from global cost-minimising assignment.

**H. Downstream.** `include_for_density`, body-stop, energy sums.

**I. Tests.** `tests/phase_13/test_exclusive_assignment_and_validated_gating.py`.

---

### M-018. Cell-averaging CFAR peak gate

**A. Status.** **Production** (candidate classification).

**B. Source.** [harmonic_peak_validation.py](../harmonic_peak_validation.py) `cfar_peak_detection` L1372–1437.

**C. Exact code excerpt.**

```python
    power = mags * mags
    cut = float(power[peak_idx])
    train = np.concatenate([power[lo:gl], power[gh:hi]])
    if 0.0 < trim_upper_fraction < 0.9:
        keep = int(max(4, round(train.size * (1.0 - trim_upper_fraction))))
        train = np.sort(train)[:keep]
    noise_mean = float(np.mean(train))
    n_train = int(train.size)
    pfa = float(min(max(pfa, 1e-9), 0.9))
    alpha = float(n_train * (pfa ** (-1.0 / n_train) - 1.0))
    threshold = alpha * noise_mean
    margin_db = 10.0 * float(np.log10(max(cut, 1e-30) / threshold))
    return bool(margin_db >= 0.0), margin_db, threshold_db
```

**D. Mathematical expression.**

$$
\alpha=N\bigl(P_{\mathrm{fa}}^{-1/N}-1\bigr),\quad T=\alpha\,\bar N,\quad
\mathrm{margin}_{dB}=10\log_{10}(\mathrm{CUT}/T)
$$

Detected iff margin $\ge 0$. CUT power is $|X[k]|^2$. Defaults: $P_{\mathrm{fa}}=10^{-2}$, `guard_bins=2`, `train_bins=64`, `trim_upper_fraction=0.25`. $P_{\mathrm{fa}}$ is clipped to $[10^{-9},0.9]$. If fewer than 8 finite training cells remain, the gate returns not-detected.

**E. Symbols.** **Power** domain (factor 10 in dB).

**F. Plain language.** A peak must beat a noise estimate built from nearby bins, with a threshold set for a stated false-alarm rate.

**G. Scientific.** Standard CA-CFAR form. Assumes i.i.d. exponential noise in the training cells — a model, not a proof on musical spectra.

**H. Downstream.** `strict_validated` vs `cfar_marginal`; inharmonic confirmation.

**I. Tests.** `tests/phase_11/test_cfar_detection.py`, `tests/phase_16/test_high_n_harmonic_guards.py`.

---

### M-019. Stiff-string prediction and WLS $(f_0,B)$

**A. Status.** **Production.**

**B. Source.** [inharmonicity_model.py](../inharmonicity_model.py) `_model_freq` L63–67; `_wls_ac` / `_wls_ac_raw` L278–326; `fit_inharmonicity_coefficient` L400–593.

**C. Exact code excerpt.**

```python
def _model_freq(n: float, f0: float, b: float) -> float:
    inner = 1.0 + float(b) * float(n) * float(n)
    if not np.isfinite(inner) or inner <= 0.0:
        return float("nan")
    return float(n) * float(f0) * float(np.sqrt(inner))
```

```python
    y = freqs * freqs
    weights = 1.0 / np.maximum(y, 1e-12)
    x = np.column_stack([n2, n4])
    xw = x * weights[:, None]
    try:
        beta, *_ = np.linalg.lstsq(xw, y * weights, rcond=None)
```

```python
    return a_fit[0], c_fit[1]
```

**D. Mathematical expression.**

$$
f_n=n f_0\sqrt{1+B n^2}\qquad(1+Bn^2>0)
$$

$$
f_n^2=a n^2+c n^4,\quad w_n=1/f_n^2,\quad
\hat a,\hat c=\arg\min\sum_n w_n(f_n^2-a n^2-c n^4)^2
$$

$$
f_0=\sqrt{\hat a},\qquad B=\hat c/\hat a
$$

$c$ is estimated on $n\ge 2$ when at least two such points exist; $a$ uses all orders (n=1 excluded from the $n^4$ step). Up to 4 assignment/fit iterations. $|t_c|<2$ ⇒ $B\leftarrow 0$, status `not_significant` (heuristic; residuals are systematic peak-frequency error — **no formal coverage claimed**). $|B|<10^{-12}$ also `not_significant`.

**E. Symbols.** $B$ dimensionless. $t_c$: WLS $t$ for $c$ (`_wls_t_c` L242–263).

**F. Plain language.** Stiff strings’ partials sit slightly sharp of $n f_0$. The code fits that stretch from measured peak frequencies.

**G. Scientific.** Fletcher (1962) *model* $f_n=nf_0\sqrt{1+Bn^2}$ is a physical idealisation for a stiff string. The **estimator** is a project WLS with assignment and a heuristic $t$ screen. Docs and tests treat recovered $B$ as a stretch descriptor (practical floor $\sim 10^{-4}$), not a precision material constant. **Disagreement:** a nearby docstring says $f_0$ comes from the n≥2-only fit; **executed** `_wls_ac` takes $a$ from all orders.

**H. Downstream.** Comb centres (M-022); family scope (M-023).

**I. Tests.** `tests/formula_validation/test_stiff_string_fit_canonical.py`, `tests/phase_4/test_inharmonicity_recovers_known_B.py`, `tests/phase_11/test_ground_truth_accuracy.py` (`cello_A2` / `clarinet_A2`).

---

### M-020. Global order–peak assignment (fit path)

**A. Status.** **Production** inside `fit_inharmonicity_coefficient`. Algorithmic.

**B. Source.** [inharmonicity_model.py](../inharmonicity_model.py) `match_orders_detailed` L156–198. Solver: `scipy.optimize.linear_sum_assignment` (L-005).

**C. Exact code excerpt.**

```python
    cost = np.full((orders.size, freqs.size), LARGE_COST, dtype=float)
    n_hat = np.rint(freqs / max(float(f0_anchor), 1e-12))
    for i, n in enumerate(orders):
        pred = _model_freq(float(n), f0_anchor, b_anchor)
        if not np.isfinite(pred):
            continue
        err = np.abs(_cents_err(freqs, pred))
        ok = err <= window
        cost[i, ok] = err[ok]
    row_ind, col_ind = linear_sum_assignment(cost)
    keep = _longest_monotone_keep(n_arr, f_arr)
```

**D. Mathematical expression.** Minimise $\sum | \Delta c_{n\leftrightarrow j}|$ over a one-to-one matching, with infeasible pairs costed at `LARGE_COST`, then keep the longest strictly increasing-frequency subsequence.

**E. Symbols.** Window typically in cents.

**F. Plain language.** Pair each harmonic number with at most one peak, as cheaply as possible in cents, then drop pairings that go backwards in frequency.

**G. Scientific.** Combinatorial assignment + monotone prune. Not unique in general.

**H. Downstream.** Observation set for M-019.

**I. Tests.** `tests/phase_35/test_harmonic_assignment_ground_truth.py`.

---

### M-021. Equivalent noise bandwidth (ENBW)

**A. Status.** **Production** (energy module).

**B. Source.** [spectral_energy.py](../spectral_energy.py) `window_enbw_bins` L56–62; `window_enbw_hz` L65–73.

**C. Exact code excerpt.**

```python
    return float(w.size * np.sum(w * w) / (s * s))
```

```python
    return float(window_enbw_bins(window, n_fft) * df)
```

**D. Mathematical expression.**

$$
\mathrm{ENBW}_{\mathrm{bins}}=N\frac{\sum w^2}{(\sum w)^2},\qquad
\mathrm{ENBW}_{Hz}=\mathrm{ENBW}_{\mathrm{bins}}\cdot\Delta f
$$

Residual *exclusion* footprint is **not** ENBW: Blackman–Harris uses 8 bins (`RESIDUAL_EXCLUSION_FOOTPRINT`); Hann/Hamming 4; Blackman 6 (`residual_exclusion_footprint_bins` L86–100).

**E. Symbols.** $w$: `scipy.signal.get_window` samples (L-004).

**F. Plain language.** How wide a noise-equivalent rectangle would be for this window.

**G. Scientific.** Heinzel / Harris definition as implemented. `HANN_ENBW_BINS=1.5` in constants is documentation only; runtime ENBW is computed from samples.

**H. Downstream.** Fallback branch of `peak_psd_energy` when window/n_fft omitted.

**I. Tests.** Energy / Phase-8 normalisation tests.

---

### M-022. Stretched comb centres

**A. Status.** **Production.**

**B. Source.** [proc_audio.py](../proc_audio.py) `_expected_harmonic_hz` L4036–4040; `_comb_expected_freqs` L4023.

**C. Exact code excerpt.**

```python
        if stretch_enabled(b_hat, INHARMONICITY_B_ENABLE_THRESHOLD):
            inner = 1.0 + b_hat * order * order
            if inner > 0.0:
                return float(order * f0 * np.sqrt(inner))
        return float(order * f0)
```

`stretch_enabled`: $|B|>10^{-5}$ ([constants.py](../constants.py) `INHARMONICITY_B_ENABLE_THRESHOLD` L214; [inharmonicity_model.py](../inharmonicity_model.py) L337–339).

**D. Mathematical expression.**

$$
f_n=\begin{cases}
n f_0\sqrt{1+B n^2} & |B|>10^{-5}\ \mathrm{and}\ 1+Bn^2>0\\
n f_0 & \mathrm{otherwise}
\end{cases}
$$

**E. Symbols.** Same $B$ as M-019 (raw fit, before family NaN).

**F. Plain language.** Where the software *looks* for harmonic $n$.

**G. Scientific.** Internal matching still uses the numerical $B$ even when the *published* physical $B$ is NaN (family policy).

**H. Downstream.** Expected frequencies on harmonic sheets.

**I. Tests.** Ground-truth harmonic recovery tests.

---

### M-023. Instrument-family scope for published $B$

**A. Status.** **Production.**

**B. Source.** [inharmonicity_model.py](../inharmonicity_model.py) `apply_inharmonicity_family_scope` L342–370. Call site: [acoustic_density_core.py](../acoustic_density_core.py) ~L657; instrument token from [proc_audio.py](../proc_audio.py) L7699–7704: `self.instrument or self.source_file_name or self.note`.

**C. Exact code excerpt.**

```python
    token = str(instrument or "").strip().lower()
    in_family = bool(token) and any(name in token for name in STRING_FAMILY_TOKENS)
    if in_family:
        out["inharmonicity_model_scope"] = "string_family"
        out["spectral_stretch_coefficient"] = float("nan")
        return out
    out["spectral_stretch_coefficient"] = b_f
    out["inharmonicity_coefficient_B"] = float("nan")
    out["inharmonicity_model_scope"] = (
        "out_of_family" if token else "out_of_family_unspecified"
    )
```

**D. Mathematical expression.** Let $B_{\mathrm{fit}}$ be M-019.

$$
(B_{\mathrm{pub}},S_{\mathrm{stretch}},\mathrm{scope})=\begin{cases}
(B_{\mathrm{fit}},\mathrm{NaN},\texttt{string\_family}) & \text{token hits a string-family substring}\\
(\mathrm{NaN},B_{\mathrm{fit}},\texttt{out\_of\_family}) & \text{non-empty non-string token}\\
(\mathrm{NaN},B_{\mathrm{fit}},\texttt{out\_of\_family\_unspecified}) & \text{empty token}
\end{cases}
$$

**E. Symbols.** Token is a lower-cased substring of instrument / **source filename** / note. Tokens include `cello`, `violin`, `piano`, `arco`, … ([docs/validation/INHARMONICITY_FAMILY_SCOPE.md](validation/INHARMONICITY_FAMILY_SCOPE.md)). A bare `A2.wav` is a **non-empty non-string** token ⇒ `out_of_family`.

**F. Plain language.** Physical “string stiffness $B$” is only claimed when the name looks like a string instrument. Otherwise the same number is labelled phenomenological stretch.

**G. Scientific.** Policy mapping, not a classifier trained on audio. Working-tree `source_file_name` stamp is what makes `cello_A2.wav` eligible.

**H. Downstream.** Export columns `inharmonicity_coefficient_B`, `spectral_stretch_coefficient`.

**I. Tests.** `tests/phase_11/test_ground_truth_accuracy.py`, `tests/phase_35/test_harmonic_assignment_ground_truth.py`.

---

## Energy, $\varphi$, and compiled density

### M-024. Periodogram $\to$ PSD and broadband integral

**A. Status.** **Production.**

**B. Source.** [spectral_energy.py](../spectral_energy.py) `periodogram_to_psd` L119–132; `integrate_psd` L135–169.

**C. Exact code excerpt.**

```python
    """Heinzel: S(f) = |X|² / (f_s Σ w²)."""
    return arr / denom
```

```python
        return float(np.sum(psd) * df)
```

**D. Mathematical expression.**

$$
S(f_k)=\frac{P_k}{f_s\sum w^2},\qquad
E_{\mathrm{band}}=\sum_k S(f_k)\,\Delta f
$$

when `sr_hz`, `n_fft`, and `window` are all provided. Otherwise legacy $E=\sum P_k\Delta f$ on already-normalised densities.

**E. Symbols.** $P_k$: periodogram $|X_k|^2$ (**power**). $S$: PSD per hertz.

**F. Plain language.** Convert bin power into power-per-hertz and add up a band.

**G. Scientific.** Heinzel-style scaling as coded. One-sided conventions are applied by the caller’s bin list.

**H. Downstream.** Sub-bass energy in `_calculate_metrics`.

**I. Tests.** Energy-accounting tests under `tests/phase_12/`.

---

### M-025. Peak main-lobe energy

**A. Status.** **Production.**

**B. Source.** [spectral_energy.py](../spectral_energy.py) `peak_psd_energy` L172–201.

**C. Exact code excerpt.**

```python
    if window and int(n_fft) > 0:
        s1, _s2 = window_sums(window, int(n_fft))
        if s1 > 0.0:
            return float(p / (s1 * s1))
    return float(p * bw)
```

**D. Mathematical expression.**

$$
E_{\mathrm{peak}}=\begin{cases}
P_{\mathrm{peak}}/(\sum w)^2 & \text{window and }n_{\mathrm{fft}}\text{ given}\\
P_{\mathrm{peak}}\cdot\mathrm{ENBW}_{Hz} & \text{else}
\end{cases}
$$

**E. Symbols.** $P_{\mathrm{peak}}$: `peak_power` (typically $\sum A^2$ of a peak list — **power**).

**F. Plain language.** Turn a peak’s bin power into an energy that is more comparable across windows/FFT lengths.

**G. Scientific.** Two branches; production Stage 1 usually takes the $(\sum w)^2$ branch.

**H. Downstream.** $H$ and $I$ energies before ratios (M-026).

**I. Tests.** Phase-8 / energy tests.

---

### M-026. Three-way energy ratios

**A. Status.** **Production.**

**B. Source.** [proc_audio.py](../proc_audio.py) L8079–8209 and `_finalize_component_energy_ratios` L6546–6549.

**C. Exact code excerpt.**

```python
            h_raw = float(np.sum(np.square(harmonic_amps))) if harmonic_amps.size else 0.0
            ...
            if tot_energy > 1e-30:
                self.harmonic_energy_ratio = float(h_energy / tot_energy)
```

```python
            T = Hn + In + Sn
            if T > 1e-30:
                comp_h = Hn / T
```

**D. Mathematical expression.**

$$
E_H=\mathrm{peak\_psd\_energy}(\sum A_H^2),\quad
E_I=\mathrm{peak\_psd\_energy}(\sum A_I^2),\quad
E_S=\mathrm{integrate\_psd}(\ldots)
$$

$$
r_k=E_k/(E_H+E_I+E_S)\quad\text{if }T>10^{-30};\ \text{else }0
$$

**E. Symbols.** $A$: linear amplitudes. Ratios dimensionless.

**F. Plain language.** What fraction of the note’s accounted energy sits in harmonics, leftover tones, and the rumble band.

**G. Scientific.** Partition of a constructed energy, not a thermodynamic conservation law. $H$/$I$ vs $S$ use different converters (peak vs integral).

**H. Downstream.** `note_density_final` (M-029), EWSD $r_k$, ACD $r_k$.

**I. Tests.** `tests/phase_12/test_density_metric_contract_additional.py`.

---

### M-027. Sub-bass upper bound (F-020)

**A. Status.** **Production.**

**B. Source.** [subbass_policy.py](../subbass_policy.py) `SubBassPolicy.resolve_f020_bound` L29–45.

**C. Exact code excerpt.**

```python
        if not math.isfinite(f0) or f0 <= 0.0:
            return {
                "subbass_upper_bound_hz": float(SUBBASS_BOUND_CAP_HZ),
                ...
            }
        return {
            "subbass_upper_bound_hz": float(min(0.5 * f0, 80.0)),
```

**D. Mathematical expression.**

$$
f_{\mathrm{sub,max}}=\begin{cases}
80\,\mathrm{Hz} & f_0\notin(0,\infty)\\
\min(0.5 f_0,\,80) & \mathrm{otherwise}
\end{cases}
$$

Spot check: A1 $f_0=55\,\mathrm{Hz}$ ⇒ $27.5\,\mathrm{Hz}$.

**E. Symbols.** $f_0$ in Hz.

**F. Plain language.** Sub-bass stops at the lower of “half the note” and 80 Hz.

**G. Scientific.** Project policy citing Zwicker & Fastl (1990) for the ~80 Hz region; the $\min(0.5f_0,80)$ intersection is an implementation choice.

**H. Downstream.** Sub-bass membership masks; $D_S$.

**I. Tests.** `tests/formula_validation/test_subbass_policy_canonical.py`.

---

### M-028. Weight functions $\varphi$

**A. Status.** **Production** (canonical element-wise $\varphi$). Compile aggregate `log` is a **different** formula (M-029).

**B. Source.** [density.py](../density.py) `WeightFunction` L1404–1436; `get_weight_function` L1439–1482.

**C. Exact code excerpt.**

```python
    def linear(x):
        return x
    def squared(x):
        return np.square(x)  # x^2
    def logarithmic(x):
        return np.log1p(x)
        'log':         WeightFunction.logarithmic,   # alias
```

There is **no** `power` key in `get_weight_function`. Compile-only `wf=="power"` sums $P$ or $A^2$.

**D. Mathematical expression.** For $A\ge 0$:

$$
\varphi_{\mathrm{lin}}(A)=A,\quad
\varphi_{\mathrm{sq}}(A)=A^2,\quad
\varphi_{\mathrm{log}}(A)=\ln(1+A),\quad
\varphi_{\mathrm{exp}}(A)=e^{A}-1
$$

$$
\varphi_{\mathrm{invlog}}(A)=1/(\ln(1+A)+10^{-10})
$$

**E. Symbols.** $\ln$ = `np.log1p` (natural). $A$: linear amplitude.

**F. Plain language.** How loudly a partial “counts” in a density sum. Default **log** compresses large peaks.

**G. Scientific.** Project $\varphi$, not an auditory filter. **Disagreement:** Stage-2 *aggregate* `log` uses $\log_{10}(1+\sum A)$ (M-029), not $\sum\ln(1+A)$, unless the element-wise override runs.

**H. Downstream.** `apply_density_metric`; element-wise compile path.

**I. Tests.** `tests/phase_20/test_weight_function_phi.py`, `tests/formula_validation/test_density_formula_canonical.py`.

---

### M-029. Band density $D$ and `note_density_final`

**A. Status.** **Production.**

**B. Source.** [compile_metrics.py](../compile_metrics.py) `extract_density_component_sum` L3366–3370; `_compute_note_density_final` L1763–1820.

**C. Exact code excerpt.**

```python
    raw_total = float(series.to_numpy(dtype=float)[mask].sum())
    if wf == "log":
        d_value = float(np.log10(1.0 + max(0.0, raw_total)))
    else:
        d_value = raw_total
```

```python
        total = total + (ratio * dsum)
```

**D. Mathematical expression.** Default $\mathrm{wf}=\texttt{log}$:

$$
D_k=\log_{10}\bigl(1+\max(0,\sum_{i\in k}A_i)\bigr)
$$

`linear`: $D_k=\sum A_i$. `power`: $D_k=\sum P_i$ or $\sum A_i^2$. Then

$$
\mathrm{note\_density\_final}=\sum_{k\in\{H,I,S\}} r_k D_k
$$

with $r_k$ from M-026. Any missing $r_k$ or $D_k$ ⇒ row NaN (never coerced to 0).

**E. Symbols.** $A_i$: `Amplitude_raw` on inclusion-masked rows.

**F. Plain language.** Each band is summarised, then mixed using that note’s own energy mix.

**G. Scientific.** Canonical compile scalar. Adaptive GUI weights (M-036) are **not** substituted here (comment L1706–1707).

**H. Downstream.** Research workbook primary density; CI (M-037).

**I. Tests.** `tests/formula_validation/test_density_formula_canonical.py`, `tests/phase_11/test_density_uncertainty.py`.

---

### M-030. Participation ratio / effective count

**A. Status.** **Production.**

**B. Source.** [validated_partials.py](../validated_partials.py) `participation_ratio_from_amplitudes` L91–104; [compile_metrics.py](../compile_metrics.py) `_energy_distribution_density` L4564–4598; Stage 1 [proc_audio.py](../proc_audio.py) L8190–8194.

**C. Exact code excerpt.**

```python
    def _neff(p: np.ndarray) -> float:
        ptot = float(np.sum(p))
        return float((ptot * ptot) / max(float(np.sum(p * p)), 1e-30)) if ptot > 0 else nan
            out["note_effective_component_density"] = _neff(allc * allc)
```

**D. Mathematical expression.** For powers $P_i=A_i^2$:

$$
N_{\mathrm{eff}}=\frac{(\sum P_i)^2}{\sum P_i^2}=\frac{(\sum A_i^2)^2}{\sum A_i^4}
$$

F-045: harmonics only → `harmonic_effective_partial_count`. F-047: pooled H∪I∪S → `note_effective_component_density`.

**E. Symbols.** $P$: **power**.

**F. Plain language.** How many equal-loud partials would carry the same energy spread. One dominant peak ⇒ $N_{\mathrm{eff}}\approx 1$.

**G. Scientific.** Inverse Herfindahl / Hill $D_2$. F-047’s membership pool is **not** the same as F-056 (M-035).

**H. Downstream.** Fatness / EWSD penalties.

**I. Tests.** `tests/formula_validation/test_effective_partial_density_canonical.py`.

---

### M-031. $n_{\mathrm{FFT}}$ tier normalisation

**A. Status.** **Production** (when comparing across FFT lengths).

**B. Source.** [spectral_normalization.py](../spectral_normalization.py) `n_fft_normalization_factor` L47–72.

**C. Exact code excerpt.**

```python
    ratio = float(n_ref) / float(n)
    if qk == "peak_amplitude_sum":
        return float(ratio)
    if qk == "peak_power_sum":
        return float(ratio * ratio)
    if qk == "broadband_amplitude_l2":
        return float(math.sqrt(ratio))
    if qk == "broadband_power_l2":
        return float(ratio)
```

**D. Mathematical expression.** $r=N_{\mathrm{ref}}/N$.

$$
\alpha_{\mathrm{amp}}=r,\quad
\alpha_{\mathrm{pow}}=r^2,\quad
\alpha_{\|A\|_2}=\sqrt{r},\quad
\alpha_{\|P\|_2}=r
$$

**E. Symbols.** $N$: current `n_fft`. Invalid $N\le 0$ raises.

**F. Plain language.** A longer FFT makes coherent peaks taller; these factors undo that when summing peaks across tiers.

**G. Scientific.** Scaling heuristic documented against Harris/Heinzel; not a full STFT-invariant estimator.

**H. Downstream.** `*_tier_normalized` export columns.

**I. Tests.** `tests/formula_validation/test_n_fft_normalization_factor_canonical.py`.

---

## ACD, spectral mass, EWSD

### M-032. ERB bandwidth, ERB-rate, and peak merge

**A. Status.** **Production** (Stage 3 ACD). Duplicate ERB helpers exist in [mir_descriptors.py](../mir_descriptors.py) (intentionally not cross-imported).

**B. Source.** [tools/spectral_density_hill.py](../tools/spectral_density_hill.py) L57–66, `merge_peaks_within_erb` L81–126.

**C. Exact code excerpt.**

```python
    return ERB_SLOPE * f + ERB_INTERCEPT_HZ
    return ERB_RATE_SCALE * np.log10(1.0 + ERB_RATE_COEFF * f)
```

Default merge strategy `fixed_erb_grid`: $\mathrm{bin}=\lfloor E(f)/\varepsilon\rfloor$. Moving-centroid alternative: join while $f_{\mathrm{next}}-f_{\mathrm{centroid}}\le \varepsilon\,\mathrm{ERB}(f_{\mathrm{centroid}})$. Merged

$$
A_m=\sqrt{\sum A_i^2},\qquad
f_m=\frac{\sum f_i A_i^2}{\sum A_i^2}
$$

**D. Mathematical expression.**

$$
\mathrm{ERB}(f)=0.108f+24.7,\qquad
E(f)=21.4\log_{10}(1+0.00437 f)
$$

($f$ in Hz, ERB in Hz, $E$ in Cam/ERB-rate.)

**E. Symbols.** $\varepsilon$: `erb_fraction` (default 1).

**F. Plain language.** Peaks closer than about one ear-filter are counted as one component.

**G. Scientific.** Glasberg & Moore (1990) ERB; Moore & Glasberg (1983) rate. Merge is an energy-preserving heuristic.

**H. Downstream.** Hill numbers (M-033), ACD (M-034).

**I. Tests.** `tests/phase_32/test_acd_*.py`.

---

### M-033. Hill numbers on energy shares

**A. Status.** **Production** (ACD).

**B. Source.** [tools/spectral_density_hill.py](../tools/spectral_density_hill.py) `energy_shares` / `hill_number` ~L220–260.

**C. Exact code excerpt** (implemented cases). $p_i=A_i^2/\sum A^2$.

**D. Mathematical expression.**

$$
D_q=\bigl(\sum_i p_i^q\bigr)^{1/(1-q)}\ (q\neq 1),\quad
D_1=\exp\bigl(-\sum_i p_i\ln p_i\bigr),\quad
D_0=N,\quad
D_\infty=1/\max p_i
$$

**E. Symbols.** $p_i$: **power** shares. $\ln$ natural.

**F. Plain language.** Diversity indices: $D_0$ is a count, $D_1$ an entropy-effective count, $D_2$ the participation ratio.

**G. Scientific.** Hill (1973) numbers on a discrete power distribution. Not an auditory excitation pattern by itself.

**H. Downstream.** ACD uses $D_1$ by default; mass uses $D_0,D_1$ per compartment.

**I. Tests.** `tests/phase_32/`.

---

### M-034. Auditory Component Density (ACD)

**A. Status.** **Production** Stage 3 companion.

**B. Source.** [tools/spectral_density_hill.py](../tools/spectral_density_hill.py) `compute_note_density` L398–503.

**C. Exact code excerpt.** $r_k=E_k/\sum_j E_j$; `ACD = sum r_k D_{q,k}`; `LAM = E_total / ACD`.

**D. Mathematical expression.**

$$
\mathrm{ACD}=\sum_{k\in\{H,I,S\}} r_k D_{1,k},\qquad
\lambda=E_{\mathrm{tot}}/\mathrm{ACD}
$$

Previous D2-weighted score retained as `ACD_score_D2_dominance`.

**E. Symbols.** $E_k$: compartment energy. $\lambda$: `ACD_magnitude_per_component`.

**F. Plain language.** ACD: “how many effective sounding components?” $\lambda$: “how large is each, on average?”

**G. Scientific.** Constructed index. FFT-tier invariance is approximate (documented gates in ACD validation docs).

**H. Downstream.** Spectral mass (M-035).

**I. Tests.** `tests/phase_32/test_acd_*.py`.

---

### M-035. Spectral mass (F-061 v2) and balanced $D_1$ (F-056)

**A. Status.** **Production** Stage 3 (`spectral_mass`); F-056 is a companion column.

**B. Source.** [tools/spectral_mass.py](../tools/spectral_mass.py) L31–32, `compartment_count` L83–87, `compute_spectral_mass` L106–154. [tools/balanced_density.py](../tools/balanced_density.py) L46–71.

**C. Exact code excerpt.**

```python
MASS_COUNT_BLEND: float = 0.5
MASS_LEVEL_EXPONENT: float = 0.15
    return float((float(d0) * float(d1)) ** MASS_COUNT_BLEND)
    return float(count * (lam_f ** MASS_LEVEL_EXPONENT)), float(count)
```

```python
    shares = power / total
    entropy = np.float64(0.0) - np.float64(
        np.sum(shares * np.log(shares), dtype=np.float64)
    )
    return float(np.exp(entropy, dtype=np.float64))
```

**D. Mathematical expression.**

$$
\mathrm{count}_k=(D_{0,k}D_{1,k})^{1/2},\quad
\mathrm{count}=\sum_k r_k\,\mathrm{count}_k,\quad
\lambda=E/\mathrm{count}
$$

$$
\mathrm{spectral\_mass}=\mathrm{count}\,\lambda^{0.15}
$$

NaN if `ACD_status≠ok` or any required input is NaN (never 0).

F-056: $D_1=\exp(-\sum p_i\ln p_i)$ on a **stricter** partial pool than F-047; empty/$\sum P=0$ → NaN; one component → $1$.

**E. Symbols.** $r_k$ energy shares. v1 pooled-D0 mass is **legacy** (`compute_spectral_mass_v1`).

**F. Plain language.** Mass: how much is sounding, after not letting quiet leftover bands count as if they were as numerous as the harmonics.

**G. Scientific.** Author-defined blend. External notes dated before v2 may quote a v1 worked example.

**H. Downstream.** Research workbook `spectral_mass`.

**I. Tests.** `tests/phase_34/test_spectral_mass.py`, `tests/formula_validation/test_balanced_component_density_canonical.py`.

---

### M-036. Strict and acoustic-balanced EWSD

**A. Status.** **Production** Stage 3.

**B. Source.** [tools/ewsd_pure.py](../tools/ewsd_pure.py) `participation_stats` L190–205; `compute_compartment_metrics` L208–253; `compute_acoustic_balanced_score` L260–274. $\alpha=0.50$ (`ACOUSTIC_BALANCE_ALPHA_DEFAULT` L19).

**C. Exact code excerpt.**

```python
    p = s / total
    neff = float(1.0 / np.sum(p ** 2)) if np.sum(p ** 2) > 0 else 0.0
    penalty = float(neff / n) if n > 0 else 0.0
    score = (
        float(ratio_weighted_metric * penalty)
        if inputs.apply_anti_concentration
        else float(ratio_weighted_metric)
    )
        total += float(comp.ratio_weighted_metric) * (pen ** a)
```

**D. Mathematical expression.** $s_i=\varphi(A_i)\,r_k$ (ratio cancels in $p_i$). $D_k=\varphi_{\mathrm{sum},k}\,r_k$. Penalty $N_{\mathrm{eff}}/N$ with $N_{\mathrm{eff}}=1/\sum p_i^2$.

$$
\mathrm{EWSD}_k=D_k\cdot(N_{\mathrm{eff},k}/N_k),\qquad
\mathrm{EWSD}=\sum_k\mathrm{EWSD}_k
$$

$$
\mathrm{EWSD}^{bal}=\sum_k D_k\,(N_{\mathrm{eff},k}/N_k)^{\alpha},\quad\alpha=1/2
$$

**E. Symbols.** $\varphi$ from the analysis weight key (default log). METRIC_FORMULA_INDEX notes a **double** $N_{\mathrm{eff}}/N$ when `original_sum_metric` already includes a participation factor (d10) — algebra frozen.

**F. Plain language.** EWSD down-weights a band that dumps all its energy into one peak. The “balanced” score uses a milder (square-root) penalty.

**G. Scientific.** Constructed anti-concentration index. Balanced companion is documented as **level-dependent / not for cross-note comparison**.

**H. Downstream.** `EWSD_score_total`, `EWSD_score_acoustic_balanced`.

**I. Tests.** `tests/phase_11/test_ewsd_*.py`.

---

### M-037. Adaptive H/I/S profile (JSD gate)

**A. Status.** **Production** in GUI adaptive density mode (does **not** replace M-029 ratios).

**B. Source.** [adaptive_density_engine.py](../adaptive_density_engine.py) L30–119.

**C. Exact code excerpt.**

```python
    m = 0.5 * (p + q)
    kl_pm = float(np.sum(p * np.log(p / m)))
    kl_qm = float(np.sum(q * np.log(q / m)))
    return max(0.0, 0.5 * (kl_pm + kl_qm))
        reliability = float(np.exp(-jsd / self._temp))
        reliability = float(max(0.10, min(1.0, reliability)))
        self._alpha = (1.0 - self._forgetting) * self._alpha + gain * obs
```

**D. Mathematical expression.** $\ln$ natural. $o$ and $\bar\alpha$ are non-negative triplets renormalised to sum 1.

$$
\mathrm{JSD}(o,\bar\alpha)=\tfrac12\mathrm{KL}(o\|m)+\tfrac12\mathrm{KL}(\bar\alpha\|m),\quad m=\tfrac12(o+\bar\alpha)
$$

$$
\mathrm{rel}=\mathrm{clip}\bigl(e^{-\mathrm{JSD}/T},0.1,1\bigr),\quad T=0.18
$$

$$
\alpha\leftarrow(1-\rho)\alpha+g\,o,\quad\rho=0.02,\quad g\in[0.25,4]\cdot\mathrm{rel}
$$

Profile $\bar\alpha=\alpha/\sum\alpha$. Uncertainty $1/(1+\sum\alpha)$.

**E. Symbols.** Dirichlet-like pseudo-counts $\alpha$.

**F. Plain language.** The GUI slowly learns a typical H/I/S mix, ignoring notes that look unlike what it has seen.

**G. Scientific.** Heuristic online learner. Not a Bayesian posterior with a documented prior on real corpora.

**H. Downstream.** Runtime profile display and Phase-2 application weights; **not** `note_density_final` $r_k$.

**I. Tests.** `tests/formula_validation/test_js_divergence_canonical.py`.

---

## MIR, roughness, temporal, export companions

### M-038. Spectral moments, tristimulus, flatness, rolloff, ERB density

**A. Status.** **Production** (MIR sheet / research export).

**B. Source.** [mir_descriptors.py](../mir_descriptors.py) `compute_mir_descriptors_from_spectrum` L319–374.

**C. Exact code excerpt.**

```python
    power = amp * amp
    p = _safe_prob(power)
    centroid = float(np.sum(freq * p))
    spread = float(np.sqrt(max(0.0, np.sum(((freq - centroid) ** 2) * p)))
                   )
        skew = float(np.sum((((freq - centroid) / spread) ** 3) * p))
        kurt = float(np.sum((((freq - centroid) / spread) ** 4) * p))
        irregularity = float(np.sum(np.abs(np.diff(amp))) / max(float(np.sum(amp)), 1e-12))
                t1 = float(np.sum(a[n == 1]) / tot)
                t2 = float(np.sum(a[(n >= 2) & (n <= 4)]) / tot)
                t3 = float(np.sum(a[n >= 5]) / tot)
    gmean = float(np.exp(np.mean(np.log(np.maximum(power, 1e-12)))))
        r85 = float(f_sorted[np.searchsorted(cumsum, 0.85 * total, side="left")])
        erb_weighted_density = float(1.0 / max(float(np.sum(q * q)), 1e-12))
```

**D. Mathematical expression.** $p_i=P_i/\sum P$, $P=A^2$ (**power** weights for moments).

$$
C=\sum f_i p_i,\quad
\sigma=\sqrt{\sum(f_i-C)^2 p_i},\quad
\gamma_1=\sum\bigl((f_i-C)/\sigma\bigr)^3 p_i,\quad
\gamma_2=\sum\bigl((f_i-C)/\sigma\bigr)^4 p_i
$$

$$
I=\mathrm{clip}\bigl(\sum|A_{i+1}-A_i|/\sum A_i,\,0,1\bigr)
$$

$$
T_1=\sum_{n=1}A/\sum A,\quad T_2=\sum_{n=2}^{4}A/\sum A,\quad T_3=\sum_{n\ge 5}A/\sum A
$$

($n=\mathrm{round}(f/f_0)$.)

$$
F=\mathrm{clip}\bigl(\exp(\overline{\ln P})/\overline{P},\,0,1\bigr)
$$

Rolloff: smallest $f$ with cumulative $P$ reaching $85\%$ or $95\%$ of $\sum P$.

$$
D_{\mathrm{ERB}}=1/\sum_b q_b^2,\quad q=\text{power mass per }\lfloor E(f)\rfloor
$$

**E. Symbols.** $E(f)$: Moore–Glasberg ERB-rate (same coefficients as M-032).

**F. Plain language.** Classic “brightness / width / oddness / high-harmonic share / noisiness / where most energy stops” numbers.

**G. Scientific.** Standard descriptors; tristimulus uses **amplitude** sums, moments use **power**. Irregularity assumes frequency-sorted $A$.

**H. Downstream.** `_on_{attack,sustain,release}` suffixes reuse the same formulae on segment peak lists.

**I. Tests.** MIR / phase-7 export tests.

---

### M-039. Parncutt / Plomp–Levelt pairwise roughness

**A. Status.** **Production** (default roughness).

**B. Source.** [mir_descriptors.py](../mir_descriptors.py) L122–223.

**C. Exact code excerpt.**

```python
        x = (fj - f[i]) / di
        total += float(a[i] * np.sum(aj * (x * np.exp(1.0 - x))))
```

$d_i=0.25\cdot\mathrm{CB}(f_{\mathrm{lo}})$; default CB = Zwicker $25+75(1+1.4(f/1000)^2)^{0.69}$, NaN (pair dropped) if $f>15500\,\mathrm{Hz}$. Alternative `erb`: $0.25(0.108f+24.7)$.

**D. Mathematical expression.**

$$
x=\frac{|f_i-f_j|}{0.25\,\mathrm{CB}(f_{\mathrm{lo}})},\qquad
g(x)=x\,e^{1-x},\qquad
R=\sum_{i<j} A_i A_j\, g(x_{ij})
$$

(as implemented: one factor $A_i$ outside and $A_j$ inside the inner sum).

**E. Symbols.** $A$: linear amplitudes.

**F. Plain language.** Nearby partials grind; the kernel peaks when their spacing is a fraction of a critical band.

**G. Scientific.** Implemented Plomp–Levelt / Parncutt-style kernel. Not a full masking model.

**H. Downstream.** `roughness_parncutt_kernel`. Pairs with $\max(f_i,f_j)>15500$ dropped.

**I. Tests.** `tools/validation/roughness_bandwidth_basis.py` (research); unit tests in phase-33 goldens.

---

### M-040. Sethares, Hutchinson–Knopoff, and Vassilakis dissonance

**A. Status.** **Optional** (dissonance models; selected by `dissonance_metric_mode`).

**B. Source.** [dissonance_models.py](../dissonance_models.py) Sethares L475–493; HK L587–667; Vassilakis L743–754.

**C. Exact code excerpt.**

```python
        y = self._s(f1) * (f2 - f1)
        d = min(a1, a2) * self.gain * (np.exp(-self.b1 * y) - np.exp(-self.b2 * y))
```

```python
        return num / denom
```

with $g(y)$ looked up and linearly interpolated; $y=|f_i-f_j|/\mathrm{CBW}(\bar f)$; $\mathrm{CBW}=1.72\,\bar f^{0.65}$ (Zwicker CB below a low-frequency cutoff).

```python
        R = (A1 * A2) ** self.spl_exp
        R *= self.pair_factor * (af_degree ** self.af_exp) * spectral
```

**D. Mathematical expression.**

Sethares: $s(f_1)=x^\star/(s_1 f_1+s_2)$, $y=s(f_1)(f_2-f_1)$, $d=\min(A_1,A_2)\,g\,(e^{-b_1 y}-e^{-b_2 y})$. Defaults $b_1=3.5$, $b_2=5.75$, $x^\star=0.24$, $s_1=0.0207$, $s_2=18.96$. Export modes: `sum`, `mean_pair`, default `minamp_norm` $=(\sum d)/(\sum\min A_i A_j)$.

HK (1978) eq. (3): $\sum_{i<j}A_i A_j g_{ij}/\sum A^2$. $g(y)=0$ if $y\le 0$ or $y>1.2$; else table interpolation. **Lookup table** — no closed $g$ invented here.

Vassilakis (2001) eq. (6.23): $R=(A_1 A_2)^{0.1}\cdot 0.5\cdot ((2A_2)/(A_1+A_2))^{3.11}\cdot(e^{-b_1 x}-e^{-b_2 x})$ with Sethares $s(f_1)$.

**E. Symbols.** $A$ linear. HK $g$ from tabulated $y$.

**F. Plain language.** Three published sensory-dissonance recipes on the same partial list.

**G. Scientific.** Implementations of named models; coefficient sets are those in the source. Optional `amps *= 2/N` compensation (L319–323) is **not** the default Stage 1 path unless enabled.

**H. Downstream.** `sethares_dissonance`, `hutchinson_knopoff_dissonance`, `vassilakis_dissonance`, `selected_dissonance_value`.

**I. Tests.** `tools/validation/dissonance_metric_mode.py`; phase-33 goldens.

---

### M-041. Log attack time and threshold segmentation

**A. Status.** **Production** (export `log_attack_time_s`). Not a full ADSR model.

**B. Source.** [temporal_segmentation.py](../temporal_segmentation.py) L37–81.

**C. Exact code excerpt.**

```python
    alpha = np.exp(-1.0 / max(1.0, 0.010 * sr))  # ~10 ms smoother
        env[i] = alpha * env[i - 1] + (1.0 - alpha) * env[i]
    onset_thr = 0.1 * peak
    attack_end_thr = 0.9 * peak
    rel_thr = 0.2 * peak
    attack_time_s = max((a_end - a_start) / sr, 1e-6)
        "log_attack_time_s": float(np.log10(attack_time_s)),
```

**D. Mathematical expression.**

$$
\alpha=e^{-1/\max(1,0.010 f_s)},\quad
e[n]=\alpha e[n-1]+(1-\alpha)|y[n]|
$$

Attack from $0.1\,\mathrm{peak}$ to $0.9\,\mathrm{peak}$; release after $0.2\,\mathrm{peak}$.

$$
\mathrm{LAT}=\log_{10}(\max(t_{\mathrm{attack}},10^{-6}))
$$

**E. Symbols.** $\log_{10}$. Peak = max envelope.

**F. Plain language.** How long the sound takes to get loud, on a log-seconds scale.

**G. Scientific.** One-pole envelope + fixed fractions. External `_ADSR.json` sidecars (production_policy) are a different, file-based path.

**H. Downstream.** Segment-wise MIR.

**I. Tests.** Temporal / phase-15 tests where present; no isolated LAT formula-validation test identified.

---

### M-042. Shannon / normalised spectral entropy

**A. Status.** **Production.**

**B. Source.** [acoustic_density_core.py](../acoustic_density_core.py) `_normalized_entropy` L292–300; Stage 1 applies it to $P=A_H^2$ via `density.compute_spectral_entropy` ([proc_audio.py](../proc_audio.py) L8932–8934).

**C. Exact code excerpt** (`_normalized_entropy`).

```python
def _normalized_entropy(power: np.ndarray) -> float:
    p = np.asarray(power, dtype=float)
    p = p[np.isfinite(p) & (p > 0.0)]
    if p.size <= 1:
        return 0.0
    p = p / max(float(np.sum(p)), EPS)
    h = -float(np.sum(p * np.log2(np.maximum(p, EPS))))
    hmax = math.log2(p.size)
    return float(np.clip(h / hmax if hmax > 0 else 0.0, 0.0, 1.0))
```

**D. Mathematical expression.**

$$
p_i=P_i/\max(\sum P,\varepsilon),\qquad
H=-\sum_i p_i\log_2(\max(p_i,\varepsilon)),\qquad
H_{\mathrm{norm}}=\mathrm{clip}\bigl(H/\log_2 K,\,0,1\bigr)
$$

on **power**. If fewer than two strictly positive finite bins remain, the function returns $0$. $\varepsilon$ is the module `EPS`.

**E. Symbols.** $K$: number of components. $\log_2$.

**F. Plain language.** Flat spectrum ⇒ entropy near 1; one peak ⇒ near 0.

**G. Scientific.** Discrete Shannon entropy of a power distribution.

**H. Downstream.** `spectral_entropy`; optional total-metric mix (L9022–9058).

**I. Tests.** Acoustic-density additional tests.

---

### M-043. Odd/even and low-mid ratios

**A. Status.** **Production.**

**B. Source.** [acoustic_density_core.py](../acoustic_density_core.py) odd/even ~L941–947; low-mid ~L882–886.

**C. Exact code excerpt.**

```python
        low_mid_mask = body_freq <= float(max(low_mid_upper_hz, bmin))
        low_mid_salience = float(np.sum(salience[low_mid_mask]))
        total_body_salience = float(np.sum(salience))
        if total_body_salience > 0.0:
            out["low_mid_energy_ratio"] = low_mid_salience / total_body_salience
```

```python
        odd_orders = [n for n in salient_orders if (n % 2) == 1]
        even_orders = [n for n in salient_orders if (n % 2) == 0]
        odd_power = float(np.sum([order_power_max[n] for n in odd_orders])) if odd_orders else 0.0
        even_power = float(np.sum([order_power_max[n] for n in even_orders])) if even_orders else 0.0
        out["odd_even_harmonic_energy_ratio"] = float(odd_power / max(even_power, EPS))
```

**D. Mathematical expression.**

$$
R_{\mathrm{oe}}=\frac{\sum P_{\mathrm{odd,salient}}}{\max(\sum P_{\mathrm{even,salient}},\varepsilon)}
$$

$$
\mathrm{LMER}=\frac{\sum\sqrt{P}\ \text{of body peaks with }f\le 2000\,\mathrm{Hz}}{\sum\sqrt{P}\ \text{of all body peaks}}
$$

`low_mid_upper_hz=2000`. Salience is $\sqrt{P}$. Salient orders keep the strongest peak per $n$ above a relative-dB floor.

**E. Symbols.** $P$: peak power. LMER uses $\sqrt{P}$ (amplitude-like salience), **not** $P$.

**F. Plain language.** Odd/even: clarinet-like vs open-string-like energy. Low-mid: how much of the “body” sits below 2 kHz.

**G. Scientific.** Descriptive ratios. 2000 Hz is a project cutoff.

**H. Downstream.** SBTI (M-044); research columns.

**I. Tests.** `tests/phase_12/test_acoustic_density_core_additional.py`.

---

### M-044. Spectral body-thickness index (SBTI)

**A. Status.** **Production** on the research workbook path — **not** computed in `compile_metrics.py`.

**B. Source.** [tools/export_research_density_workbook.py](../tools/export_research_density_workbook.py) L2088–2093.

**C. Exact code excerpt.**

```python
    out["spectral_body_thickness_index"] = (
        0.45 * _zscore(out["body_weighted_effective_density"])
        + 0.25 * _zscore(out["low_mid_energy_ratio"])
        + 0.20 * _zscore(out["harmonic_body_density_normalized"])
        + 0.10 * _zscore(out["residual_body_contribution_capped"])
    )
```

`_zscore` is $(x-\mu)/\sigma$ with population (ddof=0) mean/std over the export table; undefined if $\sigma=0$.

**D. Mathematical expression.**

$$
\mathrm{SBTI}=0.45\,z(\mathrm{BWED})+0.25\,z(\mathrm{LMER})+0.20\,z(\mathrm{HBDN})+0.10\,z(\mathrm{RBCC})
$$

**E. Symbols.** $z$: table-wise z-score. Weights sum to 1.

**F. Plain language.** A blended “how thick does this note look in the table?” score.

**G. Scientific.** Linear combination of z-scored columns. **Corpus-relative**: adding/removing notes changes $z$. Not a physical thickness.

**H. Downstream.** `spectral_body_thickness_index` only after Stage 3 research export.

**I. Tests.** Research-export / phase-10 body-density tests.

---

### M-045. Eligibility and stable-segment representativeness

**A. Status.** **Production** policy gates.

**B. Source.** [production_policy.py](../production_policy.py) `evaluate_eligibility` L172–174; `evaluate_stable_representativeness` L197–208.

**C. Exact code excerpt.**

```python
    frames_ineligible = bool(np.isfinite(frames) and frames < float(min_independent_frames))
    degenerate = bool(harmonics_known and harmonics <= 2)
    eligible = not frames_ineligible and not degenerate
```

```python
    ratio = (
        float(full_e / stable_e)
        if np.isfinite(full_e) and np.isfinite(stable_e) and abs(stable_e) > 1e-30
        else float("nan")
    )
    unrepresentative = bool(
        (np.isfinite(ratio) and ratio > float(max_ewsd_ratio))
        or (np.isfinite(centroid_ratio) and centroid_ratio > float(max_centroid_ratio))
    )
```

**D. Mathematical expression.**

$$
\mathrm{eligible}\iff (N_{\mathrm{frames}}\ge 8)\ \mathrm{and}\ (N_h>2)
$$

(defaults). $R_E=E_{\mathrm{full}}/E_{\mathrm{stable}}$ if $|E_{\mathrm{stable}}|>10^{-30}$; unrepresentative if $R_E>1.3$ or $\max(c)/\min(c)>2$.

**E. Symbols.** Frame count = independent STFT frames on the stable segment.

**F. Plain language.** Too-short or too-harmonic-poor takes, or takes whose “stable” slice is a bad stand-in for the whole file, are flagged.

**G. Scientific.** Policy thresholds, not a sampling theorem.

**H. Downstream.** `valid_for_primary_statistics`, EWSD eligibility flags. Digital silence is a separate ineligible reason (M-004).

**I. Tests.** `tests/phase_26/test_production_policy.py`.

---

### M-046. Bootstrap uncertainty for `note_density_final`

**A. Status.** **Production** (compile CI columns). Sensitivity analysis, not a coverage-bearing CI for a superpopulation.

**B. Source.** [density_uncertainty.py](../density_uncertainty.py) `bootstrap_note_density_final` L86–180; wired from [compile_metrics.py](../compile_metrics.py) L4658–4733.

**C. Exact code excerpt.**

```python
        point += r * _band_density_sum(a, weight_function)
            idx = rng.integers(0, a.size, a.size)
            a_rs = a[idx]
            e_band = float(np.sum(a_rs * a_rs))
```

Inside `_band_density_sum`, the compile-style operators are used: `linear → ΣA`, `log → log10(1+ΣA)`, `power → ΣA²`. Compile wires `propagate_ratio_uncertainty=True` ([compile_metrics.py](../compile_metrics.py) L4725).

**D. Mathematical expression.** Let $D^{(b)}=\sum_k r_k^{(b)} D_k^{(b)}$ on bootstrap $b=1\ldots B$. Report empirical quantiles (and relative width $|q_{hi}-q_{lo}|/|D|$). When ratio uncertainty is propagated, $r_k^{(b)}=E_k^{(b)}/\sum_j E_j^{(b)}$ with $E=\sum A^2$ on the resampled amplitudes. The point estimate always uses the originally measured ratios.

**E. Symbols.** Partials are a **deterministic** structure; the label used for EWSD analogues is `partial_multiset_sensitivity`.

**F. Plain language.** If we redraw the same peaks with replacement, how much does the density number wiggle?

**G. Scientific.** Non-parametric bootstrap of a fixed list. Does **not** resample FFT length, window, or $f_0$ error.

**H. Downstream.** `note_density_final_ci_*`. EWSD has a parallel BCa path in [tools/ewsd_uncertainty.py](../tools/ewsd_uncertainty.py).

**I. Tests.** `tests/phase_11/test_density_uncertainty.py`, `tests/phase_11/test_ewsd_uncertainty.py`.

---

### M-047. Combined log-space density (Stage 1 scalar)

**A. Status.** **Production** Stage 1 companion (not `note_density_final`).

**B. Source.** [proc_audio.py](../proc_audio.py) L8949–8957.

**C. Exact code excerpt.**

```python
                harm_log = math.log1p(max(0.0, harm_density))
                inharm_log = math.log1p(max(0.0, inharm_density))
                combined_log = self.harmonic_weight * harm_log + self.inharmonic_weight * inharm_log
                self.combined_density_metric_value = float(math.expm1(combined_log))
```

**D. Mathematical expression.**

$$
C=\exp\bigl(w_H\ln(1+D_H)+w_I\ln(1+D_I)\bigr)-1
$$

**E. Symbols.** $\ln$ = `log1p`. Weights are model H/I weights, **not** M-026 $r_k$.

**F. Plain language.** A two-band blend that stays well-behaved when one band is huge.

**G. Scientific.** Softplus-like mix. Distinct from M-029.

**H. Downstream.** `combined_density_metric_value`; optional `dynamic_density_score=C\log_{10}D_{\mathrm{filt}}$ (L9064–9065).

**I. Tests.** Phase-12 density additional tests.

---

### M-048. Parabolic (QIFFT) peak interpolation

**A. Status.** **Production.** Two variants.

**B. Source.** Linear magnitude: [proc_audio.py](../proc_audio.py) `_parabolic_peak` L1096–1105. Log magnitude: [harmonic_peak_validation.py](../harmonic_peak_validation.py) `_parabolic_interpolation_log_magnitude` L836–890. Acoustic-core QIFFT: [acoustic_density_core.py](../acoustic_density_core.py) `_local_maxima_peak_centers` L252–289.

**C. Exact code excerpt.**

```python
    alpha, beta, gamma = float(y[x-1]), float(y[x]), float(y[x+1])
    denom = (alpha - 2 * beta + gamma)
    if denom == 0.0:
        return x, beta
    p = 0.5 * (alpha - gamma) / denom
    xv = x + p
    yv = beta - 0.25 * (alpha - gamma) * p
```

**D. Mathematical expression.**

$$
p=\frac{\alpha-\gamma}{2(\alpha-2\beta+\gamma)},\qquad
x_\star=x+p,\qquad
y_\star=\beta-\tfrac14(\alpha-\gamma)p
$$

Log-magnitude path fits the same parabola to $\ln A$ (or dB) before converting the abscissa to hertz with $\Delta f$.

**E. Symbols.** $\alpha,\beta,\gamma$: three consecutive bins. **Amplitude** for `_parabolic_peak`; **log amplitude** for the harmonic-list path.

**F. Plain language.** Estimate the true peak sitting between FFT bins.

**G. Scientific.** Standard 3-point QIFFT. Bias remains for unresolved close tones.

**H. Downstream.** Peak frequencies fed to $B$ and assignment.

**I. Tests.** `tests/phase_12/test_proc_audio_core_additional.py` (`test_parabolic_peak_*`).

---

### M-049. $f_0$ candidate correction against a filename prior

**A. Status.** **Production** helper on the acoustic $f_0$ path (octave / integer-ratio unwrapping). Distinct from promoting the filename frequency itself to `f0_final` (that fallback is a later policy).

**B. Source.** [proc_audio.py](../proc_audio.py) `_correct_f0_candidate_against_prior` L1243–1301.

**C. Exact code excerpt.**

```python
    candidates: List[Tuple[float, float]] = [(cand, 1.0)]
    for r in range(2, int(max_harmonic_ratio) + 1):
        candidates.append((cand / float(r), 1.0 / float(r)))
        candidates.append((cand * float(r), float(r)))
    for hz, ratio in candidates:
        err = abs(1200.0 * np.log2(hz / prior))
        if err < best_err:
            best_err = err
            best_hz = float(hz)
            best_ratio = float(ratio)
```

**D. Mathematical expression.** Default $R_{\max}=6$. Candidate set:

$$
\{f\}\cup\{f/r,\, r f\}_{r=2}^{R_{\max}}
$$

Choose $f^\star$ minimising $|1200\log_2(f^\star/f_{\mathrm{prior}})|$. Invalid / non-positive inputs leave `valid=False`.

**E. Symbols.** $f$: raw detector candidate (Hz). $f_{\mathrm{prior}}$: M-012 nominal note frequency.

**F. Plain language.** If the detector reports $2f_0$ or $f_0/2$, fold it back to the named note when that is closer in cents.

**G. Scientific.** Discrete search over integer ratios. Heuristic octave/harmonic disambiguation, not a pitch model. Digital silence never uses this as a measurement (M-004).

**H. Downstream.** Corrected candidate may seed M-014 / M-015. If the later fit is rejected, the **uncorrected filename frequency** may still be retained as `f0_final` (intentional fallback).

**I. Tests.** `tests/phase_12/test_low_f0_harmonic_validation.py`; no isolated formula-validation test identified for the ratio search itself.

---

### M-050. Body-weighted effective density and salient harmonic coverage

**A. Status.** **Production** on the acoustic-density / research-descriptor path.

**B. Source.** [acoustic_density_core.py](../acoustic_density_core.py) body weights L875–900; salient coverage L904–934.

**C. Exact code excerpt.**

```python
        salience = np.sqrt(np.maximum(body_power, 0.0))
        knee = float(max(body_weight_knee_hz, 1e-6))
        w_body = 1.0 / (1.0 + np.square(body_freq / knee))
        wx = w_body * salience
        out["body_weighted_effective_density"] = _effective_count(wx)
```

```python
    expected_harmonic_order_count = int(math.floor(salient_ceiling_hz / float(f0_hz))) if _finite_positive(f0_hz) else 0
        out["salient_harmonic_coverage_up_to_body_ceiling"] = float(salient_count / expected_harmonic_order_count)
```

**D. Mathematical expression.**

$$
s_i=\sqrt{P_i},\qquad
w_i=\frac{1}{1+(f_i/f_{\mathrm{knee}})^2},\qquad
N_{\mathrm{eff}}^{\mathrm{body}}=\frac{(\sum w_i s_i)^2}{\sum (w_i s_i)^2}
$$

$$
N_{\mathrm{exp}}=\lfloor f_{\mathrm{ceil}}/f_0\rfloor,\qquad
\mathrm{coverage}=N_{\mathrm{salient}}/N_{\mathrm{exp}}
$$

($N_{\mathrm{eff}}$ is M-030 on the weighted salience.)

**E. Symbols.** $f_{\mathrm{knee}}$: `body_weight_knee_hz`. $f_{\mathrm{ceil}}$: `_salient_harmonic_ceiling_hz`.

**F. Plain language.** Count how many independent “body” peaks remain after down-weighting very high frequencies, and what fraction of expected harmonic slots are actually present.

**G. Scientific.** Lorentzian-like frequency taper is a project heuristic. Coverage is a occupancy ratio, not a psychoacoustic density.

**H. Downstream.** Acoustic-density export columns; SBTI uses LMER from M-043, not this $N_{\mathrm{eff}}$ directly.

**I. Tests.** `tests/phase_12/test_acoustic_density_core_additional.py`.

---

# External-library operations

Declared constraints (`pyproject.toml` / `requirements.txt`): numpy `>=1.21,<2`, scipy `>=1.7,<2`, librosa `>=0.9,<1`, pandas `>=1.3,<2`, soundfile `>=0.10,<1`.

**Installed in the audit environment** (`.venv`, 2026-09-17): numpy **1.26.4**, scipy **1.15.3**, librosa **0.11.0**, pandas **1.5.3**, soundfile **0.14.0**.

Default-dependent claims below were checked against those installed versions’ public behaviour (centered STFT, `amplitude_to_db` `ref=1.0`, `get_window(..., fftbins=True)`). Internal library algebra is **not** reproduced.

### L-001. `librosa.stft`

**Package / function.** librosa 0.11.0 installed (declared `>=0.9,<1`). `librosa.stft`.

**Call site.** [proc_audio.py](../proc_audio.py) L2472–2479. Characteristics fallback path ~L652.

**Arguments (production).** `y=y_norm`, `n_fft=n_fft_padded` ($N_{\mathrm{win}}Z$), `win_length=win_length`, `hop_length=self.hop_length`, `window=win_arg` (array or name), `center=True`. Other librosa defaults (`dtype`, `pad_mode='constant'`) are not overridden.

**Purpose.** Frame the RMS-normalised waveform and return a complex STFT. Project-owned scaling around the call is M-005–M-011.

**Scientific.** A library STFT; this audit does not reproduce librosa’s framing/FFT internals. Fallback: `scipy.signal.stft` if librosa fails (~L655).

### L-002. `librosa.amplitude_to_db`, `fft_frequencies`, `frames_to_time`

**Package / function.** librosa 0.11.0. Call site [proc_audio.py](../proc_audio.py) L2514–2517.

**Arguments.** `amplitude_to_db(S_mag, ref=1.0)` — amplitude dB versus the constant 1.0, **not** versus `np.max`. `fft_frequencies(sr=..., n_fft=n_fft_padded)` builds the Hertz grid (M-006). `frames_to_time` labels frame centres.

### L-003. `librosa.load` / `soundfile.read`

**Packages.** librosa 0.11.0; soundfile 0.14.0 (declared `>=0.10,<1`).

**Call sites.** [proc_audio.py](../proc_audio.py) L2136, L2143–2145; [audio_utils.py](../audio_utils.py). `sr=None` keeps the file’s native rate; `mono=True` in the utility helper (channel mean is then project-owned if a multi-channel array still arrives — M-001).

### L-004. `librosa.filters.get_window` / `scipy.signal.get_window`

**Packages.** librosa 0.11.0; scipy 1.15.3.

**Call sites.** [proc_audio.py](../proc_audio.py) L2551; [spectral_energy.py](../spectral_energy.py) L43 (`fftbins=True`). Returns window **samples** used for $G_c$ (M-007) and ENBW (M-021). Periodic (`fftbins=True`) vs symmetric is a library choice with a small end-sample effect.

### L-005. `scipy.optimize.linear_sum_assignment`

**Package.** scipy 1.15.3. Call site [inharmonicity_model.py](../inharmonicity_model.py) L172. Minimises the cents cost matrix constructed in M-020. Project-owned: cost fill, `LARGE_COST` infeasibility, monotone prune.

### L-006. `numpy.linalg.lstsq`

**Package.** numpy 1.26.4. Call site [inharmonicity_model.py](../inharmonicity_model.py) L293, `rcond=None` (numpy 1.26 default: machine-eps scaling). Solves the weighted design of M-019; the $f_n^2=an^2+cn^4$ algebra is project-owned.

### L-007. `numpy.fft.rfft` / `rfftfreq`

**Package.** numpy 1.26.4. Call site [proc_audio.py](../proc_audio.py) L12738–12739. Per-ADSR-segment real FFT (Hann, `n_fft_seg`) for MIR suffixes. Distinct from the production Stage 1 librosa STFT (L-001).

### L-008. `scipy.signal.savgol_filter`

**Package.** scipy 1.15.3. Call site [density.py](../density.py) ~L162. Optional $|STFT|$ smoothing; **default off** (`DEFAULT_STFT_MAGNITUDE_SMOOTHING_ENABLED=False`). Not on the comparable-corpus path.

### L-009. `pandas` Excel / DataFrame arithmetic

**Package.** pandas 1.5.3 (declared `>=1.3,<2`). Compile and export use `to_numeric(..., errors="coerce")` and workbook I/O. Not a spectral kernel. NaN propagation in M-029 is pandas/numpy IEEE behaviour.

### L-010. `hashlib.sha256` (identity only)

**Package.** Python standard library. Call site [export_row_identity.py](../export_row_identity.py) L53–61. `sample_id` from `note|stem|row_index`. Cryptographic hash used as a stable row identity, not an acoustic formula.

Equivalent STFT/window/load calls in [audio_analysis/super_audio_analyzer.py](../audio_analysis/super_audio_analyzer.py) are a **legacy parallel** analyser (see coverage). `librosa.pyin` / `yin` appear there, not on the default Stage 1 path.

---

# Scientific ambiguities and implementation/documentation disagreements

These are **observed facts**, not resolutions.

1. **Window default split.** `constants.DEFAULT_WINDOW="hann"` and `AudioProcessor.apply_filters_and_generate_data` default to Hann / `n_fft=4096` / hop $N/2$ if called directly. **CLI and GUI production** force **blackmanharris**, **8192**, **1024**, **zp=2**. [METRIC_FORMULA_INDEX.md](METRIC_FORMULA_INDEX.md) F-001 writes a textbook STFT; the executed transform is L-001. Direct `apply_filters_and_generate_data` defaults remain Hann / $N=4096$ / hop $N/2$.

2. **Two logarithms named `log`.** Element-wise $\varphi_{\mathrm{log}}=\ln(1+A)$ (M-028). Compile aggregate $D=\log_{10}(1+\sum A)$ (M-029). Element-wise compile override can switch a band back to `apply_density_metric` (ln).

3. **$B$ docstring vs `_wls_ac`.** Comments near the fitter can be read as “$f_0$ from n≥2 only”; executed code estimates $a$ on all orders and $c$ on $n\ge 2$ (M-019).

4. **Physical $B$ vs matching $B$.** Family scope NaNs the *export* $B$ (M-023) but the comb may still use $|B|>10^{-5}$ (M-022).

5. **Filename $f_0$ vs estimated $f_0$.** Fallback is intentional when the fit is rejected. Digital silence records a prior but **forbids** fallback-as-measurement (M-004).

6. **Two exclusive-assignment problems.** Hungarian order×peak (M-020) ≠ greedy same-bin ownership (M-017).

7. **F-047 vs F-056 pools.** Same Hill $D_1$/$D_2$ algebra, different inclusion rules (METRIC_FORMULA_INDEX F-056 note).

8. **SBTI location.** Documented as compile-time in some catalogues; implemented only in the research exporter (M-044).

9. **`note_parser` vs Hz.** Parsing only. Hertz is M-012. Some tests call `librosa.note_to_hz` on parsed tokens — a **test** convenience, not Stage 1.

10. **EWSD double penalty on d10.** Index F-048 records a frozen double $N_{\mathrm{eff}}/N$ when the original-sum metric already includes participation.

11. **CFAR / $t$-stat / bootstrap.** Implemented as screens or sensitivity tools; the code and index **disclaim formal coverage**.

12. **ACD invariance table.** Slow tests may regenerate `docs/validation/ACD_INVARIANCE_TABLE.md`; that is a generated cache, not a physical law.

13. **Bootstrap `log` matches compile, not element-wise $\varphi$.** `density_uncertainty._band_density_sum` uses $D=\log_{10}(1+\sum A)$ (M-029 / M-046). That is **not** $\sum\ln(1+A)$ from `WeightFunction.logarithmic` (M-028). The CI therefore tracks the compiled scalar, not the Stage 1 element-wise log path.

14. **STFT pad comment vs call.** A comment at [proc_audio.py](../proc_audio.py) L2520 says `center=True` uses reflected padding. The production `librosa.stft` call (L2472–2479) does **not** set `pad_mode`. Installed librosa 0.11.0 defaults to `pad_mode='constant'` (zero pad). Edge-frame weights (M-010) still assume a pad of $N_{\mathrm{FFT}}/2$ samples.

---

# Appendix A — Coverage of first-party Python files

110 first-party `.py` files (excluding `tests/`, `installers/`, `__pycache__`). Classification:

### Documented mathematical implementation

`audio_silence_trim.py`, `proc_audio.py`, `constants.py` (numeric formulae), `spectral_normalization.py`, `spectral_energy.py`, `production_policy.py`, `density.py`, `compile_metrics.py`, `inharmonicity_model.py`, `harmonic_peak_validation.py`, `acoustic_density_core.py`, `inharmonic_confirmation.py`, `subbass_policy.py`, `validated_partials.py`, `adaptive_density_engine.py`, `density_uncertainty.py`, `mir_descriptors.py`, `dissonance_models.py`, `temporal_segmentation.py`, `tools/spectral_density_hill.py`, `tools/spectral_mass.py`, `tools/ewsd_pure.py`, `tools/ewsd_core.py`, `tools/ewsd_uncertainty.py`, `tools/balanced_density.py`, `tools/export_research_density_workbook.py` (SBTI)

### External-library operations only (plus thin wrappers)

`audio_utils.py` (load), `run_orchestrator.py` / `pipeline_orchestrator_gui.py` / `pipeline_orchestrator_integrated.py` (defaults + L-001 configuration), `note_parser.py` (no Hz), `export_row_identity.py` (L-010)

### Duplicate / legacy / research implementation documented elsewhere

`audio_analysis/super_audio_analyzer.py` (parallel STFT/MIR; L-001 equivalent), `audio_analysis/batch_audio_analyzer.py`, `attic/interface.py`, `acoustic_data_analysis_suite.py`, `tools/compare_spectral_mass_v1_v2.py` (v1 mass), `tools/ewsd_research_integration.py`, `tools/acd_research_integration.py`, `tools/canonical_note_metrics.py`, `tools/validation/roughness_bandwidth_basis.py`, `tools/validation/hk_subbass_bandwidth.py`, `tools/validation/dissonance_metric_mode.py`

### Non-mathematical (orchestration, schema, I/O, GUI, provenance)

`__init__.py`, `analysis_policy.py`, `analysis_provenance.py`, `data_integrity.py`, `debug_counts.py`, `dissonance_export.py`, `gui_compile_stage2_worker.py`, `gui_model_weight_policy.py`, `log_config.py`, `main.py`, `metadata_sanitizer.py`, `metric_contract.py`, `metric_formula_versions.py` (ID registry only), `peak_component_counts.py`, `pipeline_contract.py`, `post_compile_research_export.py`, `publication_chart_policy.py`, `publication_metric_columns.py`, `result_cache.py`, `run_manifest.py`, `weight_function_ui_labels.py`, `verify_export.py`, `verify_runtime_schema.py`, `validate_canonical_metrics.py`, `audio_analysis/super_audio_analyzer_gui.py`, `tools/__init__.py`, `tools/validation/__init__.py`, `tools/validation/diff_workbooks.py`, `tools/validation/export_cleanup_fixture.py`, `tools/build_corpus_manifest.py`, `tools/verify_corpus.py`, `tools/generate_parameter_provenance.py`, `tools/reexport_corpus.py`, `tools/compare_runs.py`, `tools/r6/*.py`, `tools/r6b/*.py`, `tools/r1_stage3_b1.py`, `tools/r1b_census_held.py`, `tools/r5_oracle_ci.py`, `tools/p1_g3_swap.py`, `tools/perceptual_agreement.py`, `tools/perceptual_pairs.py`, `tools/wp2_acceptance_export.py`, `tools/ewsd_stage3_contract.py`, `tools/acd_stage3_contract.py`, `tools/ewsd_sensitivity_report.py`, `tools/backfill_spectral_mass.py`

### Math/policy modules summarised via callers (not given a separate M-id)

`energy_accounting.py` (uses M-024/M-025), `estimated_snr.py`, `harmonic_alignment.py`, `harmonic_high_n_guards.py`, `harmonic_validation.py`, `low_frequency_policy.py`, `spectral_leakage_guards.py`, `temporal_persistence.py`, `tools/diagnose_resolution_dependence.py`, `tools/note_density_nfft_sensitivity.py`, `tools/run_measurement_evaluation.py`, `run_real_corpus_validation.py`

No first-party `.py` file is listed as “not inspected.” Research runbooks were classified from module role and imports; they were not line-audited for hidden novel kernels. If a runbook contained a new estimator, it is an **explicit residual risk**.

---

# Appendix B — Source-file SHA-256

Hashes of the working-tree bytes cited in M/L entries. This document is **excluded**. Algorithm: SHA-256 of the entire file.

| Path | SHA-256 | Bytes |
|------|---------|------:|
| `audio_silence_trim.py` | `7a19524379ee6eb09e467ca7e9e61d0c9bab20e65eb06574acb2448b4dd77b1d` | 2563 |
| `proc_audio.py` | `6d406f40f1ac999164813e11a8d6de259b23c9145a9beca89e68255691a411a0` | 746252 |
| `constants.py` | `92942aae363fd871eaf0ba830a0a88559d707d3e26d7515c98eaaf9c93899f44` | 32453 |
| `spectral_normalization.py` | `0f7167e48554fe8d9d6e3c456ac4c97ff2a899ca36d4c6db8f79416164e38f71` | 3008 |
| `spectral_energy.py` | `a7c93681f15a34574b0752d33ea23394e082c9f1e20383b45c7e144962b3da77` | 12129 |
| `production_policy.py` | `06c97d4f05501af4c4993ae24b9ccd37ca1110fd52905ada55a3c42111c04437` | 13949 |
| `density.py` | `7c30b31e8a744a770244a480c5aee864bee816ab4685a975118fa2f40a439f2c` | 143028 |
| `compile_metrics.py` | `7274eaceb889ae2a78a8bc47cd3d1963024ae6266e16e1afb44a30a4e8365cb1` | 542268 |
| `inharmonicity_model.py` | `b48977d3e0b84d2efeb4c5b61733075dcd5e58a4ca0b4bdfffb0d40871607c17` | 21180 |
| `harmonic_peak_validation.py` | `4717433753449e3799cd2ea7ae2a7b2b90e0e3f054d60a85c57ed1a8e929f1bf` | 59819 |
| `acoustic_density_core.py` | `32f97f154b4a4c9b47ba9391820748e2c17e946c040769e9760ed391c4b5d81c` | 66334 |
| `note_parser.py` | `69f4e96be250b408b5a83ce8d04071eaf1771f6d0653d9ce5eaf6132b1f3f984` | 5833 |
| `inharmonic_confirmation.py` | `b7b6d760a769c31fed0c78e69ecf1d1e57a44aeacdfaf1f05c31d70cddc2b128` | 13574 |
| `subbass_policy.py` | `c1d9402f3cb14669210030e2e458f40cc94abd0662b77ee0498e97ac8ec79729` | 1582 |
| `validated_partials.py` | `095e7a93b413c95a3dc4d7bfb427d11ec04aa277a99b81155e80a410e017116a` | 12538 |
| `adaptive_density_engine.py` | `8b9dc459835dce4a97228dc518430e2d57000c5c5d70503c2b02ccedeeff263d` | 4575 |
| `density_uncertainty.py` | `3901aa0dc053b76b0dfd4e54da332e83cb1b8988e86904c5187fa0235ca17738` | 22000 |
| `mir_descriptors.py` | `8538469829209462ef4def2e3cdb3e770c840def197c7379a35ec77e03fe18ce` | 15697 |
| `dissonance_models.py` | `73ce9539b29e781e57fb63681aef35faadcaa9f703f6d25a9e4f58d68ca212d5` | 34696 |
| `temporal_segmentation.py` | `87a44cdf0956391c3b8d327f0dd5c26326a3c5fd468d2cf2132443363b47d225` | 2833 |
| `pipeline_orchestrator_gui.py` | `09ed9263363cd9601ca02fd6c1069c954dcf6f6141a81d00f2a863bcddf283b9` | 131557 |
| `run_orchestrator.py` | `abc6d82f366f6e742c265d2d52157832350aa4cbe14fa09e0e50ef91633a28b6` | 10077 |
| `tools/spectral_density_hill.py` | `988939c2cf60f5db8c32c3237a66c58617c7c0f484eacc44d870a3e7611e1215` | 20011 |
| `tools/spectral_mass.py` | `e7ddbec02401fbf85b2bf18cf6af562130d42aac7268fe6ac9c37e6c0d0a3531` | 9737 |
| `tools/ewsd_pure.py` | `78154bc1d6faf82817537ccb763df2a02c36ca333bd1516d93dad09698f111f7` | 11465 |
| `tools/ewsd_core.py` | `25161c10026a8b17ed2165db3467797a1d7e374ddf651fb0722e81ad3cc3e8bb` | 45593 |
| `tools/ewsd_uncertainty.py` | `59b3846076c794df518567f902e9832cd1383a2522c4d2baa16114193f9abde7` | 14309 |
| `tools/balanced_density.py` | `5cc6727d658fe698a00b22a6fb89b8391a0626b5aea736ebe2109403df16c356` | 8515 |
| `tools/export_research_density_workbook.py` | `5b2763ea64433933bb9f403966f284b04c360c680450a5f56014d3a20b0e342d` | 211682 |

Machine-readable copy (outside the repo): `Spectral_Analyser-git_ENV_20260917_075428\outputs\math_ref_source_hashes.json`.

---

# References actually consulted

In-repository (not an external bibliography dump):

- [METRIC_FORMULA_INDEX.md](METRIC_FORMULA_INDEX.md)
- [validation/FORMULA_VALIDATION_STATUS.md](validation/FORMULA_VALIDATION_STATUS.md)
- [validation/INHARMONICITY_FAMILY_SCOPE.md](validation/INHARMONICITY_FAMILY_SCOPE.md)
- [CONSTANTS_PROVENANCE.md](CONSTANTS_PROVENANCE.md) (existence; constants read from source)
- Module docstrings in `spectral_energy.py`, `subbass_policy.py`, `tools/spectral_density_hill.py`, `tools/spectral_mass.py`, `tools/ewsd_pure.py`, `dissonance_models.py`, `mir_descriptors.py`
- `REFERENCES.md` is cited *by those modules* for Fletcher (1962), Harris (1978), Heinzel et al. (2002), Glasberg & Moore (1990), Moore & Glasberg (1983), Hill (1973), Sethares (2005), Hutchinson & Knopoff (1978), Vassilakis (2001), Zwicker & Fastl (1990). Those works were **not** re-read for this audit; attributions follow the source comments.

Installed-library versions: numpy 1.26.4, scipy 1.15.3, librosa 0.11.0 (call signatures only).

Numerical spot checks (outside the repo): $440\cdot 2^{-4.75}\approx 16.3516$; $\min(0.5\cdot 55,80)=27.5$.

---

*End of reference. Documentation does not validate the science.*
