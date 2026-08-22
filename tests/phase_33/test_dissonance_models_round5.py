"""Round-5 dissonance_models repairs (export numbers change)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dissonance_models import (
    DEFAULT_DISSONANCE_METRIC_MODE,
    DISSONANCE_METRIC_MODES,
    HutchinsonKnopoffDissonance,
    SetharesDissonance,
    VassilakisDissonance,
    analyze_real_timbre,
    get_dissonance_model,
)
from tools.validation.dissonance_metric_mode import (
    GOLDEN_PATH,
    _legacy_sethares_override,
    _series_df,
    build_payload,
)


def test_default_metric_mode_is_minamp_norm() -> None:
    assert DEFAULT_DISSONANCE_METRIC_MODE == "minamp_norm"
    assert SetharesDissonance().metric_mode == "minamp_norm"
    df = _series_df(146.83)
    a = SetharesDissonance().calculate_dissonance_metric(df)
    b = SetharesDissonance().calculate_dissonance_metric(df, metric_mode="minamp_norm")
    assert a == pytest.approx(b)


def test_sethares_base_matches_legacy_override_on_golden_modes() -> None:
    df = _series_df(146.83, 20)
    for mode in DISSONANCE_METRIC_MODES:
        model = SetharesDissonance(metric_mode=mode)
        base = model.calculate_dissonance_metric(df, metric_mode=mode)
        old = _legacy_sethares_override(model, df)
        assert base == pytest.approx(old, rel=1e-12, abs=1e-12)


def test_all_three_models_accept_metric_mode_kwarg() -> None:
    df = _series_df(440.0, 8)
    for name in ("sethares", "hutchinson-knopoff", "vassilakis"):
        model = get_dissonance_model(name)
        value = model.calculate_dissonance_metric(df, metric_mode="minamp_norm")
        assert np.isfinite(value)


def test_hk_export_is_eq3_not_mean_pair() -> None:
    df = _series_df(146.83, 12)
    model = HutchinsonKnopoffDissonance()
    partials = list(zip(df["Frequency (Hz)"], df["Amplitude"]))
    eq3 = model.total_dissonance(partials, [])
    exported = model.calculate_dissonance_metric(df)
    legacy = model.legacy_mean_pair_scaled_dissonance(df)
    assert exported == pytest.approx(eq3)
    assert exported != pytest.approx(legacy)
    assert legacy > 0.0


def test_analyze_real_timbre_save_directory_none_does_not_crash() -> None:
    df = _series_df(440.0, 6)
    out = analyze_real_timbre(df, note_name="A4", save_directory=None)
    assert "metrics" in out
    assert out["metrics"]


def test_analyze_real_timbre_none_does_not_write_csv(tmp_path: Path) -> None:
    df = _series_df(440.0, 6)
    analyze_real_timbre(df, note_name="A4", save_directory=None)
    assert not (tmp_path / "dissonance_metrics.csv").exists()


def test_find_local_minima_is_symmetric() -> None:
    model = SetharesDissonance()
    # Centre is 0.0; left drop is 0.02, right drop is 0.005.
    # Old test applied sensitivity to the left neighbour only.
    curve = {1.0: 1.00, 1.1: 0.98, 1.2: 0.985}
    assert model.find_local_minima(curve, sensitivity=0.01) == []
    curve_sym = {1.0: 1.00, 1.1: 0.98, 1.2: 1.00}
    assert model.find_local_minima(curve_sym, sensitivity=0.01) == [1.1]


def test_g_table_is_lazy(monkeypatch: pytest.MonkeyPatch) -> None:
    import dissonance_models as dm

    def _boom() -> list:
        raise FileNotFoundError("missing hk1978_g_table.csv")

    monkeypatch.setattr(dm, "_load_hk_default_g_table", _boom)
    lazy = dm._LazyDefaultGTable()
    with pytest.raises(FileNotFoundError):
        _ = lazy.__get__(None, dm.HutchinsonKnopoffDissonance)


def test_golden_register_magnitudes_and_ranks() -> None:
    payload = build_payload()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert payload["default_metric_mode"] == golden["default_metric_mode"]
    assert payload["n_notes"] == golden["n_notes"]
    assert payload["sethares_rank_moves"] == golden["sethares_rank_moves"]
    assert payload["hk_rank_moves"] == golden["hk_rank_moves"]
    assert payload["sethares_rank_spearman_minamp_vs_mean_pair_scaled"] == pytest.approx(
        golden["sethares_rank_spearman_minamp_vs_mean_pair_scaled"]
    )
    assert payload["hk_rank_spearman_eq3_vs_legacy"] == pytest.approx(
        golden["hk_rank_spearman_eq3_vs_legacy"]
    )
    for got, exp in zip(payload["register"], golden["register"]):
        assert got["note"] == exp["note"]
        assert got["sethares"]["minamp_norm"] == pytest.approx(exp["sethares_minamp_norm"])
        assert got["hk_eq3"] == pytest.approx(exp["hk_eq3"])
    assert golden["sethares_rank_moves"] == 0
    assert golden["hk_rank_moves"] == 0
    assert payload["mixed_sethares_rank_moves"] == golden["mixed_sethares_rank_moves"]
    assert golden["mixed_sethares_rank_moves"] > 0
    peak = golden["peak_count_sweep"]
    mean_pair = [row["sethares"]["mean_pair_scaled"] for row in peak]
    minamp = [row["sethares"]["minamp_norm"] for row in peak]
    assert mean_pair[0] > mean_pair[-1]
    assert minamp[-1] > minamp[0]
