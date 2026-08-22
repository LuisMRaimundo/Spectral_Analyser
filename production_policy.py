"""WP3 production policy: FFT defaults, segment pairing, eligibility, CI NaN.

This module is the single place that encodes the comparable-corpus contract:

* FFT default is ``fixed`` / 8192 / 1024. ``adaptive_tier`` stays behind an
  explicit flag and is never primary-comparable.
* Analysis consumes the sustain cut. A stable-sustain sibling is diagnostic
  only — never substituted for the primary EWSD.
* Missing sibling diagnostics are NaN (``nan_not_zero_v1``), never 0.0.
* A note is EWSD-primary-ineligible when independent frames < 8 or
  ``harmonic_validated_count <= 2``. Degenerate CIs are NaN, never 0.0.

ADSR_Segmenter is not imported or modified. Sibling discovery only reads
paths and optional JSON sidecars.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence, Union

import numpy as np

from analysis_policy import MISSING_METRIC_POLICY_VERSION
from constants import (
    DENSITY_WEIGHT_FUNCTION_DEFAULT,
    ELIGIBILITY_POLICY_VERSION,
    FFT_POLICY_DEFAULT,
    FIXED_HOP_LENGTH_DEFAULT,
    FIXED_N_FFT_DEFAULT,
    MIN_INDEPENDENT_FRAMES,
    SEGMENT_POLICY_DEFAULT,
    STABLE_CENTROID_MAX_RATIO,
    STABLE_REPRESENTATIVENESS_MAX_RATIO,
)

__all__ = [
    "AUDIO_SUFFIXES",
    "ELIGIBILITY_POLICY_VERSION",
    "FFT_POLICY_DEFAULT",
    "FIXED_HOP_LENGTH_DEFAULT",
    "FIXED_N_FFT_DEFAULT",
    "MIN_INDEPENDENT_FRAMES",
    "MISSING_METRIC_POLICY_VERSION",
    "SEGMENT_POLICY_DEFAULT",
    "STABLE_CENTROID_MAX_RATIO",
    "STABLE_REPRESENTATIVENESS_MAX_RATIO",
    "apply_degenerate_ci_nan",
    "build_analysis_parameter_profile_id",
    "classify_segment_role",
    "default_parameter_profile_id",
    "evaluate_eligibility",
    "evaluate_segment_diagnostics",
    "evaluate_stable_representativeness",
    "find_adsr_sidecar",
    "find_segment_sibling",
    "is_primary_comparable_profile",
    "missing_metric_nan",
    "mixed_profile_ids",
    "sanitize_ci_value",
]

AUDIO_SUFFIXES: tuple[str, ...] = (".wav", ".aif", ".aiff", ".flac", ".mp3", ".ogg")
_CI_KEYS: tuple[str, ...] = (
    "rel_uncertainty",
    "relative_uncertainty",
    "note_density_final_rel_uncertainty",
    "note_effective_component_density_rel_uncertainty",
    "EWSD_score_total_rel_uncertainty",
    "EWSD_score_acoustic_balanced_rel_uncertainty",
    "ewsd_score_total_rel_uncertainty",
    "ewsd_score_acoustic_balanced_rel_uncertainty",
    "ci_low",
    "ci_high",
    "note_density_final_ci_low",
    "note_density_final_ci_high",
    "note_effective_component_density_ci_low",
    "note_effective_component_density_ci_high",
    "EWSD_score_total_ci_low",
    "EWSD_score_total_ci_high",
    "EWSD_score_acoustic_balanced_ci_low",
    "EWSD_score_acoustic_balanced_ci_high",
    "EWSD_score_total_ci_low_bca",
    "EWSD_score_total_ci_high_bca",
    "EWSD_score_acoustic_balanced_ci_low_bca",
    "EWSD_score_acoustic_balanced_ci_high_bca",
    "ewsd_score_total_ci_low",
    "ewsd_score_total_ci_high",
    "ewsd_score_acoustic_balanced_ci_low",
    "ewsd_score_acoustic_balanced_ci_high",
)


def missing_metric_nan() -> float:
    """Canonical missing-metric token (never 0.0)."""
    return float("nan")


def _as_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out if np.isfinite(out) else float("nan")


def _fmt_profile_token(value: Any) -> str:
    if value is None:
        return "runtime_configured"
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "runtime_configured"}:
        return "runtime_configured"
    try:
        return f"{float(text):.1f}"
    except (TypeError, ValueError):
        return text


def is_primary_comparable_profile(
    weight_function: Any = DENSITY_WEIGHT_FUNCTION_DEFAULT,
    fft_policy: Any = FFT_POLICY_DEFAULT,
) -> bool:
    wf = str(weight_function or DENSITY_WEIGHT_FUNCTION_DEFAULT).strip().lower()
    pol = str(fft_policy or FFT_POLICY_DEFAULT).strip().lower()
    return wf == str(DENSITY_WEIGHT_FUNCTION_DEFAULT).strip().lower() and pol == "fixed"


def build_analysis_parameter_profile_id(
    weight_function: Any = DENSITY_WEIGHT_FUNCTION_DEFAULT,
    density_salience_threshold_db: Any = "runtime_configured",
    density_frequency_ceiling_hz: Any = "runtime_configured",
    fft_policy: Any = FFT_POLICY_DEFAULT,
    segment_policy: Any = SEGMENT_POLICY_DEFAULT,
    eligibility_policy: Any = ELIGIBILITY_POLICY_VERSION,
) -> str:
    wf = str(weight_function or DENSITY_WEIGHT_FUNCTION_DEFAULT).strip().lower()
    pol = str(fft_policy or FFT_POLICY_DEFAULT).strip().lower()
    if pol not in {"fixed", "adaptive_tier"}:
        pol = str(FFT_POLICY_DEFAULT)
    seg = str(segment_policy or SEGMENT_POLICY_DEFAULT).strip() or SEGMENT_POLICY_DEFAULT
    elig = str(eligibility_policy or ELIGIBILITY_POLICY_VERSION).strip() or ELIGIBILITY_POLICY_VERSION
    return (
        f"wf={wf}|dst={_fmt_profile_token(density_salience_threshold_db)}"
        f"|ceil={_fmt_profile_token(density_frequency_ceiling_hz)}"
        f"|fft={pol}|seg={seg}|elig={elig}"
    )


def default_parameter_profile_id(weight_function: Optional[str] = None) -> str:
    return build_analysis_parameter_profile_id(weight_function=weight_function)


def evaluate_eligibility(
    sustain_frame_count_independent: Any,
    harmonic_validated_count: Any,
    *,
    min_independent_frames: int = MIN_INDEPENDENT_FRAMES,
) -> dict[str, Any]:
    frames = _as_float(sustain_frame_count_independent)
    try:
        harmonics = int(harmonic_validated_count)
        harmonics_known = True
    except (TypeError, ValueError):
        harmonics = 0
        harmonics_known = False
        raw = _as_float(harmonic_validated_count)
        if np.isfinite(raw):
            harmonics = int(raw)
            harmonics_known = True

    frames_ineligible = bool(np.isfinite(frames) and frames < float(min_independent_frames))
    degenerate = bool(harmonics_known and harmonics <= 2)
    eligible = not frames_ineligible and not degenerate
    return {
        "ewsd_primary_analysis_eligible": bool(eligible),
        "degenerate_partial_set": bool(degenerate),
        "sustain_frame_count_independent": frames,
        "harmonic_validated_count": harmonics if harmonics_known else float("nan"),
        "frames_below_min_independent": frames_ineligible,
    }


def evaluate_stable_representativeness(
    full_ewsd: Any,
    stable_ewsd: Any,
    full_centroid_hz: Any,
    stable_centroid_hz: Any,
    *,
    max_ewsd_ratio: float = STABLE_REPRESENTATIVENESS_MAX_RATIO,
    max_centroid_ratio: float = STABLE_CENTROID_MAX_RATIO,
) -> dict[str, Any]:
    full_e = _as_float(full_ewsd)
    stable_e = _as_float(stable_ewsd)
    full_c = _as_float(full_centroid_hz)
    stable_c = _as_float(stable_centroid_hz)
    ratio = (
        float(full_e / stable_e)
        if np.isfinite(full_e) and np.isfinite(stable_e) and abs(stable_e) > 1e-30
        else float("nan")
    )
    centroid_ratio = float("nan")
    if np.isfinite(full_c) and np.isfinite(stable_c) and min(full_c, stable_c) > 1e-30:
        centroid_ratio = float(max(full_c, stable_c) / min(full_c, stable_c))
    unrepresentative = bool(
        (np.isfinite(ratio) and ratio > float(max_ewsd_ratio))
        or (np.isfinite(centroid_ratio) and centroid_ratio > float(max_centroid_ratio))
    )
    return {
        "full_stable_ewsd_ratio": ratio,
        "full_stable_centroid_ratio": centroid_ratio,
        "stable_segment_unrepresentative": unrepresentative,
    }


def evaluate_segment_diagnostics(
    *,
    primary_ewsd: Any = None,
    primary_centroid_hz: Any = None,
    primary_frames_independent: Any = None,
    sibling_ewsd: Any = None,
    sibling_centroid_hz: Any = None,
    sibling_frames_independent: Any = None,
    primary_role: str = "full_sustain",
    sibling_found: bool = False,
) -> dict[str, Any]:
    """Build the exported stable-segment diagnostic block.

    Primary EWSD is never replaced. Missing sibling values stay NaN.
    """
    role = str(primary_role or "full_sustain").strip().lower()
    out: dict[str, Any] = {
        "segment_policy": SEGMENT_POLICY_DEFAULT,
        "stable_segment_ewsd": missing_metric_nan(),
        "full_stable_ewsd_ratio": missing_metric_nan(),
        "stable_segment_frames_independent": missing_metric_nan(),
        "stable_segment_unrepresentative": False,
        "full_stable_centroid_ratio": missing_metric_nan(),
        "missing_metric_policy_version": MISSING_METRIC_POLICY_VERSION,
    }
    if not sibling_found:
        return out

    if role == "stable":
        stable_ewsd = primary_ewsd
        stable_frames = primary_frames_independent
        full_ewsd = sibling_ewsd
        full_centroid = sibling_centroid_hz
        stable_centroid = primary_centroid_hz
    else:
        stable_ewsd = sibling_ewsd
        stable_frames = sibling_frames_independent
        full_ewsd = primary_ewsd
        full_centroid = primary_centroid_hz
        stable_centroid = sibling_centroid_hz

    out["stable_segment_ewsd"] = _as_float(stable_ewsd)
    out["stable_segment_frames_independent"] = _as_float(stable_frames)
    flags = evaluate_stable_representativeness(
        full_ewsd, stable_ewsd, full_centroid, stable_centroid
    )
    out.update(flags)
    return out


def classify_segment_role(path: Union[str, Path, None]) -> str:
    if path is None:
        return "full_sustain"
    p = Path(path)
    token = f"{p.stem}|{p.parent.name}"
    if "SustainStable" in token or "Sustains_Stable" in token:
        return "stable"
    return "full_sustain"


def find_adsr_sidecar(path: Union[str, Path]) -> Optional[Path]:
    p = Path(path)
    for cand in (
        p.with_suffix(".json"),
        p.with_name(f"{p.stem}_adsr.json"),
        p.with_name(f"{p.stem}_ADSR.json"),
    ):
        if cand.is_file():
            return cand
    return None


def _sidecar_stable_path(sidecar: Path) -> Optional[Path]:
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, Mapping):
        return None
    for key in ("stable_path", "sustain_stable_path", "stable_segment_path"):
        raw = payload.get(key)
        if raw:
            cand = Path(str(raw))
            if not cand.is_absolute():
                cand = sidecar.parent / cand
            if cand.is_file():
                return cand
    return None


def _first_existing(candidates: Iterable[Path]) -> Optional[Path]:
    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def find_segment_sibling(path: Union[str, Path, None]) -> Optional[Path]:
    """Return the full↔stable audio sibling, or a path named in an ADSR sidecar."""
    if path is None:
        return None
    p = Path(path)
    sidecar = find_adsr_sidecar(p)
    if sidecar is not None:
        named = _sidecar_stable_path(sidecar)
        if named is not None and named.resolve() != p.resolve():
            return named

    stem = p.stem
    parent = p.parent
    suffixes = [p.suffix] if p.suffix else list(AUDIO_SUFFIXES)
    suffixes = list(dict.fromkeys([*suffixes, *AUDIO_SUFFIXES]))

    role = classify_segment_role(p)
    if role == "stable":
        full_stem = (
            stem.replace("_SustainStable", "_Sustains")
            .replace("SustainStable", "Sustains")
        )
        same_dir = [parent / f"{full_stem}{ext}" for ext in suffixes]
        if parent.name in {"_Sustains_Stable", "Sustains_Stable"}:
            full_dir = parent.parent / "_Sustains"
            same_dir.extend(full_dir / f"{full_stem}{ext}" for ext in suffixes)
            same_dir.extend(full_dir / f"{stem.replace('SustainStable', 'Sustains')}{ext}" for ext in suffixes)
        return _first_existing(same_dir)

    stable_stem = stem.replace("_Sustains", "_SustainStable")
    if "SustainStable" not in stable_stem:
        if stem.endswith("_Sustains"):
            stable_stem = stem[: -len("_Sustains")] + "_SustainStable"
        else:
            stable_stem = f"{stem}_SustainStable"
    same_dir = [parent / f"{stable_stem}{ext}" for ext in suffixes]
    if parent.name in {"_Sustains", "Sustains"}:
        stable_dir = parent.parent / "_Sustains_Stable"
        same_dir.extend(stable_dir / f"{stable_stem}{ext}" for ext in suffixes)
        same_dir.extend(stable_dir / f"{stem.replace('_Sustains', '_SustainStable')}{ext}" for ext in suffixes)
    return _first_existing(same_dir)


def sanitize_ci_value(value: Any, *, degenerate: bool) -> float:
    """Degenerate CIs are NaN. A finite 0.0 on a degenerate set is a lie."""
    if degenerate:
        return missing_metric_nan()
    return _as_float(value)


def apply_degenerate_ci_nan(payload: Mapping[str, Any], *, degenerate: bool) -> dict[str, Any]:
    out = dict(payload)
    if not degenerate:
        for key in _CI_KEYS:
            if key in out and _as_float(out[key]) == 0.0:
                # Keep genuine zero-width CIs on eligible notes; only the
                # degenerate path is rewritten.
                continue
        return out
    for key in _CI_KEYS:
        if key in out:
            out[key] = missing_metric_nan()
    return out


def mixed_profile_ids(profile_ids: Sequence[Any]) -> list[str]:
    uniq = sorted(
        {
            str(v).strip()
            for v in profile_ids
            if str(v).strip() not in ("", "nan", "None", "<NA>")
        }
    )
    return uniq
