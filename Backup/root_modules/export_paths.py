"""
Publication-safe path handling for JSON/Excel/metadata exports.

Delegates to :mod:`metadata_sanitizer` export helpers (v7-compatible).

Legacy: set ``SOUNDSPECTRANALYSE_EXPORT_ABSOLUTE_PATHS=1`` to skip structured
sanitization (maps to ``metadata_privacy_mode=internal_debug``).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

try:
    from metadata_sanitizer import (
        detect_absolute_local_path,
        get_metadata_privacy_mode,
        sanitize_export_metadata_dict as _sanitize_metadata_dict,
        sanitize_path_for_publication,
    )
except Exception:  # pragma: no cover - import guard for partial installs
    detect_absolute_local_path = None  # type: ignore

    def get_metadata_privacy_mode() -> str:  # type: ignore
        return "public"

    def _sanitize_metadata_dict(obj: Any, dataset_root: Optional[Path] = None) -> Any:  # type: ignore
        return obj

    def sanitize_path_for_publication(path: Any, dataset_root: Optional[Path] = None) -> str:  # type: ignore
        try:
            return Path(str(path)).name
        except Exception:
            return "path_redacted"


def export_absolute_paths() -> bool:
    """True when callers should preserve raw paths (internal debug / legacy env)."""
    try:
        return get_metadata_privacy_mode() == "internal_debug"
    except Exception:
        v = os.environ.get("SOUNDSPECTRANALYSE_EXPORT_ABSOLUTE_PATHS", "").strip().lower()
        return v in ("1", "true", "yes", "debug")


def redact_path_str(s: str) -> str:
    """Return basename or corpus-relative path for publication exports."""
    if not isinstance(s, str):
        return str(s)
    return sanitize_path_for_publication(s, dataset_root=None)


def sanitize_str(value: str) -> str:
    if export_absolute_paths():
        return value
    if len(value) > 160 and (":\\" in value or "\\\\" in value):
        try:
            obj = json.loads(value)
            dumped = json.dumps(_sanitize_metadata_dict(obj), ensure_ascii=False, default=str)
            return dumped
        except Exception:
            pass
    if detect_absolute_local_path is not None and len(value) >= 3 and detect_absolute_local_path(value):
        return redact_path_str(value)
    return value


def sanitize_for_repo(obj: Any) -> Any:
    """Recursively redact absolute paths for repository / publication exports."""
    if export_absolute_paths():
        return obj
    return _sanitize_metadata_dict(obj, dataset_root=None)
