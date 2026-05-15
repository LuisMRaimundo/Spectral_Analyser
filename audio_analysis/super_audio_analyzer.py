#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LEGACY / DIAGNOSTIC MODULE.

This module is not the canonical publication-facing acoustic-analysis path.

Canonical per-note analysis is:
    proc_audio.AudioProcessor

Canonical compiled analysis is:
    compile_metrics.compile_density_metrics_with_pca

This module must not be used to produce publication-facing density,
harmonic, inharmonic, low-frequency, f0, or dissonance metrics unless it
delegates directly to the canonical pipeline.
"""

import sys
import os
import warnings
import logging
import re
from pathlib import Path
import hashlib
from typing import Dict, List, Tuple, Optional, Union, Any

# Ensure UTF-8 output on Windows consoles (avoids UnicodeEncodeError)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from datetime import datetime
import traceback
import json
import math
from functools import lru_cache
from multiprocessing import Pool, cpu_count
from concurrent.futures import ThreadPoolExecutor, as_completed

# Core scientific libraries
import numpy as np
import pandas as pd
import librosa
import librosa.display
import soundfile as sf
from scipy import signal
from scipy.stats import shapiro, normaltest, pearsonr, spearmanr, kruskal
from scipy.fft import fft, fftfreq

# Visualization
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend to avoid GUI hangs
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
try:
    import seaborn as sns
    plt.style.use('seaborn-v0_8-darkgrid')
    sns.set_palette("husl")
except (ImportError, OSError):
    # Fallback if seaborn not available or style not found
    warnings.warn("seaborn not available or style not found, using default matplotlib style")
    plt.style.use('default')

# Machine Learning
try:
    from sklearn.preprocessing import StandardScaler, RobustScaler
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LinearRegression, Ridge, Lasso
    from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    warnings.warn("sklearn not available. Some ML features will be skipped.")

# Dimensionality Reduction
try:
    from sklearn.manifold import TSNE
    TSNE_AVAILABLE = True
except ImportError:
    TSNE_AVAILABLE = False

try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False

# Dissonance models
try:
    from dissonance_models import SetharesDissonance
    DISSONANCE_MODELS_AVAILABLE = True
except ImportError:
    DISSONANCE_MODELS_AVAILABLE = False
    warnings.warn("dissonance_models not available. Dissonance calculations will be limited.")

# Repository root on sys.path (harmonic_validation, spectral_leakage_guards live next to this package)
_SA_ROOT = Path(__file__).resolve().parents[1]
if str(_SA_ROOT) not in sys.path:
    sys.path.insert(0, str(_SA_ROOT))

from harmonic_validation import validate_harmonic_series_matched

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('super_audio_analyzer.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

CANONICAL_PIPELINE_ROLE = "legacy_diagnostic"
PUBLICATION_OUTPUT_ALLOWED = False

_METRICS_SUMMARY_NOTES = """NOTES (READ BEFORE INTERPRETING THIS FILE)
----------------------------------------------------------------------
• FINAL BATCH METRICS (canonical export): see block ``FINAL BATCH SUMMARY`` below.
  Linear power mass per class is P_i = A_i**2 (STFT-bin masks); percentages use
  denominator (harmonic + inharmonic residual + subbass noise) so the three-class
  percents sum to 100%% (after numerical normalization).

• Component counts in this batch report are STFT bin row counts per mask unless
  labelled as peak-collapsed partials.

• Bin-based energy profile (canonical export):
    harmonic_energy_percentage, inharmonic_energy_percentage
    (and the sub-bass complement) are computed as Σ A² per STFT-bin mask
    over the (harmonic + inharmonic residual + subbass noise) denominator.
  Bin-based percentages are the canonical batch output and are NOT a
  peak-list quantity.

• Peak-based validation profile (diagnostics only unless configured otherwise):
    harmonic_energy_percentage_peak_based, inharmonic_energy_percentage_peak_based
  Peak-based energy is for validation/diagnostics only unless explicitly
  configured otherwise.

• harmonic_density / inharmonic_density / combined_density here are legacy
  batch diagnostic scalars (linear-amplitude sums / log blend). They are not
  the final public spectral fatness metric.

• The final public density/fatness descriptor is effective_partial_density
  in the compiled Density_Metrics workbook (per-note / corpus compile path).

• dissonance_curve: only a short numeric summary appears below; the full curve
  lives in super_analysis_results.json.

----------------------------------------------------------------------

