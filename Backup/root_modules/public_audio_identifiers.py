"""
Phase 2 — public dataset identifiers (no local paths, stable sample_id).

Builds publication metadata blocks for JSON / Excel / CSV / batch exports.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any, Optional, Union

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

__all__ = [
    "extract_note_label_from_filename",
    "parse_filename_heuristic_labels",
    "compute_sample_id",
    "sha256_hex_of_file",
    "sha256_hex_of_array",
    "build_public_audio_identifier_block",
    "default_dataset_root_from_env",
]


def default_dataset_root_from_env() -> Optional[Path]:
    v = os.environ.get("SPECTRAL_ANALYSER_DATASET_ROOT", "").strip()
    if not v:
        return None
    return Path(v)


def default_dataset_name_from_env() -> Optional[str]:
    v = os.environ.get("SPECTRAL_ANALYSER_DATASET_NAME", "").strip()
    return v or None


def default_dataset_version_from_env() -> Optional[str]:
    v = os.environ.get("SPECTRAL_ANALYSER_DATASET_VERSION", "").strip()
    return v or None


def extract_note_label_from_filename(name: str) -> Optional[str]:
    """Same convention as proc_audio.AudioProcessor.extract_note_name (note+octave)."""
    base = Path(name).name if not isinstance(name, Path) else name.name
    base = base.replace('"', "").replace("'", "")
    for pat in (r"([A-G][#b]?)[-_]?(\d)", r"([A-G][#b]?)(\d)"):
        m = re.search(pat, base)
        if m:
            return m.group(1) + m.group(2)
    return None


_KNOWN_INSTR = frozenset(
    {
        "vla",
        "vln",
        "vc",
        "cb",
        "tpt",
        "tbn",
        "hn",
        "fl",
        "ob",
        "cl",
        "bsn",
        "sax",
        "pno",
        "hp",
        "gtr",
        "viola",
        "violin",
        "cello",
        "bass",
    }
)
_KNOWN_TECH = frozenset(
    {
        "arco",
        "pizz",
        "pizzicato",
        "spiccato",
        "trem",
        "trill",
        "mute",
        "ord",
        "legato",
        "staccato",
        "marcato",
        "sul",
    }
)
_KNOWN_DYN = frozenset({"pp", "p", "mp", "mf", "f", "ff", "fff", "sf", "sfz", "fp", "rfz"})


def parse_filename_heuristic_labels(stem: str) -> dict[str, Optional[str]]:
    """
    Best-effort labels from filename stem (e.g. IOWA_Vla_arco_mf.A4).
    All values may be None when not inferable.
    """
    out: dict[str, Optional[str]] = {
        "parsed_instrument_label": None,
        "parsed_technique_label": None,
        "parsed_dynamic_label": None,
    }
    if not stem:
        return out
    note = extract_note_label_from_filename(stem + ".wav")
    work = stem
    if note:
        work = re.sub(r"[_\-.]?" + re.escape(note) + r"$", "", stem, flags=re.I).rstrip("._-")
    parts = [p for p in re.split(r"[\s_\-]+", work.replace(".", "_")) if p]
    if not parts:
        return out
    for p in parts:
        low = p.lower()
        if low in _KNOWN_INSTR:
            out["parsed_instrument_label"] = p
        elif low in _KNOWN_TECH or any(t in low for t in ("arco", "pizz", "spicc")):
            out["parsed_technique_label"] = p
        elif low in _KNOWN_DYN:
            out["parsed_dynamic_label"] = p.upper() if len(low) <= 4 else p
    return out


def sha256_hex_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_hex_of_array(y: Any) -> str:
    if np is None:
        return hashlib.sha256(str(y).encode("utf-8", errors="replace")).hexdigest()
    arr = np.asarray(y, dtype=np.float64)
    return hashlib.sha256(arr.tobytes(order="C")).hexdigest()


def compute_sample_id(file_stem: str, sha256_hex: str, *, max_stem_chars: int = 96) -> str:
    """Stable slug: sanitized stem + first 8 hex chars of SHA-256."""
    h8 = sha256_hex[:8]
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", file_stem).strip("._")
    if len(base) > max_stem_chars:
        base = base[:max_stem_chars].rstrip("._")
    base = base.replace(".", "_")
    if not base:
        base = "sample"
    return f"{base}__sha256_{h8}"


def build_public_audio_identifier_block(
    path: Union[str, Path],
    *,
    dataset_root: Optional[Path] = None,
    y: Any = None,
    sr: Optional[int] = None,
    detected_note_label: Optional[str] = None,
    channel_mode: Optional[str] = None,
    dataset_name: Optional[str] = None,
    dataset_version: Optional[str] = None,
    corpus_id: Optional[str] = None,
    item_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Publication-safe identifiers for one audio clip.

    Never includes absolute ``dataset_root``; only paths relative to it (POSIX ``/``).
    """
    from metadata_sanitizer import publication_audio_path_fields

    p = Path(str(path))
    dr = dataset_root if dataset_root is not None else default_dataset_root_from_env()
    pub = publication_audio_path_fields(p, dataset_root=dr)

    stem = p.stem
    ext = p.suffix
    if ext and not ext.startswith("."):
        ext = "." + ext

    sha_full = ""
    size_b: Optional[int] = None
    if p.is_file():
        try:
            sha_full = sha256_hex_of_file(p)
            size_b = int(p.stat().st_size)
        except OSError:
            sha_full = ""
    if not sha_full and y is not None:
        sha_full = sha256_hex_of_array(y)
    if not sha_full:
        sha_full = hashlib.sha256(stem.encode("utf-8")).hexdigest()

    sha_short = sha_full[:16] if sha_full else ""

    note_lbl = detected_note_label or extract_note_label_from_filename(p.name) or ""
    labels = parse_filename_heuristic_labels(stem)

    duration_sec: Optional[float] = None
    if y is not None and sr and int(sr) > 0 and np is not None:
        try:
            arr = np.asarray(y)
            n = int(arr.shape[-1]) if arr.ndim >= 1 else int(arr.size)
            duration_sec = float(n) / float(sr)
        except Exception:
            duration_sec = None

    ch = channel_mode
    if ch is None and y is not None and np is not None:
        try:
            arr = np.asarray(y)
            if arr.ndim == 1:
                ch = "mono"
            elif arr.ndim == 2:
                ch = f"{int(arr.shape[0])}-channel"
        except Exception:
            ch = None

    rel = pub.get("audio_relative_path", p.name)
    if isinstance(rel, str):
        rel = rel.replace("\\", "/")

    sample_id = compute_sample_id(stem, sha_full)

    out: dict[str, Any] = {
        "audio_file": pub["audio_file_name"],
        "audio_file_name": pub["audio_file_name"],
        "audio_file_stem": stem,
        "audio_file_extension": ext if ext else "",
        "audio_sha256": sha_full or None,
        "audio_sha256_short": sha_short or None,
        "audio_size_bytes": size_b,
        "sample_rate_hz": int(sr) if sr is not None else None,
        "duration_sec": duration_sec,
        "channel_mode": ch,
        "detected_note_label": note_lbl or None,
        "parsed_instrument_label": labels.get("parsed_instrument_label"),
        "parsed_technique_label": labels.get("parsed_technique_label"),
        "parsed_dynamic_label": labels.get("parsed_dynamic_label"),
        "dataset_relative_path": rel,
        "sample_id": sample_id,
        "audio_file_basename": stem,
        "audio_file_ext": ext if ext else "",
        "audio_relative_path": rel,
        "audio_path_policy": pub.get("audio_path_policy", "sanitized_for_publication"),
    }

    dn = dataset_name if dataset_name is not None else default_dataset_name_from_env()
    dv = dataset_version if dataset_version is not None else default_dataset_version_from_env()
    if dn:
        out["dataset_name"] = dn
    if dv:
        out["dataset_version"] = dv
    if corpus_id:
        out["corpus_id"] = corpus_id
    if item_id:
        out["item_id"] = item_id

    return out
