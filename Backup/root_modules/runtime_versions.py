"""
Runtime dependency fingerprint for reproducibility (CI, logs, local checks).

Single import path with no heavy side effects beyond version reads.

This module does **not** write into spectral or compiled Excel exports; use only
where callers explicitly opt in (e.g. CI echo, custom logging).
"""

from __future__ import annotations

import sys
from typing import Dict


def runtime_versions_dict() -> Dict[str, str]:
    """Versions of stack components relevant to STFT / metrics."""
    out: Dict[str, str] = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    }
    for mod_name, key in (
        ("numpy", "numpy"),
        ("scipy", "scipy"),
        ("librosa", "librosa"),
        ("sklearn", "sklearn"),
        ("pandas", "pandas"),
        ("matplotlib", "matplotlib"),
    ):
        try:
            m = __import__(mod_name)
            ver = getattr(m, "__version__", "unknown")
            out[key] = str(ver)
        except Exception:
            out[key] = "unavailable"
    return out


def runtime_stack_fingerprint() -> str:
    """
    Semicolon-separated key=value string (stable key order for diffing across runs).

    For optional inclusion in custom logs or tooling only — not appended to
    workbook schemas by this repository.
    """
    d = runtime_versions_dict()
    order = ("python", "numpy", "scipy", "librosa", "sklearn", "pandas", "matplotlib")
    parts = [f"{k}={d.get(k, '')}" for k in order if d.get(k)]
    return ";".join(parts)
