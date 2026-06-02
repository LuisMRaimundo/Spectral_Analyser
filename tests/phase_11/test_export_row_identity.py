"""Tests for export row identity and duplicate-column cleanup."""

from __future__ import annotations

import pandas as pd

from export_row_identity import (
    assign_sample_ids,
    compute_sample_id,
    dedupe_identical_columns,
    drop_dead_columns,
    merge_keys_for_frames,
)


def test_compute_sample_id_is_stable_for_duplicate_notes() -> None:
    a = compute_sample_id(note="G#4", source_file_name="file_a.wav", row_index=0)
    b = compute_sample_id(note="G#4", source_file_name="file_b.wav", row_index=1)
    assert a != b


def test_assign_sample_ids_adds_column() -> None:
    df = pd.DataFrame({"Note": ["D3", "D3"], "source_file_name": ["a.wav", "b.wav"]})
    out = assign_sample_ids(df)
    assert "sample_id" in out.columns
    assert out["sample_id"].nunique() == 2


def test_dedupe_identical_columns_drops_suffix_dupes() -> None:
    df = pd.DataFrame(
        {
            "density_component_body_weighted_sum_body_ceiling": [1.0, 2.0],
            "density_component_body_weighted_sum_body_ceiling_2": [1.0, 2.0],
        }
    )
    out = dedupe_identical_columns(df)
    assert "density_component_body_weighted_sum_body_ceiling_2" not in out.columns


def test_drop_dead_columns_removes_all_blank_columns() -> None:
    df = pd.DataFrame(
        {
            "Note": ["D3", "G4"],
            "live_metric": [1.0, 2.0],
            "dead_metric": [None, None],
            "dead_text": ["", ""],
        }
    )
    out = drop_dead_columns(df)
    assert list(out.columns) == ["Note", "live_metric"]


def test_merge_keys_for_frames_falls_back_to_note_without_matching_sample_id() -> None:
    left = pd.DataFrame(
        {
            "Note": ["D3"],
            "sample_id": ["anchor__abc123"],
        }
    )
    right = pd.DataFrame(
        {
            "Note": ["D3"],
            "f0_used_for_density_hz": [146.83],
        }
    )
    assert merge_keys_for_frames(left, right) == ["Note"]


def test_merge_keys_for_frames_uses_sample_id_when_ids_overlap() -> None:
    left = pd.DataFrame({"Note": ["D3"], "sample_id": ["same__id001"]})
    right = pd.DataFrame({"Note": ["D3"], "sample_id": ["same__id001"], "n_fft": [8192]})
    assert merge_keys_for_frames(left, right) == ["sample_id"]
