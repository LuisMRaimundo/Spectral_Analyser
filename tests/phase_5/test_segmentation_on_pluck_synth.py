from __future__ import annotations

import numpy as np

from temporal_segmentation import segment_attack_sustain_release


def _synth_pluck(sr: int, seconds: float, f0_hz: float) -> np.ndarray:
    n = int(sr * seconds)
    t = np.arange(n, dtype=float) / float(sr)
    # Fast attack and long decay (pluck-like).
    envelope = np.exp(-t / 0.9) * (1.0 - np.exp(-t / 0.008))
    y = envelope * np.sin(2.0 * np.pi * float(f0_hz) * t)
    return y.astype(float)


def test_segmentation_on_pluck_synth() -> None:
    sr = 48000
    y = _synth_pluck(sr=sr, seconds=1.6, f0_hz=220.0)

    seg = segment_attack_sustain_release(y=y, sr_hz=sr)
    attack = seg["attack"]
    sustain = seg["sustain"]
    release = seg["release"]

    attack_dur_s = (attack["end_sample"] - attack["start_sample"]) / float(sr)
    sustain_dur = sustain["end_sample"] - sustain["start_sample"]
    release_dur = release["end_sample"] - release["start_sample"]

    assert attack_dur_s < 0.050
    assert sustain_dur > release_dur
    assert sustain_dur > (attack["end_sample"] - attack["start_sample"])
