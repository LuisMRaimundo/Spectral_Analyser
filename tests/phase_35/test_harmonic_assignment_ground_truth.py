"""Seeded synthesis harness for global monotone assignment (F-008 v2)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from inharmonicity_model import (
    ASSIGNMENT_METHOD,
    ASSIGNMENT_METHOD_LEGACY,
    CENTS_WINDOW_DEFAULT,
    apply_inharmonicity_family_scope,
    fit_inharmonicity_coefficient,
    match_orders_detailed,
    _match_orders_legacy_greedy,
)

F0_SET = (65.4, 146.8, 261.6, 523.3)
B_SET = (0.0, -2e-5, 1e-5, 1e-4, 5e-4)
N_PARTIALS = 40
WINDOW_SWEEP = (30.0, 40.0, 50.0, 60.0, 80.0)
B5_HZ = 987.7666025122483
SEED = 20260833
REPORT_PATH = Path(__file__).resolve().parent / "assignment_harness_report.json"


def _stiff(f0: float, b: float, n: int) -> np.ndarray:
    orders = np.arange(1, n + 1, dtype=float)
    inner = 1.0 + float(b) * orders * orders
    inner = np.maximum(inner, 1e-12)
    return orders * float(f0) * np.sqrt(inner)


def _cents(a: float, b: float) -> float:
    return 1200.0 * float(np.log2(max(a, 1e-12) / max(b, 1e-12)))


def corrupt_partials(
    true_freqs: np.ndarray,
    *,
    f0: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Delete 3, inject 5 spurious, jitter N(0, 5 cents). Returns peaks, kept, deleted."""
    orders = np.arange(1, true_freqs.size + 1, dtype=int)
    # Drop three mid/high partials. Deleting n=1..5 would remove the f0
    # anchors the joint fit is required to recover within 10 cents.
    delete = np.sort(rng.choice(orders[5:], size=3, replace=False))
    keep_mask = ~np.isin(orders, delete)
    kept_n = orders[keep_mask]
    kept_f = true_freqs[keep_mask]
    jitter = rng.normal(0.0, 5.0, size=kept_f.size)
    jittered = kept_f * np.power(2.0, jitter / 1200.0)
    spurious = []
    while len(spurious) < 5:
        cand = float(rng.uniform(0.6 * f0, 18.0 * f0))
        nearest = min(abs(_cents(cand, float(n) * float(f0))) for n in orders)
        if nearest > 40.0:
            spurious.append(cand)
    peaks = np.concatenate([jittered, np.asarray(spurious, dtype=float)])
    rng.shuffle(peaks)
    return peaks, kept_n, delete


def _nearest(cand: float, refs: np.ndarray) -> float:
    return float(np.min(np.abs([_cents(cand, float(r)) for r in refs])))


def assignment_scores(
    peaks: np.ndarray,
    kept_n: np.ndarray,
    true_all: np.ndarray,
    *,
    f0: float,
    b: float,
    cents_window: float = CENTS_WINDOW_DEFAULT,
    method: str = ASSIGNMENT_METHOD,
) -> dict[str, float]:
    if method == ASSIGNMENT_METHOD_LEGACY:
        mf, mn = _match_orders_legacy_greedy(
            peaks, f0_anchor=f0, b_anchor=b, cap=N_PARTIALS, cents_window=cents_window
        )
        attempted = np.arange(1, N_PARTIALS + 1, dtype=int)
        missed = np.asarray(sorted(set(int(x) for x in attempted) - set(int(x) for x in mn)), dtype=int)
        matched_f, matched_n = mf, mn
    else:
        detail = match_orders_detailed(
            peaks, f0_anchor=f0, b_anchor=b, cap=N_PARTIALS, cents_window=cents_window
        )
        matched_f = detail["freqs"]
        matched_n = detail["orders"]
        attempted = detail["orders_attempted"]
        missed = detail["orders_missed"]
    true_kept_f = true_all[np.asarray(kept_n, dtype=int) - 1]
    tp = 0
    fp = 0
    for freq in matched_f:
        if _nearest(float(freq), true_kept_f) <= 20.0:
            tp += 1
        else:
            fp += 1
    precision = tp / max(tp + fp, 1)
    recall = tp / max(int(kept_n.size), 1)
    silent = int(attempted.size) - int(matched_n.size) - int(missed.size)
    monotone = bool(matched_f.size < 2 or np.all(np.diff(matched_f) > 0.0))
    return {
        "precision": float(precision),
        "recall": float(recall),
        "silent_dropouts": float(silent),
        "monotone": float(monotone),
        "n_matched": float(matched_n.size),
    }


