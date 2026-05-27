"""
Temporal segmentation descriptors (attack, sustain, release) derived
from envelope analysis. Used as ancillary descriptors alongside the
MIR descriptor battery.

References
----------
- Peeters, G., Giordano, B. L., Susini, P., Misdariis, N., & McAdams, S.
  (2011). The Timbre Toolbox: Extracting audio descriptors from musical
  signals. Journal of the Acoustical Society of America, 130(5), 2902–2916.

See REFERENCES.md at the repository root for canonical APA-7 entries.
"""

from __future__ import annotations

from typing import Dict

import numpy as np


def segment_attack_sustain_release(
    *,
    y: np.ndarray,
    sr_hz: float,
) -> Dict[str, Dict[str, int | float]]:
    sig = np.asarray(y, dtype=float).ravel()
    n = int(sig.size)
    if n == 0 or not np.isfinite(sr_hz) or sr_hz <= 0.0:
        return {
            "attack": {"start_sample": 0, "end_sample": 0},
            "sustain": {"start_sample": 0, "end_sample": 0},
            "release": {"start_sample": 0, "end_sample": 0},
            "log_attack_time_s": float("nan"),
        }

    sr = float(sr_hz)
    env = np.abs(sig)
    alpha = np.exp(-1.0 / max(1.0, 0.010 * sr))  # ~10 ms smoother
    for i in range(1, n):
        env[i] = alpha * env[i - 1] + (1.0 - alpha) * env[i]

    peak = float(np.max(env))
    if peak <= 0.0 or not np.isfinite(peak):
        return {
            "attack": {"start_sample": 0, "end_sample": 0},
            "sustain": {"start_sample": 0, "end_sample": n},
            "release": {"start_sample": n, "end_sample": n},
            "log_attack_time_s": float("nan"),
        }

    onset_thr = 0.1 * peak
    attack_end_thr = 0.9 * peak
    above_onset = np.where(env >= onset_thr)[0]
    a_start = int(above_onset[0]) if above_onset.size else 0
    above_attack_end = np.where(env >= attack_end_thr)[0]
    a_end = int(above_attack_end[0]) if above_attack_end.size else int(np.argmax(env))
    a_end = max(a_end, a_start + 1)

    rel_thr = 0.2 * peak
    tail = env[a_end:]
    below_rel = np.where(tail <= rel_thr)[0]
    if below_rel.size:
        r_start = int(a_end + below_rel[0])
    else:
        r_start = int(0.85 * n)
    r_start = max(r_start, a_end + 1)
    r_start = min(r_start, n)

    sustain_start = a_end
    sustain_end = r_start
    if sustain_end <= sustain_start:
        sustain_end = min(n, sustain_start + max(1, int(0.5 * n)))
        r_start = sustain_end

    attack_time_s = max((a_end - a_start) / sr, 1e-6)
    return {
        "attack": {"start_sample": a_start, "end_sample": a_end},
        "sustain": {"start_sample": sustain_start, "end_sample": sustain_end},
        "release": {"start_sample": r_start, "end_sample": n},
        "log_attack_time_s": float(np.log10(attack_time_s)),
    }
