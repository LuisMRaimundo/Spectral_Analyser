"""Run-level reproducibility manifest (Phase H).

``run_orchestrator.py --corpus … --out … --stages 1,2,3 --figures`` writes
``run_manifest.json`` beside the compiled workbooks. The payload is the
audit record for a corpus run: git identity, package version, constants
hash, parameter profile id, input SHA-256 hashes, and wall time.
"""

from __future__ import annotations

import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from analysis_provenance import resolve_analysis_provenance
from constants import (
    DENSITY_WEIGHT_FUNCTION_DEFAULT,
    ELIGIBILITY_POLICY_VERSION,
    FFT_POLICY_DEFAULT,
    FIXED_HOP_LENGTH_DEFAULT,
    FIXED_N_FFT_DEFAULT,
    SEGMENT_POLICY_DEFAULT,
)
from production_policy import default_parameter_profile_id as _production_profile_id

MANIFEST_SCHEMA_VERSION = "phase21.1"
MANIFEST_FILENAME = "run_manifest.json"
AUDIO_SUFFIXES = (".wav", ".aif", ".aiff", ".flac", ".mp3")
STAGE3_SCORE_COLUMN = "EWSD_score_acoustic_balanced"

__all__ = [
    "AUDIO_SUFFIXES",
    "MANIFEST_FILENAME",
    "MANIFEST_SCHEMA_VERSION",
    "STAGE3_SCORE_COLUMN",
    "build_run_manifest",
    "constants_hash",
    "default_parameter_profile_id",
    "discover_corpus_audio",
    "hash_file",
    "load_run_manifest",
    "looks_like_stage1_root",
    "parse_stages",
    "write_run_manifest",
]


def parse_stages(raw: Union[str, Sequence[int], None]) -> List[int]:
    """Parse ``1,2,3`` / ``2,3`` / ``[1, 2]`` into a unique ordered stage list."""
    if raw is None:
        return [1, 2, 3]
    if isinstance(raw, (list, tuple)) and raw and not isinstance(raw[0], str):
        values = [int(x) for x in raw]
    else:
        text = str(raw).strip()
        if not text:
            return [1, 2, 3]
        values = []
        for part in text.replace(" ", "").split(","):
            if not part:
                continue
            values.append(int(part))
    out: List[int] = []
    for stage in values:
        if stage not in {1, 2, 3}:
            raise ValueError(f"unsupported pipeline stage: {stage}")
        if stage not in out:
            out.append(stage)
    if not out:
        raise ValueError("at least one stage is required")
    return out


