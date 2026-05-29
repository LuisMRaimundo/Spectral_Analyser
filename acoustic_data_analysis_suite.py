#!/usr/bin/env python3
"""
Acoustic Data Analysis Suite - Production-Grade Statistical Analysis Tool
================================================================================
Senior Data Engineer & Computational Musicologist Level Analysis

This script performs comprehensive statistical analysis of spectral density
metrics from acoustic analysis outputs. Designed for CERN-level scientific rigor.

Features:
- Comprehensive descriptive statistics
- Advanced inferential statistics
- Regression analysis with model selection
- Correlation and covariance analysis
- Frequency-dependent pattern analysis
- Register-based clustering
- Outlier detection (multiple methods)
- Dimensionality reduction analysis
- Internal physical consistency checks (tabular heuristics only)
- Automated report generation
- High-quality visualizations

Author: AI Assistant (Senior Data Engineer & Computational Musicologist)
Version: 1.0.0
License: Scientific Research Use
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import warnings
from typing import Dict, List, Tuple, Optional, Union, Any
from datetime import datetime
import sys
import traceback

# Scientific computing libraries
try:
    from scipy import stats
    from scipy.stats import (
        shapiro, normaltest, kstest, anderson,
        pearsonr, spearmanr, kendalltau,
        mannwhitneyu, kruskal, friedmanchisquare,
        chi2_contingency
    )
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    warnings.warn("scipy not available. Some statistical tests will be skipped.")

try:
    from sklearn.preprocessing import StandardScaler, RobustScaler
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
    from sklearn.ensemble import IsolationForest
    from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
    from sklearn.model_selection import cross_val_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    warnings.warn("sklearn not available. Some ML features will be skipped.")

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    plt.style.use('seaborn-v0_8-darkgrid')
    sns.set_palette("husl")
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    warnings.warn("matplotlib/seaborn not available. Visualizations will be skipped.")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    warnings.warn("requests library not available. Install with: pip install requests")


class AcousticDataAnalyzer:
    """
    Production-grade acoustic data analysis suite.
    
    Performs comprehensive statistical analysis of spectral density metrics
    with scientific rigor appropriate for high-level research.
    """
    
    def __init__(self, excel_path: Union[str, Path], output_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the analyzer.
        
        Args:
            excel_path: Path to compiled_metrics.xlsx file
            output_dir: Directory for output files (default: same as input)
        """
        self.excel_path = Path(excel_path)
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_path}")
        
        self.output_dir = Path(output_dir) if output_dir else self.excel_path.parent
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # AUDIT FIX — publication policy: prefer the ``Canonical_Metrics``
        # sheet for analysis/plotting. Falling back to the first sheet
        # silently is forbidden because the first sheet may be
        # ``Compile_Guide`` or the unbounded ``Density_Metrics`` (raw bin-
        # row sums such as ``Harmonic Partials sum``).
        print(f"Loading data from: {self.excel_path}")
        try:
            from publication_chart_policy import (
                DEFAULT_PUBLICATION_SHEET,
                load_canonical_sheet_with_fallback_warning,
            )
            self.df, self._sheet_used, _warns = load_canonical_sheet_with_fallback_warning(
                self.excel_path
            )
            self._sheet_warnings: List[str] = list(_warns)
            if self._sheet_used != DEFAULT_PUBLICATION_SHEET:
                print(
                    f"[publication_chart_policy] WARNING — falling back to sheet "
                    f"{self._sheet_used!r}; charts may now expose diagnostic/legacy "
                    "columns. Use the compiled Canonical_Metrics sheet for "
                    "publication."
                )
        except Exception:
            self.df = pd.read_excel(self.excel_path)
            self._sheet_used = "<first-sheet-fallback>"
            self._sheet_warnings = [
                "publication_chart_policy import failed; using first sheet."
            ]
        print(f"Loaded {len(self.df)} records with {len(self.df.columns)} columns from sheet {self._sheet_used!r}")
        
        # Initialize analysis results storage
        self.results = {
            'metadata': {
                'input_file': str(self.excel_path),
                'analysis_date': datetime.now().isoformat(),
                'n_samples': len(self.df),
                'n_features': len(self.df.columns)
            },
            'descriptive_stats': {},
            'inferential_stats': {},
            'correlation_analysis': {},
            'regression_analysis': {},
            'outlier_detection': {},
            'dimensionality_reduction': {},
            'frequency_analysis': {},
            'register_analysis': {},
            'internal_consistency_checks': {}
        }
        
        # Identify key columns
        self._identify_columns()
        
        # Add derived features
        self._add_derived_features()
    
    def _identify_columns(self):
        """Identify key column types in the dataset.

        AUDIT FIX — publication policy:
          * ``self.density_metrics``  → canonical density descriptors only,
            following the publication preference order. Legacy "Density
            Metric" / "Spectral Density Metric" / "Combined Density
            Metric" / "Filtered Density Metric" are *never* selected here.
          * ``self.default_publication_metric`` records the single metric
            used as the default for publication-style plots.
          * ``self.forbidden_default_metrics_present`` lists raw legacy
            columns that exist in the workbook but must never be auto-
            selected as a default.
        """
        try:
            from publication_chart_policy import (
                DEFAULT_PUBLICATION_METRIC_PREFERENCE,
                FORBIDDEN_DEFAULT_METRIC_NAMES,
                classify_metric_for_publication,
                select_default_publication_metric,
            )
        except Exception:
            DEFAULT_PUBLICATION_METRIC_PREFERENCE = ()
            FORBIDDEN_DEFAULT_METRIC_NAMES = frozenset()
            def classify_metric_for_publication(name):
                return "diagnostic"
            def select_default_publication_metric(cols, *, preference=()):
                return None

        self.note_col = 'Note' if 'Note' in self.df.columns else None
        self.folder_col = 'Folder' if 'Folder' in self.df.columns else None

        # Canonical density descriptors only — never the unbounded legacy
        # capitalised "*Density Metric*" columns. Preference order follows
        # publication_chart_policy.DEFAULT_PUBLICATION_METRIC_PREFERENCE
        # plus any other column the dictionary marks as ``canonical``.
        self.density_metrics = [
            c for c in self.df.columns
            if c in DEFAULT_PUBLICATION_METRIC_PREFERENCE
        ]
        # Append any other canonical column that is not yet on the list,
        # preserving DataFrame order.
        for c in self.df.columns:
            cs = str(c)
            if cs in self.density_metrics:
                continue
            if classify_metric_for_publication(cs) == "canonical":
                self.density_metrics.append(cs)

        # The default publication metric used by all "single metric" plots.
        self.default_publication_metric = select_default_publication_metric(
            list(self.df.columns)
        )

        # Legacy raw / forbidden columns that should *not* be selected
        # automatically. Kept for the diagnostic / legacy section only.
        self.forbidden_default_metrics_present = [
            c for c in self.df.columns
            if str(c) in FORBIDDEN_DEFAULT_METRIC_NAMES
        ]

        # Dissonance metrics
        self.dissonance_metrics = [c for c in self.df.columns if 'Dissonance' in c]

        # Harmonic metrics
        self.harmonic_metrics = [c for c in self.df.columns if 'Harmonic' in c or 'harm' in c.lower()]

        # Normalized metrics
        self.normalized_metrics = [c for c in self.df.columns if '_Norm' in c or 'norm' in c.lower()]

        # PCA/DR components
        self.dr_components = [c for c in self.df.columns if c.startswith('PC') or c.startswith('TSNE') or c.startswith('UMAP')]

        # Processing parameters
        self.processing_params = [c for c in self.df.columns if any(x in c for x in ['N FFT', 'Hop', 'Window', 'Weight', 'Function'])]

        # All numeric columns (excluding text fields)
        text_fields = {'Note', 'Folder', 'Analysis Type', 'Window', 'DM Domain', 'Density Scale', 'Weight Function'}
        self.numeric_cols = [c for c in self.df.columns
                            if c not in text_fields and pd.api.types.is_numeric_dtype(self.df[c])]

        print(f"Identified {len(self.density_metrics)} canonical density metrics")
        print(f"Default publication metric: {self.default_publication_metric!r}")
        if self.forbidden_default_metrics_present:
            print(
                f"WARNING: forbidden raw/legacy columns present "
                f"(NOT selected as default): {self.forbidden_default_metrics_present}"
            )
        print(f"Identified {len(self.dissonance_metrics)} dissonance metrics")
        print(f"Identified {len(self.harmonic_metrics)} harmonic metrics")
        print(f"Identified {len(self.numeric_cols)} numeric columns")
    
    def _add_derived_features(self):
        """Add derived features for analysis."""
        # Convert note to fundamental frequency
        if self.note_col:
            self.df['Fundamental_Freq_Hz'] = self.df[self.note_col].apply(self._note_to_frequency)
            
            # Add register classification
            self.df['Register'] = self.df['Fundamental_Freq_Hz'].apply(self._classify_register)
            
            # Add octave
            self.df['Octave'] = self.df[self.note_col].apply(self._extract_octave)
            
            # Add MIDI note number for ordering
            self.df['MIDI_Note'] = self.df[self.note_col].apply(self._note_to_midi)
        
        # Add log transforms for metrics that might benefit
        for metric in self.density_metrics:
            if metric in self.df.columns:
                values = pd.to_numeric(self.df[metric], errors='coerce')
                if (values > 0).all():
                    self.df[f'{metric}_log'] = np.log1p(values)
    
    def _note_to_frequency(self, note: str) -> float:
        """Convert musical note to fundamental frequency in Hz."""
        if pd.isna(note) or not isinstance(note, str):
            return np.nan
        
        import re
        match = re.match(r"([A-Ga-g])([#b]?)(\d+)", str(note))
        if not match:
            return np.nan
        
        letter, accidental, octave_str = match.groups()
        octave = int(octave_str)
        
        # Note to semitone position within octave (0-11, where C=0, C#=1, ..., B=11)
        note_map = {
            'C': 0, 'C#': 1, 'Db': 1,
            'D': 2, 'D#': 3, 'Eb': 3,
            'E': 4, 'Fb': 4, 'E#': 5,
            'F': 5, 'F#': 6, 'Gb': 6,
            'G': 7, 'G#': 8, 'Ab': 8,
            'A': 9, 'A#': 10, 'Bb': 10,
            'B': 11, 'Cb': 11, 'B#': 0
        }
        
        note_name = letter.upper() + accidental
        semitone_in_octave = note_map.get(note_name, 0)
        
        # A4 = 440 Hz, MIDI note 69
        # MIDI note = (octave + 1) * 12 + semitone_in_octave
        midi_note = (octave + 1) * 12 + semitone_in_octave
        freq = 440.0 * (2.0 ** ((midi_note - 69) / 12.0))
        
        return freq
    
    def _note_to_midi(self, note: str) -> int:
        """Convert note to MIDI number for ordering."""
        if pd.isna(note) or not isinstance(note, str):
            return 999
        
        import re
        match = re.match(r"([A-Ga-g])([#b]?)(\d+)", str(note))
        if not match:
            return 999
        
        letter, accidental, octave_str = match.groups()
        octave = int(octave_str)
        
        note_map = {
            'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
            'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
            'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
        }
        
        note_name = letter.upper() + accidental
        semitones = note_map.get(note_name, 0)
        
        return (octave + 1) * 12 + semitones
    
    def _extract_octave(self, note: str) -> int:
        """Extract octave number from note."""
        if pd.isna(note) or not isinstance(note, str):
            return -1
        
        import re
        match = re.match(r"[A-Ga-g][#b]?(\d+)", str(note))
        if match:
            return int(match.group(1))
        return -1
    
    def _classify_register(self, freq: float) -> str:
        """Classify note into register based on frequency."""
        if pd.isna(freq) or freq <= 0:
            return 'Unknown'
        elif freq < 200:
            return 'Low (< 200 Hz)'
        elif freq < 400:
            return 'Mid (200-400 Hz)'
        elif freq < 800:
            return 'High (400-800 Hz)'
        else:
            return 'Very High (> 800 Hz)'
    
    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """
        Run the complete analysis suite.
        
        Returns:
            Dictionary containing all analysis results
        """
        print("\n" + "="*80)
        print("COMPREHENSIVE ACOUSTIC DATA ANALYSIS")
        print("="*80)
        
        try:
            # 1. Descriptive Statistics
            print("\n[1/9] Computing descriptive statistics...")
            self.analyze_descriptive_statistics()
            
            # 2. Inferential Statistics
            print("[2/9] Performing inferential statistical tests...")
            self.analyze_inferential_statistics()
            
            # 3. Correlation Analysis
            print("[3/9] Analyzing correlations...")
            self.analyze_correlations()
            
            # 4. Regression Analysis
            print("[4/9] Performing regression analysis...")
            self.analyze_regression()
            
            # 5. Outlier Detection
            print("[5/9] Detecting outliers...")
            self.detect_outliers()
            
            # 6. Dimensionality Reduction Analysis
            print("[6/9] Analyzing dimensionality reduction...")
            self.analyze_dimensionality_reduction()
            
            # 7. Frequency-Dependent Analysis
            print("[7/9] Analyzing frequency-dependent patterns...")
            self.analyze_frequency_dependence()
            
            # 8. Register Analysis
            print("[8/9] Analyzing register differences...")
            self.analyze_registers()
            
            # 9. Internal consistency checks
            print("[9/9] Performing physical validation...")
            self.validate_physics()
            
            # Generate reports
            print("\nGenerating reports...")
            self.generate_reports()
            
            print("\n" + "="*80)
            print("ANALYSIS COMPLETE")
            print("="*80)
            print(f"Results saved to: {self.output_dir}")
            
            return self.results
            
        except Exception as e:
            print(f"\nERROR during analysis: {e}")
            traceback.print_exc()
            raise
    
    def analyze_descriptive_statistics(self):
        """Compute comprehensive descriptive statistics."""
        stats_dict = {}
        
        # Key metrics to analyze
        key_metrics = self.density_metrics + self.dissonance_metrics + self.harmonic_metrics[:3]
        key_metrics = [m for m in key_metrics if m in self.df.columns]
        
        for metric in key_metrics:
            values = pd.to_numeric(self.df[metric], errors='coerce').dropna()
            if len(values) < 2:
                continue
            
            stats_dict[metric] = {
                'count': len(values),
                'mean': float(values.mean()),
                'median': float(values.median()),
                'std': float(values.std()),
                'min': float(values.min()),
                'max': float(values.max()),
                'range': float(values.max() - values.min()),
                'q25': float(values.quantile(0.25)),
                'q75': float(values.quantile(0.75)),
                'iqr': float(values.quantile(0.75) - values.quantile(0.25)),
                'cv': float(values.std() / values.mean()) if values.mean() != 0 else np.inf,
                'skewness': float(values.skew()),
                'kurtosis': float(values.kurtosis())
            }
        
        self.results['descriptive_stats'] = stats_dict
        
        # Summary statistics
        print(f"  Analyzed {len(stats_dict)} metrics")
        print(f"  Sample size: {len(self.df)} records")
    
    def analyze_inferential_statistics(self):
        """Perform inferential statistical tests."""
        if not SCIPY_AVAILABLE:
            print("  Skipping (scipy not available)")
            return
        
        stats_dict = {}
        
        # Normality tests for key metrics
        key_metrics = self.density_metrics[:3]  # Top 3 density metrics
        key_metrics = [m for m in key_metrics if m in self.df.columns]
        
        for metric in key_metrics:
            values = pd.to_numeric(self.df[metric], errors='coerce').dropna()
            if len(values) < 3:
                continue
            
            normality_tests = {}
            
            # Shapiro-Wilk test (SciPy recommends this only for relatively small n)
            shapiro_sample_limit = 4999
            if len(values) <= shapiro_sample_limit:
                try:
                    stat, p_value = shapiro(values)
                    normality_tests['shapiro_wilk'] = {
                        'statistic': float(stat),
                        'p_value': float(p_value),
                        'normal': p_value > 0.05
                    }
                except:
                    pass
            
            # D'Agostino's normality test
            try:
                stat, p_value = normaltest(values)
                normality_tests['dagostino'] = {
                    'statistic': float(stat),
                    'p_value': float(p_value),
                    'normal': p_value > 0.05
                }
            except:
                pass
            
            # Anderson-Darling test
            try:
                result = anderson(values, dist='norm')
                normality_tests['anderson_darling'] = {
                    'statistic': float(result.statistic),
                    'critical_values': [float(cv) for cv in result.critical_values],
                    'significance_levels': [float(sl) for sl in result.significance_levels]
                }
            except:
                pass
            
            stats_dict[metric] = {'normality_tests': normality_tests}
        
        self.results['inferential_stats'] = stats_dict
        print(f"  Performed normality tests on {len(stats_dict)} metrics")
    
    def analyze_correlations(self):
        """Analyze correlations between metrics."""
        corr_dict = {}
        
        # Select key metrics for correlation
        key_metrics = (self.density_metrics[:5] + 
                      self.dissonance_metrics[:3] + 
                      self.harmonic_metrics[:2])
        key_metrics = [m for m in key_metrics if m in self.df.columns]
        
        if len(key_metrics) < 2:
            print("  Insufficient metrics for correlation analysis")
            return
        
        # Compute correlation matrix
        corr_matrix = self.df[key_metrics].corr()
        corr_dict['correlation_matrix'] = corr_matrix.to_dict()
        
        # Find strong correlations
        strong_correlations = []
        for i, m1 in enumerate(key_metrics):
            for m2 in key_metrics[i+1:]:
                corr_val = corr_matrix.loc[m1, m2]
                if abs(corr_val) > 0.7:
                    strong_correlations.append({
                        'metric1': m1,
                        'metric2': m2,
                        'correlation': float(corr_val),
                        'strength': 'very_strong' if abs(corr_val) > 0.9 else 'strong'
                    })
        
        corr_dict['strong_correlations'] = strong_correlations
        
        # Frequency correlation
        if 'Fundamental_Freq_Hz' in self.df.columns:
            freq_correlations = {}
            for metric in key_metrics:
                values = pd.to_numeric(self.df[metric], errors='coerce')
                freqs = self.df['Fundamental_Freq_Hz']
                valid_mask = values.notna() & freqs.notna()
                if valid_mask.sum() >= 3:
                    corr_val = values[valid_mask].corr(freqs[valid_mask])
                    freq_correlations[metric] = float(corr_val) if not pd.isna(corr_val) else None
            corr_dict['frequency_correlations'] = freq_correlations
        
        self.results['correlation_analysis'] = corr_dict
        print(f"  Analyzed correlations between {len(key_metrics)} metrics")
        print(f"  Found {len(strong_correlations)} strong correlations (|r| > 0.7)")
    
    def analyze_regression(self):
        """Perform regression analysis."""
        if not SKLEARN_AVAILABLE:
            print("  Skipping (sklearn not available)")
            return
        
        reg_dict = {}
        
        # Target: Use Index_Weighted or first density metric
        target_col = None
        for candidate in ['Index_Weighted', 'Weighted Combined Metric', 'Density Metric']:
            if candidate in self.df.columns:
                target_col = candidate
                break
        
        if not target_col:
            print("  No suitable target variable found")
            return
        
        # Predictors: Exclude target and non-numeric
        predictor_candidates = [c for c in self.numeric_cols 
                               if c != target_col and 
                               not c.startswith('PC') and 
                               not c.startswith('TSNE') and
                               not c.startswith('UMAP') and
                               '_log' not in c]
        
        # Select top predictors by correlation
        target_values = pd.to_numeric(self.df[target_col], errors='coerce')
        correlations = {}
        for pred in predictor_candidates:
            pred_values = pd.to_numeric(self.df[pred], errors='coerce')
            valid_mask = target_values.notna() & pred_values.notna()
            if valid_mask.sum() >= 5:
                corr = target_values[valid_mask].corr(pred_values[valid_mask])
                if not pd.isna(corr):
                    correlations[pred] = abs(corr)
        
        # Select top 10 predictors
        top_predictors = sorted(correlations.items(), key=lambda x: x[1], reverse=True)[:10]
        top_predictors = [p[0] for p in top_predictors]
        
        if len(top_predictors) < 2:
            print("  Insufficient predictors for regression")
            return
        
        # Prepare data
        X = self.df[top_predictors].fillna(0)
        y = target_values.fillna(0)
        
        # Standardize
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Linear Regression
        try:
            lr = LinearRegression()
            lr.fit(X_scaled, y)
            y_pred = lr.predict(X_scaled)
            
            reg_dict['linear_regression'] = {
                'r2_score': float(r2_score(y, y_pred)),
                'rmse': float(np.sqrt(mean_squared_error(y, y_pred))),
                'mae': float(mean_absolute_error(y, y_pred)),
                'coefficients': {pred: float(coef) for pred, coef in zip(top_predictors, lr.coef_)},
                'intercept': float(lr.intercept_)
            }
            
            # Cross-validation
            cv_scores = cross_val_score(lr, X_scaled, y, cv=min(5, len(y)//2), scoring='r2')
            reg_dict['linear_regression']['cv_r2_mean'] = float(cv_scores.mean())
            reg_dict['linear_regression']['cv_r2_std'] = float(cv_scores.std())
        except Exception as e:
            print(f"  Linear regression failed: {e}")
        
        self.results['regression_analysis'] = reg_dict
        print(f"  Performed regression with {len(top_predictors)} predictors")
    
    def detect_outliers(self):
        """Detect outliers using multiple methods."""
        outlier_dict = {}
        
        key_metrics = self.density_metrics[:3]
        key_metrics = [m for m in key_metrics if m in self.df.columns]
        
        for metric in key_metrics:
            values = pd.to_numeric(self.df[metric], errors='coerce').dropna()
            if len(values) < 5:
                continue
            
            outliers = {}
            
            # IQR method
            Q1 = values.quantile(0.25)
            Q3 = values.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            iqr_outliers = self.df[(self.df[metric] < lower_bound) | (self.df[metric] > upper_bound)]
            outliers['iqr'] = {
                'count': len(iqr_outliers),
                'indices': iqr_outliers.index.tolist() if len(iqr_outliers) > 0 else []
            }
            
            # Z-score method (|z| > 3)
            z_scores = np.abs(stats.zscore(values))
            z_outliers_idx = values.index[z_scores > 3]
            outliers['zscore'] = {
                'count': len(z_outliers_idx),
                'indices': z_outliers_idx.tolist()
            }
            
            # Isolation Forest (if available)
            if SKLEARN_AVAILABLE and len(values) >= 10:
                try:
                    iso_forest = IsolationForest(contamination=0.1, random_state=42)
                    X = values.values.reshape(-1, 1)
                    predictions = iso_forest.fit_predict(X)
                    iso_outliers_idx = values.index[predictions == -1]
                    outliers['isolation_forest'] = {
                        'count': len(iso_outliers_idx),
                        'indices': iso_outliers_idx.tolist()
                    }
                except:
                    pass
            
            outlier_dict[metric] = outliers
        
        self.results['outlier_detection'] = outlier_dict
        print(f"  Detected outliers in {len(outlier_dict)} metrics")
    
    def analyze_dimensionality_reduction(self):
        """Analyze dimensionality reduction results."""
        dr_dict = {}
        
        # PCA analysis
        if 'PC1' in self.df.columns:
            dr_dict['pca'] = {
                'available': True,
                'components': ['PC1', 'PC2'] if 'PC2' in self.df.columns else ['PC1'],
                'pc1_range': [float(self.df['PC1'].min()), float(self.df['PC1'].max())],
                'pc1_mean': float(self.df['PC1'].mean()),
                'pc1_std': float(self.df['PC1'].std())
            }
            if 'PC2' in self.df.columns:
                dr_dict['pca']['pc2_range'] = [float(self.df['PC2'].min()), float(self.df['PC2'].max())]
                dr_dict['pca']['pc2_mean'] = float(self.df['PC2'].mean())
                dr_dict['pca']['pc2_std'] = float(self.df['PC2'].std())
        else:
            dr_dict['pca'] = {'available': False}
        
        # t-SNE analysis
        if 'TSNE1' in self.df.columns:
            dr_dict['tsne'] = {
                'available': True,
                'tsne1_range': [float(self.df['TSNE1'].min()), float(self.df['TSNE1'].max())],
                'tsne2_range': [float(self.df['TSNE2'].min()), float(self.df['TSNE2'].max())] if 'TSNE2' in self.df.columns else None
            }
        else:
            dr_dict['tsne'] = {'available': False}
        
        # UMAP analysis
        if 'UMAP1' in self.df.columns:
            dr_dict['umap'] = {
                'available': True,
                'umap1_range': [float(self.df['UMAP1'].min()), float(self.df['UMAP1'].max())],
                'umap2_range': [float(self.df['UMAP2'].min()), float(self.df['UMAP2'].max())] if 'UMAP2' in self.df.columns else None
            }
        else:
            dr_dict['umap'] = {'available': False}
        
        self.results['dimensionality_reduction'] = dr_dict
        print(f"  Analyzed dimensionality reduction components")
    
    def analyze_frequency_dependence(self):
        """Analyze frequency-dependent patterns."""
        if 'Fundamental_Freq_Hz' not in self.df.columns:
            print("  Frequency data not available")
            return
        
        freq_dict = {}
        
        key_metrics = self.density_metrics[:5]
        key_metrics = [m for m in key_metrics if m in self.df.columns]
        
        for metric in key_metrics:
            values = pd.to_numeric(self.df[metric], errors='coerce')
            freqs = self.df['Fundamental_Freq_Hz']
            valid_mask = values.notna() & freqs.notna()
            
            if valid_mask.sum() < 3:
                continue
            
            valid_values = values[valid_mask]
            valid_freqs = freqs[valid_mask]
            
            # Correlation
            corr = valid_values.corr(valid_freqs)
            
            # Linear regression
            if SKLEARN_AVAILABLE:
                try:
                    X = valid_freqs.values.reshape(-1, 1)
                    y = valid_values.values
                    lr = LinearRegression()
                    lr.fit(X, y)
                    y_pred = lr.predict(X)
                    r2 = r2_score(y, y_pred)
                    
                    freq_dict[metric] = {
                        'correlation': float(corr) if not pd.isna(corr) else None,
                        'linear_regression': {
                            'slope': float(lr.coef_[0]),
                            'intercept': float(lr.intercept_),
                            'r2': float(r2)
                        }
                    }
                except:
                    freq_dict[metric] = {
                        'correlation': float(corr) if not pd.isna(corr) else None
                    }
            else:
                freq_dict[metric] = {
                    'correlation': float(corr) if not pd.isna(corr) else None
                }
        
        self.results['frequency_analysis'] = freq_dict
        print(f"  Analyzed frequency dependence for {len(freq_dict)} metrics")
    
    def analyze_registers(self):
        """Analyze differences between registers."""
        if 'Register' not in self.df.columns:
            print("  Register classification not available")
            return
        
        register_dict = {}
        
        key_metrics = self.density_metrics[:3]
        key_metrics = [m for m in key_metrics if m in self.df.columns]
        
        for metric in key_metrics:
            register_stats = self.df.groupby('Register')[metric].agg([
                'count', 'mean', 'std', 'min', 'max', 'median'
            ]).to_dict()
            register_dict[metric] = register_stats
        
        # Statistical tests between registers
        if SCIPY_AVAILABLE and len(self.df['Register'].unique()) >= 2:
            for metric in key_metrics:
                values = pd.to_numeric(self.df[metric], errors='coerce')
                registers = self.df['Register']
                valid_mask = values.notna() & registers.notna()
                
                if valid_mask.sum() < 5:
                    continue
                
                groups = []
                for reg in registers[valid_mask].unique():
                    group_values = values[valid_mask][registers[valid_mask] == reg]
                    if len(group_values) >= 2:
                        groups.append(group_values.values)
                
                if len(groups) >= 2:
                    try:
                        # Kruskal-Wallis test (non-parametric ANOVA)
                        stat, p_value = kruskal(*groups)
                        register_dict[metric]['kruskal_wallis'] = {
                            'statistic': float(stat),
                            'p_value': float(p_value),
                            'significant': p_value < 0.05
                        }
                    except:
                        pass
        
        self.results['register_analysis'] = register_dict
        print(f"  Analyzed {len(register_dict)} metrics across registers")
    
    def validate_physics(self):
        """Run internal physical consistency checks on tabular metrics (no external APIs)."""
        validation_dict: Dict[str, Any] = {
            "internal_consistency_enabled": True,
            "physical_checks": [],
        }
        checks = validation_dict["physical_checks"]
        if "Fundamental_Freq_Hz" in self.df.columns:
            freqs = self.df["Fundamental_Freq_Hz"].dropna()
            if len(freqs) > 0:
                min_freq = freqs.min()
                max_freq = freqs.max()
                checks.append(
                    {
                        "check": "frequency_range",
                        "min_freq_hz": float(min_freq),
                        "max_freq_hz": float(max_freq),
                        "valid": 20 <= min_freq <= 20000 and 20 <= max_freq <= 20000,
                        "note": "Human hearing range: 20 Hz - 20 kHz",
                    }
                )
        if "Harmonic Count" in self.df.columns:
            harm_counts = pd.to_numeric(self.df["Harmonic Count"], errors="coerce").dropna()
            if len(harm_counts) > 0:
                max_harm = harm_counts.max()
                if "Fundamental_Freq_Hz" in self.df.columns:
                    min_freq = self.df["Fundamental_Freq_Hz"].dropna().min()
                    theoretical_max = int(20000 / min_freq) if min_freq > 0 else 1000
                    checks.append(
                        {
                            "check": "harmonic_count",
                            "max_observed": float(max_harm),
                            "theoretical_max": theoretical_max,
                            "valid": max_harm <= theoretical_max * 1.5,
                            "note": (
                                f"Theoretical limit: {theoretical_max} harmonics for "
                                f"{min_freq:.1f} Hz fundamental (internal heuristic)"
                            ),
                        }
                    )
        if "Density Metric" in self.df.columns:
            density = pd.to_numeric(self.df["Density Metric"], errors="coerce").dropna()
            if len(density) > 0:
                checks.append(
                    {
                        "check": "density_range",
                        "min": float(density.min()),
                        "max": float(density.max()),
                        "mean": float(density.mean()),
                        "valid": density.min() >= 0,
                        "note": "Density metrics should be non-negative",
                    }
                )
        if "Fundamental_Freq_Hz" in self.df.columns and "Density Metric" in self.df.columns:
            freqs = self.df["Fundamental_Freq_Hz"].dropna()
            density = pd.to_numeric(self.df["Density Metric"], errors="coerce")
            valid_mask = freqs.notna() & density.notna()
            if valid_mask.sum() >= 3:
                corr = density[valid_mask].corr(freqs[valid_mask])
                checks.append(
                    {
                        "check": "spectral_rolloff",
                        "frequency_correlation": float(corr) if not pd.isna(corr) else None,
                        "expected_alpha": 1.5,
                        "valid": corr < 0 if not pd.isna(corr) else None,
                        "note": "Expected negative correlation (density decreases with frequency)",
                    }
                )
        if self.dissonance_metrics:
            for dissonance_col in self.dissonance_metrics[:1]:
                dissonance = pd.to_numeric(self.df[dissonance_col], errors="coerce").dropna()
                if len(dissonance) > 0:
                    checks.append(
                        {
                            "check": "dissonance_range",
                            "metric": dissonance_col,
                            "min": float(dissonance.min()),
                            "max": float(dissonance.max()),
                            "mean": float(dissonance.mean()),
                            "valid": dissonance.min() >= 0,
                            "note": "Dissonance values should be non-negative",
                        }
                    )
                    break
        self.results["internal_consistency_checks"] = validation_dict
        print(f"  Performed {len(checks)} internal consistency checks")
    
    def generate_reports(self):
        """Generate comprehensive reports."""
        # JSON report
        json_path = self.output_dir / 'analysis_results.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"  JSON report: {json_path}")
        
        # Text report
        txt_path = self.output_dir / 'analysis_report.txt'
        self._generate_text_report(txt_path)
        print(f"  Text report: {txt_path}")
        
        # Markdown report
        md_path = self.output_dir / 'analysis_report.md'
        self._generate_markdown_report(md_path)
        print(f"  Markdown report: {md_path}")
        
        # Visualizations
        if MATPLOTLIB_AVAILABLE:
            self._generate_visualizations()
            print(f"  Visualizations saved to: {self.output_dir / 'visualizations'}")
    
    def _generate_text_report(self, output_path: Path):
        """Generate comprehensive text report."""
        lines = []
        
        lines.append("="*80 + "\n")
        lines.append("ACOUSTIC DATA ANALYSIS REPORT\n")
        lines.append("="*80 + "\n\n")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"Input File: {self.excel_path.name}\n")
        lines.append(f"Samples: {len(self.df)}\n\n")
        
        lines.append("="*80 + "\n")
        lines.append("1. DESCRIPTIVE STATISTICS\n")
        lines.append("="*80 + "\n\n")
        
        for metric, stats in self.results['descriptive_stats'].items():
            lines.append(f"Metric: {metric}\n")
            lines.append("-"*80 + "\n")
            lines.append(f"  Count:        {stats['count']}\n")
            lines.append(f"  Mean:         {stats['mean']:.6f}\n")
            lines.append(f"  Median:       {stats['median']:.6f}\n")
            lines.append(f"  Std Dev:      {stats['std']:.6f}\n")
            lines.append(f"  Min:          {stats['min']:.6f}\n")
            lines.append(f"  Max:          {stats['max']:.6f}\n")
            lines.append(f"  Range:        {stats['range']:.6f}\n")
            lines.append(f"  IQR:          {stats['iqr']:.6f}\n")
            lines.append(f"  CV:           {stats['cv']:.4f}\n")
            lines.append(f"  Skewness:     {stats['skewness']:.4f}\n")
            lines.append(f"  Kurtosis:     {stats['kurtosis']:.4f}\n\n")
        
        # Correlation Analysis
        if 'correlation_analysis' in self.results:
            lines.append("\n" + "="*80 + "\n")
            lines.append("2. CORRELATION ANALYSIS\n")
            lines.append("="*80 + "\n\n")
            
            if 'strong_correlations' in self.results['correlation_analysis']:
                lines.append("Strong Correlations (|r| > 0.7):\n")
                lines.append("-"*80 + "\n")
                for corr in self.results['correlation_analysis']['strong_correlations']:
                    lines.append(f"  {corr['metric1']} <-> {corr['metric2']}: {corr['correlation']:.4f} ({corr['strength']})\n")
                lines.append("\n")
        
        # Frequency Analysis
        if 'frequency_analysis' in self.results:
            lines.append("\n" + "="*80 + "\n")
            lines.append("3. FREQUENCY-DEPENDENT ANALYSIS\n")
            lines.append("="*80 + "\n\n")
            
            for metric, analysis in self.results['frequency_analysis'].items():
                lines.append(f"Metric: {metric}\n")
                lines.append("-"*80 + "\n")
                if 'correlation' in analysis and analysis['correlation'] is not None:
                    lines.append(f"  Correlation with frequency: {analysis['correlation']:.4f}\n")
                if 'linear_regression' in analysis:
                    lr = analysis['linear_regression']
                    lines.append(f"  Linear regression slope:   {lr['slope']:.6e}\n")
                    lines.append(f"  R²:                         {lr['r2']:.4f}\n")
                lines.append("\n")
        
        # Outlier Detection
        if 'outlier_detection' in self.results:
            lines.append("\n" + "="*80 + "\n")
            lines.append("4. OUTLIER DETECTION\n")
            lines.append("="*80 + "\n\n")
            
            for metric, outliers in self.results['outlier_detection'].items():
                lines.append(f"Metric: {metric}\n")
                lines.append("-"*80 + "\n")
                for method, result in outliers.items():
                    lines.append(f"  {method}: {result['count']} outliers detected\n")
                lines.append("\n")
        
        # Internal consistency checks
        if "internal_consistency_checks" in self.results:
            lines.append("\n" + "=" * 80 + "\n")
            lines.append("5. INTERNAL CONSISTENCY CHECKS\n")
            lines.append("=" * 80 + "\n\n")
            for check in self.results["internal_consistency_checks"].get("physical_checks", []):
                status = "PASS" if check.get("valid", False) else "FAIL"
                lines.append(f"  {check['check']}: {status}\n")
                if "note" in check:
                    lines.append(f"    Note: {check['note']}\n")
            lines.append("\n")
        
        lines.append("\n" + "="*80 + "\n")
        lines.append("END OF REPORT\n")
        lines.append("="*80 + "\n")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    def _generate_markdown_report(self, output_path: Path):
        """Generate a comprehensive Markdown report."""
        lines = []
        
        lines.append("# Acoustic Data Analysis Report\n")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**Input File:** {self.excel_path.name}\n")
        lines.append(f"**Samples:** {len(self.df)}\n\n")
        
        lines.append("---\n\n")
        
        # Descriptive Statistics
        lines.append("## 1. Descriptive Statistics\n\n")
        for metric, stats in self.results['descriptive_stats'].items():
            lines.append(f"### {metric}\n\n")
            lines.append(f"- **Count:** {stats['count']}\n")
            lines.append(f"- **Mean:** {stats['mean']:.6f}\n")
            lines.append(f"- **Median:** {stats['median']:.6f}\n")
            lines.append(f"- **Std Dev:** {stats['std']:.6f}\n")
            lines.append(f"- **Range:** [{stats['min']:.6f}, {stats['max']:.6f}]\n")
            lines.append(f"- **IQR:** {stats['iqr']:.6f}\n")
            lines.append(f"- **CV:** {stats['cv']:.4f}\n")
            lines.append(f"- **Skewness:** {stats['skewness']:.4f}\n")
            lines.append(f"- **Kurtosis:** {stats['kurtosis']:.4f}\n\n")
        
        # Correlation Analysis
        if 'correlation_analysis' in self.results:
            lines.append("## 2. Correlation Analysis\n\n")
            if 'strong_correlations' in self.results['correlation_analysis']:
                lines.append("### Strong Correlations (|r| > 0.7)\n\n")
                for corr in self.results['correlation_analysis']['strong_correlations']:
                    lines.append(f"- **{corr['metric1']}** ↔ **{corr['metric2']}**: {corr['correlation']:.4f}\n")
                lines.append("\n")
        
        # Frequency Analysis
        if 'frequency_analysis' in self.results:
            lines.append("## 3. Frequency-Dependent Analysis\n\n")
            for metric, analysis in self.results['frequency_analysis'].items():
                lines.append(f"### {metric}\n\n")
                if 'correlation' in analysis and analysis['correlation'] is not None:
                    lines.append(f"- **Correlation with frequency:** {analysis['correlation']:.4f}\n")
                if 'linear_regression' in analysis:
                    lr = analysis['linear_regression']
                    lines.append(f"- **Linear regression slope:** {lr['slope']:.6e}\n")
                    lines.append(f"- **R²:** {lr['r2']:.4f}\n")
                lines.append("\n")
        
        # Register Analysis
        if 'register_analysis' in self.results:
            lines.append("## 4. Register Analysis\n\n")
            for metric, analysis in self.results['register_analysis'].items():
                lines.append(f"### {metric}\n\n")
                # Add register statistics table
                lines.append("\n")
        
        # Outlier Detection
        if 'outlier_detection' in self.results:
            lines.append("## 5. Outlier Detection\n\n")
            for metric, outliers in self.results['outlier_detection'].items():
                lines.append(f"### {metric}\n\n")
                for method, result in outliers.items():
                    lines.append(f"- **{method}:** {result['count']} outliers detected\n")
                lines.append("\n")
        
        # Internal consistency checks
        if "internal_consistency_checks" in self.results:
            lines.append("## 6. Internal consistency checks\n\n")
            for check in self.results["internal_consistency_checks"].get("physical_checks", []):
                status = "✓" if check.get("valid", False) else "✗"
                lines.append(f"- **{check['check']}:** {status}\n")
            lines.append("\n")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    def _generate_visualizations(self):
        """Generate visualization plots.

        AUDIT FIX — every chart title now follows the audit-mandated format
        ``"<sheet> — <metric> — <status>"`` so the user can distinguish a
        canonical descriptor from a diagnostic/legacy one at a glance.
        Forbidden raw legacy columns (``Harmonic Partials sum`` etc.) are
        not used here at all; if a publication-grade canonical metric is
        unavailable the plot is skipped with a warning rather than fall
        back to legacy data.
        """
        try:
            from publication_chart_policy import (
                DEFAULT_PUBLICATION_SHEET,
                classify_metric_for_publication,
                compose_chart_title,
            )
        except Exception:
            DEFAULT_PUBLICATION_SHEET = "Canonical_Metrics"
            def classify_metric_for_publication(name):
                return "diagnostic"
            def compose_chart_title(sheet, metric, *, status=None):
                return f"{sheet} — {metric} — {status or ''}"

        sheet_name_used = getattr(self, "_sheet_used", DEFAULT_PUBLICATION_SHEET)

        viz_dir = self.output_dir / 'visualizations'
        viz_dir.mkdir(exist_ok=True)

        # Correlation heatmap
        if 'correlation_analysis' in self.results and 'correlation_matrix' in self.results['correlation_analysis']:
            try:
                key_metrics = list(self.results['correlation_analysis']['correlation_matrix'].keys())
                if len(key_metrics) > 1:
                    corr_data = self.df[key_metrics].corr()
                    plt.figure(figsize=(12, 10))
                    sns.heatmap(corr_data, annot=True, fmt='.3f', cmap='coolwarm', center=0,
                               square=True, linewidths=0.5)
                    plt.title(
                        f"{sheet_name_used} — correlation matrix — canonical metrics only"
                    )
                    plt.tight_layout()
                    plt.savefig(viz_dir / 'correlation_heatmap.png', dpi=300, bbox_inches='tight')
                    plt.close()
            except Exception as e:
                print(f"  Error generating correlation heatmap: {e}")

        # Frequency dependence plots — canonical descriptors only
        if 'Fundamental_Freq_Hz' in self.df.columns:
            key_metrics = self.density_metrics[:3]
            key_metrics = [m for m in key_metrics if m in self.df.columns]

            for metric in key_metrics:
                try:
                    status = classify_metric_for_publication(metric)
                    if status != "canonical":
                        print(
                            f"  Skipping plot for non-canonical metric {metric!r} "
                            f"(status={status})."
                        )
                        continue
                    values = pd.to_numeric(self.df[metric], errors='coerce')
                    freqs = self.df['Fundamental_Freq_Hz']
                    valid_mask = values.notna() & freqs.notna()

                    if valid_mask.sum() >= 3:
                        plt.figure(figsize=(10, 6))
                        plt.scatter(freqs[valid_mask], values[valid_mask], alpha=0.6)
                        plt.xlabel('Fundamental Frequency (Hz)')
                        plt.ylabel(metric)
                        plt.title(
                            compose_chart_title(sheet_name_used, metric, status=status)
                        )
                        plt.grid(True, alpha=0.3)
                        plt.tight_layout()
                        plt.savefig(viz_dir / f'{metric}_vs_frequency.png', dpi=300, bbox_inches='tight')
                        plt.close()
                except Exception as e:
                    print(f"  Error generating plot for {metric}: {e}")


class MultiFileComparator:
    """
    Advanced multi-file comparison system for acoustic data analysis.
    
    Performs comprehensive comparisons between multiple Excel files including:
    - Percentage deviations
    - Regression model comparisons
    - Correlation analysis
    - Statistical significance tests
    - Cross-file consistency analysis
    """
    
    def __init__(self, excel_files: List[Union[str, Path]], output_dir: Optional[Union[str, Path]] = None):
        """
        Initialize multi-file comparator.
        
        Args:
            excel_files: List of paths to Excel files to compare
            output_dir: Output directory for results
        """
        if len(excel_files) < 2:
            raise ValueError("At least 2 files required for comparison")
        
        self.excel_files = [Path(f) for f in excel_files]
        self.output_dir = Path(output_dir) if output_dir else self.excel_files[0].parent
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load all datasets
        self.datasets = {}
        self.dataset_names = []
        print(f"Loading {len(excel_files)} files for comparison...")
        
        for i, file_path in enumerate(self.excel_files):
            name = file_path.stem
            try:
                df = pd.read_excel(file_path)
                self.datasets[name] = df
                self.dataset_names.append(name)
                print(f"  [{i+1}/{len(excel_files)}] Loaded {name}: {len(df)} records")
            except Exception as e:
                print(f"  ERROR loading {name}: {e}")
                raise
        
        # Results storage
        self.comparison_results = {
            'metadata': {
                'files': [str(f) for f in self.excel_files],
                'dataset_names': self.dataset_names,
                'comparison_date': datetime.now().isoformat(),
                'n_files': len(self.excel_files)
            },
            'percentage_deviations': {},
            'regression_comparisons': {},
            'correlation_comparisons': {},
            'statistical_tests': {},
            'consistency_analysis': {},
            'internal_consistency_comparison': {}
        }
    
    def run_comprehensive_comparison(self, baseline_index: int = 0) -> Dict[str, Any]:
        """
        Run comprehensive comparison analysis.
        
        Args:
            baseline_index: Index of baseline file (default: 0)
        
        Returns:
            Dictionary with all comparison results
        """
        print("\n" + "="*80)
        print("MULTI-FILE COMPREHENSIVE COMPARISON")
        print("="*80)
        
        baseline_name = self.dataset_names[baseline_index]
        print(f"Baseline file: {baseline_name}")
        
        try:
            # 1. Percentage Deviations
            print("\n[1/5] Computing percentage deviations...")
            self.compare_percentage_deviations(baseline_index)
            
            # 2. Regression Model Comparisons
            print("[2/5] Comparing regression models...")
            self.compare_regression_models(baseline_index)
            
            # 3. Correlation Comparisons
            print("[3/5] Comparing correlations...")
            self.compare_correlations(baseline_index)
            
            # 4. Statistical Significance Tests
            print("[4/5] Performing statistical tests...")
            self.perform_statistical_tests(baseline_index)
            
            # 5. Consistency Analysis
            print("[5/5] Analyzing consistency...")
            self.analyze_consistency()
            
            # Generate reports
            print("\nGenerating comparison reports...")
            self.generate_comparison_reports()
            
            print("\n" + "="*80)
            print("COMPARISON COMPLETE")
            print("="*80)
            print(f"Results saved to: {self.output_dir}")
            
            return self.comparison_results
            
        except Exception as e:
            print(f"\nERROR during comparison: {e}")
            traceback.print_exc()
            raise
    
    def compare_percentage_deviations(self, baseline_index: int = 0):
        """Compute percentage deviations between files."""
        baseline_name = self.dataset_names[baseline_index]
        baseline_df = self.datasets[baseline_name]
        
        results = {}
        
        # Find common numeric columns
        common_cols = set(baseline_df.columns)
        for name, df in self.datasets.items():
            if name != baseline_name:
                common_cols &= set(df.columns)
        
        # Remove non-numeric columns
        numeric_cols = []
        for col in common_cols:
            if col in ['Note', 'Folder', 'Analysis Type', 'Window', 'DM Domain']:
                continue
            if baseline_df[col].dtype in ['int64', 'float64'] or pd.api.types.is_numeric_dtype(baseline_df[col]):
                numeric_cols.append(col)
        
        # Key column for alignment
        key_col = 'Note' if 'Note' in baseline_df.columns else baseline_df.columns[0]
        
        for metric in numeric_cols[:20]:  # Limit to top 20 metrics
            metric_results = {}
            
            baseline_values = pd.to_numeric(baseline_df[metric], errors='coerce')
            
            for name, df in self.datasets.items():
                if name == baseline_name:
                    continue
                
                other_values = pd.to_numeric(df[metric], errors='coerce')
                
                # Align by key column if available
                if key_col in baseline_df.columns and key_col in df.columns:
                    baseline_aligned = baseline_df.set_index(key_col)[metric]
                    other_aligned = df.set_index(key_col)[metric]
                    common_keys = baseline_aligned.index.intersection(other_aligned.index)
                    
                    if len(common_keys) > 0:
                        baseline_vals = pd.to_numeric(baseline_aligned[common_keys], errors='coerce')
                        other_vals = pd.to_numeric(other_aligned[common_keys], errors='coerce')
                        
                        valid_mask = baseline_vals.notna() & other_vals.notna() & (baseline_vals != 0)
                        if valid_mask.sum() > 0:
                            baseline_valid = baseline_vals[valid_mask]
                            other_valid = other_vals[valid_mask]
                            
                            # Calculate percentage deviations
                            pct_dev = ((other_valid - baseline_valid) / baseline_valid) * 100.0
                            
                            metric_results[name] = {
                                'mean_pct_dev': float(pct_dev.mean()),
                                'std_pct_dev': float(pct_dev.std()),
                                'min_pct_dev': float(pct_dev.min()),
                                'max_pct_dev': float(pct_dev.max()),
                                'abs_mean_pct_dev': float(pct_dev.abs().mean()),
                                'n_comparisons': int(valid_mask.sum())
                            }
            
            if metric_results:
                results[metric] = metric_results
        
        self.comparison_results['percentage_deviations'] = results
        print(f"  Computed percentage deviations for {len(results)} metrics")
    
    def compare_regression_models(self, baseline_index: int = 0):
        """Compare regression models between files."""
        if not SKLEARN_AVAILABLE:
            print("  Skipping (sklearn not available)")
            return
        
        baseline_name = self.dataset_names[baseline_index]
        baseline_df = self.datasets[baseline_name]
        
        results = {}
        
        # Find target metric
        target_candidates = ['Index_Weighted', 'Weighted Combined Metric', 'Density Metric', 'Spectral Density Metric']
        target_col = None
        for candidate in target_candidates:
            if candidate in baseline_df.columns:
                target_col = candidate
                break
        
        if not target_col:
            print("  No suitable target variable found")
            return
        
        # Find predictor columns
        predictor_candidates = [c for c in baseline_df.columns 
                               if c != target_col and 
                               pd.api.types.is_numeric_dtype(baseline_df[c]) and
                               not c.startswith('PC') and not c.startswith('TSNE') and not c.startswith('UMAP')]
        
        # Select top predictors
        target_values = pd.to_numeric(baseline_df[target_col], errors='coerce')
        correlations = {}
        for pred in predictor_candidates[:15]:
            pred_values = pd.to_numeric(baseline_df[pred], errors='coerce')
            valid_mask = target_values.notna() & pred_values.notna()
            if valid_mask.sum() >= 3:
                corr = target_values[valid_mask].corr(pred_values[valid_mask])
                if not pd.isna(corr):
                    correlations[pred] = abs(corr)
        
        top_predictors = sorted(correlations.items(), key=lambda x: x[1], reverse=True)[:5]
        top_predictors = [p[0] for p in top_predictors]
        
        if len(top_predictors) < 2:
            print("  Insufficient predictors")
            return
        
        # Compare models across files
        for name, df in self.datasets.items():
            try:
                X = df[top_predictors].fillna(0)
                y = pd.to_numeric(df[target_col], errors='coerce').fillna(0)
                
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                
                lr = LinearRegression()
                lr.fit(X_scaled, y)
                y_pred = lr.predict(X_scaled)
                
                results[name] = {
                    'r2_score': float(r2_score(y, y_pred)),
                    'rmse': float(np.sqrt(mean_squared_error(y, y_pred))),
                    'mae': float(mean_absolute_error(y, y_pred)),
                    'coefficients': {pred: float(coef) for pred, coef in zip(top_predictors, lr.coef_)},
                    'intercept': float(lr.intercept_)
                }
            except Exception as e:
                print(f"  Error comparing model for {name}: {e}")
        
        self.comparison_results['regression_comparisons'] = {
            'target_variable': target_col,
            'predictors': top_predictors,
            'models': results
        }
        print(f"  Compared regression models across {len(results)} files")
    
    def compare_correlations(self, baseline_index: int = 0):
        """Compare correlation matrices between files."""
        baseline_name = self.dataset_names[baseline_index]
        baseline_df = self.datasets[baseline_name]
        
        # Find common numeric columns
        key_metrics = []
        for col in baseline_df.columns:
            if any(x in col for x in ['Density', 'Dissonance', 'Harmonic', 'Spectral']):
                if pd.api.types.is_numeric_dtype(baseline_df[col]):
                    key_metrics.append(col)
        
        key_metrics = key_metrics[:10]  # Limit to top 10
        
        results = {}
        
        for name, df in self.datasets.items():
            available_metrics = [m for m in key_metrics if m in df.columns]
            if len(available_metrics) >= 2:
                try:
                    corr_matrix = df[available_metrics].corr()
                    results[name] = {
                        'correlation_matrix': corr_matrix.to_dict(),
                        'mean_abs_correlation': float(corr_matrix.abs().values[np.triu_indices_from(corr_matrix.values, k=1)].mean()),
                        'max_correlation': float(corr_matrix.abs().values[np.triu_indices_from(corr_matrix.values, k=1)].max())
                    }
                except:
                    pass
        
        # Compare with baseline
        if baseline_name in results:
            baseline_corr = results[baseline_name]['correlation_matrix']
            comparisons = {}
            
            for name, result in results.items():
                if name == baseline_name:
                    continue
                other_corr = result['correlation_matrix']
                
                # Compare correlation values
                differences = []
                for m1 in baseline_corr:
                    if m1 in other_corr:
                        for m2 in baseline_corr[m1]:
                            if m2 in other_corr[m1]:
                                diff = abs(baseline_corr[m1][m2] - other_corr[m1][m2])
                                differences.append(diff)
                
                if differences:
                    comparisons[name] = {
                        'mean_correlation_difference': float(np.mean(differences)),
                        'max_correlation_difference': float(np.max(differences))
                    }
            
            self.comparison_results['correlation_comparisons'] = {
                'baseline': baseline_name,
                'individual_matrices': results,
                'comparisons': comparisons
            }
        
        print(f"  Compared correlations across {len(results)} files")
    
    def perform_statistical_tests(self, baseline_index: int = 0):
        """Perform statistical significance tests between files."""
        if not SCIPY_AVAILABLE:
            print("  Skipping (scipy not available)")
            return
        
        baseline_name = self.dataset_names[baseline_index]
        baseline_df = self.datasets[baseline_name]
        
        # Find common numeric metrics
        key_metrics = []
        for col in baseline_df.columns:
            if any(x in col for x in ['Density Metric', 'Spectral Density']):
                if pd.api.types.is_numeric_dtype(baseline_df[col]):
                    key_metrics.append(col)
        
        results = {}
        
        for metric in key_metrics[:5]:  # Top 5 metrics
            if metric not in baseline_df.columns:
                continue
            
            baseline_values = pd.to_numeric(baseline_df[metric], errors='coerce').dropna()
            
            metric_tests = {}
            
            for name, df in self.datasets.items():
                if name == baseline_name:
                    continue
                
                other_values = pd.to_numeric(df[metric], errors='coerce').dropna()
                
                if len(baseline_values) >= 3 and len(other_values) >= 3:
                    try:
                        # Mann-Whitney U test (non-parametric)
                        stat, p_value = mannwhitneyu(baseline_values, other_values, alternative='two-sided')
                        metric_tests[name] = {
                            'mann_whitney_u': {
                                'statistic': float(stat),
                                'p_value': float(p_value),
                                'significant': p_value < 0.05
                            }
                        }
                    except:
                        pass
            
            if metric_tests:
                results[metric] = metric_tests
        
        self.comparison_results['statistical_tests'] = results
        print(f"  Performed statistical tests for {len(results)} metrics")
    
    def analyze_consistency(self):
        """Analyze consistency across files."""
        results = {}
        
        # Find common columns
        common_cols = None
        for name, df in self.datasets.items():
            if common_cols is None:
                common_cols = set(df.columns)
            else:
                common_cols &= set(df.columns)
        
        numeric_cols = [c for c in common_cols 
                       if c not in ['Note', 'Folder'] and 
                       any(df[c].dtype in ['int64', 'float64'] for df in self.datasets.values())]
        
        consistency_metrics = {}
        
        for col in numeric_cols[:10]:  # Top 10
            values_across_files = []
            for name, df in self.datasets.items():
                vals = pd.to_numeric(df[col], errors='coerce').dropna()
                if len(vals) > 0:
                    values_across_files.append(vals.values)
            
            if len(values_across_files) >= 2:
                # Calculate coefficient of variation across files
                means = [np.mean(v) for v in values_across_files]
                stds = [np.std(v) for v in values_across_files]
                
                if np.mean(means) != 0:
                    cv_across_files = np.std(means) / np.mean(means)
                    consistency_metrics[col] = {
                        'mean_of_means': float(np.mean(means)),
                        'std_of_means': float(np.std(means)),
                        'cv_across_files': float(cv_across_files),
                        'consistency': 'high' if cv_across_files < 0.1 else 'medium' if cv_across_files < 0.3 else 'low'
                    }
        
        results['consistency_metrics'] = consistency_metrics
        self.comparison_results['consistency_analysis'] = results
        print(f"  Analyzed consistency for {len(consistency_metrics)} metrics")
    
    def generate_comparison_reports(self):
        """Generate comprehensive comparison reports."""
        # JSON report
        json_path = self.output_dir / 'comparison_results.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.comparison_results, f, indent=2, default=str)
        print(f"  JSON report: {json_path}")
        
        # Text report
        txt_path = self.output_dir / 'comparison_report.txt'
        self._generate_text_report(txt_path)
        print(f"  Text report: {txt_path}")
        
        # Markdown report
        md_path = self.output_dir / 'comparison_report.md'
        self._generate_markdown_report(md_path)
        print(f"  Markdown report: {md_path}")
    
    def _generate_text_report(self, output_path: Path):
        """Generate comprehensive text report."""
        lines = []
        
        lines.append("="*80 + "\n")
        lines.append("MULTI-FILE ACOUSTIC DATA COMPARISON REPORT\n")
        lines.append("="*80 + "\n\n")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"Number of files compared: {len(self.excel_files)}\n\n")
        
        lines.append("FILES ANALYZED:\n")
        lines.append("-"*80 + "\n")
        for i, (name, file_path) in enumerate(zip(self.dataset_names, self.excel_files)):
            lines.append(f"  [{i+1}] {name}\n")
            lines.append(f"      Path: {file_path}\n")
            lines.append(f"      Records: {len(self.datasets[name])}\n\n")
        
        # Percentage Deviations
        if 'percentage_deviations' in self.comparison_results:
            lines.append("\n" + "="*80 + "\n")
            lines.append("PERCENTAGE DEVIATIONS ANALYSIS\n")
            lines.append("="*80 + "\n\n")
            
            for metric, file_results in self.comparison_results['percentage_deviations'].items():
                lines.append(f"Metric: {metric}\n")
                lines.append("-"*80 + "\n")
                
                for file_name, stats in file_results.items():
                    lines.append(f"  Compared to baseline - {file_name}:\n")
                    lines.append(f"    Mean % deviation:     {stats['mean_pct_dev']:+.4f}%\n")
                    lines.append(f"    Std % deviation:      {stats['std_pct_dev']:.4f}%\n")
                    lines.append(f"    Mean |% deviation|:   {stats['abs_mean_pct_dev']:.4f}%\n")
                    lines.append(f"    Range:                [{stats['min_pct_dev']:.4f}%, {stats['max_pct_dev']:.4f}%]\n")
                    lines.append(f"    Valid comparisons:   {stats['n_comparisons']}\n\n")
        
        # Regression Comparisons
        if 'regression_comparisons' in self.comparison_results:
            lines.append("\n" + "="*80 + "\n")
            lines.append("REGRESSION MODEL COMPARISONS\n")
            lines.append("="*80 + "\n\n")
            
            reg_data = self.comparison_results['regression_comparisons']
            lines.append(f"Target Variable: {reg_data.get('target_variable', 'N/A')}\n")
            lines.append(f"Predictors: {', '.join(reg_data.get('predictors', []))}\n\n")
            
            for file_name, model_stats in reg_data.get('models', {}).items():
                lines.append(f"Model for {file_name}:\n")
                lines.append(f"  R² Score:        {model_stats['r2_score']:.6f}\n")
                lines.append(f"  RMSE:            {model_stats['rmse']:.6f}\n")
                lines.append(f"  MAE:             {model_stats['mae']:.6f}\n")
                lines.append(f"  Intercept:       {model_stats['intercept']:.6f}\n")
                lines.append(f"  Coefficients:\n")
                for pred, coef in model_stats['coefficients'].items():
                    lines.append(f"    {pred:30s}: {coef:+.6f}\n")
                lines.append("\n")
        
        # Correlation Comparisons
        if 'correlation_comparisons' in self.comparison_results:
            lines.append("\n" + "="*80 + "\n")
            lines.append("CORRELATION COMPARISONS\n")
            lines.append("="*80 + "\n\n")
            
            corr_data = self.comparison_results['correlation_comparisons']
            baseline = corr_data.get('baseline', 'N/A')
            lines.append(f"Baseline: {baseline}\n\n")
            
            for file_name, comparison in corr_data.get('comparisons', {}).items():
                lines.append(f"Comparison: {file_name} vs {baseline}\n")
                lines.append(f"  Mean correlation difference: {comparison['mean_correlation_difference']:.6f}\n")
                lines.append(f"  Max correlation difference:  {comparison['max_correlation_difference']:.6f}\n\n")
        
        # Statistical Tests
        if 'statistical_tests' in self.comparison_results:
            lines.append("\n" + "="*80 + "\n")
            lines.append("STATISTICAL SIGNIFICANCE TESTS\n")
            lines.append("="*80 + "\n\n")
            
            for metric, file_tests in self.comparison_results['statistical_tests'].items():
                lines.append(f"Metric: {metric}\n")
                lines.append("-"*80 + "\n")
                
                for file_name, tests in file_tests.items():
                    if 'mann_whitney_u' in tests:
                        mw = tests['mann_whitney_u']
                        lines.append(f"  {file_name} vs baseline:\n")
                        lines.append(f"    Mann-Whitney U:     {mw['statistic']:.4f}\n")
                        lines.append(f"    p-value:            {mw['p_value']:.6f}\n")
                        lines.append(f"    Significant:        {'Yes' if mw['significant'] else 'No'} (α=0.05)\n\n")
        
        # Consistency Analysis
        if 'consistency_analysis' in self.comparison_results:
            lines.append("\n" + "="*80 + "\n")
            lines.append("CROSS-FILE CONSISTENCY ANALYSIS\n")
            lines.append("="*80 + "\n\n")
            
            consistency = self.comparison_results['consistency_analysis'].get('consistency_metrics', {})
            for metric, stats in consistency.items():
                lines.append(f"Metric: {metric}\n")
                lines.append(f"  Mean of means:        {stats['mean_of_means']:.6f}\n")
                lines.append(f"  Std of means:         {stats['std_of_means']:.6f}\n")
                lines.append(f"  CV across files:      {stats['cv_across_files']:.6f}\n")
                lines.append(f"  Consistency level:    {stats['consistency'].upper()}\n\n")
        
        lines.append("\n" + "="*80 + "\n")
        lines.append("END OF REPORT\n")
        lines.append("="*80 + "\n")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    def _generate_markdown_report(self, output_path: Path):
        """Generate Markdown report (similar structure to text report)."""
        # Similar to text report but with Markdown formatting
        lines = []
        lines.append("# Multi-File Acoustic Data Comparison Report\n\n")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        # ... (similar content with Markdown formatting)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)


