from __future__ import annotations

import numpy as np

from inharmonicity_model import fit_inharmonicity_coefficient


def test_inharmonicity_zero_for_exact_harmonics() -> None:
    f0_hz = 110.0
    orders = np.arange(1, 21, dtype=float)
    freqs = orders * f0_hz

    fit = fit_inharmonicity_coefficient(
        candidate_freqs_hz=freqs,
        f0_hz=f0_hz,
        order_cap=40,
        cents_window=80.0,
    )

    assert fit["fit_status"] == "ok"
    assert float(fit["inharmonicity_coefficient_B"]) < 1e-6
