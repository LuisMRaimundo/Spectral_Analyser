"""Resolve harmonic / inharmonic model coefficients (α / β) for GUI analysis.

These weights are passed to :class:`AudioProcessor` as ``harmonic_weight`` /
``inharmonic_weight``. They are *not* the same as the per-note component
energy ratios.

In the Stage 1 / Stage 2 pipeline the canonical source of these weights is
the current per-note spectral analysis. ``proc_audio.AudioProcessor`` derives
them from the spectrum when ``auto_model_weights_from_analysis=True`` is
passed (this is the default in the current orchestrator); the GUI therefore
hands neutral placeholders to the processor and lets the analysis populate
the final values. A manual override lets the user force a particular α /
β if needed.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def resolve_analysis_model_weights(
    manual_override: bool,
    slider_harmonic_fraction: float,
    batch_payload: Optional[Dict[str, Any]] = None,  # back-compat; unused
) -> Tuple[float, float, Dict[str, Any]]:
    """Return ``(harmonic_weight, inharmonic_weight, metadata)`` for one
    analysis run.

    ``manual_override``: when True, use the slider fraction as α and 1-α as
    β; metadata records ``model_weights_source = manual_override``.

    Otherwise the GUI passes neutral placeholders (0.5, 0.5) to
    :class:`AudioProcessor`; the processor then overwrites them with the
    coefficients derived from the current per-note spectrum. The metadata
    therefore reports ``model_weights_source = current_analysis``.

    ``batch_payload`` is retained for backwards-compatible callers but is
    ignored: the Stage 1 / Stage 2 pipeline does not consult any external
    H / I / S mapping.
    """
    slider_alpha = max(0.0, min(1.0, float(slider_harmonic_fraction)))
    meta_out: Dict[str, Any] = {
        "model_weight_denominator": "harmonic_plus_inharmonic",
        "external_component_profile_used": False,
        "external_h_i_s_mapping_used": False,
    }

    if manual_override:
        meta_out["model_weights_source"] = "manual_override"
        meta_out["model_weights_warning"] = (
            "manual_model_weight_override:overrides_current_analysis_weights"
        )
        meta_out["manual_model_harmonic_weight"] = float(slider_alpha)
        meta_out["manual_model_inharmonic_weight"] = float(1.0 - slider_alpha)
        return float(slider_alpha), float(1.0 - slider_alpha), meta_out

    meta_out["model_weights_source"] = "current_analysis"
    meta_out["model_weights_warning"] = None
    meta_out["component_profile_source"] = "current_analysis"
    # Neutral placeholders. proc_audio will overwrite these once the
    # current spectrum has been classified.
    return 0.5, 0.5, meta_out
