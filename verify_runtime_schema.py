#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify per-note ``spectral_analysis.xlsx`` workbooks against the
current single-pass raw-export schema.

AUDIT FIX (stale-pipeline detection) — this CLI is the third leg of
the schema-guard tripod, alongside:

  * the pre-save validator in :mod:`proc_audio`
    (``AudioProcessor._validate_per_note_export_schema``); and
  * the compile-time guard in :mod:`compile_metrics`
    (``assert_results_dir_schema_or_raise`` /
    ``extract_density_components_from_per_note_workbook``).

Usage
-----

    python verify_runtime_schema.py --results-dir <analysis_results>
    python verify_runtime_schema.py --results-dir <dir> --json
    python verify_runtime_schema.py --results-dir <dir> --quiet

Exit codes
----------

    0   every per-note workbook passes the schema check; the runtime
        paths printed at the top match the on-disk source tree.
    1   at least one stale-schema workbook detected, or the directory
        does not contain per-note workbooks at all (e.g. the user
        pointed at the wrong results folder).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit per-note spectral_analysis.xlsx workbooks against the "
            "current ANALYSIS_SCHEMA_VERSION; report stale-pipeline outputs."
        )
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        required=True,
        help="Directory containing per-note spectral_analysis.xlsx files "
        "(recursive scan).",
    )
    parser.add_argument(
        "--file-pattern",
        type=str,
        default="spectral_analysis.xlsx",
        help="File-name pattern for the per-note workbooks (default: "
        "spectral_analysis.xlsx).",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Optionally cap the number of files scanned (useful on huge "
        "corpora; first N files only).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable JSON report to stdout instead of the "
        "human-friendly text summary.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file detail lines; only print the rolled-up "
        "summary (and the first failing file, when applicable).",
    )
    args = parser.parse_args(argv)

    try:
        from compile_metrics import (
            scan_results_dir_for_stale_per_note_workbooks,
            EXPECTED_ANALYSIS_SCHEMA_VERSION,
        )
        from proc_audio import log_runtime_paths
    except Exception as exc:
        print(
            f"[verify_runtime_schema] FATAL: could not import "
            f"compile_metrics / proc_audio: {exc}",
            file=sys.stderr,
        )
        return 1

    # Always announce the resolved runtime paths first; if the operator
    # ran this against a stale install of the package, this single block
    # makes the divergence obvious.
    try:
        runtime = log_runtime_paths()
    except Exception:
        runtime = {}

    summary = scan_results_dir_for_stale_per_note_workbooks(
        args.results_dir,
        file_pattern=args.file_pattern,
        max_samples=args.max_samples,
    )

    # Roll-up counters required by the audit.
    counters: Dict[str, Any] = {
        "results_dir": str(args.results_dir),
        "expected_schema": EXPECTED_ANALYSIS_SCHEMA_VERSION,
        "files_found": summary.get("total", 0),
        "schema_ok": 0,
        "missing_amplitude_raw": 0,
        "missing_power_raw": 0,
        "model_weights_source_not_current_analysis": 0,
        "stale_density_metrics_layout": 0,
        "first_failing_path": summary.get("first_failing_path"),
        "first_failing_reason": summary.get("first_failing_reason"),
    }
    for info in summary.get("details", []):
        if info.get("schema_ok"):
            counters["schema_ok"] += 1
        if not info.get("has_amplitude_raw"):
            counters["missing_amplitude_raw"] += 1
        if not info.get("has_power_raw"):
            counters["missing_power_raw"] += 1
        if (
            info.get("model_weights_source")
            and info.get("model_weights_source") != "current_analysis"
        ):
            counters["model_weights_source_not_current_analysis"] += 1
        if info.get("density_metrics_layout") == "legacy_six_columns":
            counters["stale_density_metrics_layout"] += 1

    if args.json:
        payload = {
            "runtime": runtime,
            "counters": counters,
            "details": summary.get("details", []) if not args.quiet else None,
            "stale_total": summary.get("stale", 0),
            "valid_total": summary.get("valid", 0),
        }
        print(json.dumps(payload, indent=2, default=str))
    else:
        print("=" * 72)
        print("verify_runtime_schema — runtime audit")
        print("=" * 72)
        for k in (
            "sys_executable",
            "cwd",
            "proc_audio_file",
            "compile_metrics_file",
            "publication_chart_policy_file",
            "analysis_schema_version",
            "proc_audio_runtime_signature",
        ):
            print(f"  {k:<32} = {runtime.get(k, '<unknown>')}")
        print("-" * 72)
        print(f"  results_dir                      = {counters['results_dir']}")
        print(f"  expected_schema                  = {counters['expected_schema']}")
        print(f"  files_found                      = {counters['files_found']}")
        print(f"  schema_ok                        = {counters['schema_ok']}")
        print(
            f"  missing_amplitude_raw            = "
            f"{counters['missing_amplitude_raw']}"
        )
        print(f"  missing_power_raw                = {counters['missing_power_raw']}")
        print(
            f"  model_weights_source!=current_analysis = "
            f"{counters['model_weights_source_not_current_analysis']}"
        )
        print(
            f"  stale_density_metrics_layout     = "
            f"{counters['stale_density_metrics_layout']}"
        )
        if counters["first_failing_path"]:
            print(f"  first_failing_path               = {counters['first_failing_path']}")
            print(
                f"  first_failing_reason             = "
                f"{counters['first_failing_reason']}"
            )
        print("=" * 72)
        if not args.quiet:
            for info in summary.get("details", []):
                tag = "OK   " if info.get("schema_ok") and not info.get("problems") else "STALE"
                print(
                    f"  [{tag}] {info.get('path')} "
                    f"schema={info.get('schema_version')!r} "
                    f"mws={info.get('model_weights_source')!r} "
                    f"raw_amp={info.get('has_amplitude_raw')} "
                    f"power_raw={info.get('has_power_raw')}"
                )
                for prob in info.get("problems", []):
                    print(f"        - {prob}")

    if counters["files_found"] == 0:
        # Treat "no per-note workbooks" as a failing audit: the operator
        # almost certainly pointed at the wrong directory, and silently
        # exiting 0 would be misleading.
        return 1
    if summary.get("stale", 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
