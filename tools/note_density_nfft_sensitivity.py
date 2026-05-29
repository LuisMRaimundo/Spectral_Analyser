"""Opt-in n_fft (window/resolution) sensitivity for ``note_density_final``.

This is a SEPARATE, opt-in study tool. It is intentionally NOT part of the main
per-note pipeline because it re-analyses each note at several FFT resolutions,
which multiplies per-note runtime. Use it to report, for one or more notes, how
much ``note_density_final`` moves under reasonable analysis-resolution
perturbations — the window/n_fft component of the uncertainty quantification
that complements the per-note bootstrap CI (which propagates partials + ratios).

Example
-------
    python tools/note_density_nfft_sensitivity.py path/to/note.wav \
        --nffts 8192 16384 32768 --weight-function log

The metric is comparable across n_fft only within the SAME analysis profile
(weight function + ceiling), so the same ``--weight-function`` is applied to
every resolution.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import pandas as pd

# Allow running as a script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from density_uncertainty import nfft_sensitivity  # noqa: E402


def _note_density_final_for_nfft(
    wav_path: Path,
    n_fft: int,
    *,
    weight_function: str,
    freq_max: float,
    work_root: Path,
) -> float:
    """Run one note through the pipeline at ``n_fft`` and return note_density_final."""
    from proc_audio import AudioProcessor
    import compile_metrics as cm

    run = work_root / f"run_{wav_path.stem}_{n_fft}"
    ap = AudioProcessor()
    ap.load_audio_files([str(wav_path)])
    ap.apply_filters_and_generate_data(
        results_directory=run / "stage1",
        n_fft=int(n_fft),
        zero_padding=2,
        freq_max=float(freq_max),
        dissonance_enabled=False,
        dissonance_curve=False,
        dissonance_scale=False,
        compare_models=False,
        compile_per_call=False,
        parallel_processing=False,
    )
    out_xlsx = run / "compiled_density_metrics.xlsx"
    cm.compile_density_metrics_with_pca(
        folder_path=run / "stage1",
        output_path=out_xlsx,
        file_pattern="spectral_analysis.xlsx",
        include_pca=False,
        weight_function=str(weight_function),
    )
    wb = next(run.rglob("compiled_density_metrics*.xlsx"))
    dm = pd.read_excel(wb, sheet_name="Density_Metrics")
    return float(pd.to_numeric(dm.iloc[0]["note_density_final"], errors="coerce"))


def compute_nfft_sensitivity_for_wav(
    wav_path: Path,
    n_ffts: Sequence[int],
    *,
    weight_function: str = "log",
    freq_max: float = 20000.0,
    work_root: Path | None = None,
) -> Dict[str, object]:
    """Compute ``note_density_final`` across ``n_ffts`` and summarise dispersion."""
    created_tmp = False
    if work_root is None:
        work_root = Path(tempfile.mkdtemp(prefix="nfft_sens_"))
        created_tmp = True
    values_by_nfft: Dict[int, float] = {}
    for n_fft in n_ffts:
        values_by_nfft[int(n_fft)] = _note_density_final_for_nfft(
            wav_path, int(n_fft),
            weight_function=weight_function,
            freq_max=freq_max,
            work_root=work_root,
        )
    summary = nfft_sensitivity(values_by_nfft)
    return {
        "wav": str(wav_path),
        "weight_function": weight_function,
        "values_by_nfft": values_by_nfft,
        "sensitivity": summary,
        "work_root": str(work_root) if not created_tmp else "(temp)",
    }


def _iter_wavs(paths: Iterable[str]) -> List[Path]:
    out: List[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            out.extend(sorted(path.rglob("*.wav")))
        elif path.suffix.lower() == ".wav":
            out.append(path)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="WAV file(s) or directory(ies).")
    parser.add_argument(
        "--nffts", type=int, nargs="+", default=[8192, 16384, 32768],
        help="FFT sizes to evaluate (default: 8192 16384 32768).",
    )
    parser.add_argument("--weight-function", default="log", help="Profile weight key (default: log).")
    parser.add_argument("--freq-max", type=float, default=20000.0, help="Analysis ceiling Hz.")
    args = parser.parse_args(argv)

    wavs = _iter_wavs(args.inputs)
    if not wavs:
        parser.error("no .wav inputs found")
    results = [
        compute_nfft_sensitivity_for_wav(
            wav, args.nffts,
            weight_function=args.weight_function,
            freq_max=args.freq_max,
        )
        for wav in wavs
    ]
    print(json.dumps(results, indent=2, default=float))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
