from __future__ import annotations

import pipeline_orchestrator_gui as pog


def test_obs_ws_artifact_flag_true_for_high_obs_ws_with_negligible_subbass_energy() -> None:
    flagged = pog.compute_obs_ws_artifact_diagnostics(
        pure_observation_w_h=0.75,
        pure_observation_w_i=0.05,
        pure_observation_w_s=0.20,
        component_subbass_energy_ratio=1e-6,
        harmonic_energy_sum=10.0,
        subbass_energy_sum=1e-8,
    )
    assert flagged["obs_wS"] == 0.20
    assert flagged["obs_wS_artifact_flag"] is True
    assert str(flagged["obs_wS_artifact_reason"]).strip() != ""
    assert (
        str(flagged["subbass_component_interpretation"]).strip()
        == "model_density_residual_not_physical_subbass_energy"
    )


def test_obs_ws_artifact_flag_false_for_real_subbass_case() -> None:
    flagged = pog.compute_obs_ws_artifact_diagnostics(
        pure_observation_w_h=0.65,
        pure_observation_w_i=0.15,
        pure_observation_w_s=0.20,
        component_subbass_energy_ratio=0.15,
        harmonic_energy_sum=1.0,
        subbass_energy_sum=0.2,
    )
    assert flagged["obs_wS"] == 0.20
    assert flagged["obs_wS_artifact_flag"] is False
