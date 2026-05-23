from __future__ import annotations

import numpy as np

import dissonance_models as dm


def test_hk_g_table_provenance_is_non_empty() -> None:
    assert isinstance(dm.HK_G_TABLE_PROVENANCE, str)
    assert dm.HK_G_TABLE_PROVENANCE.strip() != ""


def test_hk_g_table_is_piecewise_monotone() -> None:
    """Allow tiny numeric jitter when checking piecewise monotonicity."""
    tol = 1e-12
    table = np.asarray(dm.HutchinsonKnopoffDissonance.DEFAULT_G_TABLE, dtype=float)
    assert table.ndim == 2 and table.shape[1] == 2

    g = table[:, 1]
    peak_idx = int(np.argmax(g))
    asc_diffs = np.diff(g[: peak_idx + 1])
    desc_diffs = np.diff(g[peak_idx:])

    assert np.all(asc_diffs >= -tol), "Ascending limb is not monotone within tolerance."
    assert np.all(desc_diffs <= tol), "Descending limb is not monotone within tolerance."
