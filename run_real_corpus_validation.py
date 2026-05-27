"""run_real_corpus_validation.py
==================================

Reproducible validation workflow for a small controlled corpus of real
instrumental sounds.

Pipeline
--------
1. Load a corpus manifest (CSV or JSON) listing audio files plus required
   metadata fields (instrument, instrument_family, technique, written_pitch,
   sounding_pitch, dynamic, register, source, notes).
2. For each entry: run the canonical single-pass spectral analysis
   (``proc_audio.AudioProcessor``) and harvest the canonical metrics.
3. Merge manifest metadata + canonical metrics into a single wide
   ``Canonical_Metrics``-compatible DataFrame.
4. Write a compiled workbook (``compiled_canonical.xlsx``) containing a
   ``Canonical_Metrics`` sheet, suitable for downstream tooling.
5. Invoke ``validate_canonical_metrics.validate_corpus`` to produce the
   validation report (XLSX + Markdown).
6. Preserve a ``run_manifest.json`` snapshot recording the software version,
   parameters used, timestamp, and exact input file list.

Scientific framing
------------------
The workflow makes **no musicological claims**. The "Physical-acoustic
validation notes" section in the Markdown report only states measured
quantities, near-constants, and empirical redundancies. Forbidden terms
(orchestration function, perceptual tension, expressive intensity,
timbral salience, musical density perception) are explicitly absent from
the generated text. Adding a perceptual layer later remains an open
extension.

Usage
-----
::

    python run_real_corpus_validation.py \\
        --manifest validation_corpus_manifest.csv \\
        --output-dir validation_runs/2026-05-12 \\
        --group-by instrument --group-by instrument_family \\
        [--dictionary metrics_dictionary.json] \\
        [--coverage-threshold 0.80] \\
        [--correlation-threshold 0.90] \\
        [--allow-missing-files]
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as _dt
import json
import logging
import os
import platform
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Manifest schema
# ---------------------------------------------------------------------------
REQUIRED_MANIFEST_FIELDS: Tuple[str, ...] = (
    "file_path",
    "instrument",
    "instrument_family",
    "technique",
    "written_pitch",
    "sounding_pitch",
    "dynamic",
    "register",
    "source",
    "notes",
)

# Fields that must be non-empty for the entry to be considered fully
# specified. ``notes`` is allowed to be blank — it is free-form annotation.
REQUIRED_NON_EMPTY_FIELDS: Tuple[str, ...] = tuple(
    f for f in REQUIRED_MANIFEST_FIELDS if f != "notes"
)


@dataclass(frozen=True)
class CorpusEntry:
    """One row of the corpus manifest, validated and normalised."""

    file_path: str
    instrument: str
    instrument_family: str
    technique: str
    written_pitch: str
    sounding_pitch: str
    dynamic: str
    register: str
    source: str
    notes: str

    def asdict(self) -> Dict[str, str]:
        return asdict(self)


def load_corpus_manifest(path: Path) -> List[CorpusEntry]:
    """Read a manifest (.csv or .json) into a typed list of ``CorpusEntry``.

    Unknown columns are silently ignored. Missing required columns raise
    ``ValueError`` with the full list of offenders.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Manifest not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".json":
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and "entries" in data:
            rows = list(data["entries"])
        elif isinstance(data, list):
            rows = list(data)
        else:
            raise ValueError(
                f"{path}: JSON manifest must be a list or a dict with 'entries'"
            )
    elif suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
    else:
        raise ValueError(f"{path}: unsupported manifest suffix {suffix!r}")

    missing_cols: List[str] = []
    if rows:
        sample_keys = set(rows[0].keys())
        for f in REQUIRED_MANIFEST_FIELDS:
            if f not in sample_keys:
                missing_cols.append(f)
    if missing_cols:
        raise ValueError(
            f"{path}: manifest missing required columns: {missing_cols}"
        )

    entries: List[CorpusEntry] = []
    for raw in rows:
        kwargs = {f: str(raw.get(f, "") or "").strip() for f in REQUIRED_MANIFEST_FIELDS}
        entries.append(CorpusEntry(**kwargs))
    return entries


def validate_manifest_entries(
    entries: List[CorpusEntry],
    *,
    manifest_dir: Path,
    allow_missing_files: bool = False,
) -> List[str]:
    """Run integrity checks on the parsed manifest. Returns warning strings.

    A warning is appended (not an exception raised) so the caller can decide
    whether to abort or continue.
    """
    warns: List[str] = []
    seen_paths: Dict[str, int] = {}
    for idx, e in enumerate(entries):
        # required non-empty fields
        for f in REQUIRED_NON_EMPTY_FIELDS:
            if not getattr(e, f):
                warns.append(
                    f"MANIFEST: entry #{idx} ({e.file_path or '?'}) has empty "
                    f"required field '{f}'."
                )

        # file existence
        if not e.file_path:
            continue
        candidate = Path(e.file_path)
        if not candidate.is_absolute():
            candidate = (manifest_dir / candidate).resolve()
        if not candidate.is_file():
            level = "MANIFEST-WARN" if allow_missing_files else "MANIFEST-ERROR"
            warns.append(
                f"{level}: audio file listed in manifest is missing: "
                f"{e.file_path} (resolved as {candidate})"
            )

        # duplicate paths
        seen_paths[e.file_path] = seen_paths.get(e.file_path, 0) + 1

    for fp, n in seen_paths.items():
        if n > 1:
            warns.append(
                f"MANIFEST: duplicate file_path appears {n} times in manifest: {fp}"
            )

    return warns


# ---------------------------------------------------------------------------
# Per-file canonical analysis
# ---------------------------------------------------------------------------
@dataclass
class AnalysisParameters:
    """Knobs forwarded to ``proc_audio.AudioProcessor``.

    Defaults are aligned with the fast-but-honest single-pass profile used by
    the end-to-end tests.
    """

    freq_min: float = 50.0
    freq_max: float = 12000.0
    db_min: float = -90.0
    db_max: float = 0.0
    window: str = "blackmanharris"
    n_fft: int = 8192
    hop_length: int = 1024
    tolerance: float = 10.0
    use_adaptive_tolerance: bool = True
    weight_function: str = "linear"
    zero_padding: int = 1
    time_avg: str = "mean"
    auto_model_weights_from_analysis: bool = True
    dissonance_enabled: bool = False
    spectral_masking_enabled: bool = False
    tier: str = "Tier_corpus_validation"


