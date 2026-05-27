from __future__ import annotations

import numpy as np
import pytest

from inharmonicity_model import fit_inharmonicity_coefficient


def test_inharmonicity_recovers_known_B_within_20_percent() -> None:
    f0_hz = 55.0
    b_true = 1e-4
    orders = np.arange(1, 17, dtype=float)
    freqs = orders * f0_hz * np.sqrt(1.0 + b_true * (orders**2))

    fit = fit_inharmonicity_coefficient(
        candidate_freqs_hz=freqs,
        f0_hz=f0_hz,
        order_cap=40,
        cents_window=80.0,
    )

    assert fit["fit_status"] == "ok"
    assert float(fit["inharmonicity_coefficient_B"]) == pytest.approx(
        b_true, rel=0.20, abs=0.0
    )