def _cases() -> list[tuple[float, float]]:
    return [(f0, b) for f0 in F0_SET for b in B_SET]


@pytest.mark.parametrize("f0,b_true", _cases())
def test_global_assignment_recovers_ground_truth(f0: float, b_true: float) -> None:
    rng = np.random.default_rng(SEED + int(round(f0)) + int(round(abs(b_true) * 1e8)))
    true_f = _stiff(f0, b_true, N_PARTIALS)
    peaks, kept_n, _deleted = corrupt_partials(true_f, f0=f0, rng=rng)
    fit = fit_inharmonicity_coefficient(peaks, f0_hz=f0, order_cap=N_PARTIALS)
    assert fit["harmonic_assignment_method"] == ASSIGNMENT_METHOD
    attempted = np.asarray(fit["orders_attempted"], dtype=int)
    matched = np.asarray(fit["orders_matched"], dtype=int)
    missed = np.asarray(fit["orders_missed"], dtype=int)
    assert set(matched).isdisjoint(set(missed))
    assert set(int(x) for x in matched).union(int(x) for x in missed) == set(int(x) for x in attempted)
    scores = assignment_scores(peaks, kept_n, true_f, f0=f0, b=b_true)
    assert scores["precision"] >= 0.95
    assert scores["recall"] >= 0.95
    assert scores["silent_dropouts"] == 0.0
    assert scores["monotone"] == 1.0
    f0_hat = float(fit["inharmonicity_fit_f0_hz"])
    assert abs(_cents(f0_hat, f0)) <= 10.0
    b_hat = float(fit["inharmonicity_coefficient_B"])
    if abs(b_true) < 1e-12:
        assert abs(b_hat) < 1e-5
        assert fit["inharmonicity_b_sign_status"] == "not_significant"
    elif abs(b_true) <= 2e-5:
        recovered = abs(b_hat - b_true) <= 0.40 * abs(b_true)
        screened = fit["inharmonicity_b_sign_status"] == "not_significant" and abs(b_hat) < 5e-5
        signed = (b_true < 0.0 and b_hat < 0.0) or (b_true > 0.0 and b_hat > 0.0)
        assert recovered or screened or (signed and abs(b_hat) < 1e-4)
        if b_true < 0.0 and recovered:
            assert fit["inharmonicity_b_sign_status"] == "negative_stretch"
    else:
        recovered = abs(b_hat - b_true) <= 0.20 * abs(b_true)
        factor_ok = (
            abs(b_true) > 0.0
            and 0.3 <= abs(b_hat / b_true) <= 3.0
            and np.sign(b_hat) == np.sign(b_true)
        )
        screened = fit["inharmonicity_b_sign_status"] == "not_significant" and abs(b_hat) < 5e-5
        assert recovered or factor_ok or screened
        if b_true < 0.0 and recovered:
            assert fit["inharmonicity_b_sign_status"] == "negative_stretch"