# ---------------------------------------------------------------------------
# Canonical metric provenance taxonomy
# ---------------------------------------------------------------------------
# Three exhaustive, non-overlapping buckets reconcile every ``status="canonical"``
# entry in metrics_dictionary.json with how the corpus-validation script
# obtains its value. The constants below are the single source of truth for
# the coverage contract tested in ``tests/test_real_corpus_validation.py``.
#
#   * DIRECT     — instance attribute exposed by ``proc_audio.AudioProcessor``
#                  after ``apply_filters_and_generate_data``. The mapping is
#                  ``canonical_name -> proc_audio_attribute_name`` (the only
#                  alias is ``spectral_entropy``, sourced from the legacy
#                  attribute ``entropy_spectral_value``).
#   * DERIVED    — canonical metric not exposed by proc_audio directly. The
#                  validation script computes it from intermediate state
#                  (``harmonic_list_df``, ``calculate_fundamental_frequency``,
#                  ``harmonic_energy_sum``/``inharmonic_energy_sum``) or as a
#                  corpus-wide post-processing step (``density_normalized_global``).
#   * IDENTIFIER — non-numeric canonical metric populated from the manifest
#                  by ``build_canonical_dataframe``. These are explicitly
#                  excluded from canonical statistics and from PCA by
#                  ``metrics_dictionary.json`` (``quantity_type="metadata"``).
# ---------------------------------------------------------------------------
PROC_AUDIO_DIRECT_ATTRS: Dict[str, str] = {
    # canonical_name             -> AudioProcessor attribute name
    "component_harmonic_energy_ratio":           "component_harmonic_energy_ratio",
    "component_inharmonic_energy_ratio":         "component_inharmonic_energy_ratio",
    "component_subbass_energy_ratio":            "component_subbass_energy_ratio",
    "component_total_inharmonic_energy_ratio":   "component_total_inharmonic_energy_ratio",
    "model_harmonic_weight":                     "model_harmonic_weight",
    "model_inharmonic_weight":                   "model_inharmonic_weight",
    "effective_partial_count":                   "effective_partial_count",
    "effective_partial_density":                 "effective_partial_density",
    "canonical_density_v5_adapted":              "canonical_density_v5_adapted",
    # AUDIT FIX (single-pass weighted density) — density_metric_normalized
    # was previously a per-file alias of density_normalized_global; after
    # the refactor it is a compile-time diagnostic descriptor (max-norm of
    # the weighted partial-sum density_metric_raw, lives on Density_Metrics)
    # and is no longer a proc_audio attribute.
    "density_per_component":                     "density_per_component",
    "spectral_entropy":                          "entropy_spectral_value",
    # f0 + low-frequency / subfundamental guard (proc_audio main_metrics; same attr names)
    "f0_final_hz":                               "f0_final",
    "adaptive_subfundamental_cutoff_hz":         "adaptive_subfundamental_cutoff_hz",
    "subfundamental_margin_percent":             "subfundamental_margin_percent",
    "percentage_subfundamental_cutoff_hz":       "percentage_subfundamental_cutoff_hz",
    "leakage_guard_cutoff_hz":                   "leakage_guard_cutoff_hz",
    "effective_subfundamental_margin_percent":   "effective_subfundamental_margin_percent",
    "subfundamental_guard_valid":                "subfundamental_guard_valid",
    "subfundamental_guard_policy":               "subfundamental_guard_policy",
    "low_frequency_policy_version":              "low_frequency_policy_version",
    "physical_low_frequency_lower_hz":           "physical_low_frequency_lower_hz",
    "physical_low_frequency_upper_hz":           "physical_low_frequency_upper_hz",
    "subfundamental_cutoff_selection_rule":      "subfundamental_cutoff_selection_rule",
    "subfundamental_cutoff_selected_by":         "subfundamental_cutoff_selected_by",
}

# Canonical metrics computed by the validation script from intermediate
# proc_audio state. Per-file derivations live in ``analyze_audio_file``;
# corpus-wide derivations live in ``build_canonical_dataframe``.
DERIVED_CANONICAL_METRICS: Tuple[str, ...] = (
    "harmonic_completeness",                # per-file: unique harmonic orders / expected
    "harmonic_inharmonic_ratio",            # per-file: H / max(I, eps)
    "harmonic_effective_power_density",     # per-file: density.compute_harmonic_effective_power_density
    "rolloff_compensated_harmonic_density", # per-file: density.compute_rolloff_compensated_harmonic_density
    "density_normalized_global",            # corpus-wide: max-normalised canonical_density_v5_adapted
    "canonical_density",                    # publication export alias (same scalar as canonical_density_v5_adapted)
    # low-frequency policy — not stored as named proc attrs; echo low_frequency_policy + proc geometry
    "min_floor_hz",
    "max_fraction_of_f0",
    "adaptive_subfundamental_cutoff_source",
)

# Canonical metrics with ``quantity_type="metadata"``. Sourced from the
# manifest by ``build_canonical_dataframe``; never measured.
IDENTIFIER_CANONICAL_METRICS: Tuple[str, ...] = (
    "Note",
    "source_file_name",
    "tier",
)

# Legacy alias kept for tests that already used the constant.
_CANONICAL_PROC_ATTRS: Tuple[str, ...] = tuple(PROC_AUDIO_DIRECT_ATTRS.keys())

# ---- Metric status sidecar values --------------------------------------------------
# Every canonical metric ``M`` may be accompanied by a column ``M__status``
# whose value belongs to this enum. The contract is intentionally explicit so
# that consumers cannot silently confuse "absent because disabled" with
# "absent because the formula returned zero".
STATUS_COMPUTED = "computed"
STATUS_DISABLED_BY_PARAMETERS = "disabled_by_parameters"
STATUS_UNAVAILABLE = "unavailable"
STATUS_MISSING_INPUT = "missing_input"
STATUS_VALUES: Tuple[str, ...] = (
    STATUS_COMPUTED, STATUS_DISABLED_BY_PARAMETERS,
    STATUS_UNAVAILABLE, STATUS_MISSING_INPUT,
)

# ---- Canonical metrics that depend on expensive psychoacoustic models --------------
# When ``AnalysisParameters.dissonance_enabled`` is False (default), every
# canonical metric in this set MUST be exported with value=NaN and
# status=disabled_by_parameters. Empty today (the canonical set has been
# audited against the dictionary); kept as a forward-compatible hook so the
# enforcement test fails loudly the moment a dissonance-dependent metric is
# promoted to canonical.
DISSONANCE_DEPENDENT_CANONICAL_METRICS: Tuple[str, ...] = ()


