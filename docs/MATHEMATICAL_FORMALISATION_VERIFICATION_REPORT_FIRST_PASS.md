# Mathematical Formalisation and Verification Report — First Pass

**Repository:** `SoundSpectrAnalyse-main_6`  
**Primary code source:** `density.py` (verified against implementation; line numbers refer to this file at time of writing).  
**Rules observed:** Read-only review; third-party libraries (NumPy, SciPy, librosa, pandas, …) treated as black boxes; no code changes implied by this document.

---

## 1. Scope

This pass formalises and verifies **six** functions in **`density.py`**, in this order:

1. `compute_spectral_entropy` (lines 559–609)  
2. `effective_partial_density_from_powers` (lines 2267–2293)  
3. `_spectral_neff_from_filtered_linear_amplitudes` (lines 1808–1825)  
4. `_apply_discrete_spectral_metrics` (lines 1828–1896)  
5. `apply_density_metric` (lines 2080–2198)  
6. `compute_rolloff_compensated_harmonic_density` (lines 1690–1802)

Supporting definitions used by (5) and (6): `DISCRETE_SPECTRAL_METRIC_KEYS` (lines 1805–1806), `get_weight_function` / `WeightFunction` (lines 1405–1483), `DEFAULT_HARMONIC_ROLLOFF_ALPHA` (line 1487), `DEFAULT_ROLLOFF_COMPENSATED_DENSITY_WEIGHT_FUNCTION` (line 1488).

---

## 2. Method

1. Read each function’s control flow, filters, and numeric expressions.  
2. Map operations to explicit discrete mathematics (finite sums, piecewise definitions).  
3. State assumptions and caller contracts implied by names, docstrings, and operations (without inventing physics beyond the code).  
4. Propose hand-checkable examples and `numpy.testing.assert_allclose`-style checks (proposed only; no test files created here).  
5. Assign a correctness verdict relative to the **implemented** specification (internal consistency).

---

## 3. Function-by-function formalisation

### 3.1 `compute_spectral_entropy`

#### 3.1.1 Function identification

| Item | Detail |
|------|--------|
| **File** | `density.py` |
| **Signature** | `def compute_spectral_entropy(power: np.ndarray) -> float:` |
| **Return** | `float` in \([0,1]\) after clipping; early returns `0.0` |
| **Core lines** | 569–605 |

#### 3.1.2 Plain-language purpose

Build a non-negative mass vector from the input, drop negligible masses, form a probability vector by normalising to the sum, compute Shannon entropy in **bits** (\(\log_2\)), divide by the entropy of the **uniform distribution** over the surviving count \(N\), then clip to \([0,1]\).

#### 3.1.3 Mathematical formulation

Let the raw input be \((x_1,\ldots,x_M)\).

**Absolute value**

\[
u_i = |x_i|.
\]

**Strict threshold filter** (`power > 1e-12`)

\[
\mathcal{I} = \{\, i \mid u_i > 10^{-12}\,\}, \quad
P_j = u_{i_j},\ j=1,\ldots,N
\]

reindexed over \(\mathcal{I}\). If \(N=0\): return \(0\).

**Total mass**

\[
S = \sum_{j=1}^{N} P_j.
\]

If \(S \le 0\): return \(0\).

**Normalised weights**

\[
p_j = \frac{P_j}{S}, \qquad \sum_{j=1}^{N} p_j = 1.
\]

**Shannon entropy (bits)**

\[
H = -\sum_{j=1}^{N} p_j \log_2 p_j.
\]

**Normalisation denominator**

\[
H_{\max} = \log_2 N.
\]

**Normalised value (before clip)**

\[
\tilde{H} =
\begin{cases}
0 & \text{if } H_{\max} \le 0 \ (\text{e.g. } N=1 \Rightarrow \log_2 1 = 0) \\
H / H_{\max} & \text{if } H_{\max} > 0
\end{cases}
\]

**Output**

\[
H_{\mathrm{out}} = \operatorname{clip}(\tilde{H},\,0,\,1).
\]

