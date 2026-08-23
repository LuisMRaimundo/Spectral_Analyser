"""Gate F-062..F-068 companion stamps on a production-shaped research export."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from tools.export_research_density_workbook import export_research_workbook
from tools.validation.export_cleanup_fixture import write_compiled_workbook


EXPECTED_STAMPS = {
    "sethares_dissonance_formula_id": "F-062",
    "hutchinson_knopoff_dissonance_formula_id": "F-063",
    "vassilakis_dissonance_formula_id": "F-064",
    "selected_dissonance_value_formula_id": "F-065",
    "odd_even_harmonic_energy_ratio_formula_id": "F-066",
    "low_mid_energy_ratio_formula_id": "F-067",
    "harmonic_density_weight_formula_id": "F-068",
    "inharmonic_density_weight_formula_id": "F-068",
    "subbass_density_weight_formula_id": "F-068",
}


def test_research_export_emits_f062_to_f068_companion_stamps(tmp_path: Path) -> None:
    compiled = tmp_path / "compiled_density_metrics.xlsx"
    write_compiled_workbook(compiled)
    density = pd.read_excel(compiled, sheet_name="Density_Metrics")
    density["sethares_dissonance"] = 0.11
    density["hutchinson_knopoff_dissonance"] = 0.22
    density["vassilakis_dissonance"] = 0.33
    density["selected_dissonance_value"] = 0.11
    density["odd_even_harmonic_energy_ratio"] = 1.5
    density["low_mid_energy_ratio"] = 0.4
    density["harmonic_density_weight"] = 0.8
    density["inharmonic_density_weight"] = 0.15
    density["subbass_density_weight"] = 0.05
    meta = pd.read_excel(compiled, sheet_name="Analysis_Metadata")
    with pd.ExcelWriter(compiled, engine="openpyxl") as writer:
        density.to_excel(writer, sheet_name="Density_Metrics", index=False)
        meta.to_excel(writer, sheet_name="Analysis_Metadata", index=False)

    dest = tmp_path / "research.xlsx"
    export_research_workbook(
        input_path=compiled,
        output_path=dest,
        overwrite=True,
        no_charts=True,
        include_ewsd=True,
    )
    sdm = pd.read_excel(dest, sheet_name="Spectral_Density_Metrics")
    missing = [col for col in EXPECTED_STAMPS if col not in sdm.columns]
    assert not missing, f"missing companion stamp columns: {missing}"
    for col, fid in EXPECTED_STAMPS.items():
        assert str(sdm[col].iloc[0]) == fid, (col, sdm[col].iloc[0])
