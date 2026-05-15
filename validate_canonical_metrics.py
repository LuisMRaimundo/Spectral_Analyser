"""validate_canonical_metrics.py
=================================

Scientific validation script for SoundSpectrAnalyse canonical metrics.

Purpose
-------
Read a compiled ``Canonical_Metrics`` worksheet (produced by
``compile_metrics.py``) plus the machine-readable ``metrics_dictionary.json``,
then emit a validation report that:

1. summarises the corpus (rows, notes, instruments, tiers);
2. checks which canonical metrics are present, missing, or near-constant;
3. computes a correlation matrix among canonical metrics and flags pairs with
   |r| ≥ a configurable threshold (default 0.90);
4. distinguishes **algebraic redundancy** (already documented in
   ``metrics_dictionary.json`` → ``derived_from``) from **empirical redundancy**
   (observed in the corpus but not declared in the dictionary);
5. runs a PCA restricted to metrics flagged ``independent_for_pca=true``;
6. lists outlier rows per metric using IQR fences;
7. surfaces an explicit *Interpretation limits* section, populated from
   ``do_not_interpret_as`` in the dictionary.

The script makes **no musicological claims**. Wording is restricted to
physical-acoustic terms (e.g. "higher inharmonic energy fraction", "greater
spectral dispersion") and excludes terms like *tension*, *orchestration
function*, *timbral salience* unless they appear verbatim in the source
dictionary entry. See ``_make_interpretation_limits_rows`` for the
constraint mechanism.

Usage
-----
::

    python validate_canonical_metrics.py \\
        --workbook compiled_density_metrics.xlsx \\
        --dictionary metrics_dictionary.json \\
        --output validation_report.xlsx \\
        [--markdown validation_report.md] \\
        [--group-by Instrument] \\
        [--correlation-threshold 0.90] \\
        [--near-constant-std 1e-9] \\
        [--outlier-iqr-multiplier 1.5]

Library use
-----------
Every step is exposed as a pure function on top of pandas DataFrames so that
tests can drive the pipeline with a synthetic corpus without touching disk.
See ``tests/test_validate_canonical_metrics.py``.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Status keys used throughout this module.
STATUS_CANONICAL = "canonical"
STATUS_DIAGNOSTIC = "diagnostic"
STATUS_LEGACY = "legacy"


# ---------------------------------------------------------------------------
# Dictionary loading + canonical / PCA selection
# ---------------------------------------------------------------------------
@dataclass
class MetricDictionary:
    """Lightweight view over ``metrics_dictionary.json``.

    Attributes
    ----------
    schema_version : str
    metrics : Dict[str, Dict[str, Any]]
        Keyed by metric ``name``.
    allowed_metric_families : set[str]
    """

    schema_version: str
    metrics: Dict[str, Dict[str, Any]]
    allowed_metric_families: set = field(default_factory=set)

    @classmethod
    def load(cls, path: Path) -> "MetricDictionary":
        path = Path(path)
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if "metrics" not in data:
            raise ValueError(f"{path}: missing top-level 'metrics' list")
        by_name: Dict[str, Dict[str, Any]] = {}
        for entry in data["metrics"]:
            if "name" not in entry:
                raise ValueError("metrics_dictionary.json: entry without 'name'")
            by_name[entry["name"]] = entry
        fams = set(data.get("metric_family_enum", []))
        return cls(
            schema_version=str(data.get("schema_version", "")),
            metrics=by_name,
            allowed_metric_families=fams,
        )

    def canonical_names(self) -> List[str]:
        return [n for n, e in self.metrics.items() if e.get("status") == STATUS_CANONICAL]

    def diagnostic_names(self) -> List[str]:
        return [n for n, e in self.metrics.items() if e.get("status") == STATUS_DIAGNOSTIC]

    def legacy_names(self) -> List[str]:
        return [n for n, e in self.metrics.items() if e.get("status") == STATUS_LEGACY]

    def canonical_independent_for_pca(self) -> List[str]:
        out: List[str] = []
        for n, e in self.metrics.items():
            if e.get("status") != STATUS_CANONICAL:
                continue
            if e.get("independent_for_pca") is True:
                # Skip pure identifier metrics whose quantity_type is "metadata"
                # — they would not be meaningful PCA features.
                if e.get("quantity_type") == "metadata":
                    continue
                out.append(n)
        return out

    def family_groups(self, names: Iterable[str]) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = {}
        for n in names:
            fam = self.metrics.get(n, {}).get("metric_family") or "unspecified"
            groups.setdefault(fam, []).append(n)
        return groups

    def declared_dependency_pairs(self) -> set[Tuple[str, str]]:
        """All (a, b) ordered pairs where a derives_from b (declared algebraic dependency).

        We return BOTH orderings (a,b) and (b,a) so callers can do
        ``frozenset((p, q)) in declared_pairs_unordered`` for fast lookup.
        """
        pairs: set[Tuple[str, str]] = set()
        for n, e in self.metrics.items():
            for parent in e.get("derived_from", []):
                pairs.add((n, parent))
                pairs.add((parent, n))
        return pairs


# ---------------------------------------------------------------------------
# Workbook loading
# ---------------------------------------------------------------------------
def load_canonical_metrics_from_workbook(
    workbook_path: Path,
    *,
    sheet_name: str = "Canonical_Metrics",
) -> pd.DataFrame:
    """Read the ``Canonical_Metrics`` sheet from a compiled workbook.

    Raises ``FileNotFoundError`` if the workbook is missing. If the sheet is
    not present, a ``KeyError`` is raised so the caller can decide whether to
    treat it as a hard failure.
    """
    workbook_path = Path(workbook_path)
    if not workbook_path.is_file():
        raise FileNotFoundError(f"Workbook not found: {workbook_path}")
    xl = pd.ExcelFile(workbook_path)
    if sheet_name not in xl.sheet_names:
        raise KeyError(
            f"Sheet {sheet_name!r} not found in {workbook_path}. "
            f"Available: {xl.sheet_names}"
        )
    return pd.read_excel(workbook_path, sheet_name=sheet_name)


# ---------------------------------------------------------------------------
# Section 1 — corpus summary
# ---------------------------------------------------------------------------
def build_corpus_summary(
    df: pd.DataFrame,
    *,
    group_by: Optional[List[str]] = None,
) -> pd.DataFrame:
    """One-row corpus summary plus an optional per-group count table.

    Returns a long ``Key / Value`` DataFrame. The optional grouping is
    appended at the bottom so the result is a single rectangular sheet.
    """
    n_rows = int(len(df))
    rows: List[Dict[str, Any]] = [
        {"Key": "n_rows_total", "Value": n_rows},
        {"Key": "n_columns_total", "Value": int(df.shape[1])},
    ]
    for col in ("Note", "source_file_name", "tier", "Instrument"):
        if col in df.columns:
            rows.append({"Key": f"n_unique_{col}", "Value": int(df[col].nunique(dropna=True))})

    if group_by:
        present_groups = [g for g in group_by if g in df.columns]
        if present_groups:
            grouper = present_groups[0] if len(present_groups) == 1 else present_groups
            counts = (
                df.groupby(grouper, dropna=False).size().reset_index(name="row_count")
            )
            for _, r in counts.iterrows():
                key = "group(" + ", ".join(f"{g}={r[g]!r}" for g in present_groups) + ")"
                rows.append({"Key": key, "Value": int(r["row_count"])})

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Section 2 — canonical coverage + missing values
# ---------------------------------------------------------------------------
def compute_canonical_coverage(
    df: pd.DataFrame,
    canonical_names: List[str],
) -> pd.DataFrame:
    """For every canonical metric: 'present?', non-null count, NaN count."""
    rows: List[Dict[str, Any]] = []
    n_rows = int(len(df))
    for name in canonical_names:
        present = name in df.columns
        non_null = int(df[name].notna().sum()) if present else 0
        nan_count = (n_rows - non_null) if present else n_rows
        rows.append(
            {
                "metric": name,
                "present_in_workbook": present,
                "non_null_count": non_null,
                "nan_count": nan_count,
                "coverage_fraction": (non_null / n_rows) if n_rows else 0.0,
            }
        )
    return pd.DataFrame(rows)


def compute_missing_values_summary(
    df: pd.DataFrame,
    metrics: List[str],
) -> pd.DataFrame:
    """Detailed missing-value table per metric (and per group if columns exist)."""
    present = [m for m in metrics if m in df.columns]
    rows: List[Dict[str, Any]] = []
    n_rows = int(len(df))
    for m in present:
        nans = int(df[m].isna().sum())
        rows.append(
            {
                "metric": m,
                "nan_count": nans,
                "nan_fraction": (nans / n_rows) if n_rows else 0.0,
                "first_nan_note": _first_nan_note(df, m),
            }
        )
    return pd.DataFrame(rows)


def _first_nan_note(df: pd.DataFrame, m: str) -> str:
    if "Note" not in df.columns:
        return ""
    mask = df[m].isna()
    if not bool(mask.any()):
        return ""
    return str(df.loc[mask, "Note"].iloc[0])


# ---------------------------------------------------------------------------
# Section 3 — descriptive statistics
# ---------------------------------------------------------------------------
def compute_descriptive_stats(
    df: pd.DataFrame,
    metrics: List[str],
    *,
    group_by: Optional[List[str]] = None,
) -> pd.DataFrame:
    """``pandas.describe()`` plus group breakdowns when columns are available.

    Always returns a long-form DataFrame with columns ``group``, ``metric``,
    ``count``, ``mean``, ``std``, ``min``, ``q25``, ``median``, ``q75``,
    ``max``.
    """
    present = [m for m in metrics if m in df.columns]
    if not present:
        return pd.DataFrame(
            columns=[
                "group", "metric", "count", "mean", "std",
                "min", "q25", "median", "q75", "max",
            ]
        )

    def _describe(sub_df: pd.DataFrame, group_label: str) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for m in present:
            s = pd.to_numeric(sub_df[m], errors="coerce")
            out.append(
                {
                    "group": group_label,
                    "metric": m,
                    "count": int(s.notna().sum()),
                    "mean": float(s.mean(skipna=True)) if s.notna().any() else math.nan,
                    "std": float(s.std(skipna=True)) if s.notna().any() else math.nan,
                    "min": float(s.min(skipna=True)) if s.notna().any() else math.nan,
                    "q25": float(s.quantile(0.25)) if s.notna().any() else math.nan,
                    "median": float(s.median(skipna=True)) if s.notna().any() else math.nan,
                    "q75": float(s.quantile(0.75)) if s.notna().any() else math.nan,
                    "max": float(s.max(skipna=True)) if s.notna().any() else math.nan,
                }
            )
        return out

    rows: List[Dict[str, Any]] = _describe(df, "ALL")
    if group_by:
        present_g = [g for g in group_by if g in df.columns]
        if present_g:
            # Use ``by=`` and unwrap length-1 grouper to avoid pandas
            # FutureWarning about list-of-one keys.
            grouper = present_g[0] if len(present_g) == 1 else present_g
            for keys, sub in df.groupby(grouper, dropna=False):
                if not isinstance(keys, tuple):
                    keys = (keys,)
                label = " | ".join(
                    f"{name}={val!r}" for name, val in zip(present_g, keys)
                )
                rows.extend(_describe(sub, label))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Section 4 — correlation + redundancy + near-constants
# ---------------------------------------------------------------------------
def compute_correlation_matrix(
    df: pd.DataFrame,
    metrics: List[str],
) -> pd.DataFrame:
    """Pearson correlation matrix restricted to numeric, non-constant metrics."""
    usable = [m for m in metrics if m in df.columns and _is_numeric_non_constant(df[m])]
    if len(usable) < 2:
        return pd.DataFrame(index=usable, columns=usable, dtype=float)
    num = df[usable].apply(pd.to_numeric, errors="coerce")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        corr = num.corr(method="pearson")
    return corr


def _is_numeric_non_constant(s: pd.Series, *, std_threshold: float = 1e-12) -> bool:
    sn = pd.to_numeric(s, errors="coerce")
    if sn.notna().sum() < 2:
        return False
    std = float(sn.std(skipna=True) or 0.0)
    return std > std_threshold


def find_high_correlations(
    corr: pd.DataFrame,
    *,
    threshold: float = 0.90,
    declared_dependency_pairs: Optional[set[Tuple[str, str]]] = None,
) -> pd.DataFrame:
    """Return pairs with |r| ≥ threshold (excluding the trivial diagonal).

    The returned DataFrame separates **algebraic redundancy** (the pair is
    already declared in ``metrics_dictionary.json`` → ``derived_from``) from
    **empirical redundancy** (observed in this corpus but not declared).
    """
    declared = declared_dependency_pairs or set()
    cols = list(corr.columns)
    rows: List[Dict[str, Any]] = []
    for i, a in enumerate(cols):
        for j in range(i + 1, len(cols)):
            b = cols[j]
            r_val = corr.iloc[i, j]
            if r_val is None or not np.isfinite(r_val):
                continue
            if abs(float(r_val)) >= float(threshold):
                redundancy = "algebraic" if (a, b) in declared else "empirical"
                rows.append(
                    {
                        "metric_a": a,
                        "metric_b": b,
                        "pearson_r": float(r_val),
                        "abs_r": abs(float(r_val)),
                        "redundancy_type": redundancy,
                    }
                )
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values("abs_r", ascending=False).reset_index(drop=True)
    return out


def detect_near_constant_metrics(
    df: pd.DataFrame,
    metrics: List[str],
    *,
    std_threshold: float = 1e-9,
) -> pd.DataFrame:
    """Identify metrics with negligible variance (potentially uninformative)."""
    rows: List[Dict[str, Any]] = []
    for m in metrics:
        if m not in df.columns:
            continue
        s = pd.to_numeric(df[m], errors="coerce")
        if s.notna().sum() < 2:
            rows.append(
                {
                    "metric": m,
                    "std": math.nan,
                    "unique_finite_values": int(s.dropna().nunique()),
                    "warning": "fewer than 2 non-null values",
                }
            )
            continue
        std = float(s.std(skipna=True) or 0.0)
        uniq = int(s.dropna().nunique())
        if std <= std_threshold:
            rows.append(
                {
                    "metric": m,
                    "std": std,
                    "unique_finite_values": uniq,
                    "warning": f"near-constant (std={std:.3e}, ≤ {std_threshold:.0e})",
                }
            )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Section 5 — outlier detection (IQR fences)
# ---------------------------------------------------------------------------
def detect_outlier_rows(
    df: pd.DataFrame,
    metrics: List[str],
    *,
    iqr_multiplier: float = 1.5,
    max_outliers_per_metric: int = 100,
) -> pd.DataFrame:
    """Per-metric IQR outliers. Returns long-form (metric, note, value, fence)."""
    rows: List[Dict[str, Any]] = []
    note_col = "Note" if "Note" in df.columns else None
    for m in metrics:
        if m not in df.columns:
            continue
        s = pd.to_numeric(df[m], errors="coerce")
        sn = s.dropna()
        if sn.size < 4:
            continue
        q1 = float(sn.quantile(0.25))
        q3 = float(sn.quantile(0.75))
        iqr = q3 - q1
        if iqr <= 0:
            continue
        lo = q1 - iqr_multiplier * iqr
        hi = q3 + iqr_multiplier * iqr
        mask = (s < lo) | (s > hi)
        idx = list(df.index[mask])[:max_outliers_per_metric]
        for ix in idx:
            rows.append(
                {
                    "metric": m,
                    "row_index": int(ix),
                    "Note": str(df.at[ix, note_col]) if note_col else "",
                    "value": float(s.at[ix]),
                    "lower_fence": lo,
                    "upper_fence": hi,
                }
            )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Section 6 — PCA on independent_for_pca=true metrics only
# ---------------------------------------------------------------------------
@dataclass
class PCAResult:
    feature_list: List[str]
    loadings: pd.DataFrame
    explained_variance: pd.DataFrame
    note: str = ""


def run_pca_on_canonical(
    df: pd.DataFrame,
    feature_names: List[str],
    *,
    minimum_samples: int = 4,
) -> PCAResult:
    """PCA restricted to independent_for_pca=true canonical metrics.

    Drops near-constant features automatically. Returns an empty result with
    a non-empty ``note`` if the matrix is too small / degenerate.
    """
    usable = [
        m for m in feature_names
        if m in df.columns and _is_numeric_non_constant(df[m])
    ]
    if len(usable) < 2 or len(df) < minimum_samples:
        return PCAResult(
            feature_list=usable,
            loadings=pd.DataFrame(),
            explained_variance=pd.DataFrame(),
            note=(
                f"PCA skipped: usable_features={len(usable)} (need ≥2), "
                f"samples={len(df)} (need ≥{minimum_samples})."
            ),
        )

    try:
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        return PCAResult(
            feature_list=usable,
            loadings=pd.DataFrame(),
            explained_variance=pd.DataFrame(),
            note="PCA skipped: scikit-learn not installed.",
        )

    X = df[usable].apply(pd.to_numeric, errors="coerce")
    col_means = X.mean(numeric_only=True)
    X_imputed = X.fillna(col_means).fillna(0.0).to_numpy(dtype=float)
    Xz = StandardScaler().fit_transform(X_imputed)
    n_comp = int(min(3, Xz.shape[0], Xz.shape[1]))
    if n_comp < 1:
        return PCAResult(
            feature_list=usable,
            loadings=pd.DataFrame(),
            explained_variance=pd.DataFrame(),
            note="PCA skipped: degenerate after standardisation.",
        )
    pca = PCA(n_components=n_comp, random_state=42)
    pca.fit(Xz)

    loadings = pd.DataFrame(
        {f"PC{i + 1}_loading": pca.components_[i] for i in range(n_comp)},
        index=usable,
    ).reset_index().rename(columns={"index": "Feature"})

    evr = pca.explained_variance_ratio_.astype(float)
    explained = pd.DataFrame(
        {
            "Component": [f"PC{i + 1}" for i in range(len(evr))],
            "explained_variance_ratio": evr,
            "cumulative_explained_variance": np.cumsum(evr),
        }
    )
    return PCAResult(
        feature_list=usable,
        loadings=loadings,
        explained_variance=explained,
        note="ok",
    )


# ---------------------------------------------------------------------------
# Section 7 — interpretation limits (driven by dictionary, not inferred)
# ---------------------------------------------------------------------------
def _make_interpretation_limits_rows(
    md: MetricDictionary,
    metrics: List[str],
) -> pd.DataFrame:
    """Surface every metric's documented interpretation + do-not-interpret-as.

    This section is the *only* place where validation language is allowed to
    describe what each metric means. The text is taken verbatim from the
    dictionary, so this script does NOT introduce musicological claims.
    """
    rows: List[Dict[str, Any]] = []
    for m in metrics:
        e = md.metrics.get(m, {})
        if not e:
            rows.append(
                {
                    "metric": m,
                    "status": "(missing from dictionary)",
                    "metric_family": "",
                    "formula": "",
                    "quantity_type": "",
                    "denominator": "",
                    "interpretation": "",
                    "do_not_interpret_as": "",
                    "independent_for_pca": "",
                    "derived_from": "",
                }
            )
            continue
        rows.append(
            {
                "metric": m,
                "status": e.get("status", ""),
                "metric_family": e.get("metric_family", ""),
                "formula": e.get("formula", ""),
                "quantity_type": e.get("quantity_type", ""),
                "denominator": e.get("denominator", ""),
                "interpretation": e.get("interpretation", ""),
                "do_not_interpret_as": e.get("do_not_interpret_as", ""),
                "independent_for_pca": e.get("independent_for_pca", ""),
                "derived_from": ", ".join(e.get("derived_from", []) or []),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------
@dataclass
class ValidationReport:
    """Container for every section produced by :func:`validate_corpus`."""

    corpus_summary: pd.DataFrame
    canonical_coverage: pd.DataFrame
    missing_values: pd.DataFrame
    descriptive_stats: pd.DataFrame
    correlation_matrix: pd.DataFrame
    high_correlations: pd.DataFrame
    near_constant: pd.DataFrame
    outliers: pd.DataFrame
    pca: PCAResult
    pca_feature_list: pd.DataFrame
    interpretation_limits: pd.DataFrame
    warnings: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)


def validate_corpus(
    df: pd.DataFrame,
    dictionary: MetricDictionary,
    *,
    group_by: Optional[List[str]] = None,
    correlation_threshold: float = 0.90,
    near_constant_std: float = 1e-9,
    outlier_iqr_multiplier: float = 1.5,
    pca_minimum_samples: int = 4,
) -> ValidationReport:
    """Run the full validation pipeline on an already-loaded DataFrame.

    The function emits a :class:`ValidationReport` with one DataFrame per
    section plus a list of human-readable warnings.
    """
    canonical_names = dictionary.canonical_names()
    pca_features_declared = dictionary.canonical_independent_for_pca()

    warns: List[str] = []

    # ----- guard: warn about non-canonical columns silently present
    non_canonical_in_df = [
        c for c in df.columns
        if c in dictionary.metrics
        and dictionary.metrics[c].get("status") != STATUS_CANONICAL
    ]
    if non_canonical_in_df:
        warns.append(
            "WARN: workbook also contains diagnostic/legacy columns "
            f"({len(non_canonical_in_df)}): they are intentionally excluded "
            "from canonical statistics. Sample: "
            f"{non_canonical_in_df[:5]}"
        )

    # ----- coverage + missing values
    coverage = compute_canonical_coverage(df, canonical_names)
    missing_canonical = [
        row["metric"] for _, row in coverage.iterrows()
        if not row["present_in_workbook"]
    ]
    for m in missing_canonical:
        warns.append(f"MISSING: canonical metric not in workbook: {m}")

    missing_table = compute_missing_values_summary(df, canonical_names)

    # ----- descriptive stats restricted to canonical metrics that exist
    present_canonical = [m for m in canonical_names if m in df.columns]
    desc = compute_descriptive_stats(df, present_canonical, group_by=group_by)

    # ----- correlations + redundancy
    corr = compute_correlation_matrix(df, present_canonical)
    declared_pairs = dictionary.declared_dependency_pairs()
    high_corr = find_high_correlations(
        corr,
        threshold=correlation_threshold,
        declared_dependency_pairs=declared_pairs,
    )
    if not high_corr.empty:
        n_algebraic = int((high_corr["redundancy_type"] == "algebraic").sum())
        n_empirical = int((high_corr["redundancy_type"] == "empirical").sum())
        warns.append(
            f"REDUNDANCY: {len(high_corr)} canonical pairs with |r| ≥ "
            f"{correlation_threshold:.2f} (algebraic={n_algebraic}, empirical={n_empirical})."
        )

    # ----- near-constants
    near_const = detect_near_constant_metrics(
        df, present_canonical, std_threshold=near_constant_std
    )
    if not near_const.empty:
        warns.append(
            f"NEAR-CONSTANT: {len(near_const)} canonical metric(s) have std ≤ "
            f"{near_constant_std:.0e}. They will be excluded from PCA."
        )

    # ----- outliers
    outliers = detect_outlier_rows(
        df, present_canonical, iqr_multiplier=outlier_iqr_multiplier
    )

    # ----- PCA (restricted to declared-independent canonical features)
    pca_features_in_corpus = [m for m in pca_features_declared if m in df.columns]
    pca_excluded = sorted(set(pca_features_declared) - set(pca_features_in_corpus))
    pca = run_pca_on_canonical(
        df, pca_features_in_corpus, minimum_samples=pca_minimum_samples
    )

    # Cross-check: confirm no PCA feature is independent_for_pca=false
    bad_pca = [
        f for f in pca.feature_list
        if dictionary.metrics.get(f, {}).get("independent_for_pca") is not True
    ]
    if bad_pca:
        warns.append(
            f"FATAL POLICY VIOLATION: PCA contains independent_for_pca=false "
            f"metrics: {bad_pca}. This must not happen and indicates a "
            "regression in validate_canonical_metrics.py."
        )

    pca_feature_list = pd.DataFrame(
        {
            "feature": pca.feature_list,
            "included_in_pca": True,
        }
    )
    if pca_excluded:
        # Document excluded-because-missing features as well, for transparency.
        excluded_df = pd.DataFrame(
            {
                "feature": pca_excluded,
                "included_in_pca": False,
            }
        )
        pca_feature_list = pd.concat(
            [pca_feature_list, excluded_df], axis=0, ignore_index=True
        )

    # Also list rejected-because-dependent canonical metrics, so the report
    # explicitly shows the inclusion/exclusion policy.
    dependent_canonical = [
        n for n in dictionary.canonical_names()
        if dictionary.metrics[n].get("independent_for_pca") is False
        and dictionary.metrics[n].get("quantity_type") != "metadata"
    ]
    if dependent_canonical:
        excluded_dep_df = pd.DataFrame(
            {
                "feature": dependent_canonical,
                "included_in_pca": False,
            }
        )
        pca_feature_list = pd.concat(
            [pca_feature_list, excluded_dep_df], axis=0, ignore_index=True
        )

    # ----- interpretation limits (text from dictionary, no inference)
    interp = _make_interpretation_limits_rows(dictionary, present_canonical)

    # ----- corpus summary
    summary = build_corpus_summary(df, group_by=group_by)

    return ValidationReport(
        corpus_summary=summary,
        canonical_coverage=coverage,
        missing_values=missing_table,
        descriptive_stats=desc,
        correlation_matrix=corr.reset_index().rename(columns={"index": "metric"})
        if not corr.empty else corr,
        high_correlations=high_corr,
        near_constant=near_const,
        outliers=outliers,
        pca=pca,
        pca_feature_list=pca_feature_list,
        interpretation_limits=interp,
        warnings=warns,
        settings={
            "correlation_threshold": correlation_threshold,
            "near_constant_std": near_constant_std,
            "outlier_iqr_multiplier": outlier_iqr_multiplier,
            "pca_minimum_samples": pca_minimum_samples,
            "dictionary_schema_version": dictionary.schema_version,
        },
    )


# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------
def write_report_excel(path: Path, report: ValidationReport) -> Path:
    """Write the full report as a multi-sheet Excel workbook."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        # Sheet 1 — top-level summary
        report.corpus_summary.to_excel(writer, sheet_name="Corpus_Summary", index=False)
        # Sheet 2 — coverage
        report.canonical_coverage.to_excel(
            writer, sheet_name="Canonical_Coverage", index=False
        )
        # Sheet 3 — missing values
        if not report.missing_values.empty:
            report.missing_values.to_excel(
                writer, sheet_name="Missing_Values", index=False
            )
        # Sheet 4 — descriptive stats
        if not report.descriptive_stats.empty:
            report.descriptive_stats.to_excel(
                writer, sheet_name="Descriptive_Stats", index=False
            )
        # Sheet 5 — correlation matrix
        if not report.correlation_matrix.empty:
            report.correlation_matrix.to_excel(
                writer, sheet_name="Correlation_Matrix", index=False
            )
        # Sheet 6 — high correlations
        if not report.high_correlations.empty:
            report.high_correlations.to_excel(
                writer, sheet_name="High_Correlations", index=False
            )
        # Sheet 7 — near-constant
        if not report.near_constant.empty:
            report.near_constant.to_excel(
                writer, sheet_name="Near_Constant", index=False
            )
        # Sheet 8 — outliers
        if not report.outliers.empty:
            report.outliers.to_excel(writer, sheet_name="Outliers", index=False)
        # Sheets 9-10 — PCA
        if not report.pca.loadings.empty:
            report.pca.loadings.to_excel(
                writer, sheet_name="PCA_Loadings", index=False
            )
        if not report.pca.explained_variance.empty:
            report.pca.explained_variance.to_excel(
                writer, sheet_name="PCA_Variance", index=False
            )
        report.pca_feature_list.to_excel(
            writer, sheet_name="PCA_Feature_List", index=False
        )
        # Sheet 11 — interpretation limits
        report.interpretation_limits.to_excel(
            writer, sheet_name="Interpretation_Limits", index=False
        )
        # Sheet 12 — warnings + settings
        warn_df = pd.DataFrame({"warning": report.warnings or []})
        warn_df.to_excel(writer, sheet_name="Warnings", index=False)
        settings_df = pd.DataFrame(
            {"key": list(report.settings.keys()), "value": list(report.settings.values())}
        )
        settings_df.to_excel(writer, sheet_name="Settings", index=False)
    return path


