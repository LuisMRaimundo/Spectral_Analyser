from __future__ import annotations

from pathlib import Path

from pipeline_orchestrator_gui import build_phase1_file_iteration_order


def _touch(path: Path) -> Path:
    path.write_bytes(b"")
    return path


def test_phase1_ordering_is_monotonic_in_f0_and_deterministic(tmp_path: Path) -> None:
    files = [
        _touch(tmp_path / "zeta_unknown.wav"),
        _touch(tmp_path / "violin_A4_take.wav"),
        _touch(tmp_path / "violin_C4_take.wav"),
        _touch(tmp_path / "violin_Bb3_take.wav"),
        _touch(tmp_path / "flute_E5_take.wav"),
        _touch(tmp_path / "misc_invalid_note.mp3"),
    ]
    _ = files  # explicit: creation side effect is what matters

    ordered = build_phase1_file_iteration_order(
        tmp_path,
        enable_adaptive_path_randomization=False,
    )
    ordered_names = [p.name for p in ordered]

    # Parseable-note files must be monotonic by nominal f0:
    # Bb3 < C4 < A4 < E5. Unparseable tokens sort last by filename.
    assert ordered_names[:4] == [
        "violin_Bb3_take.wav",
        "violin_C4_take.wav",
        "violin_A4_take.wav",
        "flute_E5_take.wav",
    ]
    assert ordered_names[-2:] == [
        "misc_invalid_note.mp3",
        "zeta_unknown.wav",
    ]
