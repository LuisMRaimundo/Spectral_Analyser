from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from analysis_policy import EXPORT_SCHEMA_VERSION
from analysis_provenance import (
    provenance_export_fields,
    resolve_analysis_provenance,
    resolve_package_version,
)
from data_integrity import validate_header_contract_consistency
from verify_export import (
    PRE_EXCLUSIVE_REASON,
    assess_workbook_comparability,
    format_report,
)


def test_provenance_stamps_package_and_git_describe() -> None:
    pkg, source = resolve_package_version()
    assert pkg != "unknown"
    assert source.startswith("pyproject.toml") or source.startswith("importlib.metadata")
    assert pkg == "4.5.0" or not source.startswith("pyproject.toml")
    p = resolve_analysis_provenance()
    assert p["package_version"] == pkg
    assert p["export_schema_version"] == EXPORT_SCHEMA_VERSION
    assert p["code_commit"] != "unknown"
    assert p["analysis_version"] not in {"", "unknown"}
    assert p["analysis_version"].startswith(pkg) or p["analysis_version"] == p["git_describe"]
    fields = provenance_export_fields()
    for key in (
        "analysis_version",
        "package_version",
        "code_commit",
        "code_dirty",
        "export_schema_version",
    ):
        assert key in fields


def test_analysis_version_is_not_a_hardcoded_fallback() -> None:
    from proc_audio import AudioProcessor

    ap = AudioProcessor()
    ap._stamp_analysis_provenance()
    assert str(ap.analysis_version) not in {"", "unknown"}
    assert str(ap.code_commit) != "unknown"
    caption = ap._component_pie_caption("A2", chart="Component energy balance")
    assert "Component energy balance · A2" in caption
    assert ap.code_commit in caption


def test_header_contract_consistency_ok_and_conflict() -> None:
    ok = validate_header_contract_consistency(
        {
            "Density_Metrics": ["note_density_final", "Note"],
            "Spectral_Density_Metrics": ["note_density_final", "Note"],
        }
    )
    assert ok["ok"] is True
    assert ok["conflicts"] == []

    a = SimpleNamespace(
        formula="A", input_domain="x", ontology_family="f1"
    )
    b = SimpleNamespace(
        formula="B", input_domain="x", ontology_family="f1"
    )

    class Flip:
        def __init__(self) -> None:
            self._n = 0

        def get(self, key, default=None):
            if key != "dup_metric":
                return default
            self._n += 1
            return a if self._n == 1 else b

    conflict = validate_header_contract_consistency(
        {
            "SheetA": ["dup_metric"],
            "SheetB": ["dup_metric"],
        },
        contracts=Flip(),  # type: ignore[arg-type]
    )
    assert conflict["ok"] is False
    assert "dup_metric" in conflict["conflicts"]


def test_verify_export_flags_run2_style_workbook(tmp_path: Path) -> None:
    path = tmp_path / "run2_spectral_analysis.xlsx"
    meta = pd.DataFrame(
        {
            "Parameter": ["analysis_version", "analysis_date"],
            "Value": ["4.0.3", "2026-08-18T21:49"],
        }
    )
    harm = pd.DataFrame(
        {
            "Harmonic Number": [1, 2],
            "Frequency (Hz)": [110.0, 220.0],
            "include_for_density": [True, True],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        meta.to_excel(writer, sheet_name="Analysis_Metadata", index=False)
        harm.to_excel(writer, sheet_name="Harmonic Spectrum", index=False)
    cmp_ = assess_workbook_comparability(path)
    assert cmp_["comparable"] is False
    assert cmp_["comparability_reason"] == PRE_EXCLUSIVE_REASON
    report = format_report(path)
    assert PRE_EXCLUSIVE_REASON in report
    assert "validated_H:" in report


def test_verify_export_flags_per_bin_energy_basis(tmp_path: Path) -> None:
    path = tmp_path / "per_bin.xlsx"
    meta = pd.DataFrame(
        {
            "Parameter": ["export_schema_version", "energy_basis"],
            "Value": [EXPORT_SCHEMA_VERSION, "per_bin"],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        meta.to_excel(writer, sheet_name="Analysis_Metadata", index=False)
    cmp_ = assess_workbook_comparability(path)
    assert cmp_["comparable"] is False
    assert cmp_["comparability_reason"] == "not comparable (per_bin_energy_basis)"


def test_energy_pie_uses_energy_sums_not_amplitude_copy() -> None:
    from proc_audio import AudioProcessor

    ap = AudioProcessor()
    ap.harmonic_energy_sum = 10.0
    ap.inharmonic_energy_sum = 1.0
    ap.subbass_energy_sum = 0.5
    trip = ap._component_energy_sum_triple_for_pie()
    assert trip == pytest.approx((10.0, 1.0, 0.5))


def test_amplitude_pie_excludes_f020_diagnostic_rows() -> None:
    from proc_audio import AudioProcessor

    ap = AudioProcessor()
    ap.f0_used_for_density_hz = 110.0
    ap.include_lf_diagnostic_in_amplitude_pie = False
    ap.subbass_list_df = pd.DataFrame(
        {
            "Frequency (Hz)": [40.0, 90.0],
            "Amplitude_raw": [2.0, 8.0],
        }
    )
    mass = ap._amplitude_pie_subbass_mass(fallback_s=10.0)
    assert mass == pytest.approx(2.0)
    ap.include_lf_diagnostic_in_amplitude_pie = True
    assert ap._amplitude_pie_subbass_mass(fallback_s=10.0) == pytest.approx(10.0)