**Contract note:** The parameter is named `power`, but the implementation applies `np.abs` and does **not** square amplitudes. The mathematical object is “non-negative channel values treated as mass,” not necessarily \(A^2\) unless the caller already passed powers.

#### 3.1.4 Code-to-formula mapping

| Code expression | Mathematical equivalent | Notes |
|------------------|---------------------------|--------|
| `power = np.abs(power)` | \(u_i = \|x_i\|\) | |
| `power = power[power > 1e-12]` | strict threshold on mass | |
| `total_power = np.sum(power)` | \(S = \sum P_j\) | |
| `p = power / total_power` | \(p_j = P_j/S\) | |
| `-np.sum(p * np.log2(p))` | \(H = -\sum p_j \log_2 p_j\) | **Base 2** |
| `max_entropy = np.log2(len(power))` | \(H_{\max} = \log_2 N\) | \(N\) = post-filter count |
| `normalized_entropy = entropy / max_entropy` | \(\tilde H = H/H_{\max}\) | For \(N=1\), code sets \(0\) |
| `np.clip(..., 0.0, 1.0)` | \(\operatorname{clip}(\tilde H,0,1)\) | |

#### 3.1.5 Assumptions

- Input may be any finite numeric sequence; negatives mapped by \(|\cdot|\).  
- Entropy uses **\(\log_2\)** only.  
- Normaliser is \(\log_2 N\) for **retained** count \(N\), not \(\log_2 M\) for original length.  
- Output is explicitly clipped to \([0,1]\).  
- NaN/Inf are not filtered before `abs`; non-finite values can propagate unless upstream is clean.

#### 3.1.6 Edge cases