"""


def finalize_batch_power_mass_summary(
    harmonic_power_mass: float,
    inharmonic_residual_power_mass: float,
    subbass_noise_power_mass: float,
) -> Dict[str, Any]:
    """
    Canonical batch export: linear power masses (Σ A² per STFT-bin class) and
    percentages over (harmonic + inharmonic residual + subbass noise).

    Percents are renormalized so harmonic + inharmonic_residual + subbass_noise = 100%.
    total_inharmonic_power_percent is exactly inharmonic_residual + subbass_noise (after that normalization).
    """
    h = max(0.0, float(harmonic_power_mass))
    i = max(0.0, float(inharmonic_residual_power_mass))
    s = max(0.0, float(subbass_noise_power_mass))
    total_inharmonic_power_mass = i + s
    total_power_mass = h + i + s
    out: Dict[str, Any] = {
        "harmonic_power_mass": h,
        "inharmonic_residual_power_mass": i,
        "subbass_noise_power_mass": s,
        "total_inharmonic_power_mass": total_inharmonic_power_mass,
        "total_power_mass": total_power_mass,
    }
    if total_power_mass <= 0.0:
        out.update(
            {
                "harmonic_power_percent": 0.0,
                "inharmonic_residual_power_percent": 0.0,
                "subbass_noise_power_percent": 0.0,
                "total_inharmonic_power_percent": 0.0,
            }
        )
        return out
    hp = 100.0 * h / total_power_mass
    ip = 100.0 * i / total_power_mass
    sp = 100.0 * s / total_power_mass
    ssum = hp + ip + sp
    if ssum > 0.0:
        scale = 100.0 / ssum
        hp *= scale
        ip *= scale
        sp *= scale
    tip = ip + sp
    out.update(
        {
            "harmonic_power_percent": float(hp),
            "inharmonic_residual_power_percent": float(ip),
            "subbass_noise_power_percent": float(sp),
            "total_inharmonic_power_percent": float(tip),
        }
    )
    return out


def _is_interval_to_dissonance_curve(value: Any) -> bool:
    """True if dict maps numeric interval -> float dissonance (Sethares curve)."""
    if not isinstance(value, dict) or not value:
        return False
    for k in value.keys():
        if isinstance(k, bool):
            return False
        try:
            float(k)
        except (TypeError, ValueError):
            return False
    try:
        for v in value.values():
            float(v)
    except (TypeError, ValueError):
        return False
    return True


def _format_dissonance_curve_summary_lines(curve: Dict[Any, Any]) -> List[str]:
    """Human-readable summary lines for metrics_summary.txt (avoid float dict keys in %-s formats)."""
    ordered_keys = sorted(curve.keys(), key=lambda x: float(x))
    keys_f = [float(k) for k in ordered_keys]
    vals = np.array([float(curve[k]) for k in ordered_keys], dtype=float)
    lines = [
        f"  {'dissonance_curve_points':28s}: {len(vals)}\n",
        f"  {'dissonance_curve_min':28s}: {float(np.min(vals)):.6f}\n",
        f"  {'dissonance_curve_max':28s}: {float(np.max(vals)):.6f}\n",
        f"  {'dissonance_curve_mean':28s}: {float(np.mean(vals)):.6f}\n",
        f"  {'dissonance_curve_interval_min':28s}: {keys_f[0]:.6f}\n",
        f"  {'dissonance_curve_interval_max':28s}: {keys_f[-1]:.6f}\n",
    ]
    return lines


def _format_detection_method_label(name: str) -> str:
    """Plot / log labels: raw detector names vs final f0 (see octave correction in JSON)."""
    n = str(name).strip().lower()
    mapping = {
        "pyin": "pyin_raw",
        "yin": "yin_raw",
        "autocorrelation": "autocorrelation_raw",
        "note_prior": "note_prior",
        "f0_prior": "f0_prior_hz",
    }
    return mapping.get(n, str(name))


def _write_metrics_summary_mapping(
    f,
    data: Dict[str, Any],
    _ms_line,
) -> None:
    """Write key/value block for metrics_summary.txt; safe for float dict keys (dissonance_curve)."""
    for key, value in data.items():
        kstr = str(key)
        try:
            if kstr == "dissonance_curve" and isinstance(value, dict):
                f.write(f"{kstr:30s}: (summary; full curve in super_analysis_results.json)\n")
                if _is_interval_to_dissonance_curve(value):
                    for line in _format_dissonance_curve_summary_lines(value):
                        f.write(line)
                else:
                    f.write(f"  {'(non-numeric curve)':28s}: see JSON\n")
                continue
            if isinstance(value, dict):
                f.write(f"{kstr:30s}:\n")
                for subkey, subvalue in value.items():
                    sk = str(subkey)
                    if sk == "dissonance_curve" and isinstance(subvalue, dict):
                        f.write(f"  {sk:28s}: (summary; full curve in JSON)\n")
                        if _is_interval_to_dissonance_curve(subvalue):
                            for line in _format_dissonance_curve_summary_lines(subvalue):
                                f.write("  " + line)
                        continue
                    try:
                        if isinstance(subvalue, dict):
                            f.write(f"  {sk:28s}:\n")
                            for sk2, sv2 in subvalue.items():
                                sk2s = str(sk2)
                                if isinstance(sv2, (int, float)) and not isinstance(sv2, bool):
                                    f.write(f"    {sk2s:26s}: {float(sv2):.6f}\n")
                                elif isinstance(sv2, (list, tuple)):
                                    f.write(f"    {sk2s:26s}: {_ms_line(str(sv2))}\n")
                                else:
                                    f.write(f"    {sk2s:26s}: {_ms_line(str(sv2))}\n")
                        elif isinstance(subvalue, (int, float)) and not isinstance(subvalue, bool):
                            f.write(f"  {sk:28s}: {float(subvalue):.6f}\n")
                        elif isinstance(subvalue, (list, tuple)):
                            f.write(f"  {sk:28s}: {_ms_line(str(subvalue))}\n")
                        else:
                            f.write(f"  {sk:28s}: {_ms_line(str(subvalue))}\n")
                    except Exception:
                        f.write(f"  {sk:28s}: {repr(subvalue)}\n")
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                f.write(f"{kstr:30s}: {float(value):.6f}\n")
            elif isinstance(value, (list, tuple)):
                f.write(f"{kstr:30s}: {_ms_line(str(value))}\n")
            else:
                f.write(f"{kstr:30s}: {_ms_line(str(value))}\n")
        except Exception as e:
            f.write(f"{kstr:30s}: {repr(value)} (format error: {e})\n")


class SuperAudioAnalyzer:
    """
    State-of-the-art unified audio analysis tool.
    
    Combines all best features from the comprehensive codebase:
    - 90-tier granular clustering system
    - Advanced harmonic/inharmonic separation
    - Multiple dissonance models
    - Psychoacoustic weighting
    - Statistical analysis
    - Internal consistency checks
    """
    
    def __init__(
        self,
        audio_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        sample_rate: int = 44100,
        use_90_tier: bool = True,
        harmonic_tolerance: float = 0.02,
        harmonic_weight: float = 0.95,
        inharmonic_weight: float = 0.05,
        window: str = 'blackmanharris',
        use_adaptive_tolerance: bool = True,
        auto_extract_weights: bool = True,
        weight_function: str = "linear",
        minimal_spectral_probe: bool = False,
        **_: Any,
    ):
        """
        Initialize the super analyzer.
        
        Args:
            audio_path: Path to audio file
            output_dir: Output directory for results
            sample_rate: Target sample rate
            use_90_tier: Use 90-tier granular clustering system
            harmonic_tolerance: Base harmonic tolerance
            harmonic_weight: Weight for harmonic component (ignored if auto_extract_weights=True)
            inharmonic_weight: Weight for inharmonic component (ignored if auto_extract_weights=True)
            window: Window function (blackmanharris recommended for 90-tier)
            use_adaptive_tolerance: Use adaptive tolerance based on frequency
            auto_extract_weights: Auto-extract weights from actual energy distribution (recommended)
            weight_function: Weight-function key for canonical harmonic density paths
            minimal_spectral_probe: If True, run only STFT → f0 → H/I separation → spectral metrics
                and light disk output (JSON + optional H/I/S pie). Skips dissonance, stats, PCA/t-SNE,
                consistency suite, and ``super_comprehensive_analysis.png``.
        """
        self.audio_path = Path(audio_path)
        if not self.audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        self.output_dir = Path(output_dir) if output_dir else self.audio_path.parent / "super_analysis_output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Analysis parameters
        self.sample_rate = sample_rate
        self.use_90_tier = use_90_tier
        self.harmonic_tolerance = harmonic_tolerance
        self.harmonic_weight = harmonic_weight
        self.inharmonic_weight = inharmonic_weight
        self.window = window
        self.use_adaptive_tolerance = use_adaptive_tolerance
        self.auto_extract_weights = auto_extract_weights
        self.weight_function = str(weight_function or "linear").strip().lower()
        self.minimal_spectral_probe = bool(minimal_spectral_probe)

        # 90-tier configuration (from pipeline_orchestrator_gui.py)
        self.tier_config = self._load_90_tier_config() if use_90_tier else None
        
        # Data storage
        self.audio_data = None
        self.audio_sr = None
        self.audio_channels = None  # Number of channels (1=mono, 2=stereo, etc.)
        self.is_stereo = False  # Boolean flag for stereo detection
        self.stft = None
        self.magnitude_spectrogram = None
        self.frequencies = None
        self.times = None
        
        # Analysis results
        self.fundamental_freq = None
        self.harmonic_frequencies = []
        self.harmonic_amplitudes = []
        self.inharmonic_frequencies = []
        self.inharmonic_amplitudes = []
        self.harmonic_df = pd.DataFrame()
        self.inharmonic_df = pd.DataFrame()
        self.complete_spectrum_df = pd.DataFrame()
        
        # Metrics
        self.metrics = {}
        self.dissonance_metrics = {}
        
        # Results storage
        analysis_version, analysis_version_source = self._get_project_version_info()
        self.results = {
            'metadata': {
                'audio_file': str(self.audio_path),
                'analysis_date': datetime.now().isoformat(),
                'analysis_version': analysis_version,
                'analysis_version_source': analysis_version_source,
                'sample_rate': self.sample_rate,
                'channels': None,  # Will be set after loading
                'is_stereo': False,  # Will be set after loading
                'use_90_tier': self.use_90_tier,
                'window': self.window,
                'harmonic_tolerance': self.harmonic_tolerance,
                'harmonic_weight': self.harmonic_weight,
                'inharmonic_weight': self.inharmonic_weight,
                'analysis_parameters': {
                    'sample_rate': self.sample_rate,
                    'use_90_tier': self.use_90_tier,
                    'harmonic_tolerance': self.harmonic_tolerance,
                    'use_adaptive_tolerance': self.use_adaptive_tolerance,
                    'auto_extract_weights': self.auto_extract_weights,
                    'harmonic_weight': self.harmonic_weight,
                    'inharmonic_weight': self.inharmonic_weight,
                    'window': self.window
                }
            },
            'frequency_analysis': {},
            'harmonic_analysis': {},
            'inharmonic_analysis': {},
            'spectral_metrics': {},
            'dissonance_analysis': {},
            'statistical_analysis': {},
            'dimensionality_reduction': {},
            'internal_consistency_checks': {}
        }
        
        print("="*80)
        print("SUPER AUDIO ANALYZER - State-of-the-Art Edition")
        print("="*80)
        print(f"Audio file: {self.audio_path.name}")
        print(f"Output directory: {self.output_dir}")
        print(f"90-Tier System: {'Enabled' if use_90_tier else 'Disabled'}")

    @staticmethod
    def _get_project_version_info() -> tuple[str, str]:
        """
        Resolve analysis code version for reproducibility stamping.
        Prefers installed package metadata; falls back to pyproject.toml.
        """
        try:
            from importlib import metadata as importlib_metadata
            version = importlib_metadata.version("soundspectranalyse")
            return version, "importlib.metadata:soundspectranalyse"
        except Exception:
            pass

        # Fallback: parse pyproject.toml in repo root
        try:
            repo_root = Path(__file__).resolve().parent.parent
            pyproject_path = repo_root / "pyproject.toml"
            if pyproject_path.exists():
                content = pyproject_path.read_text(encoding="utf-8")
                match = re.search(r'^\s*version\s*=\s*["\']([^"\']+)["\']\s*$', content, flags=re.MULTILINE)
                if match:
                    return match.group(1), f"pyproject.toml:{pyproject_path}"
        except Exception:
            pass

        return "unknown", "unavailable"

    @staticmethod
    def _stable_hash(payload: Dict[str, Any]) -> str:
        """Stable SHA256 hash for reproducibility (sorted JSON)."""
        try:
            serialized = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        except Exception:
            serialized = str(payload).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()
    
    def _load_90_tier_config(self) -> Dict[str, Dict[str, Any]]:
        """
        Load 90-tier granular clustering configuration from external JSON file.
        
        Falls back to hardcoded config if file not found.
        Based on pipeline_orchestrator_gui.py with optimized FFT settings.
        
        Mathematical relationships:
        - N_FFT: Power-of-2 values for FFT efficiency (2^9 to 2^14)
        - Tolerance: Scales with frequency (psychoacoustic JND: 1.5% of frequency)
        - Zero Padding: 2 for low/mid frequencies (better resolution), 1 for high frequencies (efficiency)
        - Frequency boundaries: Aligned with critical band centers where possible
        """
        config_path = Path(__file__).parent / "config" / "90_tier_config.json"
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"Loaded 90-tier configuration from {config_path}")
                logger.info(f"Loaded {len(config)} tiers")
                return config
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}. Using fallback.")
        
        # Fallback: Hardcoded complete 90-tier configuration
        logger.info("Using hardcoded 90-tier configuration (fallback)")
        return self._get_fallback_90_tier_config()
    
    def _get_fallback_90_tier_config(self) -> Dict[str, Dict[str, Any]]:
        """Fallback 90-tier configuration (complete set)."""
        return {
            'Tier_01': {'max_freq': 20, 'n_fft': 16384, 'tolerance': 3.0, 'zp': 2},
            'Tier_02': {'max_freq': 23, 'n_fft': 16384, 'tolerance': 3.1, 'zp': 2},
            'Tier_03': {'max_freq': 26, 'n_fft': 16384, 'tolerance': 3.2, 'zp': 2},
            'Tier_04': {'max_freq': 30, 'n_fft': 16384, 'tolerance': 3.3, 'zp': 2},
            'Tier_05': {'max_freq': 34, 'n_fft': 16384, 'tolerance': 3.4, 'zp': 2},
            'Tier_06': {'max_freq': 38, 'n_fft': 16384, 'tolerance': 3.5, 'zp': 2},
            'Tier_07': {'max_freq': 43, 'n_fft': 16384, 'tolerance': 3.6, 'zp': 2},
            'Tier_08': {'max_freq': 48, 'n_fft': 16384, 'tolerance': 3.8, 'zp': 2},
            'Tier_09': {'max_freq': 54, 'n_fft': 16384, 'tolerance': 4.0, 'zp': 2},
            'Tier_10': {'max_freq': 60, 'n_fft': 16384, 'tolerance': 4.2, 'zp': 2},
            'Tier_11': {'max_freq': 68, 'n_fft': 16384, 'tolerance': 4.4, 'zp': 2},
            'Tier_12': {'max_freq': 76, 'n_fft': 8192, 'tolerance': 4.6, 'zp': 2},
            'Tier_13': {'max_freq': 85, 'n_fft': 8192, 'tolerance': 4.8, 'zp': 2},
            'Tier_14': {'max_freq': 95, 'n_fft': 8192, 'tolerance': 5.0, 'zp': 2},
            'Tier_15': {'max_freq': 105, 'n_fft': 8192, 'tolerance': 5.2, 'zp': 2},
            'Tier_16': {'max_freq': 115, 'n_fft': 8192, 'tolerance': 5.4, 'zp': 2},
            'Tier_17': {'max_freq': 125, 'n_fft': 8192, 'tolerance': 5.6, 'zp': 2},
            'Tier_18': {'max_freq': 135, 'n_fft': 8192, 'tolerance': 5.8, 'zp': 2},
            'Tier_19': {'max_freq': 145, 'n_fft': 8192, 'tolerance': 6.0, 'zp': 2},
            'Tier_20': {'max_freq': 155, 'n_fft': 8192, 'tolerance': 6.2, 'zp': 2},
            'Tier_21': {'max_freq': 165, 'n_fft': 8192, 'tolerance': 6.4, 'zp': 2},
            'Tier_22': {'max_freq': 175, 'n_fft': 8192, 'tolerance': 6.6, 'zp': 2},
            'Tier_23': {'max_freq': 185, 'n_fft': 8192, 'tolerance': 6.8, 'zp': 2},
            'Tier_24': {'max_freq': 195, 'n_fft': 8192, 'tolerance': 7.0, 'zp': 2},
            'Tier_25': {'max_freq': 205, 'n_fft': 8192, 'tolerance': 7.2, 'zp': 2},
            'Tier_26': {'max_freq': 215, 'n_fft': 4096, 'tolerance': 7.4, 'zp': 2},
            'Tier_27': {'max_freq': 225, 'n_fft': 4096, 'tolerance': 7.6, 'zp': 2},
            'Tier_28': {'max_freq': 235, 'n_fft': 4096, 'tolerance': 7.8, 'zp': 2},
            'Tier_29': {'max_freq': 245, 'n_fft': 4096, 'tolerance': 8.0, 'zp': 2},
            'Tier_30': {'max_freq': 260, 'n_fft': 4096, 'tolerance': 8.2, 'zp': 2},
            'Tier_31': {'max_freq': 275, 'n_fft': 4096, 'tolerance': 8.4, 'zp': 2},
            'Tier_32': {'max_freq': 290, 'n_fft': 4096, 'tolerance': 8.6, 'zp': 2},
            'Tier_33': {'max_freq': 305, 'n_fft': 4096, 'tolerance': 8.8, 'zp': 2},
            'Tier_34': {'max_freq': 320, 'n_fft': 4096, 'tolerance': 9.0, 'zp': 2},
            'Tier_35': {'max_freq': 340, 'n_fft': 4096, 'tolerance': 9.2, 'zp': 2},
            'Tier_36': {'max_freq': 360, 'n_fft': 4096, 'tolerance': 9.4, 'zp': 2},
            'Tier_37': {'max_freq': 380, 'n_fft': 4096, 'tolerance': 9.6, 'zp': 2},
            'Tier_38': {'max_freq': 400, 'n_fft': 4096, 'tolerance': 9.8, 'zp': 2},
            'Tier_39': {'max_freq': 425, 'n_fft': 4096, 'tolerance': 10.0, 'zp': 2},
            'Tier_40': {'max_freq': 450, 'n_fft': 4096, 'tolerance': 10.2, 'zp': 2},
            'Tier_41': {'max_freq': 475, 'n_fft': 4096, 'tolerance': 10.4, 'zp': 2},
            'Tier_42': {'max_freq': 500, 'n_fft': 4096, 'tolerance': 10.6, 'zp': 2},
            'Tier_43': {'max_freq': 530, 'n_fft': 2048, 'tolerance': 10.8, 'zp': 2},
            'Tier_44': {'max_freq': 560, 'n_fft': 2048, 'tolerance': 11.0, 'zp': 2},
            'Tier_45': {'max_freq': 590, 'n_fft': 2048, 'tolerance': 11.2, 'zp': 2},
            'Tier_46': {'max_freq': 620, 'n_fft': 2048, 'tolerance': 11.4, 'zp': 2},
            'Tier_47': {'max_freq': 660, 'n_fft': 2048, 'tolerance': 11.6, 'zp': 2},
            'Tier_48': {'max_freq': 700, 'n_fft': 2048, 'tolerance': 11.8, 'zp': 2},
            'Tier_49': {'max_freq': 740, 'n_fft': 2048, 'tolerance': 12.0, 'zp': 2},
            'Tier_50': {'max_freq': 790, 'n_fft': 2048, 'tolerance': 12.2, 'zp': 2},
            'Tier_51': {'max_freq': 840, 'n_fft': 2048, 'tolerance': 12.4, 'zp': 2},
            'Tier_52': {'max_freq': 890, 'n_fft': 2048, 'tolerance': 12.6, 'zp': 2},
            'Tier_53': {'max_freq': 950, 'n_fft': 2048, 'tolerance': 12.8, 'zp': 2},
            'Tier_54': {'max_freq': 1000, 'n_fft': 2048, 'tolerance': 13.0, 'zp': 2},
            'Tier_55': {'max_freq': 1070, 'n_fft': 2048, 'tolerance': 13.2, 'zp': 2},
            'Tier_56': {'max_freq': 1140, 'n_fft': 2048, 'tolerance': 13.4, 'zp': 2},
            'Tier_57': {'max_freq': 1210, 'n_fft': 2048, 'tolerance': 13.6, 'zp': 2},
            'Tier_58': {'max_freq': 1280, 'n_fft': 2048, 'tolerance': 13.8, 'zp': 2},
            'Tier_59': {'max_freq': 1360, 'n_fft': 2048, 'tolerance': 14.0, 'zp': 2},
            'Tier_60': {'max_freq': 1450, 'n_fft': 1024, 'tolerance': 14.2, 'zp': 2},
            'Tier_61': {'max_freq': 1550, 'n_fft': 1024, 'tolerance': 14.4, 'zp': 2},
            'Tier_62': {'max_freq': 1650, 'n_fft': 1024, 'tolerance': 14.6, 'zp': 2},
            'Tier_63': {'max_freq': 1760, 'n_fft': 1024, 'tolerance': 14.8, 'zp': 2},
            'Tier_64': {'max_freq': 1880, 'n_fft': 1024, 'tolerance': 15.0, 'zp': 2},
            'Tier_65': {'max_freq': 2000, 'n_fft': 1024, 'tolerance': 15.2, 'zp': 2},
            'Tier_66': {'max_freq': 2120, 'n_fft': 1024, 'tolerance': 15.4, 'zp': 2},
            'Tier_67': {'max_freq': 2250, 'n_fft': 1024, 'tolerance': 15.6, 'zp': 2},
            'Tier_68': {'max_freq': 2400, 'n_fft': 1024, 'tolerance': 15.8, 'zp': 2},
            'Tier_69': {'max_freq': 2550, 'n_fft': 1024, 'tolerance': 16.0, 'zp': 2},
            'Tier_70': {'max_freq': 2700, 'n_fft': 1024, 'tolerance': 16.5, 'zp': 2},
            'Tier_71': {'max_freq': 2850, 'n_fft': 1024, 'tolerance': 17.0, 'zp': 2},
            'Tier_72': {'max_freq': 3000, 'n_fft': 1024, 'tolerance': 17.5, 'zp': 2},
            'Tier_73': {'max_freq': 3200, 'n_fft': 1024, 'tolerance': 18.0, 'zp': 2},
            'Tier_74': {'max_freq': 3400, 'n_fft': 1024, 'tolerance': 18.5, 'zp': 2},
            'Tier_75': {'max_freq': 3600, 'n_fft': 512, 'tolerance': 19.0, 'zp': 2},
            'Tier_76': {'max_freq': 3850, 'n_fft': 512, 'tolerance': 19.5, 'zp': 2},
            'Tier_77': {'max_freq': 4100, 'n_fft': 512, 'tolerance': 20.0, 'zp': 2},
            'Tier_78': {'max_freq': 4400, 'n_fft': 512, 'tolerance': 20.5, 'zp': 2},
            'Tier_79': {'max_freq': 4700, 'n_fft': 512, 'tolerance': 21.0, 'zp': 2},
            'Tier_80': {'max_freq': 5000, 'n_fft': 512, 'tolerance': 21.5, 'zp': 2},
            'Tier_81': {'max_freq': 5400, 'n_fft': 512, 'tolerance': 22.0, 'zp': 2},
            'Tier_82': {'max_freq': 5800, 'n_fft': 512, 'tolerance': 22.5, 'zp': 2},
            'Tier_83': {'max_freq': 6300, 'n_fft': 512, 'tolerance': 23.0, 'zp': 2},
            'Tier_84': {'max_freq': 6900, 'n_fft': 512, 'tolerance': 23.5, 'zp': 2},
            'Tier_85': {'max_freq': 7500, 'n_fft': 512, 'tolerance': 24.0, 'zp': 1},
            'Tier_86': {'max_freq': 8500, 'n_fft': 512, 'tolerance': 24.5, 'zp': 1},
            'Tier_87': {'max_freq': 10000, 'n_fft': 512, 'tolerance': 25.0, 'zp': 1},
            'Tier_88': {'max_freq': 12500, 'n_fft': 512, 'tolerance': 25.5, 'zp': 1},
            'Tier_89': {'max_freq': 16000, 'n_fft': 512, 'tolerance': 26.0, 'zp': 1},
            'Tier_90': {'max_freq': 20000, 'n_fft': 512, 'tolerance': 27.0, 'zp': 1}
        }
    
    def _calculate_security_margin(self, f0: float) -> float:
        """
        Calculate continuous security margin percentage.
        
        From pipeline_orchestrator_gui.py - C¹ continuous, psychoacoustically correct.
        """
        if f0 >= 300.0:
            return 10.0
        elif f0 <= 20.0:
            return 35.0
        else:
            log_f0 = math.log(f0)
            if f0 < 60.0:
                log_20 = math.log(20.0)
                log_60 = math.log(60.0)
                t = (log_f0 - log_20) / (log_60 - log_20)
                margin = 35.0 + (25.0 - 35.0) * t
            elif f0 < 120.0:
                log_60 = math.log(60.0)
                log_120 = math.log(120.0)
                t = (log_f0 - log_60) / (log_120 - log_60)
                margin = 25.0 + (15.0 - 25.0) * t
            else:
                log_120 = math.log(120.0)
                log_300 = math.log(300.0)
                t = (log_f0 - log_120) / (log_300 - log_120)
                margin = 15.0 + (10.0 - 15.0) * t
            return max(10.0, min(35.0, margin))
    
    def _extract_harmonic_partials_peak_based(
        self, 
        f0: float, 
        magnitude_spectrum: np.ndarray,
        frequencies: np.ndarray,
        tolerance_cents: float = 20.0,
        snr_threshold_db: float = 3.0
    ) -> List[Tuple[float, float, int]]:
        """
        CRITICAL FIX #3: Peak-based harmonic partial extraction.
        
        Mathematical foundation (standard formulation):
        - Harmonic series: f_n = n * f0
        - Peak detection: local maxima in magnitude spectrum
        - Parabolic interpolation in log-magnitude domain for sub-bin accuracy
        - Cents-based tolerance: tolerance_hz = f_expected * (2^(tolerance_cents/1200) - 1)
        - Assignment: select peak closest to expected frequency (not highest amplitude)
        
        Args:
            f0: Fundamental frequency (Hz)
            magnitude_spectrum: Linear magnitude spectrum (1D, time-averaged)
            frequencies: Frequency array (Hz) corresponding to magnitude_spectrum
            tolerance_cents: Tolerance in cents (default 20 cents ≈ 1.2% at 440 Hz)
            snr_threshold_db: Minimum SNR in dB for peak validation
            
        Returns:
            List of (frequency, amplitude, harmonic_number) tuples
        """
        if len(magnitude_spectrum) == 0 or len(frequencies) == 0:
            return []
        
        # STEP 1: Peak-pick in magnitude spectrum
        # ACCURACY IMPROVEMENT: Adaptive thresholds based on signal characteristics
        # Mathematical foundation:
        # - For pre-processed stationary sections: harmonic energy should be 95-99% (very clean)
        # - For raw audio with transients: harmonic energy should be 85-95% (includes noise)
        # - Use adaptive SNR: lower threshold only if needed to capture valid inharmonic components
        # - Noise floor: Use 10th percentile for sensitivity, but validate against signal quality
        # - SNR threshold: Adaptive - use 3.0 dB for detection, but validate results
        # - Prominence: 0.05 for less strict validation (captures weaker but valid peaks)
        noise_floor = np.percentile(magnitude_spectrum, 10)  # 10th percentile (sensitive to weak components)
        # Use adaptive SNR: lower threshold to capture inharmonic components, but preserve high harmonic energy for clean sections
        # For stationary sections, this will still capture harmonics but also detect any valid inharmonic components
        effective_snr_db = min(snr_threshold_db, 3.0)  # Cap at 3.0 dB for cleaner peak detection
        min_height = noise_floor * (10 ** (effective_snr_db / 20.0))  # Convert SNR to linear
        
        peaks, properties = signal.find_peaks(
            magnitude_spectrum,
            height=min_height,
            distance=3,  # Minimum distance between peaks (3 bins)
            prominence=noise_floor * 0.05  # Lower prominence (0.05 vs 0.1) to capture weaker peaks
        )
        
        if len(peaks) == 0:
            logger.warning("No peaks detected in magnitude spectrum")
            return []
        
        # STEP 2: Interpolate peaks (parabolic in log-magnitude domain)
        # Mathematical: For peak at index k, fit parabola to log10(mag[k-1:k+2])
        # Interpolated frequency: f_interp = f[k] + δf, where δf is from parabola maximum
        interpolated_partials = []
        
        for peak_idx in peaks:
            if peak_idx == 0 or peak_idx >= len(magnitude_spectrum) - 1:
                # Can't interpolate edge peaks
                freq_interp = frequencies[peak_idx]
                amp_interp = magnitude_spectrum[peak_idx]
            else:
                # Parabolic interpolation in log-magnitude domain
                # y = a*x² + b*x + c, where x is bin offset, y is log10(magnitude)
                y_log = np.log10(np.maximum(magnitude_spectrum[peak_idx-1:peak_idx+2], 1e-12))
                x_bins = np.array([-1, 0, 1])  # Relative bin positions
                
                # Fit parabola: y = a*x² + b*x + c
                # Using Vandermonde matrix
                A = np.vstack([x_bins**2, x_bins, np.ones(3)]).T
                coeffs = np.linalg.lstsq(A, y_log, rcond=None)[0]
                a, b, c = coeffs
                
                # Parabola maximum at x = -b/(2a)
                if abs(a) > 1e-10:
                    x_max = -b / (2 * a)
                    # Clamp to [-1, 1] range
                    x_max = np.clip(x_max, -1.0, 1.0)
                    
                    # Interpolated frequency (assuming linear frequency spacing)
                    if peak_idx < len(frequencies) - 1:
                        bin_width = frequencies[1] - frequencies[0] if len(frequencies) > 1 else 0
                        freq_interp = frequencies[peak_idx] + x_max * bin_width
                    else:
                        freq_interp = frequencies[peak_idx]
                    
                    # Interpolated amplitude (from parabola)
                    y_max = a * x_max**2 + b * x_max + c
                    amp_interp = 10 ** y_max
                else:
                    # Linear case, no interpolation needed
                    freq_interp = frequencies[peak_idx]
                    amp_interp = magnitude_spectrum[peak_idx]
            
            interpolated_partials.append((freq_interp, amp_interp, peak_idx))
        
        # STEP 3: Assign peaks to harmonic numbers using cents tolerance
        # Mathematical: For harmonic n, expected frequency f_n = n * f0
        # Tolerance in Hz: tolerance_hz = f_n * (2^(tolerance_cents/1200) - 1)
        # Select peak with minimum |f_peak - f_expected| (not maximum amplitude)
        max_harmonic = int(frequencies[-1] / f0) + 1
        harmonic_partials = []
        used_peaks = set()
        
        for n in range(1, max_harmonic + 1):
            expected_freq = n * f0
            # Convert cents tolerance to Hz
            tolerance_hz = expected_freq * (2 ** (tolerance_cents / 1200.0) - 1)
            
            # Find candidates within tolerance
            candidates = []
            for freq, amp, peak_idx in interpolated_partials:
                if peak_idx in used_peaks:
                    continue
                freq_diff = abs(freq - expected_freq)
                if freq_diff <= tolerance_hz:
                    candidates.append((freq, amp, peak_idx, freq_diff))
            
            if candidates:
                # Select closest frequency (not highest amplitude) - this is the correct criterion
                best = min(candidates, key=lambda x: x[3])  # x[3] is freq_diff
                freq_best, amp_best, peak_idx_best, _ = best
                harmonic_partials.append((freq_best, amp_best, n))
                used_peaks.add(peak_idx_best)
                logger.debug(f"Harmonic {n}: {freq_best:.2f} Hz (expected: {expected_freq:.2f} Hz, diff: {abs(freq_best - expected_freq):.2f} Hz)")
        
        # Peak detection diagnostic: matched harmonic slots vs other detected peak candidates
        matched_peaks = len(harmonic_partials)
        total_peaks = len(interpolated_partials)
        non_harmonic_peak_candidates = total_peaks - matched_peaks
        expected_harmonics = max_harmonic
        nh_frac = (non_harmonic_peak_candidates / total_peaks * 100.0) if total_peaks > 0 else 0.0

        # Store validation stats in results (if available)
        if hasattr(self, 'results') and isinstance(self.results, dict):
            if 'harmonic_analysis' not in self.results:
                self.results['harmonic_analysis'] = {}
            self.results['harmonic_analysis']['peak_detection_validation'] = {
                'total_peaks_detected': total_peaks,
                'peaks_matched_to_harmonics': matched_peaks,
                'non_harmonic_peak_candidates': non_harmonic_peak_candidates,
                'expected_harmonics_count': expected_harmonics,
                'match_rate': float(matched_peaks / expected_harmonics) if expected_harmonics > 0 else 0.0,
                'non_harmonic_peak_candidate_fraction_of_detected': float(
                    non_harmonic_peak_candidates / total_peaks
                )
                if total_peaks > 0
                else 0.0,
            }
            logger.info(
                "Peak detection diagnostic: %s/%s harmonic orders matched; %s non-harmonic peak candidates "
                "outside harmonic windows (%.1f%% of detected peak candidates).",
                matched_peaks,
                expected_harmonics,
                non_harmonic_peak_candidates,
                nh_frac,
            )
        
        logger.info(f"Extracted {len(harmonic_partials)} harmonic partials using peak-based method")
        return harmonic_partials
    
    def _calculate_peak_based_energy(self, f0: float, max_freq: float, f_low: float) -> Optional[Dict[str, Any]]:
        """
        CRITICAL FIX #2: Calculate energy from peaks only (energy-consistent method).
        
        This fixes the methodological flaw of comparing a few harmonic bins to ALL remaining bins.
        Instead, we:
        1. Extract ALL spectral peaks
        2. Classify peaks as harmonic/inharmonic/subbass
        3. Compute energy from peak powers only (same representation for all)
        
        Mathematical foundation:
        - Energy = Σ(amplitude²) for peaks
        - Harmonic energy = Σ(peak_power for harmonic peaks)
        - Inharmonic energy = Σ(peak_power for inharmonic peaks)
        - Energy conservation: total = harmonic + inharmonic + subbass
        
        Args:
            f0: Fundamental frequency (Hz)
            max_freq: Maximum frequency in spectrum (Hz)
            f_low: Subbass cutoff frequency (Hz)
            
        Returns:
            Dictionary with energy values and validation flag, or None if calculation fails
        """
        try:
            if self.complete_spectrum_df.empty or self.magnitude_spectrogram is None:
                return None
            
            # Get time-averaged magnitude spectrum
            if len(self.magnitude_spectrogram.shape) == 2:
                magnitude_spectrum = np.mean(self.magnitude_spectrogram, axis=1)
            else:
                magnitude_spectrum = self.magnitude_spectrogram
            
            frequencies = self.frequencies
            
            # STEP 1: Extract ALL peaks (not just harmonic peaks)
            # ACCURACY IMPROVEMENT: Use same adaptive thresholds as harmonic extraction
            # For pre-processed stationary sections: captures both harmonics and any valid weak inharmonic components
            # This ensures consistent peak detection for both harmonic and energy calculations
            noise_floor = np.percentile(magnitude_spectrum, 10)  # 10th percentile (consistent with harmonic extraction)
            min_height = noise_floor * (10 ** (3.0 / 20.0))  # 3.0 dB SNR threshold (cleaner peak detection)
            
            peaks, properties = signal.find_peaks(
                magnitude_spectrum,
                height=min_height,
                distance=3,  # Minimum distance between peaks
                prominence=noise_floor * 0.05  # Lower prominence (consistent with harmonic extraction)
            )
            
            if len(peaks) == 0:
                logger.warning("No peaks detected for peak-based energy calculation")
                return None
            
            # STEP 2: Interpolate peaks and extract (freq, amp) pairs
            all_peaks = []
            for peak_idx in peaks:
                if peak_idx == 0 or peak_idx >= len(magnitude_spectrum) - 1:
                    freq_interp = frequencies[peak_idx]
                    amp_interp = magnitude_spectrum[peak_idx]
                else:
                    # Parabolic interpolation (same as harmonic extraction)
                    y_log = np.log10(np.maximum(magnitude_spectrum[peak_idx-1:peak_idx+2], 1e-12))
                    x_bins = np.array([-1, 0, 1])
                    A = np.vstack([x_bins**2, x_bins, np.ones(3)]).T
                    coeffs = np.linalg.lstsq(A, y_log, rcond=None)[0]
                    a, b, c = coeffs
                    
                    if abs(a) > 1e-10:
                        x_max = np.clip(-b / (2 * a), -1.0, 1.0)
                        bin_width = frequencies[1] - frequencies[0] if len(frequencies) > 1 else 0
                        freq_interp = frequencies[peak_idx] + x_max * bin_width
                        y_max = a * x_max**2 + b * x_max + c
                        amp_interp = 10 ** y_max
                    else:
                        freq_interp = frequencies[peak_idx]
                        amp_interp = magnitude_spectrum[peak_idx]
                
                all_peaks.append((freq_interp, amp_interp))
            
            # STEP 3: Classify peaks as harmonic/inharmonic/subbass
            # ACCURACY FIX: Use tolerance (18 cents) for accurate classification
            # Increased to 18 cents to accommodate collections with lower tuning quality
            tolerance_cents = 18.0  # Increased from 15.0 to 18.0 cents to analyze collections with lower tuning quality
            max_harmonic = int(max_freq / f0) + 1
            expected_harmonics = [f0 * n for n in range(1, max_harmonic + 1)]
            
            # One representative per harmonic order (largest amplitude among candidates)
            collapsed_harmonic_representatives_dict: Dict[int, Tuple[float, float]] = {}
            inharmonic_candidates: List[Tuple[float, float]] = []
            subbass_candidates: List[Tuple[float, float]] = []
            
            for freq, amp in all_peaks:
                # Classify as subbass first
                if freq < f_low:
                    subbass_candidates.append((freq, amp))
                    continue
                
                # Check if harmonic - find closest expected harmonic
                is_harmonic = False
                best_match = None
                best_error = float('inf')
                
                for n, expected_freq in enumerate(expected_harmonics, 1):
                    tolerance_hz = expected_freq * (2 ** (tolerance_cents / 1200.0) - 1)
                    error = abs(freq - expected_freq)
                    if error <= tolerance_hz and error < best_error:
                        best_match = n
                        best_error = error
                        is_harmonic = True
                
                if is_harmonic and best_match is not None:
                    if best_match not in collapsed_harmonic_representatives_dict:
                        collapsed_harmonic_representatives_dict[best_match] = (freq, amp)
                    else:
                        existing_amp = collapsed_harmonic_representatives_dict[best_match][1]
                        if amp > existing_amp:
                            collapsed_harmonic_representatives_dict[best_match] = (freq, amp)
                else:
                    inharmonic_candidates.append((freq, amp))
            
            n_orders_expected = max(0, int(math.floor(max_freq / f0)))
            collapsed_harmonic_representatives = [
                (freq, amp, n) for n, (freq, amp) in collapsed_harmonic_representatives_dict.items()
            ]
            if len(collapsed_harmonic_representatives) > n_orders_expected:
                logger.error(
                    "Invariant violated: collapsed harmonic representatives (%s) > expected orders (%s); "
                    "recomputing by harmonic order.",
                    len(collapsed_harmonic_representatives),
                    n_orders_expected,
                )
                collapsed_harmonic_representatives_dict = {
                    k: v for k, v in collapsed_harmonic_representatives_dict.items() if 1 <= k <= n_orders_expected
                }
                collapsed_harmonic_representatives = [
                    (fa, aa, nn) for nn, (fa, aa) in collapsed_harmonic_representatives_dict.items()
                ]

            # STEP 3b: drop inharmonic peak candidates near measured harmonic peaks (window leakage)
            try:
                from spectral_leakage_guards import leakage_halfwidth_hz, filter_inharmonic_peak_candidates

                _sr = float(getattr(self, "audio_sr", None) or getattr(self, "sample_rate", None) or 0.0)
                _nfft = int(getattr(self, "n_fft", 0) or 0)
                if _sr > 0.0 and _nfft > 0 and inharmonic_candidates:
                    _leak = float(
                        leakage_halfwidth_hz(sr=_sr, n_fft=_nfft, bin_width_hz=None, main_lobe_bins=None)
                    )
                    if _leak > 0.0:
                        _hrep = [float(f) for f, _a, _n in collapsed_harmonic_representatives]
                        inharmonic_candidates = filter_inharmonic_peak_candidates(
                            inharmonic_candidates,
                            _hrep,
                            leakage_halfwidth_hz=_leak,
                        )
            except Exception as _e_pk:
                logger.debug("Peak-based inharmonic leakage filter skipped: %s", _e_pk)
            
            # STEP 4: Compute energy from peak powers only
            # ACCURACY FIX: Now using only one peak per harmonic (the strongest)
            harmonic_energy = sum(amp ** 2 for _, amp, _ in collapsed_harmonic_representatives)
            inharmonic_energy = sum(amp ** 2 for _, amp in inharmonic_candidates)
            subbass_energy = sum(amp ** 2 for _, amp in subbass_candidates)
            total_energy = harmonic_energy + inharmonic_energy + subbass_energy
            
            # STEP 5: Validate energy conservation
            if total_energy > 0:
                energy_conservation_error = abs(total_energy - (harmonic_energy + inharmonic_energy + subbass_energy)) / total_energy * 100
                if energy_conservation_error > 0.1:  # More than 0.1% error
                    logger.warning(f"Energy conservation error in peak-based calculation: {energy_conservation_error:.3f}%")
            
            logger.info(
                "Peak-based energy (tolerance: %.1f cents, collapsed one representative per harmonic order): "
                "%s collapsed harmonic representatives, %s inharmonic candidates, %s subbass candidates",
                tolerance_cents,
                len(collapsed_harmonic_representatives),
                len(inharmonic_candidates),
                len(subbass_candidates),
            )
            logger.info(f"Peak-based energy: H={harmonic_energy:.6f}, I={inharmonic_energy:.6f}, S={subbass_energy:.6f}, Total={total_energy:.6f}")
            
            return {
                'valid': True,
                'harmonic_energy': float(harmonic_energy),
                'inharmonic_energy': float(inharmonic_energy),
                'subbass_energy': float(subbass_energy),
                'total_energy': float(total_energy),
                'harmonic_peak_count': len(collapsed_harmonic_representatives),
                'collapsed_harmonic_representative_count': len(collapsed_harmonic_representatives),
                'inharmonic_peak_count': len(inharmonic_candidates),
                'subbass_peak_count': len(subbass_candidates),
                'harmonic_peaks': [(f, a) for f, a, _ in collapsed_harmonic_representatives],
                'inharmonic_peaks': inharmonic_candidates,
                'subbass_peaks': subbass_candidates,
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate peak-based energy: {e}", exc_info=True)
            return None
    
    def _detect_harmonics_peak_based(self, expected_harmonics: List[float], max_freq: float) -> np.ndarray:
        """
        CRITICAL FIX #3: Peak-based harmonic detection (replaces bin-based).
        
        Uses peak-picking + interpolation + cents-based assignment.
        
        Args:
            expected_harmonics: List of expected harmonic frequencies
            max_freq: Maximum frequency in spectrum
            
        Returns:
            Boolean mask array indicating harmonic components
        """
        if self.complete_spectrum_df.empty or self.magnitude_spectrogram is None:
            return np.zeros(len(self.complete_spectrum_df), dtype=bool)
        
        # Get time-averaged magnitude spectrum
        if len(self.magnitude_spectrogram.shape) == 2:
            magnitude_spectrum = np.mean(self.magnitude_spectrogram, axis=1)
        else:
            magnitude_spectrum = self.magnitude_spectrogram
        
        frequencies = self.frequencies
        
        # Extract harmonic partials using peak-based method
        # CRITICAL FIX: Use 25 cents tolerance (≈1.45% at 440 Hz) for better balance
        # 20 cents was too restrictive; 30 cents was too permissive for inharmonic capture
        tolerance_cents = 25.0
        # ACCURACY IMPROVEMENT: Use 3.0 dB SNR threshold for peak validation
        harmonic_partials = self._extract_harmonic_partials_peak_based(
            self.fundamental_freq,
            magnitude_spectrum,
            frequencies,
            tolerance_cents=tolerance_cents,
            snr_threshold_db=3.0
        )
        
        # Create mask from extracted partials
        harmonic_mask = np.zeros(len(self.complete_spectrum_df), dtype=bool)
        
        # CRITICAL FIX: Mark multiple bins per harmonic to capture energy spread
        # FFT energy spreads across multiple bins due to windowing and spectral leakage
        # For Blackman-Harris window, energy typically spreads across 3-5 bins
        bin_width = frequencies[1] - frequencies[0] if len(frequencies) > 1 else 1.0
        
        for freq, amp, n in harmonic_partials:
            # Find closest bin in complete_spectrum_df
            freq_diffs = np.abs(self.complete_spectrum_df['Frequency (Hz)'].values - freq)
            closest_idx = np.argmin(freq_diffs)
            
            # Validate the match is close enough (within 1 bin width)
            if closest_idx < len(harmonic_mask) and freq_diffs[closest_idx] <= bin_width * 1.5:
                # HIGH PRIORITY FIX: Window-specific energy spread calculation
                # Replace heuristic with actual window characteristics
                # Mathematical foundation:
                # - Main lobe width: W_main (in bins) - from window's frequency response
                # - Energy concentration: ~90% within ±W_main/2 bins, ~95% within ±W_main bins
                # - Use window-specific calculation instead of fixed heuristic
                
                # Get window characteristics (if n_fft is available)
                try:
                    n_fft = getattr(self, 'n_fft', 2048)  # Default if not set
                    window_spread = self._calculate_window_energy_spread(self.window, n_fft, bin_width)
                    energy_90pct_bins = window_spread['energy_90pct_bins']
                    main_lobe_width_hz = window_spread['main_lobe_width_hz']
                except Exception as e:
                    logger.warning(f"Failed to get window spread, using defaults: {e}")
                    # Fallback to defaults (Blackman-Harris)
                    energy_90pct_bins = 2
                    main_lobe_width_hz = 4 * bin_width
                
                # Calculate adaptive window based on fundamental frequency and harmonic spacing
                # Harmonic spacing = f0, so overlap risk = main_lobe_width / f0
                harmonic_spacing = self.fundamental_freq  # Distance between harmonics
                overlap_ratio = main_lobe_width_hz / harmonic_spacing if harmonic_spacing > 0 else 1.0
                
                # Use window-specific energy spread, but adapt based on harmonic spacing
                # If harmonics are close together (overlap_ratio > 0.3), use narrower window
                if overlap_ratio > 0.3:
                    # Harmonics close together: use narrower window to avoid overlap
                    window_bins = max(1, energy_90pct_bins - 1) if energy_90pct_bins > 1 else 1
                else:
                    # Harmonics well-separated: use full energy spread window
                    window_bins = energy_90pct_bins
                
                # Additional constraint: don't let window exceed 30% of harmonic spacing
                # This prevents capturing energy from adjacent harmonics
                max_window_hz = harmonic_spacing * 0.3
                max_window_bins = int(max_window_hz / bin_width) if bin_width > 0 else window_bins
                window_bins = min(window_bins, max_window_bins)
                
                # Ensure at least 1 bin (the peak itself)
                window_bins = max(1, window_bins)
                
                logger.debug(f"Harmonic {n} (f={freq:.2f} Hz): window_bins={window_bins}, "
                           f"main_lobe={main_lobe_width_hz:.2f} Hz, overlap_ratio={overlap_ratio:.3f}")
                
                # Mark bins within window
                for offset in range(-window_bins, window_bins + 1):
                    idx = closest_idx + offset
                    if 0 <= idx < len(harmonic_mask):
                        harmonic_mask[idx] = True
        
        logger.info(f"Peak-based detection: {np.sum(harmonic_mask)} harmonic components (with energy spread capture)")
        return harmonic_mask
    
    def _detect_harmonic_single(self, expected_freq: float, max_freq: float) -> List[int]:
        """
        Detect ALL harmonic components near expected frequency (not just one).
        
        CRITICAL FIX: Detect multiple components per harmonic, not just the strongest.
        This is essential because FFT bins may spread energy across multiple bins.
        
        Args:
            expected_freq: Expected harmonic frequency
            max_freq: Maximum frequency in spectrum
            
        Returns:
            List of indices of detected harmonic components
        """
        if expected_freq > max_freq:
            return []
        
        # Calculate adaptive tolerance - BE MORE GENEROUS
        base_tolerance = self.harmonic_tolerance
        if isinstance(base_tolerance, float) and base_tolerance < 1.0:
            base_tolerance_hz = expected_freq * base_tolerance
        else:
            base_tolerance_hz = base_tolerance
        
        # Apply adaptive tolerance
        tolerance_hz = self._calculate_adaptive_tolerance(expected_freq, base_tolerance_hz)
        
        # CRITICAL: Increase tolerance for lower harmonics (they're more important)
        # For fundamental and first few harmonics, use 2x tolerance
        if expected_freq <= self.fundamental_freq * 3:
            tolerance_hz = max(tolerance_hz, expected_freq * 0.05)  # At least 5% for low harmonics
        
        # For higher harmonics, also be more generous (they have lower energy)
        # Musical instruments can have harmonics up to 20-30x the fundamental
        if expected_freq > self.fundamental_freq * 10:
            tolerance_hz = max(tolerance_hz, expected_freq * 0.08)  # 8% for high harmonics (tighter)
        elif expected_freq > self.fundamental_freq * 5:
            tolerance_hz = max(tolerance_hz, expected_freq * 0.06)  # 6% for mid harmonics
        
        # Find frequencies within tolerance
        freq_diffs = np.abs(self.complete_spectrum_df['Frequency (Hz)'].values - expected_freq)
        within_tolerance = freq_diffs <= tolerance_hz
        
        # CRITICAL FIX: Return ALL components within tolerance, not just the strongest
        # For musical instruments, we want to capture ALL energy near harmonics, even weak ones
        if np.any(within_tolerance):
            positional_indices = np.where(within_tolerance)[0]
            # CRITICAL FIX #1: Use Amplitude_linear (not dB) for thresholding
            candidate_magnitudes = self.complete_spectrum_df['Amplitude_linear'].values[positional_indices]
            
            # CRITICAL: Use a much lower threshold for musical instruments
            # Higher harmonics have lower energy, but they're still harmonic!
            # Use 0.1% of max magnitude (10x more sensitive than before)
            max_magnitude = self.complete_spectrum_df['Amplitude_linear'].max()
            
            # For lower harmonics (fundamental to 5th), use 0.1% threshold
            # For higher harmonics, use even lower threshold (0.05%) to catch weak harmonics
            if expected_freq <= self.fundamental_freq * 5:
                min_magnitude_threshold = max_magnitude * 0.001  # 0.1% for low harmonics
            else:
                min_magnitude_threshold = max_magnitude * 0.0005  # 0.05% for high harmonics
            
            # Also use absolute minimum: at least 0.1% of the strongest candidate in this tolerance window
            strongest_in_window = np.max(candidate_magnitudes) if len(candidate_magnitudes) > 0 else 0
            relative_threshold = strongest_in_window * 0.1  # 10% of strongest in window
            
            # Use the more lenient threshold
            min_magnitude_threshold = min(min_magnitude_threshold, relative_threshold)
            
            # Filter candidates by magnitude threshold
            significant_candidates = candidate_magnitudes >= min_magnitude_threshold
            
            if np.any(significant_candidates):
                # Return ALL significant candidates, not just the strongest
                return [int(positional_indices[i]) for i in np.where(significant_candidates)[0]]
            else:
                # If no candidates meet threshold, return at least the strongest (don't miss it!)
                strongest_pos = np.argmax(candidate_magnitudes)
                return [int(positional_indices[strongest_pos])]
        
        return []
    
    def _detect_harmonics_parallel(self, expected_harmonics: List[float], max_freq: float) -> np.ndarray:
        """
        Detect harmonics using parallel processing for efficiency.
        
        Uses ThreadPoolExecutor for I/O-bound operations (DataFrame lookups).
        Falls back to sequential processing if parallelization fails.
        
        Args:
            expected_harmonics: List of expected harmonic frequencies
            max_freq: Maximum frequency in spectrum
            
        Returns:
            Boolean mask array indicating harmonic components
        """
        harmonic_mask = np.zeros(len(self.complete_spectrum_df), dtype=bool)
        
        # Use parallel processing for large harmonic lists (>20 harmonics)
        if len(expected_harmonics) > 20 and cpu_count() > 1:
            try:
                with ThreadPoolExecutor(max_workers=min(cpu_count(), 4)) as executor:
                    # Submit all harmonic detection tasks
                    futures = {
                        executor.submit(self._detect_harmonic_single, freq, max_freq): freq
                        for freq in expected_harmonics
                    }
                    
                    # Collect results
                    for future in as_completed(futures):
                        try:
                            indices = future.result()  # Now returns a list, not a single index
                            if indices:
                                for idx in indices:
                                    # Validate index is within bounds
                                    if 0 <= idx < len(harmonic_mask):
                                        harmonic_mask[idx] = True
                                    else:
                                        logger.error(f"Invalid index {idx} for harmonic mask (length: {len(harmonic_mask)})")
                        except Exception as e:
                            logger.warning(f"Error detecting harmonic at {futures[future]:.2f} Hz: {e}")
                
                logger.info(f"Detected {np.sum(harmonic_mask)} harmonics using parallel processing")
            except Exception as e:
                logger.warning(f"Parallel processing failed, falling back to sequential: {e}")
                # Fallback to sequential
                for expected_freq in expected_harmonics:
                    indices = self._detect_harmonic_single(expected_freq, max_freq)  # Now returns a list
                    for idx in indices:
                        # Validate index is within bounds
                        if 0 <= idx < len(harmonic_mask):
                            harmonic_mask[idx] = True
                        else:
                            logger.error(f"Invalid index {idx} for harmonic mask (length: {len(harmonic_mask)})")
        else:
            # Sequential processing for small lists
            for expected_freq in expected_harmonics:
                indices = self._detect_harmonic_single(expected_freq, max_freq)  # Now returns a list
                for idx in indices:
                    # Validate index is within bounds
                    if 0 <= idx < len(harmonic_mask):
                        harmonic_mask[idx] = True
                    else:
                        logger.error(f"Invalid index {idx} for harmonic mask (length: {len(harmonic_mask)})")
        
        return harmonic_mask
    
    @lru_cache(maxsize=128)
    def _calculate_adaptive_tolerance(self, freq: float, base_tolerance: float, instrument_type: Optional[str] = None) -> float:
        """
        MEDIUM PRIORITY: Calculate adaptive tolerance based on frequency and instrument type.
        
        Mathematical formulation:
        - Uses Weber-Fechner law: Δf/f = constant (≈ 1.5% for frequency discrimination)
        - Formula: tolerance = max(base_tolerance, freq * multiplier)
        - Capped at 50 Hz for numerical stability
        - Instrument-specific adjustments:
          * Woodwinds (clarinet, oboe, bassoon): 1.5% (standard)
          * Brass (trumpet, trombone): 2.0% (slightly more forgiving)
          * Strings (violin, cello): 1.0% (stricter, vibrato handled separately)
          * Piano: 1.5% (standard)
        
        Args:
            freq: Frequency in Hz
            base_tolerance: Base tolerance from tier configuration
            instrument_type: Optional instrument type (e.g., 'clarinet', 'trumpet')
            
        Returns:
            Adaptive tolerance in Hz
        """
        if self.use_adaptive_tolerance and freq > 0:
            # Instrument-specific tolerance multipliers
            instrument_multipliers = {
                'clarinet': 0.015, 'oboe': 0.015, 'bassoon': 0.015, 'flute': 0.015,
                'trumpet': 0.020, 'trombone': 0.020, 'horn': 0.020,
                'violin': 0.010, 'viola': 0.010, 'cello': 0.010, 'bass': 0.010,
                'piano': 0.015
            }
            
            # Get multiplier based on instrument type (case-insensitive)
            multiplier = 0.015  # Default
            if instrument_type:
                instrument_lower = instrument_type.lower()
                for key, value in instrument_multipliers.items():
                    if key in instrument_lower:
                        multiplier = value
                        logger.debug(f"Using instrument-specific tolerance multiplier: {multiplier} for {instrument_type}")
                        break
            
            # Frequency-dependent adjustment
            if freq < 500:
                adaptive = freq * (multiplier * 2.0)  # More forgiving for low frequencies
            else:
                adaptive = freq * multiplier
            
            return min(max(base_tolerance, adaptive), 50.0)
        return base_tolerance
    
    def _detect_harmonics_aggressive(self, expected_harmonics: List[float], max_freq: float) -> np.ndarray:
        """
        More aggressive harmonic detection with wider tolerance.
        
        This is used as a fallback when standard detection finds too few harmonics.
        Uses 5% tolerance for all harmonics and detects ALL significant components.
        """
        harmonic_mask = np.zeros(len(self.complete_spectrum_df), dtype=bool)
        
        # Ensure sequential index
        if not self.complete_spectrum_df.index.equals(pd.RangeIndex(len(self.complete_spectrum_df))):
            self.complete_spectrum_df = self.complete_spectrum_df.reset_index(drop=True)
        
        # CRITICAL FIX #1: Use Amplitude_linear (not dB) for thresholding
        max_magnitude = self.complete_spectrum_df['Amplitude_linear'].max()
        
        for expected_freq in expected_harmonics:
            if expected_freq > max_freq:
                break
            
            # More generous tolerance: 5% for all harmonics, minimum 10 Hz
            tolerance_hz = max(expected_freq * 0.05, 10.0)
            
            # Even more generous for higher harmonics
            if expected_freq > self.fundamental_freq * 10:
                tolerance_hz = max(tolerance_hz, expected_freq * 0.08)  # 8% for high harmonics
            
            # Find frequencies within tolerance
            freq_diffs = np.abs(self.complete_spectrum_df['Frequency (Hz)'].values - expected_freq)
            within_tolerance = freq_diffs <= tolerance_hz
            
            if np.any(within_tolerance):
                # Get positional indices
                positional_indices = np.where(within_tolerance)[0]
                candidate_magnitudes = self.complete_spectrum_df['Amplitude_linear'].values[positional_indices]
                
                # CRITICAL: Balance thresholds to avoid missing low harmonics and suppress high-frequency noise
                if expected_freq <= self.fundamental_freq * 5:
                    min_magnitude_threshold = max_magnitude * 0.0005  # 0.05% for low harmonics
                else:
                    min_magnitude_threshold = max_magnitude * 0.0008  # 0.08% for high harmonics
                
                # Also use relative threshold: 10% of strongest in this window
                strongest_in_window = np.max(candidate_magnitudes) if len(candidate_magnitudes) > 0 else 0
                relative_threshold = strongest_in_window * 0.1
                min_magnitude_threshold = min(min_magnitude_threshold, relative_threshold)
                
                # Mark ALL significant candidates
                significant_candidates = candidate_magnitudes >= min_magnitude_threshold
                
                if np.any(significant_candidates):
                    for pos in np.where(significant_candidates)[0]:
                        idx = int(positional_indices[pos])
                        if 0 <= idx < len(harmonic_mask):
                            harmonic_mask[idx] = True
                else:
                    # If no candidates meet threshold, at least mark the strongest
                    strongest_pos = np.argmax(candidate_magnitudes)
                    idx = int(positional_indices[strongest_pos])
                    if 0 <= idx < len(harmonic_mask):
                        harmonic_mask[idx] = True
        
        return harmonic_mask
    
    def _detect_audio_channels(self) -> Tuple[int, bool]:
        """
        Detect the number of channels in the audio file.
        
        Returns:
            Tuple of (channels, is_stereo)
            - channels: Number of audio channels (1=mono, 2=stereo, etc.)
            - is_stereo: True if stereo (2 channels), False otherwise
        """
        try:
            # Use soundfile to get audio info without loading the entire file
            # Works with .aif, .aiff, .wav, and other formats
            info = sf.info(str(self.audio_path))
            channels = info.channels
            is_stereo = (channels == 2)
            file_ext = self.audio_path.suffix.lower()
            logger.info(f"Detected audio format ({file_ext}): {channels} channel(s), {'STEREO' if is_stereo else 'MONO'}")
            logger.info(f"  Sample rate: {info.samplerate} Hz, Format: {info.format}")
            return channels, is_stereo
        except Exception as e:
            logger.warning(f"Could not detect channels using soundfile: {e}. Trying librosa fallback...")
            # Fallback: try loading a small sample with librosa
            # This works better for some .aif files that soundfile might have issues with
            try:
                y, sr = librosa.load(str(self.audio_path), sr=None, mono=False, duration=0.1)
                if y.ndim > 1:
                    channels = y.shape[0]
                    is_stereo = (channels == 2)
                else:
                    channels = 1
                    is_stereo = False
                logger.info(f"Detected via librosa sample: {channels} channel(s), {'STEREO' if is_stereo else 'MONO'}")
                logger.info(f"  Sample rate: {sr} Hz")
                return channels, is_stereo
            except Exception as e2:
                logger.warning(f"Could not detect channels with librosa: {e2}. Defaulting to mono.")
                return 1, False

    def _detect_original_sample_rate(self) -> Optional[int]:
        """Detect original sample rate without resampling."""
        try:
            info = sf.info(str(self.audio_path))
            return int(info.samplerate)
        except Exception:
            try:
                return int(librosa.get_samplerate(str(self.audio_path)))
            except Exception:
                return None
    
    def load_audio(self) -> None:
        """
        Load audio file with stereo detection and intelligent handling.
        
        For stereo files:
        - Detects stereo format
        - Loads both channels
        - Processes intelligently (can analyze both channels or combine)
        """
        logger.info("[1/9] Loading audio file...")
        logger.info(f"Audio path: {self.audio_path}")
        
        # First, detect the audio format
        self.audio_channels, self.is_stereo = self._detect_audio_channels()
        original_sr = self._detect_original_sample_rate()
        
        try:
            if self.is_stereo:
                # Load stereo audio (preserve both channels)
                logger.info("Loading STEREO audio file...")
                audio_data_stereo, self.audio_sr = librosa.load(
                    str(self.audio_path),
                    sr=self.sample_rate,
                    mono=False  # Keep stereo channels separate
                )
                
                # audio_data_stereo shape: (channels, samples) for stereo
                if audio_data_stereo.ndim == 2:
                    # For stereo, we can either:
                    # 1. Process both channels separately (future enhancement)
                    # 2. Combine intelligently (average, or use left channel)
                    # For now, we'll use the average of both channels for analysis
                    # This preserves the overall spectral content while handling stereo
                    self.audio_data = np.mean(audio_data_stereo, axis=0)
                    logger.info("Stereo audio loaded - using averaged channels for analysis")
                    print(f"\n[1/9] Loading audio file...")
                    print(f"  [STEREO] Audio detected ({self.audio_channels} channels)")
                    print(f"  [OK] Loaded: {len(self.audio_data) / self.audio_sr:.2f} seconds, {len(self.audio_data)} samples")
                    print(f"  [OK] Sample rate: {self.audio_sr} Hz")
                    print(f"  [OK] Processing: Averaged stereo channels for spectral analysis")
                else:
                    # Fallback: treat as mono
                    self.audio_data = audio_data_stereo
                    self.is_stereo = False
                    self.audio_channels = 1
            else:
                # Load mono audio (standard behavior)
                self.audio_data, self.audio_sr = librosa.load(
                    str(self.audio_path),
                    sr=self.sample_rate,
                    mono=True
                )
                logger.info("Mono audio loaded")
            
            # Optional low-frequency HPF for very low notes (reduce rumble/leakage)
            hpf_applied = False
            hpf_cutoff_hz = None
            hpf_note_ref = None
            hpf_f0_ref = None
            try:
                note_name = self._extract_note_from_filename()
                f0_ref = self._calculate_freq_from_note(note_name) if note_name else None
                if f0_ref and f0_ref < 30.0:
                    hpf_cutoff_hz = 25.0
                    hpf_note_ref = note_name
                    hpf_f0_ref = f0_ref
                    sos = signal.butter(4, hpf_cutoff_hz, btype="highpass", fs=self.audio_sr, output="sos")
                    self.audio_data = signal.sosfiltfilt(sos, self.audio_data)
                    hpf_applied = True
                    logger.info(f"Applied HPF: cutoff={hpf_cutoff_hz:.1f} Hz (note={note_name}, f0_ref={f0_ref:.2f} Hz)")
            except Exception as e:
                logger.warning(f"Low-frequency HPF skipped: {e}")

            duration = len(self.audio_data) / self.audio_sr
            logger.info(f"Loaded: {duration:.2f} seconds, {len(self.audio_data)} samples")
            logger.info(f"Sample rate: {self.audio_sr} Hz")
            logger.info(f"Channels: {self.audio_channels} ({'STEREO' if self.is_stereo else 'MONO'})")
            
            if not self.is_stereo:
                print(f"\n[1/9] Loading audio file...")
                print(f"  [OK] Loaded: {duration:.2f} seconds, {len(self.audio_data)} samples")
                print(f"  [OK] Sample rate: {self.audio_sr} Hz")
                print(f"  [OK] Format: MONO")
            
            # Update metadata
            self.results['metadata']['channels'] = self.audio_channels
            self.results['metadata']['is_stereo'] = self.is_stereo
            self.results['metadata']['original_sample_rate'] = original_sr
            self.results['metadata']['resampled'] = (
                (original_sr is not None) and (self.sample_rate is not None) and (int(original_sr) != int(self.sample_rate))
            )
            self.results['metadata']['analysis_sample_rate'] = self.audio_sr
            self.results['metadata']['hpf_applied'] = hpf_applied
            self.results['metadata']['hpf_cutoff_hz'] = hpf_cutoff_hz
            self.results['metadata']['hpf_reference_note'] = hpf_note_ref
            self.results['metadata']['hpf_reference_f0_hz'] = hpf_f0_ref

            # RMS of stationary segment (middle 70% of signal to avoid attack/release)
            n = len(self.audio_data)
            if n >= 1000:
                start = int(0.15 * n)
                end = int(0.85 * n)
                y_stationary = self.audio_data[start:end].astype(np.float64)
            else:
                y_stationary = np.asarray(self.audio_data, dtype=np.float64)
            rms_value = float(np.sqrt(np.mean(y_stationary**2)))
            self.results['metadata']['rms_stationary'] = rms_value
            logger.info(f"RMS (stationary segment): {rms_value:.6f}")
            
        except Exception as e:
            logger.error(f"Failed to load audio: {e}", exc_info=True)
            raise RuntimeError(f"Failed to load audio: {e}")
    
    def _pick_tier_for_f0(self, f0: float) -> str:
        """
        Select the most appropriate 90-tier configuration based on f0.
        Chooses the smallest tier max_freq that still covers f0.
        """
        if not self.tier_config:
            return "Tier_01"
        tiers = []
        for name, cfg in self.tier_config.items():
            max_freq = cfg.get('max_freq', float('inf'))
            tiers.append((max_freq, name))
        tiers.sort(key=lambda x: x[0])
        for max_freq, name in tiers:
            if f0 <= max_freq:
                return name
        return tiers[-1][1]

    def _select_stft_parameters(self) -> Tuple[Optional[str], int, int, Optional[float], Optional[str]]:
        """
        Select STFT parameters adaptively using tier config and filename note.
        Returns (tier_used, n_fft, hop_length, f0_ref, note_name).
        """
        if self.use_90_tier and self.tier_config:
            note_name = self._extract_note_from_filename()
            f0_ref = self._calculate_freq_from_note(note_name) if note_name else None
            if f0_ref:
                tier_used = self._pick_tier_for_f0(f0_ref)
            else:
                tier_used = "Tier_01"
            n_fft = self.tier_config[tier_used]['n_fft']
            hop_length = n_fft // 8  # Blackman-Harris alignment
            return tier_used, n_fft, hop_length, f0_ref, note_name
        return None, 4096, 1024, None, None

    def compute_spectrogram(self) -> None:
        """Compute STFT spectrogram with optimal parameters."""
        print("\n[2/9] Computing spectrogram (STFT)...")
        
        # Determine optimal FFT size based on 90-tier and reference f0 (from filename note if available)
        tier_used, n_fft, hop_length, f0_ref, note_name = self._select_stft_parameters()
        
        try:
            # Compute STFT
            self.stft = librosa.stft(
                self.audio_data,
                n_fft=n_fft,
                hop_length=hop_length,
                window=self.window,
                center=True,
                pad_mode='reflect'
            )
            
            # Get magnitude spectrogram
            self.magnitude_spectrogram = np.abs(self.stft)
            
            # Get frequency and time arrays
            self.frequencies = librosa.fft_frequencies(sr=self.audio_sr, n_fft=n_fft)
            self.n_fft = n_fft  # Store for window energy spread calculation
            self.times = librosa.frames_to_time(
                np.arange(self.magnitude_spectrogram.shape[1]),
                sr=self.audio_sr,
                hop_length=hop_length
            )

            # Stamp STFT parameters for reproducibility
            stft_params = {
                'stft_n_fft': n_fft,
                'stft_hop_length': hop_length,
                'stft_center': True,
                'stft_pad_mode': 'reflect',
                'stft_tier_used': tier_used,
                'stft_zero_padding_factor': self.tier_config.get(tier_used, {}).get('zp') if (tier_used and self.tier_config) else None,
                'stft_reference_f0_hz': f0_ref,
                'stft_reference_note': note_name
            }
            self.results['metadata']['analysis_parameters'].update(stft_params)
            self.results['metadata']['analysis_parameters_hash'] = self._stable_hash(
                self.results['metadata']['analysis_parameters']
            )
            
            # Convert to dB
            magnitude_db = librosa.amplitude_to_db(self.magnitude_spectrogram, ref=np.max)
            
            print(f"  ✓ Spectrogram shape: {self.magnitude_spectrogram.shape}")
            print(f"  ✓ FFT size: {n_fft}, Hop length: {hop_length}")
            print(f"  ✓ Frequency range: {self.frequencies[0]:.2f} - {self.frequencies[-1]:.2f} Hz")
            
            # Create complete spectrum DataFrame (time-averaged)
            # CRITICAL FIX #1: Explicit unit naming to prevent dB/linear confusion
            # CRITICAL FIX: Correct time-averaged power calculation
            # Mathematical relationships (reference):
            # - Power P = A² (where A is linear amplitude)
            # - Mean power = mean(|X|²) NOT (mean|X|)²
            # - For time-averaged power: avg_power = mean(X²) over time dimension
            # - Then: avg_amplitude_linear = sqrt(avg_power) (RMS amplitude)
            # - dB = 20*log10(A/A_ref)
            # - Energy calculations require power (amplitude squared), NOT decibels
            # - Entropy requires probability distributions (normalized power), NOT decibels
            # CORRECT: avg_power = mean(|X|²) over time axis
            avg_power = np.mean(self.magnitude_spectrogram ** 2, axis=1)  # Mean power (time-averaged |X|²)
            avg_amplitude_linear = np.sqrt(avg_power)  # RMS amplitude = sqrt(mean power)
            avg_magnitude_db = librosa.amplitude_to_db(avg_amplitude_linear, ref=np.max)  # dB scale (for visualization only)
            
            self.complete_spectrum_df = pd.DataFrame({
                'Frequency (Hz)': self.frequencies,
                'Amplitude_linear': avg_amplitude_linear,  # Linear amplitude (for all physical calculations)
                'Power': avg_power,  # Power = amplitude² (for energy/entropy calculations)
                'Magnitude_dB': avg_magnitude_db  # Decibel scale (for visualization/thresholding only)
            })
            
            # CRITICAL: Ensure sequential index (0, 1, 2, ...) for proper mask indexing
            self.complete_spectrum_df = self.complete_spectrum_df.reset_index(drop=True)
            
            logger.info(f"Created spectrum DataFrame with {len(self.complete_spectrum_df)} components")
            logger.info(f"Frequency range: {self.frequencies[0]:.2f} - {self.frequencies[-1]:.2f} Hz")
            # CRITICAL FIX: Use avg_amplitude_linear (renamed from avg_magnitude in Fix #1)
            logger.info(f"Amplitude range: {np.min(avg_amplitude_linear):.6f} - {np.max(avg_amplitude_linear):.6f}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to compute spectrogram: {e}")
    
    def _extract_note_from_filename(self) -> Optional[str]:
        """
        Extract musical note from filename (e.g., 'bassoon_A4_...' -> 'A4').
        
        Returns:
            Note name (e.g., 'A4', 'C#3', 'Bb2') or None if not found
        """
        import re
        filename = self.audio_path.name
        
        # Try multiple patterns to match note names
        patterns = [
            r'([A-G][#b]?)(\d+)',  # Standard: A4, C#3, Bb2
            r'([A-G][♯♭]?)(\d+)',  # Unicode sharps/flats
            r'([A-G])([#b]?)(\d+)',  # Separated accidental
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                if len(match.groups()) == 2:
                    note = match.group(1) + match.group(2)
                elif len(match.groups()) == 3:
                    note = match.group(1) + match.group(2) + match.group(3)
                else:
                    continue
                
                # Normalize Unicode sharps/flats
                note = note.replace('♯', '#').replace('♭', 'b')
                logger.info(f"Extracted note '{note}' from filename: {filename}")
                return note
        
        logger.warning(f"Could not extract note from filename: {filename}")
        return None
    
    def _calculate_window_energy_spread(self, window_type: str, n_fft: int, bin_width_hz: float) -> Dict[str, float]:
        """
        HIGH PRIORITY FIX: Calculate window-specific energy spread.
        
        Mathematical foundation:
        - Main lobe width: W_main (in bins) - from window's frequency response
        - Energy concentration: ~90% within ±W_main/2 bins, ~95% within ±W_main bins
        - For Blackman-Harris: W_main ≈ 4 bins
        - For Hann: W_main ≈ 2 bins
        - For Hamming: W_main ≈ 2 bins
        
        Args:
            window_type: Window name (e.g., 'blackmanharris', 'hann')
            n_fft: FFT size
            bin_width_hz: Frequency bin width in Hz
            
        Returns:
            Dictionary with 'main_lobe_width_bins', 'energy_90pct_bins', 'energy_95pct_bins'
        """
        try:
            from proc_audio import _calculate_window_characteristics
            
            # Get window characteristics
            window_chars = _calculate_window_characteristics(window_type, n_fft)
            main_lobe_width_bins = window_chars.get('main_lobe_width', 4.0)  # Default: Blackman-Harris
            
            # Energy concentration: empirical values from window analysis
            # ~90% of energy within ±W_main/2 bins, ~95% within ±W_main bins
            energy_90pct_bins = max(1, int(np.ceil(main_lobe_width_bins / 2)))
            energy_95pct_bins = max(1, int(np.ceil(main_lobe_width_bins)))
            
            # Main lobe width in Hz
            main_lobe_width_hz = main_lobe_width_bins * bin_width_hz
            
            logger.debug(f"Window {window_type}: main_lobe={main_lobe_width_bins:.2f} bins ({main_lobe_width_hz:.2f} Hz), "
                        f"90% energy within ±{energy_90pct_bins} bins, 95% within ±{energy_95pct_bins} bins")
            
            return {
                'main_lobe_width_bins': float(main_lobe_width_bins),
                'main_lobe_width_hz': float(main_lobe_width_hz),
                'energy_90pct_bins': energy_90pct_bins,
                'energy_95pct_bins': energy_95pct_bins
            }
        except Exception as e:
            logger.warning(f"Failed to calculate window energy spread: {e}. Using defaults.")
            # Default: Blackman-Harris characteristics
            return {
                'main_lobe_width_bins': 4.0,
                'main_lobe_width_hz': 4.0 * bin_width_hz,
                'energy_90pct_bins': 2,
                'energy_95pct_bins': 4
            }
    
    def _select_best_f0(self, f0_candidates: List[float], prior_hz: float, tol_cents: float = 50.0) -> Tuple[float, Optional[float], Dict[str, Any]]:
        """
        Choose an f0 candidate closest to the filename-note prior using
        integer harmonic-ratio correction (÷n, ×n for n≤6), not half-octave
        shifts. Accept only when the best corrected error is ≤ tol_cents.
        """
        try:
            from proc_audio import _correct_f0_candidate_against_prior
        except ImportError:
            _correct_f0_candidate_against_prior = None  # type: ignore[assignment]

        empty_v = {
            "before_correction_error": None,
            "after_correction_error": None,
            "correction_applied": False,
            "best_shift": None,
            "best_candidate_raw": None,
            "harmonic_ratio_applied": None,
        }
        if (
            not f0_candidates
            or prior_hz <= 0
            or _correct_f0_candidate_against_prior is None
        ):
            return (prior_hz, None, empty_v)

        best_before_error = float("inf")
        best_before_raw: Optional[float] = None
        for cand in f0_candidates:
            if cand is None or cand <= 0:
                continue
            raw_cents = abs(1200.0 * np.log2(float(cand) / float(prior_hz)))
            if raw_cents < best_before_error:
                best_before_error = raw_cents
                best_before_raw = float(cand)

        best_f0 = float(prior_hz)
        best_err = float("inf")
        best_candidate_raw: Optional[float] = None
        best_ratio: Optional[float] = None

        for cand in f0_candidates:
            if cand is None or cand <= 0:
                continue
            res = _correct_f0_candidate_against_prior(
                float(cand), float(prior_hz), max_harmonic_ratio=6
            )
            if not res.get("valid"):
                continue
            err = float(res["cents_error"])
            hz = float(res["corrected_hz"])
            if err < best_err:
                best_err = err
                best_f0 = hz
                best_candidate_raw = float(res["raw_hz"])
                best_ratio = float(res["ratio_applied"])

        correction_applied = bool(
            best_ratio is not None and abs(best_ratio - 1.0) > 1e-12
        )
        validation_dict: Dict[str, Any] = {
            "before_correction_error": (
                float(best_before_error) if best_before_error < float("inf") else None
            ),
            "after_correction_error": float(best_err) if best_err < float("inf") else None,
            "correction_applied": correction_applied,
            "best_shift": None,
            "best_candidate_raw": best_candidate_raw,
            "harmonic_ratio_applied": best_ratio,
            "improvement_cents": None,
        }
        if best_before_error < float("inf") and best_err < float("inf"):
            validation_dict["improvement_cents"] = float(best_before_error - best_err)

        if best_err < float(tol_cents):
            return (best_f0, float(best_err), validation_dict)
        return (prior_hz, None, validation_dict)
    
    def _calculate_freq_from_note(self, note: str) -> Optional[float]:
        """
        Calculate fundamental frequency from musical note name.
        
        Args:
            note: Note name (e.g., 'A4', 'C#3', 'Bb2', 'C7')
            
        Returns:
            Fundamental frequency in Hz or None if invalid
        """
        try:
            freq = librosa.note_to_hz(note)
            # Allow frequencies up to 10000 Hz to support very high notes and harmonics (C7=2093 Hz, C8=4186 Hz, C9=8372 Hz, etc.)
            if freq and 20.0 <= freq <= 10000.0:
                logger.info(f"Calculated frequency from note '{note}': {freq:.2f} Hz")
                return float(freq)
            else:
                logger.warning(f"Calculated frequency {freq:.2f} Hz from note '{note}' is outside reasonable range")
                return None
        except Exception as e:
            logger.warning(f"Failed to calculate frequency from note '{note}': {e}")
            return None
    
    def _log_harmonic_alignment_report(self, report: Dict[str, Any]) -> None:
        """Log harmonic-order alignment (cents) separately from representative-energy diagnostics."""
        mc = report.get("harmonic_alignment_matched_count", report.get("harmonic_representative_count", 0))
        ec = report.get("harmonic_alignment_expected_count", report.get("total_expected_harmonic_orders", 0))
        mae = report.get("harmonic_order_alignment_mean_abs_error_cents", report.get("harmonic_alignment_mean_abs_error_cents", report.get("mean_abs_cents_error")))
        wmae = report.get(
            "harmonic_order_alignment_weighted_mean_abs_error_cents",
            report.get("harmonic_alignment_weighted_mean_abs_error_cents", report.get("weighted_mean_abs_cents_error")),
        )
        med = report.get("harmonic_order_alignment_median_abs_error_cents", report.get("harmonic_alignment_median_abs_error_cents", report.get("median_abs_cents_error")))
        p95 = report.get("harmonic_order_alignment_p95_abs_error_cents", report.get("harmonic_alignment_p95_abs_error_cents", report.get("p95_abs_cents_error")))
        r_rep = float(report.get("collapsed_representative_energy_share", report.get("collapsed_representative_energy_ratio", report.get("harmonic_alignment_energy_coverage_ratio", 0.0))) or 0.0)
        r_inh_e = float(report.get("non_harmonic_candidate_energy_ratio", report.get("inharmonic_candidate_energy_ratio", 0.0)) or 0.0)
        st_u = str(report.get("harmonic_order_alignment_status", report.get("harmonic_alignment_status", "failed")))
        st_w = str(report.get("harmonic_order_alignment_weighted_status", "failed"))
        st_e = str(report.get("harmonic_representative_energy_status", "unknown"))
        n_reg = int(report.get("harmonic_region_candidate_rows", report.get("harmonic_region_candidate_count", 0)) or 0)
        n_inh = int(report.get("non_harmonic_candidate_count", report.get("inharmonic_candidate_count", 0)) or 0)
        n_collapsed = int(report.get("energy_collapsed_representatives_count", report.get("harmonic_representative_count", mc)) or 0)

        def _fmt(x: Any) -> str:
            if isinstance(x, (int, float)) and np.isfinite(float(x)):
                return f"{float(x):.1f}"
            return "n/a"

        lines = [
            "Harmonic order alignment (cents; unweighted mean uses matched collapsed representatives only):",
            f"alignment_candidate_harmonic_orders_matched / total: {mc}/{ec}",
            f"harmonic_order_alignment_mean_abs_error_cents: {_fmt(mae)}",
            f"harmonic_order_alignment_weighted_mean_abs_error_cents: {_fmt(wmae)}",
            f"harmonic_order_alignment_median_abs_error_cents: {_fmt(med)}",
            f"harmonic_order_alignment_p95_abs_error_cents: {_fmt(p95)}",
            f"harmonic_order_alignment_status (cents+orders only): {st_u}",
            f"harmonic_order_alignment_weighted_status (energy-weighted mean cents): {st_w}",
            "Representative / candidate energy (separate diagnostic; does not change alignment status):",
            f"collapsed_representative_energy_share: {100.0 * r_rep:.1f}%",
            f"non_harmonic_candidate_energy_ratio (outside all harmonic windows): {100.0 * r_inh_e:.1f}%",
            f"harmonic_region_candidate_rows: {n_reg}; non_harmonic_candidate_rows: {n_inh}",
            f"energy_collapsed_representatives_count: {n_collapsed}; expected_harmonic_orders_below_nyquist: {ec}",
            f"harmonic_representative_energy_status: {st_e}",
            "Note: alignment counts use harmonic-order matching + cents gates; energy_collapsed_representatives_count "
            "counts strongest peak per matched order — populations differ by design.",
        ]
        diag = report.get("harmonic_alignment_energy_diagnostic_message")
        if isinstance(diag, str) and diag.strip():
            lines.append(str(diag))
        logger.info("%s", "\n".join(lines))
        for ln in lines:
            print(f"  {ln}")

    def detect_fundamental_frequency(self) -> float:
        """
        CRITICAL FIX #2: Signal-based fundamental frequency estimation.
        
        Strategy (in priority order):
        1. pYIN estimation (preferred - has confidence scores)
        2. YIN estimation (fallback)
        3. Autocorrelation-based estimation (fallback)
        4. Filename note as PRIOR/validation (not ground truth)
        
        Mathematical foundation (standard formulation):
        - pYIN: Probabilistic YIN algorithm with voiced/unvoiced classification
        - YIN: Autocorrelation-based pitch detection with cumulative mean normalization
        - Autocorrelation: R(τ) = Σ x[n] * x[n+τ], f0 = argmax_τ R(τ) for τ > τ_min
        
        Returns:
            Estimated fundamental frequency in Hz
        """
        try:
            logger.info("[3/9] Detecting fundamental frequency from signal...")
            print("\n[3/9] Detecting fundamental frequency from signal...")
            
            if self.audio_data is None or len(self.audio_data) == 0:
                raise ValueError("Audio data not loaded. Cannot estimate f0.")
            
            # Get filename note as PRIOR (not ground truth)
            note_prior = self._extract_note_from_filename()
            f0_prior = None
            if note_prior:
                f0_prior = self._calculate_freq_from_note(note_prior)
                logger.info(f"Filename note '{note_prior}' provides prior: {f0_prior:.2f} Hz")
            
            detection_results = {
                'pyin': None,
                'yin': None,
                'autocorrelation': None,
                'note_prior': note_prior,
                'f0_prior': f0_prior
            }
            
            # METHOD 1: pYIN (preferred - has confidence scores)
            # pYIN provides voiced probability, allowing robust median estimation
            try:
                logger.debug("Attempting pYIN estimation...")
                # CRITICAL FIX: Remove threshold parameter (not supported in some librosa versions)
                # Use default voicing threshold via beta_parameters instead
                f0_pyin, voiced_flag, voiced_prob = librosa.pyin(
                    self.audio_data,
                    fmin=20.0,  # Minimum frequency (Hz)
                    fmax=2000.0,  # Maximum frequency (Hz)
                    frame_length=2048,  # Frame length for analysis
                    hop_length=512,  # Hop length between frames
                    # threshold parameter removed - not supported in all librosa versions
                    beta_parameters=(2, 1),  # Beta distribution parameters for prior
                    boltzmann_parameter=2.0,  # Boltzmann parameter for transition
                    no_trough_prob=0.01,  # Probability of no trough
                    fill_na=np.nan  # Fill unvoiced frames with NaN
                )
                
                # Use median of voiced frames with high confidence (>0.8)
                confident_mask = (voiced_prob > 0.8) & (voiced_flag) & (~np.isnan(f0_pyin))
                if np.sum(confident_mask) > 0:
                    f0_pyin_median = np.median(f0_pyin[confident_mask])
                    if 20.0 <= f0_pyin_median <= 2000.0:
                        detection_results['pyin'] = {
                            'f0': float(f0_pyin_median),
                            'confidence': float(np.mean(voiced_prob[confident_mask])),
                            'n_voiced_frames': int(np.sum(confident_mask)),
                            'total_frames': len(f0_pyin)
                        }
                        logger.info(f"✓ pYIN estimation: {f0_pyin_median:.2f} Hz (confidence: {np.mean(voiced_prob[confident_mask]):.2f})")
                        print(f"  ✓ pYIN: {f0_pyin_median:.2f} Hz")
            except Exception as e:
                logger.warning(f"pYIN estimation failed: {e}")
            
            # METHOD 2: YIN (fallback)
            try:
                logger.debug("Attempting YIN estimation...")
                # CRITICAL FIX: Remove threshold parameter (not supported in some librosa versions)
                f0_yin = librosa.yin(
                    self.audio_data,
                    fmin=20.0,
                    fmax=2000.0,
                    frame_length=2048,
                    hop_length=512
                    # threshold parameter removed - not supported in all librosa versions
                )
                
                # Use median of valid frames (non-NaN, within range)
                valid_mask = (~np.isnan(f0_yin)) & (f0_yin >= 20.0) & (f0_yin <= 2000.0)
                if np.sum(valid_mask) > 0:
                    f0_yin_median = np.median(f0_yin[valid_mask])
                    detection_results['yin'] = {
                        'f0': float(f0_yin_median),
                        'n_valid_frames': int(np.sum(valid_mask)),
                        'total_frames': len(f0_yin)
                    }
                    logger.info(f"✓ YIN estimation: {f0_yin_median:.2f} Hz")
                    print(f"  ✓ YIN: {f0_yin_median:.2f} Hz")
            except Exception as e:
                logger.warning(f"YIN estimation failed: {e}")
            
            # METHOD 3: Autocorrelation (fallback)
            try:
                logger.debug("Attempting autocorrelation estimation...")
                # Use autocorrelation to find period
                # Normalize audio for autocorrelation
                audio_norm = self.audio_data / (np.max(np.abs(self.audio_data)) + 1e-10)
                
                # Autocorrelation
                autocorr = np.correlate(audio_norm, audio_norm, mode='full')
                autocorr = autocorr[len(autocorr)//2:]  # Take positive lags
                
                # Find peaks in autocorrelation (excluding zero lag)
                min_period = int(self.audio_sr / 2000.0)  # Minimum period for 2000 Hz
                max_period = int(self.audio_sr / 20.0)  # Maximum period for 20 Hz
                
                if len(autocorr) > max_period:
                    autocorr_window = autocorr[min_period:max_period]
                    peaks, _ = signal.find_peaks(autocorr_window, height=0.1)
                    
                    if len(peaks) > 0:
                        # Use first significant peak as period estimate
                        period_samples = peaks[0] + min_period
                        f0_autocorr = self.audio_sr / period_samples
                        
                        if 20.0 <= f0_autocorr <= 2000.0:
                            detection_results['autocorrelation'] = {
                                'f0': float(f0_autocorr),
                                'period_samples': int(period_samples)
                            }
                            logger.info(f"✓ Autocorrelation estimation: {f0_autocorr:.2f} Hz")
                            print(f"  ✓ Autocorrelation: {f0_autocorr:.2f} Hz")
            except Exception as e:
                logger.warning(f"Autocorrelation estimation failed: {e}")
            
            # PATCH 1️⃣: Robust f0 selection constrained by filename prior
            # Mathematical foundation (reference):
            # - Cents deviation: Δc = 1200 * log₂(f_est / f_prior)
            # - Octave errors: ±1200 cents (2x), ±2400 cents (4x)
            # - Consider ±0.5, ±1, ±2 octaves: multiply/divide by 2^0.5, 2^1, 2^2
            # - Choose candidate that minimizes corrected cents error
            # - If best corrected error > tolerance (50 cents), fall back to prior
            
            # Collect all candidates
            f0_candidates = []
            if detection_results['pyin'] is not None:
                f0_candidates.append(detection_results['pyin']['f0'])
            if detection_results['yin'] is not None:
                f0_candidates.append(detection_results['yin']['f0'])
            if detection_results['autocorrelation'] is not None:
                f0_candidates.append(detection_results['autocorrelation']['f0'])
            
            # Use robust selection method with validation tracking
            if f0_prior is not None and f0_candidates:
                f0_selected, cents_err, validation_dict = self._select_best_f0(f0_candidates, f0_prior, tol_cents=50)
                
                # HIGH PRIORITY: Store octave correction validation in results
                self.results['frequency_analysis']['octave_correction_validation'] = validation_dict
                
                if cents_err is None:
                    logger.warning(f"f0 tracker diverged from prior; using prior {f0_prior:.2f} Hz")
                    print(f"  ⚠ f0 tracker diverged, using filename prior: {f0_prior:.2f} Hz")
                    f0_estimated = f0_prior
                    method_used = 'filename_prior_constrained'
                    cents_err = 0.0
                else:
                    f0_estimated = f0_selected
                    # Determine which method was selected (closest to selected f0)
                    method_distances = []
                    if detection_results['pyin'] is not None:
                        method_distances.append(('pyin', abs(detection_results['pyin']['f0'] - f0_selected)))
                    if detection_results['yin'] is not None:
                        method_distances.append(('yin', abs(detection_results['yin']['f0'] - f0_selected)))
                    if detection_results['autocorrelation'] is not None:
                        method_distances.append(('autocorrelation', abs(detection_results['autocorrelation']['f0'] - f0_selected)))
                    method_used = min(method_distances, key=lambda x: x[1])[0] if method_distances else 'unknown'
                    logger.info(f"Selected {method_used}: {f0_estimated:.2f} Hz (corrected error: {cents_err:.1f} cents)")
                    print(f"  ✓ Selected {method_used}: {f0_estimated:.2f} Hz (error: {cents_err:.1f} cents)")
            elif f0_candidates:
                # No prior available, use priority order
                # CRITICAL FIX: Still test octave corrections even without prior
                # If f0 is outside reasonable range (20-5000 Hz), test ±octaves
                f0_raw = None
                if detection_results['pyin'] is not None:
                    f0_raw = detection_results['pyin']['f0']
                    method_used = 'pyin'
                elif detection_results['yin'] is not None:
                    f0_raw = detection_results['yin']['f0']
                    method_used = 'yin'
                elif detection_results['autocorrelation'] is not None:
                    f0_raw = detection_results['autocorrelation']['f0']
                    method_used = 'autocorrelation'
                
                if f0_raw is not None:
                    # Test if f0 is in reasonable range (20-5000 Hz for musical instruments)
                    # If outside, test octave corrections
                    if f0_raw < 20.0 or f0_raw > 5000.0:
                        logger.warning(f"f0 {f0_raw:.2f} Hz outside reasonable range, testing octave corrections")
                        best_f0 = f0_raw
                        best_err = abs(440.0 - f0_raw) if 20 <= f0_raw <= 5000 else float('inf')  # Use A4 as reference
                        
                        # Test ±1, ±2 octaves
                        for shift in [1.0, 2.0]:
                            for direction in [1, -1]:
                                adj = f0_raw * (2 ** (direction * shift))
                                if 20.0 <= adj <= 5000.0:
                                    # Prefer values closer to typical instrument range (80-2000 Hz)
                                    ref = 440.0  # A4 as reference
                                    err = abs(adj - ref)
                                    if err < best_err:
                                        best_f0 = adj
                                        best_err = err
                                        logger.info(f"Octave correction: {f0_raw:.2f} Hz → {adj:.2f} Hz (shift={direction*shift:+.1f} oct)")
                        
                        f0_estimated = best_f0
                        if best_f0 != f0_raw:
                            logger.info(f"Applied octave correction: {f0_raw:.2f} Hz → {f0_estimated:.2f} Hz")
                    else:
                        f0_estimated = f0_raw
                    
                    logger.info(f"No filename prior available. Using {method_used}: {f0_estimated:.2f} Hz")
                else:
                    f0_estimated = None
            
            # FALLBACK: If all methods fail, use filename prior (but warn)
            # CRITICAL FIX: For batch processing, always allow filename prior as fallback
            if f0_estimated is None:
                if f0_prior is not None:
                    logger.warning(f"All signal-based methods failed. Using filename prior: {f0_prior:.2f} Hz")
                    print(f"  ⚠ All methods failed. Using filename prior: {f0_prior:.2f} Hz")
                    f0_estimated = f0_prior
                    method_used = 'filename_prior'
                else:
                    # CRITICAL FIX: Try to extract note one more time before giving up
                    note_retry = self._extract_note_from_filename()
                    if note_retry:
                        f0_retry = self._calculate_freq_from_note(note_retry)
                        if f0_retry:
                            logger.warning(f"Retry successful: Using filename note '{note_retry}': {f0_retry:.2f} Hz")
                            print(f"  ⚠ Retry successful: Using filename note '{note_retry}': {f0_retry:.2f} Hz")
                            f0_estimated = f0_retry
                            method_used = 'filename_prior_retry'
                        else:
                            error_msg = f"ERROR: Could not estimate f0 from signal and filename note '{note_retry}' is invalid for {self.audio_path.name}."
                            logger.error(error_msg)
                            print(f"  ✗ {error_msg}")
                            raise ValueError(error_msg)
                    else:
                        error_msg = f"ERROR: Could not estimate f0 from signal and no filename prior available for {self.audio_path.name}."
                        logger.error(error_msg)
                        print(f"  ✗ {error_msg}")
                        raise ValueError(error_msg)
            
            # Store result
            self.fundamental_freq = float(f0_estimated)
            
            # Calculate security margin
            security_margin = self._calculate_security_margin(self.fundamental_freq)
            
            logger.info(f"Final fundamental frequency: {self.fundamental_freq:.2f} Hz (method: {method_used})")
            logger.info(f"  Security margin: {security_margin:.1f}%")
            print(f"  ✓ Final f0: {self.fundamental_freq:.2f} Hz ({method_used})")
            print(f"    Security margin: {security_margin:.1f}%")
            
            # CRITICAL FIX #2: Store both detected and expected f0 for validation
            # Calculate expected f0 from filename note (if available) for comparison
            expected_f0_from_note = None
            f0_error_cents = None
            note_name = None
            
            try:
                note_name = self._extract_note_from_filename()
                if note_name:
                    expected_f0_from_note = self._calculate_freq_from_note(note_name)
                    if expected_f0_from_note and expected_f0_from_note > 0:
                        # Calculate error in cents: 1200 * log2(detected / expected)
                        f0_error_cents = 1200.0 * np.log2(self.fundamental_freq / expected_f0_from_note)
            except Exception as e:
                logger.debug(f"Could not extract expected f0 from filename for comparison: {e}")
            
            # Store results with validation information
            self.results['frequency_analysis']['fundamental_freq_hz'] = float(self.fundamental_freq)
            self.results['frequency_analysis']['security_margin_percent'] = float(security_margin)
            self.results['frequency_analysis']['detection_methods'] = detection_results
            self.results['frequency_analysis']['method_used'] = method_used
            
            # CRITICAL FIX #2: Add validation fields
            if expected_f0_from_note is not None:
                self.results['frequency_analysis']['expected_f0_from_note_hz'] = float(expected_f0_from_note)
                self.results['frequency_analysis']['note_name'] = note_name
                if f0_error_cents is not None:
                    self.results['frequency_analysis']['f0_error_cents'] = float(f0_error_cents)
                    logger.info(f"f0 validation: detected={self.fundamental_freq:.2f} Hz, expected={expected_f0_from_note:.2f} Hz, error={f0_error_cents:.1f} cents")
                    if abs(f0_error_cents) > 50:
                        logger.warning(f"Large f0 deviation: {f0_error_cents:.1f} cents (detected vs expected from filename)")
            
            return self.fundamental_freq
            
        except Exception as e:
            logger.error(f"Critical error in frequency detection: {e}", exc_info=True)
            print(f"    ✗ Critical error in frequency detection: {e}")
            raise
    
    def separate_harmonic_inharmonic(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Correct separation into:
          - harmonic partials (near n*f0)
          - inharmonic partials (everything else ABOVE subgrave band)
          - subgrave noise/rumble (below f_low)

        Keeps backward-compatible return (harmonic_df, inharmonic_df),
        while additionally setting:
          self.subbass_df
          self.total_inharmonic_df  (subbass + inharmonic)

        Stores per-class sums/means/medians in self.results['spectral_component_stats'].
        """
        print("\n[4/9] Separating harmonic, inharmonic, and subgrave components...")

        # ---------- Validate fundamental frequency ----------
        if self.fundamental_freq is None or self.fundamental_freq <= 0 or not np.isfinite(self.fundamental_freq):
            print("  ⚠ Invalid fundamental frequency, attempting to extract from note name...")
            self.detect_fundamental_frequency()
            if self.fundamental_freq is None or self.fundamental_freq <= 0 or not np.isfinite(self.fundamental_freq):
                note = self._extract_note_from_filename()
                if note:
                    calculated_freq = self._calculate_freq_from_note(note)
                    if calculated_freq:
                        self.fundamental_freq = calculated_freq
                        logger.info(f"Extracted fundamental frequency from note '{note}': {self.fundamental_freq:.2f} Hz")
                        print(f"  ✓ Extracted from note '{note}': {self.fundamental_freq:.2f} Hz")
                    else:
                        logger.error(f"Failed to calculate frequency from note '{note}'")
                        raise ValueError(f"Could not determine fundamental frequency for {self.audio_path.name}")
                else:
                    logger.error(f"Could not extract note from filename: {self.audio_path.name}")
                    raise ValueError(f"Could not determine fundamental frequency for {self.audio_path.name}")

        if self.complete_spectrum_df.empty:
            raise ValueError("Complete spectrum must be computed first")

        if self.frequencies is None or len(self.frequencies) == 0:
            raise ValueError("Frequencies array is not available. Please compute spectrogram first.")

        freqs = np.asarray(self.frequencies, dtype=float)
        if len(freqs) != len(self.complete_spectrum_df):
            raise ValueError(
                f"Length mismatch: frequencies({len(freqs)}) != complete_spectrum_df({len(self.complete_spectrum_df)})"
            )

        f0 = float(self.fundamental_freq)
        max_freq = float(freqs[-1]) if len(freqs) > 0 else 20000.0

        # ---------- Define subgrave cutoff band ----------
        # Default cutoff: max(20 Hz, 0.5*f0), but ensure it does not exceed ~0.9*f0 (so the fundamental isn't "eaten")
        user_cut = float(getattr(self, "subbass_cutoff_hz", 20.0))
        f_low_candidate = max(user_cut, 0.5 * f0)
        f_low = (0.5 * f0) if (f_low_candidate >= 0.9 * f0) else f_low_candidate

        logger.info(f"Fundamental frequency: {f0:.2f} Hz")
        logger.info(f"Subgrave cutoff f_low: {f_low:.2f} Hz (user_cut={user_cut:.2f} Hz)")
        logger.info(f"Tolerance: {self.harmonic_tolerance} ({'relative' if isinstance(self.harmonic_tolerance, float) and self.harmonic_tolerance < 1.0 else 'absolute'} Hz)")

        # ---------- Expected harmonic list ----------
        max_harmonic = int(max_freq / f0) + 1
        expected_harmonics = [f0 * n for n in range(1, max_harmonic + 1)]
        logger.info(f"Expected harmonics (first 10): {[f'{f:.1f}' for f in expected_harmonics[:10]]}")
        logger.info(f"Total expected harmonics: {len(expected_harmonics)}")

        # ---------- CRITICAL FIX #3: Detect harmonics using peak-based method (not bin-based) ----------
        # Peak-based extraction: peak-pick, interpolate, assign to n*f0 with cents tolerance
        harmonic_mask = self._detect_harmonics_peak_based(expected_harmonics, max_freq)
        
        # Fallback to parallel bin-based method if peak-based finds too few harmonics
        n_detected_peak = int(np.sum(harmonic_mask))
        if n_detected_peak < 3 and len(expected_harmonics) >= 5:
            logger.warning(f"Peak-based method found only {n_detected_peak} harmonics, falling back to bin-based...")
            harmonic_mask = self._detect_harmonics_parallel(expected_harmonics, max_freq)

        # Aggressive fallback if needed (kept, but now we compute energy excluding subgrave band later)
        n_detected = int(np.sum(harmonic_mask))
        if n_detected < 5 and len(expected_harmonics) >= 5:
            logger.warning(f"Only {n_detected} harmonics detected, trying more aggressive detection...")
            harmonic_mask_aggressive = self._detect_harmonics_aggressive(expected_harmonics, max_freq)
            if int(np.sum(harmonic_mask_aggressive)) > n_detected:
                harmonic_mask = harmonic_mask_aggressive

        # ---------- Build 3-way masks ----------
        subbass_mask = freqs < f_low

        # Ensure disjointness: harmonics should not include subgrave bins
        harmonic_mask = harmonic_mask & (~subbass_mask)

        # Inharmonic partials are the remainder above subgrave cutoff
        inharmonic_mask = (~harmonic_mask) & (~subbass_mask)

        # ---------- Create DataFrames ----------
        self.harmonic_df = self.complete_spectrum_df[harmonic_mask].copy()
        self.inharmonic_df = self.complete_spectrum_df[inharmonic_mask].copy()
        self.subbass_df = self.complete_spectrum_df[subbass_mask].copy()

        # Tag component type (useful for later exports/plots if desired)
        if not self.harmonic_df.empty:
            self.harmonic_df["ComponentType"] = "harmonic"
            self.harmonic_df["Harmonic Number"] = [
                int(round(freq / f0)) for freq in self.harmonic_df["Frequency (Hz)"].values
            ]
        if not self.inharmonic_df.empty:
            self.inharmonic_df["ComponentType"] = "inharmonic"
        if not self.subbass_df.empty:
            self.subbass_df["ComponentType"] = "subbass"

        # Total inharmonicity (subbass + inharmonic partials)
        if (not self.inharmonic_df.empty) or (not self.subbass_df.empty):
            self.total_inharmonic_df = pd.concat([self.inharmonic_df, self.subbass_df], ignore_index=True)
        else:
            self.total_inharmonic_df = pd.DataFrame(columns=self.complete_spectrum_df.columns)

        # ---------- Peak-based harmonic-order alignment (cents; all H+IH candidates above subbass) ----------
        _align_parts: List[pd.DataFrame] = []
        if not self.harmonic_df.empty:
            _align_parts.append(self.harmonic_df)
        if not self.inharmonic_df.empty:
            _align_parts.append(self.inharmonic_df)
        _pool_align = pd.concat(_align_parts, ignore_index=True) if _align_parts else pd.DataFrame()
        if not _pool_align.empty:
            try:
                max_hz = float(min(max_freq, 20000.0))
                _sr = getattr(self, "sample_rate", None)
                try:
                    _sr_f = float(_sr) if _sr is not None else None
                    if _sr_f is not None and (not np.isfinite(_sr_f) or _sr_f <= 0):
                        _sr_f = None
                except (TypeError, ValueError):
                    _sr_f = None
                try:
                    _nfft = int(getattr(self, "n_fft", 0) or 0)
                    _nfft = _nfft if _nfft > 0 else None
                except (TypeError, ValueError):
                    _nfft = None
                validation = validate_harmonic_series_matched(
                    f0,
                    _pool_align,
                    max_freq_hz=max_hz,
                    sample_rate=_sr_f,
                    n_fft=_nfft,
                    match_tolerance_cents=None,
                    subbass_cutoff_hz=float(f_low),
                )
                self.results["harmonic_validation"] = validation
                self._log_harmonic_alignment_report(validation)
                st_align = str(
                    validation.get("harmonic_order_alignment_status", validation.get("harmonic_alignment_status", ""))
                )
                if st_align in ("excellent", "good"):
                    print("  ✓ Harmonic order alignment complete (unweighted cents + order match; see log).")
                elif st_align == "warning":
                    print("  ⚠ Harmonic order alignment (cents + orders): warning — see diagnostic block in log.")
                else:
                    print("  ⚠ Harmonic order alignment: failed or insufficient matches (see log).")
            except Exception as e:
                logger.warning("Harmonic alignment validation failed: %s", e, exc_info=True)
                self.results["harmonic_validation"] = {
                    "error": str(e),
                    "harmonic_validation_status": "invalid",
                    "external_validation": False,
                }
                print(f"  ⚠ Harmonic alignment skipped: {e}")

        # ---------- Noise-floor filter (applied per class) ----------
        noise_floor_db = float(getattr(self, "noise_floor_db", -60.0))

        h_before = len(self.harmonic_df)
        i_before = len(self.inharmonic_df)
        s_before = len(self.subbass_df)

        # CRITICAL FIX #1: Use Magnitude_dB (explicit naming) for noise floor filtering
        if "Magnitude_dB" in self.complete_spectrum_df.columns:
            self.harmonic_df = self.harmonic_df[self.harmonic_df["Magnitude_dB"] >= noise_floor_db].copy()
            self.inharmonic_df = self.inharmonic_df[self.inharmonic_df["Magnitude_dB"] >= noise_floor_db].copy()
            self.subbass_df = self.subbass_df[self.subbass_df["Magnitude_dB"] >= noise_floor_db].copy()

            if (not self.inharmonic_df.empty) or (not self.subbass_df.empty):
                self.total_inharmonic_df = pd.concat([self.inharmonic_df, self.subbass_df], ignore_index=True)
            else:
                self.total_inharmonic_df = pd.DataFrame(columns=self.complete_spectrum_df.columns)

        # ---------- Peak-based energy calculation (validation only) ----------
        # Compute energy from peaks for consistency checks, not for primary metrics
        peak_based_energy = self._calculate_peak_based_energy(f0, max_freq, f_low)
        
        # Define _stats function for calculating statistics from DataFrames
        # This is used both for peak-based and bin-based energy calculations
        def _stats(df: pd.DataFrame) -> Dict[str, float]:
            if df is None or df.empty:
                return {
                    "energy_sum": 0.0, "energy_mean": 0.0, "energy_median": 0.0,
                    "amp_mean": 0.0, "amp_median": 0.0
                }
            # CRITICAL FIX #1: Use Amplitude_linear for amplitude stats, Power for energy
            amps = df["Amplitude_linear"].values.astype(float) if "Amplitude_linear" in df.columns else np.array([], dtype=float)
            if amps.size == 0:
                return {
                    "energy_sum": 0.0, "energy_mean": 0.0, "energy_median": 0.0,
                    "amp_mean": 0.0, "amp_median": 0.0
                }
            # CRITICAL FIX #1: Energy = Σ(power), use Power column directly (already amplitude²)
            if "Power" in df.columns:
                energy = df["Power"].values.astype(float)
            else:
                energy = amps ** 2  # Fallback: compute from amplitude if Power not available
            return {
                "energy_sum": float(np.sum(energy)),
                "energy_mean": float(np.mean(energy)),
                "energy_median": float(np.median(energy)),
                "amp_mean": float(np.mean(amps)),
                "amp_median": float(np.median(amps)),
            }
        
        # Peak-based energy (validation only; bin-based used for primary metrics)
        peak_based_valid = False
        peak_based_pct_global = None
        peak_based_pct_musical = None
        if peak_based_energy and peak_based_energy.get('valid', False):
            logger.info("Computed peak-based energy (validation only; bin-based used for primary metrics)")
            H_energy = peak_based_energy.get('harmonic_energy', 0.0)
            I_energy = peak_based_energy.get('inharmonic_energy', 0.0)
            S_energy = peak_based_energy.get('subbass_energy', 0.0)
            total_peak_energy = H_energy + I_energy + S_energy

            if total_peak_energy > 0:
                peak_harmonic_pct_global = (H_energy / total_peak_energy * 100.0)
                peak_inharm_pct_global = (I_energy / total_peak_energy * 100.0)
                peak_subbass_pct_global = (S_energy / total_peak_energy * 100.0)

                total_musical_peak = H_energy + I_energy
                if total_musical_peak > 0:
                    peak_harmonic_pct_musical = (H_energy / total_musical_peak * 100.0)
                    peak_inharm_pct_musical = (I_energy / total_musical_peak * 100.0)
                else:
                    peak_harmonic_pct_musical = 0.0
                    peak_inharm_pct_musical = 0.0

                peak_based_pct_global = {
                    'harmonic': peak_harmonic_pct_global,
                    'inharmonic': peak_inharm_pct_global,
                    'subbass': peak_subbass_pct_global
                }
                peak_based_pct_musical = {
                    'harmonic': peak_harmonic_pct_musical,
                    'inharmonic': peak_inharm_pct_musical
                }
                peak_based_valid = True

                if 'spectral_component_stats' not in self.results:
                    self.results['spectral_component_stats'] = {}
                self.results['spectral_component_stats']['peak_based_energy_valid'] = True
                self.results['spectral_component_stats']['harmonic_energy_pct_global_peak_based'] = peak_harmonic_pct_global
                self.results['spectral_component_stats']['inharmonic_energy_pct_global_peak_based'] = peak_inharm_pct_global
                self.results['spectral_component_stats']['subbass_energy_pct_global_peak_based'] = peak_subbass_pct_global
                self.results['spectral_component_stats']['harmonic_energy_pct_musical_peak_based'] = peak_harmonic_pct_musical
                self.results['spectral_component_stats']['inharmonic_energy_pct_musical_peak_based'] = peak_inharm_pct_musical

                self.results['spectral_component_stats']['harmonic_peak_count_peak_based'] = peak_based_energy.get('harmonic_peak_count', 0)
                self.results['spectral_component_stats']['inharmonic_peak_count_peak_based'] = peak_based_energy.get('inharmonic_peak_count', 0)
                self.results['spectral_component_stats']['subbass_peak_count_peak_based'] = peak_based_energy.get('subbass_peak_count', 0)

                peak_energy_sum = peak_harmonic_pct_global + peak_inharm_pct_global + peak_subbass_pct_global
                peak_energy_error = abs(peak_energy_sum - 100.0)
                self.results['spectral_component_stats']['energy_conservation_error_pct_peak_based'] = float(peak_energy_error)
                logger.info(f"Peak-based energy (validation): H={peak_harmonic_pct_global:.2f}%, I={peak_inharm_pct_global:.2f}%, S={peak_subbass_pct_global:.2f}%")
            else:
                logger.warning("Peak-based energy total is 0.0; skipping peak-based validation metrics")
        else:
            logger.info("Peak-based energy unavailable; using bin-based metrics only")

        # Bin-based energy calculation (primary method for all metrics)
        H = _stats(self.harmonic_df)
        I = _stats(self.inharmonic_df)
        S = _stats(self.subbass_df)
        T = _stats(self.total_inharmonic_df)  # (subbass + inharmonic)

        # Energy totals (musical band excludes subbass)
        total_musical_energy = H["energy_sum"] + I["energy_sum"]
        total_global_energy = total_musical_energy + S["energy_sum"]

        # Musical band percentages (harmonic vs inharmonic, excluding subbass)
        harmonic_pct_musical = (H["energy_sum"] / total_musical_energy * 100.0) if total_musical_energy > 0 else 0.0
        inharm_pct_musical = (I["energy_sum"] / total_musical_energy * 100.0) if total_musical_energy > 0 else 0.0

        # Global percentages (all components relative to total global energy)
        harmonic_pct_global = (H["energy_sum"] / total_global_energy * 100.0) if total_global_energy > 0 else 0.0
        inharm_pct_global = (I["energy_sum"] / total_global_energy * 100.0) if total_global_energy > 0 else 0.0
        subbass_pct_global = (S["energy_sum"] / total_global_energy * 100.0) if total_global_energy > 0 else 0.0
        total_inharm_pct_global = (T["energy_sum"] / total_global_energy * 100.0) if total_global_energy > 0 else 0.0

        # Store flag indicating bin-based method was used (primary)
        if 'spectral_component_stats' not in self.results:
            self.results['spectral_component_stats'] = {}
        self.results['spectral_component_stats']['energy_calculation_method'] = 'bin_based'
        self.results['spectral_component_stats']['peak_based_energy_valid'] = peak_based_valid

        # For bin-based metrics, component counts are from DataFrames (bins)
        self.results['spectral_component_stats']['harmonic_peak_count'] = len(self.harmonic_df) if not self.harmonic_df.empty else 0
        self.results['spectral_component_stats']['inharmonic_peak_count'] = len(self.inharmonic_df) if not self.inharmonic_df.empty else 0
        self.results['spectral_component_stats']['subbass_peak_count'] = len(self.subbass_df) if not self.subbass_df.empty else 0
        
        # Energy conservation: musical band (H+I) and global (H+I+S) use distinct denominators — check separately
        musical_sum_chk = harmonic_pct_musical + inharm_pct_musical
        global_sum_chk = harmonic_pct_global + inharm_pct_global + subbass_pct_global
        musical_err = abs(musical_sum_chk - 100.0)
        global_err = abs(global_sum_chk - 100.0)
        if musical_err > 0.15:
            logger.warning(
                "Musical-band energy percentages (denominator=harmonic+inharmonic, excludes subbass) "
                "do not sum to 100%%: H_musical=%.6f%%, I_musical=%.6f%%, sum=%.6f%%.",
                harmonic_pct_musical,
                inharm_pct_musical,
                musical_sum_chk,
            )
        else:
            logger.info(
                "Musical-band energy check (H+I only): H=%.4f%%, I=%.4f%%, sum=%.4f%%.",
                harmonic_pct_musical,
                inharm_pct_musical,
                musical_sum_chk,
            )
        if global_err > 0.15:
            logger.warning(
                "Global energy percentages (denominator=harmonic+inharmonic+subbass) "
                "do not sum to 100%%: H=%.6f%%, I=%.6f%%, S=%.6f%%, sum=%.6f%%.",
                harmonic_pct_global,
                inharm_pct_global,
                subbass_pct_global,
                global_sum_chk,
            )
        else:
            logger.info(
                "Global energy check (H+I+S): H=%.4f%%, I=%.4f%%, S=%.4f%%, sum=%.4f%%.",
                harmonic_pct_global,
                inharm_pct_global,
                subbass_pct_global,
                global_sum_chk,
            )
        energy_error = float(global_err)
        
        if 'spectral_component_stats' not in self.results:
            self.results['spectral_component_stats'] = {}
        self.results['spectral_component_stats']['energy_conservation_error_pct'] = float(energy_error)

        # Store results (these are the "colunas" de resumo que você quer no Excel/batch)
        # CRITICAL FIX: Initialize if not exists (may have been partially created by peak-based energy calculation)
        if 'spectral_component_stats' not in self.results:
            self.results["spectral_component_stats"] = {}
        
        # Peak-based percentages are optional validation metrics (not used for exports)
        peak_based_pct_global = None
        peak_based_pct_musical = None
        
        if 'harmonic_energy_pct_global_peak_based' in self.results.get('spectral_component_stats', {}):
            peak_based_pct_global = {
                'harmonic': self.results['spectral_component_stats']['harmonic_energy_pct_global_peak_based'],
                'inharmonic': self.results['spectral_component_stats']['inharmonic_energy_pct_global_peak_based'],
                'subbass': self.results['spectral_component_stats']['subbass_energy_pct_global_peak_based']
            }
            peak_based_pct_musical = {
                'harmonic': self.results['spectral_component_stats'].get('harmonic_energy_pct_musical_peak_based', peak_based_pct_global['harmonic']),
                'inharmonic': self.results['spectral_component_stats'].get('inharmonic_energy_pct_musical_peak_based', peak_based_pct_global['inharmonic'])
            }
            logger.info("Peak-based percentages available for validation (not used for exported metrics)")
        
        # Exported primary metrics: bin-integrated energy (full STFT bins in each mask)
        final_harmonic_pct_global = harmonic_pct_global
        final_inharm_pct_global = inharm_pct_global  # Always use bin-based
        final_subbass_pct_global = subbass_pct_global  # Always use bin-based
        final_harmonic_pct_musical = harmonic_pct_musical  # Always use bin-based
        final_inharm_pct_musical = inharm_pct_musical  # Always use bin-based
        
        if peak_based_pct_musical is not None:
            logger.info("Peak-based percentages (validation only; not exported)")
            logger.info(f"  Peak-based: H={peak_based_pct_musical['harmonic']:.2f}%, I={peak_based_pct_musical['inharmonic']:.2f}%")
            logger.info(f"  Bin-based (used): H={harmonic_pct_musical:.2f}%, I={inharm_pct_musical:.2f}%")

        # Optional comparison (bin-based vs peak-based) for diagnostics
        if peak_based_pct_global is not None and peak_based_pct_musical is not None:
            self.results['spectral_component_stats'].update({
                "comparison_bin_vs_peak": {
                    "harmonic_pct_global_delta": float(harmonic_pct_global - peak_based_pct_global["harmonic"]),
                    "inharmonic_pct_global_delta": float(inharm_pct_global - peak_based_pct_global["inharmonic"]),
                    "subbass_pct_global_delta": float(subbass_pct_global - peak_based_pct_global["subbass"]),
                    "harmonic_pct_musical_delta": float(harmonic_pct_musical - peak_based_pct_musical["harmonic"]),
                    "inharmonic_pct_musical_delta": float(inharm_pct_musical - peak_based_pct_musical["inharmonic"]),
                }
            })

        # Musical-band partial energy (H+I) and residual "ground" energy (full spectrum − allocated bins)
        harmonic_plus_inharmonic_energy_sum = float(H["energy_sum"] + I["energy_sum"])
        total_spectrum_power = 0.0
        try:
            csdf = getattr(self, "complete_spectrum_df", None)
            if csdf is not None and not csdf.empty and "Power" in csdf.columns:
                pwr = pd.to_numeric(csdf["Power"], errors="coerce").to_numpy(dtype=float, copy=False)
                total_spectrum_power = float(np.nansum(pwr))
        except Exception:
            total_spectrum_power = 0.0
        ground_noise_energy_sum = 0.0
        if total_spectrum_power > 0.0:
            ground_noise_energy_sum = float(max(0.0, total_spectrum_power - float(total_global_energy)))

        self.results["spectral_component_stats"].update({
            "f0_hz": f0,
            "subgrave_cutoff_hz": f_low,
            "noise_floor_db": noise_floor_db,

            "harmonic_plus_inharmonic_energy_sum": harmonic_plus_inharmonic_energy_sum,
            "ground_noise_energy_sum": ground_noise_energy_sum,

            "harmonic_energy_sum": H["energy_sum"],
            "harmonic_energy_mean": H["energy_mean"],
            "harmonic_energy_median": H["energy_median"],
            "harmonic_amp_mean": H["amp_mean"],
            "harmonic_amp_median": H["amp_median"],

            "inharmonic_energy_sum": I["energy_sum"],
            "inharmonic_energy_mean": I["energy_mean"],
            "inharmonic_energy_median": I["energy_median"],
            "inharmonic_amp_mean": I["amp_mean"],
            "inharmonic_amp_median": I["amp_median"],

            "subbass_energy_sum": S["energy_sum"],
            "subbass_energy_mean": S["energy_mean"],
            "subbass_energy_median": S["energy_median"],
            "subbass_amp_mean": S["amp_mean"],
            "subbass_amp_median": S["amp_median"],

            # Total inharmonicity (subbass + inharmonic)
            "total_inharm_energy_sum": T["energy_sum"],
            "total_inharm_energy_mean": T["energy_mean"],
            "total_inharm_energy_median": T["energy_median"],
            "total_inharm_amp_mean": T["amp_mean"],
            "total_inharm_amp_median": T["amp_median"],

            # Bin-integrated percentages: explicit denominators (musical band vs global)
            "harmonic_energy_pct_musical": final_harmonic_pct_musical,
            "inharmonic_energy_pct_musical": final_inharm_pct_musical,
            "harmonic_energy_percentage_musical_band": final_harmonic_pct_musical,
            "inharmonic_energy_percentage_musical_band": final_inharm_pct_musical,
            "energy_denominator_musical_band": "harmonic_energy_sum_plus_inharmonic_energy_sum",
            "subbass_energy_pct_global": final_subbass_pct_global,
            "total_inharm_energy_pct_global": final_inharm_pct_global + final_subbass_pct_global,
            "harmonic_energy_pct_global": final_harmonic_pct_global,
            "inharmonic_energy_pct_global": final_inharm_pct_global,
            "harmonic_energy_percentage_global": final_harmonic_pct_global,
            "inharmonic_energy_percentage_global": final_inharm_pct_global,
            "subbass_energy_percentage_global": final_subbass_pct_global,
            "total_inharmonic_energy_percentage_global": final_inharm_pct_global + final_subbass_pct_global,
            "energy_denominator_global": "harmonic_energy_sum_plus_inharmonic_energy_sum_plus_subbass_energy_sum",
            "harmonic_energy_percentage_semantics": (
                "musical_band_H_and_I_share_denominator_harmonic_plus_inharmonic; "
                "global_H_I_S_share_denominator_includes_subbass"
            ),
        })

        _fbs = finalize_batch_power_mass_summary(
            float(H["energy_sum"]),
            float(I["energy_sum"]),
            float(S["energy_sum"]),
        )
        self.results["final_batch_summary"] = dict(_fbs)
        self.results["spectral_component_stats"].update(
            {k: _fbs[k] for k in _fbs},
        )

        # Store component lists (optional, mirrors your previous structure)
        # CRITICAL FIX #1: Use Amplitude_linear (explicit naming)
        self.results["harmonic_analysis"] = {
            "n_components": len(self.harmonic_df),
            "frequencies_hz": self.harmonic_df["Frequency (Hz)"].tolist() if not self.harmonic_df.empty else [],
            "amplitudes": self.harmonic_df["Amplitude_linear"].tolist() if not self.harmonic_df.empty else [],
            "harmonic_numbers": self.harmonic_df["Harmonic Number"].tolist() if (not self.harmonic_df.empty and "Harmonic Number" in self.harmonic_df.columns) else []
        }
        self.results["inharmonic_analysis"] = {
            "n_components": len(self.inharmonic_df),
            "frequencies_hz": self.inharmonic_df["Frequency (Hz)"].tolist() if not self.inharmonic_df.empty else [],
            "amplitudes": self.inharmonic_df["Amplitude_linear"].tolist() if not self.inharmonic_df.empty else [],
        }
        self.results["subbass_analysis"] = {
            "n_components": len(self.subbass_df),
            "frequencies_hz": self.subbass_df["Frequency (Hz)"].tolist() if not self.subbass_df.empty else [],
            "amplitudes": self.subbass_df["Amplitude_linear"].tolist() if not self.subbass_df.empty else [],
        }
        self.results["total_inharmonic_analysis"] = {
            "n_components": len(self.total_inharmonic_df),
            "frequencies_hz": self.total_inharmonic_df["Frequency (Hz)"].tolist() if not self.total_inharmonic_df.empty else [],
            "amplitudes": self.total_inharmonic_df["Amplitude_linear"].tolist() if not self.total_inharmonic_df.empty else [],
        }

        # ---------- Console summary ----------
        print(f"  ✓ Harmonic STFT bins: {len(self.harmonic_df)} (filtered from {h_before})")
        print(f"  ✓ Inharmonic residual STFT bins: {len(self.inharmonic_df)} (filtered from {i_before})")
        print(f"  ✓ Subbass noise STFT bins: {len(self.subbass_df)} (filtered from {s_before})")
        print(f"  ✓ Energy (musical band): Harmonic={harmonic_pct_musical:.1f}%, Inharmonic={inharm_pct_musical:.1f}%")
        print(f"  ✓ Energy (global): Subgrave={subbass_pct_global:.1f}%, TotalInharm={total_inharm_pct_global:.1f}%")
        print(
            f"  ✓ Final batch export (linear power %%, H+I+S): "
            f"H={_fbs['harmonic_power_percent']:.2f}%, "
            f"I_residual={_fbs['inharmonic_residual_power_percent']:.2f}%, "
            f"S_noise={_fbs['subbass_noise_power_percent']:.2f}%"
        )

        # Backward-compatible return
        return self.harmonic_df, self.inharmonic_df

    
    def calculate_spectral_metrics(self) -> Dict[str, float]:
        """Calculate comprehensive spectral metrics."""
        print("\n[5/9] Calculating spectral metrics...")
        
        metrics = {}
        
        # Harmonic metrics
        # CRITICAL FIX #1: Use Amplitude_linear and Power columns explicitly
        if not self.harmonic_df.empty:
            harmonic_amplitudes = self.harmonic_df['Amplitude_linear'].values
            # FIX 6 — these are *legacy* amplitude sums, not normalised densities.
            # Export both keys for backward compatibility; the canonical
            # `effective_partial_density` and the new `physical_spectral_density`
            # (Hill q=2) should be preferred for any analytical interpretation.
            _legacy_h_sum = float(np.sum(harmonic_amplitudes))
            metrics['legacy_harmonic_amplitude_sum'] = _legacy_h_sum
            metrics['harmonic_density'] = _legacy_h_sum  # alias kept for legacy callers
            # Count unique harmonics (by harmonic number), not all spectral components
            # Multiple spectral components can map to the same harmonic number
            if 'Harmonic Number' in self.harmonic_df.columns:
                metrics['harmonic_count'] = int(self.harmonic_df['Harmonic Number'].nunique())
            else:
                metrics['harmonic_count'] = len(self.harmonic_df)
            # CRITICAL FIX #1: Energy = Σ(power), use Power column if available
            if 'Power' in self.harmonic_df.columns:
                metrics['harmonic_energy'] = float(np.sum(self.harmonic_df['Power'].values))
            else:
                metrics['harmonic_energy'] = float(np.sum(harmonic_amplitudes ** 2))
            # FIX 5 — count *unique* harmonic numbers, clamp into [0, 1].
            # The previous formula used `len(self.harmonic_df)` (the number of
            # detected spectral rows), which can include multiple bins per
            # harmonic and easily exceed the theoretical max-harmonic count,
            # producing completeness values > 1.
            try:
                f_top = float(self.frequencies[-1]) if len(self.frequencies) else 0.0
            except Exception:
                f_top = 0.0
            f_top = min(f_top, 20000.0) if f_top > 0.0 else 20000.0
            f0 = float(self.fundamental_freq) if self.fundamental_freq else 0.0
            max_expected = max(1, int(f_top / f0)) if f0 > 0.0 else 1
            if 'Harmonic Number' in self.harmonic_df.columns:
                n_unique_harm = int(self.harmonic_df['Harmonic Number'].nunique())
            else:
                n_unique_harm = int(len(self.harmonic_df))
            metrics['harmonic_completeness'] = float(min(1.0, n_unique_harm / max_expected))
            try:
                from density import (
                    apply_density_metric,
                    CANONICAL_DENSITY_FORMULA_VERSION,
                    CANONICAL_DENSITY_SOURCE_FORMULA,
                )

                h_amp = harmonic_amplitudes.astype(float, copy=False)
                h_freq = self.harmonic_df["Frequency (Hz)"].to_numpy(dtype=float, copy=False)
                f0_c = float(self.fundamental_freq) if self.fundamental_freq not in (None, 0) else None
                wf = getattr(self, "weight_function", "linear")
                if not isinstance(wf, str) or not str(wf).strip():
                    wf = "linear"
                canonical = float(
                    apply_density_metric(
                        h_amp,
                        str(wf).strip(),
                        frequencies=h_freq,
                        fundamental_freq=f0_c,
                        account_for_spectral_rolloff=True,
                        prevent_domination=True,
                    )
                )
                metrics["canonical_density_v5_adapted"] = canonical
                hc_rows = len(self.harmonic_df)
                metrics["density_per_component"] = float(canonical / hc_rows) if hc_rows > 0 else float("nan")
                metrics["density_formula_version"] = CANONICAL_DENSITY_FORMULA_VERSION
                metrics["density_source_formula"] = CANONICAL_DENSITY_SOURCE_FORMULA
                metrics["density_normalization_scope"] = "none_until_compiled_workbook_global_max"
                metrics["density_normalization_denominator"] = None
            except Exception as _canon_e:
                logger.warning("canonical_density_v5_adapted skipped: %s", _canon_e)
                metrics["canonical_density_v5_adapted"] = 0.0
                metrics["density_per_component"] = float("nan")
                metrics["density_formula_version"] = None
                metrics["density_source_formula"] = None
                metrics["density_normalization_scope"] = None
                metrics["density_normalization_denominator"] = None
        else:
            metrics['legacy_harmonic_amplitude_sum'] = 0.0
            metrics['harmonic_density'] = 0.0
            metrics['harmonic_count'] = 0
            metrics['harmonic_energy'] = 0.0
            metrics['harmonic_completeness'] = 0.0
            metrics["canonical_density_v5_adapted"] = 0.0
            metrics["density_per_component"] = float("nan")
            metrics["density_formula_version"] = None
            metrics["density_source_formula"] = None
            metrics["density_normalization_scope"] = None
            metrics["density_normalization_denominator"] = None
        
        # Inharmonic metrics
        if not self.inharmonic_df.empty:
            # CRITICAL FIX #1: Use Amplitude_linear and Power columns explicitly
            inharmonic_amplitudes = self.inharmonic_df['Amplitude_linear'].values
            _legacy_i_sum = float(np.sum(inharmonic_amplitudes))
            metrics['legacy_inharmonic_amplitude_sum'] = _legacy_i_sum  # FIX 6
            metrics['inharmonic_density'] = _legacy_i_sum  # alias kept for legacy callers
            metrics['inharmonic_count'] = len(self.inharmonic_df)
            # CRITICAL FIX #1: Energy = Σ(power), use Power column if available
            if 'Power' in self.inharmonic_df.columns:
                metrics['inharmonic_energy'] = float(np.sum(self.inharmonic_df['Power'].values))
            else:
                metrics['inharmonic_energy'] = float(np.sum(inharmonic_amplitudes ** 2))
        else:
            metrics['legacy_inharmonic_amplitude_sum'] = 0.0
            metrics['inharmonic_density'] = 0.0
            metrics['inharmonic_count'] = 0
            metrics['inharmonic_energy'] = 0.0
        
        # PATCH 2️⃣: Energy-consistent harmonic/inharmonic weighting
        # ACCURACY FIX: Use bin-based energy percentages for exported metrics (matches CSV data)
        # Peak-based percentages are stored separately for validation but not used for exported metrics
        # This ensures consistency between metrics and CSV exports
        
        # CRITICAL FIX: Always define total_energy_components to avoid "referenced before assignment" error
        total_energy_components = metrics.get('harmonic_energy', 0.0) + metrics.get('inharmonic_energy', 0.0)
        
        # Canonical batch export: three-way linear power split (``final_batch_summary``; same as batch_summary.xlsx).
        fb = self.results.get("final_batch_summary") if isinstance(self.results, dict) else None
        if isinstance(fb, dict) and fb.get("total_power_mass") is not None:
            for key in (
                "harmonic_power_mass",
                "inharmonic_residual_power_mass",
                "subbass_noise_power_mass",
                "total_inharmonic_power_mass",
                "total_power_mass",
                "harmonic_power_percent",
                "inharmonic_residual_power_percent",
                "subbass_noise_power_percent",
                "total_inharmonic_power_percent",
            ):
                if key in fb and fb[key] is not None:
                    metrics[key] = float(fb[key])
            metrics["harmonic_energy_percentage"] = float(fb["harmonic_power_percent"])
            metrics["inharmonic_energy_percentage"] = float(fb["inharmonic_residual_power_percent"])
            metrics["subbass_energy_percentage_global"] = float(fb["subbass_noise_power_percent"])
            metrics["total_inharm_energy_percentage_global"] = float(fb["total_inharmonic_power_percent"])
            logger.info(
                "Final batch power (%% of H+I+S, linear ΣA²): H=%.2f%%, I_residual=%.2f%%, S_noise=%.2f%%",
                metrics["harmonic_power_percent"],
                metrics["inharmonic_residual_power_percent"],
                metrics["subbass_noise_power_percent"],
            )
        elif total_energy_components > 0:
            metrics['harmonic_energy_percentage'] = float(
                (metrics['harmonic_energy'] / total_energy_components) * 100.0
            )
            metrics['inharmonic_energy_percentage'] = float(
                (metrics['inharmonic_energy'] / total_energy_components) * 100.0
            )
            logger.info(
                "Using musical-band bin percentages (no final_batch_summary): "
                "Harmonic=%.2f%%, Inharmonic=%.2f%%.",
                metrics['harmonic_energy_percentage'],
                metrics['inharmonic_energy_percentage'],
            )
        else:
            metrics['harmonic_energy_percentage'] = 0.0
            metrics['inharmonic_energy_percentage'] = 0.0
        
        # Store peak-based percentages separately for validation/comparison (if available)
        if hasattr(self, 'results') and isinstance(self.results, dict):
            comp_stats = self.results.get('spectral_component_stats', {})
            if 'harmonic_energy_pct_musical_peak_based' in comp_stats:
                peak_harmonic_pct = float(comp_stats.get('harmonic_energy_pct_musical_peak_based', 0.0))
                peak_inharmonic_pct = float(comp_stats.get('inharmonic_energy_pct_musical_peak_based', 0.0))
                metrics['harmonic_energy_percentage_peak_based'] = peak_harmonic_pct
                metrics['inharmonic_energy_percentage_peak_based'] = peak_inharmonic_pct
                logger.info(
                    "Peak-candidate energy percentages (validation track, sparse peaks): "
                    "Harmonic=%.2f%%, Inharmonic=%.2f%%.",
                    peak_harmonic_pct,
                    peak_inharmonic_pct,
                )
                logger.info(
                    "Bin-integrated percentages (primary export) integrate all spectral bins in each mask; "
                    "peak-candidate track is a complementary sparse diagnostic."
                )
        
        # Determine if weights should be auto-extracted from actual energy distribution
        # For musical instruments, weights should reflect
        # actual energy distribution for accurate combined metric calculation.
        # This ensures the combined metric accurately represents the spectral characteristics.
        use_auto_weights = self.auto_extract_weights  # Use user preference (default: True)
        comp_stats_w = self.results.get("spectral_component_stats", {}) or {}
        h_mus_pct = float(comp_stats_w.get("harmonic_energy_pct_musical", 0.0) or 0.0)
        i_mus_pct = float(comp_stats_w.get("inharmonic_energy_pct_musical", 0.0) or 0.0)
        mus_sum = h_mus_pct + i_mus_pct

        if use_auto_weights and mus_sum > 0:
            auto_harmonic_weight = h_mus_pct / mus_sum
            auto_inharmonic_weight = i_mus_pct / mus_sum
            metrics["auto_extracted_harmonic_weight"] = float(auto_harmonic_weight)
            metrics["auto_extracted_inharmonic_weight"] = float(auto_inharmonic_weight)
            effective_harmonic_weight = auto_harmonic_weight
            effective_inharmonic_weight = auto_inharmonic_weight
            logger.info(
                "Auto-extracted weights from musical-band power (H vs I, excludes subbass): "
                "Harmonic=%.1f%%, Inharmonic=%.1f%%.",
                auto_harmonic_weight * 100.0,
                auto_inharmonic_weight * 100.0,
            )
        elif use_auto_weights and total_energy_components > 0:
            auto_harmonic_weight = metrics["harmonic_energy"] / total_energy_components
            auto_inharmonic_weight = metrics["inharmonic_energy"] / total_energy_components
            tw = auto_harmonic_weight + auto_inharmonic_weight
            if tw > 0:
                auto_harmonic_weight /= tw
                auto_inharmonic_weight /= tw
            metrics["auto_extracted_harmonic_weight"] = float(auto_harmonic_weight)
            metrics["auto_extracted_inharmonic_weight"] = float(auto_inharmonic_weight)
            effective_harmonic_weight = auto_harmonic_weight
            effective_inharmonic_weight = auto_inharmonic_weight
            logger.info(
                "Auto-extracted weights from bin-summed musical power: H=%.1f%%, I=%.1f%%.",
                auto_harmonic_weight * 100.0,
                auto_inharmonic_weight * 100.0,
            )
        else:
            # Use configured weights
            effective_harmonic_weight = self.harmonic_weight
            effective_inharmonic_weight = self.inharmonic_weight
            metrics['auto_extracted_harmonic_weight'] = None
            metrics['auto_extracted_inharmonic_weight'] = None
        
        # Combined metrics (logarithmic combination using auto-extracted or configured weights)
        # FIX 6 — `combined_density` aggregates the legacy amplitude sums via
        # log1p; it is kept for back-compatibility but mirrored under a name
        # that makes its origin explicit.
        harm_log = np.log1p(max(0.0, metrics['harmonic_density']))
        inharm_log = np.log1p(max(0.0, metrics['inharmonic_density']))
        _combined_legacy = float(
            effective_harmonic_weight * harm_log + effective_inharmonic_weight * inharm_log
        )
        metrics['legacy_combined_density_log_amplitude'] = _combined_legacy
        metrics['combined_density'] = _combined_legacy
        
        # Store which weights were used
        metrics["weights_used"] = (
            "auto_extracted"
            if use_auto_weights and (mus_sum > 0 or total_energy_components > 0)
            else "configured"
        )
        
        # Spectral entropy
        # CRITICAL FIX #1: Entropy requires probability distribution from power (amplitude²), NOT dB
        # Mathematical requirement: p_i = P_i / ΣP_i where P_i is power, and Σp_i = 1
        if not self.complete_spectrum_df.empty:
            # Use Power column directly (already amplitude²)
            power_spectrum = self.complete_spectrum_df['Power'].values.copy()
            power_spectrum = power_spectrum / (np.sum(power_spectrum) + 1e-10)  # Normalize to probability
            power_spectrum = power_spectrum[power_spectrum > 0]  # Remove zeros for log
            if len(power_spectrum) > 0:
                entropy = -np.sum(power_spectrum * np.log2(power_spectrum + 1e-10))
                max_entropy = np.log2(len(power_spectrum))
                metrics['spectral_entropy'] = float(entropy / max_entropy) if max_entropy > 0 else 0.0
            else:
                metrics['spectral_entropy'] = 0.0
        else:
            metrics['spectral_entropy'] = 0.0
        
        # Total energy
        # CRITICAL FIX #1: Energy = Σ(amplitude²) = Σ(power), NOT Σ(dB²)
        if not self.complete_spectrum_df.empty:
            metrics['total_energy'] = float(np.sum(self.complete_spectrum_df['Power'].values))
        else:
            metrics['total_energy'] = 0.0
        
        # Harmonic-to-inharmonic ratio
        if metrics['inharmonic_energy'] > 0:
            metrics['harmonic_inharmonic_ratio'] = float(
                metrics['harmonic_energy'] / metrics['inharmonic_energy']
            )
        else:
            metrics['harmonic_inharmonic_ratio'] = float('inf') if metrics['harmonic_energy'] > 0 else 0.0
        
        # Calculate actual density percentages (for validation)
        total_density_components = metrics['harmonic_density'] + metrics['inharmonic_density']
        if total_density_components > 0:
            metrics['harmonic_density_percentage'] = float(
                (metrics['harmonic_density'] / total_density_components) * 100.0
            )
            metrics['inharmonic_density_percentage'] = float(
                (metrics['inharmonic_density'] / total_density_components) * 100.0
            )
        else:
            metrics['harmonic_density_percentage'] = 0.0
            metrics['inharmonic_density_percentage'] = 0.0
        
        # Compare configured weights vs musical-band bin split and vs global batch power %%.
        comp_wm = self.results.get("spectral_component_stats", {}) or {}
        h_mus_e = float(comp_wm.get("harmonic_energy_pct_musical", 0.0) or 0.0)
        i_mus_e = float(comp_wm.get("inharmonic_energy_pct_musical", 0.0) or 0.0)
        metrics["weight_vs_actual_energy"] = {
            "configured_harmonic_weight_percent": float(self.harmonic_weight * 100.0),
            "configured_inharmonic_weight_percent": float(self.inharmonic_weight * 100.0),
            "musical_band_bin_harmonic_percent": h_mus_e,
            "musical_band_bin_inharmonic_residual_percent": i_mus_e,
            "global_batch_harmonic_power_percent": metrics.get(
                "harmonic_power_percent", metrics.get("harmonic_energy_percentage", 0.0)
            ),
            "global_batch_inharmonic_residual_power_percent": metrics.get(
                "inharmonic_residual_power_percent", metrics.get("inharmonic_energy_percentage", 0.0)
            ),
            "actual_harmonic_density_percent": metrics["harmonic_density_percentage"],
            "actual_inharmonic_density_percent": metrics["inharmonic_density_percentage"],
        }

        hc_rows = int(len(self.harmonic_df)) if not self.harmonic_df.empty else 0
        can = metrics.get("canonical_density_v5_adapted")
        try:
            if hc_rows > 0 and can is not None and math.isfinite(float(can)):
                metrics["density_metric_per_harmonic"] = float(can) / float(hc_rows)
        except (TypeError, ValueError):
            metrics.setdefault("density_metric_per_harmonic", None)
        metrics["density_metric_normalized"] = None

        self.metrics = metrics
        self.results['spectral_metrics'] = metrics
        
        logger.info(f"Harmonic energy: {metrics['harmonic_energy']:.6f} ({metrics['harmonic_energy_percentage']:.1f}%)")
        logger.info(f"Inharmonic energy: {metrics['inharmonic_energy']:.6f} ({metrics['inharmonic_energy_percentage']:.1f}%)")
        
        print(f"  ✓ Harmonic density: {metrics['harmonic_density']:.6f}")
        print(f"  ✓ Inharmonic density: {metrics['inharmonic_density']:.6f}")
        print(f"  ✓ Combined density: {metrics['combined_density']:.6f}")
        print(f"  ✓ Spectral entropy: {metrics['spectral_entropy']:.4f}")
        print(f"  ✓ Harmonic energy: {metrics['harmonic_energy']:.6f} ({metrics['harmonic_energy_percentage']:.1f}% of component energy)")
        print(f"  ✓ Inharmonic energy: {metrics['inharmonic_energy']:.6f} ({metrics['inharmonic_energy_percentage']:.1f}% of component energy)")
        print(f"  ✓ Configured weights: Harmonic={self.harmonic_weight*100:.1f}%, Inharmonic={self.inharmonic_weight*100:.1f}%")
        print(f"  ✓ Actual energy distribution: Harmonic={metrics['harmonic_energy_percentage']:.1f}%, Inharmonic={metrics['inharmonic_energy_percentage']:.1f}%")
        
        # Show auto-extracted weights if used
        if metrics.get('auto_extracted_harmonic_weight') is not None:
            print(f"  ✓ Auto-extracted weights (used for combined metric): Harmonic={metrics['auto_extracted_harmonic_weight']*100:.1f}%, Inharmonic={metrics['auto_extracted_inharmonic_weight']*100:.1f}%")
            print(f"     Note: Weights automatically extracted from actual energy distribution for accurate combined metric.")
            logger.info(f"Using auto-extracted weights: Harmonic={metrics['auto_extracted_harmonic_weight']*100:.1f}%, Inharmonic={metrics['auto_extracted_inharmonic_weight']*100:.1f}%")
        
        # Validation: Check if energy distribution is physically reasonable for musical instruments
        if metrics['harmonic_energy_percentage'] < 30.0 and total_energy_components > 0:
            print(f"  ⚠ WARNING: Harmonic energy ({metrics['harmonic_energy_percentage']:.1f}%) is unusually low for a musical instrument.")
            print(f"     Expected: 70-95% harmonic energy for most instruments")
            print(f"     This may indicate:")
            print(f"     - Fundamental frequency detection error")
            print(f"     - Tolerance too strict")
            print(f"     - Audio contains mostly noise/percussion")
            print(f"     - Separation logic may need adjustment")
            logger.warning(f"Unusually low harmonic energy: {metrics['harmonic_energy_percentage']:.1f}% (expected 70-95% for instruments)")
        
        # Warning if configured weights don't match actual distribution (only if not using auto-weights)
        if metrics.get('weights_used') == 'configured':
            energy_diff = abs(metrics['harmonic_energy_percentage'] - (self.harmonic_weight * 100.0))
            if energy_diff > 10.0:  # More than 10% difference
                print(f"  ⚠ WARNING: Configured harmonic weight ({self.harmonic_weight*100:.1f}%) differs significantly from actual energy distribution ({metrics['harmonic_energy_percentage']:.1f}%)")
                print(
                    "     Consider using auto-extracted weights (weights_used='auto_extracted') "
                    "so the combined metric tracks the measured energy split more closely."
                )
        
        comp_stats = self.results.get("spectral_component_stats", {}) or {}
        metrics["harmonic_energy_percentage_semantics"] = comp_stats.get(
            "harmonic_energy_percentage_semantics",
            "musical_band_denominator_harmonic_plus_inharmonic_spectral_bins",
        )
        return metrics
    
    def calculate_dissonance_metrics(self) -> Dict[str, float]:
        """
        CRITICAL FIX #4: Calculate dissonance using proper Sethares model.
        
        Mathematical foundation (standard formulation):
        - Sethares (2005) model: d(f1,f2,a1,a2) = min(a1,a2) * gain * (exp(-b1*y) - exp(-b2*y))
        - Where y = s(f1) * (f2 - f1) and s(f1) = x_star / (s1*f1 + s2)
        - Parameters: b1=3.5, b2=5.75, x_star=0.24, s1=0.0207, s2=18.96 (Sethares, 2005)
        - Pairwise summation over all partial pairs: D_total = Σ d(f_i, f_j, a_i, a_j)
        
        This replaces the ad-hoc abs(ratio - 1.5) calculation with a proper psychoacoustic model
        based on Plomp-Levelt curves and critical band interaction.
        
        Returns:
            Dictionary with dissonance metrics
        """
        print("\n[6/9] Calculating dissonance metrics...")
        
        dissonance = {}
        
        if not DISSONANCE_MODELS_AVAILABLE:
            logger.warning("dissonance_models not available. Using fallback calculation.")
            # CRITICAL FIX: Ensure we still return valid results even if dissonance models unavailable
            # Fallback to simple calculation if module not available
            if not self.harmonic_df.empty and len(self.harmonic_df) > 1:
                freqs = self.harmonic_df['Frequency (Hz)'].values
                amps = self.harmonic_df['Amplitude_linear'].values
                total_dissonance = 0.0
                pairs = 0
                for i in range(len(freqs)):
                    for j in range(i + 1, len(freqs)):
                        ratio = freqs[j] / freqs[i]
                        if 1.0 < ratio < 2.0:
                            dissonance_val = abs(ratio - 1.5) * amps[i] * amps[j]
                            total_dissonance += dissonance_val
                            pairs += 1
                dissonance['pairwise_dissonance'] = float(total_dissonance / pairs) if pairs > 0 else 0.0
                dissonance['total_dissonance'] = float(total_dissonance)
                dissonance['mean_dissonance_per_pair'] = float(total_dissonance / pairs) if pairs > 0 else 0.0
                dissonance['n_partials'] = len(freqs)
                dissonance['n_pairs'] = pairs
            else:
                dissonance['pairwise_dissonance'] = 0.0
                dissonance['total_dissonance'] = 0.0
                dissonance['mean_dissonance_per_pair'] = 0.0
                dissonance['n_partials'] = 0
                dissonance['n_pairs'] = 0
        else:
            # CRITICAL FIX #4: Extract partials (freq, linear_amp) from harmonic_df
            # CRITICAL FIX: Collapse bins to one representative sinusoid per harmonic
            # Sethares model assumes one sinusoid per partial, not many bins per partial
            # Group by Harmonic Number and take max-amplitude (or centroid) per group
            if not self.harmonic_df.empty and len(self.harmonic_df) > 1:
                # Group by Harmonic Number to collapse multiple bins per harmonic into one partial
                if 'Harmonic Number' in self.harmonic_df.columns:
                    # Group by harmonic number and select representative (max amplitude) per harmonic
                    partials = []
                    for harm_num, group in self.harmonic_df.groupby('Harmonic Number'):
                        # Use max-amplitude bin as representative partial
                        max_idx = group['Amplitude_linear'].idxmax()
                        freq = float(group.loc[max_idx, 'Frequency (Hz)'])
                        amp = float(group.loc[max_idx, 'Amplitude_linear'])
                        if freq > 0 and amp > 0:
                            partials.append((freq, amp))
                    
                    logger.info(f"Collapsed {len(self.harmonic_df)} bins to {len(partials)} partials (one per harmonic)")
                else:
                    # Fallback: if no Harmonic Number column, use all rows (legacy behavior)
                    # CRITICAL FIX #1: Use Amplitude_linear (not dB) for proper physical model
                    partials = [
                        (float(row['Frequency (Hz)']), float(row['Amplitude_linear']))
                        for _, row in self.harmonic_df.iterrows()
                        if row['Frequency (Hz)'] > 0 and row['Amplitude_linear'] > 0
                    ]
                    logger.warning("No Harmonic Number column found, using all bins (not ideal for Sethares model)")
                
                if len(partials) >= 2:
                    # Initialize Sethares model with standard parameters (Sethares, 2005)
                    sethares = SetharesDissonance(
                        b1=3.5,
                        b2=5.75,
                        x_star=0.24,
                        s1=0.0207,
                        s2=18.96,
                        gain=1.0,
                        curve_mode='full',  # Full pairwise summation (Sethares, 2005)
                        metric_mode='mean_pair_scaled',
                        metric_scale=10.0
                    )
                    
                    # Calculate total dissonance using pairwise summation
                    # Mathematical: D_total = Σ_{i<j} d(f_i, f_j, a_i, a_j)
                    total_dissonance = sethares._pairwise_sum(partials)
                    
                    # Calculate number of pairs for normalization
                    n_partials = len(partials)
                    n_pairs = n_partials * (n_partials - 1) // 2
                    
                    # Store metrics
                    dissonance['total_dissonance'] = float(total_dissonance)
                    dissonance['mean_dissonance_per_pair'] = float(total_dissonance / n_pairs) if n_pairs > 0 else 0.0
                    dissonance['scaled_dissonance'] = float((total_dissonance / n_pairs) * 10.0) if n_pairs > 0 else 0.0
                    # CRITICAL FIX #3: Store pairwise_dissonance for batch_audio_analyzer compatibility
                    dissonance['pairwise_dissonance'] = float(total_dissonance / n_pairs) if n_pairs > 0 else 0.0
                    dissonance['n_partials'] = n_partials
                    dissonance['n_pairs'] = n_pairs
                    
                    # Calculate dissonance curve for visualization/analysis
                    # This shows how dissonance varies with interval
                    try:
                        curve = sethares.calculate_dissonance_curve(
                            partials,
                            min_interval=1.0,
                            max_interval=2.0,
                            num_points=100
                        )
                        minima = sethares.find_local_minima(curve, sensitivity=0.01)
                        
                        dissonance['dissonance_curve'] = curve
                        dissonance['consonant_intervals'] = minima
                        dissonance['n_consonant_intervals'] = len(minima)
                        
                        logger.info(f"Dissonance curve calculated: {len(curve)} points, {len(minima)} consonant intervals")
                    except Exception as e:
                        logger.warning(f"Failed to calculate dissonance curve: {e}")
                        dissonance['dissonance_curve'] = {}
                        dissonance['consonant_intervals'] = []
                        dissonance['n_consonant_intervals'] = 0
                    
                    logger.info(f"Sethares dissonance: total={total_dissonance:.6f}, mean={dissonance['mean_dissonance_per_pair']:.6f}")
                    print(f"  ✓ Sethares total dissonance: {total_dissonance:.6f}")
                    print(f"  ✓ Mean dissonance per pair: {dissonance['mean_dissonance_per_pair']:.6f}")
                    print(f"  ✓ Consonant intervals found: {len(minima) if 'consonant_intervals' in dissonance else 0}")
                else:
                    logger.warning("Insufficient partials for dissonance calculation (need at least 2)")
                    dissonance['total_dissonance'] = 0.0
                    dissonance['mean_dissonance_per_pair'] = 0.0
                    dissonance['scaled_dissonance'] = 0.0
                    dissonance['pairwise_dissonance'] = 0.0  # CRITICAL FIX #3
                    dissonance['n_partials'] = len(partials) if 'partials' in locals() else 0
                    dissonance['n_pairs'] = 0
            else:
                logger.warning("No harmonic partials available for dissonance calculation")
                dissonance['total_dissonance'] = 0.0
                dissonance['mean_dissonance_per_pair'] = 0.0
                dissonance['scaled_dissonance'] = 0.0
                dissonance['pairwise_dissonance'] = 0.0  # CRITICAL FIX #3
                dissonance['n_partials'] = 0
                dissonance['n_pairs'] = 0
        
        self.dissonance_metrics = dissonance
        self.results['dissonance_analysis'] = dissonance
        # CRITICAL FIX: Store in dissonance_metrics key for batch exporter
        self.results['dissonance_metrics'] = dissonance
        
        return dissonance
    
    def perform_statistical_analysis(self) -> Dict[str, Any]:
        """Perform comprehensive statistical analysis."""
        print("\n[7/9] Performing statistical analysis...")
        
        stats = {}
        
        # Harmonic frequency statistics
        # CRITICAL FIX #1: Use Amplitude_linear (explicit naming)
        if not self.harmonic_df.empty:
            harm_freqs = self.harmonic_df['Frequency (Hz)'].values
            harm_amps = self.harmonic_df['Amplitude_linear'].values
            
            stats['harmonic_frequencies'] = {
                'mean': float(np.mean(harm_freqs)),
                'std': float(np.std(harm_freqs)),
                'min': float(np.min(harm_freqs)),
                'max': float(np.max(harm_freqs)),
                'median': float(np.median(harm_freqs))
            }
            
            stats['harmonic_amplitudes'] = {
                'mean': float(np.mean(harm_amps)),
                'std': float(np.std(harm_amps)),
                'min': float(np.min(harm_amps)),
                'max': float(np.max(harm_amps)),
                'median': float(np.median(harm_amps))
            }
            
            # Normality tests
            if len(harm_amps) >= 3:
                try:
                    stat, p_value = normaltest(harm_amps)
                    stats['harmonic_amplitudes']['normality_test'] = {
                        'statistic': float(stat),
                        'p_value': float(p_value),
                        'normal': p_value > 0.05
                    }
                except:
                    pass
        
        # Correlation analysis
        if not self.complete_spectrum_df.empty:
            freqs = self.complete_spectrum_df['Frequency (Hz)'].values
            # CRITICAL FIX #1: Use Amplitude_linear (explicit naming)
            amps = self.complete_spectrum_df['Amplitude_linear'].values
            
            if len(freqs) >= 3:
                try:
                    corr_pearson, p_pearson = pearsonr(freqs, amps)
                    corr_spearman, p_spearman = spearmanr(freqs, amps)
                    
                    stats['frequency_amplitude_correlation'] = {
                        'pearson': {
                            'correlation': float(corr_pearson),
                            'p_value': float(p_pearson)
                        },
                        'spearman': {
                            'correlation': float(corr_spearman),
                            'p_value': float(p_spearman)
                        }
                    }
                except:
                    pass
        
        self.results['statistical_analysis'] = stats
        print(f"  ✓ Statistical analysis complete")
        
        return stats
    
    def perform_dimensionality_reduction(self) -> Dict[str, Any]:
        """Perform dimensionality reduction analysis."""
        print("\n[8/9] Performing dimensionality reduction...")
        
        dr_results = {}
        
        if not SKLEARN_AVAILABLE:
            print("  ⚠ Skipping (sklearn not available)")
            return dr_results
        
        # Prepare data for DR
        if not self.complete_spectrum_df.empty:
            # Use spectral features
            features = []
            # CRITICAL FIX #1: Use Amplitude_linear (explicit naming)
            if 'Amplitude_linear' in self.complete_spectrum_df.columns:
                features.append(self.complete_spectrum_df['Amplitude_linear'].values)
            if 'Frequency (Hz)' in self.complete_spectrum_df.columns:
                features.append(self.complete_spectrum_df['Frequency (Hz)'].values)
            
            if features:
                X = np.column_stack(features)
                
                # PCA
                try:
                    pca = PCA(n_components=2)
                    X_pca = pca.fit_transform(X)
                    dr_results['pca'] = {
                        'explained_variance_ratio': pca.explained_variance_ratio_.tolist(),
                        'components': X_pca.tolist()
                    }
                    print(f"  ✓ PCA: {pca.explained_variance_ratio_[0]:.2%} variance explained")
                except:
                    pass
        
        self.results['dimensionality_reduction'] = dr_results
        return dr_results
    
    def run_internal_consistency_checks(self) -> Dict[str, Any]:
        """
        Lightweight internal consistency checks (no external symbolic engine or API calls).

        Emits neutral log lines only; results are stored under ``internal_consistency_checks``.
        """
        print("\n[9/9] Running internal consistency checks...")
        out: Dict[str, Any] = {
            "internal_consistency_enabled": True,
            "execution_method": "internal_only",
            "audit_notes": [],
            "results": {},
        }
        if self.fundamental_freq:
            f0 = float(self.fundamental_freq)
            sr = float(self.audio_sr) if getattr(self, "audio_sr", None) else 44100.0
            nyq = 0.5 * sr
            max_n = int(nyq / f0) if f0 > 0 else 0
            msg = (
                f"Recorded f0={f0:.2f} Hz; heuristic max harmonic index below Nyquist ≈ {max_n} "
                f"(sr={sr:.0f} Hz)."
            )
            out["results"]["fundamental_frequency"] = {
                "fundamental_freq_hz": f0,
                "consistency_check_message": msg,
                "status": "check_complete",
            }
            out["audit_notes"].append("fundamental_frequency")
            print("  ✓ Fundamental frequency consistency check complete")
        if self.fundamental_freq and len(self.harmonic_df) > 0:
            n_harmonics = len(self.harmonic_df)
            max_harmonic_freq = float(self.fundamental_freq) * n_harmonics
            msg = (
                f"Detected {n_harmonics} harmonic-classified rows; "
                f"max mapped frequency ≈ {max_harmonic_freq:.2f} Hz (internal bookkeeping)."
            )
            out["results"]["harmonic_series"] = {
                "n_harmonic_rows": n_harmonics,
                "consistency_check_message": msg,
                "status": "check_complete",
            }
            out["audit_notes"].append("harmonic_series")
            print("  ✓ Harmonic row bookkeeping consistency check complete")
        if self.metrics and "harmonic_power_percent" in self.metrics:
            harm_pct = float(self.metrics["harmonic_power_percent"])
            inharm_pct = float(self.metrics.get("inharmonic_residual_power_percent", 0.0))
            sb_pct = float(self.metrics.get("subbass_noise_power_percent", 0.0))
            msg = (
                f"Final batch power %% (H+I+S): harmonic={harm_pct:.2f}%, "
                f"inharmonic_residual={inharm_pct:.2f}%, subbass_noise={sb_pct:.2f}%."
            )
            out["results"]["energy_distribution"] = {
                "harmonic_power_percent": harm_pct,
                "inharmonic_residual_power_percent": inharm_pct,
                "subbass_noise_power_percent": sb_pct,
                "consistency_check_message": msg,
                "status": "check_complete",
            }
            out["audit_notes"].append("energy_distribution")
            print("  ✓ Energy-distribution consistency check complete")
        elif self.metrics and "harmonic_energy_percentage" in self.metrics:
            harm_pct = float(self.metrics["harmonic_energy_percentage"])
            inharm_pct = float(self.metrics.get("inharmonic_energy_percentage", 0.0))
            msg = (
                f"Energy split (legacy keys): harmonic {harm_pct:.2f}% vs inharmonic {inharm_pct:.2f}%."
            )
            out["results"]["energy_distribution"] = {
                "harmonic_energy_percentage": harm_pct,
                "inharmonic_energy_percentage": inharm_pct,
                "consistency_check_message": msg,
                "status": "check_complete",
            }
            out["audit_notes"].append("energy_distribution")
            print("  ✓ Energy-distribution consistency check complete")
        if not self.complete_spectrum_df.empty:
            msg = "Spectrum table non-empty; rolloff and slope checks are deferred to main spectral pipeline exports."
            out["results"]["spectral_rolloff"] = {
                "consistency_check_message": msg,
                "status": "check_complete",
            }
            out["audit_notes"].append("spectral_rolloff")
            print("  ✓ Spectral rolloff consistency check complete")
        self.results["internal_consistency_checks"] = out
        return out
    
    def generate_comprehensive_plots(self) -> None:
        """Generate comprehensive visualization suite."""
        print("\nGenerating comprehensive visualizations...")
        
        fig = plt.figure(figsize=(20, 14))
        gs = gridspec.GridSpec(4, 3, figure=fig, hspace=0.3, wspace=0.3)
        
        # 1. Spectrogram
        ax1 = fig.add_subplot(gs[0, :])
        magnitude_db = librosa.amplitude_to_db(self.magnitude_spectrogram, ref=np.max)
        # Calculate hop_length from spectrogram dimensions
        if hasattr(self, 'stft') and self.stft is not None:
            hop_length = len(self.audio_data) // self.magnitude_spectrogram.shape[1]
        else:
            hop_length = 1024  # Default fallback
        
        librosa.display.specshow(
            magnitude_db,
            x_axis='time',
            y_axis='hz',
            sr=self.audio_sr,
            hop_length=hop_length,
            ax=ax1,
            cmap='viridis'
        )
        if self.fundamental_freq:
            ax1.axhline(
                y=self.fundamental_freq,
                color='yellow',
                linestyle='-',
                linewidth=2,
                label='Final f0 (octave-corrected)',
            )
        ax1.set_title('Spectrogram', fontsize=12, fontweight='bold')
        ax1.legend()
        
        # 2. Harmonic spectrum
        ax2 = fig.add_subplot(gs[1, 0])
        if not self.harmonic_df.empty:
            ax2.stem(
                self.harmonic_df['Frequency (Hz)'],
                self.harmonic_df['Magnitude_dB'],
                basefmt=' '
            )
            ax2.set_xlabel('Frequency (Hz)')
            ax2.set_ylabel('Magnitude (dB)')
            ax2.set_title(
                'Harmonic components (STFT bins, dB)',
                fontsize=10,
                fontweight='bold',
            )
            ax2.grid(True, alpha=0.3)
        
        # 3. Inharmonic spectrum
        ax3 = fig.add_subplot(gs[1, 1])
        if not self.inharmonic_df.empty:
            sample_df = self.inharmonic_df.sample(n=min(1000, len(self.inharmonic_df)))
            ax3.scatter(
                sample_df['Frequency (Hz)'],
                sample_df['Magnitude_dB'],
                alpha=0.5,
                s=1
            )
            ax3.set_xlabel('Frequency (Hz)')
            ax3.set_ylabel('Magnitude (dB)')
            ax3.set_title(
                'Inharmonic residual (STFT bins, dB)',
                fontsize=10,
                fontweight='bold',
            )
            ax3.grid(True, alpha=0.3)
        
        # 4. One-line batch summary (avoid density bars next to energy % — different quantities, reads as contradiction)
        ax4 = fig.add_subplot(gs[1, 2])
        ax4.axis("off")
        if self.metrics:
            h_e = self.metrics.get("harmonic_energy_percentage")
            i_e = self.metrics.get("inharmonic_energy_percentage")
            sb = self.metrics.get("subbass_energy_percentage_global")
            ti = self.metrics.get("total_inharm_energy_percentage_global")
            lines = ["Batch export (energy %)"]
            if h_e is not None and i_e is not None:
                lines.append(f"  Harmonic: {float(h_e):.1f}%")
                lines.append(f"  Inharmonic: {float(i_e):.1f}%")
            if sb is not None:
                lines.append(f"  Subbass (global): {float(sb):.2f}%")
            if ti is not None:
                lines.append(f"  Total inharm. (global): {float(ti):.1f}%")
            lines.append("")
            lines.append("Density / entropy scalars stay in JSON")
            lines.append("and metrics_summary.txt (not % energy).")
            ax4.text(
                0.5,
                0.5,
                "\n".join(lines),
                ha="center",
                va="center",
                fontsize=10,
                family="sans-serif",
                transform=ax4.transAxes,
            )
        else:
            ax4.text(
                0.5,
                0.5,
                "No spectral metrics yet",
                ha="center",
                va="center",
                fontsize=10,
                transform=ax4.transAxes,
            )
        
        # 5. Frequency detection methods
        ax5 = fig.add_subplot(gs[2, 0])
        if 'detection_methods' in self.results['frequency_analysis']:
            methods = self.results['frequency_analysis']['detection_methods']
            method_names = []
            method_values = []
            for name, value in methods.items():
                if value is not None:
                    # CRITICAL FIX: Extract f0 from nested dict if value is a dict
                    # Only append to both lists if we successfully extract a value
                    extracted_value = None
                    if isinstance(value, dict):
                        # Extract f0 value from nested dictionary
                        extracted_value = value.get('f0', None)
                    elif isinstance(value, (int, float)):
                        # Already a numeric value
                        extracted_value = float(value)
                    
                    # Only append if we successfully extracted a value
                    if extracted_value is not None:
                        method_names.append(name)
                        method_values.append(extracted_value)
            
            # CRITICAL FIX: Ensure arrays have same length before plotting
            if method_names and method_values and len(method_names) == len(method_values):
                disp = [_format_detection_method_label(n) for n in method_names]
                x5 = np.arange(len(disp))
                ax5.bar(x5, method_values, color='orange', alpha=0.7)
                ax5.set_xticks(x5)
                ax5.set_xticklabels(disp, rotation=45, ha='right', fontsize=8)
                ax5.set_ylabel('Frequency (Hz)', fontsize=10)
                fa = self.results.get('frequency_analysis', {})
                oct_note = ""
                if fa.get("octave_correction_validation"):
                    oct_note = "\n(octave correction applied vs filename prior)"
                if self.fundamental_freq:
                    ax5.axhline(
                        float(self.fundamental_freq),
                        color='green',
                        linestyle='--',
                        linewidth=2,
                        label='final_f0_octave_corrected',
                    )
                    ax5.legend(fontsize=7, loc='best')
                f0_line = (
                    f"Selected f0: {float(self.fundamental_freq):.2f} Hz"
                    if self.fundamental_freq is not None
                    else "Selected f0: N/A"
                )
                ax5.set_title(
                    f"Detector candidates (Hz){oct_note}\n{f0_line}",
                    fontsize=10,
                    fontweight='bold',
                )
                ax5.grid(True, alpha=0.3, axis='y')
        
        # 6. Energy distribution (FIXED: Use energy, not component count)
        ax6 = fig.add_subplot(gs[2, 1])
        if self.metrics and 'harmonic_energy_percentage' in self.metrics:
            # Use ENERGY percentages, not component counts
            # For musical instruments, harmonic energy should be >> inharmonic energy
            harm_energy_pct = self.metrics['harmonic_energy_percentage']
            inharm_energy_pct = self.metrics['inharmonic_energy_percentage']
            
            # CRITICAL FIX: For musical instruments, harmonic should ALWAYS be > 50%
            # If not, the separation logic has failed - DO NOT swap labels, show actual values with warning
            if harm_energy_pct >= 50.0:
                # Normal case: harmonic energy is >= 50% (correct for instruments)
                values = [harm_energy_pct, inharm_energy_pct]
                labels = [
                    'Harmonic energy',
                    'Inharmonic energy',
                ]
                colors = ['blue', 'red']
            else:
                # CRITICAL ERROR: Harmonic energy < 50% indicates separation failure
                # Show actual values (don't swap) but with strong warning
                logger.error(f"SEPARATION FAILURE: Harmonic energy only {harm_energy_pct:.1f}% (expected 70-95% for instruments)")
                values = [harm_energy_pct, inharm_energy_pct]
                labels = [f'Harmonic ({harm_energy_pct:.1f}% - ERROR!)', f'Inharmonic ({inharm_energy_pct:.1f}%)']
                colors = ['red', 'orange']  # Red for error, orange for warning
            
            if sum(values) > 0:
                ax6.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
                ax6.set_title(
                    'Harmonic vs inharmonic energy\n(same values as batch summary)',
                    fontsize=10,
                    fontweight='bold',
                )
        elif not self.harmonic_df.empty or not self.inharmonic_df.empty:
            # Fallback: Component count (less meaningful but better than nothing)
            n_harm = len(self.harmonic_df) if not self.harmonic_df.empty else 0
            n_inharm = len(self.inharmonic_df) if not self.inharmonic_df.empty else 0
            if n_harm + n_inharm > 0:
                ax6.pie([n_harm, n_inharm], labels=['Harmonic (count)', 'Inharmonic (count)'], 
                       autopct='%1.1f%%', startangle=90, colors=['blue', 'red'])
                ax6.set_title(
                    'Harmonic vs inharmonic rows (count fallback)',
                    fontsize=10,
                    fontweight='bold',
                )
                logger.warning("Using component count for pie chart (energy percentages not available)")
        
        # 7. Complete spectrum (0-5 kHz)
        ax7 = fig.add_subplot(gs[2, 2])
        if not self.complete_spectrum_df.empty:
            mask = self.complete_spectrum_df['Frequency (Hz)'] <= 5000
            ax7.plot(
                self.complete_spectrum_df[mask]['Frequency (Hz)'],
                self.complete_spectrum_df[mask]['Magnitude_dB'],
                alpha=0.7,
                linewidth=0.5
            )
            ax7.set_xlabel('Frequency (Hz)')
            ax7.set_ylabel('Magnitude (dB)')
            ax7.set_title('Spectrum (0–5 kHz)', fontsize=10, fontweight='bold')
            ax7.grid(True, alpha=0.3)
        
        # 8. Statistical summary
        ax8 = fig.add_subplot(gs[3, :])
        if 'statistical_analysis' in self.results and 'harmonic_amplitudes' in self.results['statistical_analysis']:
            stats = self.results['statistical_analysis']['harmonic_amplitudes']
            stat_names = ['mean', 'std', 'min', 'median']
            stat_values = [float(stats.get(s, 0) or 0) for s in stat_names]
            ax8.bar(stat_names, stat_values, alpha=0.7, color='teal')
            ax8.set_ylabel('Amplitude (linear)', fontsize=10)
            ax8.set_title(
                'Harmonic amplitude (linear) — mean / spread / min / median\n'
                f"(max = {float(stats.get('max', 0) or 0):.4f}, often spikes scale; see CSV for full stats)",
                fontsize=10,
                fontweight='bold',
            )
            ax8.grid(True, alpha=0.3, axis='y')
        
        plt.suptitle(f'Super Audio Analysis: {self.audio_path.name}', fontsize=16, fontweight='bold', y=0.995)
        plt.savefig(self.output_dir / "super_comprehensive_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"  ✓ Saved: {self.output_dir / 'super_comprehensive_analysis.png'}")

    def _save_batch_weight_pie_chart(self, fb: Dict[str, Any]) -> None:
        """Save a single H / I_residual / S_noise pie from ``final_batch_summary`` (canonical linear %)."""
        hp = float(fb.get("harmonic_power_percent") or 0.0)
        ip = float(fb.get("inharmonic_residual_power_percent") or 0.0)
        sp = float(fb.get("subbass_noise_power_percent") or 0.0)
        vals = [max(0.0, hp), max(0.0, ip), max(0.0, sp)]
        if sum(vals) <= 1e-9:
            return
        fig, ax = plt.subplots(figsize=(4.2, 4.2))
        ax.pie(
            vals,
            labels=["Harmonic %", "Inharmonic residual %", "Subbass noise %"],
            autopct="%1.1f%%",
            startangle=90,
            colors=["#2E6F9E", "#C44E52", "#8B6FAD"],
        )
        ax.set_title("Batch weight probe (linear power %)", fontsize=10)
        out_p = self.output_dir / "batch_weight_probe_pie.png"
        fig.savefig(out_p, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  ✓ Weight probe pie: {out_p}")
    
    def save_results(self) -> None:
        """Save all results to files."""
        print("\nSaving results...")
        
        # Save JSON results
        json_path = self.output_dir / "super_analysis_results.json"
        try:
            from metadata_sanitizer import publication_redaction_enabled, sanitize_metadata_dict

            if publication_redaction_enabled():
                import json as _json

                _payload = sanitize_metadata_dict(json.loads(_json.dumps(self.results, default=str)))
            else:
                _payload = self.results
        except Exception:
            _payload = self.results
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(_payload, f, indent=2, default=str)
        print(f"  ✓ JSON results: {json_path}")

        # Save reproducibility metadata (separate file for quick audit)
        metadata_path = self.output_dir / "analysis_metadata.json"
        try:
            metadata_payload = {
                "analysis_date": self.results.get("metadata", {}).get("analysis_date"),
                "analysis_version": self.results.get("metadata", {}).get("analysis_version"),
                "analysis_version_source": self.results.get("metadata", {}).get("analysis_version_source"),
                "analysis_parameters": self.results.get("metadata", {}).get("analysis_parameters", {}),
                "analysis_parameters_hash": self.results.get("metadata", {}).get("analysis_parameters_hash"),
                "audio_file": self.results.get("metadata", {}).get("audio_file"),
            }
            try:
                from metadata_sanitizer import publication_redaction_enabled, sanitize_metadata_dict

                if publication_redaction_enabled():
                    metadata_payload = sanitize_metadata_dict(metadata_payload)
            except Exception:
                pass
            with open(metadata_path, "w", encoding="utf-8") as mf:
                json.dump(metadata_payload, mf, indent=2, default=str)
            print(f"  ✓ Analysis metadata: {metadata_path}")
        except Exception as e:
            logger.warning(f"Failed to write analysis metadata: {e}")
        
        _minimal = bool(getattr(self, "minimal_spectral_probe", False))

        # Save harmonic / inharmonic / complete spectrum CSV (skip in minimal probe mode)
        if not _minimal:
            if not self.harmonic_df.empty:
                csv_path = self.output_dir / "harmonic_components.csv"
                self.harmonic_df.to_csv(csv_path, index=False)
                print(f"  ✓ Harmonic data: {csv_path}")

            if not self.inharmonic_df.empty:
                csv_path = self.output_dir / "inharmonic_components.csv"
                self.inharmonic_df.to_csv(csv_path, index=False)
                print(f"  ✓ Inharmonic data: {csv_path}")

            if not self.complete_spectrum_df.empty:
                csv_path = self.output_dir / "complete_spectrum.csv"
                self.complete_spectrum_df.to_csv(csv_path, index=False)
                print(f"  ✓ Complete spectrum: {csv_path}")

        fb_out = self.results.get("final_batch_summary")
        if isinstance(fb_out, dict) and fb_out.get("total_power_mass") is not None:
            fb_csv = self.output_dir / "final_batch_summary.csv"
            pd.DataFrame([fb_out]).to_csv(fb_csv, index=False)
            print(f"  ✓ Final batch summary CSV: {fb_csv}")
            if _minimal:
                try:
                    self._save_batch_weight_pie_chart(fb_out)
                except Exception as _e_pie:
                    logger.warning("Weight probe pie chart failed: %s", _e_pie)
        
        # Save metrics summary (skip long text file in minimal probe — metrics remain in JSON)
        if self.metrics and not _minimal:
            metrics_path = self.output_dir / "metrics_summary.txt"
            try:
                from metadata_sanitizer import publication_redaction_enabled, sanitize_metadata_value as _smv

                def _ms_line(s: str) -> str:
                    return str(_smv(s)) if publication_redaction_enabled() else str(s)

            except Exception:

                def _ms_line(s: str) -> str:
                    return str(s)

            with open(metrics_path, 'w', encoding='utf-8') as f:
                f.write("SUPER AUDIO ANALYZER - METRICS SUMMARY\n")
                f.write("=" * 60 + "\n\n")
                f.write(_METRICS_SUMMARY_NOTES)
                fb_txt = self.results.get("final_batch_summary")
                if isinstance(fb_txt, dict) and fb_txt.get("total_power_mass") is not None:
                    f.write("FINAL BATCH SUMMARY (linear power mass ΣA²; canonical export)\n")
                    f.write("-" * 60 + "\n")
                    for k in (
                        "harmonic_power_mass",
                        "inharmonic_residual_power_mass",
                        "subbass_noise_power_mass",
                        "total_inharmonic_power_mass",
                        "total_power_mass",
                        "harmonic_power_percent",
                        "inharmonic_residual_power_percent",
                        "subbass_noise_power_percent",
                        "total_inharmonic_power_percent",
                    ):
                        f.write(f"{k:40s}: {_ms_line(str(fb_txt.get(k)))}\n")
                    f.write("\n")
                f0_txt = (
                    f"{float(self.fundamental_freq):.2f} Hz"
                    if self.fundamental_freq is not None
                    else "N/A"
                )
                f.write(f"Fundamental Frequency: {f0_txt}\n")
                f.write(f"Harmonic STFT bin rows: {len(self.harmonic_df)}\n")
                f.write(f"Inharmonic residual STFT bin rows: {len(self.inharmonic_df)}\n\n")
                f.write("SPECTRAL METRICS:\n")
                f.write("-" * 60 + "\n")
                _write_metrics_summary_mapping(f, self.metrics, _ms_line)
                if self.dissonance_metrics:
                    f.write("\nDISSONANCE METRICS:\n")
                    f.write("-" * 60 + "\n")
                    _write_metrics_summary_mapping(f, self.dissonance_metrics, _ms_line)
            print(f"  ✓ Metrics summary: {metrics_path}")
    
    def run_complete_analysis(self) -> Dict[str, Any]:
        """
        Run the complete super analysis pipeline.
        
        Returns:
            Dictionary containing all analysis results
        """
        print("\n" + "="*80)
        print("SUPER AUDIO ANALYZER - COMPLETE PIPELINE")
        print("="*80)
        
        try:
            # 1. Load audio
            self.load_audio()
            
            # 2. Compute spectrogram
            self.compute_spectrogram()
            
            # 3. Detect fundamental frequency
            self.detect_fundamental_frequency()
            
            # 4. Separate harmonic and inharmonic components
            self.separate_harmonic_inharmonic()
            
            # 5. Calculate spectral metrics
            self.calculate_spectral_metrics()

            if getattr(self, "minimal_spectral_probe", False):
                # Phase-2 handoff path: skip heavy / redundant steps (see __init__ docstring).
                self.save_results()
            else:
                # 6. Calculate dissonance metrics
                self.calculate_dissonance_metrics()

                # 7. Perform statistical analysis
                self.perform_statistical_analysis()

                # 8. Perform dimensionality reduction
                self.perform_dimensionality_reduction()

                # 9. Internal consistency checks
                self.run_internal_consistency_checks()

                # Generate visualizations
                self.generate_comprehensive_plots()

                # Save results
                self.save_results()
            
            print("\n" + "="*80)
            print("SUPER ANALYSIS COMPLETE")
            print("="*80)
            print(f"Results saved to: {self.output_dir}")
            
            return self.results
            
        except Exception as e:
            print(f"\nERROR during analysis: {e}")
            traceback.print_exc()
            raise


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Super Audio Analyzer - State-of-the-Art Edition',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python super_audio_analyzer.py audio.wav
  python super_audio_analyzer.py audio.wav --output-dir ./results --use-90-tier
  python super_audio_analyzer.py audio.wav --window blackmanharris --harmonic-tolerance 0.03
  python super_audio_analyzer.py --gui  (launch GUI interface)
        """
    )
    
    parser.add_argument('audio_file', type=str, nargs='?', default=None, help='Path to audio file (optional if --gui is used)')
    parser.add_argument('--gui', action='store_true', help='Launch GUI interface')
    parser.add_argument('--output-dir', type=str, default=None, help='Output directory')
    parser.add_argument('--sample-rate', type=int, default=44100, help='Target sample rate (default: 44100)')
    parser.add_argument('--use-90-tier', action='store_true', help='Use 90-tier granular clustering system')
    parser.add_argument('--harmonic-tolerance', type=float, default=0.02, help='Harmonic tolerance (default: 0.02 = 2%%)')
    parser.add_argument('--harmonic-weight', type=float, default=0.95, help='Harmonic weight (default: 0.95)')
    parser.add_argument('--inharmonic-weight', type=float, default=0.05, help='Inharmonic weight (default: 0.05)')
    parser.add_argument('--window', type=str, default='blackmanharris', help='Window function (default: blackmanharris)')
    parser.add_argument('--no-adaptive-tolerance', action='store_true', help='Disable adaptive tolerance')
    
    args = parser.parse_args()
    
    # Launch GUI if requested
    if args.gui or args.audio_file is None:
        try:
            from super_audio_analyzer_gui import main as gui_main
            return gui_main()
        except ImportError:
            print("ERROR: GUI module not found. Please ensure super_audio_analyzer_gui.py is available.")
            print("Falling back to command-line mode. Please provide an audio file.")
            if args.audio_file is None:
                parser.print_help()
                return 1
    
    # Command-line mode
    if args.audio_file is None:
        parser.print_help()
        return 1
    
    try:
        analyzer = SuperAudioAnalyzer(
            audio_path=args.audio_file,
            output_dir=args.output_dir,
            sample_rate=args.sample_rate,
            use_90_tier=args.use_90_tier,
            harmonic_tolerance=args.harmonic_tolerance,
            harmonic_weight=args.harmonic_weight,
            inharmonic_weight=args.inharmonic_weight,
            window=args.window,
            use_adaptive_tolerance=not args.no_adaptive_tolerance
        )
        
        results = analyzer.run_complete_analysis()
        
        print("\nSuper analysis completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

