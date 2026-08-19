from __future__ import annotations

from pathlib import Path

from compile_metrics import (
    DENSITY_WEIGHT_FUNCTION_DEFAULT as COMPILE_DEFAULT,
    _normalise_density_weight_function,
)
from constants import DENSITY_WEIGHT_FUNCTION_DEFAULT
from proc_audio import AudioProcessor, PRIMARY_COMPARABLE_WEIGHT_FUNCTION
from tools.ewsd_sensitivity_report import (
    ewsd_balanced_by_phi_from_compartments,
    min_phi_spearman_rho,
    phi_rank_stability,
    run_phi_report,
)


def test_documented_default_phi_is_log() -> None:
    assert DENSITY_WEIGHT_FUNCTION_DEFAULT == "log"
    assert COMPILE_DEFAULT == "log"
    assert PRIMARY_COMPARABLE_WEIGHT_FUNCTION == "log"
    ap = AudioProcessor()
    assert ap.weight_function == "log"
    assert _normalise_density_weight_function(None) == "log"
    assert _normalise_density_weight_function("") == "log"
    assert _normalise_density_weight_function("unknown") == "log"
    assert AudioProcessor._normalize_weight_function_ui_key(None) == "log"


def test_analysis_parameter_profile_id_includes_weight_function() -> None:
    ap = AudioProcessor()
    ap.density_salience_threshold_db = -40.0
    ap.density_frequency_ceiling_hz = 5000.0
    row = ap._build_main_metrics_export_row("A2", h_psum=1.0, i_psum=0.0, s_psum=0.0, t_psum=1.0)
    assert row["weight_function"] == "log"
    assert str(row["analysis_parameter_profile_id"]).startswith("wf=log|")


def test_phi_rank_stability_on_synthetic_tuba_like_notes() -> None:
    notes = _synthetic_tuba_like_notes()
    scores = ewsd_balanced_by_phi_from_compartments(notes)
    assert len(scores) == len(notes)
    assert "log" in scores.columns and "linear" in scores.columns
    stability = phi_rank_stability(scores)
    assert not stability.empty
    min_rho = min_phi_spearman_rho(stability)
    assert min_rho == min_rho  # finite
    payload = run_phi_report(notes=notes, source="synthetic tuba-like construct")
    assert payload["n_notes"] == len(notes)
    assert "min_spearman_rho" in payload


def test_readme_records_measured_phi_rho() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    report = Path("docs/validation/EWSD_SENSITIVITY_PHI.md").read_text(encoding="utf-8")
    assert "not" in readme and "invariant" in readme
    assert "0.075" in readme
    assert "0.948" in readme
    assert "0.0754" in report
    assert "0.9478" in report


def _synthetic_tuba_like_notes() -> list[dict]:
    """Low-register brass-like H/I/S amplitude vectors for φ rank tests."""
    notes = []
    for i, name in enumerate(("A1", "C2", "E2", "A2", "C3", "E3", "A3", "C4")):
        n_h = 10 - i
        decay = 0.72 + 0.02 * i
        h = [1.0 * (decay ** k) for k in range(n_h)]
        i_amps = [0.12 * (0.85 ** k) for k in range(max(1, 4 - i // 3))]
        s_amps = [0.08 * (1.0 - 0.1 * i)] if i < 5 else [0.01]
        h_e = sum(a * a for a in h)
        i_e = sum(a * a for a in i_amps)
        s_e = sum(a * a for a in s_amps)
        tot = h_e + i_e + s_e
        notes.append(
            {
                "Note": name,
                "compartments": [
                    {"family": "H", "amplitudes": h, "analysis_ratio": h_e / tot},
                    {"family": "I", "amplitudes": i_amps, "analysis_ratio": i_e / tot},
                    {"family": "S", "amplitudes": s_amps, "analysis_ratio": s_e / tot},
                ],
            }
        )
    return notes
