"""
Human-readable amplitude weighting / discrete metric labels ↔ internal keys.

Used by ``interface.py`` (PyQt) and ``pipeline_orchestrator_gui.py`` (Tk) so both
stay aligned with ``density.get_weight_function`` without importing Qt in batch tools.
"""
from __future__ import annotations

from typing import Dict, Tuple

# (combo label shown to the user, internal key for density / proc_audio)
WEIGHT_FUNCTION_UI_CHOICES: Tuple[Tuple[str, str], ...] = (
    ("Linear", "linear"),
    ("Logarithmic", "log"),
    ("Square root", "sqrt"),
    ("Cube root", "cbrt"),
    ("Squared", "squared"),
    ("Cubic", "cubic"),
    ("Exponential", "exp"),
    ("Inverse log", "inverse log"),
    ("D3 (Σlog1p A)", "d3"),
    ("D10 (Σlog1p·N_eff/N)", "d10"),
    ("D17 (log1p E · log1p N_eff)", "d17"),
    ("D24 (filt+log)", "d24"),
)

WEIGHT_FUNCTION_COMBO_LABELS: Tuple[str, ...] = tuple(d for d, _ in WEIGHT_FUNCTION_UI_CHOICES)

# Lowercased display strings where Σ → σ (Unicode case fold), for saved presets / typed text.
_LEGACY_WEIGHT_LABEL_MAP: Dict[str, str] = {
    "log": "log",
    "logarithmic": "log",
    "linear": "linear",
    "square root": "sqrt",
    "sqrt": "sqrt",
    "squared": "squared",
    "cubic": "cubic",
    "cube root": "cbrt",
    "cbrt": "cbrt",
    "exponential": "exp",
    "exp": "exp",
    "inverse log": "inverse log",
    "inverse logarithmic": "inverse log",
    "sum": "linear",
    "soma": "linear",
    # Removed D2/D8 from UI — map old keys & labels to supported metrics.
    "d2": "linear",
    "d8": "d17",
    "d3": "d3",
    "d10": "d10",
    "d17": "d17",
    "d24": "d24",
    "d2 (σa²)": "linear",
    "d3 (σlog1p a)": "d3",
    "d8 (n_eff)": "d17",
    "d10 (σlog1p·n_eff/n)": "d10",
    "d17 (log1p e · log1p n_eff)": "d17",
    "d24 (filt+log)": "d24",
    # Legacy Portuguese
    "logarítmica": "log",
    "logaritmica": "log",
    "raiz quadrada": "sqrt",
    "raiz cúbica": "cbrt",
    "quadrado": "squared",
    "quadrática": "squared",
    "quadratica": "squared",
    "square": "squared",
    "exponencial": "exp",
    # Orchestrator / old preset naming
    "quadratic": "linear",
}


def display_label_for_weight_key(key: str) -> str:
    """Return the UI combo label for an internal weight key, or the key itself if unknown."""
    k = (key or "").strip().lower()
    if k == "d2":
        return "Linear"
    if k == "d8":
        return "D17 (log1p E · log1p N_eff)"
    for disp, kk in WEIGHT_FUNCTION_UI_CHOICES:
        if kk == k:
            return disp
    s = (key or "").strip()
    return s if s else "—"


def resolve_weight_key_from_user_label(label: str) -> str:
    """
    Map a combo item or legacy/PT label to the internal key (e.g. ``log``, ``d3``).
    Unknown strings are returned lowercased/stripped for ``get_weight_function`` to validate.
    """
    if label is None:
        raise ValueError("Invalid weight function (label None).")
    raw = str(label).strip()
    low = raw.lower()

    for disp, key in WEIGHT_FUNCTION_UI_CHOICES:
        if disp.lower() == low:
            return key

    resolved = _LEGACY_WEIGHT_LABEL_MAP.get(low, low)
    if not resolved:
        raise ValueError(f"Invalid weight function: {label!r}")
    return resolved