| Case | Behaviour |
|------|-------------|
| Empty input | `0.0` |
| All masses \(\le 10^{-12}\) after `abs` | `0.0` |
| `total_power <= 0` | `0.0` |
| Exactly one survivor (\(N=1\)) | Shannon \(H=0\); `log2(1)=0` → branch sets **normalized \(= 0.0`** |
| Uniform on \(N>1\) | \(\tilde H = 1\) |

#### 3.1.7 Numerical verification (proposed)

- **Example A:** `power = [4, 4]` → \(p=[0.5,0.5]\), \(H=1\), \(H_{\max}=1\) → output `1.0`.  
- **Example B:** `power = [1, 0, 0]` → after filter one mass → output `0.0` (implementation convention).

#### 3.1.8 Correctness verdict

**MATHEMATICALLY CORRECT BUT NEEDS DOCUMENTATION** — internally consistent for finite positive masses on survivors; caller contract for “power” vs `abs` without squaring should be documented; \(N=1 \Rightarrow 0\) convention must be stated in any thesis.

#### 3.1.9 Documentation recommendation

State: (i) \(\log_2\) entropy; (ii) masses = `abs` then threshold \(10^{-12}\); (iii) normaliser \(\log_2 N\) for retained \(N\); (iv) single-bin returns \(0\) by code path.

---

### 3.2 `effective_partial_density_from_powers`

#### 3.2.1 Function identification

| Item | Detail |
|------|--------|
| **Signature** | `def effective_partial_density_from_powers(powers: np.ndarray, *, eps: float = 1e-30,) -> float:` |
| **Core lines** | 2284–2293 |

#### 3.2.2 Plain-language purpose

Inverse participation ratio on strictly positive finite powers after filtering \(P_i > \varepsilon\):

\[
D_{\mathrm{eff}} = \frac{\left(\sum_{i=1}^{N} P_i\right)^2}{\sum_{i=1}^{N} P_i^2}.
\]

#### 3.2.3 Mathematical formulation

Let \(Q_k\) be flattened inputs. Retain indices with finite \(Q_k\) and \(Q_k > \varepsilon\). Denote retained \(P_1,\ldots,P_N\).

\[
S_1 = \sum_{i=1}^{N} P_i, \qquad S_2 = \sum_{i=1}^{N} P_i^2.
\]

If \(N=0\) or \(S_1 \le \varepsilon\) or \(S_2 \le \varepsilon\): return \(0\). Else \(D_{\mathrm{eff}} = S_1^2 / S_2\); if not finite, return \(0\).

**Scale invariance:** For \(\lambda > 0\), replacing \(P_i\) by \(\lambda P_i\) leaves \(D_{\mathrm{eff}}\) unchanged.

#### 3.2.4 Code-to-formula mapping

| Code | Math |
|------|------|
| `p = p[np.isfinite(p) & (p > float(eps))]` | retain \(P_i > \varepsilon\) |
| `s = float(np.sum(p))`, `ss = float(np.sum(p * p))` | \(S_1, S_2\) |
| `d = (s * s) / ss` | \(S_1^2/S_2\) |

#### 3.2.5 Assumptions

Input is **linear power** in the docstring sense; code does not square again. Result is **not** bounded to \([0,1]\).

#### 3.2.6 Edge cases

Empty / all filtered → `0.0`; one component \(P > \varepsilon\) → \(D_{\mathrm{eff}} = 1\); uniform positive powers → \(D_{\mathrm{eff}} = N\).

#### 3.2.7 Numerical verification (proposed)

`powers = [1.0, 1.0, 1.0]` → \(S_1=3\), \(S_2=3\) → \(D_{\mathrm{eff}} = 3\). Use `assert_allclose(out, 3.0)`.

#### 3.2.8 Correctness verdict

**CORRECT AS IMPLEMENTED** for the stated formula on filtered nonnegative inputs.

#### 3.2.9 Documentation recommendation

Define \(D_{\mathrm{eff}}\) exactly with strict \(P_i > \varepsilon\) filter; state scale invariance; clarify “powers” vs amplitudes.

---

### 3.3 `_spectral_neff_from_filtered_linear_amplitudes`

#### 3.3.1 Function identification

| Item | Detail |
|------|--------|
| **Signature** | `def _spectral_neff_from_filtered_linear_amplitudes(v: np.ndarray) -> float:` |
| **Core lines** | 1814–1825 |

#### 3.3.2 Plain-language purpose

From nonnegative linear amplitudes \(A_i\), set \(W_i = A_i^2\), \(S = \sum_i W_i\), \(p_i = W_i/S\), then

\[
N_{\mathrm{eff}} = \frac{1}{\sum_{i=1}^{N} p_i^2}.
\]

#### 3.3.3 Mathematical formulation

Same as §3.2 with \(P_i = A_i^2\) and **no** per-element \(>\varepsilon\) filter on amplitudes; only guards on empty vector and \(S \le 10^{-30}\), \(\sum p_i^2 \le 10^{-30}\).

#### 3.3.4 Relation to `effective_partial_density_from_powers`

For nonnegative amplitudes,

\[
N_{\mathrm{eff}}(\{A_i\}) = \frac{\left(\sum_i A_i^2\right)^2}{\sum_i A_i^4} = D_{\mathrm{eff}}\bigl(\{A_i^2\}\bigr)
\]

**when** the \(\varepsilon\)-filter in `effective_partial_density_from_powers` does not remove additional terms. Filters differ in edge cases (tiny positives).

#### 3.3.5 Correctness verdict

**CORRECT AS IMPLEMENTED** for \(1/\sum p_i^2\) on \(p_i \propto A_i^2\).

#### 3.3.6 Documentation recommendation

Relate explicitly to inverse participation on squared amplitudes and to \(D_{\mathrm{eff}}\) on the power vector; note threshold differences vs §3.2.

---

### 3.4 `_apply_discrete_spectral_metrics`

#### 3.4.1 Function identification

| Item | Detail |
|------|--------|
| **Signature** | `def _apply_discrete_spectral_metrics(weight_key, values, frequencies=None, *, d24_amplitude_max_override=None) -> float:` |
| **Core lines** | 1844–1896 |

#### 3.4.2 Plain-language purpose

Atomic scalar summaries on **linear amplitudes** \(A_i \ge 0\) (finite mask; optional aligned frequencies). **No** max-normalisation or rolloff compensation inside this function (docstring L1836).

#### 3.4.3 Preprocessing

Flatten `values` to \(v\). If `frequencies` has same length as \(v\), keep aligned \(f_i\); else ignore frequencies.

Mask:

\[
m_i = \mathbb{1}[v_i\ \text{finite}] \cdot \mathbb{1}[v_i \ge 0] \cdot
\begin{cases}
\mathbb{1}[f_i\ \text{finite}] & \text{if aligned} \\
1 & \text{otherwise}
\end{cases}
\]

Let \(A_i\) be the retained sequence, \(i=1,\ldots,N\). If \(N=0\): return \(0\).

#### 3.4.4 Metrics

**d3**

\[
\mathrm{d3} = \sum_{i=1}^{N} \ln(1 + A_i) \quad \text{(natural log, `np.log1p`).}
\]

**d10**

\[
S_{\ln} = \sum_{i=1}^{N} \ln(1 + A_i), \qquad
N_{\mathrm{eff}} = N_{\mathrm{eff}}(\{A_i\}) \ \text{from §3.3},
\]

\[
\mathrm{d10} = S_{\ln} \cdot \frac{N_{\mathrm{eff}}}{N}.
\]

**d17**

\[
E = \sum_{i=1}^{N} A_i^2, \qquad
\mathrm{d17} = \ln(1 + E)\cdot \ln(1 + N_{\mathrm{eff}}).
\]

**d24**

Let

\[
A_{\max} =
\begin{cases}
\texttt{d24\_amplitude\_max\_override} & \text{if finite override} \\
\max_i A_i & \text{otherwise.}
\end{cases}
\]

If \(A_{\max} \le 0\): return \(0\).

Frequency mask: if frequencies present, \(F_i = \mathbb{1}[f_i \le 12000]\); else all `True`.

Amplitude mask: \(G_i = \mathbb{1}[A_i \ge 0.01\,A_{\max}]\).

Retain \(A^{(24)}\) with \(F_i \wedge G_i\). If empty: return \(0\).

\[
\mathrm{d24} = \sum_{j} \ln\bigl(1 + A^{(24)}_j\bigr).
\]

Unknown keys → `0.0`.

#### 3.4.5 Code-to-formula mapping

| Key | Formula |
|-----|---------|
| d3 | \(\sum \ln(1+A_i)\) |
| d10 | \(\bigl(\sum \ln(1+A_i)\bigr)\, N_{\mathrm{eff}}/N\) |
| d17 | \(\ln(1+\sum A_i^2)\,\ln(1+N_{\mathrm{eff}})\) |
| d24 | \(\sum \ln(1+A_i)\) on \(f_i \le 12000\) and \(A_i \ge 0.01 A_{\max}\) |

#### 3.4.6 Correctness verdict

**CORRECT BUT MODEL-DEPENDENT** — matches coded piecewise definitions; composite heuristics for scientific interpretation.

#### 3.4.7 Documentation recommendation

Four explicit equations; natural logs; 1% and 12 kHz gates; definition of \(N_{\mathrm{eff}}\) used in d10/d17.

---

### 3.5 `apply_density_metric`

#### 3.5.1 Function identification

| Item | Detail |
|------|--------|
| **Signature** | `def apply_density_metric(values, weight_function='linear', normalize=False, remove_noise=False, frequencies=None, fundamental_freq=None, account_for_spectral_rolloff=True, prevent_domination=True):` |
| **Core lines** | 2106–2198 (plus discrete short-circuit 2111–2112) |

#### 3.5.2 Two disjoint paths

**(A) Discrete short-circuit:** If normalised `weight_function` key is in \(\{\texttt{d3},\texttt{d10},\texttt{d17},\texttt{d24}\}\),

\[
\text{return } \texttt{\_apply\_discrete\_spectral\_metrics}(\texttt{key}, \texttt{values}, \texttt{frequencies}).
\]

This **bypasses** `remove_noise`, NaN/Inf filtering, domination, and rolloff blocks.

**(B) Generic path:** optional noise gate; finite filter; `abs` for negatives; optional max-normalisation if `prevent_domination` and \(N>1\); optional rolloff compensation; `get_weight_function`; sum; optional divide by \(N\).

#### 3.5.3 Generic path mathematics

Let amplitudes after early steps be \(a_i\), \(i=1,\ldots,N\).

**Optional noise removal** (`remove_noise`): keep \(a_i > 10^{-6} \max_j a_j\).

**Finite filter:** drop non-finite; if empty return \(0\).

**Nonnegativity:** \(a_i \leftarrow |a_i|\) if any negative.

**Domination prevention** (`prevent_domination` and \(N>1\)): if \(a_{\max} = \max_i a_i > 10^{-10}\),

\[
a_i \leftarrow \frac{a_i}{a_{\max}}.
\]

**Rolloff** (`account_for_spectral_rolloff` and `frequencies` and `fundamental_freq` with \(f_0>0\)):

Harmonic number (continuous):

\[
n_i = \frac{f_i}{f_0}.
\]

Hard-coded in code:

\[
\alpha = 1.5.
\]

Expected factor:

\[
E_i = \bigl(\max(n_i, 1)\bigr)^{-\alpha}.
\]

Compensated amplitudes:

\[
a_i \leftarrow \frac{a_i}{E_i + 10^{-10}}.
\]

**Weight and sum**

Let \(w\) be the element-wise weight from `get_weight_function(weight_function)` (e.g. `linear`: identity; `logarithmic`: \(\ln(1+a_i)\)).

\[
R = \sum_{i=1}^{N} w(a_i).
\]

If `normalize` and \(N>0\): return \(R/N\); else return \(R\).

#### 3.5.4 Important implementation facts

- \(\alpha = 1.5\) is a **literal** at line 2168, **not** wired to `DEFAULT_HARMONIC_ROLLOFF_ALPHA` in this function.  
- Rolloff uses **continuous** \(f_i/f_0\), not `round` (contrast §3.6).  
- Result is **unbounded** in general (no clip).

#### 3.5.5 Correctness verdict

**CORRECT BUT MODEL-DEPENDENT** — matches implementation; discrete short-circuit semantics must be documented for callers.

#### 3.5.6 Documentation recommendation

Flowchart with two branches; explicit \(\alpha\), \(\varepsilon = 10^{-10}\); `prevent_domination` requires \(N>1\); rolloff requires `frequencies` and \(f_0>0\).

---

### 3.6 `compute_rolloff_compensated_harmonic_density`

#### 3.6.1 Function identification

| Item | Detail |
|------|--------|
| **Signature** | `def compute_rolloff_compensated_harmonic_density(amplitudes, frequencies_hz, fundamental_freq_hz, *, harmonic_orders=None, alpha: float = DEFAULT_HARMONIC_ROLLOFF_ALPHA, weight_function: str = DEFAULT_ROLLOFF_COMPENSATED_DENSITY_WEIGHT_FUNCTION, epsilon: float = 1e-12,) -> Dict[str, Any]:` |
| **Core lines** | 1734–1800 |

#### 3.6.2 Algorithm (computed branch)

Integer orders:

\[
n_i =
\begin{cases}
\mathrm{round}(h_i) & \text{if optional } h_i \text{ provided} \\
\mathrm{round}(f_i/f_0) & \text{otherwise}
\end{cases}
\]

Retain rows with finite \(A_i,f_i\), \(A_i\ge 0\), \(f_i>0\), \(n_i\ge 1\).

Max-normalise:

\[
A^{\mathrm{norm}}_i = \frac{A_i}{\max_j A_j}.
\]

Expected rolloff:

\[
E_i = \bigl(\max(n_i,1)\bigr)^{-\alpha}
\]

(compensated denominator uses \(\max(n_i,1)\) in code).

Compensate:

\[
C_i = \frac{A^{\mathrm{norm}}_i}{E_i + \varepsilon}, \qquad \varepsilon = 10^{-12}\ \text{by default}.
\]

Density:

\[
D = \sum_i w(C_i)
\]

with default weight `logarithmic` \(\Rightarrow w(C_i)=\ln(1+C_i)\).

Optional ratio (docstring warns **not** in \([0,1]\)):

If \(\exists\) partial with \(n_i=1\), let \(A^{(1)}\) be the **first** such raw amplitude in index order; if \(A^{(1)} > \varepsilon\),

\[
D_{\mathrm{norm}} = \frac{D}{A^{(1)}}.
\]

Else `nan`.

#### 3.6.3 Correctness verdict

**CORRECT BUT MODEL-DEPENDENT** — matches docstring (lines 1703–1708); optional normalised field is explicitly **not** a calibrated \([0,1]\) metric (lines 1718–1721).

#### 3.6.4 Documentation recommendation

Emphasise **rounded** orders, default **logarithmic** weight on compensated values, and non-probability interpretation of `rolloff_density_metric_normalized`.

---

## 4. Cross-function consistency

| Topic | Observation |
|-------|-------------|
| \(N_{\mathrm{eff}}\) vs \(D_{\mathrm{eff}}\) on powers | \(N_{\mathrm{eff}}(\{A_i\}) = D_{\mathrm{eff}}(\{A_i^2\})\) algebraically; filters differ (§3.2 vs §3.3). |
| Entropy vs effective counts | Entropy uses normalised **\(|x|\)** (thresholded); effective counts use **\(A^2\)** or user powers — different objects. |
| Rolloff: two conventions | `apply_density_metric`: continuous \(f/f_0\), **literal** \(\alpha=1.5\). `compute_rolloff_compensated_harmonic_density`: **rounded** orders, \(\alpha\) **parameter** defaulting from `DEFAULT_HARMONIC_ROLLOFF_ALPHA` (=1.5). |
| Log bases | Discrete metrics and `WeightFunction.logarithmic` use **natural** `log1p`; `compute_spectral_entropy` uses **\(\log_2\)**. |

---

## 5. Ambiguities and risks

1. `compute_spectral_entropy`: parameter name `power` vs `abs` without squaring.  
2. `N=1` entropy: returns **0**, not undefined — must be cited in papers.  
3. `apply_density_metric`: discrete short-circuit **ignores** `remove_noise` / generic preprocessing.  
4. Hard-coded \(\alpha=1.5\) in `apply_density_metric` vs named default in rolloff function — drift risk.  
5. Continuous vs rounded harmonic index across rolloff-related paths.  
6. `compute_spectral_entropy`: no explicit `isfinite` filter before probability normalisation.

---

## 6. Recommended numerical tests (proposed only)

1. `test_entropy_uniform_two_bins`: `[1,1]` → `1.0`.  
2. `test_deff_uniform_powers`: three equal powers → `3.0`.  
3. `test_neff_matches_deff_on_squares`: compare §3.3 vs §3.2 on positive toys (watch \(\varepsilon\)).  
4. `test_d3_d10_d17_d24_toy`: small handcrafted vectors.  
5. `test_apply_density_metric_discrete_ignores_remove_noise`.  
6. `test_rolloff_rounding_vs_apply_density_continuous` near half-integer \(f/f_0\).

Use `numpy.testing.assert_allclose` with explicit `rtol` / `atol` for log chains.

---

## 7. Final priority for next pass

1. `get_weight_function` / `WeightFunction` — completes interpretation of weighted sums.  
2. `band_partial_metric_sum` / `partial_metric_sums_h_i_s_total` / `compute_discrete_spectral_metrics_bundle`.  
3. `proc_audio` producers of inputs (scaling, dB vs linear, which arrays feed “power” for entropy).  
4. `compile_metrics` dataset-relative normalisations consuming these metrics.

---

*End of document.*