def discover_corpus_audio(
    corpus: Union[str, Path],
    pattern: Optional[str] = None,
) -> List[Path]:
    """Return audio files under *corpus* (non-recursive, then one-level fallback)."""
    root = Path(corpus)
    if not root.is_dir():
        return []
    if pattern:
        found = sorted(p for p in root.glob(pattern) if p.is_file())
        if found:
            return found
    found = sorted(
        p
        for p in root.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_SUFFIXES
    )
    if found:
        return found
    nested: List[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        nested.extend(
            p
            for p in child.iterdir()
            if p.is_file() and p.suffix.lower() in AUDIO_SUFFIXES
        )
    return sorted(nested)


def looks_like_stage1_root(path: Union[str, Path]) -> bool:
    root = Path(path)
    if not root.is_dir():
        return False
    return any(root.rglob("spectral_analysis.xlsx"))


def hash_file(path: Union[str, Path], chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def constants_hash() -> str:
    """SHA-256 of numeric constants plus documented string defaults."""
    import constants as constants_mod

    payload: Dict[str, Any] = {}
    for name in constants_mod._iter_numeric_constant_names():
        payload[name] = getattr(constants_mod, name)
    payload["DENSITY_WEIGHT_FUNCTION_DEFAULT"] = str(
        getattr(constants_mod, "DENSITY_WEIGHT_FUNCTION_DEFAULT", "log")
    )
    serialized = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def default_parameter_profile_id(weight_function: Optional[str] = None) -> str:
    return _production_profile_id(weight_function)


def _input_file_records(paths: Iterable[Union[str, Path]]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for raw in paths:
        path = Path(raw)
        rec: Dict[str, Any] = {
            "path": str(path),
            "name": path.name,
            "exists": path.is_file(),
        }
        if path.is_file():
            rec["bytes"] = int(path.stat().st_size)
            rec["sha256"] = hash_file(path)
        else:
            rec["bytes"] = None
            rec["sha256"] = None
        records.append(rec)
    return records


def build_run_manifest(
    *,
    corpus: Optional[Union[str, Path]] = None,
    out_dir: Union[str, Path],
    stages: Sequence[int],
    figures: bool = False,
    weight_function: Optional[str] = None,
    input_files: Optional[Sequence[Union[str, Path]]] = None,
    wall_time_s: Optional[float] = None,
    analysis_parameter_profile_id: Optional[str] = None,
    outputs: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
    repo_root: Optional[Path] = None,
    fft_policy: Optional[str] = None,
    fixed_n_fft: Optional[int] = None,
    fixed_hop_length: Optional[int] = None,
    segment_policy: Optional[str] = None,
    eligibility_policy: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble the canonical ``run_manifest.json`` payload."""
    provenance = resolve_analysis_provenance(repo_root)
    wf = str(weight_function or DENSITY_WEIGHT_FUNCTION_DEFAULT).strip().lower()
    pol = str(fft_policy or FFT_POLICY_DEFAULT).strip().lower()
    if pol not in {"fixed", "adaptive_tier"}:
        pol = str(FFT_POLICY_DEFAULT)
    try:
        n_fft = int(FIXED_N_FFT_DEFAULT if fixed_n_fft is None else fixed_n_fft)
    except (TypeError, ValueError):
        n_fft = int(FIXED_N_FFT_DEFAULT)
    try:
        hop = int(FIXED_HOP_LENGTH_DEFAULT if fixed_hop_length is None else fixed_hop_length)
    except (TypeError, ValueError):
        hop = int(FIXED_HOP_LENGTH_DEFAULT)
    seg = str(segment_policy or SEGMENT_POLICY_DEFAULT).strip() or SEGMENT_POLICY_DEFAULT
    elig = (
        str(eligibility_policy or ELIGIBILITY_POLICY_VERSION).strip()
        or ELIGIBILITY_POLICY_VERSION
    )
    payload: Dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "wall_time_s": None if wall_time_s is None else float(wall_time_s),
        "stages": [int(s) for s in stages],
        "figures": bool(figures),
        "corpus": str(corpus) if corpus is not None else "",
        "out": str(Path(out_dir)),
        "weight_function": wf,
        "fft_policy": pol,
        "fixed_n_fft": n_fft,
        "fixed_hop_length": hop,
        "segment_policy": seg,
        "eligibility_policy": elig,
        "analysis_parameter_profile_id": (
            analysis_parameter_profile_id or default_parameter_profile_id(wf)
        ),
        "constants_hash": constants_hash(),
        "package_version": provenance["package_version"],
        "analysis_version": provenance["analysis_version"],
        "code_commit": provenance["code_commit"],
        "code_dirty": bool(provenance["code_dirty"]),
        "git_describe": provenance["git_describe"],
        "export_schema_version": provenance["export_schema_version"],
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "input_files": _input_file_records(input_files or []),
        "outputs": dict(outputs or {}),
    }
    if extra:
        payload["extra"] = dict(extra)
    return payload


def write_run_manifest(
    out_dir: Union[str, Path],
    payload: Dict[str, Any],
    *,
    filename: str = MANIFEST_FILENAME,
) -> Path:
    dest_dir = Path(out_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / filename
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def load_run_manifest(path: Union[str, Path]) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
