#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sensitivity analysis for harmonic/inharmonic/subbass "mass" metrics.
Runs the SuperAudioAnalyzer with controlled parameter sweeps and exports CSV.
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd
import soundfile as sf
import matplotlib.pyplot as plt
import hashlib

import sys

ROOT = Path(__file__).resolve().parent.parent
ANALYZER_DIR = ROOT / "audio_analysis"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ANALYZER_DIR))

from super_audio_analyzer import SuperAudioAnalyzer  # type: ignore


def _time_vector(sr: int, duration: float) -> np.ndarray:
    n_samples = int(sr * duration)
    return np.linspace(0.0, duration, n_samples, endpoint=False)


def _normalize_peak(signal: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
    peak = np.max(np.abs(signal)) if signal.size else 0.0
    if peak <= 0:
        return signal
    return (signal / peak) * target_peak


def _generate_signal(signal_type: str, sr: int, duration: float) -> np.ndarray:
    t = _time_vector(sr, duration)
    if signal_type == "sine":
        signal = np.sin(2.0 * np.pi * 440.0 * t)
    elif signal_type == "harmonic":
        signal = (
            1.0 * np.sin(2.0 * np.pi * 220.0 * t)
            + 0.6 * np.sin(2.0 * np.pi * 440.0 * t)
            + 0.3 * np.sin(2.0 * np.pi * 660.0 * t)
        )
    elif signal_type == "inharmonic":
        signal = (
            1.0 * np.sin(2.0 * np.pi * 220.0 * t)
            + 0.5 * np.sin(2.0 * np.pi * 440.0 * t)
            + 0.7 * np.sin(2.0 * np.pi * 352.0 * t)
        )
    elif signal_type == "subbass_mix":
        signal = (
            1.0 * np.sin(2.0 * np.pi * 440.0 * t)
            + 0.5 * np.sin(2.0 * np.pi * 880.0 * t)
            + 0.3 * np.sin(2.0 * np.pi * 110.0 * t)
        )
    else:
        raise ValueError(f"Unknown signal_type: {signal_type}")
    return _normalize_peak(signal)


def _run_minimal_analysis(audio_path: Path, sample_rate: int, params: Dict[str, Any]) -> Dict[str, Any]:
    analyzer = SuperAudioAnalyzer(
        audio_path=audio_path,
        output_dir=audio_path.parent / params["run_id"],
        sample_rate=sample_rate,
        use_90_tier=params["use_90_tier"],
        harmonic_tolerance=params["harmonic_tolerance"],
        window=params["window"],
        use_adaptive_tolerance=params["use_adaptive_tolerance"],
        auto_extract_weights=params["auto_extract_weights"],
        harmonic_weight=params["harmonic_weight"],
        inharmonic_weight=params["inharmonic_weight"],
    )
    analyzer.noise_floor_db = params["noise_floor_db"]
    analyzer.load_audio()
    analyzer.compute_spectrogram()
    analyzer.detect_fundamental_frequency()
    analyzer.separate_harmonic_inharmonic()
    analyzer.calculate_spectral_metrics()
    return analyzer.results


def main() -> None:
    parser = argparse.ArgumentParser(description="Sensitivity analysis for fatness metrics.")
    parser.add_argument("--audio", type=Path, default=None, help="Optional input audio file")
    parser.add_argument("--signal-type", type=str, default="harmonic",
                        choices=["sine", "harmonic", "inharmonic", "subbass_mix"])
    parser.add_argument("--sample-rate", type=int, default=22050)
    parser.add_argument("--duration", type=float, default=1.0)
    parser.add_argument("--output-dir", type=Path, default=Path("sensitivity_results"))
    parser.add_argument("--no-plots", action="store_true", help="Skip plot generation")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.audio:
        audio_path = args.audio
    else:
        signal = _generate_signal(args.signal_type, args.sample_rate, args.duration)
        audio_path = args.output_dir / f"reference_{args.signal_type}.wav"
        sf.write(audio_path, signal.astype(np.float32), args.sample_rate)

    param_grid = {
        "window": ["hann", "blackmanharris"],
        "harmonic_tolerance": [0.02, 0.03, 0.05],
        "use_adaptive_tolerance": [True, False],
        "noise_floor_db": [-80.0, -60.0],
        "use_90_tier": [False],
        "auto_extract_weights": [True],
        "harmonic_weight": [0.9],
        "inharmonic_weight": [0.1],
    }

    keys = list(param_grid.keys())
    combos = list(itertools.product(*(param_grid[k] for k in keys)))

    rows = []
    for idx, combo in enumerate(combos, start=1):
        params = dict(zip(keys, combo))
        params["run_id"] = f"run_{idx:03d}"
        results = _run_minimal_analysis(audio_path, args.sample_rate, params)

        stats = results.get("spectral_component_stats", {})
        row = {
            "run_id": params["run_id"],
            "audio_path": str(audio_path),
            "fundamental_freq": results.get("fundamental_freq"),
            "harmonic_energy_pct_musical": stats.get("harmonic_energy_pct_musical"),
            "inharmonic_energy_pct_musical": stats.get("inharmonic_energy_pct_musical"),
            "subbass_energy_pct_global": stats.get("subbass_energy_pct_global"),
            "total_inharm_energy_pct_global": stats.get("total_inharm_energy_pct_global"),
            "mean_harmonic": stats.get("harmonic_energy_mean"),
            "mean_inharmonic": stats.get("inharmonic_energy_mean"),
            "mean_subbass": stats.get("subbass_energy_mean"),
            "mean_total_inharm": stats.get("total_inharm_energy_mean"),
        }
        row.update(params)
        rows.append(row)

    df = pd.DataFrame(rows)
    out_csv = args.output_dir / "sensitivity_results.csv"
    df.to_csv(out_csv, index=False)

    out_json = args.output_dir / "sensitivity_params.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(param_grid, f, indent=2)

    if not args.no_plots and not df.empty:
        plots_dir = args.output_dir / "plots"
        plots_dir.mkdir(parents=True, exist_ok=True)
        metrics = [
            "harmonic_energy_pct_musical",
            "inharmonic_energy_pct_musical",
            "subbass_energy_pct_global",
            "total_inharm_energy_pct_global",
            "mean_harmonic",
            "mean_inharmonic",
            "mean_subbass",
            "mean_total_inharm",
        ]
        for param in keys:
            for metric in metrics:
                if metric not in df.columns:
                    continue
                fig = plt.figure(figsize=(8, 4))
                ax = fig.add_subplot(111)
                df.boxplot(column=metric, by=param, ax=ax)
                ax.set_title(f"{metric} vs {param}")
                ax.set_xlabel(param)
                ax.set_ylabel(metric)
                fig.suptitle("")
                fig.tight_layout()
                out_path = plots_dir / f"{metric}_by_{param}.png"
                fig.savefig(out_path, dpi=200)
                plt.close(fig)

        # Save plot metadata (parameters + hash)
        meta = {
            "analysis_date": pd.Timestamp.utcnow().isoformat(),
            "param_grid": param_grid,
            "n_runs": int(len(df)),
            "metrics": metrics,
            "parameters": keys,
        }
        meta_bytes = json.dumps(meta, sort_keys=True, default=str).encode("utf-8")
        meta["analysis_parameters_hash"] = hashlib.sha256(meta_bytes).hexdigest()
        with open(plots_dir / "plot_metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    print(f"Saved sensitivity results to: {out_csv}")
    print(f"Saved parameter grid to: {out_json}")
    if not args.no_plots:
        print(f"Saved plots to: {plots_dir}")


if __name__ == "__main__":
    main()