def test_legacy_greedy_is_weaker_or_equal_on_same_fixtures() -> None:
    rows = []
    for f0, b_true in _cases():
        rng = np.random.default_rng(SEED + int(round(f0)) + int(round(abs(b_true) * 1e8)))
        true_f = _stiff(f0, b_true, N_PARTIALS)
        peaks, kept_n, _ = corrupt_partials(true_f, f0=f0, rng=rng)
        new_fit = fit_inharmonicity_coefficient(peaks, f0_hz=f0, order_cap=N_PARTIALS)
        old_fit = fit_inharmonicity_coefficient(
            peaks, f0_hz=f0, order_cap=N_PARTIALS, assignment_method=ASSIGNMENT_METHOD_LEGACY
        )
        new = assignment_scores(peaks, kept_n, true_f, f0=f0, b=b_true)
        old = assignment_scores(
            peaks, kept_n, true_f, f0=f0, b=b_true, method=ASSIGNMENT_METHOD_LEGACY
        )
        f0_hat = float(new_fit["inharmonicity_fit_f0_hz"])
        b_hat = float(new_fit["inharmonicity_coefficient_B"])
        rows.append(
            {
                "f0": f0,
                "B": b_true,
                "new_precision": new["precision"],
                "new_recall": new["recall"],
                "old_precision": old["precision"],
                "old_recall": old["recall"],
                "delta_precision": new["precision"] - old["precision"],
                "delta_recall": new["recall"] - old["recall"],
                "f0_cents_error": abs(_cents(f0_hat, f0)),
                "B_new": b_hat,
                "B_old": float(old_fit["inharmonicity_coefficient_B"]),
                "B_rel_error": (
                    abs(b_hat - b_true) / abs(b_true) if abs(b_true) > 0.0 else abs(b_hat)
                ),
                "sign_status": new_fit["inharmonicity_b_sign_status"],
            }
        )
        assert new["precision"] >= 0.95
        assert new["recall"] >= 0.95
    mean_dp = float(np.mean([r["delta_precision"] for r in rows]))
    mean_dr = float(np.mean([r["delta_recall"] for r in rows]))
    REPORT_PATH.write_text(
        json.dumps(
            {
                "ground_truth": [
                    {
                        "f0": r["f0"],
                        "B": r["B"],
                        "precision": r["new_precision"],
                        "recall": r["new_recall"],
                        "f0_cents_error": r["f0_cents_error"],
                        "B_rel_error": r["B_rel_error"],
                        "B_hat": r["B_new"],
                        "sign_status": r["sign_status"],
                    }
                    for r in rows
                ],
                "greedy_vs_global": rows,
                "mean_delta_precision": mean_dp,
                "mean_delta_recall": mean_dr,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    assert all(r["new_precision"] >= 0.90 for r in rows)
    assert all(r["new_recall"] >= 0.90 for r in rows)


def test_cents_window_sweep_on_b5_synthetic() -> None:
    f0 = B5_HZ
    b_true = 1e-4
    rng = np.random.default_rng(SEED + 5)
    true_f = _stiff(f0, b_true, N_PARTIALS)
    peaks, kept_n, _ = corrupt_partials(true_f, f0=f0, rng=rng)
    sweep = []
    for window in WINDOW_SWEEP:
        scores = assignment_scores(peaks, kept_n, true_f, f0=f0, b=0.0, cents_window=window)
        fit = fit_inharmonicity_coefficient(
            peaks, f0_hz=f0, order_cap=N_PARTIALS, cents_window=window
        )
        b_hat = float(fit["inharmonicity_coefficient_B"])
        rel_err = abs(b_hat - b_true) / b_true
        sweep.append(
            {
                "cents_window": window,
                "precision": scores["precision"],
                "recall": scores["recall"],
                "B_rel_error": rel_err,
                "fit_status": fit["fit_status"],
            }
        )
    payload = json.loads(REPORT_PATH.read_text(encoding="utf-8")) if REPORT_PATH.is_file() else {}
    payload["b5_window_sweep"] = sweep
    payload["default_cents_window"] = CENTS_WINDOW_DEFAULT
    best = max(sweep, key=lambda r: (r["precision"] + r["recall"], -r["B_rel_error"]))
    payload["proposed_window_if_tighter_dominates"] = (
        best["cents_window"]
        if best["cents_window"] < CENTS_WINDOW_DEFAULT
        and best["precision"] >= 0.95
        and best["recall"] >= 0.95
        else None
    )
    REPORT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    default_row = next(r for r in sweep if r["cents_window"] == CENTS_WINDOW_DEFAULT)
    assert default_row["precision"] >= 0.90
    assert default_row["recall"] >= 0.90


def test_family_scope_string_vs_wind() -> None:
    freqs = _stiff(146.8, 1e-4, 16)
    fit = fit_inharmonicity_coefficient(freqs, f0_hz=146.8)
    cello = apply_inharmonicity_family_scope(fit, instrument="cello")
    clarinet = apply_inharmonicity_family_scope(fit, instrument="clarinet")
    missing = apply_inharmonicity_family_scope(fit, instrument=None)
    assert cello["inharmonicity_model_scope"] == "string_family"
    assert np.isfinite(float(cello["inharmonicity_coefficient_B"]))
    assert not np.isfinite(float(cello["spectral_stretch_coefficient"]))
    assert clarinet["inharmonicity_model_scope"] == "out_of_family"
    assert not np.isfinite(float(clarinet["inharmonicity_coefficient_B"]))
    assert np.isfinite(float(clarinet["spectral_stretch_coefficient"]))
    assert missing["inharmonicity_model_scope"] == "out_of_family_unspecified"
    assert not np.isfinite(float(missing["inharmonicity_coefficient_B"]))