def write_report_markdown(path: Path, report: ValidationReport) -> Path:
    """Write a human-readable Markdown twin of the Excel report.

    The Markdown is intentionally restricted to physical-acoustic language;
    every per-metric statement is sourced from the dictionary.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append("# Canonical metrics validation report")
    lines.append("")
    lines.append(
        "This report is generated by `validate_canonical_metrics.py`. "
        "It is restricted to canonical metrics declared in "
        "`metrics_dictionary.json`. Diagnostic / legacy metrics are "
        "deliberately excluded. No musicological claims are inferred — "
        "interpretation language is taken verbatim from each metric's "
        "dictionary entry."
    )
    lines.append("")

    lines.append("## Corpus summary")
    lines.append(_df_to_markdown(report.corpus_summary))

    lines.append("## Canonical metric coverage")
    lines.append(_df_to_markdown(report.canonical_coverage))

    if not report.missing_values.empty:
        lines.append("## Missing values")
        lines.append(_df_to_markdown(report.missing_values))

    if not report.descriptive_stats.empty:
        lines.append("## Descriptive statistics")
        lines.append(_df_to_markdown(report.descriptive_stats))

    if not report.high_correlations.empty:
        lines.append("## Correlation / redundancy analysis")
        lines.append(
            f"Pairs with |r| ≥ {report.settings.get('correlation_threshold', 0.90):.2f}. "
            "*algebraic* means the relation is declared in "
            "`metrics_dictionary.json → derived_from`; *empirical* means the "
            "high correlation is observed in this corpus but not declared."
        )
        lines.append("")
        lines.append(_df_to_markdown(report.high_correlations))

    if not report.near_constant.empty:
        lines.append("## Near-constant canonical metrics")
        lines.append(_df_to_markdown(report.near_constant))

    if not report.outliers.empty:
        lines.append("## Outlier rows (IQR fences)")
        lines.append(_df_to_markdown(report.outliers.head(50)))

    lines.append("## PCA feature list")
    lines.append(
        "PCA is restricted to canonical metrics with "
        "`independent_for_pca=true` in `metrics_dictionary.json`. Metrics "
        "marked `independent_for_pca=false` (algebraic complements, exact "
        "ratios, aliases) are excluded by design."
    )
    lines.append("")
    lines.append(_df_to_markdown(report.pca_feature_list))
    if report.pca.note:
        lines.append("")
        lines.append(f"PCA note: {report.pca.note}")

    if not report.pca.loadings.empty:
        lines.append("## PCA loadings")
        lines.append(_df_to_markdown(report.pca.loadings))
    if not report.pca.explained_variance.empty:
        lines.append("## PCA explained variance")
        lines.append(_df_to_markdown(report.pca.explained_variance))

    lines.append("## Interpretation limits")
    lines.append(
        "Every metric is documented below with `interpretation` and "
        "`do_not_interpret_as` text taken verbatim from "
        "`metrics_dictionary.json`. Readers should treat statements "
        "beyond this dictionary entry as out of scope for this report."
    )
    lines.append("")
    lines.append(_df_to_markdown(report.interpretation_limits))

    lines.append("## Warnings")
    if report.warnings:
        for w in report.warnings:
            lines.append(f"- {w}")
    else:
        lines.append("(no warnings)")
    lines.append("")
    lines.append("## Settings")
    lines.append(
        _df_to_markdown(
            pd.DataFrame(
                {
                    "key": list(report.settings.keys()),
                    "value": [str(v) for v in report.settings.values()],
                }
            )
        )
    )

    path.write_text("\n\n".join(lines), encoding="utf-8")
    return path


def _df_to_markdown(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "_(empty)_"
    try:
        return df.to_markdown(index=False)
    except Exception:
        # ``to_markdown`` requires the optional ``tabulate`` extra; degrade
        # gracefully to a fenced CSV if it is missing.
        return "```\n" + df.to_csv(index=False) + "\n```"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="validate_canonical_metrics",
        description=(
            "Scientific validation of the SoundSpectrAnalyse canonical "
            "metrics. Reads a compiled workbook plus metrics_dictionary.json "
            "and emits a validation report (xlsx and/or md). Performs no "
            "musicological inference."
        ),
    )
    p.add_argument("--workbook", type=Path, required=True,
                   help="Compiled workbook with a Canonical_Metrics sheet.")
    p.add_argument("--dictionary", type=Path,
                   default=Path("metrics_dictionary.json"),
                   help="Path to metrics_dictionary.json.")
    p.add_argument("--output", type=Path, default=Path("validation_report.xlsx"),
                   help="Excel output path.")
    p.add_argument("--markdown", type=Path, default=None,
                   help="Optional Markdown output path.")
    p.add_argument("--group-by", action="append", default=None,
                   help="Group descriptive stats / summary by this column "
                        "(may be passed multiple times).")
    p.add_argument("--correlation-threshold", type=float, default=0.90)
    p.add_argument("--near-constant-std", type=float, default=1e-9)
    p.add_argument("--outlier-iqr-multiplier", type=float, default=1.5)
    p.add_argument("--pca-minimum-samples", type=int, default=4)
    p.add_argument("--canonical-sheet-name", type=str, default="Canonical_Metrics")
    p.add_argument("-v", "--verbose", action="count", default=0)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING - 10 * int(args.verbose),
        format="%(levelname)s %(name)s: %(message)s",
    )
    md = MetricDictionary.load(args.dictionary)
    df = load_canonical_metrics_from_workbook(
        args.workbook, sheet_name=args.canonical_sheet_name
    )
    report = validate_corpus(
        df,
        md,
        group_by=args.group_by,
        correlation_threshold=args.correlation_threshold,
        near_constant_std=args.near_constant_std,
        outlier_iqr_multiplier=args.outlier_iqr_multiplier,
        pca_minimum_samples=args.pca_minimum_samples,
    )
    write_report_excel(args.output, report)
    if args.markdown:
        write_report_markdown(args.markdown, report)
    for w in report.warnings:
        logger.warning("%s", w)
    print(
        f"Validation report written to {args.output}"
        + (f" (+ {args.markdown})" if args.markdown else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
