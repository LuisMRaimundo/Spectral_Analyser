#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spectral_Analyser - Pipeline Entry Point
=========================================

Pipeline:
    Stage 1: Per-note spectral analysis (proc_audio.AudioProcessor)
    Stage 2: Compilation (per-note spectral_analysis.xlsx -> compiled workbook)
    Stage 3: Research export + EWSD-R v18 merge (compiled_density_metrics_research.xlsx)

Usage:
    python run_orchestrator.py --corpus PATH --out DIR --stages 1,2,3 --figures
    python run_orchestrator.py --audio-dir PATH
    python run_orchestrator.py file1.wav file2.wav ...

There is no Phase 1, no Batch preprocessing, no batch_summary.xlsx, and no
synthetic harmonic/inharmonic percentages. Component energy ratios come only
from the current per-note spectral analysis.
"""

import argparse
import sys
from pathlib import Path

from constants import (
    DENSITY_WEIGHT_FUNCTION_DEFAULT,
    FFT_POLICY_DEFAULT,
    FIXED_HOP_LENGTH_DEFAULT,
    FIXED_N_FFT_DEFAULT,
)
from pipeline_orchestrator_integrated import RobustOrchestrator
from run_manifest import discover_corpus_audio, looks_like_stage1_root, parse_stages

# Legacy CLI flags removed in the Stage 1 / Stage 2 refactor. Passing any of
# them must hard-error so old shell invocations fail loudly instead of
# silently reactivating the obsolete batch pipeline.
_LEGACY_REJECTED_TOKENS = (
    "--phase1-mode",
    "--phase1_mode",
    "--phase-1-mode",
    "--excel-summary",
    "--batch-output",
    "--batch-excel",
    "--batch_excel",
    "--legacy-batch",
    "--legacy_batch",
)


def _reject_legacy_cli_flags(argv: list[str]) -> None:
    """Hard-error if any deprecated batch/phase1 flag is passed."""
    bad: list[str] = []
    for token in argv:
        lowered = token.lower().split("=", 1)[0]
        if lowered in _LEGACY_REJECTED_TOKENS:
            bad.append(token)
    if bad:
        sys.stderr.write(
            "error: the following legacy flags were removed in the Stage 1 / "
            "Stage 2 refactor and are no longer accepted: "
            f"{', '.join(bad)}\n"
            "The current pipeline performs per-note spectral analysis only; "
            "there is no Batch preprocessing.\n"
        )
        sys.exit(2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Spectral_Analyser pipeline - Stage 1 (per-note spectral "
            "analysis), Stage 2 (compilation), Stage 3 (research export + EWSD)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python run_orchestrator.py --corpus \"C:\\audio\" --out results "
            "--stages 1,2,3 --figures\n"
            "  python run_orchestrator.py --audio-dir \"C:\\path\\to\\audio\"\n"
            "  python run_orchestrator.py file1.wav file2.wav file3.wav\n"
            "  python -m tools.reexport_corpus --stage1-root results --out reexport "
            "--baseline docs/validation/ANALISE_3_TUBA_PP_EWSD_2026_08_19.json\n"
        ),
    )
    parser.add_argument(
        "audio_files",
        nargs="*",
        help="Audio files to process (optional if --corpus / --audio-dir is provided)",
    )
    parser.add_argument(
        "--corpus",
        type=str,
        help="Corpus directory (audio files, or Stage 1 workbooks when Stage 1 is skipped)",
    )
    parser.add_argument(
        "--audio-dir",
        type=str,
        help="Directory containing audio files to process (alias of --corpus)",
    )
    parser.add_argument(
        "--out",
        type=str,
        help="Output directory (writes run_manifest.json here)",
    )
    parser.add_argument(
        "--main-output",
        type=str,
        default="main_analysis_results",
        help="Legacy alias of --out (default: main_analysis_results)",
    )
    parser.add_argument(
        "--stages",
        type=str,
        default="1,2,3",
        help="Comma-separated stages to run (default: 1,2,3)",
    )
    parser.add_argument(
        "--figures",
        action="store_true",
        help="Write Stage 3 publication charts (EWSD CI figure)",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default=None,
        help="Optional glob under --corpus / --audio-dir (default: common audio suffixes)",
    )
    parser.add_argument(
        "--weight-function",
        type=str,
        default=DENSITY_WEIGHT_FUNCTION_DEFAULT,
        choices=("linear", "log", "power"),
        help=(
            "Weighting algorithm used by Stage 2 to fold each component "
            "sheet's per-row amplitudes into a band-level density "
            "(linear: SUM(Amplitude_raw); log: LOG10(1 + SUM(Amplitude_raw)); "
            "power: SUM(Power_raw) or SUM(Amplitude_raw**2)). "
            f"Default: {DENSITY_WEIGHT_FUNCTION_DEFAULT}."
        ),
    )
    parser.add_argument(
        "--fft-policy",
        type=str,
        default=FFT_POLICY_DEFAULT,
        choices=("fixed", "adaptive_tier"),
        help=(
            "FFT sizing: fixed (default, one n_fft/hop for every note) or "
            "adaptive_tier (legacy per-f0 window table)."
        ),
    )
    parser.add_argument(
        "--fixed-n-fft",
        type=int,
        default=FIXED_N_FFT_DEFAULT,
        help=f"n_fft when --fft-policy=fixed (default {FIXED_N_FFT_DEFAULT}).",
    )
    parser.add_argument(
        "--fixed-hop-length",
        type=int,
        default=FIXED_HOP_LENGTH_DEFAULT,
        help=f"hop_length when --fft-policy=fixed (default {FIXED_HOP_LENGTH_DEFAULT}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    _reject_legacy_cli_flags(argv)

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        stages = parse_stages(args.stages)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2

    out_dir = Path(args.out or args.main_output)
    corpus = Path(args.corpus or args.audio_dir) if (args.corpus or args.audio_dir) else None

    audio_files: list[Path] = []
    if args.audio_files:
        for f in args.audio_files:
            p = Path(f)
            if p.exists():
                audio_files.append(p)
            else:
                print(f"Warning: File not found: {f}")

    if corpus is not None:
        if not corpus.exists():
            print(f"Error: Directory not found: {corpus}")
            return 1
        if corpus.is_dir():
            audio_files.extend(discover_corpus_audio(corpus, args.pattern))

    stage1_search_root = None
    if 1 not in stages:
        if corpus is not None and looks_like_stage1_root(corpus):
            stage1_search_root = corpus
        elif looks_like_stage1_root(out_dir):
            stage1_search_root = out_dir

    if 1 in stages and not audio_files:
        current_dir = Path.cwd()
        audio_files = discover_corpus_audio(current_dir, args.pattern or "*.wav")
        if audio_files:
            print(f"Found {len(audio_files)} audio files in current directory")
        else:
            print("Error: No audio files found.")
            print("Please specify files or use --corpus / --audio-dir")
            parser.print_help()
            return 1

    if 1 in stages:
        print(f"Processing {len(audio_files)} audio file(s)...")
        print(
            f"Files: {[f.name for f in audio_files[:5]]}"
            f"{'...' if len(audio_files) > 5 else ''}"
        )
    else:
        print(
            f"Re-export stages {','.join(str(s) for s in stages)} "
            f"from {stage1_search_root or out_dir}"
        )
    print(
        "Pipeline: Stage 1 (per-note spectral analysis) -> "
        "Stage 2 (compilation) -> Stage 3 (research export + EWSD). "
        "Component energy ratios are computed from the current analysis."
    )
    print(f"Output: {out_dir}")
    print(f"Stages: {','.join(str(s) for s in stages)}; figures={bool(args.figures)}")

    try:
        orchestrator = RobustOrchestrator(
            audio_files=audio_files,
            main_analysis_output_dir=out_dir,
            weight_function=args.weight_function,
            stage1_search_root=stage1_search_root,
            figures=bool(args.figures),
            fft_policy=str(args.fft_policy),
            fixed_n_fft=int(args.fixed_n_fft),
            fixed_hop_length=int(args.fixed_hop_length),
        )
        results = orchestrator.run_selected_stages(
            stages,
            figures=bool(args.figures),
            corpus=corpus or stage1_search_root,
        )

        print("\n" + "=" * 80)
        print("PIPELINE SUMMARY")
        print("=" * 80)
        print(f"Status: {results['status']}")
        print(f"Audio Files: {results['audio_files_count']}")
        if results.get("run_manifest"):
            print(f"Run manifest: {results['run_manifest']}")

        for stage_name, stage_result in results["stages"].items():
            status = "OK" if stage_result.get("success") else "FAIL"
            print(f"{stage_name}: {status}")
            if "results_count" in stage_result:
                print(f"  -> Results: {stage_result['results_count']}")
            if "compiled_workbook" in stage_result and stage_result["compiled_workbook"]:
                print(f"  -> Compiled workbook: {stage_result['compiled_workbook']}")
            if stage_result.get("research_workbook"):
                print(f"  -> Research workbook: {stage_result['research_workbook']}")

        print("=" * 80)

        return 0 if results["status"] == "success" else 1

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