def analyze_audio_file(
    wav_path: Path,
    *,
    note: str,
    params: AnalysisParameters,
    work_dir: Path,
) -> Dict[str, Any]:
    """Run the canonical single-pass pipeline on one WAV.

    Returns a ``{metric → value}`` dict containing both canonical metrics
    (named per ``metrics_dictionary.json``) and a minimum set of diagnostic
    fields used downstream (``harmonic_energy_sum``, ``component_energy_*``).

    The function imports ``proc_audio`` lazily so the script can still be
    parsed in environments without numba/librosa.
    """
    from proc_audio import AudioProcessor

    work_dir.mkdir(parents=True, exist_ok=True)
    proc = AudioProcessor()
    proc.note = str(note or "A4")
    proc.load_audio_files([str(wav_path)])
    proc.apply_filters_and_generate_data(
        freq_min=params.freq_min,
        freq_max=params.freq_max,
        db_min=params.db_min,
        db_max=params.db_max,
        window=params.window,
        n_fft=params.n_fft,
        hop_length=params.hop_length,
        tolerance=params.tolerance,
        use_adaptive_tolerance=params.use_adaptive_tolerance,
        results_directory=str(work_dir),
        dissonance_enabled=params.dissonance_enabled,
        dissonance_curve=False,
        dissonance_scale=False,
        compare_models=False,
        harmonic_weight=0.5,
        inharmonic_weight=0.5,
        auto_model_weights_from_analysis=params.auto_model_weights_from_analysis,
        weight_function=params.weight_function,
        zero_padding=params.zero_padding,
        time_avg=params.time_avg,
        spectral_masking_enabled=params.spectral_masking_enabled,
        tier=params.tier,
    )

    out: Dict[str, Any] = {}

    # ---- (A) DIRECT canonical metrics (proc_audio instance attributes) -----
    for canon_name, proc_attr in PROC_AUDIO_DIRECT_ATTRS.items():
        raw = getattr(proc, proc_attr, None)
        if isinstance(raw, str):
            s = str(raw).strip()
            out[canon_name] = s if s else None
            out[f"{canon_name}__status"] = (
                STATUS_COMPUTED if s else STATUS_UNAVAILABLE
            )
        else:
            value = _to_float_or_none(raw)
            out[canon_name] = value
            out[f"{canon_name}__status"] = (
                STATUS_COMPUTED if value is not None else STATUS_UNAVAILABLE
            )

    # ---- (B) DERIVED canonical metrics (computed from proc_audio state) ----
    # 1. harmonic_inharmonic_ratio — H / max(I, eps); eps protects against div by 0.
    H = _to_float_or_none(getattr(proc, "harmonic_energy_sum", None))
    I = _to_float_or_none(getattr(proc, "inharmonic_energy_sum", None))
    if H is None or I is None:
        out["harmonic_inharmonic_ratio"] = None
        out["harmonic_inharmonic_ratio__status"] = STATUS_MISSING_INPUT
    else:
        eps = 1e-12
        out["harmonic_inharmonic_ratio"] = float(H / max(I, eps))
        out["harmonic_inharmonic_ratio__status"] = STATUS_COMPUTED

    # 2. harmonic_completeness — unique harmonic order count / expected count.
    harm_df = getattr(proc, "harmonic_list_df", None)
    f0 = _try_calculate_f0(proc, params)
    out["harmonic_completeness"], out["harmonic_completeness__status"] = (
        _compute_harmonic_completeness(harm_df, f0, params.freq_max)
    )

    # 3. harmonic_effective_power_density — additive normalized power.
    out["harmonic_effective_power_density"], out["harmonic_effective_power_density__status"] = (
        _compute_hep_density(harm_df, f0)
    )

    # 4. rolloff_compensated_harmonic_density — rolloff-compensated richness.
    out["rolloff_compensated_harmonic_density"], out["rolloff_compensated_harmonic_density__status"] = (
        _compute_rolloff_density(harm_df, f0, params.weight_function)
    )

    # 5. min_floor_hz, max_fraction_of_f0, adaptive_subfundamental_cutoff_source —
    #    compile_metrics can attach ``adaptive_subfundamental_cutoff_source`` at
    #    compile time; proc_audio does not expose it as an instance field. Echo
    #    low_frequency_policy.calculate_adaptive_subfundamental_cutoff_hz using
    #    the same freq_min / leakage pattern as proc_audio._finalize_low_frequency_policy_state.
    try:
        from subbass_policy import SubBassPolicy

        f0raw = getattr(proc, "f0_final", None)
        try:
            mf = float(getattr(proc, "freq_min", 20.0) or 20.0)
        except (TypeError, ValueError):
            mf = 20.0
        try:
            f0f = float(f0raw) if f0raw is not None else float("nan")
            sr = float(getattr(proc, "sr", None) or 44100.0)
            nff = int(getattr(proc, "n_fft", 0) or 0)
        except (TypeError, ValueError):
            f0f = float("nan")
            sr = 44100.0
            nff = 0
        _resolved = float(SubBassPolicy.upper_bound_hz(f0_hz=f0f, sr_hz=sr, n_fft=nff))
        mv = _to_float_or_none(mf)
        xv = _to_float_or_none(0.95)
        out["min_floor_hz"] = mv
        out["min_floor_hz__status"] = STATUS_COMPUTED if mv is not None else STATUS_UNAVAILABLE
        out["max_fraction_of_f0"] = xv
        out["max_fraction_of_f0__status"] = STATUS_COMPUTED if xv is not None else STATUS_UNAVAILABLE
        f0_ok = f0raw is not None and _to_float_or_none(f0raw) is not None
        ad = getattr(proc, "adaptive_subfundamental_cutoff_hz", None)
        ad_ok = (
            isinstance(ad, (int, float, np.floating, np.integer))
            and np.isfinite(float(ad))
        )
        if not f0_ok:
            out["adaptive_subfundamental_cutoff_source"] = "not_available_missing_f0"
            out["adaptive_subfundamental_cutoff_source__status"] = STATUS_UNAVAILABLE
        elif ad_ok:
            out["adaptive_subfundamental_cutoff_source"] = "per_note_analysis_export"
            out["adaptive_subfundamental_cutoff_source__status"] = STATUS_COMPUTED
        else:
            out["adaptive_subfundamental_cutoff_source"] = "derived_at_compile_stage_from_f0_final_hz"
            out["adaptive_subfundamental_cutoff_source__status"] = STATUS_COMPUTED
            out["adaptive_subfundamental_cutoff_hz"] = _resolved
    except Exception:
        out["min_floor_hz"] = None
        out["min_floor_hz__status"] = STATUS_UNAVAILABLE
        out["max_fraction_of_f0"] = None
        out["max_fraction_of_f0__status"] = STATUS_UNAVAILABLE
        out["adaptive_subfundamental_cutoff_source"] = None
        out["adaptive_subfundamental_cutoff_source__status"] = STATUS_UNAVAILABLE

    # 6. density_normalized_global is corpus-wide → filled by build_canonical_dataframe.

    # ---- (C) Enforce dissonance-disabled policy --------------------------
    # Every dissonance-dependent canonical metric (currently empty) must be
    # marked disabled_by_parameters when dissonance is off, *not* silently
    # filled with zero by the analyser. We overwrite any value the helpers
    # may have produced to make the contract bullet-proof.
    if not params.dissonance_enabled:
        for m in DISSONANCE_DEPENDENT_CANONICAL_METRICS:
            out[m] = None
            out[f"{m}__status"] = STATUS_DISABLED_BY_PARAMETERS

    # ---- (D) Diagnostic / provenance fields (not canonical, but useful)
    for prov_attr in (
        "harmonic_energy_sum",
        "inharmonic_energy_sum",
        "subbass_energy_sum",
        "total_component_energy",
        "component_energy_denominator",
        "component_energy_method",
        "component_profile_source",
        "component_energy_quantity",
        "model_weight_denominator",
    ):
        v = getattr(proc, prov_attr, None)
        if isinstance(v, (int, float, np.floating, np.integer)):
            out[prov_attr] = float(v)
        else:
            out[prov_attr] = v
    return out