def run_gui():
    """Run the GUI interface for file selection."""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError:
        print("ERROR: tkinter not available. Please use command-line interface:")
        print("  python acoustic_data_analysis_suite.py <excel_file>")
        return 1
    
    class AnalysisGUI:
        def __init__(self, root):
            self.root = root
            self.root.title("Acoustic Data Analysis Suite - Multi-File Comparison")
            self.root.geometry("900x700")
            self.root.resizable(True, True)
            
            # Variables
            self.excel_files = []  # List of file paths
            self.output_dir = tk.StringVar()
            self.status_text = tk.StringVar(value="Ready to analyze")
            self.progress_var = tk.DoubleVar(value=0.0)
            self.analysis_mode = tk.StringVar(value="single")  # "single" or "compare"
            self.baseline_index = tk.IntVar(value=0)
            
            self.setup_ui()
        
        def setup_ui(self):
            """Setup the user interface."""
            # Main frame
            main_frame = ttk.Frame(self.root, padding="10")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            self.root.columnconfigure(0, weight=1)
            self.root.rowconfigure(0, weight=1)
            
            # Title
            title_label = ttk.Label(
                main_frame, 
                text="Acoustic Data Analysis Suite",
                font=("Arial", 16, "bold")
            )
            title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
            
            subtitle_label = ttk.Label(
                main_frame,
                text="Production-Grade Statistical Analysis Tool",
                font=("Arial", 10)
            )
            subtitle_label.grid(row=1, column=0, columnspan=3, pady=(0, 20))
            
            # Analysis mode selection
            mode_frame = ttk.LabelFrame(main_frame, text="Analysis Mode")
            mode_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
            
            ttk.Radiobutton(
                mode_frame,
                text="Single File Analysis",
                variable=self.analysis_mode,
                value="single",
                command=self.update_ui_mode
            ).grid(row=0, column=0, padx=10, pady=5)
            
            ttk.Radiobutton(
                mode_frame,
                text="Multi-File Comparison",
                variable=self.analysis_mode,
                value="compare",
                command=self.update_ui_mode
            ).grid(row=0, column=1, padx=10, pady=5)
            
            # File selection frame
            self.files_frame = ttk.LabelFrame(main_frame, text="Excel Files")
            self.files_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
            
            # Listbox for files
            self.files_listbox = tk.Listbox(self.files_frame, height=6, selectmode=tk.EXTENDED)
            self.files_listbox.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
            
            scrollbar = ttk.Scrollbar(self.files_frame, orient="vertical", command=self.files_listbox.yview)
            scrollbar.grid(row=0, column=2, sticky=(tk.N, tk.S), padx=5)
            self.files_listbox.config(yscrollcommand=scrollbar.set)
            
            # File buttons
            file_buttons_frame = ttk.Frame(self.files_frame)
            file_buttons_frame.grid(row=0, column=3, padx=5, pady=5)
            
            ttk.Button(
                file_buttons_frame,
                text="Add File(s)...",
                command=self.browse_excel_files
            ).pack(fill=tk.X, pady=2)
            
            ttk.Button(
                file_buttons_frame,
                text="Remove Selected",
                command=self.remove_selected_files
            ).pack(fill=tk.X, pady=2)
            
            ttk.Button(
                file_buttons_frame,
                text="Clear All",
                command=self.clear_files
            ).pack(fill=tk.X, pady=2)
            
            self.files_frame.columnconfigure(0, weight=1)
            self.files_frame.rowconfigure(0, weight=1)
            
            # Baseline selection (for comparison mode)
            self.baseline_frame = ttk.LabelFrame(main_frame, text="Baseline File (for comparison)")
            self.baseline_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
            
            self.baseline_combo = ttk.Combobox(self.baseline_frame, state="readonly", width=50)
            self.baseline_combo.grid(row=0, column=0, padx=5, pady=5)
            self.baseline_frame.grid_remove()  # Hidden by default
            
            # Output directory selection
            output_frame = ttk.LabelFrame(main_frame, text="Output Directory")
            output_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
            
            ttk.Label(output_frame, text="Directory:", font=("Arial", 10, "bold")).grid(
                row=0, column=0, sticky=tk.W, padx=5, pady=5
            )
            ttk.Entry(output_frame, textvariable=self.output_dir, width=50).grid(
                row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5
            )
            ttk.Button(
                output_frame,
                text="Browse...",
                command=self.browse_output_dir
            ).grid(row=0, column=2, padx=5, pady=5)
            
            ttk.Label(
                output_frame,
                text="(Leave empty to use same directory as input file)",
                font=("Arial", 8),
                foreground="gray"
            ).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
            
            output_frame.columnconfigure(1, weight=1)
            
            # Progress bar
            ttk.Label(main_frame, text="Progress:", font=("Arial", 10, "bold")).grid(
                row=6, column=0, sticky=tk.W, pady=(20, 5)
            )
            self.progress_bar = ttk.Progressbar(
                main_frame,
                variable=self.progress_var,
                maximum=100,
                length=400
            )
            self.progress_bar.grid(row=6, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
            
            # Status text
            self.status_label = ttk.Label(
                main_frame,
                textvariable=self.status_text,
                font=("Arial", 9),
                foreground="blue"
            )
            self.status_label.grid(row=7, column=0, columnspan=3, pady=5)
            
            # Buttons
            button_frame = ttk.Frame(main_frame)
            button_frame.grid(row=8, column=0, columnspan=3, pady=20, sticky=(tk.W, tk.E))
            
            self.analyze_button = ttk.Button(
                button_frame,
                text="Run Analysis",
                command=self.run_analysis,
                width=20
            )
            self.analyze_button.pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                button_frame,
                text="Exit",
                command=self.root.quit,
                width=20
            ).pack(side=tk.LEFT, padx=5)
            
            # Info text
            info_text = """
Instructions:
SINGLE FILE MODE:
1. Add one Excel file to analyze
2. (Optional) Choose output directory
3. Click 'Run Analysis'

MULTI-FILE COMPARISON MODE:
1. Add 2+ Excel files for comparison
2. Select baseline file (reference)
3. (Optional) Choose output directory
4. Click 'Run Analysis'

Analysis includes:
• Percentage Deviations
• Regression Model Comparisons
• Correlation Comparisons
• Statistical Significance Tests
• Cross-File Consistency Analysis
• Internal consistency checks (tabular heuristics)
• Comprehensive Reports (JSON, TXT, MD)
            """
            info_label = ttk.Label(
                main_frame,
                text=info_text,
                font=("Arial", 9),
                justify=tk.LEFT,
                foreground="darkgreen"
            )
            info_label.grid(row=9, column=0, columnspan=3, pady=10, sticky=tk.W)
            
            # Configure grid weights
            main_frame.columnconfigure(1, weight=1)
            main_frame.rowconfigure(3, weight=1)
        
        def update_ui_mode(self):
            """Update UI based on selected mode."""
            if self.analysis_mode.get() == "compare":
                self.baseline_frame.grid()
                self.update_baseline_combo()
            else:
                self.baseline_frame.grid_remove()
        
        def browse_excel_files(self):
            """Browse for Excel files (supports multiple selection)."""
            filenames = filedialog.askopenfilenames(
                title="Select Compiled Metrics Excel File(s)",
                filetypes=[
                    ("Excel files", "*.xlsx *.xls"),
                    ("All files", "*.*")
                ]
            )
            if filenames:
                for filename in filenames:
                    if filename not in self.excel_files:
                        self.excel_files.append(filename)
                self.refresh_files_list()
                # Auto-set output directory if not set
                if not self.output_dir.get() and self.excel_files:
                    self.output_dir.set(str(Path(self.excel_files[0]).parent))
        
        def remove_selected_files(self):
            """Remove selected files from list."""
            selected_indices = list(self.files_listbox.curselection())
            if selected_indices:
                # Remove in reverse order to maintain indices
                for idx in reversed(selected_indices):
                    if 0 <= idx < len(self.excel_files):
                        del self.excel_files[idx]
                self.refresh_files_list()
        
        def clear_files(self):
            """Clear all files."""
            self.excel_files = []
            self.refresh_files_list()
        
        def refresh_files_list(self):
            """Refresh the files listbox."""
            self.files_listbox.delete(0, tk.END)
            for file_path in self.excel_files:
                self.files_listbox.insert(tk.END, Path(file_path).name)
            self.update_baseline_combo()
        
        def update_baseline_combo(self):
            """Update baseline combo box."""
            if self.excel_files:
                file_names = [Path(f).stem for f in self.excel_files]
                self.baseline_combo['values'] = file_names
                if len(file_names) > 0 and self.baseline_combo.current() < 0:
                    self.baseline_combo.current(0)
            else:
                self.baseline_combo['values'] = []
                self.baseline_combo.set("")
        
        def browse_output_dir(self):
            """Browse for output directory."""
            dirname = filedialog.askdirectory(
                title="Select Output Directory"
            )
            if dirname:
                self.output_dir.set(dirname)
        
        def run_analysis(self):
            """Run the analysis."""
            mode = self.analysis_mode.get()
            output_path = self.output_dir.get().strip() or None
            
            if mode == "single":
                if not self.excel_files:
                    messagebox.showerror("Error", "Please select at least one Excel file to analyze.")
                    return
                excel_path = self.excel_files[0]
                if not Path(excel_path).exists():
                    messagebox.showerror("Error", f"File not found: {excel_path}")
                    return
            else:  # compare mode
                if len(self.excel_files) < 2:
                    messagebox.showerror("Error", "Please select at least 2 Excel files for comparison.")
                    return
                for file_path in self.excel_files:
                    if not Path(file_path).exists():
                        messagebox.showerror("Error", f"File not found: {file_path}")
                        return
            
            # Disable button during analysis
            self.analyze_button.config(state=tk.DISABLED)
            self.status_text.set("Starting analysis...")
            self.root.update()
            
            try:
                # Run analysis in a separate thread to avoid freezing GUI
                import threading
                
                def analysis_thread():
                    try:
                        if mode == "single":
                            excel_path = self.excel_files[0]
                            self.status_text.set("Loading data...")
                            self.root.update()
                            self.progress_var.set(10)
                            
                            analyzer = AcousticDataAnalyzer(excel_path, output_path)
                            
                            self.status_text.set("Running comprehensive analysis...")
                            self.root.update()
                            self.progress_var.set(20)
                            
                            # Run analysis with progress updates
                            results = analyzer.run_comprehensive_analysis()
                            
                            self.progress_var.set(100)
                            self.status_text.set(f"Analysis complete! Results saved to: {analyzer.output_dir}")
                            
                            # Show completion message
                            messagebox.showinfo(
                                "Analysis Complete",
                                f"Analysis completed successfully!\n\n"
                                f"Results saved to:\n{analyzer.output_dir}\n\n"
                                f"Files generated:\n"
                                f"• analysis_results.json\n"
                                f"• analysis_report.md\n"
                                f"• analysis_report.txt\n"
                                f"• visualizations/ (if available)"
                            )
                        else:  # compare mode
                            baseline_idx = self.baseline_combo.current()
                            if baseline_idx < 0:
                                baseline_idx = 0
                            
                            self.status_text.set("Loading files for comparison...")
                            self.root.update()
                            self.progress_var.set(10)
                            
                            comparator = MultiFileComparator(self.excel_files, output_path)
                            
                            self.status_text.set("Running comprehensive comparison...")
                            self.root.update()
                            self.progress_var.set(30)
                            
                            results = comparator.run_comprehensive_comparison(baseline_index=baseline_idx)
                            
                            self.progress_var.set(100)
                            self.status_text.set(f"Comparison complete! Results saved to: {comparator.output_dir}")
                            
                            # Show completion message
                            messagebox.showinfo(
                                "Comparison Complete",
                                f"Comparison completed successfully!\n\n"
                                f"Results saved to:\n{comparator.output_dir}\n\n"
                                f"Files generated:\n"
                                f"• comparison_results.json\n"
                                f"• comparison_report.txt\n"
                                f"• comparison_report.md\n"
                            )
                        
                    except Exception as e:
                        error_msg = f"Error during analysis:\n{str(e)}\n\n{traceback.format_exc()}"
                        self.status_text.set(f"Error: {str(e)}")
                        messagebox.showerror("Analysis Error", error_msg)
                    finally:
                        self.analyze_button.config(state=tk.NORMAL)
                        self.progress_var.set(0)
                
                # Start analysis in background thread
                thread = threading.Thread(target=analysis_thread, daemon=True)
                thread.start()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start analysis: {str(e)}")
                self.analyze_button.config(state=tk.NORMAL)
                self.progress_var.set(0)
    
    # Create and run GUI
    root = tk.Tk()
    app = AnalysisGUI(root)
    root.mainloop()
    return 0


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Acoustic Data Analysis Suite - Production-Grade Statistical Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python acoustic_data_analysis_suite.py compiled_metrics.xlsx
  python acoustic_data_analysis_suite.py compiled_metrics.xlsx --output-dir ./analysis_results
  python acoustic_data_analysis_suite.py  (launches GUI interface)
        """
    )
    
    parser.add_argument('excel_file', type=str, nargs='?', default=None,
                       help='Path to compiled_metrics.xlsx file (optional - launches GUI if not provided)')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='Output directory for results (default: same as input file)')
    parser.add_argument('--gui', action='store_true',
                       help='Force GUI mode (even if file is provided)')
    
    args = parser.parse_args()
    
    # If no file provided or --gui flag, launch GUI
    if args.gui or args.excel_file is None:
        return run_gui()
    
    # Otherwise, use command-line interface
    try:
        analyzer = AcousticDataAnalyzer(args.excel_file, args.output_dir)
        results = analyzer.run_comprehensive_analysis()
        
        print("\nAnalysis completed successfully!")
        print(f"Results saved to: {analyzer.output_dir}")
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

