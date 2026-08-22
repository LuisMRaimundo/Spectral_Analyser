"""Corpus manifest tooling (no live audio required)."""
from __future__ import annotations

import json
from pathlib import Path

from tools.build_corpus_manifest import AUDIO_SUFFIXES, build_manifest


def test_build_manifest_empty_root(tmp_path: Path) -> None:
    payload = build_manifest(tmp_path)
    assert payload["n_files"] == 0
    assert payload["files"] == []
    assert payload["corpus_root"] == str(tmp_path.resolve())


def test_build_manifest_records_relative_path_and_sha(tmp_path: Path) -> None:
    audio = tmp_path / "sub" / "note.wav"
    audio.parent.mkdir()
    audio.write_bytes(b"RIFF____WAVEfmt ")
    (tmp_path / "readme.txt").write_text("ignore", encoding="utf-8")
    payload = build_manifest(tmp_path)
    assert payload["n_files"] == 1
    row = payload["files"][0]
    assert row["relative_path"] == "sub/note.wav"
    assert len(row["source_sha256"]) == 64
    assert set(AUDIO_SUFFIXES)


def test_manifest_json_roundtrip(tmp_path: Path) -> None:
    dest = tmp_path / "corpus_manifest.json"
    dest.write_text(
        json.dumps(build_manifest(tmp_path), indent=2) + "\n",
        encoding="utf-8",
    )
    loaded = json.loads(dest.read_text(encoding="utf-8"))
    assert loaded["n_files"] == 0