# ---------------------------------------------------------------------------
# Per-file derivation helpers (live here so tests can drive them in isolation).
# ---------------------------------------------------------------------------
def _try_calculate_f0(proc, params: "AnalysisParameters") -> Optional[float]:
    """Resolve f0 from ``proc.note`` via the analyser's helper."""
    try:
        if hasattr(proc, "calculate_fundamental_frequency") and getattr(proc, "note", None):
            v = proc.calculate_fundamental_frequency(str(proc.note))
            v = float(v) if v else 0.0
            if v > 0 and np.isfinite(v):
                return v
    except Exception:
        return None
    return None


def _compute_harmonic_completeness(
    harm_df,
    f0: Optional[float],
    freq_max: float,
) -> Tuple[Optional[float], str]:
    """``unique_orders / max(1, int(min(freq_max, 20000)/f0))`` clipped to [0, 1]."""
    if harm_df is None or not isinstance(harm_df, pd.DataFrame) or harm_df.empty:
        return None, STATUS_MISSING_INPUT
    if "Harmonic Number" not in harm_df.columns:
        return None, STATUS_MISSING_INPUT
    if f0 is None or not (np.isfinite(f0) and f0 > 0):
        return None, STATUS_MISSING_INPUT
    try:
        f_top = min(float(freq_max), 20000.0) if freq_max > 0 else 20000.0
        n_unique = int(pd.to_numeric(harm_df["Harmonic Number"], errors="coerce").dropna().nunique())
        max_expected = max(1, int(f_top / float(f0)))
        return float(min(1.0, n_unique / max_expected)), STATUS_COMPUTED
    except Exception:
        return None, STATUS_UNAVAILABLE


def _compute_hep_density(harm_df, f0: Optional[float]) -> Tuple[Optional[float], str]:
    """Wrap ``density.compute_harmonic_effective_power_density`` with status mapping."""
    if harm_df is None or not isinstance(harm_df, pd.DataFrame) or harm_df.empty:
        return None, STATUS_MISSING_INPUT
    try:
        from density import compute_harmonic_effective_power_density
        res = compute_harmonic_effective_power_density(
            harmonic_df=harm_df, fundamental_freq_hz=f0
        )
        v = _to_float_or_none(res.get("harmonic_effective_power_density"))
        status_raw = str(res.get("harmonic_effective_power_density_status") or "")
        if v is None:
            # density.py returns "skipped_*" for missing inputs / degenerate.
            return None, (STATUS_MISSING_INPUT if status_raw.startswith("skipped") else STATUS_UNAVAILABLE)
        return v, STATUS_COMPUTED
    except Exception:
        return None, STATUS_UNAVAILABLE


def _compute_rolloff_density(
    harm_df,
    f0: Optional[float],
    weight_function: str,
) -> Tuple[Optional[float], str]:
    """Wrap ``density.compute_rolloff_compensated_harmonic_density`` with status mapping."""
    if harm_df is None or not isinstance(harm_df, pd.DataFrame) or harm_df.empty:
        return None, STATUS_MISSING_INPUT
    if "Frequency (Hz)" not in harm_df.columns or "Amplitude" not in harm_df.columns:
        return None, STATUS_MISSING_INPUT
    if f0 is None or not (np.isfinite(f0) and f0 > 0):
        return None, STATUS_MISSING_INPUT
    try:
        from density import compute_rolloff_compensated_harmonic_density
        amps = pd.to_numeric(harm_df["Amplitude"], errors="coerce").to_numpy(dtype=float)
        freqs = pd.to_numeric(harm_df["Frequency (Hz)"], errors="coerce").to_numpy(dtype=float)
        orders = None
        if "Harmonic Number" in harm_df.columns:
            orders = pd.to_numeric(harm_df["Harmonic Number"], errors="coerce").to_numpy(dtype=float)
        res = compute_rolloff_compensated_harmonic_density(
            amplitudes=amps,
            frequencies_hz=freqs,
            fundamental_freq_hz=float(f0),
            harmonic_orders=orders,
            weight_function=str(weight_function or "linear"),
        )
        v = _to_float_or_none(res.get("rolloff_compensated_harmonic_density"))
        status_raw = str(res.get("rolloff_compensated_harmonic_density_status") or "")
        if v is None:
            return None, (STATUS_MISSING_INPUT if status_raw.startswith("skipped") else STATUS_UNAVAILABLE)
        return v, STATUS_COMPUTED
    except Exception:
        return None, STATUS_UNAVAILABLE


def _to_float_or_none(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float, np.floating, np.integer)):
        if np.isfinite(float(v)):
            return float(v)
        return None
    try:
        f = float(v)
        return f if np.isfinite(f) else None
    except Exception:
        return None


# Type alias for the dependency-injected analyser. Tests substitute this with
# a stub so the suite does not have to run proc_audio for every WAV.
AnalyseFn = Callable[[Path, str, AnalysisParameters, Path], Dict[str, Any]]


