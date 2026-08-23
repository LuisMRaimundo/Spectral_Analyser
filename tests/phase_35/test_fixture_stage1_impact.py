"""B7: fixture-only impact. No corpus re-analysis."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from acoustic_density_core import compute_acoustic_density_descriptors
from inharmonicity_model import (
    ASSIGNMENT_METHOD,
    ASSIGNMENT_METHOD_LEGACY,
    fit_inharmonicity_coefficient,
)

REPORT_PATH = Path(__file__).resolve().parent / "fixture_impact_report.json"


def _peak_table(freqs: np.ndarray, amps: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Frequency (Hz)": freqs,
            "Amplitude": amps,
            "Power": np.square(np.maximum(amps, 0.0)),
        }
    )


def _clarinet_like() -> tuple[pd.DataFrame, float]:
    f0 = 261.6
    n = np.arange(1, 21, dtype=float)
    return _peak_table(n * f0, 1.0 / n), f0


def _cello_like() -> tuple[pd.DataFrame, float]:
    f0 = 146.8
    b = 1.2e-4
    n = np.arange(1, 25, dtype=float)
    freqs = n * f0 * np.sqrt(1.0 + b * n * n)
    extra = np.array([f0 * 2.47, f0 * 3.61])
    amps = np.concatenate([1.0 / n, np.array([0.18, 0.10])])
    return _peak_table(np.concatenate([freqs, extra]), amps), f0


def _row(peaks: pd.DataFrame, f0: float, instrument: str) -> dict:
    desc = compute_acoustic_density_descriptors(
        peaks, f0_hz=f0, f0_fit_accepted=True, instrument=instrument
    )
    freqs = peaks["Frequency (Hz)"].to_numpy(dtype=float)
    new = fit_inharmonicity_coefficient(freqs, f0_hz=f0)
    old = fit_inharmonicity_coefficient(
        freqs, f0_hz=f0, assignment_method=ASSIGNMENT_METHOD_LEGACY
    )
    return {
        "instrument": instrument,
        "H_count": desc.get("detected_harmonic_slot_count"),
        "I_energy_ratio": desc.get("residual_energy_ratio"),
        "r_H": desc.get("harmonic_energy_ratio"),
        "r_I": desc.get("residual_energy_ratio"),
        "r_S": desc.get("subbass_energy_ratio"),
        "B_new": new.get("inharmonicity_coefficient_B"),
        "B_old": old.get("inharmonicity_coefficient_B"),
        "B_delta": float(new.get("inharmonicity_coefficient_B", 0.0))
        - float(old.get("inharmonicity_coefficient_B", 0.0)),
        "n_matched_new": int(np.asarray(new.get("orders_matched", [])).size),
        "n_matched_old": int(np.asarray(old.get("orders_matched", [])).size),
        "orders_missed_new": int(np.asarray(new.get("orders_missed", [])).size),
        "assignment_new": new.get("harmonic_assignment_method"),
        "assignment_old": old.get("harmonic_assignment_method"),
        "scope": desc.get("inharmonicity_model_scope"),
        "exported_B": desc.get("inharmonicity_coefficient_B"),
        "exported_stretch": desc.get("spectral_stretch_coefficient"),
    }


def test_fixture_impact_old_vs_new_assignment() -> None:
    clarinet, f0_c = _clarinet_like()
    cello, f0_v = _cello_like()
    rows = {
        "clarinet_like": _row(clarinet, f0_c, "clarinet"),
        "cello_like": _row(cello, f0_v, "cello"),
        "audio_fixtures": (
            "Sounds for testing/ is not in this repository. "
            "Impact numbers are Stage-1-equivalent peak-table fixtures "
            "(clarinet-like harmonic stack; cello-like stretched stack)."
        ),
        "acd_and_mass": (
            "ACD_score and spectral_mass v2 are Stage 3; they are not "
            "recomputed here. Expect small movement after corpus re-run."
        ),
        "corpus_reanalysis_required": True,
        "assignment_method": ASSIGNMENT_METHOD,
    }
    REPORT_PATH.write_text(json.dumps(rows, indent=2, default=float), encoding="utf-8")
    assert rows["clarinet_like"]["assignment_new"] == ASSIGNMENT_METHOD
    assert rows["cello_like"]["assignment_old"] == ASSIGNMENT_METHOD_LEGACY
    assert rows["cello_like"]["scope"] == "string_family"
    assert rows["clarinet_like"]["scope"] == "out_of_family"
