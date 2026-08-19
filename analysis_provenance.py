"""Single-source analysis / export provenance.

``analysis_version`` and ``export_schema_version`` are never hard-coded in
callers. Package version comes from ``importlib.metadata`` or
``pyproject.toml``; the git identity is ``git describe --always --dirty``.
``export_schema_version`` is the token in ``analysis_policy``.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from analysis_policy import EXPORT_SCHEMA_VERSION

__all__ = [
    "EXPORT_SCHEMA_VERSION",
    "provenance_export_fields",
    "resolve_analysis_provenance",
    "resolve_git_describe",
    "resolve_package_version",
]

_REPO_ROOT = Path(__file__).resolve().parent
_UNKNOWN = "unknown"


def resolve_package_version(repo_root: Optional[Path] = None) -> tuple[str, str]:
    """Return ``(version, source)``. Never a hard-coded package number.

    A checkout's ``pyproject.toml`` wins over an older installed wheel so
    exports stamp the tree that actually ran, not site-packages.
    """
    root = Path(repo_root) if repo_root is not None else _REPO_ROOT
    try:
        pyproject_path = root / "pyproject.toml"
        if pyproject_path.is_file():
            content = pyproject_path.read_text(encoding="utf-8")
            match = re.search(
                r'^\s*version\s*=\s*["\']([^"\']+)["\']\s*$',
                content,
                flags=re.MULTILINE,
            )
            if match:
                return match.group(1), f"pyproject.toml:{pyproject_path.name}"
    except Exception:
        pass

    try:
        from importlib import metadata as importlib_metadata

        version = importlib_metadata.version("spectral-analyser")
        if str(version).strip():
            return str(version).strip(), "importlib.metadata:spectral-analyser"
    except Exception:
        pass
    return _UNKNOWN, "unavailable"


def resolve_git_describe(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Run ``git describe --always --dirty`` in the repo (or report unavailable)."""
    root = Path(repo_root) if repo_root is not None else _REPO_ROOT
    out: Dict[str, Any] = {
        "git_describe": _UNKNOWN,
        "code_commit": _UNKNOWN,
        "code_dirty": False,
        "git_available": False,
    }
    try:
        describe = subprocess.run(
            ["git", "describe", "--always", "--dirty"],
            capture_output=True,
            text=True,
            cwd=str(root),
            check=False,
        )
        if describe.returncode == 0 and str(describe.stdout).strip():
            token = str(describe.stdout).strip()
            out["git_describe"] = token
            out["git_available"] = True
            out["code_dirty"] = token.endswith("-dirty")
        short = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(root),
            check=False,
        )
        if short.returncode == 0 and str(short.stdout).strip():
            out["code_commit"] = str(short.stdout).strip()
            out["git_available"] = True
    except Exception:
        return out
    return out


def resolve_analysis_provenance(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Canonical provenance dict for every Stage 1/2/3 export."""
    package_version, package_source = resolve_package_version(repo_root)
    git = resolve_git_describe(repo_root)
    describe = str(git.get("git_describe") or _UNKNOWN)
    if package_version != _UNKNOWN and describe not in {_UNKNOWN, ""}:
        if describe == package_version or describe.lstrip("v") == package_version:
            analysis_version = package_version
        else:
            analysis_version = f"{package_version}+{describe}"
        source = f"{package_source}+git-describe"
    elif package_version != _UNKNOWN:
        analysis_version = package_version
        source = package_source
    elif describe != _UNKNOWN:
        analysis_version = describe
        source = "git-describe"
    else:
        analysis_version = _UNKNOWN
        source = "unavailable"
    return {
        "package_version": package_version,
        "package_version_source": package_source,
        "analysis_version": analysis_version,
        "analysis_version_source": source,
        "git_describe": describe,
        "code_commit": str(git.get("code_commit") or _UNKNOWN),
        "code_dirty": bool(git.get("code_dirty")),
        "export_schema_version": EXPORT_SCHEMA_VERSION,
    }


def provenance_export_fields(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Flat fields written to Analysis_Metadata / Stage3_Summary."""
    p = resolve_analysis_provenance(repo_root)
    return {
        "analysis_version": p["analysis_version"],
        "analysis_version_source": p["analysis_version_source"],
        "package_version": p["package_version"],
        "code_commit": p["code_commit"],
        "code_dirty": p["code_dirty"],
        "git_describe": p["git_describe"],
        "export_schema_version": p["export_schema_version"],
    }