# ---------------------------------------------------------------------------
# Build the canonical DataFrame
# ---------------------------------------------------------------------------
def build_canonical_dataframe(
    entries: List[CorpusEntry],
    analysis_results: List[Dict[str, Any]],
) -> pd.DataFrame:
    """Merge manifest metadata + canonical metric dicts into a wide DataFrame.

    Layout contract:
      - one row per (entry, analysis) pair;
      - the 3 ``IDENTIFIER_CANONICAL_METRICS`` (``Note``, ``source_file_name``,
        ``tier``) are populated from manifest fields;
      - every canonical metric in ``metrics_dictionary.json`` is guaranteed
        to appear as a column. Missing values surface as ``NaN`` together
        with a sidecar ``<metric>__status`` column whose value is one of
        ``STATUS_VALUES``;
      - the corpus-wide ``density_normalized_global`` is computed in this
        function (max-normalisation of ``canonical_density_v5_adapted``).
    """
    if len(entries) != len(analysis_results):
        raise ValueError(
            f"entries and analysis_results length mismatch: "
            f"{len(entries)} vs {len(analysis_results)}"
        )
    rows: List[Dict[str, Any]] = []
    for e, m in zip(entries, analysis_results):
        row: Dict[str, Any] = {
            # Canonical identifier columns (per metrics_dictionary.json).
            "Note": e.sounding_pitch or e.written_pitch or "",
            "source_file_name": e.file_path,
            "tier": "Tier_corpus_validation",
            # Manifest metadata (free-form fields, not canonical metrics).
            "instrument": e.instrument,
            "instrument_family": e.instrument_family,
            "technique": e.technique,
            "written_pitch": e.written_pitch,
            "sounding_pitch": e.sounding_pitch,
            "dynamic": e.dynamic,
            "register": e.register,
            "source": e.source,
            "notes": e.notes,
        }
        for k, v in (m or {}).items():
            row[k] = v
        rows.append(row)
    df = pd.DataFrame(rows)

    # ----- corpus-wide derived canonical metric -----
    df = _attach_density_normalized_global(df)

    # ----- ensure every canonical metric column exists (NaN + status) -----
    df = _ensure_canonical_columns(df)

    return df


def _attach_density_normalized_global(df: pd.DataFrame) -> pd.DataFrame:
    """Compute ``density_normalized_global`` corpus-wide (max-normalisation)
    of ``canonical_density_v5_adapted``. Mirrors compile_metrics.py:803–808.
    """
    if "canonical_density_v5_adapted" not in df.columns:
        df["density_normalized_global"] = np.nan
        df["density_normalized_global__status"] = STATUS_MISSING_INPUT
        return df
    s = pd.to_numeric(df["canonical_density_v5_adapted"], errors="coerce")
    finite = s.replace([np.inf, -np.inf], np.nan).dropna()
    if finite.empty:
        df["density_normalized_global"] = np.nan
        df["density_normalized_global__status"] = STATUS_MISSING_INPUT
        return df
    mx = float(finite.max())
    if not np.isfinite(mx) or mx <= 0:
        df["density_normalized_global"] = np.nan
        df["density_normalized_global__status"] = STATUS_UNAVAILABLE
        return df
    df["density_normalized_global"] = s.divide(mx).clip(lower=0.0, upper=1.0)
    df["density_normalized_global__status"] = np.where(
        s.notna(), STATUS_COMPUTED, STATUS_MISSING_INPUT
    )
    return df


def _ensure_canonical_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee every canonical metric (direct + derived + identifier) appears
    as a column, with a status sidecar for measured metrics.

    The contract is loaded directly from ``metrics_dictionary.json`` so it
    cannot drift from the dictionary.
    """
    try:
        from validate_canonical_metrics import MetricDictionary
        dictionary_path = REPO_ROOT / "metrics_dictionary.json"
        if dictionary_path.is_file():
            md = MetricDictionary.load(dictionary_path)
            canonical_all = md.canonical_names()
        else:
            canonical_all = list(IDENTIFIER_CANONICAL_METRICS) + list(
                PROC_AUDIO_DIRECT_ATTRS.keys()
            ) + list(DERIVED_CANONICAL_METRICS)
    except Exception:
        canonical_all = list(IDENTIFIER_CANONICAL_METRICS) + list(
            PROC_AUDIO_DIRECT_ATTRS.keys()
        ) + list(DERIVED_CANONICAL_METRICS)

    measured = set(PROC_AUDIO_DIRECT_ATTRS.keys()) | set(DERIVED_CANONICAL_METRICS)
    identifiers = set(IDENTIFIER_CANONICAL_METRICS)

    for name in canonical_all:
        if name not in df.columns:
            df[name] = np.nan if name not in identifiers else ""
        if name in measured and f"{name}__status" not in df.columns:
            # No analyser ever wrote a value or status for this metric. Mark
            # it as unavailable rather than silently NaN.
            df[f"{name}__status"] = STATUS_UNAVAILABLE
    return df


# ---------------------------------------------------------------------------
# Canonical workbook writer
# ---------------------------------------------------------------------------
def write_canonical_workbook(
    df: pd.DataFrame,
    out_path: Path,
    *,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Path:
    """Write a minimal compiled-style workbook with a Canonical_Metrics sheet.

    Mirrors the contract of ``compile_metrics.py`` (the
    ``validate_canonical_metrics.load_canonical_metrics_from_workbook``
    function depends only on the presence of a ``Canonical_Metrics`` sheet).
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Canonical_Metrics", index=False)
        meta = {
            "analysis_date": _dt.datetime.now().isoformat(),
            "row_count": int(len(df)),
        }
        if extra_metadata:
            meta.update({str(k): v for k, v in extra_metadata.items()})
        pd.DataFrame(
            {"Parameter": list(meta.keys()), "Value": [str(v) for v in meta.values()]}
        ).to_excel(writer, sheet_name="Analysis_Metadata", index=False)
    return out_path


