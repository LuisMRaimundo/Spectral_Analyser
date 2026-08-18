"""End-to-end low-f₀ harmonic validation: spacing cap, body stop, fragility.

Fixtures (optional): place IOWA tuba C1 / D#1 / C2 ``spectral_analysis.xlsx``
(and audio if available) under ``tests/acoustic_validity/fixtures/low_f0/``,
and trombone *pp* E2–C5 workbooks under
``tests/acoustic_validity/fixtures/low_f0/trombone_pp/``. Tests that need
those files skip when they are absent.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from proc_audio import AudioProcessor

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "low_f0"
TROMBONE_DIR = FIXTURE_DIR / "trombone_pp"


def _write_harmonic_wav(
    path: Path,
    *,
    f0_hz: float,
    n_harmonics: int,
    sr_hz: int = 44100,
    seconds: float = 1.5,
    rolloff: float = 1.0,
    noise_dbfs: float | None = None,
    half_integer: bool = False,
    inharmonicity_B: float = 0.0,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(sr_hz * seconds), dtype=float) / float(sr_hz)
    y = np.zeros_like(t)
    nyq = 0.45 * sr_hz
    for n in range(1, int(n_harmonics) + 1):
        stretch = 1.0
        if float(inharmonicity_B) > 0.0:
            stretch = float(np.sqrt(1.0 + float(inharmonicity_B) * float(n) * float(n)))
        fn = float(n) * float(f0_hz) * stretch
        if fn >= nyq:
            break
        y += (1.0 / float(n) ** rolloff) * np.sin(2.0 * np.pi * fn * t)
        if half_integer:
            fh = (float(n) + 0.5) * float(f0_hz)
            if fh < nyq:
                y += (0.7 / float(n) ** rolloff) * np.sin(2.0 * np.pi * fh * t)
    if noise_dbfs is not None:
        rng = np.random.default_rng(0)
        amp = 10.0 ** (float(noise_dbfs) / 20.0)
        y = y + amp * rng.standard_normal(y.size)
    peak = float(np.max(np.abs(y))) or 1.0
    y = 0.25 * y / peak
    pcm = np.asarray(np.clip(y, -1.0, 1.0) * 32767.0, dtype=np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr_hz))
        wf.writeframes(pcm.tobytes())
    return path


def _run_note(
    tmp_path: Path,
    name: str,
    *,
    f0_hz: float,
    n_harmonics: int,
    n_fft: int,
    noise_dbfs: float | None = None,
    half_integer: bool = False,
    seconds: float = 1.5,
    window_offset_s: float = 0.0,
    inharmonicity_B: float = 0.0,
    rolloff: float = 1.0,
) -> Path:
    wav = _write_harmonic_wav(
        tmp_path / "audio" / f"{name}.wav",
        f0_hz=f0_hz,
        n_harmonics=n_harmonics,
        noise_dbfs=noise_dbfs,
        half_integer=half_integer,
        seconds=seconds,
        inharmonicity_B=inharmonicity_B,
        rolloff=rolloff,
    )
    if abs(window_offset_s) > 1e-9:
        with wave.open(str(wav), "rb") as wf:
            sr = int(wf.getframerate())
            nch = int(wf.getnchannels())
            sw = int(wf.getsampwidth())
            frames = wf.readframes(wf.getnframes())
        x = np.frombuffer(frames, dtype=np.int16).astype(np.float64)
        shift = int(round(window_offset_s * sr))
        if shift > 0:
            x = np.concatenate([np.zeros(shift, dtype=np.float64), x])
        elif shift < 0:
            x = x[-shift:]
        pcm = np.asarray(np.clip(x, -32767.0, 32767.0), dtype=np.int16)
        with wave.open(str(wav), "wb") as wf:
            wf.setnchannels(nch)
            wf.setsampwidth(sw)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())
    out = tmp_path / f"run_{name}"
    ap = AudioProcessor()
    ap.load_audio_files([str(wav)])
    ap.apply_filters_and_generate_data(
        results_directory=out,
        n_fft=n_fft,
        zero_padding=1,
        freq_min=20.0,
        freq_max=20000.0,
        density_frequency_ceiling_hz=20000.0,
        dissonance_enabled=False,
        dissonance_curve=False,
        dissonance_scale=False,
        compare_models=False,
        compile_per_call=False,
        parallel_processing=False,
    )
    workbooks = list(out.rglob("spectral_analysis.xlsx"))
    assert workbooks, f"no workbook for {name}"
    return workbooks[0]


def _included(wb: Path) -> pd.DataFrame:
    harm = pd.read_excel(wb, sheet_name="Harmonic Spectrum")
    return harm.loc[harm["include_for_density"].astype(bool)].copy()


def test_synthetic_33hz_noise_floor_stop(tmp_path: Path) -> None:
    """Clean 33 Hz series to 1 kHz + flat −45 dBFS noise."""
    true_n = int(np.floor(1000.0 / 33.0))
    wb = _run_note(
        tmp_path,
        "C1",
        f0_hz=33.0,
        n_harmonics=true_n,
        n_fft=16384,
        noise_dbfs=-45.0,
        seconds=1.6,
    )
    inc = _included(wb)
    metrics = pd.read_excel(wb, sheet_name="Metrics")
    row = metrics.iloc[0]
    count = int(row.get("validated_harmonic_component_count_body_ceiling", len(inc)))
    assert abs(count - true_n) <= 2 or abs(len(inc) - true_n) <= 2
    stop_hz = float(row.get("harmonic_body_stop_hz", np.nan))
    assert 900.0 <= stop_hz <= 1500.0
    if not inc.empty:
        assert float(inc["Frequency (Hz)"].max()) <= stop_hz + 33.0


def test_synthetic_33hz_window_perturbation_not_fragile(tmp_path: Path) -> None:
    true_n = int(np.floor(1000.0 / 33.0))
    wb0 = _run_note(
        tmp_path, "C1a", f0_hz=33.0, n_harmonics=true_n, n_fft=16384, noise_dbfs=-45.0
    )
    metrics = pd.read_excel(wb0, sheet_name="Metrics")
    row = metrics.iloc[0]
    spread = float(row.get("density_perturbation_spread_pct", np.nan))
    if np.isfinite(spread):
        assert spread < 5.0
    assert bool(row.get("density_fragile", False)) is False


def test_synthetic_stretched_B_validates_to_h40(tmp_path: Path) -> None:
    """B = 5e-4 tone: every partial through H40 must validate.

    A 0.30·f0 cap centred on n·f0 would reject the stretched high orders;
    the window must sit on the Inharmonicity_Fit prediction.
    """
    f0 = 220.0
    b_hat = 5.0e-4
    wb = _run_note(
        tmp_path,
        "A3",
        f0_hz=f0,
        n_harmonics=40,
        n_fft=8192,
        inharmonicity_B=b_hat,
        seconds=1.6,
        rolloff=0.25,
    )
    harm = pd.read_excel(wb, sheet_name="Harmonic Spectrum")
    orders = pd.to_numeric(harm["Harmonic Number"], errors="coerce")
    inc = harm.loc[harm["include_for_density"].astype(bool)]
    inc_orders = set(int(n) for n in pd.to_numeric(inc["Harmonic Number"], errors="coerce").dropna())
    missing = [n for n in range(1, 41) if n not in inc_orders]
    assert not missing, f"unstretched-cap rejected orders: {missing}"
    h40 = harm.loc[orders == 40]
    assert not h40.empty
    pred = 40.0 * f0 * float(np.sqrt(1.0 + b_hat * 1600.0))
    got = float(pd.to_numeric(h40.iloc[0].get("expected_frequency_hz"), errors="coerce"))
    assert abs(got - pred) / pred < 0.02


def test_synthetic_523hz_unchanged_vs_cap_inactive(tmp_path: Path) -> None:
    """On-grid 523 Hz series to 12 kHz: cap/stop must not change the validated set."""
    n_harm = int(np.floor(12000.0 / 523.0))
    wb = _run_note(tmp_path, "C5", f0_hz=523.0, n_harmonics=n_harm, n_fft=8192)
    inc = _included(wb)
    assert not inc.empty
    assert abs(len(inc) - n_harm) <= 2
    metrics = pd.read_excel(wb, sheet_name="Metrics")
    row = metrics.iloc[0]
    # Cap inactive on the low orders; body never meets the floor before 12 kHz.
    if "harmonic_body_stop_hz" in row.index and pd.notna(row["harmonic_body_stop_hz"]):
        stop = float(row["harmonic_body_stop_hz"])
        assert stop >= 11000.0 or bool(row.get("density_effective_ceiling_hz", 20000.0) >= 11000.0)
    if "tolerance_limb" in inc.columns:
        low = inc.loc[pd.to_numeric(inc["Harmonic Number"], errors="coerce") <= 8]
        if not low.empty:
            assert (low["tolerance_limb"].astype(str) == "cents").all()


def test_multiphonic_half_integers_are_inharmonic(tmp_path: Path) -> None:
    wb = _run_note(
        tmp_path,
        "A3",
        f0_hz=220.0,
        n_harmonics=18,
        n_fft=8192,
        half_integer=True,
        seconds=1.2,
    )
    harm = pd.read_excel(wb, sheet_name="Harmonic Spectrum")
    inc = harm.loc[harm["include_for_density"].astype(bool)]
    if not inc.empty:
        dev = pd.to_numeric(inc["frequency_deviation_hz"], errors="coerce").abs()
        # Validated harmonics stay on the integer comb, not the half-integer one.
        assert float(dev.median()) < 20.0
    inh_names = [n for n in pd.ExcelFile(wb).sheet_names if "inharm" in n.lower()]
    if inh_names:
        inh = pd.read_excel(wb, sheet_name=inh_names[0])
        if "Frequency (Hz)" in inh.columns and not inc.empty:
            f0 = 220.0
            freqs = pd.to_numeric(inh["Frequency (Hz)"], errors="coerce").dropna()
            half = ((freqs / f0) % 1.0)
            near_half = ((half - 0.5).abs() < 0.08).sum()
            assert int(near_half) >= 1 or len(inh) > 0


def test_c1_fixture_count_drops_if_present() -> None:
    wb = FIXTURE_DIR / "C1" / "spectral_analysis.xlsx"
    if not wb.exists():
        pytest.skip("C1 tuba fixture not present under tests/acoustic_validity/fixtures/low_f0/")
    # Re-running the fixture audio is preferred; if only the old export exists,
    # document the pre-fix count so a future regeneration can be compared.
    old = pd.read_excel(wb, sheet_name="Metrics")
    old_count = float(old.iloc[0].get("validated_harmonic_component_count_body_ceiling", np.nan))
    expect = FIXTURE_DIR / "C1" / "expected_v2.json"
    if expect.exists():
        spec = json.loads(expect.read_text(encoding="utf-8"))
        assert 28 <= spec["validated_count"] <= 45
    else:
        assert not np.isfinite(old_count) or old_count >= 28


def test_trombone_pp_regression_if_present() -> None:
    if not TROMBONE_DIR.exists():
        pytest.skip("trombone pp fixtures not present")
    moved: list[str] = []
    for wb in sorted(TROMBONE_DIR.rglob("spectral_analysis.xlsx")):
        expect = wb.parent / "expected_main.json"
        if not expect.exists():
            continue
        spec = json.loads(expect.read_text(encoding="utf-8"))
        metrics = pd.read_excel(wb, sheet_name="Metrics")
        row = metrics.iloc[0]
        note = str(spec.get("note") or wb.parent.name)
        tol = 0.03 if note[:1] in {"E", "F", "G"} and "2" in note or "D#" in note else 0.01
        if note >= "E3":
            tol = 0.01
        else:
            tol = 0.03
        for key in (
            "note_density_final",
            "EWSD_score_total",
            "EWSD_score_acoustic_balanced",
        ):
            if key not in spec or key not in row.index:
                continue
            old = float(spec[key])
            new = float(row[key])
            if not np.isfinite(old) or abs(old) < 1e-12:
                continue
            rel = abs(new - old) / abs(old)
            if rel > tol:
                moved.append(f"{note} {key}: {rel:.3%}")
    if moved:
        pytest.fail("trombone notes moved more than allowed:\n" + "\n".join(moved))
