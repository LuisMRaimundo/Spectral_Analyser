"""Corpus-level check complementary to ``verify_export.py`` (per-workbook).

Usage::

    python -m tools.verify_corpus <run_dir>
    python tools/verify_corpus.py path/to/run_manifest.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from constants import (
    DENSITY_WEIGHT_FUNCTION_DEFAULT,
    ELIGIBILITY_POLICY_VERSION,
    FFT_POLICY_DEFAULT,
    FIXED_HOP_LENGTH_DEFAULT,
    FIXED_N_FFT_DEFAULT,
    SEGMENT_POLICY_DEFAULT,
)
from production_policy import (
    is_primary_comparable_profile,
    mixed_profile_ids,
)
from run_manifest import MANIFEST_FILENAME, load_run_manifest

REQUIRED_MANIFEST_KEYS = (
    "schema_version",
    "package_version",
    "analysis_version",
    "code_commit",
    "constants_hash",
    "analysis_parameter_profile_id",
    "weight_function",
)
WORKBOOK_CANDIDATES = (
    "compiled_density_metrics_research.xlsx",
    "compiled_density_metrics.xlsx",
)
NOTE_SHEETS = ("Spectral_Density_Metrics", "Density_Metrics", "Metrics")


def parse_profile_id(profile_id: Any) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for part in str(profile_id or "").split("|"):
        token = part.strip()
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        key = key.strip()
        if key:
            out[key] = value.strip()
    return out


def resolve_run_paths(target: Path) -> tuple[Path, Path]:
    """Return ``(run_dir, manifest_path)`` from a folder or a manifest file."""
    path = Path(target)
    if path.is_file():
        return path.parent, path
    return path, path / MANIFEST_FILENAME


def _first_col(df: pd.DataFrame, *names: str) -> Optional[str]:
    lower = {str(c).strip().lower(): str(c) for c in df.columns}
    for name in names:
        hit = lower.get(str(name).strip().lower())
        if hit:
            return hit
    return None


def load_compiled_metrics(path: Path) -> Optional[pd.DataFrame]:
    src = Path(path)
    if src.is_dir():
        for cand in WORKBOOK_CANDIDATES:
            hit = src / cand
            if hit.is_file():
                src = hit
                break
        else:
            return None
    if not src.is_file():
        return None
    try:
        sheets = pd.ExcelFile(src).sheet_names
    except Exception:
        return None
    for name in NOTE_SHEETS:
        if name not in sheets:
            continue
        try:
            df = pd.read_excel(src, sheet_name=name)
        except Exception:
            continue
        note_col = _first_col(df, "Note", "sample_note_tag")
        if note_col:
            df = df.rename(columns={note_col: "Note"})
            df["Note"] = df["Note"].astype(str).str.strip()
            return df
    return None


def discover_workbooks(run_dir: Path, manifest: Dict[str, Any]) -> List[Path]:
    found: List[Path] = []
    outputs = manifest.get("outputs") or {}
    for key in ("research_workbook", "compiled_workbook"):
        raw = outputs.get(key)
        if raw:
            cand = Path(str(raw))
            if cand.is_file() and cand not in found:
                found.append(cand)
    for name in WORKBOOK_CANDIDATES:
        cand = run_dir / name
        if cand.is_file() and cand not in found:
            found.append(cand)
    return found


def _boolish(value: Any) -> Optional[bool]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "1.0", "yes"}:
        return True
    if text in {"false", "0", "0.0", "no"}:
        return False
    return None


def _finite_float(value: Any) -> Optional[float]:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out:
        return None
    return out


def _check_workbook_policy(
    df: pd.DataFrame,
    *,
    expected_profile: str,
    issues: List[str],
    warnings: List[str],
    require_comparable: bool,
) -> None:
    profile_col = _first_col(df, "analysis_parameter_profile_id")
    if profile_col is not None:
        ids = mixed_profile_ids(df[profile_col].tolist())
        if len(ids) > 1:
            issues.append(
                f"mixed analysis_parameter_profile_id ({len(ids)}): {', '.join(ids)}"
            )
        elif ids and expected_profile and ids[0] != expected_profile:
            issues.append(
                "workbook analysis_parameter_profile_id does not match "
                f"run_manifest ({ids[0]} != {expected_profile})"
            )
    fft_col = _first_col(df, "fft_policy")
    if fft_col is not None:
        policies = sorted(
            {
                str(v).strip().lower()
                for v in df[fft_col].tolist()
                if str(v).strip() not in ("", "nan", "None")
            }
        )
        if any(p != "fixed" for p in policies):
            message = f"workbook fft_policy is not fixed: {policies}"
            if require_comparable:
                issues.append(message)
            else:
                warnings.append(message)

    elig_col = _first_col(df, "ewsd_primary_analysis_eligible")
    deg_col = _first_col(df, "degenerate_partial_set")
    rel_col = _first_col(
        df,
        "EWSD_score_acoustic_balanced_rel_uncertainty",
        "ewsd_score_acoustic_balanced_rel_uncertainty",
        "rel_uncertainty",
    )
    if elig_col is None:
        warnings.append("workbook has no ewsd_primary_analysis_eligible column")
        return
    for idx, row in df.iterrows():
        eligible = _boolish(row.get(elig_col))
        degenerate = _boolish(row.get(deg_col)) if deg_col else None
        if eligible is False and degenerate is True and rel_col is not None:
            rel = _finite_float(row.get(rel_col))
            if rel == 0.0:
                note = str(row.get("Note", idx))
                issues.append(
                    f"{note}: degenerate ineligible CI rel_uncertainty is 0.0 "
                    "(must be NaN)"
                )


def verify_corpus(
    target: Path,
    *,
    require_comparable: bool = True,
) -> Dict[str, Any]:
    """Inspect a corpus run directory or ``run_manifest.json``."""
    issues: List[str] = []
    warnings: List[str] = []
    run_dir, manifest_path = resolve_run_paths(Path(target))
    payload: Dict[str, Any] = {
        "path": str(run_dir),
        "manifest_path": str(manifest_path),
        "ok": False,
        "comparable": False,
        "issues": issues,
        "warnings": warnings,
    }
    if not run_dir.exists():
        issues.append(f"run directory not found: {run_dir}")
        return payload
    if not manifest_path.is_file():
        issues.append(f"missing {MANIFEST_FILENAME}")
        return payload

    try:
        manifest = load_run_manifest(manifest_path)
    except Exception as exc:
        issues.append(f"run_manifest is not valid JSON: {exc}")
        return payload
    if not isinstance(manifest, dict):
        issues.append("run_manifest root is not an object")
        return payload

    payload["package_version"] = str(manifest.get("package_version") or "")
    payload["analysis_parameter_profile_id"] = str(
        manifest.get("analysis_parameter_profile_id") or ""
    )
    payload["weight_function"] = str(manifest.get("weight_function") or "")
    payload["fft_policy"] = str(manifest.get("fft_policy") or "")
    payload["fixed_n_fft"] = manifest.get("fixed_n_fft")
    payload["fixed_hop_length"] = manifest.get("fixed_hop_length")
    payload["segment_policy"] = str(manifest.get("segment_policy") or "")
    payload["eligibility_policy"] = str(manifest.get("eligibility_policy") or "")

    missing = [key for key in REQUIRED_MANIFEST_KEYS if not manifest.get(key)]
    if missing:
        issues.append("run_manifest missing keys: " + ", ".join(missing))

    wf = str(manifest.get("weight_function") or "").strip().lower()
    tokens = parse_profile_id(manifest.get("analysis_parameter_profile_id"))
    fft = str(manifest.get("fft_policy") or tokens.get("fft") or "").strip().lower()
    seg = str(
        manifest.get("segment_policy") or tokens.get("seg") or ""
    ).strip()
    elig = str(
        manifest.get("eligibility_policy") or tokens.get("elig") or ""
    ).strip()

    if "fft" not in tokens:
        issues.append("analysis_parameter_profile_id missing fft= token")
    if "seg" not in tokens:
        issues.append("analysis_parameter_profile_id missing seg= token")
    if "elig" not in tokens:
        issues.append("analysis_parameter_profile_id missing elig= token")

    policy_deviations: List[str] = []
    if fft and fft != str(FFT_POLICY_DEFAULT):
        policy_deviations.append(
            f"fft_policy is {fft!r}, expected {FFT_POLICY_DEFAULT!r}"
        )
    if seg and seg != SEGMENT_POLICY_DEFAULT:
        policy_deviations.append(
            f"segment_policy is {seg!r}, expected {SEGMENT_POLICY_DEFAULT!r}"
        )
    if elig and elig != str(ELIGIBILITY_POLICY_VERSION):
        policy_deviations.append(
            f"eligibility_policy is {elig!r}, expected {ELIGIBILITY_POLICY_VERSION!r}"
        )

    n_fft = manifest.get("fixed_n_fft")
    if n_fft is not None:
        try:
            if int(n_fft) != int(FIXED_N_FFT_DEFAULT):
                policy_deviations.append(
                    f"fixed_n_fft is {n_fft}, expected {FIXED_N_FFT_DEFAULT}"
                )
        except (TypeError, ValueError):
            policy_deviations.append(f"fixed_n_fft is not an integer: {n_fft!r}")
    hop = manifest.get("fixed_hop_length")
    if hop is not None:
        try:
            if int(hop) != int(FIXED_HOP_LENGTH_DEFAULT):
                policy_deviations.append(
                    f"fixed_hop_length is {hop}, expected {FIXED_HOP_LENGTH_DEFAULT}"
                )
        except (TypeError, ValueError):
            policy_deviations.append(f"fixed_hop_length is not an integer: {hop!r}")

    comparable = is_primary_comparable_profile(
        wf or DENSITY_WEIGHT_FUNCTION_DEFAULT, fft or FFT_POLICY_DEFAULT
    )
    payload["comparable"] = bool(comparable)
    if not comparable:
        policy_deviations.append(
            "run is not a primary-comparable profile "
            f"(weight_function={wf or 'missing'}, fft_policy={fft or 'missing'})"
        )
    if require_comparable:
        issues.extend(policy_deviations)
    else:
        warnings.extend(policy_deviations)

    workbooks = discover_workbooks(run_dir, manifest)
    payload["workbooks"] = [str(p) for p in workbooks]
    if not workbooks:
        warnings.append("no compiled / research workbook found beside the manifest")
    expected_profile = str(manifest.get("analysis_parameter_profile_id") or "")
    for book in workbooks:
        frame = load_compiled_metrics(book)
        if frame is None or frame.empty:
            warnings.append(f"could not read Note metrics from {book.name}")
            continue
        _check_workbook_policy(
            frame,
            expected_profile=expected_profile,
            issues=issues,
            warnings=warnings,
            require_comparable=require_comparable,
        )

    payload["ok"] = not issues
    return payload


def format_report(result: Dict[str, Any]) -> str:
    lines = [
        f"run: {result.get('path')}",
        f"manifest: {result.get('manifest_path')}",
        f"package_version: {result.get('package_version') or 'missing'}",
        f"profile: {result.get('analysis_parameter_profile_id') or 'missing'}",
        f"fft_policy: {result.get('fft_policy') or 'missing'}",
        f"fixed_n_fft: {result.get('fixed_n_fft')}",
        f"fixed_hop_length: {result.get('fixed_hop_length')}",
        f"segment_policy: {result.get('segment_policy') or 'missing'}",
        f"eligibility_policy: {result.get('eligibility_policy') or 'missing'}",
        f"comparable: {result.get('comparable')}",
        f"status: {'ok' if result.get('ok') else 'FAIL'}",
    ]
    workbooks = result.get("workbooks") or []
    if workbooks:
        lines.append("workbooks: " + ", ".join(Path(p).name for p in workbooks))
    for issue in result.get("issues") or []:
        lines.append(f"issue: {issue}")
    for warning in result.get("warnings") or []:
        lines.append(f"warning: {warning}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify a corpus run against the production policy "
            "(fft=fixed/8192/1024, sustain-primary, eligibility, one profile)."
        )
    )
    parser.add_argument(
        "run",
        type=Path,
        help="Run directory or run_manifest.json",
    )
    parser.add_argument(
        "--allow-noncomparable",
        action="store_true",
        help="Do not fail adaptive_tier / non-default φ research runs.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the structured result as JSON.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = verify_corpus(
        Path(args.run),
        require_comparable=not bool(args.allow_noncomparable),
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        print(format_report(result))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