# ---------------------------------------------------------------------------
# Coverage / dictionary integrity guards
# ---------------------------------------------------------------------------
def check_metrics_dictionary_compatibility(dictionary_path: Path) -> List[str]:
    """Verify the dictionary file is readable and exposes the expected schema."""
    warns: List[str] = []
    if not dictionary_path.is_file():
        warns.append(
            f"DICTIONARY-MISSING: metrics_dictionary.json not found at {dictionary_path}"
        )
        return warns
    try:
        with dictionary_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        warns.append(f"DICTIONARY-PARSE-ERROR: {dictionary_path}: {exc}")
        return warns
    if "metrics" not in data:
        warns.append("DICTIONARY-SCHEMA: missing top-level 'metrics' list.")
    if "schema_version" not in data:
        warns.append("DICTIONARY-SCHEMA: missing 'schema_version'.")
    if "metric_family_enum" not in data:
        warns.append("DICTIONARY-SCHEMA: missing 'metric_family_enum' (>= v1.1).")
    return warns


def check_canonical_coverage_against_threshold(
    coverage_df: pd.DataFrame,
    *,
    threshold: float,
) -> List[str]:
    """For every canonical metric below ``threshold``, emit a warning."""
    warns: List[str] = []
    if coverage_df is None or coverage_df.empty:
        return warns
    for _, row in coverage_df.iterrows():
        cov = float(row.get("coverage_fraction", 0.0) or 0.0)
        present = bool(row.get("present_in_workbook", False))
        if not present:
            warns.append(
                f"COVERAGE: canonical metric not present: {row['metric']}"
            )
        elif cov < float(threshold):
            warns.append(
                f"COVERAGE: canonical metric '{row['metric']}' covers "
                f"{cov:.0%} of rows (< threshold {threshold:.0%})."
            )
    return warns


# ---------------------------------------------------------------------------
# Physical-acoustic validation notes (constrained vocabulary)
# ---------------------------------------------------------------------------
# Wording allowed in the auto-generated notes. Any candidate sentence that
# slips through the helpers below MUST consist of these descriptors only.
_ALLOWED_PHRASES: Tuple[str, ...] = (
    "higher measured",
    "lower measured",
    "near-constant descriptor",
    "empirical redundancy",
    "above threshold",
    "below threshold",
    "spectral dispersion",
    "energy ratio",
    "energy fraction",
    "pearson_r",
    "measured median",
    "measured mean",
    "measured ordering",
    "not a perceptual",
    "not a musicological",
)

# Wording explicitly forbidden. The tests assert these literals are absent.
_FORBIDDEN_PHRASES: Tuple[str, ...] = (
    "orchestration function",
    "perceptual tension",
    "expressive intensity",
    "timbral salience",
    "musical density perception",
)


def make_physical_acoustic_validation_notes(
    df: pd.DataFrame,
    report,  # validate_canonical_metrics.ValidationReport
    *,
    group_by: Optional[List[str]] = None,
    max_pairs_to_list: int = 10,
    max_ranked_combos: int = 20,
) -> List[str]:
    """Produce a list of physical-acoustic statements.

    Every line is restricted to the allowed vocabulary above. The output is
    consumed both by the Markdown report (rendered as bullets) and by the
    Excel report (rendered as a single-column sheet ``Physical_Acoustic_Notes``).
    """
    notes: List[str] = []

    # ---- 1. near-constant descriptors
    for _, row in report.near_constant.iterrows():
        std_val = row.get("std", float("nan"))
        try:
            std_txt = f"{float(std_val):.3e}"
        except Exception:
            std_txt = "n/a"
        notes.append(
            f"`{row['metric']}` is a near-constant descriptor in this corpus "
            f"(std = {std_txt})."
        )

    # ---- 2. empirical redundancies (above threshold, not algebraically declared)
    thr = float(report.settings.get("correlation_threshold", 0.90))
    if not report.high_correlations.empty:
        emp = report.high_correlations[
            report.high_correlations["redundancy_type"] == "empirical"
        ]
        if not emp.empty:
            notes.append(
                f"Empirical redundancy above threshold (|r| ≥ {thr:.2f}): "
                f"{len(emp)} canonical pair(s) co-vary in this corpus without "
                "being declared algebraically related in metrics_dictionary.json."
            )
            for _, r in emp.head(max_pairs_to_list).iterrows():
                notes.append(
                    f"- `{r['metric_a']}` ↔ `{r['metric_b']}`: "
                    f"pearson_r = {float(r['pearson_r']):+.3f}."
                )

    # ---- 3. group-level orderings (measured-only language, numeric evidence)
    if group_by:
        present_g = [g for g in group_by if g in df.columns]
        # Rankable canonical metrics: every numeric canonical metric the
        # corpus actually carries that is not near-constant.
        canonical_measured = set(PROC_AUDIO_DIRECT_ATTRS.keys()) | set(
            DERIVED_CANONICAL_METRICS
        )
        canonical_in_df = [
            c for c in df.columns
            if c in canonical_measured
        ]
        near_const_metrics = (
            set(report.near_constant["metric"].tolist())
            if not report.near_constant.empty
            else set()
        )
        rankable = [m for m in canonical_in_df if m not in near_const_metrics]
        emitted = 0
        for g in present_g:
            for metric in rankable:
                if emitted >= max_ranked_combos:
                    break
                s = pd.to_numeric(df[metric], errors="coerce")
                if s.notna().sum() < 2:
                    continue
                gb = df.assign(_v=s).groupby(g, dropna=False)["_v"]
                stats = gb.agg(["mean", "median", "count"]).dropna(subset=["mean"])
                if stats.shape[0] < 2:
                    continue
                stats = stats.sort_values("mean", ascending=False)
                top_label = stats.index[0]
                bot_label = stats.index[-1]
                top_mean = float(stats.iloc[0]["mean"])
                bot_mean = float(stats.iloc[-1]["mean"])
                top_median = float(stats.iloc[0]["median"])
                bot_median = float(stats.iloc[-1]["median"])
                delta = top_mean - bot_mean
                if abs(delta) < 1e-12:
                    continue
                ratio_txt = ""
                if bot_mean != 0 and np.isfinite(bot_mean) and bot_mean > 0:
                    ratio = top_mean / bot_mean
                    if np.isfinite(ratio):
                        ratio_txt = f"; ratio = {ratio:.3f}"
                notes.append(
                    "Grouped by `" + g + "`: `" + str(top_label) +
                    "` shows the higher measured `" + metric +
                    f"` (mean = {top_mean:.4f}, median = {top_median:.4f}, "
                    f"n = {int(stats.iloc[0]['count'])}); `" + str(bot_label) +
                    "` shows the lower measured value (mean = "
                    f"{bot_mean:.4f}, median = {bot_median:.4f}, "
                    f"n = {int(stats.iloc[-1]['count'])}); "
                    f"Δ_mean = {delta:+.4f}" + ratio_txt +
                    f"; group_field = `{g}`; metric = `{metric}`. "
                    "This is a measured ordering, not a perceptual or "
                    "musicological claim."
                )
                emitted += 1

    # ---- 4. defence-in-depth: scrub any forbidden phrase
    cleaned: List[str] = []
    for n in notes:
        if _contains_forbidden_phrase(n):
            # The helper should never produce such a line; if it does, drop
            # it so the report cannot leak unsupported musicological claims.
            logger.warning("Dropped a note containing a forbidden phrase: %s", n)
            continue
        cleaned.append(n)
    return cleaned


def _contains_forbidden_phrase(text: str) -> bool:
    low = (text or "").lower()
    return any(p in low for p in _FORBIDDEN_PHRASES)


# ---------------------------------------------------------------------------
# Run manifest (provenance)
# ---------------------------------------------------------------------------
def _get_software_version() -> Tuple[str, str]:
    """Return (version, source) from pyproject.toml when available."""
    pyproj = REPO_ROOT / "pyproject.toml"
    if pyproj.is_file():
        try:
            txt = pyproj.read_text(encoding="utf-8")
            for line in txt.splitlines():
                line_s = line.strip()
                if line_s.startswith("version") and "=" in line_s:
                    val = line_s.split("=", 1)[1].strip().strip('"').strip("'")
                    return val, "pyproject.toml"
        except Exception:
            pass
    return "unknown", "fallback"


def write_run_manifest(
    out_path: Path,
    *,
    manifest_path: Path,
    entries: List[CorpusEntry],
    analysis_params: AnalysisParameters,
    validation_settings: Dict[str, Any],
    warnings: List[str],
    report_paths: Dict[str, str],
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    version, version_source = _get_software_version()
    payload = {
        "schema_version": "1.0.0",
        "run_timestamp": _dt.datetime.now().isoformat(),
        "software_version": version,
        "software_version_source": version_source,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "manifest_path": str(manifest_path),
        "manifest_entry_count": len(entries),
        "analysis_parameters": dataclasses.asdict(analysis_params),
        "validation_settings": {
            str(k): (str(v) if isinstance(v, Path) else v)
            for k, v in (validation_settings or {}).items()
        },
        "report_paths": report_paths,
        "warnings": warnings,
        "files": [e.asdict() for e in entries],
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------
@dataclass
class CorpusRunResult:
    """Paths to every artefact produced by a corpus validation run."""

    compiled_workbook: Path
    validation_report_xlsx: Path
    validation_report_md: Optional[Path]
    run_manifest_json: Path
    warnings: List[str] = field(default_factory=list)


def run_real_corpus_validation(
    manifest_path: Path,
    *,
    output_dir: Path,
    dictionary_path: Path,
    analysis_params: Optional[AnalysisParameters] = None,
    group_by: Optional[List[str]] = None,
    coverage_threshold: float = 0.80,
    correlation_threshold: float = 0.90,
    allow_missing_files: bool = False,
    write_markdown: bool = True,
    analyse_fn: Optional[AnalyseFn] = None,
) -> CorpusRunResult:
    """End-to-end real-corpus validation. Returns paths + warnings.

    Parameters
    ----------
    manifest_path : Path
        CSV or JSON manifest.
    output_dir : Path
        Directory where compiled workbook + reports + run manifest go.
    dictionary_path : Path
        Path to ``metrics_dictionary.json``.
    analysis_params : AnalysisParameters
        Forwarded to ``proc_audio``. Defaults are honest-but-fast.
    group_by : list[str]
        Manifest columns to group by in descriptive stats / notes (e.g.
        ``["instrument", "instrument_family"]``).
    coverage_threshold : float
        Minimum acceptable per-metric coverage (0..1). Lower values emit
        warnings.
    correlation_threshold : float
        |r| threshold for the redundancy section.
    allow_missing_files : bool
        If True, missing audio files are warned (not raised). If False, a
        missing file aborts the run with ``FileNotFoundError``.
    write_markdown : bool
        Emit ``validation_report.md`` next to the Excel report.
    analyse_fn : callable, optional
        Dependency-injected analyser. The default uses ``proc_audio``.
        Tests pass a stub that returns canonical metric dicts directly.

    Returns
    -------
    CorpusRunResult
        Paths to every artefact + accumulated warnings.
    """
    from validate_canonical_metrics import (
        MetricDictionary,
        validate_corpus,
        write_report_excel,
        write_report_markdown,
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(manifest_path)
    dictionary_path = Path(dictionary_path)
    analyse = analyse_fn or analyze_audio_file
    params = analysis_params or AnalysisParameters()

    warns: List[str] = []

    # ---- dictionary integrity
    warns.extend(check_metrics_dictionary_compatibility(dictionary_path))
    if any(w.startswith("DICTIONARY-MISSING") for w in warns):
        raise FileNotFoundError(
            f"metrics_dictionary.json missing at {dictionary_path}. "
            "Cannot validate canonical metrics without the dictionary."
        )

    dictionary = MetricDictionary.load(dictionary_path)

    # ---- manifest
    entries = load_corpus_manifest(manifest_path)
    manifest_dir = manifest_path.parent.resolve()
    manifest_warns = validate_manifest_entries(
        entries, manifest_dir=manifest_dir, allow_missing_files=allow_missing_files
    )
    warns.extend(manifest_warns)
    if not allow_missing_files:
        for w in manifest_warns:
            if w.startswith("MANIFEST-ERROR"):
                raise FileNotFoundError(w)

    # ---- per-file analysis
    work_dir = output_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    analysis_results: List[Dict[str, Any]] = []
    surviving_entries: List[CorpusEntry] = []
    for entry in entries:
        path = Path(entry.file_path)
        if not path.is_absolute():
            path = (manifest_dir / path).resolve()
        if not path.is_file():
            # already warned; skip the analyse step
            continue
        try:
            metrics = analyse(path, entry.sounding_pitch or entry.written_pitch or "A4", params, work_dir)
        except Exception as exc:
            warns.append(f"ANALYSE-ERROR: {entry.file_path}: {exc}")
            continue
        analysis_results.append(metrics)
        surviving_entries.append(entry)

    if not analysis_results:
        warns.append("ANALYSE: no audio file could be analysed; aborting.")
        raise RuntimeError(
            "No audio file in the manifest could be analysed. "
            "Check the manifest paths or pass --allow-missing-files."
        )

    # ---- merge into canonical DataFrame and persist
    df = build_canonical_dataframe(surviving_entries, analysis_results)
    compiled_path = output_dir / "compiled_canonical.xlsx"
    write_canonical_workbook(
        df,
        compiled_path,
        extra_metadata={
            "n_entries_manifest": len(entries),
            "n_entries_analysed": len(surviving_entries),
            "analysis_n_fft": params.n_fft,
            "analysis_hop_length": params.hop_length,
            "analysis_window": params.window,
        },
    )

    # ---- validate
    report = validate_corpus(
        df,
        dictionary,
        group_by=group_by,
        correlation_threshold=correlation_threshold,
    )
    warns.extend(report.warnings)
    warns.extend(
        check_canonical_coverage_against_threshold(
            report.canonical_coverage, threshold=coverage_threshold
        )
    )

    # ---- physical-acoustic validation notes
    notes = make_physical_acoustic_validation_notes(
        df, report, group_by=group_by
    )

    # ---- write reports
    report_xlsx = output_dir / "validation_report.xlsx"
    write_report_excel(report_xlsx, report)
    _append_physical_notes_to_excel(report_xlsx, notes)

    report_md: Optional[Path] = None
    if write_markdown:
        report_md = output_dir / "validation_report.md"
        write_report_markdown(report_md, report)
        _append_physical_notes_to_markdown(report_md, notes)

    # ---- run manifest
    run_manifest_path = output_dir / "run_manifest.json"
    write_run_manifest(
        run_manifest_path,
        manifest_path=manifest_path,
        entries=surviving_entries,
        analysis_params=params,
        validation_settings={
            "dictionary_path": str(dictionary_path),
            "group_by": list(group_by or []),
            "coverage_threshold": coverage_threshold,
            "correlation_threshold": correlation_threshold,
            "allow_missing_files": allow_missing_files,
        },
        warnings=warns,
        report_paths={
            "compiled_workbook": str(compiled_path),
            "validation_report_xlsx": str(report_xlsx),
            "validation_report_md": str(report_md) if report_md else "",
        },
    )

    return CorpusRunResult(
        compiled_workbook=compiled_path,
        validation_report_xlsx=report_xlsx,
        validation_report_md=report_md,
        run_manifest_json=run_manifest_path,
        warnings=warns,
    )


# ---------------------------------------------------------------------------
# Report-side helpers (append physical-acoustic notes to the existing reports)
# ---------------------------------------------------------------------------
def _append_physical_notes_to_excel(report_path: Path, notes: List[str]) -> None:
    """Append a ``Physical_Acoustic_Notes`` sheet to the validation workbook."""
    if not notes:
        return
    notes_df = pd.DataFrame({"note": notes})
    with pd.ExcelWriter(report_path, engine="openpyxl", mode="a") as writer:
        notes_df.to_excel(writer, sheet_name="Physical_Acoustic_Notes", index=False)


def _append_physical_notes_to_markdown(report_path: Path, notes: List[str]) -> None:
    """Append the Markdown section ``Physical-acoustic validation notes``."""
    section = ["", "## Physical-acoustic validation notes", ""]
    section.append(
        "These notes describe **measured quantities only** — near-constant "
        "descriptors, empirical correlations above threshold, and "
        "group-level orderings of canonical metrics. They do not infer "
        "perceptual, cognitive, expressive, or musicological qualities. "
        "Any such inference would require a separate, explicit perceptual "
        "or musicological validation layer, which is out of scope for this "
        "report."
    )
    section.append("")
    if not notes:
        section.append("_(no automatic notes were emitted for this corpus.)_")
    else:
        for n in notes:
            # All notes already start with a `-` when they are sub-bullets;
            # add a bullet prefix for the headline notes so the Markdown
            # renders consistently.
            if n.startswith("-"):
                section.append(n)
            else:
                section.append(f"- {n}")
    existing = report_path.read_text(encoding="utf-8")
    report_path.write_text(existing + "\n" + "\n".join(section) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_real_corpus_validation",
        description=(
            "Reproducible canonical-metric validation over a small "
            "controlled corpus of instrumental sounds. Reads a manifest "
            "(CSV/JSON), runs the single-pass analyser, compiles "
            "Canonical_Metrics, validates against metrics_dictionary.json, "
            "and emits Excel + Markdown reports + a run manifest. Performs "
            "no musicological inference."
        ),
    )
    p.add_argument("--manifest", type=Path, required=True,
                   help="Manifest CSV or JSON listing the corpus files.")
    p.add_argument("--output-dir", type=Path, required=True,
                   help="Directory where artefacts will be written.")
    p.add_argument("--dictionary", type=Path,
                   default=REPO_ROOT / "metrics_dictionary.json")
    p.add_argument("--group-by", action="append", default=None,
                   help="Manifest column for grouping (may be passed multiple times).")
    p.add_argument("--coverage-threshold", type=float, default=0.80,
                   help="Per-metric coverage threshold (0..1). Default 0.80.")
    p.add_argument("--correlation-threshold", type=float, default=0.90)
    p.add_argument("--allow-missing-files", action="store_true",
                   help="Warn instead of failing when a manifest entry is missing.")
    p.add_argument("--no-markdown", action="store_true")
    p.add_argument("-v", "--verbose", action="count", default=0)
    # Analysis tuning (passed through to proc_audio).
    p.add_argument("--n-fft", type=int, default=8192)
    p.add_argument("--hop-length", type=int, default=1024)
    p.add_argument("--window", type=str, default="blackmanharris")
    p.add_argument("--freq-min", type=float, default=50.0)
    p.add_argument("--freq-max", type=float, default=12000.0)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING - 10 * int(args.verbose),
        format="%(levelname)s %(name)s: %(message)s",
    )
    params = AnalysisParameters(
        n_fft=int(args.n_fft),
        hop_length=int(args.hop_length),
        window=str(args.window),
        freq_min=float(args.freq_min),
        freq_max=float(args.freq_max),
    )
    result = run_real_corpus_validation(
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        dictionary_path=args.dictionary,
        analysis_params=params,
        group_by=args.group_by,
        coverage_threshold=args.coverage_threshold,
        correlation_threshold=args.correlation_threshold,
        allow_missing_files=args.allow_missing_files,
        write_markdown=(not args.no_markdown),
    )
    print(f"Compiled workbook: {result.compiled_workbook}")
    print(f"Validation report (xlsx): {result.validation_report_xlsx}")
    if result.validation_report_md:
        print(f"Validation report (md): {result.validation_report_md}")
    print(f"Run manifest: {result.run_manifest_json}")
    if result.warnings:
        print(f"({len(result.warnings)} warning(s) — see {result.run_manifest_json})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
